# modules/boq_generator.py - COMPLETE FINAL VERSION

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
from io import BytesIO
import re
import os
from utils.currency_transformer import number_to_bangladesh_taka_words
from database.unified_db_manager import UnifiedDatabaseManager
from typing import List, Union, Dict, Callable, Optional

db = UnifiedDatabaseManager()
DB_PATH = db.db_path


class BOQGenerator:
    """BOQ Generation with tenant rate support"""
    
    def __init__(self, db_instance=None):
        self.db = db_instance or db
    
    def get_connection(self):
        """Get database connection"""
        try:
            if hasattr(self.db, 'get_connection'):
                return self.db.get_connection()
        except:
            pass
        return sqlite3.connect(DB_PATH)
    
    # ========== RATE BOOK METHODS ==========
    
    def get_company_rate_books(self, company_id: int):
        """Get all rate books for a company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, source_type, custom_source, is_demo, is_active
            FROM tenant_rate_books 
            WHERE tenant_id = ? AND is_archived = 0 AND is_active = 1
            ORDER BY source_type, name
        """, (company_id,))
        books = cursor.fetchall()
        conn.close()
        
        result = []
        for book in books:
            result.append({
                'id': book[0],
                'name': book[1],
                'source_type': book[2],
                'custom_source': book[3],
                'is_demo': book[4],
                'is_active': book[5]
            })
        return result
    
    def get_rate_book_version(self, book_id: int):
        """Get current version for a rate book"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, version_name, is_current 
            FROM tenant_rate_versions 
            WHERE rate_book_id = ? AND is_current = 1
            ORDER BY version_number DESC LIMIT 1
        """, (book_id,))
        version = cursor.fetchone()
        conn.close()
        
        if version:
            return {'id': version[0], 'name': version[1], 'is_current': version[2]}
        return None
    
    def get_rates_from_book(self, book_id: int, version_id: int, pricing_level: str = 'COMPETITIVE'):
        """Get rates from a specific rate book"""
        conn = self.get_connection()
        
        query = """
            SELECT 
                ri.item_code,
                ri.item_description as description,
                ri.unit,
                pl.price as rate,
                ri.is_custom
            FROM tenant_rate_items ri
            JOIN tenant_pricing_levels pl ON ri.id = pl.rate_item_id
            WHERE ri.rate_book_id = ? 
              AND pl.rate_version_id = ?
              AND ri.is_active = 1
              AND pl.pricing_level = ?
            ORDER BY ri.item_code
        """
        
        df = pd.read_sql_query(query, conn, params=(book_id, version_id, pricing_level))
        conn.close()
        return df
    
    # ========== BOQ MATCHING ==========
    
    # modules/boq_generator.py - FIXED match_boq_items to properly handle item codes

    def match_boq_items(self, df_boq: pd.DataFrame, rates_df: pd.DataFrame) -> Dict:
        """Match BOQ items with rates"""
        
        matched_items = []
        unmatched_items = []
        
        # Clean rates data
        rates_df['item_code'] = rates_df['item_code'].astype(str).str.strip()
        rates_df['description'] = rates_df['description'].astype(str).str.lower().str.strip()
        
        # Build lookup dictionaries
        code_lookup = {}
        desc_lookup = {}
        
        for _, row in rates_df.iterrows():
            code = row['item_code']
            desc = row['description']
            rate = row['rate']
            unit = row['unit']
            
            code_lookup[code] = (rate, unit)
            desc_lookup[desc] = (rate, unit)
            
            # Clean description without brackets
            desc_clean = re.sub(r'\[[^\]]+\]', '', desc).strip()
            if desc_clean != desc:
                desc_lookup[desc_clean] = (rate, unit)
        
        for idx, row in df_boq.iterrows():
            # ✅ FIX: Get item code from the uploaded file
            # Try multiple possible column names
            item_code = ''
            for col in ['Item Code (if any)', 'Item Code', 'Code', 'item_code', 'code']:
                if col in df_boq.columns:
                    val = str(row.get(col, '')).strip()
                    if val and val != 'nan':
                        item_code = val
                        break
            
            item_desc = str(row.get('Description of Item', '')).strip()
            if not item_desc:
                item_desc = str(row.get('Description', '')).strip()
            
            quantity = float(row.get('Quantity', 0)) if pd.notna(row.get('Quantity', 0)) else 0
            
            # ✅ If no item_desc, try other columns
            if not item_desc or item_desc == 'nan':
                for col in ['Description', 'Item Description', 'description']:
                    if col in df_boq.columns:
                        val = str(row.get(col, '')).strip()
                        if val and val != 'nan':
                            item_desc = val
                            break
            
            if quantity == 0 or not item_desc or item_desc == 'nan':
                continue
            
            matched_rate = None
            matched_unit = None
            match_method = None
            matched_code = None
            
            # Try exact code match
            if item_code and item_code in code_lookup:
                matched_rate, matched_unit = code_lookup[item_code]
                match_method = "Exact Code"
                matched_code = item_code
            
            # Try exact description match
            if not matched_rate:
                item_desc_lower = item_desc.lower().strip()
                if item_desc_lower in desc_lookup:
                    matched_rate, matched_unit = desc_lookup[item_desc_lower]
                    match_method = "Exact Description"
                    # ✅ Find the code for this description
                    for code, desc in code_lookup.items():
                        if desc_lookup[item_desc_lower] == (matched_rate, matched_unit):
                            matched_code = code
                            break
            
            # Try partial match
            if not matched_rate:
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
                        best_match = (rate, unit, db_desc)
                
                if best_match:
                    matched_rate, matched_unit, matched_desc = best_match
                    match_method = "Partial Description"
                    # ✅ Find the code for this description
                    for code, desc in code_lookup.items():
                        if desc_lookup.get(matched_desc) == (matched_rate, matched_unit):
                            matched_code = code
                            break
            
            item_data = {
                'Item Code': matched_code or item_code,  # ✅ Use matched code or original
                'Description': item_desc,
                'Unit': matched_unit if matched_unit else row.get('Measurement Unit', ''),
                'Quantity': quantity,
                'Unit Rate': matched_rate if matched_rate else 0,
                'Total': (quantity * matched_rate) if matched_rate else 0,
                'Match Method': match_method if match_method else 'Not Found'
            }
            
            if matched_rate:
                matched_items.append(item_data)
            else:
                unmatched_items.append(item_data)
        
        return {
            'matched': matched_items,
            'unmatched': unmatched_items,
            'total_matched': len(matched_items),
            'total_unmatched': len(unmatched_items),
            'total_cost': sum(item['Total'] for item in matched_items)
        }
    # ========== BOQ CRUD ==========
    
    def create_boq(self, user_id: int, company_id: int, tender_id: str, 
                   tender_title: str, procuring_entity: str, 
                   rate_book_id: int, version_id: int, 
                   selected_zone: str, source_type: str,
                   is_quick_boq: bool = False) -> int:
        """Create a new BOQ record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # If tender_id is None or empty, generate one
        if not tender_id or tender_id == "None":
            tender_id = f"BOQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            tender_title = tender_title or f"Quick BOQ {datetime.now().strftime('%Y-%m-%d')}"
        
        status = 'draft' if is_quick_boq else 'pending'
        
        cursor.execute("""
            INSERT INTO boq_generation_history (
                user_id, company_id, tender_id, tender_title, procuring_entity,
                rate_book_id, version_id, selected_zone, rate_source, 
                status, is_quick_boq, generated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, company_id, tender_id, tender_title, procuring_entity,
            rate_book_id, version_id, selected_zone, source_type,
            status, 1 if is_quick_boq else 0,
            datetime.now()
        ))
        
        boq_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return boq_id
    
    def update_boq_totals(self, boq_id: int):
        """Update BOQ totals after items change"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE boq_generation_history 
            SET item_count = (SELECT COUNT(*) FROM boq_items WHERE boq_id = ?),
                total_estimated_cost = (SELECT SUM(total) FROM boq_items WHERE boq_id = ?)
            WHERE id = ?
        """, (boq_id, boq_id, boq_id))
        
        conn.commit()
        conn.close()
    # modules/boq_generator.py - FIXED add_boq_items

    def add_boq_items(self, boq_id: int, items: list):
        """Add multiple items to BOQ with proper item_code"""
        if not items:
            return
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for item in items:
            # ✅ Ensure we have an item_code
            item_code = str(item.get('Item Code', '')).strip()
            if not item_code:
                # Try to generate from description
                desc = item.get('Description', '')
                if desc:
                    # Take first 3 letters of each word
                    words = desc.split()[:3]
                    item_code = ''.join(w[:3] for w in words).upper()
                    if len(item_code) < 3:
                        item_code = f"ITEM_{len(item_code)+1}"
            
            cursor.execute("""
                INSERT INTO boq_items (
                    boq_id, item_code, description, unit, quantity, unit_rate, total, is_custom
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                boq_id,
                item_code,  # ✅ Now saving item_code
                item.get('Description', ''),
                item.get('Unit', ''),
                item.get('Quantity', 0),
                item.get('Unit Rate', 0),
                item.get('Total', 0),
                0
            ))
        
        conn.commit()
        conn.close()
        
        # Update totals
        self.update_boq_totals(boq_id)
    def add_boq_items(self, boq_id: int, items: list):
        """Add multiple items to BOQ"""
        if not items:
            return
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for item in items:
            cursor.execute("""
                INSERT INTO boq_items (
                    boq_id, item_code, description, unit, quantity, unit_rate, total, is_custom
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                boq_id,
                item.get('Item Code', ''),
                item.get('Description', ''),
                item.get('Unit', ''),
                item.get('Quantity', 0),
                item.get('Unit Rate', 0),
                item.get('Total', 0),
                0
            ))
        
        conn.commit()
        conn.close()
        
        # Update totals
        self.update_boq_totals(boq_id)
    
    def lock_boq(self, boq_id: int, user_id: int) -> bool:
        """Lock BOQ as final"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE boq_generation_history 
            SET is_locked = 1, locked_at = ?, locked_by = ?, status = 'locked'
            WHERE id = ?
        """, (datetime.now(), user_id, boq_id))
        
        conn.commit()
        conn.close()
        return True
    
    def unlock_boq(self, boq_id: int, user_id: int) -> bool:
        """Unlock BOQ (admin only)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE boq_generation_history 
            SET is_locked = 0, locked_at = NULL, locked_by = NULL, status = 'draft'
            WHERE id = ?
        """, (boq_id,))
        
        conn.commit()
        conn.close()
        return True
    
    def get_boq_by_id(self, boq_id: int) -> Dict:
        """Get BOQ by ID with items"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        
        # Get BOQ header
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM boq_generation_history WHERE id = ?
        """, (boq_id,))
        boq = cursor.fetchone()
        
        if not boq:
            conn.close()
            return None
        
        # Get items
        cursor.execute("""
            SELECT * FROM boq_items WHERE boq_id = ?
        """, (boq_id,))
        items = cursor.fetchall()
        
        conn.close()
        
        return {
            'boq': dict(boq),
            'items': [dict(item) for item in items]
        }
    
    def generate_boq_excel(self, matched_items: list, unmatched_items: list, 
                          boq_info: dict, total_cost: float) -> BytesIO:
        """Generate BOQ Excel file"""
        
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Matched Items
            if matched_items:
                df_matched = pd.DataFrame(matched_items)
                if 'Unit Rate' in df_matched.columns:
                    df_matched['Unit Rate'] = df_matched['Unit Rate'].apply(lambda x: f"{x:,.2f}")
                if 'Total' in df_matched.columns:
                    df_matched['Total'] = df_matched['Total'].apply(lambda x: f"{x:,.2f}")
                df_matched.to_excel(writer, sheet_name='Matched Items', index=False)
            else:
                empty_df = pd.DataFrame({
                    'Message': ['No items matched. Please check your rate book or try a different rate source.']
                })
                empty_df.to_excel(writer, sheet_name='Matched Items', index=False)
            
            # Sheet 2: Unmatched Items
            if unmatched_items:
                df_unmatched = pd.DataFrame(unmatched_items)
                df_unmatched.to_excel(writer, sheet_name='Unmatched Items', index=False)
            else:
                empty_df = pd.DataFrame({
                    'Message': ['All items were matched successfully!']
                })
                empty_df.to_excel(writer, sheet_name='Unmatched Items', index=False)
            
            # Sheet 3: Summary
            summary_data = {
                'Parameter': [
                    'Tender ID', 'Tender Title', 'Rate Source', 'Zone',
                    'Total Items', 'Matched', 'Unmatched', 'Total Estimated Cost', 'Generated On'
                ],
                'Value': [
                    boq_info.get('tender_id', 'N/A'),
                    boq_info.get('tender_title', 'N/A')[:50],
                    boq_info.get('rate_source', 'N/A'),
                    boq_info.get('selected_zone', 'N/A'),
                    len(matched_items) + len(unmatched_items),
                    len(matched_items),
                    len(unmatched_items),
                    f"BDT {total_cost:,.2f}",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ]
            }
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        output.seek(0)
        return output