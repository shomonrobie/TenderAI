# modules/boq_generator_ui.py

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from modules.boq_generator import BOQGenerator

DB_PATH = "data/tender_system.db"


def check_rates_in_database(source, zone, edition_year):
    """Debug function to check rates in database"""
    
    conn = sqlite3.connect(DB_PATH)
    
    results = {
        'pwd_rates': pd.DataFrame(),
        'lged_rates': pd.DataFrame(),
        'versions': pd.DataFrame(),
        'selected_found': 0,
        'available_zones': [],
        'available_editions': []
    }
    
    # Check PWD rates
    pwd_check = pd.read_sql_query("""
        SELECT DISTINCT 
            r.zone_name, 
            r.edition_year,
            COUNT(*) as rate_count
        FROM pwd_rates r
        GROUP BY r.zone_name, r.edition_year
        ORDER BY r.edition_year DESC, r.zone_name
    """, conn)
    results['pwd_rates'] = pwd_check
    
    if not pwd_check.empty:
        results['available_zones'] = pwd_check['zone_name'].unique().tolist()
        results['available_editions'] = pwd_check['edition_year'].unique().tolist()
        
        # Check specific selection
        specific = pd.read_sql_query("""
            SELECT COUNT(*) as count
            FROM pwd_rates r
            WHERE r.zone_name = ? AND r.edition_year = ?
        """, conn, params=(zone, edition_year))
        results['selected_found'] = specific.iloc[0]['count'] if not specific.empty else 0
    
    # Check LGED rates
    lged_check = pd.read_sql_query("""
        SELECT DISTINCT 
            r.zone_name,
            COUNT(*) as rate_count
        FROM lged_zone_rates r
        GROUP BY r.zone_name
        ORDER BY r.zone_name
    """, conn)
    results['lged_rates'] = lged_check
    
    # Check versions
    versions = pd.read_sql_query("""
        SELECT source, edition_year, is_active, total_parents, total_children, total_rates
        FROM rate_versions
        ORDER BY source, edition_year DESC
    """, conn)
    results['versions'] = versions
    
    # Check children tables
    pwd_children = pd.read_sql_query("SELECT COUNT(*) as count FROM pwd_children", conn)
    lged_children = pd.read_sql_query("SELECT COUNT(*) as count FROM lged_children", conn)
    results['pwd_children_count'] = pwd_children.iloc[0]['count'] if not pwd_children.empty else 0
    results['lged_children_count'] = lged_children.iloc[0]['count'] if not lged_children.empty else 0
    
    conn.close()
    return results


def render_debug_panel(source, zone, edition_year):
    """Render debug information panel"""
    
    with st.expander("🔍 Debug: Check Database Rates", expanded=False):
        st.markdown("### Database Rate Information")
        
        conn = sqlite3.connect(DB_PATH)
        
        # Show available editions first
        st.markdown("**📅 Available Editions:**")
        if source == "PWD":
            editions = pd.read_sql_query("""
                SELECT DISTINCT edition_year, COUNT(*) as rate_count
                FROM pwd_rates
                GROUP BY edition_year
                ORDER BY edition_year DESC
            """, conn)
        else:
            editions = pd.read_sql_query("""
                SELECT DISTINCT edition_year, COUNT(*) as rate_count
                FROM lged_children
                GROUP BY edition_year
                ORDER BY edition_year DESC
            """, conn)
        
        if not editions.empty:
            st.dataframe(editions, use_container_width=True)
            st.info(f"Select from available editions: {editions['edition_year'].tolist()}")
        else:
            st.warning("No editions found. Please import rate data first.")
        
        # Show rates for selected criteria
        st.markdown(f"**🎯 Selected: {source} | Zone={zone} | Edition={edition_year}**")
        
        if source == "PWD":
            rates = pd.read_sql_query("""
                SELECT COUNT(*) as count
                FROM pwd_rates r
                WHERE r.zone_name = ? AND r.edition_year = ?
            """, conn, params=(zone, edition_year))
        else:
            rates = pd.read_sql_query("""
                SELECT COUNT(*) as count
                FROM lged_zone_rates r
                WHERE r.zone_name = ?
            """, conn, params=(zone,))
        
        count = rates.iloc[0]['count'] if not rates.empty else 0
        st.write(f"**Rates found:** {count}")
        
        if count == 0:
            st.warning(f"No rates for {zone} {edition_year}")
            
            # Show what's available
            if source == "PWD":
                available = pd.read_sql_query("""
                    SELECT DISTINCT zone_name, edition_year, COUNT(*) as count
                    FROM pwd_rates
                    GROUP BY zone_name, edition_year
                    ORDER BY edition_year DESC, zone_name
                """, conn)
            else:
                available = pd.read_sql_query("""
                    SELECT DISTINCT zone_name, COUNT(*) as count
                    FROM lged_zone_rates
                    GROUP BY zone_name
                    ORDER BY zone_name
                """, conn)
            
            if not available.empty:
                st.markdown("**📊 Available rate combinations:**")
                st.dataframe(available, use_container_width=True)
        
        conn.close()
        
        # Recommendations
        st.markdown("---")
        st.markdown("**💡 Recommendations:**")
        
        if count == 0:
            st.warning(f"No rates for {zone} {edition_year}. Try:")
            st.write("- Select a different edition year from the dropdown above")
            st.write("- Or import rates for this zone/edition in Rate Management")

