# modules/tender_boq_workspace.py - Refactored to use DatabaseCRUD

import streamlit as st
import pandas as pd
import numpy as np
import difflib
import io
from database.unified_db_manager import get_db_manager

from modules.matching_engine import search_best_pwd_match
from utils.currency_transformer import number_to_bangladesh_taka_words
from utils.data_sanitizer import sanitize_text, sanitize_item_code

# Note: Ensure calculate_win_probability is imported from your analytics module
# from modules.analytics import calculate_win_probability 

# 1. Platform Infrastructure Foundations
st.set_page_config(layout="wide", page_title="TenderAI Enterprise Workspace")

# Initialize DB Manager (Singleton)
db = get_db_manager()

# 2. Extract Session Security Access Contexts
current_user = st.session_state.get("username", None)
current_role = st.session_state.get("role", "User") 

if not st.session_state.get("authenticated", False) or current_user is None:
    st.error("🚨 Access Denied: Please log in through the main iTender Dashboard gateway first.")
    st.stop()

# Helper Lookups
def get_original_pwd_rate(pwd_code, zone):
    """Get original PWD rate using DatabaseCRUD"""
    if not pwd_code or pwd_code == "N/A": 
        return None
    result = db.query_one(
        "SELECT unit_rate FROM pwd_rates WHERE pwd_code = ? AND zone_name = ?", 
        (str(pwd_code).strip(), zone)
    )
    return float(result['unit_rate']) if result and result.get('unit_rate') is not None else None

st.title("🚀 TenderAI - Enterprise Bid Management & Estimation Suite")
st.markdown(f"**Operator Identity:** {current_user} | **Security Clearance Tier:** `{current_role}`")

# Discovery Loop - Using query instead of direct Supabase
df_active = db.query("SELECT tender_id FROM tenders_boq_meta WHERE workflow_status != 'Approved'")
active_tenders = [row['tender_id'] for row in df_active] if df_active else []

