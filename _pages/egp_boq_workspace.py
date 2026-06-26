import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import difflib
from database.unified_db_manager import UnifiedDatabaseManagerDatabaseManagerDatabaseManagerDatabaseManager

from modules.matching_engine import search_best_pwd_match
from utils.currency_transformer import number_to_bangladesh_taka_words
from utils.data_sanitizer import sanitize_text, sanitize_item_code

#db = st.session_state['db']

# 1. Platform Infrastructure Foundations
st.set_page_config(layout="wide", page_title="TenderAI Enterprise Workspace")

# 2. Extract Session Security Access Contexts From Existing App Ecosystems
current_user = st.session_state.get("username", None)
current_role = st.session_state.get("role", "User") 

if not st.session_state.get("authenticated", False) or current_user is None:
    st.error("🚨 Access Denied: Please log in through the main iTender Dashboard gateway first.")
    st.stop()

# Helper Lookups
def get_original_pwd_rate(pwd_code, zone):
    if not pwd_code or pwd_code == "N/A": return None
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT unit_rate FROM pwd_rates=? AND zone_name=?", (str(pwd_code).strip(), zone))
    res = cursor.fetchone()
    conn.close()
    return float(res) if res else None

st.title("🚀 TenderAI - Enterprise Bid Management & Estimation Suite")
st.markdown(f"**Operator Identity:** {current_user} | **Security Clearance Tier:** `{current_role}`")

# Discovery Loop
conn = sqlite3.connect(DB_PATH)
active_tenders = pd.read_sql_query("SELECT tender_id FROM tenders_boq_meta WHERE workflow_status != 'Approved'", conn)['tender_id'].tolist()
conn.close()

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
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR REPLACE INTO tenders_boq_meta (tender_id, ministry_or_agency, selected_zone, workflow_status, official_budget_cap, created_by) VALUES (?, ?, ?, 'Draft', ?, ?)",
                                   (new_tid, new_agency, new_zone, b_cap, current_user))
                    
                    df_in = pd.read_excel(new_file)
                    cursor.execute("DELETE FROM tender_boq_items WHERE tender_id = ?", (new_tid,))
                    
                    for _, row in df_in.iterrows():
                        c_code = row.get('Item Code (if any)')
                        c_desc = row.get('Description of Item')
                        c_qty = float(row.get('Quantity', 0))
                        
                        _, m_desc, m_unit, m_rate, _ = search_best_pwd_match(c_code, c_desc, zone=new_zone)
                        
                        cursor.execute('''
                            INSERT INTO tender_boq_items (tender_id, item_no, group_name, item_code, description, unit, quantity, unit_rate, last_modified_by)
                            VALUES (?,?,?,?,?,?,?,?,?)
                        ''', (new_tid, str(row.get('Item no.')), str(row.get('Group')), str(c_code), m_desc, m_unit, c_qty, m_rate, current_user))
                    conn.commit()
                    conn.close()
                    st.success(f"Tender Workspace #{new_tid} created successfully!")
                    st.rerun()
    st.stop()

# Load Active Workspace States
select_tender_id = st.selectbox("Select Target Active Pipeline Workspace to Review", active_tenders)

conn = sqlite3.connect(DB_PATH)
t_meta = pd.read_sql_query("SELECT workflow_status, selected_zone, ministry_or_agency, official_budget_cap FROM tenders_boq_meta WHERE tender_id = ?", conn, params=(select_tender_id,)).iloc
df_items = pd.read_sql_query("SELECT id, item_no, group_name, item_code, description, unit, quantity, unit_rate FROM tender_boq_items WHERE tender_id = ?", conn, params=(select_tender_id,))
conn.close()

