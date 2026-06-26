# modules/egp_boq_workspace.py
import streamlit as st
import pandas as pd
import sqlite3
import os
from modules.matching_engine import search_best_pwd_match
from utils.currency_transformer import number_to_bangladesh_taka_words
from database.competitor_db import calculate_win_probability
from database.unified_db_manager import UnifiedDatabaseManager
from utils.data_sanitizer import sanitize_text, sanitize_item_code

db = UnifiedDatabaseManager()
#db = st.session_state['db']
DB_PATH = db.db_path 
def render_boq_workspace():
    
    
    # 2. Extract Session Security parameters from your main router configuration layout
    current_user = st.session_state.get("username", "Unknown User")
    current_role = st.session_state.get("user_role", "user")
    
    st.markdown("""
    <div class="main-header">
        <h1>🏗️ e-GP BOQ Workspace</h1>
        <p>Relational Tender estimation suite and PWD automated cost tracking</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"**Operator Context:** {st.session_state.get('full_name', current_user)} | **Security Clearance Tier:** `{current_role.upper()}`")
    
    def get_original_pwd_rate(pwd_code, zone):
        if not pwd_code or pwd_code == "N/A": return None
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT unit_rate FROM pwd_rates WHERE pwd_code=? AND zone_name=?", (str(pwd_code).strip(), zone))
        res = cursor.fetchone()
        conn.close()
        return float(res) if res else None

    # Load active data matrices
    conn = sqlite3.connect(DB_PATH)
    active_tenders = pd.read_sql_query("SELECT tender_id FROM tenders_boq_meta WHERE workflow_status != 'Approved'", conn)['tender_id'].tolist()
    conn.close()
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Ingestion & Workspace", 
        "📈 Global Adjustments & Analytics", 
        "🔮 Competitor Intelligence Matrix",
        "🗄️ Relational Corporate Archive"
    ])
    
    # ==========================================
    # 🎯 TAB 1: INGESTION & WORKSPACE WORKBENCH
    # ==========================================
    with tab1:
        can_create = current_role in ['admin', 'system_admin', 'company_admin']
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
                            cursor.execute("INSERT OR REPLACE INTO tenders_boq_meta (tender_id, ministry_or_agency, selected_zone, workflow_status, official_budget_cap, created_by) VALUES (?, ?, ?, 'Draft', ?, ?)",
                                        (new_tid, new_agency, new_zone, b_cap, current_user))
                            
                            df_in = pd.read_excel(new_file)
                            cursor.execute("DELETE FROM tender_boq_items WHERE tender_id = ?", (new_tid,))
                            
                            for _, row in df_in.iterrows():
                                # 🧪 EXTRACT RAW VALUES FROM EXCEL CELLS
                                raw_code = row.get('Item Code (if any)')
                                raw_desc = row.get('Description of Item')
                                c_qty = float(row.get('Quantity', 0))
                                
                                # ✨ APPLY DATA SANITIZER PIPELINES INSTANTLY
                                c_code = sanitize_item_code(raw_code)
                                c_desc = sanitize_text(raw_desc) # Strips hidden tabs, symbols, list markers
                                
                                # 🧠 RUN MATCHING PROFILES OVER THE CLEAN SANITIZED TEXT Strings
                                _, m_desc, m_unit, m_rate, _ = search_best_pwd_match(c_code, c_desc, zone=new_zone)
                                
                                cursor.execute('''
                                    INSERT INTO tender_boq_items (tender_id, item_no, group_name, item_code, description, unit, quantity, unit_rate, last_modified_by)
                                    VALUES (?,?,?,?,?,?,?,?,?)
                                ''', (new_tid, str(row.get('Item no.')), str(row.get('Group')), c_code, m_desc, m_unit, c_qty, m_rate, current_user))
                            
                            conn.commit()
                            conn.close()
                            st.success(f"Workspace generated successfully for Tender #{new_tid}!")
                            st.rerun()
                # ==========================================
                # 📊 AUTOMATED PRE-FLIGHT ESTIMATE SUMMARY SHEET
                # ==========================================
                st.markdown("---")
                with st.expander("📊 Automated Estimate Summary Sheet (Pre-Flight Compliance Check)", expanded=True):
                    st.markdown("##### 🔍 Proposal Financial Health Check & Compliance Analytics")
                    
                    # Recalculate working parameters live
                    df_items['Total Price'] = df_items['quantity'] * df_items['unit_rate']
                    total_bid_cost = float(df_items['Total Price'].sum())
                    gov_budget = float(t_meta['official_budget_cap'])
                    
                    sum_col1, sum_col2 = st.columns([2, 1])
                    
                    with sum_col1:
                        st.write("**📂 Chapter-by-Chapter Price Concentration (Cost Pareto Distribution):**")
                        # Group lines by their Group/Chapter context to isolate major spending blocks
                        df_grouped = df_items.groupby('group_name')['Total Price'].sum().reset_index()
                        df_grouped['Percentage (%)'] = (df_grouped['Total Price'] / total_bid_cost * 100).round(2) if total_bid_cost > 0 else 0
                        df_grouped = df_grouped.sort_values(by='Total Price', ascending=False)
                        
                        # Format numeric prices to readable commas string formats (e.g., 1,25,000.00)
                        df_grouped_display = df_grouped.copy()
                        df_grouped_display['Total Price (BDT)'] = df_grouped_display['Total Price'].map(lambda x: f"{x:,.2f}")
                        df_grouped_display = df_grouped_display.drop(columns=['Total Price']).rename(columns={'group_name': 'Work Category / Group'})
                        
                        st.dataframe(df_grouped_display, use_container_width=True, hide_index=True)
                        
                    with sum_col2:
                        st.write("**🛡️ e-GP Regulatory Threshold Status:**")
                        if gov_budget <= 0:
                            st.info("💡 Official Government Budget Cap not specified for this tender. Input budget cap during initialization to unlock PPR compliance variance testing checks.")
                        else:
                            variance_amt = total_bid_cost - gov_budget
                            variance_pct = (variance_amt / gov_budget) * 100
                            
                            st.metric(
                                label="Overall Estimate Variance",
                                value=f"{variance_pct:+.2f}%",
                                delta=f"{variance_amt:+,.2f} BDT",
                                delta_color="inverse" if variance_pct > 0 else "normal"
                            )
                            
                            # PPR rule evaluation boundaries criteria checking logic
                            st.markdown("**Compliance Analysis:**")
                            if abs(variance_pct) > 10.0:
                                st.markdown(
                                    f"<div style='background-color:#ef444420; padding:10px; border-radius:5px; border:1px solid #ef4444; color:#b91c1c; font-size:0.9rem;'>"
                                    f"❌ <strong>CRITICAL REJECTION RISK:</strong> Your offer is <strong>{abs(variance_pct):.2f}%</strong> "
                                    f"{'above' if variance_pct > 0 else 'below'} the official government estimate limit. "
                                    f"Under PPR procurement law standard regulations, variances exceeding <strong>±10%</strong> "
                                    f"will cause automatic bid rejection during technical/financial evaluation. Use the <em>Auto-Balancing Optimizer</em> above to adjust."
                                    f"</div>", 
                                    unsafe_allow_html=True
                                )
                            else:
                                st.markdown(
                                    f"<div style='background-color:#22c55e20; padding:10px; border-radius:5px; border:1px solid #22c55e; color:#15803d; font-size:0.9rem;'> "
                                    f"✅ <strong>PROPOSAL COMPLIANT:</strong> Your overall estimate total falls safely within the mandatory "
                                    f"<strong>±10%</strong> official legislative margin threshold. Bid is securely optimized for financial submission approval paths."
                                    f"</div>",
                                    unsafe_allow_html=True
                                )
                                
                    # Simple text visualization chart of where your money goes inside this proposal profile
                    if not df_grouped.empty:
                        st.markdown("###### 📊 Cost Distribution Visualization Graph")
                        st.bar_chart(df_grouped, x='group_name', y='Total Price', use_container_width=True)
        if not active_tenders:
            st.info("No active pipeline workspace drafts available. Initialize a project using the creation tools above.")
            return


        st.markdown("---")
        select_tender_id = st.selectbox("Select Active Workspace Pipeline to Review", active_tenders)
        
        conn = sqlite3.connect(DB_PATH)
        t_meta = pd.read_sql_query("SELECT workflow_status, selected_zone, ministry_or_agency, official_budget_cap FROM tenders_boq_meta WHERE tender_id = ?", conn, params=(select_tender_id,)).iloc
        df_items = pd.read_sql_query("SELECT id, item_no, group_name, item_code, description, unit, quantity, unit_rate FROM tender_boq_items WHERE tender_id = ?", conn, params=(select_tender_id,))
        conn.close()
        
        df_items['Total Price'] = df_items['quantity'] * df_items['unit_rate']
        gross_base_cost = float(df_items['Total Price'].sum())
        budget_limit = float(t_meta['official_budget_cap'])

        if budget_limit > 0:
            variance = budget_limit - gross_base_cost
            if variance < 0:
                st.error(f"🚨 BUDGET VIOLATION CRITICAL WARNING: Proposed pricing matrix total (BDT {gross_base_cost:,.2f}) exceeds official procurement limit cap (BDT {budget_limit:,.2f}) by BDT {abs(variance):,.2f}!")
            else:
                st.success(f"✅ Estimate Within Limits. Remaining Margin Cushion: BDT {variance:,.2f}")

        # Review validation threshold variances
        validation_flags = []
        for _, r in df_items.iterrows():
            base_r = get_original_pwd_rate(r['item_code'], t_meta['selected_zone'])
            if base_r and abs(((r['unit_rate'] - base_r) / base_r) * 100) > 10.0:
                validation_flags.append({"Item No": r['item_no'], "Code": r['item_code'], "Current": r['unit_rate'], "PWD Base": base_r})
        
        if validation_flags:
            st.warning("⚠️ Variation Flag Warning: Rates on certain items deviate by more than ±10% from the baseline PWD reference indices.")
            st.dataframe(pd.DataFrame(validation_flags), use_container_width=True, hide_index=True)

        can_edit = current_role in ['admin', 'system_admin', 'company_admin'] and t_meta['workflow_status'] != 'Approved'
        
        edited_grid = st.data_editor(
            df_items,
            hide_index=True,
            disabled=['id', 'item_no', 'group_name', 'item_code', 'description', 'unit', 'quantity'] if not can_edit else ['id', 'item_no', 'group_name', 'item_code', 'description', 'unit', 'quantity'],
            use_container_width=True,
            key=f"grid_{select_tender_id}"
        )
        
        if can_edit:
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                if st.button("💾 Save Matrix Pricing Changes"):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    for _, r in edited_grid.iterrows():
                        cursor.execute("UPDATE tender_boq_items SET unit_rate = ?, last_modified_by = ? WHERE id = ?", (float(r['unit_rate']), current_user, int(r['id'])))
                    conn.commit()
                    conn.close()
                    st.toast("Internal sandbox changes saved successfully!", icon="✅")
                    st.rerun()
            with col_b2:
                if budget_limit > 0 and gross_base_cost > budget_limit:
                    if st.button("⚖️ Run Auto-Balancing Cost Optimizer"):
                        ratio = budget_limit / gross_base_cost
                        conn = sqlite3.connect(DB_PATH)
                        conn.cursor().execute("UPDATE tender_boq_items SET unit_rate = unit_rate * ? WHERE tender_id = ?", (ratio, select_tender_id))
                        conn.commit()
                        conn.close()
                        st.rerun()
            with col_b3:
                if t_meta['workflow_status'] == 'Draft' and st.button("📤 Escalate to Executive Review Cycle"):
                    conn = sqlite3.connect(DB_PATH)
                    conn.cursor().execute("UPDATE tenders_boq_meta SET workflow_status = 'Pending Approval' WHERE tender_id = ?", (select_tender_id,))
                    conn.commit()
                    conn.close()
                    st.rerun()

        # Render Signature Authentication Boards
        if t_meta['workflow_status'] == 'Pending Approval':
            st.markdown("---")
            if current_role not in ['admin', 'system_admin']:
                st.info("🔒 Awaiting secure sign-off authentication from an administrative manager or executive Approver.")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Sign, Approve & Lock Financial Schedule"):
                        conn = sqlite3.connect(DB_PATH)
                        conn.cursor().execute(
                            """
                            UPDATE tenders_boq_meta
                            SET workflow_status = 'Approved',
                                approved_by = ?
                            WHERE tender_id = ?
                            """,
                            (current_user, select_tender_id)
                        )

                        conn.commit()
                        conn.close()

                        st.rerun()

                        with c2:
                            if st.button("❌ Reject back to Draft Sandbox Working Space"):
                                conn = sqlite3.connect(DB_PATH)

                                conn.cursor().execute(
                                    """
                                    UPDATE tenders_boq_meta
                                    SET workflow_status = 'Draft'
                                    WHERE tender_id = ?
                                    """,
                                    (select_tender_id,)
                                )

                                conn.commit()
                                conn.close()

                                st.rerun()


    # ==========================================
    # 📈 TAB 2: OVERHEADS & ANALYTICS
    # ==========================================

    with tab2:
        st.subheader("⚙️ Global Scale Factor Injectors")

        if not can_edit:
            st.warning(
                "🔒 Overhead manipulation operations are restricted during active review evaluations."
            )
        else:
            col_m1, col_m2 = st.columns(2)

            p_margin = col_m1.slider(
                "Profit Margin markup factor (%)",
                0.0,
                25.0,
                10.0,
                step=0.5
            )

            v_margin = col_m2.slider(
                "Government VAT / Corporate Tax markup (%)",
                0.0,
                15.0,
                7.5,
                step=0.5
            )

            if st.button("⚡ Apply Global Markups"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()

                factor = 1 + ((p_margin + v_margin) / 100)

                cursor.execute(
                    """
                    UPDATE tender_boq_items
                    SET unit_rate = unit_rate * ?
                    WHERE tender_id = ?
                    """,
                    (factor, select_tender_id)
                )

                conn.commit()
                conn.close()

                st.rerun()

        st.markdown("---")

        k1, k2, k3 = st.columns(3)

        k1.metric(
            "Gross Projected Cost",
            f"BDT {gross_base_cost:,.2f}"
        )

        k2.metric(
            "Target Budget Cap Limit",
            f"BDT {budget_limit:,.2f}"
            if budget_limit > 0
            else "Unspecified"
        )

        k3.metric(
            "Project Variance Buffer",
            f"BDT {(budget_limit - gross_base_cost):,.2f}"
            if budget_limit > 0
            else "N/A"
        )


    # ==========================================
    # 🔮 TAB 3: COMPETITOR INTELLIGENCE MATRIX
    # ==========================================

    with tab3:
        st.subheader(
        "🔮 Market Intelligence & Predictive Analysis Engine"
        )

        col_cp1, col_cp2 = st.columns(2)

        with col_cp1:
            with st.form(
                "comp_form",
                clear_on_submit=True
            ):
                c_name = st.text_input(
                    "Competitor Company / Joint Venture Identity Name"
                )

                c_amt = st.number_input(
                    "Total Contract Value Offered (BDT)",
                    min_value=0.0
                )

                c_won = st.checkbox(
                    "Mark as Lowest Responsive L1 Candidate Winner"
                )

                if st.form_submit_button(
                    "Record Competitor Metrics"
                ):
                    if c_name and c_amt > 0:
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()

                        if c_won:
                            cursor.execute(
                                """
                                UPDATE competitor_bids
                                SET is_winner = 0
                                WHERE tender_id = ?
                                """,
                                (select_tender_id,)
                            )

                        cursor.execute(
                            """
                            INSERT INTO competitor_bids
                            (
                                tender_id,
                                competitor_name,
                                total_bid_amount,
                                is_winner
                            )
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                select_tender_id,
                                c_name,
                                c_amt,
                                1 if c_won else 0
                            )
                        )

                        conn.commit()
                        conn.close()

                        st.rerun()

        with col_cp2:
            pct, r_desc = calculate_win_probability(
                select_tender_id,
                gross_base_cost
            )

            if pct is not None:
                st.metric(
                    "Calculated Win Probability",
                    f"{pct}%",
                    delta=r_desc
                )

            conn = sqlite3.connect(DB_PATH)

            df_comps = pd.read_sql_query(
                """
                SELECT
                    competitor_name AS 'Bidder Name',
                    total_bid_amount AS 'Bid Amount (BDT)'
                FROM competitor_bids
                WHERE tender_id = ?
                ORDER BY total_bid_amount ASC
                """,
                conn,
                params=(select_tender_id,)
            )

            conn.close()

            if not df_comps.empty:
                my_co = pd.DataFrame(
                    [
                        {
                            "Bidder Name": "★ Your Company (TenderAI Live)",
                            "Bid Amount (BDT)": gross_base_cost
                        }
                    ]
                )

                st.dataframe(
                    pd.concat(
                        [df_comps, my_co]
                    ).sort_values(
                        by="Bid Amount (BDT)"
                    ),
                    use_container_width=True,
                    hide_index=True
                )


    # ==========================================
    # 🗄️ TAB 4: CORPORATE LEDGER EXPORT PANEL
    # ==========================================

    with tab4:
        st.subheader(
            "📚 Signed Enterprise Historical Archives Vault"
        )

        conn = sqlite3.connect(DB_PATH)

        df_arch = pd.read_sql_query(
            """
            SELECT
                tender_id AS 'Tender ID',
                ministry_or_agency AS 'Agency',
                selected_zone AS 'Zone Context',
                workflow_status AS 'Status'
            FROM tenders_boq_meta
            ORDER BY created_at DESC
            """,
            conn
        )

        conn.close()

        if df_arch.empty:
            st.info(
                "No recorded historical tender profiles stored inside the database repository archives."
            )
        else:
            st.dataframe(
                df_arch,
                use_container_width=True,
                hide_index=True
            )

        app_list = df_arch[
            df_arch["Status"] == "Approved"
        ]["Tender ID"].tolist()

        if not app_list:
            st.warning(
                "🔒 Package Export Lock: Generation operations remain restricted until a package receives an Approved executive signature."
            )
        else:
            sel_exp = st.selectbox(
                "Select Signed Tender Framework for Compilation",
                app_list
            )

            if st.button(
                "Compile Output Deliverable Workbook"
            ):
                conn = sqlite3.connect(DB_PATH)

                df_final = pd.read_sql_query(
                    """
                    SELECT
                        item_no,
                        group_name,
                        item_code,
                        description,
                        unit,
                        quantity,
                        unit_rate
                    FROM tender_boq_items
                    WHERE tender_id = ?
                    """,
                    conn,
                    params=(sel_exp,)
                )

                conn.close()

                df_final["Total Price In Figures (BDT)"] = (
                    df_final["quantity"]
                    * df_final["unit_rate"]
                )

                df_final["Unit Price In Figures (BDT)"] = (
                    df_final["unit_rate"]
                    .map(lambda x: f"{x:.3f}")
                )

                df_final["Unit Price In Words (BDT)"] = (
                    df_final["unit_rate"]
                    .apply(number_to_bangladesh_taka_words)
                )

                df_final["Total Price In Words (BDT)"] = (
                    df_final["Total Price In Figures (BDT)"]
                    .apply(number_to_bangladesh_taka_words)
                )

                df_final["Total Price In Figures (BDT)"] = (
                    df_final["Total Price In Figures (BDT)"]
                    .map(lambda x: f"{x:.3f}")
                )

                out = (
                    df_final.rename(
                        columns={
                            "item_no": "Item no.",
                            "group_name": "Group",
                            "item_code": "Item Code (if any)",
                            "description": "Description of Item",
                            "unit": "Measurement Unit",
                            "quantity": "Quantity",
                        }
                    )
                    .drop(columns=["unit_rate"])
                )

                fname = (
                    f"Finalized_eGP_BOQ_{sel_exp}.xlsx"
                )

                out.to_excel(
                    fname,
                    index=False
                )

                with open(fname, "rb") as f:
                    st.download_button(
                        "Download Official Locked e-GP Spreadsheet Package",
                        f,
                        file_name=fname
                    )