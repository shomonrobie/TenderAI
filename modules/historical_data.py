"""
Historical Data Management for NPPI Calculation
PPR 2025 Compliant - Clause 49.4 - 49.5
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from database.unified_db_manager import UnifiedDatabaseManager
from utils.helpers import (
    render_page_header,
    format_currency_bd,
    format_percentage,
    get_compact_css,
    navigate_to
)

db = UnifiedDatabaseManager()

def render_historical_data_page():
    """Render historical data management page for admin/premium users"""
    
    st.markdown(get_compact_css(), unsafe_allow_html=True)
    
    # Use the centralized page header
    render_page_header(
        "📚 Historical Tender Data Management", 
        "Manage past tender results for accurate NPPI calculation (PPR 2025 Clause 49.4-49.5)",
        icon="📚"
    )

    # Check if user has permission (Admin, Professional, Enterprise)
    subscription = db.get_user_subscription(st.session_state.user_id)
    is_premium = subscription.get('plan') in ['professional', 'enterprise'] or st.session_state.user_role == 'admin'
    
    if not is_premium:
        st.warning("⚠️ Historical data management is available for Professional and Enterprise plans only.")
        st.info("Upgrade to Professional to access historical data tracking and company-specific NPPI calculation.")
        
        if st.button("View Upgrade Plans"):
            st.session_state.page = "subscription"
            st.rerun()
        return
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Add Historical Tender", 
        "📊 View Historical Data", 
        "📈 NPPI Analytics",
        "📥 Import/Export"
    ])
    
    with tab1:
        render_add_historical_form()
    
    with tab2:
        render_view_historical_data()
    
    with tab3:
        render_nppi_analytics()
    
    with tab4:
        render_import_export()

def render_add_historical_form():
    """Form to add historical tender data with participant-based winner selection"""
    
    st.markdown("### Add Past Tender Result")
    st.caption("Enter details of completed tenders to improve ML predictions and competitor tracking")
    
    # Get competitor master list
    competitors = db.get_competitor_master_list(st.session_state.company_id)
    
    if not competitors:
        st.warning("⚠️ No competitors in master list. Please add competitors first.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Go to Competitor Master", use_container_width=True):
                st.session_state.page = "competitor_master"
                st.rerun()
        with col2:
            if st.button("📝 Continue Without Competitors", use_container_width=True):
                st.session_state.skip_competitors = True
                st.rerun()
        return
    
    with st.form("add_historical_tender"):
        # Basic Information Section
        st.markdown("#### 📋 Basic Tender Information")
        col1, col2 = st.columns(2)
        
        with col1:
            tender_id = st.text_input("Tender ID/Reference Number*", placeholder="e.g., TND-2024-001")
            tender_title = st.text_input("Tender Title*", placeholder="e.g., Road Construction Project")
            procuring_entity = st.text_input("Procuring Entity*", placeholder="e.g., PWD, LGED, RHD")
            procurement_type = st.selectbox("Procurement Type*", ["goods", "works", "services"])
        
        with col2:
            official_estimate = st.number_input("Official Estimate (BDT)*", min_value=0, step=1000000, format="%d", value=5000000)
            award_date = st.date_input("Award Date", value=datetime.now() - timedelta(days=30))
        
        # Participants Section
        st.markdown("---")
        st.markdown("### 👥 All Participants")
        st.caption("Add all participants including our company (if we participated)")
        
        # Option to include our company
        include_our_company = st.checkbox("Our company participated in this tender", value=True)
        
        # Build participant list
        participants = []
        
        # Add our company if selected
        if include_our_company:
            st.markdown("#### Our Company")
            col1, col2 = st.columns(2)
            with col1:
                our_bid = st.number_input("Our Bid Price (BDT)", min_value=0, step=1000000, format="%d", 
                                         value=int(official_estimate * 0.92))
            with col2:
                our_rank_placeholder = st.empty()
            
            participants.append({
                'name': "Our Company",
                'type': 'our_company',
                'bid': our_bid,
                'bid_ratio': our_bid / official_estimate if official_estimate > 0 else 0.92
            })
        
        # Add competitors
        st.markdown("#### Competitors")
        num_competitors = st.number_input("Number of competitors", min_value=1, max_value=20, value=3)
        
        for i in range(num_competitors):
            with st.container():
                st.markdown(f"**Competitor {i+1}**")
                col_a, col_b, col_c = st.columns([3, 2.5, 1])
                
                with col_a:
                    competitor_options = {c[1]: c[0] for c in competitors}
                    selected_name = st.selectbox(
                        f"Select Competitor",
                        options=["-- Select Competitor --"] + list(competitor_options.keys()),
                        key=f"comp_select_{i}",
                        label_visibility="collapsed"
                    )
                
                with col_b:
                    comp_bid = st.number_input(
                        f"Bid Amount (BDT)", 
                        key=f"comp_bid_{i}", 
                        min_value=0, 
                        step=1000000, 
                        format="%d",
                        label_visibility="collapsed",
                        placeholder="Enter bid amount",
                        value=int(official_estimate * 0.90) if official_estimate > 0 else 0
                    )
                
                with col_c:
                    if selected_name and selected_name != "-- Select Competitor --" and official_estimate > 0 and comp_bid > 0:
                        bid_ratio = comp_bid / official_estimate
                        if bid_ratio < 0.88:
                            st.markdown("🟢 Aggressive")
                        elif bid_ratio < 0.93:
                            st.markdown("🟡 Moderate")
                        else:
                            st.markdown("🔴 Conservative")
                
                if selected_name and selected_name != "-- Select Competitor --" and comp_bid > 0:
                    comp_id = competitor_options[selected_name]
                    participants.append({
                        'name': selected_name,
                        'competitor_id': comp_id,
                        'bid': comp_bid,
                        'type': 'competitor',
                        'bid_ratio': comp_bid / official_estimate if official_estimate > 0 else 0.90
                    })
                
                st.markdown("---")
        
        # Winner Selection - ONLY from participants
        st.markdown("---")
        st.markdown("#### 🏆 Winner Selection")
        st.caption("Select who won this tender from the participants above")
        
        # Create list of participant names for selection
        participant_names = [p['name'] for p in participants]
        
        if not participant_names:
            st.warning("Please add at least one participant first")
        else:
            winner_name = st.selectbox(
                "Select the winning participant*",
                options=participant_names,
                help="Select from the participants listed above"
            )
            
            # Find the winner's bid
            winner_data = next((p for p in participants if p['name'] == winner_name), None)
            if winner_data:
                winning_price = winner_data['bid']
                st.info(f"💰 Winning bid amount: BDT {winning_price:,.0f} ({winning_price/official_estimate*100:.1f}% of estimate)")
                
                # Mark winner in participants list
                for p in participants:
                    p['was_winner'] = (p['name'] == winner_name)
        
        # Show participant summary
        if participants:
            st.markdown("#### 📊 Participant Summary")
            summary_df = pd.DataFrame(participants)
            summary_df['Bid Amount'] = summary_df['bid'].apply(lambda x: f"BDT {x:,.0f}")
            summary_df['% of Estimate'] = summary_df['bid_ratio'].apply(lambda x: f"{x*100:.1f}%")
            summary_df['Winner'] = summary_df.apply(lambda x: "🏆 YES" if x.get('was_winner') else "❌", axis=1)
            
            # Determine our rank if we participated
            our_participant = next((p for p in participants if p['type'] == 'our_company'), None)
            if our_participant:
                # Sort by bid to determine rank
                sorted_participants = sorted(participants, key=lambda x: x['bid'])
                our_rank = next((i+1 for i, p in enumerate(sorted_participants) if p['name'] == "Our Company"), None)
                st.info(f"📊 Our rank: {our_rank}/{len(participants)}")
            
            st.dataframe(summary_df[['name', 'Bid Amount', '% of Estimate', 'Winner']], 
                        use_container_width=True, hide_index=True)
        
        # Notes Section
        st.markdown("---")
        notes = st.text_area("📝 Additional Notes", placeholder="Any observations, lessons learned, or special circumstances...", height=68)
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Historical Tender", use_container_width=True, type="primary")
        
        if submitted:
            if not all([tender_id, tender_title, procuring_entity, official_estimate > 0]):
                st.error("Please fill all required fields")
            elif not participants:
                st.error("Please add at least one participant")
            elif not winner_name:
                st.error("Please select the winning participant")
            else:
                # Prepare data
                competitors_list = [p for p in participants if p['type'] == 'competitor']
                competitors_json = json.dumps([{
                    'name': c['name'],
                    'competitor_id': c.get('competitor_id'),
                    'bid': c['bid'],
                    'was_winner': c.get('was_winner', False),
                    'bid_ratio': c['bid_ratio']
                } for c in competitors_list])
                
                # Determine winner type
                if winner_name == "Our Company":
                    winner_type = "Our Company"
                    winning_competitor = None
                else:
                    winner_type = "Competitor"
                    winning_competitor = winner_name
                
                data = {
                    'tender_id': tender_id,
                    'tender_title': tender_title,
                    'procuring_entity': procuring_entity,
                    'procurement_type': procurement_type,
                    'official_estimate': official_estimate,
                    'awarded_price': winning_price,
                    'our_awarded_price': our_bid if include_our_company else None,
                    'num_competitors': len(competitors_list),
                    'total_bidders': len(participants),
                    'our_rank': our_rank if include_our_company else None,
                    'award_date': award_date,
                    'competitors_data': competitors_json,
                    'winning_competitor': winning_competitor,
                    'winning_company_type': winner_type,
                    'notes': notes
                }
                
                try:
                    result = db.save_historical_tender(
                        st.session_state.user_id, 
                        st.session_state.company_id, 
                        data
                    )
                    
                    if result:
                        st.success(f"✅ Historical tender saved! ID: {result}")
                        
                        # Update competitor master stats
                        from modules.competitor_tracking import CompetitorTracker
                        tracker = CompetitorTracker(st.session_state.company_id)
                        
                        for comp in competitors_list:
                            tracker.update_competitor_profile(
                                competitor_name=comp['name'],
                                bid_amount=comp['bid'],
                                official_estimate=official_estimate,
                                was_winner=comp.get('was_winner', False),
                                tender_id=tender_id
                            )
                        
                        st.success(f"✅ Updated {len(competitors_list)} competitor profiles")
                        
                        # Recalculate NPPI
                        update_company_nppi(st.session_state.company_id, procurement_type)
                        
                        st.balloons()
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")

def render_view_historical_data():
    """View and manage historical tender data with edit functionality"""
    
    st.markdown("### Historical Tender Records")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        procurement_filter = st.selectbox("Filter by Type", ["All", "goods", "works", "services"])
    
    with col2:
        date_filter = st.date_input("From Date", value=datetime.now() - timedelta(days=365))
    
    with col3:
        winner_filter = st.selectbox("Filter by Winner", ["All", "Our Company", "Competitor", "Unknown"])
    
    with col4:
        search = st.text_input("🔍 Search", placeholder="Tender ID or Title...")
    
    # Get data
    procurement_type = None if procurement_filter == "All" else procurement_filter
    df = db.get_historical_tenders(st.session_state.company_id, procurement_type)
    
    if len(df) == 0:
        st.info("No historical tender data found. Add your first historical tender using the form above.")
        return
    
    # Apply filters
    if search:
        df = df[df['tender_id'].str.contains(search, case=False) | 
                df['tender_title'].str.contains(search, case=False)]
    
    if 'award_date' in df.columns:
        df['award_date'] = pd.to_datetime(df['award_date'])
        df = df[df['award_date'] >= pd.Timestamp(date_filter)]
    
    # Apply winner filter
    if winner_filter != "All" and 'winning_company_type' in df.columns:
        df = df[df['winning_company_type'] == winner_filter]
    
    # Display statistics
    st.markdown("#### 📊 Summary Statistics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Records", len(df))
    
    with col2:
        if len(df) > 0 and 'winning_company_type' in df.columns:
            our_wins = len(df[df['winning_company_type'] == "Our Company"])
            win_rate = (our_wins / len(df) * 100) if len(df) > 0 else 0
            st.metric("Our Win Rate", f"{win_rate:.0f}%")
    
    with col3:
        if len(df) > 0:
            avg_deviation = ((df['awarded_price'] - df['official_estimate']) / df['official_estimate'] * 100).mean()
            st.metric("Avg Winning Deviation", f"{avg_deviation:+.1f}%")
    
    with col4:
        if len(df) > 0:
            total_value = df['official_estimate'].sum()
            st.metric("Total Value (Est)", f"BDT {total_value/10000000:.2f}Cr")
    
    with col5:
        if len(df) > 0:
            nppi = calculate_company_nppi_from_df(df)
            if nppi:
                st.metric("Company NPPI", f"{nppi:.3f}")
    
    # Winner breakdown
    if len(df) > 0 and 'winning_company_type' in df.columns:
        st.markdown("#### 🏆 Winner Breakdown")
        
        col1, col2, col3 = st.columns(3)
        winner_counts = df['winning_company_type'].value_counts()
        
        with col1:
            our_wins = winner_counts.get("Our Company", 0)
            st.metric("🏆 Our Wins", our_wins)
        with col2:
            comp_wins = winner_counts.get("Competitor", 0)
            st.metric("👥 Competitor Wins", comp_wins)
        with col3:
            unknown_wins = winner_counts.get("Unknown", 0)
            st.metric("❓ Unknown Winner", unknown_wins)
    
    # Display data table
    st.markdown("#### 📋 Historical Tenders List")
    
    display_cols = ['id', 'tender_id', 'tender_title', 'procurement_type', 'official_estimate', 
                    'awarded_price', 'our_rank', 'total_bidders', 'award_date']
    
    if 'winning_company_type' in df.columns:
        display_cols.insert(5, 'winning_company_type')
    
    available_cols = [col for col in display_cols if col in df.columns]
    
    if available_cols:
        display_df = df[available_cols].copy()
        display_df['official_estimate'] = display_df['official_estimate'].apply(lambda x: f"BDT {x:,.0f}")
        display_df['awarded_price'] = display_df['awarded_price'].apply(lambda x: f"BDT {x:,.0f}")
        
        if 'winning_company_type' in display_df.columns:
            display_df['winning_company_type'] = display_df['winning_company_type'].apply(
                lambda x: "🏆 Us" if x == "Our Company" else "👤 Competitor" if x == "Competitor" else "❓ Unknown"
            )
            display_df.rename(columns={'winning_company_type': 'Winner'}, inplace=True)
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Edit and Delete Section
    st.markdown("---")
    st.markdown("#### ✏️ Edit or Delete Record")
    
    if len(df) > 0 and 'id' in df.columns:
        selected_id = st.selectbox(
            "Select Record to Edit/Delete", 
            df['id'].tolist(), 
            format_func=lambda x: f"{df[df['id']==x]['tender_id'].iloc[0]} - {df[df['id']==x]['tender_title'].iloc[0]}"
        )
        
        if selected_id:
            selected_record = df[df['id'] == selected_id].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✏️ Edit Selected Record", use_container_width=True, type="primary"):
                    st.session_state.edit_record = selected_record.to_dict()
                    st.rerun()
            
            with col2:
                if st.button("🗑️ Delete Selected Record", use_container_width=True, type="secondary"):
                    confirm = st.checkbox("Confirm deletion (cannot be undone)")
                    if confirm:
                        try:
                            conn = db.get_connection()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM historical_tenders WHERE id = ?", (selected_id,))
                            conn.commit()
                            conn.close()
                            st.success("Record deleted successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting: {str(e)}")
    
    # Edit Form (shows when edit mode is active)
    if st.session_state.get('edit_record'):
        st.markdown("---")
        st.markdown("### ✏️ Edit Historical Tender")

        record = st.session_state.edit_record

        # Safe numeric defaults
        def safe_float(val, default=0.0):
            try:
                if pd.notna(val):
                    return float(val)
            except:
                pass
            return default

        # Use a form with proper submit button
        with st.form(key="edit_tender_form"):

            # ==============================
            # BASIC INFORMATION
            # ==============================

            st.markdown("#### 📋 Basic Tender Information")

            col1, col2 = st.columns(2)

            with col1:
                tender_id = st.text_input(
                    "Tender ID",
                    value=record.get('tender_id', '')
                )

                tender_title = st.text_input(
                    "Tender Title",
                    value=record.get('tender_title', '')
                )

                procuring_entity = st.text_input(
                    "Procuring Entity",
                    value=record.get('procuring_entity', '')
                )

                procurement_types = ["goods", "works", "services"]

                current_type = record.get('procurement_type', 'goods')

                try:
                    type_index = procurement_types.index(current_type)
                except:
                    type_index = 0

                procurement_type = st.selectbox(
                    "Procurement Type",
                    procurement_types,
                    index=type_index
                )

            with col2:

                official_estimate = st.number_input(
                    "Official Estimate (BDT)",
                    min_value=0.0,
                    step=1000000.0,
                    value=safe_float(record.get('official_estimate')),
                    format="%.0f"
                )

                award_date = st.date_input(
                    "Award Date",
                    value=pd.to_datetime(
                        record.get('award_date', datetime.now())
                    )
                )

            # ==============================
            # WINNER INFORMATION
            # ==============================

            st.markdown("---")
            st.markdown("#### 🏆 Winner Information")

            col1, col2 = st.columns(2)

            winner_types = [
                "Our Company",
                "Competitor",
                "Unknown"
            ]

            current_winner = record.get(
                'winning_company_type',
                'Unknown'
            )

            try:
                winner_index = winner_types.index(current_winner)
            except:
                winner_index = 2

            with col1:

                winner_type = st.radio(
                    "Who won the tender?",
                    winner_types,
                    index=winner_index
                )

            with col2:

                winning_price = st.number_input(
                    "Winning Bid Price (BDT)",
                    min_value=0.0,
                    step=1000000.0,
                    value=safe_float(record.get('awarded_price')),
                    format="%.0f"
                )

            # ==============================
            # OUR PARTICIPATION
            # ==============================

            if winner_type != "Our Company":

                st.markdown("#### 📝 Our Participation")

                col1, col2 = st.columns(2)

                with col1:

                    our_bid = st.number_input(
                        "Our Bid Price (BDT)",
                        min_value=0.0,
                        step=1000000.0,
                        value=safe_float(
                            record.get('our_awarded_price')
                        ),
                        format="%.0f"
                    )

                with col2:

                    if our_bid > 0:

                        our_rank = st.number_input(
                            "Our Rank",
                            min_value=2,
                            max_value=50,
                            value=int(
                                record.get('our_rank', 2)
                            )
                        )

                    else:

                        our_rank = None

            else:

                our_bid = winning_price
                our_rank = 1

            # ==============================
            # COMPETITORS
            # ==============================

            st.markdown("---")
            st.markdown("#### 👥 Competitor Bids")

            existing_competitors = []

            if (
                'competitors_data' in record
                and pd.notna(record['competitors_data'])
            ):
                try:
                    existing_competitors = json.loads(
                        record['competitors_data']
                    )
                except:
                    existing_competitors = []

            st.info(
                f"Current competitors: {len(existing_competitors)}"
            )

            updated_competitors = []

            for idx, comp in enumerate(existing_competitors):

                st.markdown(
                    f"**Competitor {idx+1}**"
                )

                col_a, col_b, col_c, col_d = st.columns(
                    [3, 2.5, 1, 1]
                )

                with col_a:

                    comp_name = st.text_input(
                        "Name",
                        value=comp.get('name', ''),
                        key=f"edit_comp_name_{idx}",
                        disabled=True
                    )

                with col_b:

                    comp_bid = st.number_input(
                        "Bid Amount",
                        min_value=0.0,
                        step=1000000.0,
                        value=safe_float(comp.get('bid')),
                        format="%.0f",
                        key=f"edit_comp_bid_{idx}"
                    )

                with col_c:

                    was_winner = st.checkbox(
                        "Winner?",
                        value=comp.get(
                            'was_winner',
                            False
                        ),
                        key=f"edit_comp_winner_{idx}"
                    )

                with col_d:

                    if (
                        official_estimate > 0
                        and comp_bid > 0
                    ):

                        ratio = comp_bid / official_estimate

                        if ratio < 0.88:
                            st.markdown("🟢 Aggressive")

                        elif ratio < 0.93:
                            st.markdown("🟡 Moderate")

                        else:
                            st.markdown("🔴 Conservative")

                updated_competitors.append({
                    'name': comp_name,
                    'competitor_id': comp.get('competitor_id'),
                    'bid': comp_bid,
                    'was_winner': was_winner,
                    'bid_ratio':
                        comp_bid / official_estimate
                        if official_estimate > 0
                        else 0.90
                })

            # ==============================
            # NOTES
            # ==============================

            st.markdown("---")

            notes = st.text_area(
                "Notes",
                value=record.get('notes', '')
                if pd.notna(
                    record.get('notes')
                )
                else '',
                height=68
            )

            # ==============================
            # SUBMIT BUTTONS
            # ==============================

            st.markdown("---")

            col1, col2 = st.columns(2)

            with col1:

                submitted = st.form_submit_button(
                    "💾 Save Changes",
                    use_container_width=True,
                    type="primary"
                )

            with col2:

                cancelled = st.form_submit_button(
                    "Cancel",
                    use_container_width=True
                )

        # ==============================
        # HANDLE SUBMIT
        # ==============================

        if submitted:

            competitors_json = (
                json.dumps(updated_competitors)
                if updated_competitors
                else None
            )

            winning_competitor = None

            for comp in updated_competitors:

                if comp.get('was_winner'):
                    winning_competitor = comp['name']
                    break

            conn = db.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            UPDATE historical_tenders 
            SET
                tender_id = ?,
                tender_title = ?,
                procuring_entity = ?,
                procurement_type = ?,
                official_estimate = ?,
                awarded_price = ?,
                our_awarded_price = ?,
                our_rank = ?,
                winning_company_type = ?,
                winning_competitor = ?,
                award_date = ?,
                competitors_data = ?,
                notes = ?,
                total_bidders = ?
            WHERE id = ?
            ''', (

                tender_id,
                tender_title,
                procuring_entity,
                procurement_type,

                float(official_estimate),
                float(winning_price),

                float(our_bid)
                if our_bid > 0
                else None,

                our_rank
                if our_rank
                else None,

                winner_type,
                winning_competitor,

                award_date,

                competitors_json,
                notes,

                len(updated_competitors) + 1,

                selected_id

            ))

            conn.commit()
            conn.close()

            st.success(
                "✅ Record updated successfully!"
            )

            del st.session_state.edit_record

            st.rerun()

        if cancelled:

            del st.session_state.edit_record

            st.rerun()
    
    # Detailed view (without edit)
    st.markdown("---")
    st.markdown("#### 🔍 Detailed Tender View")
    
    if len(df) > 0:
        tenders_with_competitors = df[df['competitors_data'].notna()] if 'competitors_data' in df.columns else pd.DataFrame()
        
        if len(tenders_with_competitors) > 0:
            selected_tender = st.selectbox(
                "Select Tender to View Details",
                tenders_with_competitors['tender_id'].tolist(),
                format_func=lambda x: f"{x} - {tenders_with_competitors[tenders_with_competitors['tender_id']==x]['tender_title'].iloc[0]}"
            )
            
            if selected_tender:
                tender_data = df[df['tender_id'] == selected_tender].iloc[0]
                
                st.markdown(f"**Tender:** {tender_data['tender_title']}")
                st.markdown(f"**Procuring Entity:** {tender_data['procuring_entity']}")
                st.markdown(f"**Official Estimate:** BDT {tender_data['official_estimate']:,.0f}")
                
                st.markdown("#### 🏆 Winner Information")
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'winning_company_type' in tender_data:
                        winner_type_val = tender_data['winning_company_type']
                        if winner_type_val == "Our Company":
                            st.success("✅ **Winner: Our Company**")
                            if 'our_awarded_price' in tender_data and pd.notna(tender_data['our_awarded_price']):
                                st.metric("Our Winning Bid", f"BDT {tender_data['our_awarded_price']:,.0f}")
                            else:
                                st.metric("Winning Bid", f"BDT {tender_data['awarded_price']:,.0f}")
                        elif winner_type_val == "Competitor":
                            winning_comp = tender_data.get('winning_competitor', 'Unknown Competitor')
                            st.warning(f"⚠️ **Winner: {winning_comp}**")
                            st.metric("Winning Bid", f"BDT {tender_data['awarded_price']:,.0f}")
                            
                            if 'our_awarded_price' in tender_data and pd.notna(tender_data['our_awarded_price']):
                                our_diff = tender_data['our_awarded_price'] - tender_data['awarded_price']
                                st.metric("Our Bid", f"BDT {tender_data['our_awarded_price']:,.0f}", 
                                        f"{'Higher' if our_diff > 0 else 'Lower'} by BDT {abs(our_diff):,.0f}")
                        else:
                            st.info("❓ **Winner: Unknown**")
                            st.metric("Winning Bid", f"BDT {tender_data['awarded_price']:,.0f}")
                
                with col2:
                    if 'our_rank' in tender_data and pd.notna(tender_data['our_rank']):
                        st.metric("Our Rank", f"{int(tender_data['our_rank'])} / {int(tender_data['total_bidders'])}")
                    
                    if tender_data['official_estimate'] > 0:
                        win_deviation = ((tender_data['awarded_price'] - tender_data['official_estimate']) / tender_data['official_estimate']) * 100
                        if win_deviation < 0:
                            st.success(f"Winning bid is {abs(win_deviation):.1f}% BELOW estimate")
                        else:
                            st.warning(f"Winning bid is {win_deviation:.1f}% ABOVE estimate")
                
                if 'competitors_data' in tender_data and pd.notna(tender_data['competitors_data']):
                    try:
                        competitors = json.loads(tender_data['competitors_data'])
                        
                        if competitors:
                            st.markdown("#### 👥 All Participants Breakdown")
                            
                            comp_df = pd.DataFrame(competitors)
                            comp_df['Bid Amount'] = comp_df['bid'].apply(lambda x: f"BDT {x:,.0f}")
                            comp_df['% of Estimate'] = comp_df['bid_ratio'].apply(lambda x: f"{x*100:.1f}%")
                            comp_df['Winner'] = comp_df['was_winner'].apply(lambda x: "🏆 YES" if x else "❌")
                            
                            comp_df = comp_df.sort_values('bid')
                            
                            st.dataframe(comp_df[['name', 'Bid Amount', '% of Estimate', 'Winner']], 
                                        use_container_width=True, hide_index=True)
                    except:
                        pass

def render_nppi_analytics():
    """Display NPPI analytics and trends with winner-based calculation"""
    
    st.markdown("### 📈 NPPI Analytics")
    st.caption("National Public Procurement Price Index - PPR 2025 Clause 49.4-49.5")
    st.info("💡 NPPI is calculated using actual winning bid prices, not our bids")
    
    # Get historical data
    df = db.get_historical_tenders(st.session_state.company_id)
    
    if len(df) == 0:
        st.info("Not enough historical data for NPPI calculation. Add at least 3 historical tenders.")
        return
    
    # Calculate NPPI by winner type
    nppi_analysis = calculate_nppi_by_winner_type(df)
    
    # Display current NPPI values with winner breakdown
    st.markdown("#### Current NPPI Values by Winner Type")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if nppi_analysis['overall']:
            st.metric(
                "Overall Market NPPI", 
                f"{nppi_analysis['overall']:.4f}",
                help=f"Based on {nppi_analysis['data_points']['overall']} total tenders"
            )
        else:
            st.metric("Overall Market NPPI", "Insufficient Data", help="Need at least 3 tenders")
    
    with col2:
        if nppi_analysis['our_wins']:
            st.metric(
                "🎯 Our Wins NPPI", 
                f"{nppi_analysis['our_wins']:.4f}",
                help=f"Based on {nppi_analysis['data_points']['our_wins']} tenders we won"
            )
            # Show comparison
            if nppi_analysis['overall']:
                diff = (nppi_analysis['our_wins'] - nppi_analysis['overall']) * 100
                if diff < 0:
                    st.caption(f"📉 {abs(diff):.1f}% below market average (more competitive)")
                else:
                    st.caption(f"📈 {diff:.1f}% above market average")
        else:
            st.metric("🎯 Our Wins NPPI", "Insufficient Data", help="Need at least 3 wins")
    
    with col3:
        if nppi_analysis['competitor_wins']:
            st.metric(
                "👥 Competitor Wins NPPI", 
                f"{nppi_analysis['competitor_wins']:.4f}",
                help=f"Based on {nppi_analysis['data_points']['competitor_wins']} competitor wins"
            )
            if nppi_analysis['overall']:
                diff = (nppi_analysis['competitor_wins'] - nppi_analysis['overall']) * 100
                if diff < 0:
                    st.caption(f"📉 {abs(diff):.1f}% below market average")
                else:
                    st.caption(f"📈 {diff:.1f}% above market average")
        else:
            st.metric("👥 Competitor Wins NPPI", "Insufficient Data", help="Need at least 3 competitor wins")
    
    # NPPI Trend Chart by Winner Type
    st.markdown("#### 📊 NPPI Trend Over Time")
    
    if 'award_date' in df.columns and len(df) >= 5:
        df['award_date'] = pd.to_datetime(df['award_date'])
        df_sorted = df.sort_values('award_date')
        
        # Calculate rolling NPPI for different winner types
        rolling_overall = []
        rolling_our_wins = []
        rolling_comp_wins = []
        dates = []
        
        for i in range(3, len(df_sorted) + 1):
            subset = df_sorted.iloc[:i]
            dates.append(subset['award_date'].iloc[-1])
            
            # Overall
            overall_nppi = calculate_company_nppi_from_df(subset)
            rolling_overall.append(overall_nppi if overall_nppi else None)
            
            # Our Wins
            our_wins_subset = subset[subset['winning_company_type'] == "Our Company"] if 'winning_company_type' in subset.columns else pd.DataFrame()
            if len(our_wins_subset) >= 3:
                our_nppi = calculate_company_nppi_from_df(our_wins_subset)
                rolling_our_wins.append(our_nppi)
            else:
                rolling_our_wins.append(None)
            
            # Competitor Wins
            comp_wins_subset = subset[subset['winning_company_type'] == "Competitor"] if 'winning_company_type' in subset.columns else pd.DataFrame()
            if len(comp_wins_subset) >= 3:
                comp_nppi = calculate_company_nppi_from_df(comp_wins_subset)
                rolling_comp_wins.append(comp_nppi)
            else:
                rolling_comp_wins.append(None)
        
        fig = go.Figure()
        
        # Add overall trend
        valid_overall = [(d, v) for d, v in zip(dates, rolling_overall) if v is not None]
        if valid_overall:
            fig.add_trace(go.Scatter(
                x=[d for d, v in valid_overall],
                y=[v for d, v in valid_overall],
                mode='lines+markers',
                name='Overall Market',
                line=dict(color='blue', width=3),
                marker=dict(size=8)
            ))
        
        # Add our wins trend
        valid_our = [(d, v) for d, v in zip(dates, rolling_our_wins) if v is not None]
        if valid_our:
            fig.add_trace(go.Scatter(
                x=[d for d, v in valid_our],
                y=[v for d, v in valid_our],
                mode='lines+markers',
                name='Our Wins',
                line=dict(color='green', width=3),
                marker=dict(size=8)
            ))
        
        # Add competitor wins trend
        valid_comp = [(d, v) for d, v in zip(dates, rolling_comp_wins) if v is not None]
        if valid_comp:
            fig.add_trace(go.Scatter(
                x=[d for d, v in valid_comp],
                y=[v for d, v in valid_comp],
                mode='lines+markers',
                name='Competitor Wins',
                line=dict(color='red', width=3),
                marker=dict(size=8)
            ))
        
        # Add baseline
        fig.add_hline(y=1.0, line_dash="dash", line_color="gray", 
                     annotation_text="Baseline (1.0)")
        
        fig.update_layout(
            title="NPPI Trend by Winner Type",
            xaxis_title="Date",
            yaxis_title="NPPI Factor",
            height=450,
            showlegend=True,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Winner Analysis based on NPPI
    st.markdown("#### 💡 Market Intelligence")
    
    if nppi_analysis['our_wins'] and nppi_analysis['competitor_wins']:
        col1, col2 = st.columns(2)
        
        with col1:
            if nppi_analysis['our_wins'] < nppi_analysis['competitor_wins']:
                st.success("✅ **We win with more competitive bids**\n\nOur winning bids are, on average, more aggressive than competitor-winning bids.")
            elif nppi_analysis['our_wins'] > nppi_analysis['competitor_wins']:
                st.warning("⚠️ **Competitors win with more aggressive bids**\n\nWe may need to lower our bids to be more competitive.")
            else:
                st.info("📊 **Market balanced**\n\nOur winning bids and competitor-winning bids are at similar levels.")
        
        with col2:
            # Calculate market aggression indicator
            market_aggression = (1 - nppi_analysis['competitor_wins']) * 100
            if market_aggression > 15:
                st.warning(f"🔥 **Aggressive Market**\n\nMarket aggression index: {market_aggression:.0f}%")
            elif market_aggression > 8:
                st.info(f"📊 **Moderate Market**\n\nMarket aggression index: {market_aggression:.0f}%")
            else:
                st.success(f"✅ **Conservative Market**\n\nMarket aggression index: {market_aggression:.0f}%")
    
    # Winning Price Distribution
    st.markdown("#### 📊 Winning Price Deviation Distribution")
    
    if len(df) > 0:
        df['win_deviation'] = ((df['awarded_price'] - df['official_estimate']) / df['official_estimate']) * 100
        
        # Color by winner type
        colors = []
        if 'winning_company_type' in df.columns:
            color_map = {"Our Company": "green", "Competitor": "red", "Unknown": "gray"}
            colors = [color_map.get(wt, "blue") for wt in df['winning_company_type']]
        
        fig = px.histogram(
            df, 
            x='win_deviation', 
            nbins=25,
            title="Distribution of Winning Bid Deviations",
            labels={'win_deviation': 'Deviation from Estimate (%)', 'count': 'Number of Tenders'},
            color_discrete_sequence=['blue']
        )
        
        fig.add_vline(x=0, line_dash="dash", line_color="gray", 
                     annotation_text="Estimate")
        fig.add_vline(x=df['win_deviation'].median(), line_dash="dash", line_color="green",
                     annotation_text=f"Median: {df['win_deviation'].median():.1f}%")
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # Statistics by winner type
        if 'winning_company_type' in df.columns:
            st.markdown("#### 📊 Statistics by Winner Type")
            
            stats_data = []
            for winner_type in ["Our Company", "Competitor"]:
                subset = df[df['winning_company_type'] == winner_type]
                if len(subset) > 0:
                    stats_data.append({
                        'Winner': winner_type,
                        'Count': len(subset),
                        'Avg Deviation': f"{subset['win_deviation'].mean():+.1f}%",
                        'Median Deviation': f"{subset['win_deviation'].median():+.1f}%",
                        'Std Deviation': f"{subset['win_deviation'].std():.1f}%",
                        'Min Deviation': f"{subset['win_deviation'].min():+.1f}%",
                        'Max Deviation': f"{subset['win_deviation'].max():+.1f}%"
                    })
            
            if stats_data:
                st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)
    
    # Recommendation based on data
    st.markdown("#### 💡 NPPI Insights & Recommendations")
    
    if len(df) >= 10:
        st.success("✅ **Excellent Data Coverage** - Your NPPI calculation is highly reliable")
        
        # Provide specific recommendations based on NPPI
        if nppi_analysis['our_wins'] and nppi_analysis['competitor_wins']:
            if nppi_analysis['our_wins'] > nppi_analysis['competitor_wins']:
                st.info("📌 **Recommendation:** Consider reducing your bid prices by 2-3% to match competitor aggression levels.")
            elif nppi_analysis['our_wins'] < nppi_analysis['competitor_wins']:
                st.info("📌 **Recommendation:** Your bidding strategy is already competitive. Focus on maintaining margins while selectively being aggressive.")
            else:
                st.info("📌 **Recommendation:** Maintain current bidding strategy. Market conditions are favorable.")
        
        st.info(f"Based on {len(df)} historical tenders, your company-specific NPPI provides accurate market intelligence.")
        
    elif len(df) >= 5:
        st.warning("⚠️ **Moderate Data Coverage** - NPPI is reliable but adding more data will improve accuracy")
        st.info(f"Add {10 - len(df)} more historical tenders for optimal NPPI accuracy.")
        st.info("📌 Include both wins and losses for better market understanding.")
    else:
        st.warning("⚠️ **Insufficient Data** - Add more historical tenders for reliable NPPI")
        st.info(f"Need at least 5 tenders for reliable NPPI. Currently have {len(df)}.")
        st.info("📌 Record both our wins and competitor wins to get accurate market intelligence.")

def render_import_export():
    """Import/Export historical data"""
    
    st.markdown("### 📥 Import Historical Data")
    st.caption("Bulk import historical tenders from CSV/Excel file")
    
    st.info("""
    **Expected CSV Format:**
    - Required columns: `tender_id`, `tender_title`, `procuring_entity`, `procurement_type`, 
      `official_estimate`, `awarded_price`, `award_date`
    - Optional columns: `num_competitors`, `our_rank`, `total_bidders`, `notes`
    - For competitor data, use JSON format in `competitors_data` column
    """)
    
    uploaded_file = st.file_uploader("Upload CSV/Excel file", type=['csv', 'xlsx'])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            else:
                df = pd.read_csv(uploaded_file)
            
            st.success(f"✅ Loaded {len(df)} records")
            st.dataframe(df.head(), use_container_width=True)
            
            if st.button("Import Data", use_container_width=True):
                success_count = 0
                error_count = 0
                
                for _, row in df.iterrows():
                    try:
                        data = {
                            'tender_id': str(row.get('tender_id', '')),
                            'tender_title': str(row.get('tender_title', '')),
                            'procuring_entity': str(row.get('procuring_entity', '')),
                            'procurement_type': str(row.get('procurement_type', 'goods')),
                            'official_estimate': float(row.get('official_estimate', 0)),
                            'awarded_price': float(row.get('awarded_price', 0)),
                            'num_competitors': int(row.get('num_competitors', 0)),
                            'total_bidders': int(row.get('total_bidders', 0)),
                            'our_rank': int(row.get('our_rank', 0)),
                            'award_date': pd.to_datetime(row.get('award_date', datetime.now())).date(),
                            'competitors_data': row.get('competitors_data', None),
                            'winning_competitor': row.get('winning_competitor', None),
                            'notes': str(row.get('notes', ''))
                        }
                        
                        if data['official_estimate'] > 0 and data['awarded_price'] > 0:
                            db.save_historical_tender(
                                st.session_state.user_id,
                                st.session_state.company_id,
                                data
                            )
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        error_count += 1
                        st.warning(f"Error importing row: {str(e)}")
                
                st.success(f"✅ Imported {success_count} records successfully!")
                if error_count > 0:
                    st.warning(f"⚠️ {error_count} records failed to import")
                
                # Recalculate NPPI
                for ptype in ['goods', 'works', 'services']:
                    update_company_nppi(st.session_state.company_id, ptype)
                
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
    
    st.markdown("---")
    st.markdown("### 📤 Export Historical Data")
    
    df = db.get_historical_tenders(st.session_state.company_id)
    
    if len(df) > 0:
        # Prepare export data
        export_df = df.copy()
        
        # Drop large JSON columns if needed
        if 'competitors_data' in export_df.columns:
            export_df['competitors_data'] = export_df['competitors_data'].apply(lambda x: x if len(str(x)) < 100 else "See detailed view")
        
        csv = export_df.to_csv(index=False)
        st.download_button(
            label="📥 Export All Historical Data (CSV)",
            data=csv,
            file_name=f"historical_tenders_{st.session_state.company_name}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # Export with competitor details
        st.markdown("#### Export with Competitor Details")
        st.caption("Download a detailed export including all competitor information")
        
        # Create detailed export with competitor data parsed
        detailed_records = []
        for _, row in df.iterrows():
            record = {
                'tender_id': row.get('tender_id', ''),
                'tender_title': row.get('tender_title', ''),
                'procurement_type': row.get('procurement_type', ''),
                'official_estimate': row.get('official_estimate', 0),
                'awarded_price': row.get('awarded_price', 0),
                'our_rank': row.get('our_rank', 0),
                'award_date': row.get('award_date', '')
            }
            
            # Add competitor data if available
            if 'competitors_data' in row and pd.notna(row['competitors_data']):
                try:
                    competitors = json.loads(row['competitors_data'])
                    for idx, comp in enumerate(competitors):
                        record[f'competitor_{idx+1}_name'] = comp.get('name', '')
                        record[f'competitor_{idx+1}_bid'] = comp.get('bid', 0)
                        record[f'competitor_{idx+1}_winner'] = comp.get('was_winner', False)
                except:
                    pass
            
            detailed_records.append(record)
        
        detailed_df = pd.DataFrame(detailed_records)
        detailed_csv = detailed_df.to_csv(index=False)
        st.download_button(
            label="📥 Export with Competitor Details (CSV)",
            data=detailed_csv,
            file_name=f"historical_tenders_detailed_{st.session_state.company_name}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("No historical data to export")

def calculate_company_nppi_from_df(df):
    """
    Calculate NPPI from DataFrame using actual winning prices
    As per PPR 2025, Clause 49.4 - 49.5
    
    NPPI is calculated as 1 + median deviation of winning prices from official estimates
    Minimum 3 data points required
    """
    if len(df) < 3:
        return None
    
    deviations = []
    for _, row in df.iterrows():
        # Use ONLY the actual winning price (awarded_price)
        if row['official_estimate'] > 0 and row['awarded_price'] > 0:
            deviation = (row['awarded_price'] - row['official_estimate']) / row['official_estimate']
            deviations.append(deviation)
    
    if len(deviations) >= 3:
        # Use median to avoid outlier impact (PPR 2025 recommends median)
        median_deviation = np.median(deviations)
        nppi_factor = 1 + median_deviation
        return round(nppi_factor, 4)
    return None


def calculate_nppi_by_winner_type(df):
    """
    Calculate NPPI separately for different winner types
    As per PPR 2025 - uses winning prices only
    """
    if len(df) < 3:
        return None
    
    result = {
        'overall': None,
        'our_wins': None,
        'competitor_wins': None,
        'data_points': {
            'overall': len(df),
            'our_wins': 0,
            'competitor_wins': 0
        }
    }
    
    # Overall NPPI (all tenders - using winning price)
    result['overall'] = calculate_company_nppi_from_df(df)
    
    # Our Wins NPPI
    if 'winning_company_type' in df.columns:
        our_wins_df = df[df['winning_company_type'] == "Our Company"]
        if len(our_wins_df) >= 3:
            result['our_wins'] = calculate_company_nppi_from_df(our_wins_df)
            result['data_points']['our_wins'] = len(our_wins_df)
        
        # Competitor Wins NPPI
        comp_wins_df = df[df['winning_company_type'] == "Competitor"]
        if len(comp_wins_df) >= 3:
            result['competitor_wins'] = calculate_company_nppi_from_df(comp_wins_df)
            result['data_points']['competitor_wins'] = len(comp_wins_df)
    
    return result


def get_weighted_nppi(company_id, procurement_type='goods'):
    """
    Get weighted NPPI based on available historical winning data
    Priority: Our Wins > Competitor Wins > Overall > Default
    As per PPR 2025 - uses winning prices only
    """
    df = db.get_historical_tenders(company_id, procurement_type)
    
    if len(df) < 3:
        # Default based on procurement type (PPR 2025 default values)
        # According to the document, these are typical market indices
        defaults = {'goods': 0.92, 'works': 0.89, 'services': 0.91}
        return defaults.get(procurement_type, 0.92), "Default Market Index"
    
    nppi_analysis = calculate_nppi_by_winner_type(df)
    
    # Priority: Our Wins (most relevant) > Competitor Wins > Overall > Default
    if nppi_analysis['our_wins'] and nppi_analysis['data_points']['our_wins'] >= 3:
        return nppi_analysis['our_wins'], f"Our Wins ({nppi_analysis['data_points']['our_wins']} tenders)"
    elif nppi_analysis['competitor_wins'] and nppi_analysis['data_points']['competitor_wins'] >= 3:
        return nppi_analysis['competitor_wins'], f"Competitor Wins ({nppi_analysis['data_points']['competitor_wins']} tenders)"
    elif nppi_analysis['overall']:
        return nppi_analysis['overall'], f"Overall Market ({nppi_analysis['data_points']['overall']} tenders)"
    else:
        defaults = {'goods': 0.92, 'works': 0.89, 'services': 0.91}
        return defaults.get(procurement_type, 0.92), "Default Market Index"


def calculate_nppi_by_winner_type(df):
    """
    Calculate NPPI separately for different winner types using actual winning prices
    """
    if len(df) < 3:
        return None
    
    result = {
        'overall': None,
        'our_wins': None,
        'competitor_wins': None,
        'data_points': {
            'overall': len(df),
            'our_wins': 0,
            'competitor_wins': 0
        }
    }
    
    # Overall NPPI (all tenders - using winning price)
    result['overall'] = calculate_company_nppi_from_df(df)
    
    # Our Wins NPPI
    if 'winning_company_type' in df.columns:
        our_wins_df = df[df['winning_company_type'] == "Our Company"]
        if len(our_wins_df) >= 3:
            result['our_wins'] = calculate_company_nppi_from_df(our_wins_df)
            result['data_points']['our_wins'] = len(our_wins_df)
        
        # Competitor Wins NPPI
        comp_wins_df = df[df['winning_company_type'] == "Competitor"]
        if len(comp_wins_df) >= 3:
            result['competitor_wins'] = calculate_company_nppi_from_df(comp_wins_df)
            result['data_points']['competitor_wins'] = len(comp_wins_df)
    
    return result


def update_company_nppi(company_id, procurement_type):
    """Update NPPI for a company based on historical winning prices"""
    df = db.get_historical_tenders(company_id, procurement_type)
    
    if len(df) >= 3:
        # Calculate NPPI using overall winning prices
        nppi = calculate_company_nppi_from_df(df)
        if nppi:
            try:
                db.save_company_nppi(company_id, procurement_type, nppi, len(df))
                return nppi
            except Exception as e:
                print(f"Error saving NPPI: {e}")
    return None

def get_weighted_nppi(company_id, procurement_type='goods'):
    """
    Get weighted NPPI based on available historical winning data
    Prioritizes Our Wins, then Competitor Wins, then Overall, then Default
    """
    df = db.get_historical_tenders(company_id, procurement_type)
    
    if len(df) < 3:
        # Default based on procurement type
        defaults = {'goods': 0.92, 'works': 0.89, 'services': 0.91}
        return defaults.get(procurement_type, 0.92), "Default Market Index"
    
    # Calculate NPPI by winner type
    nppi_analysis = calculate_nppi_by_winner_type(df)
    
    # Priority: Our Wins (most relevant) > Competitor Wins > Overall > Default
    if nppi_analysis['our_wins'] and nppi_analysis['data_points']['our_wins'] >= 3:
        return nppi_analysis['our_wins'], f"Our Wins ({nppi_analysis['data_points']['our_wins']} tenders)"
    elif nppi_analysis['competitor_wins'] and nppi_analysis['data_points']['competitor_wins'] >= 3:
        return nppi_analysis['competitor_wins'], f"Competitor Wins ({nppi_analysis['data_points']['competitor_wins']} tenders)"
    elif nppi_analysis['overall']:
        return nppi_analysis['overall'], f"Overall Market ({nppi_analysis['data_points']['overall']} tenders)"
    else:
        defaults = {'goods': 0.92, 'works': 0.89, 'services': 0.91}
        return defaults.get(procurement_type, 0.92), "Default Market Index"

def get_company_nppi(company_id, procurement_type='goods'):
    """Get company-specific NPPI, fallback to default if not available"""
    try:
        company_nppi = db.get_nppi_for_company(company_id, procurement_type)
        
        if company_nppi and company_nppi.get('data_points', 0) >= 3:
            return company_nppi['nppi_factor']
    except:
        pass
    
    # Default based on procurement type
    defaults = {'goods': 0.92, 'works': 0.89, 'services': 0.91}
    return defaults.get(procurement_type, 0.92)