if not active_tenders:
    st.warning("⚠️ No active draft workspaces found in the sandbox repository pipeline.")
    if current_role in ["Admin", "Company Admin", "Individual"]:
        with st.expander("🆕 Initialize a Named e-GP Tender Instance", expanded=True):
            col_init1, col_init2 = st.columns(2)
            with col_init1:
                new_tid = st.text_input("e-GP Tender ID (e.g., 945321)").strip()
                new_agency = st.text_input("Procuring Entity Context Name (e.g., LGED)")
                b_cap = st.number_input("Official Government Estimated Budget Cap (BDT)", min_value=0.0)
            with col_init2:
                new_zone = st.selectbox("Cost Zone Evaluation Matrix", ["Dhaka", "Chattogram", "Rajshahi", "Khulna"])
                new_file = st.file_uploader("Upload Blank e-GP Matrix Worksheet (.xlsx)", type=["xlsx"])
                
            if st.button("Ingest, Parse & Run Fuzzy Alignment Filters"):
                if new_tid and new_file:
                    # ✅ Use db.execute instead of supabase_client
                    # Upsert tender metadata
                    db.execute("""
                        INSERT INTO tenders_boq_meta (tender_id, ministry_or_agency, selected_zone, workflow_status, official_budget_cap, created_by)
                        VALUES (?, ?, ?, 'Draft', ?, ?)
                        ON CONFLICT (tender_id) DO UPDATE SET
                            ministry_or_agency = EXCLUDED.ministry_or_agency,
                            selected_zone = EXCLUDED.selected_zone,
                            workflow_status = EXCLUDED.workflow_status,
                            official_budget_cap = EXCLUDED.official_budget_cap,
                            created_by = EXCLUDED.created_by
                    """, (new_tid, new_agency, new_zone, float(b_cap), current_user))
                    
                    df_in = pd.read_excel(new_file)
                    
                    # Delete existing items
                    db.execute("DELETE FROM tender_boq_items WHERE tender_id = ?", (new_tid,))
                    
                    # Prepare items for batch insert
                    items_to_insert = []
                    for _, row in df_in.iterrows():
                        c_code = row.get('Item Code (if any)')
                        c_desc = row.get('Description of Item')
                        c_qty = float(row.get('Quantity', 0))
                        
                        _, m_desc, m_unit, m_rate, _ = search_best_pwd_match(c_code, c_desc, zone=new_zone)
                        
                        items_to_insert.append({
                            'tender_id': new_tid,
                            'item_no': str(row.get('Item no.')),
                            'group_name': str(row.get('Group')),
                            'item_code': str(c_code),
                            'description': m_desc,
                            'unit': m_unit,
                            'quantity': c_qty,
                            'unit_rate': float(m_rate) if m_rate else 0.0,
                            'last_modified_by': current_user
                        })
                    
                    if items_to_insert:
                        # ✅ Use db.execute for each insert
                        for item in items_to_insert:
                            db.execute("""
                                INSERT INTO tender_boq_items (
                                    tender_id, item_no, group_name, item_code, description, 
                                    unit, quantity, unit_rate, last_modified_by
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                item['tender_id'], item['item_no'], item['group_name'], 
                                item['item_code'], item['description'], item['unit'],
                                item['quantity'], item['unit_rate'], item['last_modified_by']
                            ))
                        
                    st.success(f"Tender Workspace #{new_tid} created successfully!")
                    st.rerun()
    st.stop()

# Load Active Workspace States
select_tender_id = st.selectbox("Select Target Active Pipeline Workspace to Review", active_tenders)

df_meta = db.query(
    "SELECT workflow_status, selected_zone, ministry_or_agency, official_budget_cap FROM tenders_boq_meta WHERE tender_id = ?", 
    (select_tender_id,)
)
if not df_meta:
    st.error("Tender metadata not found.")
    st.stop()
    
t_meta = df_meta[0]

df_items = db.query(
    "SELECT id, item_no, group_name, item_code, description, unit, quantity, unit_rate FROM tender_boq_items WHERE tender_id = ?", 
    (select_tender_id,)
)

# Evaluate Metrics Realtime Calculations
if df_items:
    for item in df_items:
        item['Total Price'] = item['quantity'] * item['unit_rate']
    gross_base_cost = float(sum(item['Total Price'] for item in df_items))
else:
    gross_base_cost = 0.0
budget_limit = float(t_meta.get('official_budget_cap')) if t_meta.get('official_budget_cap') else 0.0

tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Active Workspace Workbench", 
    "📈 Strategic Pricing Analytics & Overheads", 
    "🔮 Competitor Intelligence Matrix",
    "🗄️ Relational Corporate Archive Ledger"
])

# ==========================================
# 🎯 TAB 1: ACTIVE WORKSPACE WORKBENCH
# ==========================================
with tab1:
    st.markdown(f"### 📍 Client: {t_meta.get('ministry_or_agency', 'N/A')} | Pipeline Status: **`{t_meta.get('workflow_status', 'Draft')}`**")
    
    # Core Budget Guard Real-Time Alert System
    if budget_limit > 0:
        budget_variance = budget_limit - gross_base_cost
        if budget_variance < 0:
            st.error(f"🚨 BUDGET VIOLATION CRITICAL WARNING: Current estimate (BDT {gross_base_cost:,.2f}) exceeds the official government budget cap (BDT {budget_limit:,.2f}) by BDT {abs(budget_variance):,.2f}!")
        else:
            st.success(f"✅ Budget Cap Guard Active: Offer is safe. Cushion margin remaining: BDT {budget_variance:,.2f}")

    can_edit = (current_role in ["Admin", "Company Admin", "Individual"]) and (t_meta.get('workflow_status') != 'Approved')
    
    # Convert to DataFrame for display
    df_display = pd.DataFrame(df_items) if df_items else pd.DataFrame()
    disabled_cols = ['id', 'item_no', 'group_name', 'item_code', 'description', 'unit', 'quantity']
    
    if not df_display.empty:
        edited_grid = st.data_editor(
            df_display,
            hide_index=True,
            disabled=disabled_cols,
            use_container_width=True,
            key=f"live_editor_{select_tender_id}"
        )
    else:
        st.info("No items found in this tender workspace.")
        edited_grid = pd.DataFrame()
    
    if can_edit and not edited_grid.empty:
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            if st.button("💾 Commit Adjustments & Log Changes"):
                logs_to_insert = []
                for _, r in edited_grid.iterrows():
                    item_db_id = int(r['id'])
                    new_rate = float(r['unit_rate'])
                    
                    orig = db.query_one("SELECT unit_rate, item_code, item_no FROM tender_boq_items WHERE id = ?", (item_db_id,))
                    if orig and float(orig['unit_rate']) != new_rate:
                        db.execute("""
                            UPDATE tender_boq_items 
                            SET unit_rate = ?, last_modified_by = ?
                            WHERE id = ?
                        """, (new_rate, current_user, item_db_id))
                        
                        logs_to_insert.append({
                            'tender_id': select_tender_id,
                            'item_code': orig['item_code'],
                            'item_no': orig['item_no'],
                            'old_rate': float(orig['unit_rate']),
                            'new_rate': new_rate,
                            'modified_by': current_user
                        })
                
                if logs_to_insert:
                    for log in logs_to_insert:
                        db.execute("""
                            INSERT INTO price_change_logs (tender_id, item_code, item_no, old_rate, new_rate, modified_by)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (log['tender_id'], log['item_code'], log['item_no'], log['old_rate'], log['new_rate'], log['modified_by']))
                        
                st.toast(f"Changes saved successfully! Logged {len(logs_to_insert)} modifications.", icon="✅")
                st.rerun()
                
        with col_s2:
            # AUTO-BALANCING ALGORITHM LAYER
            if budget_limit > 0 and gross_base_cost > budget_limit:
                if st.button("⚖️ Run Auto-Balancing Cost Optimizer"):
                    excess_ratio = budget_limit / gross_base_cost
                    
                    df_items_to_update = db.query("SELECT id, unit_rate FROM tender_boq_items WHERE tender_id = ?", (select_tender_id,))
                    for row in df_items_to_update:
                        db.execute("""
                            UPDATE tender_boq_items 
                            SET unit_rate = ?, last_modified_by = ?
                            WHERE id = ?
                        """, (float(row['unit_rate']) * excess_ratio, current_user, int(row['id'])))
                        
                    st.success("Optimization algorithms applied. Financial rates adjusted to fit the budget cap.")
                    st.rerun()
                    
        with col_s3:
            if t_meta.get('workflow_status') == 'Draft' and st.button("📤 Submit Workspace to Review Pipeline"):
                db.execute("""
                    UPDATE tenders_boq_meta 
                    SET workflow_status = 'Pending Approval'
                    WHERE tender_id = ?
                """, (select_tender_id,))
                st.success("Tender forwarded to management approval cycle.")
                st.rerun()

    # Executive Signature Interface Controls
    if t_meta.get('workflow_status') == 'Pending Approval':
        st.markdown("---")
        st.subheader("🛡️ Executive Sign-Off Verification Matrix")
        if current_role not in ["Admin", "Company Admin"]:
            st.info("🔒 Awaiting signature sign-off from an authorized administrative executive profile.")
        else:
            c_sig1, c_sig2 = st.columns(2)
            with c_sig1:
                if st.button("✅ Officially Approve & Lock Financial Schedule"):
                    db.execute("""
                        UPDATE tenders_boq_meta 
                        SET workflow_status = 'Approved', approved_by = ?
                        WHERE tender_id = ?
                    """, (current_user, select_tender_id))
                    st.success("Tender instance successfully locked and signed!")
                    st.rerun()

            with c_sig2:
                if st.button("❌ Deny & Reject Back to Sandbox Development"):
                    db.execute("""
                        UPDATE tenders_boq_meta 
                        SET workflow_status = 'Draft'
                        WHERE tender_id = ?
                    """, (select_tender_id,))
                    st.warning("Tender schedule returned to draft workspace.")
                    st.rerun()

    with st.expander("🕒 View Workspace Modification Audit Trail (History)"):
        df_l = db.query("""
            SELECT item_no AS 'Item No', item_code AS 'PWD Code', old_rate AS 'Old Rate', 
                   new_rate AS 'New Rate', modified_by AS 'User Account', modified_at AS 'Timestamp'
            FROM price_change_logs WHERE tender_id = ? ORDER BY modified_at DESC
        """, (select_tender_id,))

        if not df_l:
            st.caption("No historical modifications logged against this bid framework profile yet.")
        else:
            st.dataframe(pd.DataFrame(df_l), use_container_width=True, hide_index=True)


