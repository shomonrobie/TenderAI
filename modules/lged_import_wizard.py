# modules/lged_import_wizard.py - Refactored to use SystemRateCRUD

import streamlit as st
import pandas as pd
import os
import re
import pdfplumber
from datetime import datetime
from modules.parse_lged_pdf import LGERateParser
from modules.unified_version_manager import register_version_after_import
from modules.unified_rollback_manager import UnifiedRollbackManager
from modules.progress_tracker import ProgressTracker, BatchProgressTracker, render_batch_control_ui
from typing import List, Dict, Any, Optional
import json

from utils.rate_import_helpers import (
    save_temp_file,
    parse_quick_test,
    parse_full_document,
    init_persistent_import,
    fix_description_spacing, 
    get_pdf_total_pages,
    parse_page_range,
    build_hierarchy_from_items,
    hierarchy_to_dataframe,
    get_column_config,
    find_issues,
    validate_pwd_data,
    auto_fix_pwd_issues,
    get_issues_summary
)

from database.unified_db_manager import get_db_manager


class LGEDImportWizard:
    """Enhanced LGED Import Wizard with incremental parsing, batch import, and persistent sessions"""
    
    def __init__(self, db_instance=None):
        self.db = db_instance or get_db_manager()  # ✅ Use cached db manager
        self.parser = LGERateParser()
        self.rollback_manager = UnifiedRollbackManager(self.db)
    
    # =========================================================
    # EXCEL EXTRACTION - Using SystemRateCRUD for DB operations
    # =========================================================
    
    def extract_excel_data(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract data from LGED-style Excel file with hierarchical item structure.
        Handles any code pattern (2-part, 3-part, 4-part, 5-part, etc.)
        """
        import re
        
        # Read the Excel file
        df = pd.read_excel(file_path, sheet_name=0, header=None, dtype=str)
        extracted_items = []
        
        # Find the header row
        header_row_idx = None
        for idx, row in df.iterrows():
            row_values = row.astype(str).tolist()
            if 'Item Code' in str(row_values[0]):
                header_row_idx = idx
                break
        
        if header_row_idx is None:
            header_row_idx = 0
        
        def get_rate_value(val):
            """Safely convert rate value to float"""
            if pd.isna(val) or val == 'nan' or val == '':
                return None
            try:
                cleaned = str(val).replace(',', '').strip()
                return float(cleaned)
            except:
                return None
        
        # Process each row after header
        for idx in range(header_row_idx + 1, len(df)):
            row = df.iloc[idx]
            
            # Get the item code (first column)
            item_code = str(row[0]) if pd.notna(row[0]) else ''
            item_code = item_code.strip()
            
            # Skip empty rows
            if item_code == '' or item_code == 'nan':
                continue
            
            # Skip separator rows (like "1", "2", "3")
            if item_code in ['1', '2', '3']:
                continue
            
            # Skip if it's a date
            if re.match(r'^\d{4}-\d{2}-\d{2}', item_code):
                continue
            
            # Get description
            description = str(row[1]) if pd.notna(row[1]) else ''
            description = description.strip()
            if description == 'nan':
                description = ''
            
            # Get unit
            unit = str(row[2]) if pd.notna(row[2]) else ''
            unit = unit.strip()
            if unit == 'nan':
                unit = ''
            
            # Get zone rates (columns 3-6)
            zone_a = get_rate_value(row[3]) if len(row) > 3 else None
            zone_b = get_rate_value(row[4]) if len(row) > 4 else None
            zone_c = get_rate_value(row[5]) if len(row) > 5 else None
            zone_d = get_rate_value(row[6]) if len(row) > 6 else None
            
            has_rates = any([zone_a, zone_b, zone_c, zone_d])
            dot_count = item_code.count('.')
            
            # Determine parent code (everything except the last part)
            parent_code = None
            if '.' in item_code:
                parts = item_code.split('.')
                if len(parts) >= 2:
                    parent_code = '.'.join(parts[:-1])
            
            # Create item
            item = {
                'item_code': item_code,
                'description': description,
                'unit': unit,
                'zone_a': zone_a,
                'zone_b': zone_b,
                'zone_c': zone_c,
                'zone_d': zone_d,
                'has_rates': has_rates,
                'dot_count': dot_count,
                'parent_code': parent_code,
                'is_parent': not has_rates and '.' in item_code,
                'is_child': has_rates,
                'is_section_header': not has_rates and '.' in item_code,
                'is_leaf_item': has_rates and dot_count <= 2
            }
            
            extracted_items.append(item)
        
        return extracted_items
    
    def excel_to_hierarchy(self, excel_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert extracted Excel items to hierarchy format compatible with database saving."""
        parents = []
        children = []
        parent_codes = set()
        
        for item in excel_items:
            code = item.get('item_code', '')
            description = item.get('description', '')
            unit = item.get('unit', '')
            
            if '.' not in code:
                parent_codes.add(code)
                parents.append({
                    'code': code,
                    'description': description,
                    'chapter': code
                })
            else:
                parent_code = code.split('.')[0]
                rates = {}
                if item.get('zone_a') and item['zone_a'] > 0:
                    rates['Zone-A'] = item['zone_a']
                if item.get('zone_b') and item['zone_b'] > 0:
                    rates['Zone-B'] = item['zone_b']
                if item.get('zone_c') and item['zone_c'] > 0:
                    rates['Zone-C'] = item['zone_c']
                if item.get('zone_d') and item['zone_d'] > 0:
                    rates['Zone-D'] = item['zone_d']
                
                children.append({
                    'code': code,
                    'parent_code': parent_code,
                    'description': description,
                    'unit': unit,
                    'rates': rates
                })
        
        # Add missing parent codes
        for child in children:
            parent_code = child['parent_code']
            if parent_code not in parent_codes:
                parents.append({
                    'code': parent_code,
                    'description': f"Section {parent_code}",
                    'chapter': parent_code
                })
                parent_codes.add(parent_code)
        
        parents.sort(key=lambda x: x['code'])
        
        return {
            'parents': parents,
            'children': children
        }
    
    # =========================================================
    # DATABASE HELPERS - Using SystemRateCRUD
    # =========================================================
    
    def _get_sections_from_db(self, chapter_num: str) -> pd.DataFrame:
        """Get sections for a chapter from LGED tables using SystemRateCRUD"""
        try:
            # ✅ Use SystemRateCRUD method
            sections = self.db.get_lged_sections_dict(chapter_num)
            if sections:
                return pd.DataFrame(sections)
            return pd.DataFrame()
        except Exception as e:
            print(f"Error getting sections: {e}")
            return pd.DataFrame()
    
    def _get_version_history(self, edition_year: int) -> pd.DataFrame:
        """Get version history for LGED using SystemRateCRUD"""
        try:
            # ✅ Use SystemRateCRUD method
            versions = self.db.get_rate_versions_dict('LGED')
            df = pd.DataFrame(versions) if versions else pd.DataFrame()
            if not df.empty and 'edition_year' in df.columns:
                df = df[df['edition_year'] == edition_year]
            return df
        except Exception as e:
            print(f"Error getting version history: {e}")
            return pd.DataFrame()
    
    def _save_to_database(self, df, edition_year, version_name):
        """Save LGED data to database using SystemRateCRUD"""
        try:
            # Rebuild hierarchy from edited data
            children = []
            for _, row in df[df['Type'] == 'Child'].iterrows():
                rates = {}
                if row.get('Zone-A') and row['Zone-A'] > 0:
                    rates['Zone-A'] = float(row['Zone-A'])
                if row.get('Zone-B') and row['Zone-B'] > 0:
                    rates['Zone-B'] = float(row['Zone-B'])
                if row.get('Zone-C') and row['Zone-C'] > 0:
                    rates['Zone-C'] = float(row['Zone-C'])
                if row.get('Zone-D') and row['Zone-D'] > 0:
                    rates['Zone-D'] = float(row['Zone-D'])
                
                children.append({
                    'code': row['Code'],
                    'parent_code': row.get('Parent Code', ''),
                    'description': row['Description'],
                    'unit': row['Unit'],
                    'rates': rates
                })
            
            parents = []
            for _, row in df[df['Type'] == 'Parent'].iterrows():
                parents.append({
                    'code': row['Code'],
                    'description': row['Description'],
                    'chapter': row['Code'].split('.')[0]
                })
            
            hierarchy = {
                'parents': parents,
                'children': children
            }
            
            # ✅ Use SystemRateCRUD method
            version_id = self.db.save_lged_hierarchy(
                hierarchy,
                version_name,
                edition_year,
                datetime.now().date()
            )
            
            # Register in unified version management
            total_rates = sum(len(c['rates']) for c in children)
            register_version_after_import(
                db=self.db,
                source='LGED',
                version_name=version_name,
                edition_year=edition_year,
                effective_date=datetime.now().date(),
                total_parents=len(parents),
                total_children=len(children),
                total_rates=total_rates
            )
            
            return True
            
        except Exception as e:
            st.error(f"Error saving: {str(e)}")
            return False
    
    def _update_lged_chapter_section(self, hierarchy, version_id, edition_year, chapter_num, section_num=None, notes=""):
        """Update a specific chapter/section in LGED using SystemRateCRUD"""
        try:
            # ✅ Use SystemRateCRUD method
            return self.db.update_lged_chapter_section(
                version_id=version_id,
                chapter_num=chapter_num,
                section_num=section_num,
                hierarchy=hierarchy,
                edition_year=edition_year,
                notes=notes,
                updated_by=st.session_state.get('username', 'admin')
            )
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    # =========================================================
    # UI METHODS - Keep UI logic, DB ops use SystemRateCRUD
    # =========================================================
    
    def render(self):
        """Render the LGED import wizard"""
        
        st.markdown("""
        <div class="main-header">
            <h1>🏗️ LGED Rate Schedule Import Wizard</h1>
            <p>Step-by-step guide to import, validate, and update LGED rates from Excel files</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize session state
        if 'lged_excel_wizard_step' not in st.session_state:
            st.session_state.lged_excel_wizard_step = 1
        if 'lged_excel_data' not in st.session_state:
            st.session_state.lged_excel_data = None
        if 'lged_excel_edited_df' not in st.session_state:
            st.session_state.lged_excel_edited_df = None
        
        self._render_excel_wizard()
    
    def _render_excel_wizard(self):
        """Render the Excel import wizard with step indicators"""
        excel_steps = [
            ("1️⃣ Upload", 1),
            ("2️⃣ Map Data", 2),
            ("3️⃣ Review & Edit", 3),
            ("4️⃣ Validate", 4),
            ("5️⃣ Rollback", 5),
            ("6️⃣ Complete", 6)
        ]
        
        cols = st.columns(len(excel_steps))
        for i, (label, step_num) in enumerate(excel_steps):
            with cols[i]:
                if step_num < st.session_state.lged_excel_wizard_step:
                    st.markdown(f"✅ **{label}**")
                elif step_num == st.session_state.lged_excel_wizard_step:
                    st.markdown(f"🔵 **{label}**")
                else:
                    st.markdown(f"⚪ {label}")
        
        st.markdown("---")
        
        if st.session_state.lged_excel_wizard_step == 1:
            self._excel_step1_upload()
        elif st.session_state.lged_excel_wizard_step == 2:
            self._excel_step2_map_data()
        elif st.session_state.lged_excel_wizard_step == 3:
            self._excel_step3_review_edit()
        elif st.session_state.lged_excel_wizard_step == 4:
            self._excel_step4_validate()
        elif st.session_state.lged_excel_wizard_step == 5:
            self._excel_step5_rollback()
        elif st.session_state.lged_excel_wizard_step == 6:
            self._excel_step6_complete()
    
    def _excel_step1_upload(self):
        """Step 1: Upload Excel file with Chapter and Section selection"""
        st.markdown("### Step 1: Upload Excel File")
        st.caption("Upload an LGED Excel file with rate data")
        
        uploaded_file = st.file_uploader(
            "📄 **Select LGED Excel File**",
            type=["xlsx", "xls"],
            key="lged_excel_upload"
        )
        
        if uploaded_file:
            temp_path = f"temp_lged_excel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                preview_df = pd.read_excel(temp_path, nrows=5)
                st.markdown("#### 📋 File Preview")
                st.dataframe(preview_df, use_container_width=True)
                st.success(f"✅ File loaded: {uploaded_file.name}")
                
                st.session_state.lged_excel_temp_path = temp_path
                st.session_state.lged_excel_filename = uploaded_file.name
            except Exception as e:
                st.error(f"Error reading file: {e}")
                return
            
            st.markdown("---")
            st.markdown("### ⚙️ Import Configuration")
            
            col1, col2 = st.columns(2)
            with col1:
                edition_year = st.number_input(
                    "📅 Edition Year",
                    min_value=2020,
                    max_value=2030,
                    value=2025,
                    key="lged_excel_edition_year"
                )
            
            with col2:
                version_name = st.text_input(
                    "📌 Version Name",
                    value=f"LGED Excel Import {edition_year}",
                    key="lged_excel_version_name"
                )
            
            st.markdown("---")
            st.markdown("### 📚 Chapter & Section Selection")
            
            # ✅ Use SystemRateCRUD for chapters
            chapters = self.db.get_lged_chapters_dict()
            
            if not chapters:
                st.warning("⚠️ No LGED chapters found in database. Please add chapters first.")
                st.info("Go to **Rate Management → Chapters** tab to add LGED chapters.")
                return
            
            chapter_options = []
            for ch in chapters:
                chapter_num = str(ch.get('chapter_number', ''))
                chapter_name = ch.get('chapter_name', '')
                chapter_options.append(f"{chapter_num} - {chapter_name}")
            
            selected_chapter_option = st.selectbox(
                "Select Chapter (Required)",
                options=chapter_options,
                key="lged_excel_chapter_select"
            )
            
            if selected_chapter_option:
                chapter_num = selected_chapter_option.split(" - ")[0]
                
                # ✅ Use SystemRateCRUD for sections
                sections_df = self._get_sections_from_db(chapter_num)
                
                st.markdown("#### 📑 Section Selection (Optional)")
                st.caption("Sections are sub-categories within a chapter. Leave blank if no section applies.")
                
                section_options = [("", "None - No section")]
                for _, row in sections_df.iterrows():
                    section_options.append((row['section_number'], f"{row['section_number']} - {row['section_name']}"))
                
                selected_section_option = st.selectbox(
                    "Select Section (Optional)",
                    options=section_options,
                    format_func=lambda x: x[1] if isinstance(x, tuple) else str(x),
                    key="lged_excel_section_select"
                )
                
                section_num = selected_section_option[0] if selected_section_option and selected_section_option[0] else None
                
                st.info(f"""
                **Selected Configuration:**
                - Edition Year: {edition_year}
                - Version Name: {version_name}
                - Chapter: {chapter_num}
                - Section: {section_num if section_num else 'None'}
                """)
                
                st.session_state.lged_excel_config = {
                    'edition_year': edition_year,
                    'version_name': version_name,
                    'chapter_num': chapter_num,
                    'section_num': section_num,
                    'temp_path': temp_path,
                    'filename': uploaded_file.name
                }
                
                st.markdown("---")
                
                if st.button("➡️ Next: Extract & Map Data", type="primary", use_container_width=True):
                    with st.spinner("Extracting data from Excel..."):
                        extracted_items = self.extract_excel_data(temp_path)
                        
                        if extracted_items:
                            for item in extracted_items:
                                item['chapter_number'] = chapter_num
                                item['section_number'] = section_num
                            
                            st.session_state.lged_excel_data = extracted_items
                            st.session_state.lged_excel_wizard_step = 2
                            st.rerun()
                        else:
                            st.error("No data extracted from Excel file")
            else:
                st.info("Please select a chapter to continue")
    
    def _excel_step2_map_data(self):
        """Step 2: Map Data Fields & Define Relationships"""
        st.markdown("### Step 2: Map Data Fields & Define Relationships")
        st.caption("Verify extracted data and define parent-child relationships")
        
        extracted_items = st.session_state.lged_excel_data
        config = st.session_state.lged_excel_config
        
        if not extracted_items:
            st.error("No data found. Please go back to Step 1.")
            if st.button("◀️ Back to Upload"):
                st.session_state.lged_excel_wizard_step = 1
                st.rerun()
            return
        
        # UI logic remains the same - just display and edit
        df = pd.DataFrame(extracted_items)
        df['temp_id'] = range(len(df))
        
        def has_rates(row):
            return any([
                pd.notna(row.get('zone_a')) and row.get('zone_a', 0) > 0,
                pd.notna(row.get('zone_b')) and row.get('zone_b', 0) > 0,
                pd.notna(row.get('zone_c')) and row.get('zone_c', 0) > 0,
                pd.notna(row.get('zone_d')) and row.get('zone_d', 0) > 0
            ])
        
        df['has_rates'] = df.apply(has_rates, axis=1)
        items_with_rates = df[df['has_rates'] == True].copy()
        items_without_rates = df[df['has_rates'] == False].copy()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Items", len(df))
        with col2:
            st.metric("Items with Rates", len(items_with_rates))
        with col3:
            st.metric("Potential Parents", len(items_without_rates))
        
        with st.expander("📋 View Extracted Data Preview", expanded=False):
            preview_df = df[['item_code', 'description', 'unit', 'zone_a', 'zone_b', 'zone_c', 'zone_d', 'has_rates']].head(10)
            st.dataframe(preview_df, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🔗 Define Parent-Child Relationships")
        
        relationship_method = st.radio(
            "Select method:",
            options=[
                ("🤖 Auto-Detect (Recommended for consistent codes)", "auto"),
                ("✏️ Manual Assignment (For complex/inconsistent patterns)", "manual"),
                ("📝 Edit in Table (Most control, best for review)", "table")
            ],
            format_func=lambda x: x[0],
            key="relationship_method"
        )
        
        if isinstance(relationship_method, tuple):
            relationship_method = relationship_method[1]
        
        assigned_items = []
        
        if relationship_method == "auto":
            st.info("🤖 **Auto-Detect Mode:** System will automatically assign parents based on code patterns.")
            st.caption("Example: '3.01.3.2.01' → Parent: '3.01.3.2'")
            
            for _, row in items_with_rates.iterrows():
                code = str(row['item_code'])
                code_parts = code.split('.')
                
                parent_code = None
                if len(code_parts) >= 2:
                    suggested_parent = '.'.join(code_parts[:-1])
                    if suggested_parent in items_without_rates['item_code'].values:
                        parent_code = suggested_parent
                
                assigned_items.append({
                    'temp_id': row['temp_id'],
                    'item_code': row['item_code'],
                    'description': row['description'],
                    'unit': row['unit'],
                    'zone_a': row.get('zone_a'),
                    'zone_b': row.get('zone_b'),
                    'zone_c': row.get('zone_c'),
                    'zone_d': row.get('zone_d'),
                    'parent_code': parent_code,
                    'has_rates': True
                })
            
            for _, row in items_without_rates.iterrows():
                assigned_items.append({
                    'temp_id': row['temp_id'],
                    'item_code': row['item_code'],
                    'description': row['description'],
                    'unit': row['unit'],
                    'zone_a': None,
                    'zone_b': None,
                    'zone_c': None,
                    'zone_d': None,
                    'parent_code': None,
                    'has_rates': False
                })
            
            st.success(f"✅ Auto-detected relationships for {len([i for i in assigned_items if i['parent_code']])} items")
            
        elif relationship_method == "manual":
            # Manual assignment UI
            if items_without_rates.empty:
                parent_options = [("", "None (Root Level)")]
            else:
                parent_options = [("", "None (Root Level)")]
                for _, row in items_without_rates.iterrows():
                    desc_short = str(row['description'])[:60] if pd.notna(row['description']) else ""
                    parent_options.append((row['item_code'], f"{row['item_code']} - {desc_short}..."))
            
            for idx, row in items_with_rates.iterrows():
                with st.expander(f"📝 Assign Parent for: {row['item_code']}", expanded=(idx < 3)):
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        desc_text = str(row['description'])[:100] if pd.notna(row['description']) else ""
                        st.write(f"**Description:** {desc_text}...")
                        st.write(f"**Unit:** {row['unit'] if pd.notna(row['unit']) else 'N/A'}")
                    
                    with col2:
                        default_parent = ""
                        code_parts = str(row['item_code']).split('.')
                        if len(code_parts) >= 2 and not items_without_rates.empty:
                            suggested = '.'.join(code_parts[:-1])
                            if suggested in items_without_rates['item_code'].values:
                                default_parent = suggested
                        
                        selected_parent = st.selectbox(
                            f"Parent for {row['item_code']}",
                            options=parent_options,
                            format_func=lambda x: x[1] if isinstance(x, tuple) else str(x),
                            index=0 if not default_parent else next((i for i, opt in enumerate(parent_options) if opt[0] == default_parent), 0),
                            key=f"parent_{row['temp_id']}"
                        )
                        
                        parent_code = selected_parent[0] if isinstance(selected_parent, tuple) and selected_parent[0] else None
                        
                        assigned_items.append({
                            'temp_id': row['temp_id'],
                            'item_code': row['item_code'],
                            'description': row['description'],
                            'unit': row['unit'],
                            'zone_a': row.get('zone_a'),
                            'zone_b': row.get('zone_b'),
                            'zone_c': row.get('zone_c'),
                            'zone_d': row.get('zone_d'),
                            'parent_code': parent_code,
                            'has_rates': True
                        })
            
            for _, row in items_without_rates.iterrows():
                assigned_items.append({
                    'temp_id': row['temp_id'],
                    'item_code': row['item_code'],
                    'description': row['description'],
                    'unit': row['unit'],
                    'zone_a': None,
                    'zone_b': None,
                    'zone_c': None,
                    'zone_d': None,
                    'parent_code': None,
                    'has_rates': False
                })
        
        else:  # table mode
            st.info("📝 **Table Edit Mode:** Edit parent_code directly in the table below.")
            
            table_data = []
            for idx, row in df.iterrows():
                has_rates_flag = row['has_rates']
                
                suggested_parent = None
                code = str(row['item_code'])
                if '.' in code and has_rates_flag:
                    code_parts = code.split('.')
                    if len(code_parts) >= 2:
                        parent_candidate = '.'.join(code_parts[:-1])
                        if parent_candidate in df['item_code'].values:
                            suggested_parent = parent_candidate
                
                desc_text = str(row['description'])[:80] if pd.notna(row['description']) else ""
                if len(str(row['description'])) > 80:
                    desc_text = desc_text + "..."
                
                table_data.append({
                    'item_code': row['item_code'],
                    'description': desc_text,
                    'unit': row['unit'] if pd.notna(row['unit']) else '',
                    'has_rates': has_rates_flag,
                    'parent_code': suggested_parent,
                    'zone_a': row.get('zone_a'),
                    'zone_b': row.get('zone_b'),
                    'zone_c': row.get('zone_c'),
                    'zone_d': row.get('zone_d')
                })
            
            edit_df = pd.DataFrame(table_data)
            
            edited_table = st.data_editor(
                edit_df,
                use_container_width=True,
                hide_index=True,
                key="parent_editor",
                column_config={
                    "item_code": st.column_config.TextColumn("Item Code", disabled=True, width="small"),
                    "description": st.column_config.TextColumn("Description", width="large"),
                    "unit": st.column_config.TextColumn("Unit", width="small"),
                    "has_rates": st.column_config.CheckboxColumn("Has Rates", disabled=True, width="small"),
                    "parent_code": st.column_config.TextColumn("Parent Code", width="small", 
                                                            help="Enter parent code (e.g., '3.01' or '3.01.3.2')"),
                    "zone_a": st.column_config.NumberColumn("Zone-A", format="%.2f", width="small"),
                    "zone_b": st.column_config.NumberColumn("Zone-B", format="%.2f", width="small"),
                    "zone_c": st.column_config.NumberColumn("Zone-C", format="%.2f", width="small"),
                    "zone_d": st.column_config.NumberColumn("Zone-D", format="%.2f", width="small"),
                }
            )
            
            for idx, row in edited_table.iterrows():
                assigned_items.append({
                    'temp_id': idx,
                    'item_code': row['item_code'],
                    'description': row['description'],
                    'unit': row['unit'],
                    'zone_a': row['zone_a'] if pd.notna(row['zone_a']) else None,
                    'zone_b': row['zone_b'] if pd.notna(row['zone_b']) else None,
                    'zone_c': row['zone_c'] if pd.notna(row['zone_c']) else None,
                    'zone_d': row['zone_d'] if pd.notna(row['zone_d']) else None,
                    'parent_code': row['parent_code'] if pd.notna(row['parent_code']) and row['parent_code'] != '' else None,
                    'has_rates': row['has_rates']
                })
        
        if assigned_items:
            result_df = pd.DataFrame(assigned_items)
            
            st.markdown("---")
            st.markdown("#### 📊 Relationship Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                parents_count = len(result_df[(result_df['parent_code'].isna() | result_df['parent_code'].isnull()) & (result_df['has_rates'] == False)])
                st.metric("Section Headers", parents_count)
            with col2:
                children_count = len(result_df[result_df['parent_code'].notna() & (result_df['parent_code'] != '')])
                st.metric("Child Items", children_count)
            with col3:
                orphan_count = len(result_df[result_df['has_rates'] & (result_df['parent_code'].isna() | result_df['parent_code'] == '')])
                st.metric("Orphan Items", orphan_count, delta="⚠️ Needs parent" if orphan_count > 0 else None)
            with col4:
                st.metric("Total Items", len(result_df))
            
            if children_count > 0:
                st.markdown("#### 📋 Parent-Child Mapping Preview")
                mapping_items = result_df[result_df['parent_code'].notna() & (result_df['parent_code'] != '')]
                if not mapping_items.empty:
                    mapping_df = mapping_items[['item_code', 'parent_code']].head(10)
                    st.dataframe(mapping_df, use_container_width=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("◀️ Back to Upload", use_container_width=True):
                if os.path.exists(config['temp_path']):
                    os.remove(config['temp_path'])
                st.session_state.lged_excel_wizard_step = 1
                st.rerun()
        
        with col2:
            if assigned_items and st.button("➡️ Next: Review & Edit", type="primary", use_container_width=True):
                final_items = []
                for _, row in result_df.iterrows():
                    final_items.append({
                        'item_code': row['item_code'],
                        'description': row['description'],
                        'unit': row['unit'] if pd.notna(row['unit']) else '',
                        'zone_a': row['zone_a'] if pd.notna(row['zone_a']) else None,
                        'zone_b': row['zone_b'] if pd.notna(row['zone_b']) else None,
                        'zone_c': row['zone_c'] if pd.notna(row['zone_c']) else None,
                        'zone_d': row['zone_d'] if pd.notna(row['zone_d']) else None,
                        'is_parent': (pd.isna(row['parent_code']) or row['parent_code'] == '') and not row['has_rates'],
                        'is_child': row['has_rates'],
                        'has_rates': row['has_rates'],
                        'parent_code': row['parent_code'] if pd.notna(row['parent_code']) and row['parent_code'] != '' else None
                    })
                
                st.session_state.lged_excel_data = final_items
                st.session_state.lged_excel_wizard_step = 3
                st.rerun()
    
    def _excel_step3_review_edit(self):
        """Step 3: Review and edit extracted data with export option"""
        # UI only - no DB operations in this step
        st.markdown("### Step 3: Review & Edit Data")
        st.caption("Double-click any cell to edit values. Use export to verify against original Excel file.")
        
        extracted_items = st.session_state.lged_excel_data
        config = st.session_state.lged_excel_config
        
        if not extracted_items:
            st.error("No data found. Please go back to Step 2.")
            if st.button("◀️ Back to Map Data"):
                st.session_state.lged_excel_wizard_step = 2
                st.rerun()
            return
        
        df = pd.DataFrame(extracted_items)
        expected_cols = ['item_code', 'description', 'unit', 'zone_a', 'zone_b', 'zone_c', 'zone_d', 
                        'parent_code', 'has_rates', 'is_parent', 'is_child', 'dot_count']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        
        if 'has_rates' not in df.columns:
            df['has_rates'] = df.apply(
                lambda row: any([
                    pd.notna(row.get('zone_a')) and row.get('zone_a', 0) > 0,
                    pd.notna(row.get('zone_b')) and row.get('zone_b', 0) > 0,
                    pd.notna(row.get('zone_c')) and row.get('zone_c', 0) > 0,
                    pd.notna(row.get('zone_d')) and row.get('zone_d', 0) > 0
                ]), axis=1
            )
        
        if 'dot_count' not in df.columns:
            df['dot_count'] = df['item_code'].apply(lambda x: str(x).count('.') if pd.notna(x) else 0)
        
        df['is_parent'] = (~df['has_rates']) & (df['dot_count'] >= 1)
        df['is_child'] = df['has_rates']
        
        display_cols = ['item_code', 'description', 'unit', 'parent_code', 'zone_a', 'zone_b', 'zone_c', 'zone_d', 
                        'has_rates', 'is_parent', 'is_child', 'dot_count']
        df = df[[c for c in display_cols if c in df.columns]]
        df = df.sort_values('item_code').reset_index(drop=True)
        
        st.markdown("#### 📝 Editable Data Table")
        st.caption("💡 Tip: Set 'parent_code' to establish parent-child relationships")
        
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            key="lged_excel_editor",
            column_config={
                "item_code": st.column_config.TextColumn("Item Code", width="small", disabled=True),
                "description": st.column_config.TextColumn("Description", width="large"),
                "unit": st.column_config.TextColumn("Unit", width="small"),
                "parent_code": st.column_config.TextColumn("Parent Code", width="small", 
                                                        help="Enter parent code (e.g., '2.02.1' for child items)"),
                "zone_a": st.column_config.NumberColumn("Zone-A (Dhaka)", format="%.2f", width="small"),
                "zone_b": st.column_config.NumberColumn("Zone-B (Chattogram)", format="%.2f", width="small"),
                "zone_c": st.column_config.NumberColumn("Zone-C (Rajshahi)", format="%.2f", width="small"),
                "zone_d": st.column_config.NumberColumn("Zone-D (Khulna)", format="%.2f", width="small"),
                "has_rates": st.column_config.CheckboxColumn("Has Rates", disabled=True, width="small"),
                "is_parent": st.column_config.CheckboxColumn("Is Parent", disabled=True, width="small"),
                "is_child": st.column_config.CheckboxColumn("Is Child", disabled=True, width="small"),
                "dot_count": st.column_config.NumberColumn("Dots", disabled=True, width="small"),
            }
        )
        
        st.session_state.lged_excel_edited_df = edited_df
        
        st.markdown("---")
        st.markdown("#### 📊 Data Statistics")
        
        total_items = len(edited_df)
        items_with_rates = len(edited_df[edited_df['has_rates'] == True])
        parents = len(edited_df[(edited_df['has_rates'] == False) & (edited_df['dot_count'] >= 1)])
        children_with_parents = len(edited_df[(edited_df['has_rates'] == True) & (edited_df['parent_code'].notna()) & (edited_df['parent_code'] != '')])
        leaf_items = len(edited_df[(edited_df['has_rates'] == True) & ((edited_df['parent_code'].isna()) | (edited_df['parent_code'] == ''))])
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Items", total_items)
        col2.metric("With Rates", items_with_rates)
        col3.metric("Parent Headers", parents)
        col4.metric("Child Items", children_with_parents)
        col5.metric("Leaf Items", leaf_items)
        
        # Export options
        st.markdown("---")
        st.markdown("#### 💾 Export Data for Verification")
        
        col_export1, col_export2, col_export3 = st.columns(3)
        
        with col_export1:
            csv_data = edited_df.to_csv(index=False)
            st.download_button(
                label="📥 Export to CSV",
                data=csv_data,
                file_name=f"lged_export_{config['chapter_num']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="export_csv"
            )
        
        with col_export2:
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                edited_df.to_excel(writer, sheet_name='LGED_Data', index=False)
                summary_data = {
                    'Metric': ['Chapter', 'Section', 'Total Items', 'With Rates', 'Parent Headers', 'Child Items', 'Leaf Items', 'Export Date'],
                    'Value': [config['chapter_num'], config.get('section_num', 'None'), total_items, items_with_rates, parents, children_with_parents, leaf_items, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            output.seek(0)
            st.download_button(
                label="📊 Export to Excel",
                data=output.getvalue(),
                file_name=f"lged_export_{config['chapter_num']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="export_excel"
            )
        
        with col_export3:
            json_data = edited_df.to_json(orient='records', indent=2)
            st.download_button(
                label="📋 Export to JSON",
                data=json_data,
                file_name=f"lged_export_{config['chapter_num']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
                key="export_json"
            )
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("◀️ Back to Map Data", use_container_width=True):
                st.session_state.lged_excel_wizard_step = 2
                st.rerun()
        
        with col2:
            if st.button("➡️ Next: Validate", type="primary", use_container_width=True):
                errors = []
                duplicates = edited_df[edited_df['item_code'].duplicated()]
                if not duplicates.empty:
                    errors.append(f"Duplicate item codes: {duplicates['item_code'].tolist()}")
                
                if errors:
                    for error in errors:
                        st.error(f"❌ {error}")
                    st.stop()
                
                st.session_state.lged_excel_wizard_step = 4
                st.rerun()
    
    def _excel_step4_validate(self):
        """Step 4: Validate & Confirm with clear chapter/section replacement info"""
        st.markdown("### Step 4: Validate & Confirm")
        
        edited_df = st.session_state.lged_excel_edited_df
        config = st.session_state.lged_excel_config
        
        if edited_df is None:
            st.error("No data found. Please go back to Step 3.")
            if st.button("◀️ Back to Review"):
                st.session_state.lged_excel_wizard_step = 3
                st.rerun()
            return
        
        total_items = len(edited_df)
        items_with_rates = len(edited_df[edited_df['has_rates'] == True])
        parents = len(edited_df[(edited_df['has_rates'] == False) & (edited_df['dot_count'] >= 1)])
        children_with_parents = len(edited_df[(edited_df['has_rates'] == True) & (edited_df['parent_code'].notna()) & (edited_df['parent_code'] != '')])
        leaf_items = len(edited_df[(edited_df['has_rates'] == True) & ((edited_df['parent_code'].isna()) | (edited_df['parent_code'] == ''))])
        
        # ✅ Use SystemRateCRUD for version history
        versions_df = self._get_version_history(config['edition_year'])
        
        st.markdown("### 🔄 Import Mode Selection")
        
        import_mode = st.radio(
            "Select import mode:",
            options=[
                ("🆕 Create New Version (Keep existing versions)", "new_version"),
                ("🔄 Update Chapter/Section in Existing Version", "update_chapter")
            ],
            format_func=lambda x: x[0],
            key="excel_import_mode_select"
        )
        
        if isinstance(import_mode, tuple):
            import_mode = import_mode[1]
        
        version_id = None
        version_number = None
        confirm_update = False
        
        if import_mode == "update_chapter":
            st.markdown("---")
            st.markdown("### 📌 Select Target Version")
            
            if versions_df.empty:
                st.error("❌ No existing versions found. Please create a new version first.")
                import_mode = "new_version"
            else:
                st.info(f"📊 Existing versions for LGED {config['edition_year']}:")
                display_df = versions_df.copy()
                if 'is_active' in display_df.columns:
                    display_df['is_active'] = display_df['is_active'].map({1: '✅ Active', 0: '📦 Archived'})
                st.dataframe(display_df[['version_number', 'is_active', 'created_at', 'total_items']], 
                            use_container_width=True, hide_index=True)
                
                version_options = []
                for _, row in versions_df.iterrows():
                    version_options.append({
                        'id': row['id'],
                        'number': row['version_number'],
                        'is_active': row['is_active'],
                        'label': f"Version {row['version_number']} ({'Active' if row['is_active'] else 'Archived'})"
                    })
                
                selected_version = st.selectbox(
                    "Select version to update:",
                    options=version_options,
                    format_func=lambda x: x['label'],
                    key="update_version_select"
                )
                
                version_id = selected_version['id']
                version_number = selected_version['number']
                
                st.markdown("---")
                st.markdown("### 🎯 Update Scope - WHAT WILL BE REPLACED")
                
                st.warning(f"""
                ⚠️ **YOU ARE ABOUT TO REPLACE THE FOLLOWING DATA IN VERSION {version_number}:**
                
                | Item | Value |
                |------|-------|
                | **Edition Year** | {config['edition_year']} |
                | **Version** | {version_number} |
                | **Chapter** | **Chapter {config['chapter_num']}** |
                | **Section** | {config.get('section_num') if config.get('section_num') else 'ENTIRE CHAPTER (all sections)'} |
                """)
                
                if config.get('section_num'):
                    st.markdown(f"- ✅ Only **Section {config['section_num']}** in Chapter {config['chapter_num']}")
                    st.markdown(f"- ✅ Other sections in Chapter {config['chapter_num']} will remain **UNCHANGED**")
                else:
                    st.markdown(f"- ✅ **ENTIRE Chapter {config['chapter_num']}** (all sections within this chapter)")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Items", total_items)
                col2.metric("With Rates", items_with_rates)
                col3.metric("Parent Headers", parents)
                col4.metric("Child/Leaf Items", children_with_parents + leaf_items)
                
                confirm_update = st.checkbox(
                    f"✓ I understand that I am REPLACING Chapter {config['chapter_num']}" + 
                    (f" Section {config['section_num']}" if config.get('section_num') else " (ENTIRE CHAPTER)") + 
                    f" in Version {version_number}",
                    key="confirm_chapter_update"
                )
        
        st.markdown("---")
        st.markdown("#### 📋 Data to be Saved")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Configuration**")
            st.write(f"Version Name: {config['version_name']}")
            st.write(f"Edition Year: {config['edition_year']}")
            st.write(f"Chapter: {config['chapter_num']}")
            st.write(f"Section: {config.get('section_num', 'None')}")
            if import_mode == "update_chapter" and version_id:
                st.write(f"**Action:** Update Version {version_number}")
                st.write(f"**Scope:** Chapter {config['chapter_num']}" + 
                        (f" Section {config['section_num']}" if config.get('section_num') else " (ENTIRE CHAPTER)"))
            else:
                st.write(f"**Action:** Create New Version")
        
        with col2:
            st.markdown("**Statistics**")
            st.write(f"Total Items: {total_items}")
            st.write(f"Items with Rates: {items_with_rates}")
            st.write(f"Parent Headers: {parents}")
            st.write(f"Child Items: {children_with_parents}")
            st.write(f"Leaf Items: {leaf_items}")
        
        st.markdown("---")
        st.markdown("#### ✅ Validation Results")
        
        issues = []
        orphans = edited_df[(edited_df['has_rates'] == True) & ((edited_df['parent_code'].isna()) | (edited_df['parent_code'] == ''))]
        if not orphans.empty:
            issues.append({'type': 'info', 'message': f"{len(orphans)} leaf items (no parent) - these will be treated as standalone"})
        
        missing_desc = edited_df[edited_df['description'].isna() | (edited_df['description'] == '')]
        if not missing_desc.empty:
            issues.append({'type': 'warning', 'message': f"{len(missing_desc)} items missing descriptions"})
        
        if issues:
            for issue in issues:
                if issue['type'] == 'error':
                    st.error(f"❌ {issue['message']}")
                elif issue['type'] == 'warning':
                    st.warning(f"⚠️ {issue['message']}")
                else:
                    st.info(f"ℹ️ {issue['message']}")
        else:
            st.success("✅ All validation checks passed!")
        
        notes = st.text_area("Notes (optional)", placeholder="Add notes about this import...", key="import_notes")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("◀️ Back to Edit", use_container_width=True):
                st.session_state.lged_excel_wizard_step = 3
                st.rerun()
        
        with col2:
            button_disabled = import_mode == "update_chapter" and not confirm_update
            
            if st.button("💾 **Import to Database**", type="primary", use_container_width=True, disabled=button_disabled):
                hierarchy = self._build_hierarchy_from_df(edited_df, config)
                
                with st.spinner(f"Saving data..."):
                    if import_mode == "update_chapter" and version_id:
                        result = self._update_lged_chapter_section(
                            hierarchy,
                            version_id,
                            config['edition_year'],
                            config['chapter_num'],
                            config.get('section_num'),
                            notes
                        )
                    else:
                        result = self._save_to_database_from_hierarchy(hierarchy, config, notes)
                    
                    if result.get('success'):
                        st.success(result.get('message', 'Import successful!'))
                        st.balloons()
                        st.session_state.lged_import_result = result
                        st.session_state.lged_excel_wizard_step = 6
                        st.rerun()
                    else:
                        st.error(result.get('message', 'Import failed'))
    
    def _build_hierarchy_from_df(self, df, chapter_num):
        """Build hierarchy from DataFrame with proper zone handling"""
        hierarchy = {
            'parents': [],
            'children': []
        }
        
        parent_codes = set()
        
        for _, row in df.iterrows():
            if row.get('has_rates', False):
                # ✅ Build rates dictionary with proper zone values
                rates = {}
                
                # Check each zone column
                zone_a = row.get('zone_a')
                if zone_a and pd.notna(zone_a) and zone_a > 0:
                    rates['Zone-A'] = float(zone_a)
                
                zone_b = row.get('zone_b')
                if zone_b and pd.notna(zone_b) and zone_b > 0:
                    rates['Zone-B'] = float(zone_b)
                
                zone_c = row.get('zone_c')
                if zone_c and pd.notna(zone_c) and zone_c > 0:
                    rates['Zone-C'] = float(zone_c)
                
                zone_d = row.get('zone_d')
                if zone_d and pd.notna(zone_d) and zone_d > 0:
                    rates['Zone-D'] = float(zone_d)
                
                # Debug: print if rates are being captured
                if rates:
                    print(f"✅ Rates for {row['item_code']}: {rates}")
                else:
                    print(f"⚠️ No rates for {row['item_code']}")
                
                parent_code = row.get('parent_code') if pd.notna(row.get('parent_code')) and row.get('parent_code') != '' else None
                
                hierarchy['children'].append({
                    'pwd_code': row['item_code'],
                    'parent_code': parent_code,
                    'description': row.get('description', '') if pd.notna(row.get('description')) else '',
                    'unit': row.get('unit', '') if pd.notna(row.get('unit')) else '',
                    'rates': rates  # ✅ Now includes zone values
                })
                
                if parent_code:
                    parent_codes.add(parent_code)
            else:
                hierarchy['parents'].append({
                    'code': row['item_code'],
                    'description': row.get('description', '') if pd.notna(row.get('description')) else '',
                    'chapter': chapter_num
                })
                parent_codes.add(row['item_code'])
        
        # Add any missing parents
        for parent_code in parent_codes:
            if not any(p['code'] == parent_code for p in hierarchy['parents']):
                hierarchy['parents'].append({
                    'code': parent_code,
                    'description': f"Parent {parent_code}",
                    'chapter': chapter_num
                })
        
        return hierarchy

    
    def _save_to_database_from_hierarchy(self, hierarchy, config, notes):
        """Save hierarchy to database using SystemRateCRUD"""
        try:
            # ✅ Use SystemRateCRUD method
            version_id = self.db.save_lged_hierarchy_enhanced(
                hierarchy=hierarchy,
                version_name=config['version_name'],
                edition_year=config['edition_year'],
                effective_date=datetime.now().date(),
                selected_chapters={config['chapter_num']: {'name': f"Chapter {config['chapter_num']}"}},
                selected_sections={config['section_num']: {'name': f"Section {config['section_num']}"}} if config.get('section_num') else None
            )
            
            return {
                'success': True,
                'version_id': version_id,
                'message': f"Successfully imported {config['version_name']}",
                'mode': 'new_version'
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _excel_step5_rollback(self):
        """Step 5: Rollback options"""
        st.markdown("### Step 5: Rollback & Recovery")
        st.caption("Manage rollback points and recover previous versions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("◀️ Back to Validate", use_container_width=True):
                st.session_state.lged_excel_wizard_step = 4
                st.rerun()
        
        with col2:
            if st.button("➡️ Complete Import", type="primary", use_container_width=True):
                st.session_state.lged_excel_wizard_step = 6
                st.rerun()
    
    def _excel_step6_complete(self):
        """Step 6: Completion"""
        st.markdown("### ✅ Import Complete!")
        
        config = st.session_state.lged_excel_config
        result = st.session_state.get('lged_import_result', {})
        
        st.balloons()
        
        if result.get('success'):
            st.success(f"""
            🎉 **Successfully imported {config['version_name']}**!
            
            The LGED rate schedule has been saved to the database and is now available for use.
            """)
        
        st.markdown("---")
        st.markdown("#### 🎯 What would you like to do next?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Import Another Excel File", use_container_width=True):
                st.session_state.lged_excel_wizard_step = 1
                st.session_state.lged_excel_data = None
                st.session_state.lged_excel_edited_df = None
                if 'lged_import_result' in st.session_state:
                    del st.session_state.lged_import_result
                st.rerun()
        
        with col2:
            if st.button("📊 Go to Rate Management", use_container_width=True):
                st.session_state.lged_excel_wizard_step = 1
                st.session_state.lged_excel_data = None
                st.rerun()


def render_lged_import_wizard(db=None):
    """Convenience function to render LGED import wizard"""
    if db is None:
        db = get_db_manager()
    wizard = LGEDImportWizard(db)
    wizard.render()