def get_tenders_for_user(is_admin, username):
    """Get tenders based on user role"""
    conn = sqlite3.connect(DB_PATH)
    
    if is_admin:
        tenders_df = pd.read_sql_query("""
            SELECT tender_id, ministry_or_agency, selected_zone, workflow_status, 
                   official_budget_cap, created_by, created_at
            FROM tenders_boq_meta
            ORDER BY created_at DESC
        """, conn)
    else:
        tenders_df = pd.read_sql_query("""
            SELECT tender_id, ministry_or_agency, selected_zone, workflow_status, 
                   official_budget_cap, created_by, created_at
            FROM tenders_boq_meta
            WHERE created_by = ? OR tender_id IN (
                SELECT tender_id FROM tender_boq_items WHERE last_modified_by = ?
            )
            ORDER BY created_at DESC
        """, conn, params=(username, username))
    
    conn.close()
    return tenders_df


def create_test_tender(username):
    """Create a test tender for admin"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    test_tender_id = f"TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    cursor.execute("""
        INSERT OR REPLACE INTO tenders_boq_meta 
        (tender_id, ministry_or_agency, selected_zone, workflow_status, official_budget_cap, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (test_tender_id, "Test Agency", "Dhaka", "Draft", 10000000, username))
    conn.commit()
    conn.close()
    return test_tender_id