# ==========================================
# 📈 TAB 2: STRATEGIC PRICING ANALYTICS & OVERHEADS
# ==========================================
with tab2:
    st.subheader("⚙️ Global Overhead Adjustments & Financial Analytics")

    if not can_edit:
        st.warning("🔒 Modification Restricted: Overhead adjustment factors are locked during active evaluation states.")
    else:
        c_an1, c_an2 = st.columns(2)
        with c_an1:
            profit_margin = st.slider("Inject Planned Profit Margin Factor (%)", 0.0, 25.0, 10.0, step=0.5)
        with c_an2:
            vat_margin = st.slider("Inject Government Tax / VAT Factor (%)", 0.0, 15.0, 7.5, step=0.5)

        if st.button("⚡ Apply Global Overheads to Current Estimates"):
            multiplier = 1 + ((profit_margin + vat_margin) / 100)
            
            df_items_to_update = db.query("SELECT id, unit_rate FROM tender_boq_items WHERE tender_id = ?", (select_tender_id,))
            for row in df_items_to_update:
                db.execute("""
                    UPDATE tender_boq_items 
                    SET unit_rate = ?
                    WHERE id = ?
                """, (float(row['unit_rate']) * multiplier, int(row['id'])))
                
            st.success(f"Applied a combined {profit_margin + vat_margin}% markup adjustment factor globally.")
            st.rerun()

    st.markdown("---")
    st.markdown("#### 📊 Executive Cost Performance KPIs")

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Gross Projected Cost (BDT)", f"{gross_base_cost:,.2f}")
    kpi2.metric("Target Estimated Budget Cap", f"{budget_limit:,.2f}" if budget_limit > 0 else "Not Specified")
    kpi3.metric("Project Variance Gap Margin", f"{(budget_limit - gross_base_cost):,.2f}" if budget_limit > 0 else "N/A")

    if df_items:
        df_chart_data = []
        for item in df_items:
            df_chart_data.append({
                'Group Classification': item.get('group_name', 'Uncategorized'),
                'Evaluated Price (BDT)': item['quantity'] * item['unit_rate']
            })
        df_chart = pd.DataFrame(df_chart_data)
        if not df_chart.empty:
            st.bar_chart(df_chart, x="Group Classification", y="Evaluated Price (BDT)", use_container_width=True)