# Evaluate Metrics Realtime Calculations
df_items['Total Price'] = df_items['quantity'] * df_items['unit_rate']
gross_base_cost = float(df_items['Total Price'].sum())
budget_limit = float(t_meta['official_budget_cap'])

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
    st.markdown(f"### 📍 Client: {t_meta['ministry_or_agency']} | Pipeline Status: **`{t_meta['workflow_status']}`**")
    
    # Core Budget Guard Real-Time Alert System
    if budget_limit > 0:
        budget_variance = budget_limit - gross_base_cost
        if budget_variance < 0:
            st.error(f"🚨 BUDGET VIOLATION CRITICAL WARNING: Current estimate (BDT {gross_base_cost:,.2f}) exceeds the official government budget cap (BDT {budget_limit:,.2f}) by BDT {abs(budget_variance):,.2f}! This proposal risks automatic disqualification on the e-GP platform.")
        else:
            st.success(f"✅ Budget Cap Guard Active: Offer is safe. Cushion margin remaining: BDT {budget_variance:,.2f}")

    can_edit = (current_role in ["Admin", "Company Admin", "Individual"]) and (t_meta['workflow_status'] != 'Approved')
    
    edited_grid = st.data_editor(
        df_items,
        hide_index=True,
        disabled=['id', 'item_no', 'group_name', 'item_code', 'description', 'unit', 'quantity'] if not can_edit else ['id', 'item_no', 'group_name', 'item_code', 'description', 'unit', 'quantity'],
        use_container_width=True,
        key=f"live_editor_{select_tender_id}"
    )
    
    if can_edit:
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            if st.button("💾 Commit Adjustments & Log Changes"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                logs_count = 0
                for _, r in edited_grid.iterrows():
                    item_db_id = int(r['id'])
                    new_rate = float(r['unit_rate'])
                    cursor.execute("SELECT unit_rate, item_code, item_no FROM tender_boq_items WHERE id = ?", (item_db_id,))
                    db_rec = cursor.fetchone()
                    if db_rec and db_rec != new_rate:
                        cursor.execute("UPDATE tender_boq_items SET unit_rate = ?, last_modified_by = ? WHERE id = ?", (new_rate, current_user, item_db_id))
                        cursor.execute("INSERT INTO price_change_logs (tender_id, item_code, item_no, old_rate, new_rate, modified_by) VALUES (?,?,?,?,?,?)",
                                       (select_tender_id, db_rec, db_rec, db_rec, new_rate, current_user))
                        logs_count += 1
                conn.commit()
                conn.close()
                st.toast(f"Changes saved successfully! Logged {logs_count} modifications.", icon="✅")
                st.rerun()
                
        with col_s2:
            # AUTO-BALANCING ALGORITHM LAYER
            if budget_limit > 0 and gross_base_cost > budget_limit:
                if st.button("⚖️ Run Auto-Balancing Cost Optimizer"):
                    excess_ratio = budget_limit / gross_base_cost
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    # Scale down rates safely by the exact deficit percentage to perfectly meet the budget target
                    cursor.execute("UPDATE tender_boq_items SET unit_rate = unit_rate * ?, last_modified_by = ? WHERE tender_id = ?", (excess_ratio, current_user, select_tender_id))
                    conn.commit()
                    conn.close()
                    st.success("Optimization algorithms applied. Financial rates adjusted to fit the budget cap.")
                    st.rerun()
                    
        with col_s3:
            if t_meta['workflow_status'] == 'Draft' and st.button("📤 Submit Workspace to Review Pipeline"):
                conn = sqlite3.connect(DB_PATH)
                conn.cursor().execute("UPDATE tenders_boq_meta SET workflow_status = 'Pending Approval' WHERE tender_id = ?", (select_tender_id,))
                conn.commit()
                conn.close()
                st.success("Tender forwarded to management approval cycle.")
                st.rerun()

    # Executive Signature Interface Controls
    if t_meta['workflow_status'] == 'Pending Approval':
        st.markdown("---")
        st.subheader("🛡️ Executive Sign-Off Verification Matrix")
        if current_role not in ["Admin", "Company Admin"]:
            st.info("🔒 Awaiting signature sign-off from an authorized administrative executive profile.")
        else:
            c_sig1, c_sig2 = st.columns(2)
            with c_sig1:
                if st.button("✅ Officially Approve & Lock Financial Schedule"):
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

st.success("Tender instance successfully locked and signed!")
st.rerun()

with c_sig2:
    if st.button("❌ Deny & Reject Back to Sandbox Development"):
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

        st.warning("Tender schedule returned to draft workspace.")
        st.rerun()

with st.expander("🕒 View Workspace Modification Audit Trail (History)"):
    conn = sqlite3.connect(DB_PATH)

    df_l = pd.read_sql_query(
        """
        SELECT
            item_no AS 'Item No',
            item_code AS 'PWD Code',
            old_rate AS 'Old Rate',
            new_rate AS 'New Rate',
            modified_by AS 'User Account',
            modified_at AS 'Timestamp'
        FROM price_change_logs
        WHERE tender_id = ?
        ORDER BY modified_at DESC
        """,
        conn,
        params=(select_tender_id,)
    )

    conn.close()

    if df_l.empty:
        st.caption(
            "No historical modifications logged against this bid framework profile yet."
        )
    else:
        st.dataframe(
            df_l,
            use_container_width=True,
            hide_index=True
        )


# ==========================================
# 📈 TAB 2: STRATEGIC PRICING ANALYTICS & OVERHEADS
# ==========================================

with tab2:
    st.subheader("⚙️ Global Overhead Adjustments & Financial Analytics")

    if not can_edit:
        st.warning(
            "🔒 Modification Restricted: Overhead adjustment factors are locked during active evaluation states."
        )
    else:
        c_an1, c_an2 = st.columns(2)

        with c_an1:
            profit_margin = st.slider(
                "Inject Planned Profit Margin Factor (%)",
                0.0,
                25.0,
                10.0,
                step=0.5
            )

        with c_an2:
            vat_margin = st.slider(
                "Inject Government Tax / VAT Factor (%)",
                0.0,
                15.0,
                7.5,
                step=0.5
            )

        if st.button("⚡ Apply Global Overheads to Current Estimates"):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            multiplier = 1 + ((profit_margin + vat_margin) / 100)

            cursor.execute(
                """
                UPDATE tender_boq_items
                SET unit_rate = unit_rate * ?
                WHERE tender_id = ?
                """,
                (multiplier, select_tender_id)
            )

            conn.commit()
            conn.close()

            st.success(
                f"Applied a combined {profit_margin + vat_margin}% markup adjustment factor globally."
            )

            st.rerun()

    st.markdown("---")
    st.markdown("#### 📊 Executive Cost Performance KPIs")

    kpi1, kpi2, kpi3 = st.columns(3)

    kpi1.metric(
        "Gross Projected Cost (BDT)",
        f"{gross_base_cost:,.2f}"
    )

    kpi2.metric(
        "Target Estimated Budget Cap",
        f"{budget_limit:,.2f}"
        if budget_limit > 0
        else "Not Specified"
    )

    kpi3.metric(
        "Project Variance Gap Margin",
        f"{(budget_limit - gross_base_cost):,.2f}"
        if budget_limit > 0
        else "N/A"
    )

    if not df_items.empty:
        df_chart = df_items.rename(
            columns={
                "group_name": "Group Classification",
                "Total Price": "Evaluated Price (BDT)"
            }
        )

        st.bar_chart(
            df_chart,
            x="Group Classification",
            y="Evaluated Price (BDT)",
            use_container_width=True
        )


# ==========================================
# 🔮 TAB 3: COMPETITOR INTELLIGENCE MATRIX
# ==========================================

with tab3:
    st.subheader(
        "🔮 Competitor Analysis & Predictive Evaluation Marketplace"
    )

    col_c1, col_c2 = st.columns(2)

    with col_c1:
        st.markdown("#### ➕ Record Competitor Bid Data")

        with st.form(
            "competitor_entry_form",
            clear_on_submit=True
        ):
            c_name = st.text_input(
                "Competitor / Joint Venture Name"
            )

            c_amount = st.number_input(
                "Total Submitted Bid Price (BDT)",
                min_value=1.0,
                format="%.2f"
            )

            c_won = st.checkbox(
                "Mark as Lowest Evaluated Responsive Bidder (L1)"
            )

            if st.form_submit_button(
                "Log Competitor Metrics"
            ):
                if c_name and c_amount > 0:
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
                            c_amount,
                            1 if c_won else 0
                        )
                    )

                    conn.commit()
                    conn.close()

                    st.rerun()

    with col_c2:
        st.markdown("#### 📉 Win-Loss Analytics Matrix")

        prob_pct, rank_desc = calculate_win_probability(
            select_tender_id,
            gross_base_cost
        )

        if prob_pct is not None:
            st.metric(
                "Win Probability Engine Estimate",
                f"{prob_pct}%",
                delta=rank_desc
            )
        else:
            st.info(
                "Log additional competitor prices to activate analytical win-probability modeling."
            )

        conn = sqlite3.connect(DB_PATH)

        df_cbids = pd.read_sql_query(
            """
            SELECT
                competitor_name AS 'Bidder Entity Name',
                total_bid_amount AS 'Total Amount Offered (BDT)'
            FROM competitor_bids
            WHERE tender_id = ?
            ORDER BY total_bid_amount ASC
            """,
            conn,
            params=(select_tender_id,)
        )

        conn.close()

        if not df_cbids.empty:
            my_row = pd.DataFrame([
                {
                    "Bidder Entity Name":
                        "★ Your Company (TenderAI Dynamic)",
                    "Total Amount Offered (BDT)":
                        gross_base_cost
                }
            ])

            comp_df = pd.concat(
                [df_cbids, my_row]
            ).sort_values(
                by="Total Amount Offered (BDT)"
            )

            st.dataframe(
                comp_df,
                use_container_width=True,
                hide_index=True
            )


