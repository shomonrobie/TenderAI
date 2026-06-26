"""
tender_data_importer.py
Module for importing tender data from Excel files with competitor management
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import re
from typing import Dict, List, Tuple, Optional

from database.unified_db_manager import UnifiedDatabaseManager


class TenderDataImporter:
    """Handles import of tender data from Excel files"""
    
    def __init__(self, db_manager: UnifiedDatabaseManager):
        self.db = db_manager
        
    def parse_opening_report(self, df: pd.DataFrame) -> Dict:
        """
        Parse the opening report format with headers and footers
        Expected format: Opening Report Header, then data rows, then footer
        """
        result = {
            'tender_id': None,
            'data_rows': [],
            'winner_info': None,
            'competitors': []
        }
        
        # Find the header row (contains "Name of Tenderer" and column headers)
        header_row_idx = None
        for idx, row in df.iterrows():
            row_str = ' '.join(str(val) for val in row.values if pd.notna(val))
            if 'Name of Tenderer' in row_str and 'Quoted Amount' in row_str:
                header_row_idx = idx
                break
        
        if header_row_idx is None:
            st.error("Could not find header row in the file")
            return result
        
        # Get column names from header row
        header_row = df.iloc[header_row_idx]
        columns = []
        for col in header_row:
            if pd.notna(col):
                columns.append(str(col).strip())
        
        # Find data rows (after header, before footer)
        data_start = header_row_idx + 1
        data_end = len(df)
        
        # Look for footer
        for idx in range(data_start, len(df)):
            row_str = ' '.join(str(val) for val in df.iloc[idx].values if pd.notna(val))
            if 'Opening Report Footer' in row_str or 'Tender ID' in row_str:
                data_end = idx
                break
        
        # Extract tender ID from footer or header
        for idx in range(max(0, data_end - 5), len(df)):
            row_str = ' '.join(str(val) for val in df.iloc[idx].values if pd.notna(val))
            tender_match = re.search(r'Tender\s*ID[:\s]*([A-Z0-9]+)', row_str, re.IGNORECASE)
            if tender_match:
                result['tender_id'] = tender_match.group(1)
                break
        
        # Extract data rows
        data_rows = []
        for idx in range(data_start, data_end):
            row = df.iloc[idx]
            if pd.notna(row.iloc[0]):  # Skip empty rows
                data_rows.append(row)
        
        result['data_rows'] = data_rows
        result['header_columns'] = columns
        
        # Parse the data based on column structure
        self._parse_competitor_data(result)
        
        return result
    
    def _parse_competitor_data(self, parsed_data: Dict):
        """Parse competitor data from the opening report"""
        competitors = []
        winner_info = None
        
        columns = parsed_data.get('header_columns', [])
        data_rows = parsed_data.get('data_rows', [])
        
        # Identify column indices
        name_col = None
        quoted_col = None
        discount_pct_col = None
        discount_amount_col = None
        final_col = None
        
        for idx, col in enumerate(columns):
            col_lower = col.lower()
            if 'name' in col_lower or 'tenderer' in col_lower:
                name_col = idx
            elif 'quoted amount' in col_lower and 'discount' not in col_lower:
                quoted_col = idx
            elif 'discount in percentage' in col_lower:
                discount_pct_col = idx
            elif 'discount in amount' in col_lower:
                discount_amount_col = idx
            elif 'amount' in col_lower and 'discount' in col_lower:
                final_col = idx
        
        # If columns not found, try alternative detection
        if name_col is None or quoted_col is None:
            # Fallback: use first 4 columns
            name_col = 0
            quoted_col = 1
            discount_pct_col = 2
            discount_amount_col = 3
            final_col = 4
        
        for row in data_rows:
            if len(row) <= max(name_col, quoted_col, final_col):
                continue
                
            competitor_name = str(row.iloc[name_col]).strip()
            if not competitor_name or competitor_name in ['Name of Tenderer', 'S. No']:
                continue
            
            # Skip serial number rows if they don't contain names
            if re.match(r'^\d+$', competitor_name):
                continue
            
            # Parse numeric values
            try:
                quoted_amount = float(row.iloc[quoted_col]) if pd.notna(row.iloc[quoted_col]) else 0
            except:
                quoted_amount = 0
                
            try:
                discount_pct = float(row.iloc[discount_pct_col]) if pd.notna(row.iloc[discount_pct_col]) else 0
            except:
                discount_pct = 0
                
            try:
                discount_amount = float(row.iloc[discount_amount_col]) if pd.notna(row.iloc[discount_amount_col]) else 0
            except:
                discount_amount = 0
                
            try:
                final_amount = float(row.iloc[final_col]) if pd.notna(row.iloc[final_col]) else 0
            except:
                final_amount = quoted_amount - discount_amount if discount_amount > 0 else quoted_amount
            
            competitor_data = {
                'name': competitor_name,
                'quoted_amount': quoted_amount,
                'discount_percentage': discount_pct,
                'discount_amount': discount_amount,
                'final_amount': final_amount,
                'is_winner': False
            }
            competitors.append(competitor_data)
        
        # Find winner (lowest final amount)
        if competitors:
            min_bid = min(c['final_amount'] for c in competitors if c['final_amount'] > 0)
            for comp in competitors:
                if comp['final_amount'] == min_bid:
                    comp['is_winner'] = True
                    winner_info = comp
                    break
        
        parsed_data['competitors'] = competitors
        parsed_data['winner_info'] = winner_info
    
    def import_tender_data(self, company_id: int, tender_id: str, 
                          parsed_data: Dict) -> Tuple[bool, Dict]:
        """
        Import tender data into database
        Returns: (success, summary_dict)
        """
        summary = {
            'competitors_added': [],
            'competitors_updated': [],
            'bids_inserted': [],
            'errors': [],
            'winner': None,
            'tender_id': tender_id
        }
        
        try:
            # Check if tender already exists
            existing_tender = self.db.get_tender_by_id(tender_id)
            if existing_tender:
                summary['errors'].append(f"Tender {tender_id} already exists in database")
                return False, summary
            
            # Process each competitor
            for competitor_data in parsed_data['competitors']:
                comp_name = competitor_data['name'].strip().upper()
                
                # Check if competitor exists in master
                existing_comp = self._find_competitor_by_name(company_id, comp_name)
                
                if existing_comp:
                    # Update existing competitor stats
                    comp_id = existing_comp['id']
                    summary['competitors_updated'].append(comp_name)
                    
                    # Update stats
                    bid_ratio = competitor_data['final_amount'] / competitor_data['quoted_amount'] if competitor_data['quoted_amount'] > 0 else 0.95
                    self.db.update_competitor_stats_from_bid(
                        company_id, 
                        comp_name, 
                        bid_ratio, 
                        competitor_data['is_winner']
                    )
                else:
                    # Add new competitor to master
                    comp_data = {
                        'competitor_name': comp_name,
                        'business_type': self._guess_business_type(comp_name),
                        'preferred_strategy': 'Unknown',
                        'total_bids': 1,
                        'total_wins': 1 if competitor_data['is_winner'] else 0,
                        'avg_bid_ratio': competitor_data['final_amount'] / competitor_data['quoted_amount'] if competitor_data['quoted_amount'] > 0 else 0.95,
                        'first_seen': datetime.now().date(),
                        'last_seen': datetime.now().date()
                    }
                    comp_id = self.db.add_competitor_to_master(company_id, comp_data)
                    summary['competitors_added'].append(comp_name)
                
                # Insert bid history
                if comp_id:
                    bid_success = self.db.add_competitor_bid_history(
                        company_id=company_id,
                        competitor_name=comp_name,
                        tender_id=tender_id,
                        bid_amount=competitor_data['final_amount'],
                        official_estimate=competitor_data['quoted_amount'],
                        was_winner=competitor_data['is_winner'],
                        bid_date=datetime.now().date()
                    )
                    
                    if bid_success:
                        summary['bids_inserted'].append(comp_name)
                        if competitor_data['is_winner']:
                            summary['winner'] = comp_name
            
            return True, summary
            
        except Exception as e:
            st.error(f"Error importing data: {str(e)}")
            summary['errors'].append(str(e))
            return False, summary
    
    def _find_competitor_by_name(self, company_id: int, competitor_name: str) -> Optional[Dict]:
        """Find competitor in master list by name (case-insensitive)"""
        competitors = self.db.get_competitor_master_list(company_id, active_only=False)
        
        comp_name_upper = competitor_name.upper().strip()
        for comp in competitors:
            if comp['competitor_name'].upper().strip() == comp_name_upper:
                return comp
        return None
    
    def _guess_business_type(self, name: str) -> str:
        """Guess business type from company name"""
        name_upper = name.upper()
        
        if 'LIMITED' in name_upper or 'LTD' in name_upper:
            return 'Construction Company'
        elif 'TRADING' in name_upper or 'TRADERS' in name_upper:
            return 'Trading Company'
        elif 'JOINT VENTURE' in name_upper or 'JV' in name_upper:
            return 'Joint Venture'
        elif 'ENTERPRISE' in name_upper or 'CORPORATION' in name_upper:
            return 'Private Limited'
        else:
            return 'Other'
    
    def calculate_nppi_factor(self, winner_amount: float, official_estimate: float) -> float:
        """Calculate NPPI factor"""
        if official_estimate > 0:
            return (winner_amount / official_estimate) * 100
        return 0

def render_tender_importer_page(db: UnifiedDatabaseManager):
    """Render the tender data import page"""
    
    st.markdown("""
    <div class="main-header">
        <h1>📥 Import Tender Opening Report</h1>
        <p>Upload Excel file with tender opening report data</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize importer
    importer = TenderDataImporter(db)
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload Opening Report (Excel format)",
        type=['xlsx', 'xls'],
        help="Upload the opening report Excel file from e-GP or similar platform"
    )
    
    if uploaded_file is not None:
        try:
            # Read Excel file
            df = pd.read_excel(uploaded_file, header=None)
            
            # Parse the opening report
            with st.spinner("Parsing tender data..."):
                parsed_data = importer.parse_opening_report(df)
            
            if parsed_data['competitors']:
                st.success(f"✅ Found {len(parsed_data['competitors'])} competitors in the report")
                
                # Display parsed data
                st.subheader("📊 Parsed Data Preview")
                
                # Create display DataFrame
                display_data = []
                for comp in parsed_data['competitors']:
                    display_data.append({
                        'Competitor': comp['name'],
                        'Quoted Amount': f"BDT {comp['quoted_amount']:,.2f}",
                        'Discount %': f"{comp['discount_percentage']:.2f}%",
                        'Final Amount': f"BDT {comp['final_amount']:,.2f}",
                        'Winner': "🏆" if comp['is_winner'] else ""
                    })
                
                display_df = pd.DataFrame(display_data)
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Winner info
                if parsed_data['winner_info']:
                    winner = parsed_data['winner_info']
                    st.info(f"🏆 **Winner:** {winner['name']} with BDT {winner['final_amount']:,.2f}")
                    
                    # Calculate NPPI factor if official estimate available
                    official_estimate = st.number_input(
                        "Official Estimate (for NPPI calculation)",
                        min_value=0.0,
                        value=winner['quoted_amount'] * 1.2,  # Guess estimate
                        help="Enter the official estimate to calculate NPPI factor"
                    )
                    
                    if official_estimate > 0:
                        nppi_factor = (winner['final_amount'] / official_estimate) * 100
                        st.metric(
                            "NPPI Factor",
                            f"{nppi_factor:.2f}%",
                            help="Non-Price Performance Index factor"
                        )
                        
                        # NPPI interpretation
                        if nppi_factor < 85:
                            st.success("✅ NPPI Factor: **Excellent** (Below 85%)")
                        elif nppi_factor < 90:
                            st.info("ℹ️ NPPI Factor: **Good** (85-90%)")
                        elif nppi_factor < 95:
                            st.warning("⚠️ NPPI Factor: **Average** (90-95%)")
                        else:
                            st.error("❌ NPPI Factor: **High** (Above 95%)")
                
                # Import button
                tender_id = st.text_input(
                    "Tender ID",
                    value=parsed_data.get('tender_id', '') or st.text_input("Enter Tender ID", placeholder="e.g., 1295058"),
                    help="Enter the tender ID for reference"
                )
                
                if st.button("📥 Import Data to Database", type="primary", use_container_width=True):
                    if not tender_id:
                        st.error("Please enter a Tender ID")
                    else:
                        # Confirm import
                        with st.spinner("Importing data..."):
                            success, summary = importer.import_tender_data(
                                st.session_state.company_id,
                                tender_id,
                                parsed_data
                            )
                        
                        if success:
                            st.success("✅ Data imported successfully!")
                            
                            # Display summary
                            st.subheader("📋 Import Summary")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("New Competitors Added", len(summary['competitors_added']))
                            with col2:
                                st.metric("Competitors Updated", len(summary['competitors_updated']))
                            with col3:
                                st.metric("Bids Recorded", len(summary['bids_inserted']))
                            
                            if summary['competitors_added']:
                                with st.expander("🆕 New Competitors Added"):
                                    st.write("\n".join(summary['competitors_added']))
                            
                            if summary['competitors_updated']:
                                with st.expander("🔄 Existing Competitors Updated"):
                                    st.write("\n".join(summary['competitors_updated']))
                            
                            if summary['winner']:
                                st.success(f"🏆 Winner: **{summary['winner']}**")
                            
                            st.balloons()
                        else:
                            st.error("❌ Import failed")
                            if summary['errors']:
                                for error in summary['errors']:
                                    st.error(f"• {error}")
            else:
                st.warning("No competitor data found in the file. Please check the file format.")
                
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)
    
    # Help section
    with st.expander("ℹ️ How to use this importer"):
        st.markdown("""
        ### Supported File Format
        
        The importer expects Excel files (.xlsx, .xls) with the following structure:
        
        1. **Header row** containing: "Name of Tenderer", "Quoted Amount", "Discount in Percentage", etc.
        2. **Data rows** with competitor information
        3. **Footer** containing tender ID or summary information
        
        ### Data Processing
        
        - Competitors are matched by name (case-insensitive)
        - New competitors are added to the master list
        - Existing competitors are updated with new bid data
        - Winner is automatically identified (lowest final amount)
        - NPPI factor is calculated based on official estimate
        
        ### Tips
        
        - Ensure tender ID is unique to avoid duplicate imports
        - Official estimate should be from the tender document
        - Competitor names should be consistent for proper matching
        """)

# Integration with main app
if __name__ == "__main__":
    # For testing
    from database.unified_db_manager import UnifiedDatabaseManager
    db = UnifiedDatabaseManager()
    
    # Simulate session state
    st.session_state.company_id = 1
    st.session_state.user_id = 1
    
    render_tender_importer_page(db)