# ==========================================
# 🔮 TAB 3: COMPETITOR INTELLIGENCE MATRIX
# ==========================================
with tab3:
    st.subheader("🔮 Competitor Analysis & Predictive Evaluation Marketplace")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("#### ➕ Record Competitor Bid Data")
        with st.form("competitor_entry_form", clear_on_submit=True):
            c_name = st.text_input("Competitor / Joint Venture Name")
            c_amount = st.number_input("Total Submitted Bid Price (BDT)", min_value=1.0, format="%.2f")
            c_won = st.checkbox("Mark as Lowest Evaluated Responsive Bidder (L1)")

            if st.form_submit_button("Log Competitor Metrics"):
                if c_name and c_amount > 0:
                    if c_won:
                        db.execute("""
                            UPDATE competitor_bids 
                            SET is_winner = 0 
                            WHERE tender_id = ?
                        """, (select_tender_id,))
                    
                    db.execute("""
                        INSERT INTO competitor_bids (tender_id, competitor_name, total_bid_amount, is_winner)
                        VALUES (?, ?, ?, ?)
                    """, (select_tender_id, c_name, float(c_amount), 1 if c_won else 0))
                    st.rerun()

    with col_c2:
        st.markdown("#### 📉 Win-Loss Analytics Matrix")
        
        # Note: Ensure calculate_win_probability is defined/imported
        try:
            prob_pct, rank_desc = calculate_win_probability(select_tender_id, gross_base_cost)
            if prob_pct is not None:
                st.metric("Win Probability Engine Estimate", f"{prob_pct}%", delta=rank_desc)
            else:
                st.info("Log additional competitor prices to activate analytical win-probability modeling.")
        except NameError:
            st.warning("Win probability function not found. Please import `calculate_win_probability`.")

        df_cbids = db.query("""
            SELECT competitor_name AS 'Bidder Entity Name', total_bid_amount AS 'Total Amount Offered (BDT)'
            FROM competitor_bids WHERE tender_id = ? ORDER BY total_bid_amount ASC
        """, (select_tender_id,))

        if df_cbids:
            my_row = [{
                "Bidder Entity Name": "★ Your Company (TenderAI Dynamic)",
                "Total Amount Offered (BDT)": gross_base_cost
            }]
            comp_df = pd.DataFrame(df_cbids + my_row)
            comp_df = comp_df.sort_values(by="Total Amount Offered (BDT)")
            st.dataframe(comp_df, use_container_width=True, hide_index=True)


