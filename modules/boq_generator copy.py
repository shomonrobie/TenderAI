# modules/boq_generator.py - UPDATED with tenant rate support

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
from io import BytesIO
import re
from utils.currency_transformer import number_to_bangladesh_taka_words, number_to_bangladesh_taka_words_simple
from database.unified_db_manager import db

DB_PATH = db.db_path

class BOQGenerator:
    """BOQ Generation with tenant rate support"""
    
    def get_company_rate_book(self, company_id: int, source_type: str = None):
        """Get company's rate book for a specific source type"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get active rate book for this company
            query = """
                SELECT rb.id, rb.name, rb.source_type, rb.is_demo,
                       (SELECT id FROM tenant_rate_versions 
                        WHERE rate_book_id = rb.id AND is_current = 1) as version_id
                FROM tenant_rate_books rb
                WHERE rb.tenant_id = ? AND rb.is_active = 1 AND rb.is_archived = 0
            """
            params = [company_id]
            
            if source_type:
                query += " AND rb.source_type = ?"
                params.append(source_type)
            
            query += " ORDER BY rb.is_demo DESC, rb.created_at DESC LIMIT 1"
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'book_id': result[0],
                    'name': result[1],
                    'source_type': result[2],
                    'is_demo': result[3],
                    'version_id': result[4]
                }
            return None
            
        except Exception as e:
            st.error(f"Error getting rate book: {e}")
            return None
    
    def get_tenant_rates(self, company_id: int, source_type: str, zone: str = None):
        """Get rates from tenant's rate book (with pricing levels)"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get active rate book and version
            book = self.get_company_rate_book(company_id, source_type)
            if not book or not book.get('version_id'):
                conn.close()
                return pd.DataFrame()
            
            version_id = book['version_id']
            
            # Get items with pricing
            query = """
                SELECT 
                    ri.item_code,
                    ri.item_description as description,
                    ri.unit,
                    pl.price as rate,
                    pl.pricing_level,
                    ri.is_custom
                FROM tenant_rate_items ri
                JOIN tenant_pricing_levels pl ON ri.id = pl.rate_item_id
                WHERE ri.rate_book_id = ? 
                AND pl.rate_version_id = ?
                AND ri.is_active = 1
                AND pl.pricing_level = 'MARKET'
                ORDER BY ri.item_code
            """
            
            df = pd.read_sql_query(query, conn, params=(book['book_id'], version_id))
            conn.close()
            
            # Add source info
            if not df.empty:
                df['source'] = source_type
                df['item_type'] = 'tenant'
            
            return df
            
        except Exception as e:
            print(f"Error loading tenant rates: {e}")
            return pd.DataFrame()

            
        except Exception as e:
            st.error(f"Error loading tenant rates: {e}")
            return pd.DataFrame()
    
    def get_rates_from_database(self, source='PWD', zone='Dhaka', edition_year=2022):
        """Get rates from master database (fallback)"""
        conn = sqlite3.connect(DB_PATH)
        
        if source == 'PWD':
            df = pd.read_sql_query("""
                SELECT c.pwd_code as code, c.description, c.unit, r.unit_rate
                FROM pwd_children c
                JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                WHERE r.zone_name = ? AND r.edition_year = ?
            """, conn, params=(zone, edition_year))
        else:
            df = pd.read_sql_query("""
                SELECT c.code, c.description, c.unit, r.unit_rate
                FROM lged_children c
                JOIN lged_zone_rates r ON c.id = r.child_id
                WHERE r.zone_name = ?
            """, conn, params=(zone,))
        
        conn.close()
        return df
    
    def match_boq_items(self, df_boq, rates_df, source_type='tenant'):
        """Match BOQ items with rates from tenant or master"""
        
        matched_items = []
        unmatched_items = []
        
        # Clean the rates data
        rates_df['item_code'] = rates_df['item_code'].astype(str).str.strip()
        rates_df['description'] = rates_df['description'].astype(str).str.lower().str.strip()
        
        # Create lookup dictionaries
        code_lookup = {}
        desc_lookup = {}
        
        for _, row in rates_df.iterrows():
            code = row['item_code']
            desc = row['description']
            rate = row['rate']
            unit = row['unit']
            
            code_lookup[code] = (rate, unit)
            desc_lookup[desc] = (rate, unit)
            
            # Also store without special characters
            desc_clean = re.sub(r'\[[^\]]+\]', '', desc).strip()
            if desc_clean != desc:
                desc_lookup[desc_clean] = (rate, unit)
        
        for idx, row in df_boq.iterrows():
            item_code = str(row.get('Item Code (if any)', '')).strip()
            item_desc = str(row.get('Description of Item', '')).strip()
            quantity = float(row.get('Quantity', 0)) if pd.notna(row.get('Quantity', 0)) else 0
            
            if quantity == 0 or not item_desc or item_desc == 'nan':
                continue
            
            matched_rate = None
            matched_unit = None
            match_method = None
            
            # Try code match
            if item_code and item_code in code_lookup:
                matched_rate, matched_unit = code_lookup[item_code]
                match_method = "Exact Code Match"
            
            # Try description match
            elif not matched_rate:
                item_desc_lower = item_desc.lower().strip()
                if item_desc_lower in desc_lookup:
                    matched_rate, matched_unit = desc_lookup[item_desc_lower]
                    match_method = "Exact Description Match"
            
            # Try partial match
            elif not matched_rate:
                stop_words = {'providing', 'including', 'supplying', 'fitting', 'fixing', 
                            'construction', 'complete', 'direction', 'engineer', 'charge'}
                item_words = set(item_desc_lower.split()) - stop_words
                
                best_match = None
                best_score = 0
                
                for db_desc, (rate, unit) in desc_lookup.items():
                    db_words = set(db_desc.split()) - stop_words
                    common = item_words.intersection(db_words)
                    score = len(common)
                    
                    if score > best_score and score >= 2:
                        best_score = score
                        best_match = (rate, unit)
                
                if best_match:
                    matched_rate, matched_unit = best_match
                    match_method = "Partial Description Match"
            
            item_data = {
                'Item Code': item_code,
                'Description': item_desc,
                'Unit': matched_unit if matched_unit else row.get('Measurement Unit', ''),
                'Quantity': quantity,
                'Unit Rate': matched_rate if matched_rate else 0,
                'Total Price': (quantity * matched_rate) if matched_rate else 0,
                'Source Type': source_type,
                'Match Status': match_method if match_method else 'Not Found'
            }
            
            if matched_rate:
                matched_items.append(item_data)
            else:
                unmatched_items.append(item_data)
        
        return matched_items, unmatched_items
    
    def get_user_plan(self, user_id, company_id):
        """Get user's subscription plan"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT plan FROM subscriptions 
            WHERE user_id = ? OR company_id = ?
            ORDER BY CASE WHEN company_id = ? THEN 1 ELSE 2 END
            LIMIT 1
        """, (user_id, company_id, company_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        return 'free'
    
    def get_remaining_boq_count(self, user_id, company_id):
        """Get remaining BOQ generations for user this month"""
        
        user_role = st.session_state.get('user_role', 'viewer')
        
        # Admins have unlimited access
        if user_role in ['admin', 'system_admin']:
            return -1, "Unlimited BOQ generations (Admin)", 'enterprise'
        
        plan = self.get_user_plan(user_id, company_id)
        
        BOQ_LIMITS = {
            'free': 5,
            'basic': 20,
            'professional': 50,
            'enterprise': -1
        }
        
        monthly_limit = BOQ_LIMITS.get(plan, 5)
        
        if monthly_limit == -1:
            return -1, "Unlimited BOQ generations", plan
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        current_month_start = date.today().replace(day=1)
        
        cursor.execute("""
            SELECT COUNT(*) FROM boq_generation_history 
            WHERE (user_id = ? OR company_id = ?)
            AND generated_at >= ?
        """, (user_id, company_id, current_month_start))
        
        used_count = cursor.fetchone()[0]
        conn.close()
        
        remaining = max(0, monthly_limit - used_count)
        return remaining, f"{remaining} of {monthly_limit} remaining this month", plan
    
    def get_tender_details(self, tender_id):
        """Get tender details from database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT tender_id, ministry_or_agency, selected_zone, workflow_status, official_budget_cap
            FROM tenders_boq_meta 
            WHERE tender_id = ?
        """, (tender_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'tender_id': result[0],
                'ministry_or_agency': result[1],
                'selected_zone': result[2],
                'workflow_status': result[3],
                'official_budget_cap': result[4]
            }
        return None
    
    def record_boq_generation(self, user_id, company_id, tender_id, tender_title, procuring_entity,
                              file_name, item_count, total_cost, zone, source, edition_year,
                              rate_book_id=None, version_id=None):
        """Record BOQ generation with tenant rate book info"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO boq_generation_history 
            (user_id, company_id, tender_id, tender_title, procuring_entity, file_name, 
             item_count, total_estimated_cost, selected_zone, rate_source, edition_year, 
             status, rate_book_id, version_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, company_id, tender_id, tender_title, procuring_entity, file_name,
              item_count, total_cost, zone, source, edition_year, 'completed',
              rate_book_id, version_id))
        
        history_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return history_id
    
    def record_bid_submission(self, boq_history_id, tender_id, company_id, bid_amount, submitted_by):
        """Record bid submission"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO bid_submissions (boq_history_id, tender_id, company_id, submitted_bid_amount, submitted_by, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (boq_history_id, tender_id, company_id, bid_amount, submitted_by, 'submitted'))
        
        conn.commit()
        conn.close()
    
    def generate_boq_excel(self, matched_items, unmatched_items, source, zone, edition_year, tender_id):
        """Generate BOQ Excel file"""
        
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if matched_items:
                matched_df = pd.DataFrame(matched_items)
                matched_df = matched_df.drop(columns=['Match Status', 'Source Type'], errors='ignore')
                
                matched_df['Unit Price (BDT)'] = matched_df['Unit Rate'].apply(lambda x: f"{x:,.2f}")
                matched_df['Total Price (BDT)'] = matched_df['Total Price'].apply(lambda x: f"{x:,.2f}")
                matched_df['Unit Price In Words'] = matched_df['Unit Rate'].apply(number_to_bangladesh_taka_words)
                matched_df['Total Price In Words'] = matched_df['Total Price'].apply(number_to_bangladesh_taka_words)
                matched_df.to_excel(writer, sheet_name='Matched Items', index=False)
            
            if unmatched_items:
                unmatched_df = pd.DataFrame(unmatched_items)
                unmatched_df = unmatched_df.drop(columns=['Match Status', 'Source Type'], errors='ignore')
                unmatched_df.to_excel(writer, sheet_name='Unmatched Items', index=False)
            
            total_cost = sum(item['Total Price'] for item in matched_items)
            summary_data = {
                'Parameter': ['Tender ID', 'Rate Source', 'Zone', 'Edition Year', 'Total Items', 
                             'Matched', 'Unmatched', 'Total Estimated Cost', 'Generated On'],
                'Value': [
                    tender_id, source, zone, edition_year,
                    len(matched_items) + len(unmatched_items),
                    len(matched_items), len(unmatched_items),
                    f"BDT {total_cost:,.2f}",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        output.seek(0)
        return output, total_cost