def render_boq_generator():
    """BOQ Generator UI with Tender ID selection"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📄 BOQ Generator</h1>
        <p>Generate BOQ for specific tender and match rates from PWD/LGED database</p>
    </div>
    """, unsafe_allow_html=True)
    
    user_id = st.session_state.get('user_id')
    company_id = st.session_state.get('company_id')
    user_role = st.session_state.get('user_role', 'viewer')
    username = st.session_state.get('username', '')
    
    is_admin = user_role in ['admin', 'system_admin']
    
    if user_role == 'viewer':
        st.error("❌ You don't have permission to generate BOQ.")
        return
    
    # Check BOQ quota
    boq_gen = BOQGenerator()
    remaining, message, plan = boq_gen.get_remaining_boq_count(user_id, company_id)
    
    if remaining == 0 and not is_admin:
        st.error(f"❌ {message}")
        if st.button("Upgrade Subscription"):
            st.session_state.page = "subscription"
            st.rerun()
        return
    
    # Show quota
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"📊 Plan: **{plan.upper()}**")
    with col2:
        if remaining == -1 or is_admin:
            st.success("🎉 Unlimited BOQ generations")
        else:
            st.info(f"📊 {message}")
    
    st.markdown("---")
    
    # Tender Selection
    st.markdown("### 🎯 Select Tender")
    
    tenders_df = get_tenders_for_user(is_admin, username)
    
    if tenders_df.empty:
        st.warning("No tenders found. Please create a tender first in e-GP BOQ Workspace.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏗️ Go to e-GP BOQ Workspace", use_container_width=True):
                st.session_state.page = "egp_boq_workspace"
                st.rerun()
        with col2:
            if is_admin:
                if st.button("📝 Create Test Tender", use_container_width=True):
                    test_id = create_test_tender(username)
                    st.success(f"✅ Created test tender: {test_id}")
                    st.rerun()
        return
    
    # Tender selection
    if is_admin:
        tenders_df['display'] = tenders_df.apply(
            lambda x: f"{x['tender_id']} - {x['ministry_or_agency']} ({x['selected_zone']}) - By: {x['created_by']}", 
            axis=1
        )
        selected_display = st.selectbox("Select Tender", tenders_df['display'].tolist())
        selected_tender = selected_display.split(" - ")[0] if selected_display else None
    else:
        selected_tender = st.selectbox(
            "Select Tender",
            options=tenders_df['tender_id'].tolist(),
            format_func=lambda x: f"{x} - {tenders_df[tenders_df['tender_id']==x]['ministry_or_agency'].iloc[0]}"
        )
    
    if selected_tender:
        tender_info = tenders_df[tenders_df['tender_id'] == selected_tender].iloc[0]
        st.info(f"📌 Tender: {selected_tender} | Agency: {tender_info['ministry_or_agency']} | Zone: {tender_info['selected_zone']} | Status: {tender_info['workflow_status']}")
        
        if tender_info['official_budget_cap'] > 0:
            st.info(f"💰 Official Budget Cap: BDT {tender_info['official_budget_cap']:,.2f}")
    
    st.markdown("---")
    st.markdown("### ⚙️ Rate Configuration")

    col1, col2, col3 = st.columns(3)

    with col1:
        source = st.selectbox("Rate Source", ["PWD", "LGED"])

    with col2:
        # Get available editions for selected source
        conn = sqlite3.connect(DB_PATH)
        if source == "PWD":
            editions_df = pd.read_sql_query("""
                SELECT DISTINCT edition_year 
                FROM pwd_rates 
                ORDER BY edition_year DESC
            """, conn)
        else:
            editions_df = pd.read_sql_query("""
                SELECT DISTINCT edition_year 
                FROM lged_children 
                ORDER BY edition_year DESC
            """, conn)
        conn.close()
        
        edition_options = editions_df['edition_year'].tolist() if not editions_df.empty else [2022]
        
        edition_year = st.selectbox(
            "Edition Year", 
            options=edition_options,
            index=0,
            help="Select the rate schedule edition year"
        )

    with col3:
        # Get available zones for selected source and edition
        conn = sqlite3.connect(DB_PATH)
        if source == "PWD":
            zones_df = pd.read_sql_query("""
                SELECT DISTINCT zone_name 
                FROM pwd_rates 
                WHERE edition_year = ?
                ORDER BY zone_name
            """, conn, params=(edition_year,))
        else:
            zones_df = pd.read_sql_query("""
                SELECT DISTINCT zone_name 
                FROM lged_zone_rates 
                ORDER BY zone_name
            """, conn)
        conn.close()
        
        zone_options = zones_df['zone_name'].tolist() if not zones_df.empty else (
            ["Dhaka", "Chattogram", "Khulna", "Rajshahi"] if source == "PWD" 
            else ["Zone-A", "Zone-B", "Zone-C", "Zone-D"]
        )
        
        zone = st.selectbox("Zone", zone_options)

    
    # Debug toggle
    show_debug = st.checkbox("🔍 Show Debug Info", value=False)
    
    st.markdown("---")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload BOQ Excel File",
        type=["xlsx", "xls"],
        help="Upload your e-GP BOQ template with columns: Item Code (if any), Description of Item, Quantity"
    )
    
    if uploaded_file and selected_tender:
        try:
            df_boq = pd.read_excel(uploaded_file)
            # Remove completely empty rows
            original_count = len(df_boq)

            # Filter out empty rows
            df_boq = df_boq.dropna(how='all')
            df_boq = df_boq[df_boq['Description of Item'].notna()]
            df_boq = df_boq[df_boq['Description of Item'].astype(str).str.strip() != '']
            df_boq = df_boq[df_boq['Quantity'] > 0]
            df_boq = df_boq.reset_index(drop=True)

            filtered_count = len(df_boq)

            if original_count > filtered_count:
                st.info(f"📊 Filtered out {original_count - filtered_count} empty/invalid rows. Processing {filtered_count} valid items.")


            st.markdown("#### Uploaded File Preview")
            st.dataframe(df_boq.head(10), use_container_width=True, hide_index=True)
            
            # Show column mapping
            expected_cols = ['Item Code (if any)', 'Description of Item', 'Quantity']
            missing_cols = [col for col in expected_cols if col not in df_boq.columns]
            
            if missing_cols:
                st.warning(f"Missing columns: {missing_cols}")
                st.info("Please ensure your file has these columns.")
            
            # Show debug panel if enabled
            if show_debug:
                render_debug_panel(source, zone, edition_year)
            
            if st.button("🚀 Generate BOQ", type="primary", use_container_width=True):
                with st.spinner("Matching rates from database..."):
                    rates_df = boq_gen.get_rates_from_database(source, zone, edition_year)
                    
                    if rates_df.empty:
                        st.error(f"No rates found for {source} {zone} {edition_year}.")
                        if show_debug:
                            st.info("Debug info above shows what rates are available.")
                        else:
                            st.info("Enable 'Show Debug Info' to see what rates exist in database.")
                        st.info("Go to Rate Management tab to import PWD/LGED rates.")
                        return
                    
                    matched_items, unmatched_items = boq_gen.match_boq_items(df_boq, rates_df)
                    
                    # Calculate total cost
                    total_cost = sum(item['Total Price'] for item in matched_items)
                    
                    # Display results
                    st.markdown("### 📊 Matching Results")
                    
                    col_a, col_b, col_c = st.columns(3)
                    total_items = len(matched_items) + len(unmatched_items)
                    match_rate = (len(matched_items) / total_items * 100) if total_items > 0 else 0
                    
                    col_a.metric("Total Items", total_items)
                    col_b.metric("Matched Items", len(matched_items), delta=f"{match_rate:.0f}%")
                    col_c.metric("Total Estimated Cost", f"BDT {total_cost:,.2f}")
                    
                    if matched_items:
                        with st.expander(f"✅ Matched Items ({len(matched_items)})", expanded=True):
                            # Keep Match Status in UI display for debugging
                            display_df = pd.DataFrame(matched_items)
                            st.dataframe(display_df, use_container_width=True, hide_index=True)

                    
                    if unmatched_items:
                        with st.expander(f"⚠️ Unmatched Items ({len(unmatched_items)})", expanded=True):
                            st.dataframe(pd.DataFrame(unmatched_items), use_container_width=True, hide_index=True)
                            st.warning("These items were not found in the database.")
                    
                    # Generate and record
                    output, total_cost = boq_gen.generate_boq_excel(
                        matched_items, unmatched_items, source, zone, edition_year, selected_tender
                    )
                    
                    history_id = boq_gen.record_boq_generation(
                        user_id, company_id, selected_tender, 
                        tender_info.get('ministry_or_agency', ''), 
                        tender_info.get('ministry_or_agency', ''),
                        uploaded_file.name, total_items, total_cost, zone, source, edition_year
                    )
                    
                    st.success(f"✅ BOQ generated successfully! Record ID: {history_id}")
                    
                    # Download button
                    st.download_button(
                        "📥 Download BOQ Excel",
                        output,
                        f"BOQ_{selected_tender}_{source}_{zone}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
                    st.balloons()
                    
                    # Bid submission option
                    st.markdown("---")
                    st.markdown("### 📤 Submit Bid")
                    
                    bid_amount = st.number_input("Final Bid Amount (BDT)", value=float(total_cost), step=1000.0)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📤 Record Bid Submission", type="primary", use_container_width=True):
                            boq_gen.record_bid_submission(history_id, selected_tender, company_id, bid_amount, username)
                            st.success("✅ Bid submission recorded successfully!")
                    
                    with col2:
                        if st.button("📊 View Bid Analysis", use_container_width=True):
                            st.session_state.page = "boq_admin_report"
                            st.rerun()
                    
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.info("Required columns: 'Item Code (if any)', 'Description of Item', 'Quantity'")

def get_available_editions(source):
    """Get available edition years for selected source"""
    conn = sqlite3.connect(DB_PATH)
    
    if source == "PWD":
        editions = pd.read_sql_query("""
            SELECT DISTINCT edition_year 
            FROM pwd_rates 
            ORDER BY edition_year DESC
        """, conn)
    else:
        # For LGED, check lged_children table
        editions = pd.read_sql_query("""
            SELECT DISTINCT edition_year 
            FROM lged_children 
            ORDER BY edition_year DESC
        """, conn)
    
    conn.close()
    
    if not editions.empty:
        return editions['edition_year'].tolist()
    return [2022]  # Default fallback


def get_available_zones(source, edition_year):
    """Get available zones for selected source and edition"""
    conn = sqlite3.connect(DB_PATH)
    
    if source == "PWD":
        zones = pd.read_sql_query("""
            SELECT DISTINCT zone_name 
            FROM pwd_rates 
            WHERE edition_year = ?
            ORDER BY zone_name
        """, conn, params=(edition_year,))
    else:
        zones = pd.read_sql_query("""
            SELECT DISTINCT zone_name 
            FROM lged_zone_rates 
            ORDER BY zone_name
        """, conn)
    
    conn.close()
    
    if not zones.empty:
        return zones['zone_name'].tolist()
    
    # Default zones based on source
    if source == "PWD":
        return ["Dhaka", "Chattogram", "Khulna", "Rajshahi"]
    else:
        return ["Zone-A", "Zone-B", "Zone-C", "Zone-D"]