# ==========================================
# 🗄️ TAB 4: RELATIONAL CORPORATE ARCHIVE LEDGER
# ==========================================

with tab4:
    st.subheader(
        "📚 Historical Enterprise System Records Ledger"
    )

    conn = sqlite3.connect(DB_PATH)

    df_archive = pd.read_sql_query(
        """
        SELECT
            tender_id AS 'Tender ID',
            ministry_or_agency AS 'Agency',
            selected_zone AS 'Zone Context',
            workflow_status AS 'Status State',
            created_by AS 'Created By ID',
            approved_by AS 'Approved By ID',
            created_at AS 'Timestamp'
        FROM tenders_boq_meta
        ORDER BY created_at DESC
        """,
        conn
    )

    conn.close()

    if not df_archive.empty:
        st.dataframe(
            df_archive,
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")
    st.subheader("📥 Export Finalized Production Packages")

    approved_lists = df_archive[
        df_archive["Status State"] == "Approved"
    ]["Tender ID"].tolist()

    if not approved_lists:
        st.warning(
            "🔒 Exports are locked. Packages can only be downloaded after receiving executive Approved signatures."
        )
    else:
        sel_exp = st.selectbox(
            "Select Target Signed Tender Package for Export",
            approved_lists
        )

        if st.button("Generate Final Production Packages"):
            conn = sqlite3.connect(DB_PATH)

            df_exp_items = pd.read_sql_query(
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

            df_exp_items[
                'Total Price In Figures (BDT)'
            ] = (
                df_exp_items['quantity']
                * df_exp_items['unit_rate']
            )

            df_exp_items[
                'Unit Price In Figures (BDT)'
            ] = (
                df_exp_items['unit_rate']
                .map(lambda x: f"{x:.3f}")
            )

            df_exp_items[
                'Unit Price In Words (BDT)'
            ] = (
                df_exp_items['unit_rate']
                .apply(number_to_bangladesh_taka_words)
            )

            df_exp_items[
                'Total Price In Words (BDT)'
            ] = (
                df_exp_items[
                    'Total Price In Figures (BDT)'
                ].apply(number_to_bangladesh_taka_words)
            )

            df_exp_items[
                'Total Price In Figures (BDT)'
            ] = (
                df_exp_items[
                    'Total Price In Figures (BDT)'
                ].map(lambda x: f"{x:.3f}")
            )

            final_output = (
                df_exp_items.rename(
                    columns={
                        'item_no': 'Item no.',
                        'group_name': 'Group',
                        'item_code': 'Item Code (if any)',
                        'description': 'Description of Item',
                        'unit': 'Measurement Unit',
                        'quantity': 'Quantity'
                    }
                )
                .drop(columns=['unit_rate'])
            )

            excel_filename = (
                f"Finalized_eGP_BOQ_{sel_exp}.xlsx"
            )

            final_output.to_excel(
                excel_filename,
                index=False
            )

            with open(excel_filename, "rb") as f:
                st.download_button(
                    "📥 Download Official Locked e-GP Excel Sheet",
                    f,
                    file_name=excel_filename
                )    