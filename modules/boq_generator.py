# modules/boq_generator.py - Simplified (only business logic, no DB ops)

import pandas as pd
from datetime import datetime
from io import BytesIO
import re
from typing import List, Dict, Optional
from database.unified_db_manager import get_db_manager


class BOQGenerator:
    """BOQ Generator - Business logic only, DB ops in BOQCRUD"""

    def __init__(self, db_instance=None):
        self.db = db_instance or get_db_manager()

    # ====================== RATE BOOK METHODS (delegates to DB) ======================

    def get_company_rate_books(self, company_id: int):
        """Get all rate books for a company"""
        return self.db.get_company_rate_books(company_id)

     # ✅ Add missing method
    def get_boq_items(self, boq_id: int) -> List[Dict]:
        """Get all items for a BOQ"""
        return self.db.get_boq_items(boq_id)
    
    def get_rate_book_version(self, book_id: int):
        """Get current active version"""
        return self.db.get_rate_book_version(book_id)

    def get_rates_from_book(self, book_id: int, version_id: int, pricing_level: str = 'COMPETITIVE'):
        """Get rates from specific rate book"""
        return self.db.get_rates_from_book(book_id, version_id, pricing_level)

    # ====================== BOQ CRUD (delegates to DB) ======================

    def create_boq(self, user_id: int, company_id: int, tender_id: str, 
                   tender_title: str, procuring_entity: str = "", 
                   rate_book_id: int = None, version_id: int = None, 
                   selected_zone: str = "N/A", source_type: str = "",
                   is_quick_boq: bool = False) -> int:
        """Create new BOQ record"""
        return self.db.create_boq(
            user_id, company_id, tender_id, tender_title, procuring_entity,
            rate_book_id, version_id, selected_zone, source_type, is_quick_boq
        )

    def add_boq_items(self, boq_id: int, items: List[Dict]):
        """Add multiple items to a BOQ"""
        return self.db.add_boq_items(boq_id, items)

    def update_boq_totals(self, boq_id: int):
        """Update totals after adding items"""
        return self.db.update_boq_totals(boq_id)

    def lock_boq(self, boq_id: int, user_id: int):
        """Lock BOQ as final"""
        return self.db.lock_boq(boq_id, user_id)

    def get_boq_by_id(self, boq_id: int) -> Optional[Dict]:
        """Get full BOQ with items"""
        return self.db.get_boq_by_id(boq_id)

    # ====================== BOQ MATCHING (business logic) ======================

    def match_boq_items(self, df_boq: pd.DataFrame, rates_df: pd.DataFrame) -> Dict:
        """Match uploaded BOQ items with rates - with improved column detection"""
        matched_items = []
        unmatched_items = []

        # ✅ Debug: Show columns
        print(f"🔍 BOQ DataFrame columns: {df_boq.columns.tolist()}")
        print(f"🔍 Rates DataFrame columns: {rates_df.columns.tolist()}")
        
        # ✅ Normalize column names - try multiple variations
        def find_column(df, possible_names):
            """Find a column in DataFrame by trying multiple possible names"""
            df_cols_lower = [col.lower().strip() for col in df.columns]
            for name in possible_names:
                name_lower = name.lower().strip()
                if name_lower in df_cols_lower:
                    idx = df_cols_lower.index(name_lower)
                    return df.columns[idx]
            return None
        
        # Find required columns
        code_col = find_column(df_boq, ['Item Code (if any)', 'Item Code', 'Code', 'item_code', 'Item No', 'Sl No'])
        desc_col = find_column(df_boq, ['Description of Item', 'Description', 'description', 'Item Description', 'Particulars'])
        qty_col = find_column(df_boq, ['Quantity', 'Qty', 'qty', 'quantity'])
        unit_col = find_column(df_boq, ['Measurement Unit', 'Unit', 'unit', 'UOM'])
        
        print(f"🔍 Found columns - Code: {code_col}, Description: {desc_col}, Quantity: {qty_col}, Unit: {unit_col}")
        
        # ✅ If description column not found, try to use first text column
        if not desc_col:
            for col in df_boq.columns:
                if df_boq[col].dtype == 'object':
                    desc_col = col
                    break
        
        if not desc_col or not qty_col:
            st.error(f"❌ Could not find required columns. Found columns: {df_boq.columns.tolist()}")
            st.info("Please ensure your file has columns for: Description (text) and Quantity (number)")
            return {
                'matched': [],
                'unmatched': [],
                'total_matched': 0,
                'total_unmatched': 0,
                'total_cost': 0
            }
        
        # ✅ Prepare rates lookup
        rates_df['item_code'] = rates_df['item_code'].astype(str).str.strip().str.upper()
        rates_df['description'] = rates_df['description'].astype(str).str.lower().str.strip()

        code_lookup = {}
        desc_lookup = {}

        for _, row in rates_df.iterrows():
            code = row.get('item_code')
            desc = row.get('description')
            rate = row.get('rate')
            unit = row.get('unit')

            if code and code != 'nan':
                code_lookup[code] = (rate, unit)
            if desc and desc != 'nan':
                desc_lookup[desc] = (rate, unit)

        print(f"🔍 Code lookup has {len(code_lookup)} entries")
        print(f"🔍 Description lookup has {len(desc_lookup)} entries")

        # ✅ Process each row
        for idx, row in df_boq.iterrows():
            # Get values using found columns
            item_code = str(row.get(code_col, '')).strip() if code_col else ''
            description = str(row.get(desc_col, '')).strip()
            
            # Try to get quantity
            try:
                quantity = float(row.get(qty_col, 0)) if row.get(qty_col) is not None else 0
            except (ValueError, TypeError):
                quantity = 0
            
            # Get unit
            unit = str(row.get(unit_col, '')).strip() if unit_col else ''
            
            # Skip if no description or zero quantity
            if quantity <= 0 or not description:
                print(f"⚠️ Skipping row {idx}: quantity={quantity}, description={description[:50] if description else 'None'}")
                continue

            matched_rate = None
            matched_unit = None
            match_method = None

            # ✅ Try exact code match
            if item_code and item_code.upper() in code_lookup:
                matched_rate, matched_unit = code_lookup[item_code.upper()]
                match_method = "Exact Code"
                print(f"✅ Exact code match: {item_code} -> {matched_rate}")

            # ✅ Try exact description match
            if not matched_rate:
                desc_lower = description.lower().strip()
                if desc_lower in desc_lookup:
                    matched_rate, matched_unit = desc_lookup[desc_lower]
                    match_method = "Exact Description"
                    print(f"✅ Exact description match: {description[:50]} -> {matched_rate}")

            # ✅ Try partial match fallback
            if not matched_rate:
                best_score = 0
                best_match = None
                desc_words = set(description.lower().split())
                
                # Remove common words to improve matching
                stop_words = {'the', 'and', 'for', 'with', 'of', 'to', 'in', 'on', 'at', 'by', 'from', 'up', 'off', 'over', 'under'}
                desc_words = desc_words - stop_words

                for db_desc, (rate, unit) in desc_lookup.items():
                    db_words = set(db_desc.split())
                    db_words = db_words - stop_words
                    common = len(desc_words.intersection(db_words))
                    # Weight by percentage of words matched
                    if common > 0:
                        score = common / max(len(desc_words), len(db_words))
                        if score > best_score and score >= 0.3:  # At least 30% match
                            best_score = score
                            best_match = (rate, unit)

                if best_match:
                    matched_rate, matched_unit = best_match
                    match_method = f"Partial Match ({best_score:.0%})"
                    print(f"✅ Partial match: {description[:50]} -> {matched_rate} (score: {best_score:.0%})")

            # ✅ Build item data
            item_data = {
                'Item Code': item_code or "N/A",
                'Description': description,
                'Unit': matched_unit or unit or 'N/A',
                'Quantity': quantity,
                'Unit Rate': matched_rate or 0,
                'Total': quantity * (matched_rate or 0),
                'Match Method': match_method or 'Not Found'
            }

            if matched_rate:
                matched_items.append(item_data)
            else:
                unmatched_items.append(item_data)
                print(f"⚠️ No match for: {description[:50]}")

        print(f"✅ Match complete: {len(matched_items)} matched, {len(unmatched_items)} unmatched")

        return {
            'matched': matched_items,
            'unmatched': unmatched_items,
            'total_matched': len(matched_items),
            'total_unmatched': len(unmatched_items),
            'total_cost': sum(item['Total'] for item in matched_items)
        }

    def _get_column_value(self, row, possible_names):
        """Helper to extract value from multiple column name possibilities"""
        for name in possible_names:
            if name in row and pd.notna(row[name]) and str(row[name]).strip() not in ('', 'nan'):
                return str(row[name]).strip()
        return ''

    # ====================== EXCEL GENERATION (UI/business logic) ======================

    def generate_boq_excel(self, matched_items: List[Dict], unmatched_items: List[Dict], 
                          boq_info: Dict, total_cost: float) -> BytesIO:
        """Generate Excel BOQ report"""
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if matched_items:
                pd.DataFrame(matched_items).to_excel(writer, sheet_name='Matched Items', index=False)
            else:
                pd.DataFrame([{"Message": "No matched items"}]).to_excel(writer, sheet_name='Matched Items', index=False)

            if unmatched_items:
                pd.DataFrame(unmatched_items).to_excel(writer, sheet_name='Unmatched Items', index=False)

            # Summary Sheet
            summary = pd.DataFrame({
                'Parameter': ['Tender ID', 'Tender Title', 'Rate Source', 'Total Items', 'Matched', 'Total Cost', 'Generated'],
                'Value': [
                    boq_info.get('tender_id', 'N/A'),
                    boq_info.get('tender_title', 'N/A'),
                    boq_info.get('rate_source', 'N/A'),
                    len(matched_items) + len(unmatched_items),
                    len(matched_items),
                    f"BDT {total_cost:,.2f}",
                    datetime.now().strftime('%Y-%m-%d %H:%M')
                ]
            })
            summary.to_excel(writer, sheet_name='Summary', index=False)

        output.seek(0)
        return output