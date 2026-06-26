# modules/egp_boq_workspace.py

import streamlit as st
import pandas as pd
import sqlite3
import os
from modules.matching_engine import search_best_pwd_match
from utils.currency_transformer import number_to_bangladesh_taka_words
#from database.competitor_db import calculate_win_probability
from database.unified_db_manager import UnifiedDatabaseManager
from utils.data_sanitizer import sanitize_text, sanitize_item_code
from modules.rbac import (
    rbac, can_view_tenders, can_create_tender, can_edit_tender,
    can_submit_bid, can_manage_team, can_export_data,
    render_role_badge, require_permission
)

db = UnifiedDatabaseManager()
DB_PATH = db.db_path 


def render_boq_workspace():
    """e-GP BOQ Workspace with RBAC"""
    
    # Get current user info
    current_user = st.session_state.get("username", "Unknown User")
    current_role = st.session_state.get("user_role", "user")
    permissions = rbac.get_current_user_permissions()
    
    st.markdown("""
    <div class="main-header">
        <h1>🏗️ e-GP BOQ Workspace</h1>
        <p>Relational Tender estimation suite and PWD automated cost tracking</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Render role badge
    render_role_badge()
    st.markdown("---")
    
    st.markdown(f"**Operator Context:** {st.session_state.get('full_name', current_user)} | **Security Clearance Tier:** `{current_role.upper()}`")
    
    # Check if user has access to e-GP workspace (based on subscription/permissions)
    subscription = db.get_user_subscription(st.session_state.user_id)
    is_premium = subscription.get('plan') in ['professional', 'enterprise'] or current_role in ['admin', 'system_admin']
    
    if not is_premium:
        st.warning("⚠️ e-GP BOQ Workspace is available for Professional and Enterprise plans only.")
        if st.button("💳 Upgrade to Access", use_container_width=True):
            st.session_state.page = "subscription"
            st.rerun()
        return
    
    def get_original_pwd_rate(pwd_code, zone):
        if not pwd_code or pwd_code == "N/A": 
            return None
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT unit_rate FROM pwd_rates WHERE pwd_code=? AND zone_name=?", (str(pwd_code).strip(), zone))
        res = cursor.fetchone()
        conn.close()
        return float(res[0]) if res else None

    # Load active data matrices
    conn = sqlite3.connect(DB_PATH)
    active_tenders = pd.read_sql_query(
        "SELECT tender_id FROM tenders_boq_meta WHERE workflow_status != 'Approved'", 
        conn
    )['tender_id'].tolist()
    conn.close()
    
    # Define tabs based on permissions
    tab_list = ["🎯 Ingestion & Workspace", "📈 Global Adjustments & Analytics"]
    
    # Only show competitor tab if user has appropriate permissions
    if permissions.get('can_view_tenders') or current_role in ['admin', 'system_admin', 'company_admin', 'manager']:
        tab_list.append("🔮 Competitor Intelligence Matrix")
    
    tab_list.append("🗄️ Relational Corporate Archive")
    
    tabs = st.tabs(tab_list)
    tab_idx = 0
    
    # ==========================================
    # 🎯 TAB 1: INGESTION & WORKSPACE WORKBENCH
    # ==========================================
    with tabs[tab_idx]:
        _render_ingestion_tab(current_user, current_role, permissions, active_tenders, get_original_pwd_rate)
    tab_idx += 1
    
    # ==========================================
    # 📈 TAB 2: OVERHEADS & ANALYTICS
    # ==========================================
    with tabs[tab_idx]:
        _render_analytics_tab(current_role, permissions, active_tenders, get_original_pwd_rate)
    tab_idx += 1
    
    # ==========================================
    # 🔮 TAB 3: COMPETITOR INTELLIGENCE MATRIX (conditional)
    # ==========================================
    if len(tabs) > tab_idx and "🔮 Competitor Intelligence Matrix" in tab_list:
        with tabs[tab_idx]:
            _render_competitor_tab(active_tenders)
        tab_idx += 1
    
    # ==========================================
    # 🗄️ TAB 4: CORPORATE LEDGER EXPORT PANEL
    # ==========================================
    with tabs[tab_idx]:
        _render_export_tab(permissions)


def _render_ingestion_tab(current_user, current_role, permissions, active_tenders, get_original_pwd_rate):
    """Render the Ingestion & Workspace tab"""
    
    can_create = permissions.get('can_create_tender', False) or current_role in ['admin', 'system_admin', 'company_admin']
    can_edit = permissions.get('can_edit_tender', False) or current_role in ['admin', 'system_admin', 'company_admin', 'manager']
    
    # Initialize workspace creation section
    if can_create:
        with st.expander("🆕 Initialize a New e-GP Tender Instance Workspace", expanded=not bool(active_tenders)):
            col_init1, col_init2 = st.columns(2)
            with col_init1:
                new_tid = st.text_input("e-GP Tender Reference ID (e.g., 945321)").strip()
                new_agency = st.text_input("Procuring Agency Context Name (e.g., LGED / PWD)")
                b_cap = st.number_input("Official Estimated Budget Cap (BDT)", min_value=0.0)
            with col_init2:
                new_zone = st.selectbox("Cost Zone Matrix Selection", ["Dhaka", "Chattogram", "Rajshahi", "Khulna"])
                new_file = st.file_uploader("Upload Blank e-GP Template Document Worksheet (.xlsx)", type=["xlsx"])
                
                if st.button("Ingest File & Run Fuzzy Match Alignment"):
                    if new_tid and new_file:
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT OR REPLACE INTO tenders_boq_meta 
                            (tender_id, ministry_or_agency, selected_zone, workflow_status, official_budget_cap, created_by) 
                            VALUES (?, ?, ?, 'Draft', ?, ?)
                        """, (new_tid, new_agency, new_zone, b_cap, current_user))
                        
                        df_in = pd.read_excel(new_file)
                        cursor.execute("DELETE FROM tender_boq_items WHERE tender_id = ?", (new_tid,))
                        
                        for _, row in df_in.iterrows():
                            raw_code = row.get('Item Code (if any)')
                            raw_desc = row.get('Description of Item')
                            c_qty = float(row.get('Quantity', 0))
                            
                            c_code = sanitize_item_code(raw_code)
                            c_desc = sanitize_text(raw_desc)
                            
                            _, m_desc, m_unit, m_rate, _ = search_best_pwd_match(c_code, c_desc, zone=new_zone)
                            
                            cursor.execute('''
                                INSERT INTO tender_boq_items 
                                (tender_id, item_no, group_name, item_code, description, unit, quantity, unit_rate, last_modified_by)
                                VALUES (?,?,?,?,?,?,?,?,?)
                            ''', (new_tid, str(row.get('Item no.')), str(row.get('Group')), c_code, m_desc, m_unit, c_qty, m_rate, current_user))
                        
                        conn.commit()
                        conn.close()
                        st.success(f"Workspace generated successfully for Tender #{new_tid}!")
                        st.rerun()
    
    # Check if there are active tenders to display
    if not active_tenders:
        st.info("No active pipeline workspace drafts available. Initialize a project using the creation tools above.")
        return

    # Select and load active tender
    st.markdown("---")
    select_tender_id = st.selectbox("Select Active Workspace Pipeline to Review", active_tenders)
    
    # Load tender metadata and items
    conn = sqlite3.connect(DB_PATH)
    t_meta_df = pd.read_sql_query(
        "SELECT workflow_status, selected_zone, ministry_or_agency, official_budget_cap FROM tenders_boq_meta WHERE tender_id = ?", 
        conn, 
        params=(select_tender_id,)
    )
    
    df_items = pd.read_sql_query(
        "SELECT id, item_no, group_name, item_code, description, unit, quantity, unit_rate FROM tender_boq_items WHERE tender_id = ?", 
        conn, 
        params=(select_tender_id,)
    )
    conn.close()
    
    if df_items.empty:
        st.warning(f"No BOQ items found for tender #{select_tender_id}. Please check the data or re-upload the file.")
        return
    
    df_items['Total Price'] = df_items['quantity'] * df_items['unit_rate']
    gross_base_cost = float(df_items['Total Price'].sum())
    
    budget_limit = 0.0
    if not t_meta_df.empty:
        budget_limit = float(t_meta_df.iloc[0]['official_budget_cap'])
    
    if budget_limit > 0:
        variance = budget_limit - gross_base_cost
        if variance < 0:
            st.error(f"🚨 BUDGET VIOLATION: Proposed pricing total (BDT {gross_base_cost:,.2f}) exceeds budget cap (BDT {budget_limit:,.2f}) by BDT {abs(variance):,.2f}!")
        else:
            st.success(f"✅ Estimate Within Limits. Remaining Margin: BDT {variance:,.2f}")

    # Validation
    validation_flags = []
    for _, r in df_items.iterrows():
        base_r = get_original_pwd_rate(r['item_code'], t_meta_df.iloc[0]['selected_zone'] if not t_meta_df.empty else "Dhaka")
        if base_r and abs(((r['unit_rate'] - base_r) / base_r) * 100) > 10.0:
            validation_flags.append({
                "Item No": r['item_no'], 
                "Code": r['item_code'], 
                "Current": r['unit_rate'], 
                "PWD Base": base_r
            })
    
    if validation_flags:
        st.warning("⚠️ Variation Flag: Rates deviate by more than ±10% from PWD reference indices.")
        st.dataframe(pd.DataFrame(validation_flags), use_container_width=True, hide_index=True)

    # Determine if user can edit
    workflow_status = t_meta_df.iloc[0]['workflow_status'] if not t_meta_df.empty else 'Draft'
    can_edit_boq = can_edit and workflow_status != 'Approved'
    
    # Display data editor
    edited_grid = st.data_editor(
        df_items,
        hide_index=True,
        disabled=['id', 'item_no', 'group_name', 'item_code', 'description', 'unit', 'quantity'] if not can_edit_boq else ['id', 'item_no', 'group_name', 'item_code', 'description', 'unit'],
        use_container_width=True,
        key=f"grid_{select_tender_id}"
    )
    
    # Save changes if editable
    if can_edit_boq:
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            if st.button("💾 Save Matrix Pricing Changes"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                for _, r in edited_grid.iterrows():
                    cursor.execute(
                        "UPDATE tender_boq_items SET unit_rate = ?, last_modified_by = ? WHERE id = ?", 
                        (float(r['unit_rate']), current_user, int(r['id']))
                    )
                conn.commit()
                conn.close()
                st.toast("Sandbox changes saved!", icon="✅")
                st.rerun()
        
        with col_b2:
            if budget_limit > 0 and gross_base_cost > budget_limit:
                if st.button("⚖️ Run Auto-Balancing Optimizer"):
                    ratio = budget_limit / gross_base_cost
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE tender_boq_items SET unit_rate = unit_rate * ? WHERE tender_id = ?", 
                        (ratio, select_tender_id)
                    )
                    conn.commit()
                    conn.close()
                    st.rerun()
        
        with col_b3:
            if workflow_status == 'Draft' and permissions.get('can_submit_bid', False):
                if st.button("📤 Escalate to Executive Review"):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE tenders_boq_meta SET workflow_status = 'Pending Approval' WHERE tender_id = ?", 
                        (select_tender_id,)
                    )
                    conn.commit()
                    conn.close()
                    st.rerun()

    # Signature Authentication
    if workflow_status == 'Pending Approval':
        st.markdown("---")
        if current_role not in ['admin', 'system_admin']:
            st.info("🔒 Awaiting sign-off from an administrative manager.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Sign, Approve & Lock Schedule"):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE tenders_boq_meta
                        SET workflow_status = 'Approved', approved_by = ?
                        WHERE tender_id = ?
                    """, (current_user, select_tender_id))
                    conn.commit()
                    conn.close()
                    st.rerun()
            
            with c2:
                if st.button("❌ Reject to Draft"):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE tenders_boq_meta
                        SET workflow_status = 'Draft'
                        WHERE tender_id = ?
                    """, (select_tender_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()


def _render_analytics_tab(current_role, permissions, active_tenders, get_original_pwd_rate):
    """Render Global Adjustments & Analytics tab"""
    
    st.subheader("⚙️ Global Scale Factor Injectors")
    
    can_edit = permissions.get('can_edit_tender', False) or current_role in ['admin', 'system_admin', 'company_admin', 'manager']
    
    if not can_edit:
        st.warning("🔒 Overhead manipulation operations are restricted.")
        return
    
    col_m1, col_m2 = st.columns(2)
    p_margin = col_m1.slider("Profit Margin markup factor (%)", 0.0, 25.0, 10.0, step=0.5)
    v_margin = col_m2.slider("Government VAT / Corporate Tax markup (%)", 0.0, 15.0, 7.5, step=0.5)
    
    if st.button("⚡ Apply Global Markups"):
        # This would need to know which tender to apply to - simplified for now
        st.info("Select a tender from the Ingestion tab first to apply markups.")


def _render_competitor_tab(active_tenders):
    """Render Competitor Intelligence Matrix tab"""
    
    st.subheader("🔮 Market Intelligence & Predictive Analysis Engine")
    
    if not active_tenders:
        st.info("No active tenders available. Create a tender workspace first.")
        return
    
    select_tender_id = st.selectbox("Select Tender for Analysis", active_tenders)
    
    if not select_tender_id:
        return
    
    # Get BOQ total for this tender
    conn = sqlite3.connect(DB_PATH)
    df_items = pd.read_sql_query(
        "SELECT quantity, unit_rate FROM tender_boq_items WHERE tender_id = ?", 
        conn, 
        params=(select_tender_id,)
    )
    conn.close()
    
    gross_base_cost = (df_items['quantity'] * df_items['unit_rate']).sum() if not df_items.empty else 0
    
    col_cp1, col_cp2 = st.columns(2)
    
    with col_cp1:
        with st.form("comp_form", clear_on_submit=True):
            c_name = st.text_input("Competitor Company Name")
            c_amt = st.number_input("Total Contract Value Offered (BDT)", min_value=0.0)
            c_won = st.checkbox("Mark as Lowest Responsive L1 Candidate Winner")
            
            if st.form_submit_button("Record Competitor Metrics"):
                if c_name and c_amt > 0:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    
                    if c_won:
                        cursor.execute("UPDATE competitor_bids SET is_winner = 0 WHERE tender_id = ?", (select_tender_id,))
                    
                    cursor.execute("""
                        INSERT INTO competitor_bids (tender_id, competitor_name, total_bid_amount, is_winner)
                        VALUES (?, ?, ?, ?)
                    """, (select_tender_id, c_name, c_amt, 1 if c_won else 0))
                    
                    conn.commit()
                    conn.close()
                    st.success("Competitor recorded!")
                    st.rerun()
    
    with col_cp2:
        pct, r_desc = calculate_win_probability(select_tender_id, gross_base_cost)
        if pct is not None:
            st.metric("Calculated Win Probability", f"{pct}%", delta=r_desc)
        
        conn = sqlite3.connect(DB_PATH)
        df_comps = pd.read_sql_query("""
            SELECT competitor_name AS 'Bidder Name', total_bid_amount AS 'Bid Amount (BDT)'
            FROM competitor_bids WHERE tender_id = ?
            ORDER BY total_bid_amount ASC
        """, conn, params=(select_tender_id,))
        conn.close()
        
        if not df_comps.empty:
            my_co = pd.DataFrame([{"Bidder Name": "★ Your Company (TenderAI Live)", "Bid Amount (BDT)": gross_base_cost}])
            st.dataframe(pd.concat([df_comps, my_co]).sort_values(by="Bid Amount (BDT)"), use_container_width=True, hide_index=True)


def _render_export_tab(permissions):
    """Render Corporate Ledger Export Panel tab"""
    
    st.subheader("📚 Signed Enterprise Historical Archives Vault")
    
    can_export = permissions.get('can_export_data', False)
    
    conn = sqlite3.connect(DB_PATH)
    df_arch = pd.read_sql_query("""
        SELECT tender_id AS 'Tender ID', ministry_or_agency AS 'Agency', 
               selected_zone AS 'Zone Context', workflow_status AS 'Status'
        FROM tenders_boq_meta
        ORDER BY created_at DESC
    """, conn)
    conn.close()
    
    if df_arch.empty:
        st.info("No recorded historical tender profiles in archives.")
    else:
        st.dataframe(df_arch, use_container_width=True, hide_index=True)
    
    app_list = df_arch[df_arch["Status"] == "Approved"]["Tender ID"].tolist()
    
    if not app_list:
        st.warning("🔒 Export locked: Package must receive Approved signature first.")
    else:
        sel_exp = st.selectbox("Select Signed Tender Framework for Compilation", app_list)
        
        if st.button("Compile Output Deliverable Workbook"):
            conn = sqlite3.connect(DB_PATH)
            df_final = pd.read_sql_query("""
                SELECT item_no, group_name, item_code, description, unit, quantity, unit_rate
                FROM tender_boq_items WHERE tender_id = ?
            """, conn, params=(sel_exp,))
            conn.close()
            
            df_final["Total Price In Figures (BDT)"] = df_final["quantity"] * df_final["unit_rate"]
            df_final["Unit Price In Words (BDT)"] = df_final["unit_rate"].apply(number_to_bangladesh_taka_words)
            df_final["Total Price In Words (BDT)"] = df_final["Total Price In Figures (BDT)"].apply(number_to_bangladesh_taka_words)
            
            out = df_final.rename(columns={
                "item_no": "Item no.",
                "group_name": "Group",
                "item_code": "Item Code (if any)",
                "description": "Description of Item",
                "unit": "Measurement Unit",
                "quantity": "Quantity",
            }).drop(columns=["unit_rate"])
            
            out["Unit Price In Figures (BDT)"] = out["Unit Price In Words (BDT)"].apply(lambda x: "N/A")
            out["Total Price In Figures (BDT)"] = out["Total Price In Figures (BDT)"].map(lambda x: f"{x:,.2f}")
            
            fname = f"Finalized_eGP_BOQ_{sel_exp}.xlsx"
            out.to_excel(fname, index=False)
            
            with open(fname, "rb") as f:
                st.download_button("Download Official Locked e-GP Spreadsheet Package", f, file_name=fname)