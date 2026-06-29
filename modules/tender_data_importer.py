"""
tender_data_importer.py
Module for importing tender data from Excel files with competitor management
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import re
from typing import Dict, Any, Optional, List, Tuple

from database.unified_db_manager import UnifiedDatabaseManager


# ============================================================
# Tender Data Importer Class
# ============================================================

class TenderDataImporter:
    """Handles import of tender data from Excel files"""
    
    def __init__(self, db_manager: UnifiedDatabaseManager):
        self.db = db_manager
    
    def parse_opening_report(self, df: pd.DataFrame) -> Dict:
        """
        Parse the opening report format with headers and footers
        Supports multiple formats including e-GP format
        """
        result = {
            'tender_id': None,
            'data_rows': [],
            'winner_info': None,
            'competitors': []
        }
        
        # Debug: Print first few rows to see what we're working with
        st.write("### Debug: First 5 rows of the file")
        debug_df = df.head(10).copy()
        debug_df.columns = [f"Col_{i}" for i in range(len(debug_df.columns))]
        st.dataframe(debug_df)
        
        # Find the header row - look for "Name of Tenderer" or "Competitor"
        header_row_idx = None
        for idx, row in df.iterrows():
            row_values = [str(val).strip() for val in row.values if pd.notna(val)]
            row_str = ' '.join(row_values)
            row_str_lower = row_str.lower()
            
            # Check for various header patterns
            if ('name of tenderer' in row_str_lower or 'competitor' in row_str_lower) and \
            ('quoted amount' in row_str_lower or 'amount' in row_str_lower):
                header_row_idx = idx
                st.write(f"✅ Found header at row {idx}: {row_values[:5]}")
                break
        
        # If not found, try a more lenient approach
        if header_row_idx is None:
            for idx, row in df.iterrows():
                row_values = [str(val).strip() for val in row.values if pd.notna(val)]
                row_str = ' '.join(row_values).lower()
                
                # Check for common header keywords
                header_keywords = ['name', 'tenderer', 'competitor', 'amount', 'discount', 'price', 'bid']
                found_keywords = [kw for kw in header_keywords if kw in row_str]
                if len(found_keywords) >= 3:  # If we find at least 3 keywords
                    header_row_idx = idx
                    st.write(f"✅ Found header at row {idx} (lenient): {row_values[:5]}")
                    break
        
        if header_row_idx is None:
            st.error("Could not find header row in the file")
            st.info("Expected header with: 'Name of Tenderer', 'Quoted Amount', 'Discount %', etc.")
            st.info("Please ensure the file is in the correct format.")
            return result
        
        # Get column names from header row
        header_row = df.iloc[header_row_idx]
        columns = []
        for col in header_row:
            if pd.notna(col):
                columns.append(str(col).strip())
        
        st.write(f"📋 Header columns found: {columns}")
        
        # Find data rows (after header)
        data_start = header_row_idx + 1
        data_end = len(df)
        
        # Look for footer or empty rows
        for idx in range(data_start, len(df)):
            row = df.iloc[idx]
            row_values = [str(val).strip() for val in row.values if pd.notna(val)]
            row_str = ' '.join(row_values).lower()
            
            # Stop if we hit a footer or empty row
            if not row_str.strip() or 'footer' in row_str or 'total' in row_str:
                data_end = idx
                break
        
        # Extract data rows
        data_rows = []
        for idx in range(data_start, data_end):
            row = df.iloc[idx]
            # Check if row has any non-empty value
            if any(pd.notna(val) and str(val).strip() != '' for val in row):
                data_rows.append(row)
        
        st.write(f"📊 Found {len(data_rows)} data rows")
        
        if data_rows:
            st.write("📋 Sample data row:", [str(val)[:30] for val in data_rows[0].values if pd.notna(val)])
        
        result['data_rows'] = data_rows
        result['header_columns'] = columns
        
        # Parse the data
        self._parse_competitor_data_full(result)
        
        return result

    def _parse_competitor_data_full(self, parsed_data: Dict):
        """Parse competitor data with optional manual winner override"""
        competitors = []
        winner_info = None
        
        # ... existing column detection code ...
        
        columns = parsed_data.get('header_columns', [])
        data_rows = parsed_data.get('data_rows', [])
        
        if not data_rows:
            st.warning("No data rows found to parse")
            parsed_data['competitors'] = competitors
            parsed_data['winner_info'] = winner_info
            return
        
        # Identify column indices based on the exact format
        name_col = None
        quoted_col = None
        discount_pct_col = None
        discount_amount_col = None
        final_col = None
        winner_col = None
        
        for idx, col in enumerate(columns):
            col_lower = col.lower()
            
            # Name column
            if 'name of tenderer' in col_lower or 'tenderer' in col_lower or 'competitor' in col_lower:
                name_col = idx
            # Quoted amount without discount
            elif 'quoted amount' in col_lower and 'without discount' in col_lower:
                quoted_col = idx
            elif 'quoted amount' in col_lower and 'without' in col_lower:
                quoted_col = idx
            # Discount percentage
            elif 'discount in percentage' in col_lower or 'discount %' in col_lower or 'discount percentage' in col_lower:
                discount_pct_col = idx
            # Discount amount
            elif 'discount in amount' in col_lower:
                discount_amount_col = idx
            # Final amount with discount
            elif 'quoted amount' in col_lower and 'with discount' in col_lower:
                final_col = idx
            elif 'amount' in col_lower and 'discount' in col_lower and final_col is None:
                final_col = idx
            # Winner column
            elif 'winner' in col_lower or 'win' in col_lower:
                winner_col = idx
        
        # Fallback: use position-based detection
        if name_col is None:
            # Try to find by position
            if len(columns) > 1:
                name_col = 1  # Column B
            else:
                name_col = 0
        
        if quoted_col is None:
            if len(columns) > 2:
                quoted_col = 2  # Column C
            else:
                quoted_col = 1
        
        if discount_pct_col is None:
            if len(columns) > 3:
                discount_pct_col = 3  # Column D
            else:
                discount_pct_col = 2
        
        if discount_amount_col is None:
            if len(columns) > 4:
                discount_amount_col = 4  # Column E
            else:
                discount_amount_col = 3
        
        if final_col is None:
            if len(columns) > 5:
                final_col = 5  # Column F
            else:
                final_col = 4
        
        if winner_col is None:
            if len(columns) > 6:
                winner_col = 6  # Column G
            else:
                winner_col = len(columns) - 1  # Last column
        
        st.write(f"🔍 Column mapping: Name={name_col}, Quoted={quoted_col}, Discount%={discount_pct_col}, DiscountAmt={discount_amount_col}, Final={final_col}, Winner={winner_col}")

        for idx, row in enumerate(data_rows):
            # Ensure row has enough columns
            if len(row) <= max(name_col, quoted_col, final_col):
                st.write(f"⚠️ Row {idx} has only {len(row)} columns, skipping")
                continue
                
            competitor_name = str(row.iloc[name_col]).strip()
            if not competitor_name or competitor_name in ['Name of Tenderer', 'S. No', '']:
                continue
            
            # Skip serial number rows
            if re.match(r'^\d+$', competitor_name):
                continue
            
            # Parse numeric values
            try:
                quoted_amount = float(row.iloc[quoted_col]) if pd.notna(row.iloc[quoted_col]) else 0
            except (ValueError, TypeError):
                quoted_amount = 0
                
            try:
                discount_pct = float(row.iloc[discount_pct_col]) if pd.notna(row.iloc[discount_pct_col]) else 0
            except (ValueError, TypeError):
                discount_pct = 0
                
            try:
                discount_amount = float(row.iloc[discount_amount_col]) if pd.notna(row.iloc[discount_amount_col]) else 0
            except (ValueError, TypeError):
                discount_amount = 0
                
            try:
                final_amount = float(row.iloc[final_col]) if pd.notna(row.iloc[final_col]) else 0
            except (ValueError, TypeError):
                final_amount = 0
            
            # If final_amount is 0 but we have quoted and discount, calculate it
            if final_amount == 0 and quoted_amount > 0 and discount_pct > 0:
                final_amount = quoted_amount - (quoted_amount * discount_pct / 100)
            elif final_amount == 0 and quoted_amount > 0:
                final_amount = quoted_amount
            
            # Check if winner
            is_winner = False
            if winner_col is not None and winner_col < len(row):
                winner_val = str(row.iloc[winner_col]).strip().lower()
                is_winner = winner_val in ['yes', 'y', 'true', 'winner', '1', '🏆']
            

            competitor_data = {
                'name': competitor_name,
                'quoted_amount': quoted_amount,
                'discount_percentage': discount_pct,
                'discount_amount': discount_amount,
                'final_amount': final_amount,
                'is_winner': is_winner,          # from Excel column
                'original_row': idx + 1
            }
            competitors.append(competitor_data)
            
            if is_winner:
                winner_info = competitor_data

        # ================== IMPROVED WINNER LOGIC ==================
        explicit_winner = any(c['is_winner'] for c in competitors)
        
        if not explicit_winner:
            st.warning("⚠️ No winner marked in Excel. Lowest bidder will be used as default.")
            
            # Ask user to confirm or change winner
            valid_competitors = [c for c in competitors if c['final_amount'] > 0]
            if valid_competitors:
                min_bid = min(c['final_amount'] for c in valid_competitors)
                default_winner = next((c for c in competitors if c['final_amount'] == min_bid), None)
                
                st.subheader("🏆 Winner Selection")
                winner_options = [c['name'] for c in competitors]
                selected_winner_name = st.selectbox(
                    "Select Winner (or leave as lowest bidder)",
                    options=winner_options,
                    index=winner_options.index(default_winner['name']) if default_winner else 0
                )
                
                # Apply selected winner
                for c in competitors:
                    c['is_winner'] = (c['name'] == selected_winner_name)
                    if c['is_winner']:
                        winner_info = c
        else:
            st.success("✅ Winner found in Excel file")

        parsed_data['competitors'] = competitors
        parsed_data['winner_info'] = winner_info
        
    def _parse_competitor_data_full_bak2(self, parsed_data: Dict):
        """Parse competitor data from the full opening report format"""
        competitors = []
        winner_info = None
        
        columns = parsed_data.get('header_columns', [])
        data_rows = parsed_data.get('data_rows', [])
        
        if not data_rows:
            st.warning("No data rows found to parse")
            parsed_data['competitors'] = competitors
            parsed_data['winner_info'] = winner_info
            return
        
        # Identify column indices based on the exact format
        name_col = None
        quoted_col = None
        discount_pct_col = None
        discount_amount_col = None
        final_col = None
        winner_col = None
        
        for idx, col in enumerate(columns):
            col_lower = col.lower()
            
            # Name column
            if 'name of tenderer' in col_lower or 'tenderer' in col_lower or 'competitor' in col_lower:
                name_col = idx
            # Quoted amount without discount
            elif 'quoted amount' in col_lower and 'without discount' in col_lower:
                quoted_col = idx
            elif 'quoted amount' in col_lower and 'without' in col_lower:
                quoted_col = idx
            # Discount percentage
            elif 'discount in percentage' in col_lower or 'discount %' in col_lower or 'discount percentage' in col_lower:
                discount_pct_col = idx
            # Discount amount
            elif 'discount in amount' in col_lower:
                discount_amount_col = idx
            # Final amount with discount
            elif 'quoted amount' in col_lower and 'with discount' in col_lower:
                final_col = idx
            elif 'amount' in col_lower and 'discount' in col_lower and final_col is None:
                final_col = idx
            # Winner column
            elif 'winner' in col_lower or 'win' in col_lower:
                winner_col = idx
        
        # Fallback: use position-based detection
        if name_col is None:
            # Try to find by position
            if len(columns) > 1:
                name_col = 1  # Column B
            else:
                name_col = 0
        
        if quoted_col is None:
            if len(columns) > 2:
                quoted_col = 2  # Column C
            else:
                quoted_col = 1
        
        if discount_pct_col is None:
            if len(columns) > 3:
                discount_pct_col = 3  # Column D
            else:
                discount_pct_col = 2
        
        if discount_amount_col is None:
            if len(columns) > 4:
                discount_amount_col = 4  # Column E
            else:
                discount_amount_col = 3
        
        if final_col is None:
            if len(columns) > 5:
                final_col = 5  # Column F
            else:
                final_col = 4
        
        if winner_col is None:
            if len(columns) > 6:
                winner_col = 6  # Column G
            else:
                winner_col = len(columns) - 1  # Last column
        
        st.write(f"🔍 Column mapping: Name={name_col}, Quoted={quoted_col}, Discount%={discount_pct_col}, DiscountAmt={discount_amount_col}, Final={final_col}, Winner={winner_col}")
        
        for idx, row in enumerate(data_rows):
            # Ensure row has enough columns
            if len(row) <= max(name_col, quoted_col, final_col):
                st.write(f"⚠️ Row {idx} has only {len(row)} columns, skipping")
                continue
                
            competitor_name = str(row.iloc[name_col]).strip()
            if not competitor_name or competitor_name in ['Name of Tenderer', 'S. No', '']:
                continue
            
            # Skip serial number rows
            if re.match(r'^\d+$', competitor_name):
                continue
            
            # Parse numeric values
            try:
                quoted_amount = float(row.iloc[quoted_col]) if pd.notna(row.iloc[quoted_col]) else 0
            except (ValueError, TypeError):
                quoted_amount = 0
                
            try:
                discount_pct = float(row.iloc[discount_pct_col]) if pd.notna(row.iloc[discount_pct_col]) else 0
            except (ValueError, TypeError):
                discount_pct = 0
                
            try:
                discount_amount = float(row.iloc[discount_amount_col]) if pd.notna(row.iloc[discount_amount_col]) else 0
            except (ValueError, TypeError):
                discount_amount = 0
                
            try:
                final_amount = float(row.iloc[final_col]) if pd.notna(row.iloc[final_col]) else 0
            except (ValueError, TypeError):
                final_amount = 0
            
            # If final_amount is 0 but we have quoted and discount, calculate it
            if final_amount == 0 and quoted_amount > 0 and discount_pct > 0:
                final_amount = quoted_amount - (quoted_amount * discount_pct / 100)
            elif final_amount == 0 and quoted_amount > 0:
                final_amount = quoted_amount
            
            # Check if winner
            is_winner = False
            if winner_col is not None and winner_col < len(row):
                winner_val = str(row.iloc[winner_col]).strip().lower()
                is_winner = winner_val in ['yes', 'y', 'true', 'winner', '1', '🏆']
            
            competitor_data = {
                'name': competitor_name,
                'quoted_amount': quoted_amount,
                'discount_percentage': discount_pct,
                'discount_amount': discount_amount,
                'final_amount': final_amount,
                'is_winner': is_winner
            }
            competitors.append(competitor_data)
            
            if is_winner:
                winner_info = competitor_data
        
        # If no winner was marked, find winner (lowest final amount)
        if not any(c['is_winner'] for c in competitors):
            valid_competitors = [c for c in competitors if c['final_amount'] > 0]
            if valid_competitors:
                min_bid = min(c['final_amount'] for c in valid_competitors)
                for comp in competitors:
                    if comp['final_amount'] == min_bid:
                        comp['is_winner'] = True
                        winner_info = comp
                        break
        
        st.write(f"✅ Parsed {len(competitors)} competitors")
        if winner_info:
            st.write(f"🏆 Winner: {winner_info['name']} - BDT {winner_info['final_amount']:,.2f}")
        
        parsed_data['competitors'] = competitors
        parsed_data['winner_info'] = winner_info
        
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
            valid_competitors = [c for c in competitors if c['final_amount'] > 0]
            if valid_competitors:
                min_bid = min(c['final_amount'] for c in valid_competitors)
                for comp in competitors:
                    if comp['final_amount'] == min_bid:
                        comp['is_winner'] = True
                        winner_info = comp
                        break
        
        parsed_data['competitors'] = competitors
        parsed_data['winner_info'] = winner_info
    
    
    def import_tender_data(self, company_id: int, tender_id: str, 
                      parsed_data: Dict, tender_data: Dict = None,
                      replace_existing: bool = False) -> Tuple[bool, Dict]:
        """
        Import tender data into database using batch operations
        Updates: competitor_master, competitor_bid_history, company_tenders
        
        Args:
            company_id: Company ID
            tender_id: Tender ID
            parsed_data: Parsed competitor data
            tender_data: Optional tender data
            replace_existing: If True, delete existing data before import
        
        Returns:
            Tuple[bool, Dict]: (success, summary_dict)
        """
        summary = {
            'competitors_added': [],
            'competitors_updated': [],
            'bids_inserted': [],
            'bids_deleted': 0,
            'company_tender_updated': False,
            'historical_tender_updated': False,
            'errors': [],
            'warnings': [],
            'winner': None,
            'winner_amount': None,
            'tender_id': tender_id,
            'total_competitors': len(parsed_data.get('competitors', [])),
            'replace_mode': replace_existing
        }
        
        try:
            # Validate parsed data
            if not parsed_data or not parsed_data.get('competitors'):
                summary['errors'].append("No competitor data to import")
                return False, summary
            
            competitors = parsed_data['competitors']
            st.info(f"📊 Processing {len(competitors)} competitors for import...")
            
            # ===== GET WINNER INFO - ONLY IF EXPLICITLY MARKED =====
            has_winner = any(comp.get('is_winner', False) for comp in competitors)
            winner_info = parsed_data.get('winner_info')
            
            if has_winner and winner_info:
                summary['winner'] = winner_info['name']
                summary['winner_amount'] = winner_info['final_amount']
                winner_type = self._guess_business_type(winner_info['name'])
                st.info(f"🏆 Winner: {summary['winner']} with BDT {summary['winner_amount']:,.2f}")
            else:
                # No winner - ensure all competitors have is_winner = False
                for comp in competitors:
                    comp['is_winner'] = False
                summary['winner'] = None
                summary['winner_amount'] = None
                winner_type = ''
                st.info("ℹ️ No winner selected. All competitors will have was_winner = 0.")
            
            # If no tender_data provided, try to fetch it
            if not tender_data:
                tender_data = self.db.get_tender_by_id(tender_id)
                if not tender_data:
                    st.warning(f"⚠️ No tender data found for {tender_id}, using minimal data")
                    tender_data = {
                        'tender_id': tender_id,
                        'tender_title': f'Tender {tender_id}',
                        'official_estimate': 0,
                        'procurement_type': 'LTM',
                        'procuring_entity': ''
                    }
            
            # Use a single connection for all operations
            with self.db.get_connection() as conn:
                cursor = self.db.db_conn.get_cursor(conn)
                
                # Begin transaction
                cursor.execute("BEGIN TRANSACTION")
                
                try:
                    # ===== CHECK EXISTING DATA =====
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM competitor_bid_history 
                        WHERE tender_id = ? AND company_id = ?
                    """, (tender_id, company_id))
                    existing_count = cursor.fetchone()['count']
                    
                    # ===== HANDLE REPLACE MODE =====
                    if existing_count > 0:
                        if replace_existing:
                            # Delete existing bid history for this tender
                            cursor.execute("""
                                DELETE FROM competitor_bid_history 
                                WHERE tender_id = ? AND company_id = ?
                            """, (tender_id, company_id))
                            summary['bids_deleted'] = existing_count
                            st.warning(f"🗑️ Deleted {existing_count} existing bid records for tender {tender_id}")
                        else:
                            st.info(f"ℹ️ Found {existing_count} existing bid records. Will skip duplicates.")
                    
                    # ===== GET EXISTING COMPETITORS =====
                    cursor.execute("""
                        SELECT competitor_name FROM competitor_master 
                        WHERE company_id = ?
                    """, (company_id,))
                    existing_competitors = {row['competitor_name'] for row in cursor.fetchall()}
                    
                    # ===== PREPARE DATA FOR BATCH OPERATIONS =====
                    bid_history_to_insert = []
                    competitors_updated_count = 0
                    competitors_added_count = 0
                    skipped_duplicates = 0
                    
                    # Get existing bids to check for duplicates
                    existing_bids = set()
                    if not replace_existing:
                        cursor.execute("""
                            SELECT competitor_name FROM competitor_bid_history 
                            WHERE tender_id = ? AND company_id = ?
                        """, (tender_id, company_id))
                        existing_bids = {row['competitor_name'] for row in cursor.fetchall()}
                    
                    for idx, competitor_data in enumerate(competitors):
                        comp_name = competitor_data.get('name', '').strip().upper()
                        
                        # Validate competitor data
                        if not comp_name:
                            summary['warnings'].append(f"Row {idx+1}: Empty competitor name, skipping")
                            continue
                        
                        # Skip if bid already exists (when not in replace mode)
                        if comp_name in existing_bids and not replace_existing:
                            skipped_duplicates += 1
                            summary['warnings'].append(f"Row {idx+1}: Bid for '{comp_name}' already exists, skipping")
                            continue
                        
                        # Skip if amount is 0 or invalid
                        final_amount = competitor_data.get('final_amount', 0)
                        if final_amount <= 0:
                            summary['warnings'].append(f"Row {idx+1}: Invalid final amount for {comp_name}, skipping")
                            continue
                        
                        quoted_amount = competitor_data.get('quoted_amount', 0)
                        is_winner = competitor_data.get('is_winner', False)
                        
                        # Calculate bid ratio safely
                        if quoted_amount > 0 and final_amount > 0:
                            bid_ratio = final_amount / quoted_amount
                        else:
                            bid_ratio = 0.95
                        
                        # ===== PROCESS COMPETITOR =====
                        if comp_name in existing_competitors:
                            # Update existing competitor
                            cursor.execute("""
                                SELECT id, total_bids, total_wins, avg_bid_ratio 
                                FROM competitor_master 
                                WHERE company_id = ? AND competitor_name = ?
                            """, (company_id, comp_name))
                            
                            existing = cursor.fetchone()
                            if existing:
                                total_bids = existing['total_bids'] if existing['total_bids'] is not None else 0
                                total_wins = existing['total_wins'] if existing['total_wins'] is not None else 0
                                avg_ratio = existing['avg_bid_ratio'] if existing['avg_bid_ratio'] is not None else 0.90
                                
                                new_total_bids = total_bids + 1
                                new_total_wins = total_wins + (1 if is_winner else 0)
                                
                                # Calculate new average safely
                                if total_bids > 0:
                                    new_avg_ratio = ((avg_ratio * total_bids) + bid_ratio) / new_total_bids
                                else:
                                    new_avg_ratio = bid_ratio
                                
                                # Update competitor_master
                                cursor.execute("""
                                    UPDATE competitor_master 
                                    SET total_bids = ?, total_wins = ?, avg_bid_ratio = ?,
                                        last_seen = ?, updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                """, (new_total_bids, new_total_wins, new_avg_ratio, 
                                    datetime.now().date(), existing['id']))
                                
                                summary['competitors_updated'].append(comp_name)
                                competitors_updated_count += 1
                        else:
                            # Insert new competitor
                            cursor.execute("""
                                INSERT OR IGNORE INTO competitor_master (
                                    company_id, competitor_name, total_bids, total_wins, 
                                    avg_bid_ratio, first_seen, last_seen, is_active,
                                    preferred_strategy, notes
                                ) VALUES (?, ?, 1, ?, ?, ?, ?, 1, ?, ?)
                            """, (company_id, comp_name, 1 if is_winner else 0, 
                                bid_ratio, datetime.now().date(), datetime.now().date(),
                                'Unknown', f'Auto-imported from tender {tender_id}'))
                            
                            if cursor.rowcount > 0:
                                summary['competitors_added'].append(comp_name)
                                existing_competitors.add(comp_name)
                                competitors_added_count += 1
                            else:
                                # Competitor exists - update it
                                cursor.execute("""
                                    SELECT id, total_bids, total_wins, avg_bid_ratio 
                                    FROM competitor_master 
                                    WHERE company_id = ? AND competitor_name = ?
                                """, (company_id, comp_name))
                                
                                existing = cursor.fetchone()
                                if existing:
                                    total_bids = existing['total_bids'] if existing['total_bids'] is not None else 0
                                    total_wins = existing['total_wins'] if existing['total_wins'] is not None else 0
                                    avg_ratio = existing['avg_bid_ratio'] if existing['avg_bid_ratio'] is not None else 0.90
                                    
                                    new_total_bids = total_bids + 1
                                    new_total_wins = total_wins + (1 if is_winner else 0)
                                    
                                    if total_bids > 0:
                                        new_avg_ratio = ((avg_ratio * total_bids) + bid_ratio) / new_total_bids
                                    else:
                                        new_avg_ratio = bid_ratio
                                    
                                    cursor.execute("""
                                        UPDATE competitor_master 
                                        SET total_bids = ?, total_wins = ?, avg_bid_ratio = ?,
                                            last_seen = ?, updated_at = CURRENT_TIMESTAMP
                                        WHERE id = ?
                                    """, (new_total_bids, new_total_wins, new_avg_ratio, 
                                        datetime.now().date(), existing['id']))
                                    
                                    summary['competitors_updated'].append(comp_name)
                                    competitors_updated_count += 1
                        
                        # ===== PREPARE BID HISTORY INSERTION =====
                        bid_history_to_insert.append((
                            company_id,
                            comp_name,
                            tender_id,
                            final_amount,
                            quoted_amount,
                            bid_ratio,
                            1 if is_winner else 0,
                            datetime.now().date(),
                            datetime.now()
                        ))
                    
                    # ===== BATCH INSERT BID HISTORY =====
                    if bid_history_to_insert:
                        cursor.executemany("""
                            INSERT INTO competitor_bid_history (
                                company_id, competitor_name, tender_id, bid_amount,
                                official_estimate, bid_ratio, was_winner, bid_date, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, bid_history_to_insert)
                        
                        summary['bids_inserted'] = [item[1] for item in bid_history_to_insert]
                        st.success(f"✅ Recorded {len(bid_history_to_insert)} bid history entries")
                        if skipped_duplicates > 0:
                            st.warning(f"⚠️ Skipped {skipped_duplicates} duplicate bid entries")
                    
                    # ===== COMMIT TRANSACTION =====
                    cursor.execute("COMMIT")
                    
                    st.success(f"✅ Processed: {competitors_added_count} new, {competitors_updated_count} updated")
                    
                except Exception as e:
                    cursor.execute("ROLLBACK")
                    raise e
            
            # ===== UPDATE company_tenders TABLE =====
            if summary['winner']:
                try:
                    update_data = {
                        'winning_competitor': summary['winner'],
                        'winning_bid_amount': summary['winner_amount'],
                        'total_bidders': len(competitors),
                        'evaluation_status': 'completed'
                    }
                    
                    update_success = self._update_company_tender(tender_id, update_data)
                    if update_success:
                        summary['company_tender_updated'] = True
                        st.success("✅ Company tender updated with winner info")
                    else:
                        summary['warnings'].append("Failed to update company_tenders")
                except Exception as e:
                    summary['warnings'].append(f"Error updating company tender: {str(e)}")
            else:
                # Clear any existing winner from company_tenders
                try:
                    with self.db.get_connection() as conn:
                        cursor = self.db.db_conn.get_cursor(conn)
                        cursor.execute("""
                            UPDATE company_tenders 
                            SET winning_competitor = NULL,
                                winning_bid_amount = NULL,
                                evaluation_status = 'completed',
                                updated_at = ?
                            WHERE tender_id = ?
                        """, (datetime.now(), tender_id))
                        conn.commit()
                        st.info("ℹ️ Cleared winner from company tender record")
                except Exception as e:
                    summary['warnings'].append(f"Could not clear winner: {str(e)}")
            
            # ===== FINAL SUMMARY =====
            if summary['errors']:
                st.warning(f"⚠️ Import completed with {len(summary['errors'])} errors")
                for err in summary['errors']:
                    st.error(f"❌ {err}")
            
            if summary['warnings']:
                st.warning(f"⚠️ Import completed with {len(summary['warnings'])} warnings")
                for warn in summary['warnings']:
                    st.caption(f"⚠️ {warn}")
            
            if not summary['errors'] and not summary['warnings']:
                st.success("✅ Import completed successfully with no errors or warnings!")
            
            # Show detailed summary
            with st.expander("📊 Import Summary", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Competitors", summary['total_competitors'])
                with col2:
                    st.metric("New Competitors", len(summary['competitors_added']))
                with col3:
                    st.metric("Updated Competitors", len(summary['competitors_updated']))
                with col4:
                    st.metric("Bids Inserted", len(summary['bids_inserted']))
                
                if summary['bids_deleted'] > 0:
                    st.warning(f"🗑️ Deleted {summary['bids_deleted']} existing bids (replace mode)")
                
                if summary['winner']:
                    st.success(f"🏆 Winner: {summary['winner']} - BDT {summary['winner_amount']:,.2f}")
                else:
                    st.info("ℹ️ No winner was marked (all competitors have was_winner = 0)")
                
                if summary['errors']:
                    st.error("⚠️ Errors occurred during import:")
                    for err in summary['errors']:
                        st.code(err)
            
            return True, summary
            
        except Exception as e:
            error_msg = f"Critical error during import: {str(e)}"
            st.error(error_msg)
            summary['errors'].append(error_msg)
            import traceback
            st.code(traceback.format_exc())
            return False, summary
            
    def import_tender_data_bak4(self, company_id: int, tender_id: str, 
                      parsed_data: Dict, tender_data: Dict = None,
                      replace_existing: bool = False) -> Tuple[bool, Dict]:
        """
        Import tender data into database using batch operations
        Updates: competitor_master, competitor_bid_history, company_tenders, historical_tenders
        
        Args:
            company_id: Company ID
            tender_id: Tender ID
            parsed_data: Parsed competitor data
            tender_data: Optional tender data
            replace_existing: If True, delete existing data before import
        
        Returns:
            Tuple[bool, Dict]: (success, summary_dict)
        """
        summary = {
            'competitors_added': [],
            'competitors_updated': [],
            'bids_inserted': [],
            'bids_deleted': 0,
            'company_tender_updated': False,
            'historical_tender_updated': False,
            'errors': [],
            'warnings': [],
            'winner': None,
            'winner_amount': None,
            'tender_id': tender_id,
            'total_competitors': len(parsed_data.get('competitors', [])),
            'replace_mode': replace_existing
        }
        
        try:
            # Validate parsed data
            if not parsed_data or not parsed_data.get('competitors'):
                summary['errors'].append("No competitor data to import")
                return False, summary
            
            competitors = parsed_data['competitors']
            st.info(f"📊 Processing {len(competitors)} competitors for import...")
            
            # Get the winner info
            winner_info = parsed_data.get('winner_info')
            if winner_info:
                summary['winner'] = winner_info['name']
                summary['winner_amount'] = winner_info['final_amount']
                winner_type = self._guess_business_type(winner_info['name'])
                st.info(f"🏆 Winner detected: {summary['winner']} with BDT {summary['winner_amount']:,.2f}")
            else:
                st.warning("⚠️ No winner detected in the data")
            
            # If no tender_data provided, try to fetch it
            if not tender_data:
                tender_data = self.db.get_tender_by_id(tender_id)
                if tender_data:
                    st.info(f"📋 Found tender data for {tender_id}")
                else:
                    st.warning(f"⚠️ No tender data found for {tender_id}, using minimal data")
                    tender_data = {
                        'tender_id': tender_id,
                        'tender_title': f'Tender {tender_id}',
                        'official_estimate': 0,
                        'procurement_type': 'LTM',
                        'procuring_entity': ''
                    }
            
            # Use a single connection for all operations
            with self.db.get_connection() as conn:
                cursor = self.db.db_conn.get_cursor(conn)
                
                # Begin transaction
                cursor.execute("BEGIN TRANSACTION")
                
                try:
                    # ===== CHECK EXISTING DATA =====
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM competitor_bid_history 
                        WHERE tender_id = ? AND company_id = ?
                    """, (tender_id, company_id))
                    existing_count = cursor.fetchone()['count']
                    
                    # ===== HANDLE REPLACE MODE =====
                    if existing_count > 0:
                        if replace_existing:
                            # Delete existing bid history for this tender
                            cursor.execute("""
                                DELETE FROM competitor_bid_history 
                                WHERE tender_id = ? AND company_id = ?
                            """, (tender_id, company_id))
                            summary['bids_deleted'] = existing_count
                            st.warning(f"🗑️ Deleted {existing_count} existing bid records for tender {tender_id}")
                        else:
                            # Check if we should skip duplicate bids
                            st.info(f"ℹ️ Found {existing_count} existing bid records. Will skip duplicates.")
                    
                    # ===== GET EXISTING COMPETITORS =====
                    cursor.execute("""
                        SELECT competitor_name FROM competitor_master 
                        WHERE company_id = ?
                    """, (company_id,))
                    existing_competitors = {row['competitor_name'] for row in cursor.fetchall()}
                    
                    # ===== PREPARE DATA FOR BATCH OPERATIONS =====
                    bid_history_to_insert = []
                    competitors_updated_count = 0
                    competitors_added_count = 0
                    skipped_duplicates = 0
                    
                    # Get existing bids to check for duplicates
                    existing_bids = set()
                    if not replace_existing:
                        cursor.execute("""
                            SELECT competitor_name FROM competitor_bid_history 
                            WHERE tender_id = ? AND company_id = ?
                        """, (tender_id, company_id))
                        existing_bids = {row['competitor_name'] for row in cursor.fetchall()}
                    
                    for idx, competitor_data in enumerate(competitors):
                        comp_name = competitor_data.get('name', '').strip().upper()
                        
                        # Validate competitor data
                        if not comp_name:
                            summary['warnings'].append(f"Row {idx+1}: Empty competitor name, skipping")
                            continue
                        
                        # Skip if bid already exists (when not in replace mode)
                        if comp_name in existing_bids and not replace_existing:
                            skipped_duplicates += 1
                            summary['warnings'].append(f"Row {idx+1}: Bid for '{comp_name}' already exists, skipping")
                            continue
                        
                        # Skip if amount is 0 or invalid
                        final_amount = competitor_data.get('final_amount', 0)
                        if final_amount <= 0:
                            summary['warnings'].append(f"Row {idx+1}: Invalid final amount for {comp_name}, skipping")
                            continue
                        
                        quoted_amount = competitor_data.get('quoted_amount', 0)
                        is_winner = competitor_data.get('is_winner', False)
                        
                        # Calculate bid ratio safely
                        if quoted_amount > 0 and final_amount > 0:
                            bid_ratio = final_amount / quoted_amount
                        else:
                            bid_ratio = 0.95
                        
                        # ===== PROCESS COMPETITOR =====
                        comp_id = None
                        if comp_name in existing_competitors:
                            # Update existing competitor
                            cursor.execute("""
                                SELECT id, total_bids, total_wins, avg_bid_ratio 
                                FROM competitor_master 
                                WHERE company_id = ? AND competitor_name = ?
                            """, (company_id, comp_name))
                            
                            existing = cursor.fetchone()
                            if existing:
                                comp_id = existing['id']
                                total_bids = existing['total_bids'] if existing['total_bids'] is not None else 0
                                total_wins = existing['total_wins'] if existing['total_wins'] is not None else 0
                                avg_ratio = existing['avg_bid_ratio'] if existing['avg_bid_ratio'] is not None else 0.90
                                
                                new_total_bids = total_bids + 1
                                new_total_wins = total_wins + (1 if is_winner else 0)
                                
                                # Calculate new average safely
                                if total_bids > 0:
                                    new_avg_ratio = ((avg_ratio * total_bids) + bid_ratio) / new_total_bids
                                else:
                                    new_avg_ratio = bid_ratio
                                
                                # Update competitor_master
                                cursor.execute("""
                                    UPDATE competitor_master 
                                    SET total_bids = ?, total_wins = ?, avg_bid_ratio = ?,
                                        last_seen = ?, updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                """, (new_total_bids, new_total_wins, new_avg_ratio, 
                                    datetime.now().date(), comp_id))
                                
                                summary['competitors_updated'].append(comp_name)
                                competitors_updated_count += 1
                        else:
                            # Insert new competitor using INSERT OR IGNORE to avoid duplicates
                            cursor.execute("""
                                INSERT OR IGNORE INTO competitor_master (
                                    company_id, competitor_name, total_bids, total_wins, 
                                    avg_bid_ratio, first_seen, last_seen, is_active,
                                    preferred_strategy, notes
                                ) VALUES (?, ?, 1, ?, ?, ?, ?, 1, ?, ?)
                            """, (company_id, comp_name, 1 if is_winner else 0, 
                                bid_ratio, datetime.now().date(), datetime.now().date(),
                                'Unknown', f'Auto-imported from tender {tender_id}'))
                            
                            # Check if the insert was successful
                            if cursor.rowcount > 0:
                                summary['competitors_added'].append(comp_name)
                                existing_competitors.add(comp_name)
                                competitors_added_count += 1
                            else:
                                # The competitor was inserted by another process
                                # Try to get it and update instead
                                cursor.execute("""
                                    SELECT id, total_bids, total_wins, avg_bid_ratio 
                                    FROM competitor_master 
                                    WHERE company_id = ? AND competitor_name = ?
                                """, (company_id, comp_name))
                                
                                existing = cursor.fetchone()
                                if existing:
                                    comp_id = existing['id']
                                    total_bids = existing['total_bids'] if existing['total_bids'] is not None else 0
                                    total_wins = existing['total_wins'] if existing['total_wins'] is not None else 0
                                    avg_ratio = existing['avg_bid_ratio'] if existing['avg_bid_ratio'] is not None else 0.90
                                    
                                    new_total_bids = total_bids + 1
                                    new_total_wins = total_wins + (1 if is_winner else 0)
                                    
                                    if total_bids > 0:
                                        new_avg_ratio = ((avg_ratio * total_bids) + bid_ratio) / new_total_bids
                                    else:
                                        new_avg_ratio = bid_ratio
                                    
                                    cursor.execute("""
                                        UPDATE competitor_master 
                                        SET total_bids = ?, total_wins = ?, avg_bid_ratio = ?,
                                            last_seen = ?, updated_at = CURRENT_TIMESTAMP
                                        WHERE id = ?
                                    """, (new_total_bids, new_total_wins, new_avg_ratio, 
                                        datetime.now().date(), comp_id))
                                    
                                    summary['competitors_updated'].append(comp_name)
                                    competitors_updated_count += 1
                        
                        # ===== PREPARE BID HISTORY INSERTION =====
                        bid_history_to_insert.append((
                            company_id,
                            comp_name,
                            tender_id,
                            final_amount,
                            quoted_amount,
                            bid_ratio,
                            1 if is_winner else 0,
                            datetime.now().date(),
                            datetime.now()
                        ))
                    
                    # ===== BATCH INSERT BID HISTORY =====
                    if bid_history_to_insert:
                        cursor.executemany("""
                            INSERT INTO competitor_bid_history (
                                company_id, competitor_name, tender_id, bid_amount,
                                official_estimate, bid_ratio, was_winner, bid_date, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, bid_history_to_insert)
                        
                        summary['bids_inserted'] = [item[1] for item in bid_history_to_insert]
                        st.success(f"✅ Recorded {len(bid_history_to_insert)} bid history entries")
                        if skipped_duplicates > 0:
                            st.warning(f"⚠️ Skipped {skipped_duplicates} duplicate bid entries")
                    
                    # ===== COMMIT TRANSACTION =====
                    cursor.execute("COMMIT")
                    
                    st.success(f"✅ Processed: {competitors_added_count} new, {competitors_updated_count} updated")
                    
                except Exception as e:
                    # Rollback on error
                    cursor.execute("ROLLBACK")
                    raise e
            
            # ===== UPDATE company_tenders TABLE (separate connection) =====
            if summary['winner']:
                try:
                    update_data = {
                        'winning_competitor': summary['winner'],
                        'winning_bid_amount': summary['winner_amount'],
                        'total_bidders': len(competitors),
                        'evaluation_status': 'completed',
                        'updated_at': datetime.now()
                    }
                    
                    update_success = self._update_company_tender(tender_id, update_data)
                    if update_success:
                        summary['company_tender_updated'] = True
                        st.success("✅ Company tender updated with winner info")
                    else:
                        summary['errors'].append("Failed to update company_tenders")
                except Exception as e:
                    summary['errors'].append(f"Error updating company tender: {str(e)}")
            
            # ===== UPDATE historical_tenders TABLE =====
            try:
                # Prepare competitor data for storage
                competitors_json = []
                for comp in competitors:
                    competitors_json.append({
                        'name': comp.get('name', ''),
                        'bid_amount': comp.get('final_amount', 0),
                        'quoted_amount': comp.get('quoted_amount', 0),
                        'discount_percentage': comp.get('discount_percentage', 0),
                        'is_winner': comp.get('is_winner', False)
                    })
                
                historical_data = {
                    'tender_id': tender_id,
                    'tender_title': tender_data.get('tender_title', ''),
                    'procuring_entity': tender_data.get('procuring_entity', ''),
                    'procurement_type': tender_data.get('procurement_type', 'LTM'),
                    'official_estimate': tender_data.get('official_estimate', 0),
                    'awarded_price': summary['winner_amount'] or tender_data.get('awarded_price', 0),
                    'num_competitors': len(competitors),
                    'total_bidders': len(competitors),
                    'winning_competitor': summary['winner'] or '',
                    'winning_company_type': winner_type if winner_info else '',
                    'competitors_data': json.dumps(competitors_json),
                    'award_date': datetime.now().date(),
                    'notes': f'Imported from opening report on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
                }
                
                # Use existing methods for historical tender
                historical_tenders = self.db.get_historical_tenders(limit=1000) if hasattr(self.db, 'get_historical_tenders') else []
                existing_historical = None
                for ht in historical_tenders:
                    if ht.get('tender_id') == tender_id:
                        existing_historical = ht
                        break
                
                if existing_historical:
                    if hasattr(self.db, 'update_historical_tender_winner'):
                        update_success = self.db.update_historical_tender_winner(
                            existing_historical.get('id'),
                            summary['winner'] or '',
                            winner_type if winner_info else '',
                            summary['winner_amount'] or 0
                        )
                        if update_success:
                            summary['historical_tender_updated'] = True
                            st.success("✅ Historical tender updated")
                        else:
                            summary['errors'].append("Failed to update historical_tenders")
                    else:
                        summary['warnings'].append("update_historical_tender_winner method not available")
                else:
                    if hasattr(self.db, 'insert_historical_tender'):
                        insert_success = self.db.insert_historical_tender(company_id, historical_data)
                        if insert_success:
                            summary['historical_tender_updated'] = True
                            st.success("✅ Historical tender created")
                        else:
                            summary['errors'].append("Failed to insert historical_tenders")
                    else:
                        summary['warnings'].append("insert_historical_tender method not available")
            except Exception as e:
                summary['errors'].append(f"Error updating historical tender: {str(e)}")
            
            # ===== FINAL SUMMARY =====
            if summary['errors']:
                st.warning(f"⚠️ Import completed with {len(summary['errors'])} errors")
            else:
                st.success("✅ Import completed successfully!")
            
            # Show detailed summary
            with st.expander("📊 Import Summary"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Competitors", len(competitors))
                with col2:
                    st.metric("New Competitors", len(summary['competitors_added']))
                with col3:
                    st.metric("Updated Competitors", len(summary['competitors_updated']))
                with col4:
                    st.metric("Bids Inserted", len(summary['bids_inserted']))
                
                if summary['bids_deleted'] > 0:
                    st.warning(f"🗑️ Deleted {summary['bids_deleted']} existing bids (replace mode)")
                
                if summary['winner']:
                    st.success(f"🏆 Winner: {summary['winner']} - BDT {summary['winner_amount']:,.2f}")
            
            return True, summary
            
        except Exception as e:
            error_msg = f"Critical error during import: {str(e)}"
            st.error(error_msg)
            summary['errors'].append(error_msg)
            import traceback
            st.code(traceback.format_exc())
            return False, summary
    
    def import_tender_data_bak2(self, company_id: int, tender_id: str, 
                      parsed_data: Dict, tender_data: Dict = None) -> Tuple[bool, Dict]:
        """
        Import tender data into database using batch operations
        Updates: competitor_master, competitor_bid_history, company_tenders, historical_tenders
        Returns: (success, summary_dict)
        """
        summary = {
            'competitors_added': [],
            'competitors_updated': [],
            'bids_inserted': [],
            'company_tender_updated': False,
            'historical_tender_updated': False,
            'errors': [],
            'warnings': [],
            'winner': None,
            'winner_amount': None,
            'tender_id': tender_id,
            'total_competitors': len(parsed_data.get('competitors', []))
        }
        
        try:
            # Validate parsed data
            if not parsed_data or not parsed_data.get('competitors'):
                summary['errors'].append("No competitor data to import")
                return False, summary
            
            competitors = parsed_data['competitors']
            st.info(f"📊 Processing {len(competitors)} competitors for import...")
            
            # Get the winner info
            winner_info = parsed_data.get('winner_info')
            if winner_info:
                summary['winner'] = winner_info['name']
                summary['winner_amount'] = winner_info['final_amount']
                winner_type = self._guess_business_type(winner_info['name'])
                st.info(f"🏆 Winner detected: {summary['winner']} with BDT {summary['winner_amount']:,.2f}")
            else:
                st.warning("⚠️ No winner detected in the data")
            
            # If no tender_data provided, try to fetch it
            if not tender_data:
                tender_data = self.db.get_tender_by_id(tender_id)
                if tender_data:
                    st.info(f"📋 Found tender data for {tender_id}")
                else:
                    st.warning(f"⚠️ No tender data found for {tender_id}, using minimal data")
                    tender_data = {
                        'tender_id': tender_id,
                        'tender_title': f'Tender {tender_id}',
                        'official_estimate': 0,
                        'procurement_type': 'LTM',
                        'procuring_entity': ''
                    }
            
            # Use a single connection for all operations
            with self.db.get_connection() as conn:
                cursor = self.db.db_conn.get_cursor(conn)
                
                # Begin transaction
                cursor.execute("BEGIN TRANSACTION")
                
                try:
                    # First, get all existing competitors for this company
                    cursor.execute("""
                        SELECT competitor_name FROM competitor_master 
                        WHERE company_id = ?
                    """, (company_id,))
                    existing_competitors = {row['competitor_name'] for row in cursor.fetchall()}
                    
                    # Prepare data for batch operations
                    bid_history_to_insert = []
                    competitors_updated_count = 0
                    competitors_added_count = 0
                    
                    for idx, competitor_data in enumerate(competitors):
                        comp_name = competitor_data.get('name', '').strip().upper()
                        
                        # Validate competitor data
                        if not comp_name:
                            summary['warnings'].append(f"Row {idx+1}: Empty competitor name, skipping")
                            continue
                        
                        # Skip if amount is 0 or invalid
                        final_amount = competitor_data.get('final_amount', 0)
                        if final_amount <= 0:
                            summary['warnings'].append(f"Row {idx+1}: Invalid final amount for {comp_name}, skipping")
                            continue
                        
                        quoted_amount = competitor_data.get('quoted_amount', 0)
                        is_winner = competitor_data.get('is_winner', False)
                        
                        # Calculate bid ratio safely
                        if quoted_amount > 0 and final_amount > 0:
                            bid_ratio = final_amount / quoted_amount
                        else:
                            bid_ratio = 0.95
                        
                        # Check if competitor exists
                        if comp_name in existing_competitors:
                            # Update existing competitor
                            cursor.execute("""
                                SELECT id, total_bids, total_wins, avg_bid_ratio 
                                FROM competitor_master 
                                WHERE company_id = ? AND competitor_name = ?
                            """, (company_id, comp_name))
                            
                            existing = cursor.fetchone()
                            if existing:
                                comp_id = existing['id']
                                total_bids = existing['total_bids'] if existing['total_bids'] is not None else 0
                                total_wins = existing['total_wins'] if existing['total_wins'] is not None else 0
                                avg_ratio = existing['avg_bid_ratio'] if existing['avg_bid_ratio'] is not None else 0.90
                                
                                new_total_bids = total_bids + 1
                                new_total_wins = total_wins + (1 if is_winner else 0)
                                
                                # Calculate new average safely
                                if total_bids > 0:
                                    new_avg_ratio = ((avg_ratio * total_bids) + bid_ratio) / new_total_bids
                                else:
                                    new_avg_ratio = bid_ratio
                                
                                # Update competitor_master
                                cursor.execute("""
                                    UPDATE competitor_master 
                                    SET total_bids = ?, total_wins = ?, avg_bid_ratio = ?,
                                        last_seen = ?, updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                """, (new_total_bids, new_total_wins, new_avg_ratio, 
                                    datetime.now().date(), comp_id))
                                
                                summary['competitors_updated'].append(comp_name)
                                competitors_updated_count += 1
                        else:
                            # Insert new competitor using INSERT OR IGNORE to avoid duplicates
                            cursor.execute("""
                                INSERT OR IGNORE INTO competitor_master (
                                    company_id, competitor_name, total_bids, total_wins, 
                                    avg_bid_ratio, first_seen, last_seen, is_active,
                                    preferred_strategy, notes
                                ) VALUES (?, ?, 1, ?, ?, ?, ?, 1, ?, ?)
                            """, (company_id, comp_name, 1 if is_winner else 0, 
                                bid_ratio, datetime.now().date(), datetime.now().date(),
                                'Unknown', f'Auto-imported from tender {tender_id}'))
                            
                            # Check if the insert was successful (affected rows > 0)
                            if cursor.rowcount > 0:
                                summary['competitors_added'].append(comp_name)
                                existing_competitors.add(comp_name)
                                competitors_added_count += 1
                            else:
                                # The competitor was inserted by another process or already exists
                                # Try to update it instead
                                cursor.execute("""
                                    SELECT id, total_bids, total_wins, avg_bid_ratio 
                                    FROM competitor_master 
                                    WHERE company_id = ? AND competitor_name = ?
                                """, (company_id, comp_name))
                                
                                existing = cursor.fetchone()
                                if existing:
                                    comp_id = existing['id']
                                    total_bids = existing['total_bids'] if existing['total_bids'] is not None else 0
                                    total_wins = existing['total_wins'] if existing['total_wins'] is not None else 0
                                    avg_ratio = existing['avg_bid_ratio'] if existing['avg_bid_ratio'] is not None else 0.90
                                    
                                    new_total_bids = total_bids + 1
                                    new_total_wins = total_wins + (1 if is_winner else 0)
                                    
                                    if total_bids > 0:
                                        new_avg_ratio = ((avg_ratio * total_bids) + bid_ratio) / new_total_bids
                                    else:
                                        new_avg_ratio = bid_ratio
                                    
                                    cursor.execute("""
                                        UPDATE competitor_master 
                                        SET total_bids = ?, total_wins = ?, avg_bid_ratio = ?,
                                            last_seen = ?, updated_at = CURRENT_TIMESTAMP
                                        WHERE id = ?
                                    """, (new_total_bids, new_total_wins, new_avg_ratio, 
                                        datetime.now().date(), comp_id))
                                    
                                    summary['competitors_updated'].append(comp_name)
                                    competitors_updated_count += 1
                        
                        # Prepare bid history insertion
                        bid_history_to_insert.append((
                            company_id,
                            comp_name,
                            tender_id,
                            final_amount,
                            quoted_amount,
                            bid_ratio,
                            1 if is_winner else 0,
                            datetime.now().date(),
                            datetime.now()
                        ))
                    
                    # Batch insert bid history
                    if bid_history_to_insert:
                        cursor.executemany("""
                            INSERT INTO competitor_bid_history (
                                company_id, competitor_name, tender_id, bid_amount,
                                official_estimate, bid_ratio, was_winner, bid_date, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, bid_history_to_insert)
                        
                        summary['bids_inserted'] = [item[1] for item in bid_history_to_insert]
                        st.success(f"✅ Recorded {len(bid_history_to_insert)} bid history entries")
                    
                    # Commit the transaction
                    cursor.execute("COMMIT")
                    
                    st.success(f"✅ Processed: {competitors_added_count} new, {competitors_updated_count} updated")
                    
                except Exception as e:
                    # Rollback on error
                    cursor.execute("ROLLBACK")
                    raise e
            
            # ===== UPDATE company_tenders TABLE (separate connection) =====
            if summary['winner']:
                try:
                    update_data = {
                        'winning_competitor': summary['winner'],
                        'winning_bid_amount': summary['winner_amount'],
                        'total_bidders': len(competitors),
                        'evaluation_status': 'completed',
                        'updated_at': datetime.now()
                    }
                    
                    update_success = self._update_company_tender(tender_id, update_data)
                    if update_success:
                        summary['company_tender_updated'] = True
                        st.success("✅ Company tender updated with winner info")
                    else:
                        summary['errors'].append("Failed to update company_tenders")
                except Exception as e:
                    summary['errors'].append(f"Error updating company tender: {str(e)}")
            
            # ===== UPDATE historical_tenders TABLE =====
            try:
                # Prepare competitor data for storage
                competitors_json = []
                for comp in competitors:
                    competitors_json.append({
                        'name': comp.get('name', ''),
                        'bid_amount': comp.get('final_amount', 0),
                        'quoted_amount': comp.get('quoted_amount', 0),
                        'discount_percentage': comp.get('discount_percentage', 0),
                        'is_winner': comp.get('is_winner', False)
                    })
                
                historical_data = {
                    'tender_id': tender_id,
                    'tender_title': tender_data.get('tender_title', ''),
                    'procuring_entity': tender_data.get('procuring_entity', ''),
                    'procurement_type': tender_data.get('procurement_type', 'LTM'),
                    'official_estimate': tender_data.get('official_estimate', 0),
                    'awarded_price': summary['winner_amount'] or tender_data.get('awarded_price', 0),
                    'num_competitors': len(competitors),
                    'total_bidders': len(competitors),
                    'winning_competitor': summary['winner'] or '',
                    'winning_company_type': winner_type if winner_info else '',
                    'competitors_data': json.dumps(competitors_json),
                    'award_date': datetime.now().date(),
                    'notes': f'Imported from opening report on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
                }
                
                # Use existing methods for historical tender
                historical_tenders = self.db.get_historical_tenders(limit=1000) if hasattr(self.db, 'get_historical_tenders') else []
                existing_historical = None
                for ht in historical_tenders:
                    if ht.get('tender_id') == tender_id:
                        existing_historical = ht
                        break
                
                if existing_historical:
                    if hasattr(self.db, 'update_historical_tender_winner'):
                        update_success = self.db.update_historical_tender_winner(
                            existing_historical.get('id'),
                            summary['winner'] or '',
                            winner_type if winner_info else '',
                            summary['winner_amount'] or 0
                        )
                        if update_success:
                            summary['historical_tender_updated'] = True
                            st.success("✅ Historical tender updated")
                        else:
                            summary['errors'].append("Failed to update historical_tenders")
                    else:
                        summary['warnings'].append("update_historical_tender_winner method not available")
                else:
                    if hasattr(self.db, 'insert_historical_tender'):
                        insert_success = self.db.insert_historical_tender(company_id, historical_data)
                        if insert_success:
                            summary['historical_tender_updated'] = True
                            st.success("✅ Historical tender created")
                        else:
                            summary['errors'].append("Failed to insert historical_tenders")
                    else:
                        summary['warnings'].append("insert_historical_tender method not available")
            except Exception as e:
                summary['errors'].append(f"Error updating historical tender: {str(e)}")
            
            # Final summary
            if summary['errors']:
                st.warning(f"⚠️ Import completed with {len(summary['errors'])} errors")
            else:
                st.success("✅ Import completed successfully!")
            
            return True, summary
            
        except Exception as e:
            error_msg = f"Critical error during import: {str(e)}"
            st.error(error_msg)
            summary['errors'].append(error_msg)
            import traceback
            st.code(traceback.format_exc())
            return False, summary



    def _update_competitor_stats_direct(self, company_id: int, competitor_name: str, 
                                    bid_ratio: float, was_winner: bool) -> bool:
        """Direct SQL update for competitor stats to avoid None issues"""
        try:
            with self.db.get_connection() as conn:
                cursor = self.db.db_conn.get_cursor(conn)
                
                # Ensure bid_ratio is a valid number
                if bid_ratio is None or bid_ratio <= 0:
                    bid_ratio = 0.95
                
                # First, check if competitor exists in master
                cursor.execute("""
                    SELECT id, total_bids, total_wins, avg_bid_ratio 
                    FROM competitor_master 
                    WHERE company_id = ? AND competitor_name = ?
                """, (company_id, competitor_name))
                
                existing = cursor.fetchone()
                
                if existing:
                    comp_id = existing['id']
                    total_bids = existing['total_bids'] if existing['total_bids'] is not None else 0
                    total_wins = existing['total_wins'] if existing['total_wins'] is not None else 0
                    avg_ratio = existing['avg_bid_ratio'] if existing['avg_bid_ratio'] is not None else 0.90
                    
                    new_total_bids = total_bids + 1
                    new_total_wins = total_wins + (1 if was_winner else 0)
                    
                    # Calculate new average safely
                    if total_bids > 0:
                        new_avg_ratio = ((avg_ratio * total_bids) + bid_ratio) / new_total_bids
                    else:
                        new_avg_ratio = bid_ratio
                    
                    cursor.execute("""
                        UPDATE competitor_master 
                        SET total_bids = ?, total_wins = ?, avg_bid_ratio = ?,
                            last_seen = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (new_total_bids, new_total_wins, new_avg_ratio, datetime.now().date(), comp_id))
                    
                    return True
                else:
                    # Insert new competitor
                    cursor.execute("""
                        INSERT INTO competitor_master (
                            company_id, competitor_name, total_bids, total_wins, 
                            avg_bid_ratio, first_seen, last_seen, is_active
                        ) VALUES (?, ?, 1, ?, ?, ?, ?, 1)
                    """, (company_id, competitor_name, 1 if was_winner else 0, 
                        bid_ratio, datetime.now().date(), datetime.now().date()))
                    
                    return True
                    
        except Exception as e:
            print(f"Error updating competitor stats directly: {e}")
            return False
    
    def import_tender_data_bak(self, company_id: int, tender_id: str, 
                          parsed_data: Dict, tender_data: Dict = None) -> Tuple[bool, Dict]:
        """
        Import tender data into database
        Updates: competitor_master, competitor_bid_history, company_tenders, historical_tenders
        Returns: (success, summary_dict)
        """
        summary = {
            'competitors_added': [],
            'competitors_updated': [],
            'bids_inserted': [],
            'company_tender_updated': False,
            'historical_tender_updated': False,
            'errors': [],
            'winner': None,
            'winner_amount': None,
            'tender_id': tender_id,
            'total_competitors': len(parsed_data['competitors'])
        }
        
        try:
            # Get the winner info
            winner_info = parsed_data.get('winner_info')
            if winner_info:
                summary['winner'] = winner_info['name']
                summary['winner_amount'] = winner_info['final_amount']
                winner_type = self._guess_business_type(winner_info['name'])
            
            # Process each competitor for master and bid history
            for competitor_data in parsed_data['competitors']:
                comp_name = competitor_data['name'].strip().upper()
                
                # Skip if amount is 0 or invalid
                if competitor_data['final_amount'] <= 0:
                    continue
                
                # Check if competitor exists in master
                existing_comp = self._find_competitor_by_name(company_id, comp_name)
                
                if existing_comp:
                    summary['competitors_updated'].append(comp_name)
                    
                    # Calculate bid ratio
                    bid_ratio = competitor_data['final_amount'] / competitor_data['quoted_amount'] if competitor_data['quoted_amount'] > 0 else 0.95
                    
                    # Update stats
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
                        'notes': f'Auto-imported from tender {tender_id}'
                    }
                    comp_id = self.db.add_competitor_to_master(company_id, comp_data)
                    
                    if comp_id:
                        summary['competitors_added'].append(comp_name)
                        # Update stats for new competitor
                        bid_ratio = competitor_data['final_amount'] / competitor_data['quoted_amount'] if competitor_data['quoted_amount'] > 0 else 0.95
                        self.db.update_competitor_stats_from_bid(
                            company_id, 
                            comp_name, 
                            bid_ratio, 
                            competitor_data['is_winner']
                        )
                    else:
                        summary['errors'].append(f"Failed to add competitor: {comp_name}")
                        continue
                
                # Insert bid history
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
                else:
                    summary['errors'].append(f"Failed to record bid for: {comp_name}")
            
            # ===== UPDATE company_tenders TABLE =====
            if tender_data:
                # Update the company_tenders table with opening report results
                # Use the existing update_company_tender method we'll add
                update_data = {
                    'winning_competitor': summary['winner'],
                    'winning_bid_amount': summary['winner_amount'],
                    'total_bidders': len(parsed_data['competitors']),
                    'evaluation_status': 'completed' if summary['winner'] else 'pending',
                    'updated_at': datetime.now()
                }
                
                # Update company_tenders
                update_success = self._update_company_tender(tender_id, update_data)
                if update_success:
                    summary['company_tender_updated'] = True
                else:
                    summary['errors'].append("Failed to update company_tenders")
            
            # ===== UPDATE historical_tenders TABLE =====
            # Prepare competitor data for storage
            competitors_json = []
            for comp in parsed_data['competitors']:
                competitors_json.append({
                    'name': comp['name'],
                    'bid_amount': comp['final_amount'],
                    'quoted_amount': comp['quoted_amount'],
                    'discount_percentage': comp['discount_percentage'],
                    'is_winner': comp['is_winner']
                })
            
            # Get tender data for historical record
            if not tender_data:
                tender_data = self.db.get_tender_by_id(tender_id) or {}
            
            # Check if historical tender already exists using existing method
            historical_tenders = self.db.get_historical_tenders(limit=1000)
            existing_historical = None
            for ht in historical_tenders:
                if ht.get('tender_id') == tender_id:
                    existing_historical = ht
                    break
            
            # Prepare historical data
            historical_data = {
                'tender_id': tender_id,
                'tender_title': tender_data.get('tender_title', ''),
                'procuring_entity': tender_data.get('procuring_entity', ''),
                'procurement_type': tender_data.get('procurement_type', ''),
                'official_estimate': tender_data.get('official_estimate', 0),
                'awarded_price': summary['winner_amount'] or tender_data.get('awarded_price', 0),
                'num_competitors': len(parsed_data['competitors']),
                'total_bidders': len(parsed_data['competitors']),
                'winning_competitor': summary['winner'],
                'winning_company_type': winner_type if winner_info else '',
                'competitors_data': json.dumps(competitors_json),
                'award_date': datetime.now().date(),
                'notes': f'Imported from opening report on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            }
            
            if existing_historical:
                # Use existing update method
                update_success = self.db.update_historical_tender_winner(
                    existing_historical['id'],
                    summary['winner'] or '',
                    winner_type if winner_info else '',
                    summary['winner_amount'] or 0
                )
                if update_success:
                    # Also update other fields if needed
                    summary['historical_tender_updated'] = True
                else:
                    summary['errors'].append("Failed to update historical_tenders")
            else:
                # Insert new historical record using existing method
                insert_success = self.db.insert_historical_tender(company_id, historical_data)
                if insert_success:
                    summary['historical_tender_updated'] = True
                else:
                    summary['errors'].append("Failed to insert historical_tenders")
            
            return True, summary
            
        except Exception as e:
            st.error(f"Error importing data: {str(e)}")
            summary['errors'].append(str(e))
            return False, summary
    
    def _update_company_tender(self, tender_id: str, update_data: Dict) -> bool:
        """Update company_tenders table with opening report results"""
        try:
            with self.db.get_connection() as conn:
                cursor = self.db.db_conn.get_cursor(conn)
                
                # Build update query dynamically
                allowed_fields = [
                    'winning_competitor', 'winning_bid_amount', 'total_bidders', 
                    'our_rank', 'evaluation_status', 'updated_at'
                ]
                
                updates = []
                values = []
                
                for key, value in update_data.items():
                    if key in allowed_fields:
                        updates.append(f"{key} = ?")
                        values.append(value)
                
                if not updates:
                    return False
                
                values.append(tender_id)
                query = f"""
                    UPDATE company_tenders 
                    SET {', '.join(updates)}
                    WHERE tender_id = ?
                """
                
                cursor.execute(query, values)
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating company tender: {e}")
            return False
    
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
        if not name:
            return 'Other'
            
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

    def parse_opening_report_with_header(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Parse opening report Excel with header row.
        Columns: S. No, Name of Tenderer, Quoted Amount (in BDT) Without Discount,
        Discount in Percentage (%), Discount in Amount, Quoted Amount (in BDT) with Discount, Winner
        """
        try:
            competitors = []
            winner_info = None
            
            # Get columns
            columns = df.columns.tolist()
            
            # Map columns by position (0-indexed)
            # Index 0: S. No
            # Index 1: Name of Tenderer
            # Index 2: Quoted Amount (without discount)
            # Index 3: Discount in Percentage (%)
            # Index 4: Discount in Amount
            # Index 5: Quoted Amount (with discount)
            # Index 6: Winner
            
            if len(columns) >= 7:
                name_col = columns[1]          # Name of Tenderer
                quoted_col = columns[2]        # Quoted Amount Without Discount
                discount_pct_col = columns[3]  # Discount in Percentage
                discount_amt_col = columns[4]  # Discount in Amount
                final_col = columns[5]         # Quoted Amount With Discount
                winner_col = columns[6]        # Winner
            else:
                # Fallback: try to find by name
                name_col = next((col for col in columns if 'tenderer' in str(col).lower() or 'name' in str(col).lower()), None)
                quoted_col = next((col for col in columns if 'quoted amount' in str(col).lower() and 'without' in str(col).lower()), None)
                discount_pct_col = next((col for col in columns if 'discount' in str(col).lower() and 'percentage' in str(col).lower()), None)
                discount_amt_col = next((col for col in columns if 'discount' in str(col).lower() and 'amount' in str(col).lower() and 'percentage' not in str(col).lower()), None)
                final_col = next((col for col in columns if 'quoted amount' in str(col).lower() and 'with' in str(col).lower()), None)
                winner_col = next((col for col in columns if 'winner' in str(col).lower()), None)
            
            if not name_col or not quoted_col:
                raise ValueError("Could not find required columns: Name and Quoted Amount")
            
            # Parse each row
            for idx, row in df.iterrows():
                # Skip empty rows
                if pd.isna(row.get(name_col)):
                    continue
                
                # Get competitor name
                name = str(row.get(name_col, '')).strip()
                if not name or name == 'nan':
                    continue
                
                # Get values from correct columns - KEEP EXACT PRECISION
                quoted_amount = self._safe_float_precise(row.get(quoted_col, 0))
                discount_pct = self._safe_float_precise(row.get(discount_pct_col, 0)) if discount_pct_col else 0
                discount_amount = self._safe_float_precise(row.get(discount_amt_col, 0)) if discount_amt_col else 0
                final_from_excel = self._safe_float_precise(row.get(final_col, 0)) if final_col else 0
                
                # Calculate final amount - KEEP EXACT PRECISION (don't round prematurely)
                if final_from_excel > 0:
                    # Use the value from Excel
                    final_amount = final_from_excel
                elif discount_amount > 0:
                    # Calculate using discount amount - KEEP FULL PRECISION
                    final_amount = quoted_amount - discount_amount
                elif discount_pct > 0:
                    # Calculate using discount percentage - KEEP FULL PRECISION
                    final_amount = quoted_amount * (1 - discount_pct / 100)
                else:
                    # No discount
                    final_amount = quoted_amount
                
                # Check if winner
                is_winner = False
                if winner_col:
                    winner_val = str(row.get(winner_col, '')).strip().lower()
                    is_winner = winner_val in ['yes', 'y', '1', 'winner', 'true', 'win']
                
                competitor = {
                    'name': name,
                    'quoted_amount': quoted_amount,      # Keep full precision
                    'final_amount': final_amount,        # Keep full precision
                    'discount_amount': discount_amount,  # Keep full precision
                    'discount_percentage': discount_pct,
                    'is_winner': is_winner
                }
                
                if is_winner:
                    winner_info = competitor
                
                competitors.append(competitor)
            
            return {
                'competitors': competitors,
                'winner_info': winner_info,
                'total_competitors': len(competitors)
            }
            
        except Exception as e:
            st.error(f"Error parsing opening report: {e}")
            import traceback
            st.code(traceback.format_exc())
            return {'competitors': [], 'winner_info': None, 'error': str(e)}

    def _safe_float_precise(self, value) -> float:
        """Safely convert value to float with full precision"""
        try:
            if pd.isna(value):
                return 0.0
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # Remove commas, BDT, and other characters
                cleaned = value.replace(',', '').replace('BDT', '').replace('₹', '').replace('$', '').strip()
                if cleaned:
                    return float(cleaned)
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    def _calculate_final_amount(self, quoted_amount: float, discount_amount: float, discount_pct: float) -> float:
        """
        Calculate final amount using discount information.
        
        Args:
            quoted_amount: Original quoted amount (without discount)
            discount_amount: Discount amount in BDT
            discount_pct: Discount percentage
        
        Returns:
            Calculated final amount with discount applied
        """
        # If discount amount is provided, use it
        if discount_amount > 0:
            final = quoted_amount - discount_amount
        # If discount percentage is provided, calculate discount amount
        elif discount_pct > 0:
            discount = quoted_amount * (discount_pct / 100)
            final = quoted_amount - discount
        # No discount applied
        else:
            final = quoted_amount
        
        # Round to 2 decimal places and ensure not negative
        return max(0, round(final, 2))

    def _safe_float(self, value) -> float:
        """Safely convert value to float"""
        try:
            if pd.isna(value):
                return 0.0
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # Remove commas and BDT if present
                cleaned = value.replace(',', '').replace('BDT', '').strip()
                return float(cleaned) if cleaned else 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0