# ==========================================
# 🗄️ TAB 4: RELATIONAL CORPORATE ARCHIVE LEDGER
# ==========================================
with tab4:
    st.subheader("📚 Historical Enterprise System Records Ledger")

    df_archive = db.query("""
        SELECT tender_id AS 'Tender ID', ministry_or_agency AS 'Agency', selected_zone AS 'Zone Context', 
               workflow_status AS 'Status State', created_by AS 'Created By ID', approved_by AS 'Approved By ID', 
               created_at AS 'Timestamp'
        FROM tenders_boq_meta ORDER BY created_at DESC
    """)

    if df_archive:
        st.dataframe(pd.DataFrame(df_archive), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("📥 Export Finalized Production Packages")

    if df_archive:
        approved_lists = [row["Tender ID"] for row in df_archive if row["Status State"] == "Approved"]
    else:
        approved_lists = []

    if not approved_lists:
        st.warning("🔒 Exports are locked. Packages can only be downloaded after receiving executive Approved signatures.")
    else:
        sel_exp = st.selectbox("Select Target Signed Tender Package for Export", approved_lists)

        if st.button("Generate Final Production Packages"):
            df_exp_items = db.query("""
                SELECT item_no, group_name, item_code, description, unit, quantity, unit_rate
                FROM tender_boq_items WHERE tender_id = ?
            """, (sel_exp,))

            if df_exp_items:
                # Convert to DataFrame
                df_exp = pd.DataFrame(df_exp_items)
                df_exp['Total Price In Figures (BDT)'] = df_exp['quantity'] * df_exp['unit_rate']
                df_exp['Unit Price In Figures (BDT)'] = df_exp['unit_rate'].map(lambda x: f"{x:.3f}")
                df_exp['Unit Price In Words (BDT)'] = df_exp['unit_rate'].apply(number_to_bangladesh_taka_words)
                df_exp['Total Price In Figures (BDT)'] = df_exp['Total Price In Figures (BDT)'].map(lambda x: f"{x:.3f}")
                df_exp['Total Price In Words (BDT)'] = df_exp['Total Price In Figures (BDT)'].apply(number_to_bangladesh_taka_words)

                final_output = df_exp.rename(columns={
                    'item_no': 'Item no.', 'group_name': 'Group', 'item_code': 'Item Code (if any)',
                    'description': 'Description of Item', 'unit': 'Measurement Unit', 'quantity': 'Quantity'
                }).drop(columns=['unit_rate'])

                # Use in-memory buffer instead of writing to local disk
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    final_output.to_excel(writer, index=False)
                
                st.download_button(
                    "📥 Download Official Locked e-GP Excel Sheet",
                    data=output.getvalue(),
                    file_name=f"Finalized_eGP_BOQ_{sel_exp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )