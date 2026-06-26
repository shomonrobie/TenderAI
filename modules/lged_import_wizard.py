# modules/lged_import_wizard.py

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

class LGEDImportWizard:
    """Enhanced LGED Import Wizard with incremental parsing, batch import, and persistent sessions"""
    
    def __init__(self, db_instance, parser_instance=None):
        self.db = db_instance  # DatabaseManager instance
        self.parser = parser_instance if parser_instance else LGERateParser()
        self.rollback_manager = UnifiedRollbackManager(db_instance)
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
                'is_parent': not has_rates and '.' in item_code,  # Has code but no rates = parent/section header
                'is_child': has_rates,  # Has rates = child item
                'is_section_header': not has_rates and '.' in item_code,
                'is_leaf_item': has_rates and dot_count <= 2
            }
            
            extracted_items.append(item)
        
        # Debug output
        section_headers = [i for i in extracted_items if not i.get('has_rates') and '.' in i.get('item_code', '')]
        leaf_items = [i for i in extracted_items if i.get('has_rates') and i.get('dot_count', 0) <= 2]
        children = [i for i in extracted_items if i.get('has_rates') and i.get('dot_count', 0) >= 3]
        
        print(f"✅ Extraction Summary:")
        print(f"  - Section Headers (parents without rates): {len(section_headers)}")
        print(f"  - Leaf Items (parents with rates): {len(leaf_items)}")
        print(f"  - Child Items: {len(children)}")
        print(f"  - Total Items: {len(extracted_items)}")
        
        return extracted_items
    
    
    def _safe_float(self, value: Any) -> float:
        """Safely convert a value to float."""
        if pd.isna(value) or value == '' or value == 'nan':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def excel_to_hierarchy(self, excel_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Convert extracted Excel items to hierarchy format compatible with database saving.
        
        Args:
            excel_items: List of items from extract_excel_data
            
        Returns:
            Hierarchy dict with parents and children
        """
        parents = []
        children = []
        
        # Track parent codes we've seen
        parent_codes = set()
        
        for item in excel_items:
            code = item.get('item_code', '')
            description = item.get('description', '')
            unit = item.get('unit', '')
            
            # Determine if this is a parent or child based on code pattern
            # Parent codes are like "1", "2", "3" (single digits)
            # Child codes are like "1.01", "1.02" (with decimal)
            if '.' not in code:
                # This is a parent item
                parent_codes.add(code)
                parents.append({
                    'code': code,
                    'description': description,
                    'chapter': code  # Use code as chapter for now
                })
            else:
                # This is a child item
                parent_code = code.split('.')[0]
                
                # Build rates dict
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
        
        # Add any missing parent codes from children
        for child in children:
            parent_code = child['parent_code']
            if parent_code not in parent_codes:
                # Create a placeholder parent
                parents.append({
                    'code': parent_code,
                    'description': f"Section {parent_code}",
                    'chapter': parent_code
                })
                parent_codes.add(parent_code)
        
        # Sort parents by code
        parents.sort(key=lambda x: x['code'])
        
        return {
            'parents': parents,
            'children': children
        }

    def render_excel_import_tab(self):
        """Render the Excel import tab with wizard-style flow"""
        
        # Initialize session state for Excel wizard
        if 'lged_excel_wizard_step' not in st.session_state:
            st.session_state.lged_excel_wizard_step = 1
        if 'lged_excel_data' not in st.session_state:
            st.session_state.lged_excel_data = None
        if 'lged_excel_edited_df' not in st.session_state:
            st.session_state.lged_excel_edited_df = None
        
        # Step indicators for Excel wizard
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
        
        # Render current step
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

    def _render_excel_wizard(self):
        """Render the Excel import wizard with step indicators"""
        
        # Step indicators for Excel wizard
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
        
        # Render current step
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
            help="Upload Excel file in LGED format with Item Code, Description, Unit, and Zone rates",
            key="lged_excel_upload"
        )
        
        if uploaded_file:
            # Save temp file
            temp_path = f"temp_lged_excel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Preview the file
            try:
                preview_df = pd.read_excel(temp_path, nrows=5)
                st.markdown("#### 📋 File Preview")
                st.dataframe(preview_df, use_container_width=True)
                
                st.success(f"✅ File loaded: {uploaded_file.name}")
                
                # Store in session
                st.session_state.lged_excel_temp_path = temp_path
                st.session_state.lged_excel_filename = uploaded_file.name
                
            except Exception as e:
                st.error(f"Error reading file: {e}")
                return
            
            st.markdown("---")
            
            # Configuration
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
            
            # Chapter and Section Selection
            st.markdown("---")
            st.markdown("### 📚 Chapter & Section Selection")
            
            # Get chapters from database
            lged_chapters_df = self.db.get_lged_chapters()
            
            if lged_chapters_df.empty:
                st.warning("⚠️ No LGED chapters found in database. Please add chapters in Rate Management first.")
                st.info("Go to **Rate Management → Chapters** tab to add LGED chapters.")
                return
            
            # Chapter selection (required)
            chapter_options = []
            for _, row in lged_chapters_df.iterrows():
                chapter_num = str(row['chapter_number'])
                chapter_name = row['chapter_name']
                chapter_options.append(f"{chapter_num} - {chapter_name}")
            
            selected_chapter_option = st.selectbox(
                "Select Chapter (Required)",
                options=chapter_options,
                key="lged_excel_chapter_select",
                help="Select which chapter these items belong to"
            )
            
            if selected_chapter_option:
                chapter_num = selected_chapter_option.split(" - ")[0]
                
                # Get sections for this chapter (optional)
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
                
                # Display selection summary
                st.info(f"""
                **Selected Configuration:**
                - Edition Year: {edition_year}
                - Version Name: {version_name}
                - Chapter: {chapter_num}
                - Section: {section_num if section_num else 'None'}
                """)
                
                # Store config
                st.session_state.lged_excel_config = {
                    'edition_year': edition_year,
                    'version_name': version_name,
                    'chapter_num': chapter_num,
                    'section_num': section_num,
                    'temp_path': temp_path,
                    'filename': uploaded_file.name
                }
                
                st.markdown("---")
                
                # Next button
                if st.button("➡️ Next: Extract & Map Data", type="primary", use_container_width=True):
                    # Extract data from Excel
                    with st.spinner("Extracting data from Excel..."):
                        extracted_items = self.extract_excel_data(temp_path)
                        
                        if extracted_items:
                            # Add chapter and section info to each item
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
        """Step 2: Map Excel columns with both Auto and Manual parent assignment"""
        
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
        
        # Create DataFrame for display
        df = pd.DataFrame(extracted_items)
        
        # Add a temporary ID for each row
        df['temp_id'] = range(len(df))
        
        # Determine items with rates (check zone columns)
        def has_rates(row):
            return any([
                pd.notna(row.get('zone_a')) and row.get('zone_a', 0) > 0,
                pd.notna(row.get('zone_b')) and row.get('zone_b', 0) > 0,
                pd.notna(row.get('zone_c')) and row.get('zone_c', 0) > 0,
                pd.notna(row.get('zone_d')) and row.get('zone_d', 0) > 0
            ])
        
        # Add has_rates column
        df['has_rates'] = df.apply(has_rates, axis=1)
        
        # Separate items with and without rates
        items_with_rates = df[df['has_rates'] == True].copy()
        items_without_rates = df[df['has_rates'] == False].copy()
        
        # Display summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Items", len(df))
        with col2:
            st.metric("Items with Rates", len(items_with_rates))
        with col3:
            st.metric("Potential Parents", len(items_without_rates))
        
        # Show preview of extracted data
        with st.expander("📋 View Extracted Data Preview", expanded=False):
            preview_df = df[['item_code', 'description', 'unit', 'zone_a', 'zone_b', 'zone_c', 'zone_d', 'has_rates']].head(10)
            st.dataframe(preview_df, use_container_width=True)
        
        st.markdown("---")
        
        # Choose relationship definition method
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
            
            # Auto-detect parent based on code pattern
            for _, row in items_with_rates.iterrows():
                code = str(row['item_code'])
                code_parts = code.split('.')
                
                # Suggest parent as all but last part
                parent_code = None
                if len(code_parts) >= 2:
                    suggested_parent = '.'.join(code_parts[:-1])
                    # Verify suggested parent exists in items_without_rates
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
            
            # Add section headers
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
            st.info("✏️ **Manual Assignment Mode:** Select parent for each child item from dropdown.")
            
            if items_without_rates.empty:
                st.warning("No potential parents found. All items will be treated as root level.")
                parent_options = [("", "None (Root Level)")]
            else:
                # Create parent options
                parent_options = [("", "None (Root Level)")]
                for _, row in items_without_rates.iterrows():
                    desc_short = str(row['description'])[:60] if pd.notna(row['description']) else ""
                    parent_options.append((row['item_code'], f"{row['item_code']} - {desc_short}..."))
            
            # Manual parent assignment for each rate item
            for idx, row in items_with_rates.iterrows():
                with st.expander(f"📝 Assign Parent for: {row['item_code']}", expanded=(idx < 3)):
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        desc_text = str(row['description'])[:100] if pd.notna(row['description']) else ""
                        st.write(f"**Description:** {desc_text}...")
                        st.write(f"**Unit:** {row['unit'] if pd.notna(row['unit']) else 'N/A'}")
                        st.write(f"**Rates:** Z-A: {row.get('zone_a')}, Z-B: {row.get('zone_b')}, Z-C: {row.get('zone_c')}, Z-D: {row.get('zone_d')}")
                    
                    with col2:
                        # Auto-suggest based on code pattern
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
            
            # Add section headers
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
            st.caption("For child items, enter the parent code in the 'parent_code' column.")
            
            # Prepare data for table editing
            table_data = []
            for idx, row in df.iterrows():
                has_rates_flag = row['has_rates']
                
                # Auto-suggest parent code
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
            
            # Convert back to assigned_items format
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
        
        # Convert to DataFrame for summary
        if assigned_items:
            result_df = pd.DataFrame(assigned_items)
            
            # Show summary
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
            
            # Show mapping preview
            if children_count > 0:
                st.markdown("#### 📋 Parent-Child Mapping Preview")
                mapping_items = result_df[result_df['parent_code'].notna() & (result_df['parent_code'] != '')]
                if not mapping_items.empty:
                    mapping_df = mapping_items[['item_code', 'parent_code']].head(10)
                    st.dataframe(mapping_df, use_container_width=True)
                
                if orphan_count > 0:
                    st.warning(f"⚠️ {orphan_count} items have no parent assigned. They will be treated as root level items.")
        
        # Option to switch method
        if relationship_method != "table":
            if st.button("🔄 Switch to Different Method", use_container_width=True):
                st.rerun()
        
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
                # Convert to the format expected by later steps
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
        
        # Convert to DataFrame for editing
        df = pd.DataFrame(extracted_items)
        
        # Ensure all expected columns exist
        expected_cols = ['item_code', 'description', 'unit', 'zone_a', 'zone_b', 'zone_c', 'zone_d', 
                        'parent_code', 'has_rates', 'is_parent', 'is_child', 'dot_count']
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        
        # Calculate has_rates if missing
        if 'has_rates' not in df.columns:
            df['has_rates'] = df.apply(
                lambda row: any([
                    pd.notna(row.get('zone_a')) and row.get('zone_a', 0) > 0,
                    pd.notna(row.get('zone_b')) and row.get('zone_b', 0) > 0,
                    pd.notna(row.get('zone_c')) and row.get('zone_c', 0) > 0,
                    pd.notna(row.get('zone_d')) and row.get('zone_d', 0) > 0
                ]), axis=1
            )
        
        # Calculate dot_count if missing
        if 'dot_count' not in df.columns:
            df['dot_count'] = df['item_code'].apply(lambda x: str(x).count('.') if pd.notna(x) else 0)
        
        # Determine parent/child status
        df['is_parent'] = (~df['has_rates']) & (df['dot_count'] >= 1)
        df['is_child'] = df['has_rates']
        
        # Reorder columns for better readability
        display_cols = ['item_code', 'description', 'unit', 'parent_code', 'zone_a', 'zone_b', 'zone_c', 'zone_d', 
                        'has_rates', 'is_parent', 'is_child', 'dot_count']
        df = df[[c for c in display_cols if c in df.columns]]
        
        # Sort by item_code for logical grouping
        df = df.sort_values('item_code').reset_index(drop=True)
        
        # Show editable table
        st.markdown("#### 📝 Editable Data Table")
        st.caption("💡 Tip: Set 'parent_code' to establish parent-child relationships (e.g., '2.02.1' for '2.02.1.1')")
        
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
        
        # Save edited data
        st.session_state.lged_excel_edited_df = edited_df
        
        # Statistics
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
        
        # Export Options
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
        
        # Show parent-child relationship summary
        st.markdown("---")
        st.markdown("#### 🔗 Parent-Child Relationship Summary")
        
        if children_with_parents > 0:
            parent_summary = edited_df[edited_df['parent_code'].notna() & (edited_df['parent_code'] != '')].groupby('parent_code').size().reset_index(name='child_count')
            parent_summary.columns = ['Parent Code', 'Child Count']
            st.dataframe(parent_summary, use_container_width=True, hide_index=True)
        else:
            st.info("No child items with parent assignments found.")
        
        if leaf_items > 0:
            st.info(f"💡 {leaf_items} leaf items (have rates but no parent). These will be treated as standalone items.")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("◀️ Back to Map Data", use_container_width=True):
                st.session_state.lged_excel_wizard_step = 2
                st.rerun()
        
        with col2:
            if st.button("➡️ Next: Validate", type="primary", use_container_width=True):
                # Basic validation
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
        
        # Calculate statistics
        total_items = len(edited_df)
        items_with_rates = len(edited_df[edited_df['has_rates'] == True])
        parents = len(edited_df[(edited_df['has_rates'] == False) & (edited_df['dot_count'] >= 1)])
        children_with_parents = len(edited_df[(edited_df['has_rates'] == True) & (edited_df['parent_code'].notna()) & (edited_df['parent_code'] != '')])
        leaf_items = len(edited_df[(edited_df['has_rates'] == True) & ((edited_df['parent_code'].isna()) | (edited_df['parent_code'] == ''))])
        
        # Get existing versions
        versions_df = self.db.get_version_history('LGED', config['edition_year'])
        
        st.markdown("### 🔄 Import Mode Selection")
        
        # Choose import mode
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
                # Display existing versions
                st.info(f"📊 Existing versions for LGED {config['edition_year']}:")
                display_df = versions_df.copy()
                if 'is_active' in display_df.columns:
                    display_df['is_active'] = display_df['is_active'].map({1: '✅ Active', 0: '📦 Archived'})
                st.dataframe(display_df[['version_number', 'is_active', 'created_at', 'total_items']], 
                            use_container_width=True, hide_index=True)
                
                # Version selection
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
                
                # Clear warning about what will be replaced
                st.warning(f"""
                ⚠️ **YOU ARE ABOUT TO REPLACE THE FOLLOWING DATA IN VERSION {version_number}:**
                
                | Item | Value |
                |------|-------|
                | **Edition Year** | {config['edition_year']} |
                | **Version** | {version_number} |
                | **Chapter** | **Chapter {config['chapter_num']}** |
                | **Section** | {config.get('section_num') if config.get('section_num') else 'ENTIRE CHAPTER (all sections)'} |
                
                **What will be replaced:**
                """)
                
                if config.get('section_num'):
                    st.markdown(f"- ✅ Only **Section {config['section_num']}** in Chapter {config['chapter_num']}")
                    st.markdown(f"- ✅ Other sections in Chapter {config['chapter_num']} will remain **UNCHANGED**")
                else:
                    st.markdown(f"- ✅ **ENTIRE Chapter {config['chapter_num']}** (all sections within this chapter)")
                
                st.markdown(f"- ✅ Other chapters (1, 3, 4, etc.) will remain **UNCHANGED**")
                
                st.markdown("""
                **What will be added:**
                - ✅ New items will be added to this chapter/section
                - ✅ Existing items in other chapters remain intact
                
                **Data being imported:**
                """)
                
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
        
        # Summary
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
        
        # Validation results
        st.markdown("---")
        st.markdown("#### ✅ Validation Results")
        
        issues = []
        
        # Check for orphans (items with rates but no parent)
        orphans = edited_df[(edited_df['has_rates'] == True) & ((edited_df['parent_code'].isna()) | (edited_df['parent_code'] == ''))]
        if not orphans.empty:
            issues.append({'type': 'info', 'message': f"{len(orphans)} leaf items (no parent) - these will be treated as standalone"})
        
        # Check for missing descriptions
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
        
        # Notes field
        notes = st.text_area("Notes (optional)", placeholder="Add notes about this import...", key="import_notes")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("◀️ Back to Edit", use_container_width=True):
                st.session_state.lged_excel_wizard_step = 3
                st.rerun()
        
        with col2:
            button_disabled = False
            if import_mode == "update_chapter" and not confirm_update:
                button_disabled = True
                st.caption("Please confirm to update existing version")
            
            if st.button("💾 **Import to Database**", type="primary", use_container_width=True, disabled=button_disabled):
                # Convert edited_df to hierarchy
                hierarchy = {
                    'section_headers': [],
                    'rate_items': []
                }
                
                for _, row in edited_df.iterrows():
                    if row['has_rates']:
                        # Rate item
                        hierarchy['rate_items'].append({
                            'code': row['item_code'],
                            'description': row['description'] if pd.notna(row['description']) else '',
                            'unit': row['unit'] if pd.notna(row['unit']) else '',
                            'parent_code': row['parent_code'] if pd.notna(row['parent_code']) and row['parent_code'] != '' else None,
                            'chapter_number': config['chapter_num'],
                            'section_number': config.get('section_num', ''),
                            'zone_a': row['zone_a'] if pd.notna(row['zone_a']) else None,
                            'zone_b': row['zone_b'] if pd.notna(row['zone_b']) else None,
                            'zone_c': row['zone_c'] if pd.notna(row['zone_c']) else None,
                            'zone_d': row['zone_d'] if pd.notna(row['zone_d']) else None,
                            'has_rates': True,
                            'is_parent': False,
                            'is_child': True,
                            'dot_count': row.get('dot_count', 0)
                        })
                    else:
                        # Section header (parent without rates)
                        hierarchy['section_headers'].append({
                            'code': row['item_code'],
                            'description': row['description'] if pd.notna(row['description']) else '',
                            'chapter_number': config['chapter_num'],
                            'section_number': row['item_code'],
                            'has_children': False
                        })
                
                with st.spinner(f"Saving data..."):
                    if import_mode == "update_chapter" and version_id:
                        result = self.db.update_lged_chapter_section(
                            hierarchy,
                            version_id,
                            config['edition_year'],
                            config['chapter_num'],
                            config.get('section_num'),
                            notes=notes
                        )
                    else:
                        result = self.db.save_lged_hierarchy_enhanced(
                            hierarchy,
                            config['version_name'],
                            config['edition_year'],
                            selected_chapters={config['chapter_num']: {'name': f"Chapter {config['chapter_num']}"}},
                            selected_sections={config['section_num']: {'name': f"Section {config['section_num']}"}} if config.get('section_num') else None,
                            notes=notes
                        )
                    
                    if result.get('success'):
                        st.success(result['message'])
                        st.balloons()
                        
                        st.session_state.lged_import_result = result
                        st.session_state.lged_saved_version = {
                            'parents': len(hierarchy['section_headers']),
                            'children': len(hierarchy['rate_items']),
                            'rates': len(hierarchy['rate_items']) * 4
                        }
                        
                        st.session_state.lged_excel_wizard_step = 6
                        st.rerun()
                    else:
                        st.error(result.get('message', 'Import failed'))
                        if result.get('error'):
                            st.code(result['error'])
    
    def _validate_edited_data(self, edited_df):
        """Validate the edited data before import"""
        issues = []
        
        if edited_df is None or edited_df.empty:
            issues.append({'type': 'error', 'message': 'No data to validate'})
            return issues
        
        # Check for duplicate item codes
        if 'item_code' in edited_df.columns:
            duplicates = edited_df[edited_df['item_code'].duplicated()]
            if not duplicates.empty:
                issues.append({
                    'type': 'error', 
                    'message': f"Duplicate item codes found: {duplicates['item_code'].tolist()}"
                })
        
        # Check for missing item codes
        missing_codes = edited_df[edited_df['item_code'].isna()]
        if not missing_codes.empty:
            issues.append({
                'type': 'error', 
                'message': f"{len(missing_codes)} items missing item codes"
            })
        
        # Check for valid code format - ACCEPT 1,2,3,4 dots
        invalid_codes = []
        valid_dot_counts = [1, 2, 3, 4]  # 2.01.1 (3 dots?), actually count properly
        
        for idx, row in edited_df.iterrows():
            code = str(row['item_code']) if pd.notna(row['item_code']) else ''
            if code and code not in ['nan', 'None']:
                dot_count = code.count('.')
                # Valid codes have between 1 and 4 dots
                if dot_count < 1 or dot_count > 4:
                    if not code.isdigit():  # Allow plain numbers as exception
                        invalid_codes.append(code)
        
        if invalid_codes:
            issues.append({
                'type': 'warning',
                'message': f"Unusual code formats (expected like 2.01, 2.01.1, 2.01.1.1): {invalid_codes[:5]}"
            })
        
        # Check for items with rates but no parent (orphans)
        # But note: Parents (no rates) should NOT be counted as orphans
        if 'has_rates' in edited_df.columns and 'parent_code' in edited_df.columns:
            # Orphans are items WITH rates that have no parent_code
            orphans = edited_df[
                (edited_df['has_rates'] == True) & 
                (edited_df['parent_code'].isna() | (edited_df['parent_code'] == ''))
            ]
            if not orphans.empty:
                orphan_count = len(orphans)
                if orphan_count > 0:
                    issues.append({
                        'type': 'info',
                        'message': f"{orphan_count} items have rates but no parent (these are leaf items, this is normal)"
                    })
        
        return issues



    def _excel_step5_rollback(self):
        """Step 5: Rollback options for Excel import"""
        
        st.markdown("### Step 5: Rollback & Recovery")
        st.caption("Manage rollback points and recover previous versions")
        
        # Reuse existing rollback method from PDF import
        self._step5_rollback_options()
        
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
        """Step 6: Completion for Excel Import"""
        
        st.markdown("### ✅ Import Complete!")
        
        config = st.session_state.lged_excel_config
        result = st.session_state.get('lged_import_result', {})
        
        st.balloons()
        
        if result.get('success'):
            mode = result.get('mode', 'unknown')
            if mode == 'update_chapter':
                st.success(f"""
                🎉 **Successfully updated Chapter {result.get('chapter', '')}**!
                
                The data has been merged into the existing version.
                """)
            else:
                st.success(f"""
                🎉 **Successfully imported {config['version_name']}**!
                
                The LGED rate schedule has been saved to the database and is now available for use.
                """)
            
            # Show statistics
            st.markdown("#### 📊 Import Statistics")
            
            col1, col2, col3 = st.columns(3)
            
            # Get actual counts from database if available
            version_id = result.get('version_id')
            if version_id:
                conn = self.db.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM lged_parents WHERE version_id = ?", (version_id,))
                actual_parents = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT COUNT(*) FROM lged_children WHERE version_id = ?", (version_id,))
                actual_children = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT total_rates FROM rate_versions WHERE id = ?", (version_id,))
                rates_row = cursor.fetchone()
                actual_rates = rates_row[0] if rates_row else 0
                
                conn.close()
                
                col1.metric("Section Headers", actual_parents)
                col2.metric("Rate Items", actual_children)
                col3.metric("Rate Entries", actual_rates)
            else:
                col1.metric("Section Headers", result.get('total_parents', 0))
                col2.metric("Rate Items", result.get('total_children', 0))
                col3.metric("Rate Entries", result.get('total_rates', 0))
            
            # Show version info
            st.markdown("---")
            st.markdown("#### 📌 Version Details")
            st.write(f"**Version Number:** {result.get('version_number', 'N/A')}")
            st.write(f"**Version ID:** {result.get('version_id', 'N/A')}")
            st.write(f"**Mode:** {'Update Chapter/Section' if result.get('mode') == 'update_chapter' else 'Create New Version'}")
            
            if result.get('mode') == 'update_chapter':
                st.write(f"**Updated Chapter:** {result.get('chapter', 'N/A')}")
                if result.get('section'):
                    st.write(f"**Updated Section:** {result.get('section', 'N/A')}")
        
        st.markdown("---")
        st.markdown("#### 🎯 What would you like to do next?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Import Another Excel File", use_container_width=True):
                # Reset Excel wizard state
                st.session_state.lged_excel_wizard_step = 1
                st.session_state.lged_excel_data = None
                st.session_state.lged_excel_edited_df = None
                if 'lged_import_result' in st.session_state:
                    del st.session_state.lged_import_result
                if 'lged_saved_version' in st.session_state:
                    del st.session_state.lged_saved_version
                st.rerun()
        
        with col2:
            if st.button("📊 Go to Rate Management", use_container_width=True):
                st.session_state.lged_excel_wizard_step = 1
                st.session_state.lged_excel_data = None
                st.rerun()


    def _edited_df_to_hierarchy(self, edited_df, config):
        """Convert edited DataFrame back to hierarchy format"""
        
        hierarchy = {
            'section_headers': [],  # Parents WITHOUT rates (e.g., 1.01, 1.1)
            'rate_items': []        # ALL items WITH rates (both 2-part and 3-part codes)
        }
        
        for _, row in edited_df.iterrows():
            code = str(row['item_code']) if pd.notna(row['item_code']) else ''
            description = str(row['description']) if pd.notna(row['description']) else ''
            unit = str(row['unit']) if pd.notna(row['unit']) else ''
            
            # Get zone rates
            zone_a = row.get('zone_a') if pd.notna(row.get('zone_a')) else None
            zone_b = row.get('zone_b') if pd.notna(row.get('zone_b')) else None
            zone_c = row.get('zone_c') if pd.notna(row.get('zone_c')) else None
            zone_d = row.get('zone_d') if pd.notna(row.get('zone_d')) else None
            
            has_rates = any([zone_a, zone_b, zone_c, zone_d])
            
            dot_count = code.count('.')
            
            if has_rates:
                # ALL items with rates go to rate_items
                # Determine parent_code
                parent_code = None
                if dot_count == 2:
                    # 3-part code: parent is first two parts
                    parts = code.split('.')
                    parent_code = f"{parts[0]}.{parts[1]}"
                elif dot_count == 1:
                    # 2-part code with rates: it's a leaf item, no parent
                    parent_code = None
                
                hierarchy['rate_items'].append({
                    'code': code,
                    'description': description,
                    'unit': unit,
                    'parent_code': parent_code,
                    'chapter_number': config['chapter_num'],
                    'section_number': parent_code if parent_code else config.get('section_num', ''),
                    'zone_a': zone_a,
                    'zone_b': zone_b,
                    'zone_c': zone_c,
                    'zone_d': zone_d,
                    'is_parent': dot_count == 1  # 2-part code with rates = parent
                })
            else:
                # Items WITHOUT rates are section headers
                hierarchy['section_headers'].append({
                    'code': code,
                    'description': description,
                    'chapter_number': config['chapter_num'],
                    'section_number': code,
                    'has_children': False  # Will be updated later
                })
        
        # Update has_children flag for section headers
        child_parents = set(item['parent_code'] for item in hierarchy['rate_items'] if item['parent_code'])
        for header in hierarchy['section_headers']:
            if header['code'] in child_parents:
                header['has_children'] = True
        
        # Debug output
        print(f"Hierarchy: {len(hierarchy['section_headers'])} section headers, "
            f"{len(hierarchy['rate_items'])} rate items")
        
        return hierarchy


    def _analyze_hierarchy(self, items: List[Dict]) -> tuple:
        """
        Analyze items to detect chapters and sections.
        
        Returns:
            tuple: (chapters_dict, sections_dict)
        """
        chapters = {}
        sections = {}
        
        for item in items:
            code = item.get('item_code', '')
            description = item.get('description', '')
            
            if '.' in code:
                # This is a child item (has section)
                chapter_num = code.split('.')[0]
                section_num = code
                
                # Track chapters
                if chapter_num not in chapters:
                    chapters[chapter_num] = {
                        'number': chapter_num,
                        'name': f"Chapter {chapter_num}",
                        'description': '',
                        'item_count': 0,
                        'items': []
                    }
                chapters[chapter_num]['item_count'] += 1
                chapters[chapter_num]['items'].append(item)
                
                # Track sections
                if section_num not in sections:
                    sections[section_num] = {
                        'number': section_num,
                        'name': f"Section {section_num}",
                        'description': description[:100] if description else '',
                        'chapter': chapter_num,
                        'item_count': 0,
                        'items': []
                    }
                sections[section_num]['item_count'] += 1
                sections[section_num]['items'].append(item)
                
                # Update section description if available
                if description and not sections[section_num]['description']:
                    sections[section_num]['description'] = description[:100]
            else:
                # This might be a parent item (chapter level)
                if code not in chapters:
                    chapters[code] = {
                        'number': code,
                        'name': description[:100] if description else f"Chapter {code}",
                        'description': description,
                        'item_count': 0,
                        'items': []
                    }
                chapters[code]['item_count'] += 1
                chapters[code]['items'].append(item)
        
        return chapters, sections
    def excel_to_hierarchy_with_structure(self, items: List[Dict], chapters: Dict, sections: Dict) -> Dict:
        """
        Convert extracted Excel items to hierarchy with chapter/section structure.
        
        Args:
            items: List of extracted items
            chapters: Dictionary of chapter information
            sections: Dictionary of section information
            
        Returns:
            Hierarchy dict with chapters, sections, and items
        """
        hierarchy = {
            'chapters': [],
            'sections': [],
            'items': [],
            'relationships': {}
        }
        
        # Add chapters
        for chapter_num, chapter_info in chapters.items():
            hierarchy['chapters'].append({
                'number': chapter_num,
                'name': chapter_info.get('name', f"Chapter {chapter_num}"),
                'description': chapter_info.get('description', ''),
                'order': int(chapter_num) if chapter_num.isdigit() else 999
            })
        
        # Add sections
        for section_num, section_info in sections.items():
            hierarchy['sections'].append({
                'number': section_num,
                'name': section_info.get('name', f"Section {section_num}"),
                'chapter': section_info.get('chapter', section_num.split('.')[0]),
                'description': section_info.get('description', ''),
                'order': float(section_num) if self._is_float(section_num) else 999
            })
        
        # Add items with references to sections
        for item in items:
            code = item.get('item_code', '')
            description = item.get('description', '')
            unit = item.get('unit', '')
            
            rates = {}
            if item.get('zone_a'): rates['Zone-A'] = item['zone_a']
            if item.get('zone_b'): rates['Zone-B'] = item['zone_b']
            if item.get('zone_c'): rates['Zone-C'] = item['zone_c']
            if item.get('zone_d'): rates['Zone-D'] = item['zone_d']
            
            # Determine if parent or child
            is_parent = '.' not in code
            parent_code = None if is_parent else code.split('.')[0]
            section_code = code if '.' in code else None
            
            hierarchy['items'].append({
                'code': code,
                'description': description,
                'unit': unit,
                'rates': rates,
                'is_parent': is_parent,
                'parent_code': parent_code,
                'section_code': section_code,
                'chapter_code': parent_code if is_parent else code.split('.')[0]
            })
        
        # Build relationships
        hierarchy['relationships'] = self._build_relationships(hierarchy)
        
        return hierarchy

    def _build_relationships(self, hierarchy: Dict) -> Dict:
        """Build relationships between chapters, sections, and items"""
        relationships = {
            'chapter_sections': {},
            'section_items': {},
            'parent_child_items': {}
        }
        
        # Map sections to chapters
        for section in hierarchy['sections']:
            chapter = section['chapter']
            if chapter not in relationships['chapter_sections']:
                relationships['chapter_sections'][chapter] = []
            relationships['chapter_sections'][chapter].append(section['number'])
        
        # Map items to sections and chapters
        for item in hierarchy['items']:
            if item['section_code']:
                if item['section_code'] not in relationships['section_items']:
                    relationships['section_items'][item['section_code']] = []
                relationships['section_items'][item['section_code']].append(item['code'])
            
            if item['is_parent']:
                if item['code'] not in relationships['parent_child_items']:
                    relationships['parent_child_items'][item['code']] = []
        
        # Map child items to parents
        for item in hierarchy['items']:
            if not item['is_parent'] and item['parent_code']:
                if item['parent_code'] in relationships['parent_child_items']:
                    relationships['parent_child_items'][item['parent_code']].append(item['code'])
        
        return relationships
    def _save_excel_to_database_enhanced(self, hierarchy: Dict, edition_year: int, 
                                         version_name: str, source_file: str,
                                         chapters: Dict, sections: Dict) -> bool:
        """
        Save Excel-extracted hierarchy to database with chapter/section structure.
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Create version entry
            cursor.execute("""
                INSERT INTO rate_versions (source, version_name, edition_year, 
                                          effective_date, is_active, has_sections, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ('LGED', version_name, edition_year, datetime.now().date(), 
                  1, True, datetime.now()))
            
            version_id = cursor.lastrowid
            
            # Save chapters
            chapter_ids = {}
            for chapter in hierarchy['chapters']:
                cursor.execute("""
                    INSERT INTO rate_chapters (source, version_id, chapter_number, 
                                              chapter_name, description)
                    VALUES (?, ?, ?, ?, ?)
                """, ('LGED', version_id, chapter['number'], 
                      chapter['name'], chapter.get('description', '')))
                chapter_ids[chapter['number']] = cursor.lastrowid
            
            # Save sections
            section_ids = {}
            for section in hierarchy['sections']:
                chapter_id = chapter_ids.get(section['chapter'])
                if chapter_id:
                    cursor.execute("""
                        INSERT INTO rate_sections (source, version_id, chapter_id, 
                                                  section_number, section_name, description)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, ('LGED', version_id, chapter_id, section['number'],
                          section['name'], section.get('description', '')))
                    section_ids[section['number']] = cursor.lastrowid
            
            # Save items with parent-child relationships
            item_ids = {}
            parent_items = {}
            
            # First pass: save parent items
            for item in hierarchy['items']:
                if item['is_parent']:
                    chapter_id = chapter_ids.get(item['chapter_code'])
                    cursor.execute("""
                        INSERT INTO rate_items (version_id, item_code, description, 
                                               unit, chapter_id, is_parent, item_level)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (version_id, item['code'], item['description'],
                          item['unit'], chapter_id, 1, 1))
                    item_id = cursor.lastrowid
                    item_ids[item['code']] = item_id
                    parent_items[item['code']] = item_id
            
            # Second pass: save child items with references to parents and sections
            for item in hierarchy['items']:
                if not item['is_parent']:
                    chapter_id = chapter_ids.get(item['chapter_code'])
                    section_id = section_ids.get(item['section_code']) if item['section_code'] else None
                    parent_id = item_ids.get(item['parent_code'])
                    
                    # Save rates as JSON
                    rates_json = json.dumps(item['rates'])
                    
                    cursor.execute("""
                        INSERT INTO rate_items (version_id, item_code, description, 
                                               unit, chapter_id, section_id, parent_item_id,
                                               is_parent, item_level, rates)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (version_id, item['code'], item['description'],
                          item['unit'], chapter_id, section_id, parent_id,
                          0, 2, rates_json))
            
            conn.commit()
            conn.close()
            
            # Register in unified version management
            total_rates = sum(len(item['rates']) for item in hierarchy['items'] if not item['is_parent'])
            register_version_after_import(
                db=self.db,
                source='LGED',
                version_name=version_name,
                edition_year=edition_year,
                effective_date=datetime.now().date(),
                total_parents=len([i for i in hierarchy['items'] if i['is_parent']]),
                total_children=len([i for i in hierarchy['items'] if not i['is_parent']]),
                total_rates=total_rates
            )
            
            # Update version with chapter numbers
            self.db.execute_query("""
                UPDATE rate_versions 
                SET chapter_numbers = ?, has_sections = 1
                WHERE id = ?
            """, (json.dumps(list(chapter_ids.keys())), version_id))
            
            return True
            
        except Exception as e:
            st.error(f"Error saving to database: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return False

    def _is_float(self, value: str) -> bool:
        """Check if string can be converted to float"""
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _save_excel_to_database(self, hierarchy: Dict[str, Any], edition_year: int, version_name: str, source_file: str) -> bool:
        """
        Save Excel-extracted hierarchy to database.
        
        Args:
            hierarchy: Hierarchy dict with parents and children
            edition_year: Edition year for the rate schedule
            version_name: Name for this version
            source_file: Original source file name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Save using DatabaseManager
            version_id = self.db.save_lged_hierarchy(
                hierarchy,
                version_name,
                edition_year,
                datetime.now().date()
            )
            
            # Register in unified version management
            total_rates = sum(len(c['rates']) for c in hierarchy['children'])
            from modules.unified_version_manager import register_version_after_import
            register_version_after_import(
                db=self.db,
                source='LGED',
                version_name=version_name,
                edition_year=edition_year,
                effective_date=datetime.now().date(),
                total_parents=len(hierarchy['parents']),
                total_children=len(hierarchy['children']),
                total_rates=total_rates
            )
            
            # Create rollback snapshot for this import
            self.rollback_manager.create_snapshot(
                source='LGED',
                version_id=version_id,
                snapshot_name=f"Excel Import: {version_name}",
                created_by=st.session_state.get('username', 'admin'),
                description=f"Imported from Excel file: {source_file}",
                is_auto=True
            )
            
            return True
            
        except Exception as e:
            st.error(f"Error saving to database: {str(e)}")
            return False
    def render(self):
        """Render the LGED import wizard (Excel only)"""
        
        st.markdown("""
        <div class="main-header">
            <h1>🏗️ LGED Rate Schedule Import Wizard</h1>
            <p>Step-by-step guide to import, validate, and update LGED rates from Excel files</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize session state for Excel wizard
        if 'lged_excel_wizard_step' not in st.session_state:
            st.session_state.lged_excel_wizard_step = 1
        if 'lged_excel_data' not in st.session_state:
            st.session_state.lged_excel_data = None
        if 'lged_excel_edited_df' not in st.session_state:
            st.session_state.lged_excel_edited_df = None
        
        self._render_excel_wizard()

    def _render_pdf_import(self):
        """Render PDF import flow (existing logic)"""
        
        # Step indicators
        self._show_step_indicator()
        
        # Render current step
        if st.session_state.lged_wizard_step == 1:
            self._step1_upload_and_config()
        elif st.session_state.lged_wizard_step == 2:
            self._step2_incremental_import()
        elif st.session_state.lged_wizard_step == 3:
            self._step3_review_and_edit()
        elif st.session_state.lged_wizard_step == 4:
            self._step4_validate_and_save()
        elif st.session_state.lged_wizard_step == 5:
            self._step5_rollback_options()
        elif st.session_state.lged_wizard_step == 6:
            self._step6_complete()

    def _show_step_indicator(self):
        """Show progress steps - 6 steps to match PWD"""
        
        steps = [
            ("1️⃣ Upload", 1),
            ("2️⃣ Import Pages", 2),
            ("3️⃣ Review & Edit", 3),
            ("4️⃣ Validate", 4),
            ("5️⃣ Rollback", 5),
            ("6️⃣ Complete", 6)
        ]
        
        cols = st.columns(len(steps))
        for i, (label, step_num) in enumerate(steps):
            with cols[i]:
                if step_num < st.session_state.lged_wizard_step:
                    st.markdown(f"✅ **{label}**")
                elif step_num == st.session_state.lged_wizard_step:
                    st.markdown(f"🔵 **{label}**")
                else:
                    st.markdown(f"⚪ {label}")
        
        st.markdown("---")

    
    def _step1_upload_and_config(self):
        """Step 1: Upload PDF and configure import settings"""
        
        uploaded_file = st.file_uploader(
            "📄 **Select LGED Rate Schedule PDF**",
            type=["pdf"],
            help="Upload the official LGED Rate Schedule PDF (August 2025)",
            key="lged_upload_file"  # ← Unique key
        )
        
        if uploaded_file:
            # Get total pages
            temp_path = "temp_lged_pages.pdf"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            with pdfplumber.open(temp_path) as pdf:
                total_pages = len(pdf.pages)
            
            os.remove(temp_path)
            
            st.info(f"📁 File: {uploaded_file.name} | 📄 Total Pages: {total_pages}")
            st.session_state.lged_total_pages = total_pages
        
        st.markdown("---")
        st.markdown("### ⚙️ Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            edition_year = st.number_input(
                "📅 Edition Year",
                min_value=2020,
                max_value=2030,
                value=2025,
                help="Select the year of this rate schedule",
                key="lged_edition_year"  # ← Unique key
            )
        
        with col2:
            version_name = st.text_input(
                "📌 Version Name",
                value=f"LGED Schedule {edition_year}",
                help="Give this version a descriptive name",
                key="lged_version_name"  # ← Unique key
            )
        
        st.markdown("---")
        st.markdown("### 🚀 Import Strategy")
        
        import_strategy = st.radio(
            "Choose import method:",
            options=[
                "⚡ Quick Test (First 10 pages only)",
                "📑 Batch Import (Process in chunks with progress)",
                "💾 Persistent Import (Save progress, resume later)",
                "🎯 Full Import (All pages at once)"
            ],
            help="Quick Test is fastest for validation. Batch Import lets you monitor progress. Persistent Import saves progress across sessions.",
            key="lged_import_strategy"  # ← Unique key
        )
        
        # Show additional options based on strategy
        if import_strategy == "📑 Batch Import (Process in chunks with progress)":
            batch_size = st.slider(
                "Batch Size (pages per batch)", 
                min_value=5, 
                max_value=50, 
                value=10,
                key="lged_batch_size"  # ← Unique key
            )
        else:
            batch_size = 10
        
        st.markdown("---")
        st.markdown("### 🔄 Rollback Options")
        
        col_r1, col_r2 = st.columns(2)
        
        with col_r1:
            create_snapshot = st.checkbox(
                "📸 Create rollback snapshot before import",
                value=True,
                help="Saves current state so you can rollback if needed",
                key="lged_create_snapshot"  # ← Unique key
            )
        
        with col_r2:
            snapshot_name = st.text_input(
                "Snapshot name (if enabled)",
                value=f"Before LGED Import {edition_year}",
                disabled=not create_snapshot,
                key="lged_snapshot_name"  # ← Unique key
            )
        
        st.info("**Zone Information:**\n"
                "- Zone-A: Dhaka & Mymensingh Division\n"
                "- Zone-B: Chattogram & Sylhet Division\n"
                "- Zone-C: Rajshahi & Rangpur Division\n"
                "- Zone-D: Khulna & Barishal Division\n"
                "- Accessibility Bonus: 5% for remote/offshore areas")
        
        st.markdown("---")
        
        # Action buttons
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            dry_run = st.checkbox(
                "🔍 Dry Run (Preview only, no database save)",
                value=True,
                help="Test parsing without saving to database",
                key="lged_dry_run"  # ← Unique key - THIS WAS THE MISSING ONE!
            )
        
        with col_btn2:
            if uploaded_file:
                if st.button("🚀 **Start Import**", type="primary", use_container_width=True, key="lged_start_import"):
                    # Store settings
                    st.session_state.lged_import_settings = {
                        'file': uploaded_file,
                        'edition_year': edition_year,
                        'version_name': version_name,
                        'dry_run': dry_run,
                        'import_strategy': import_strategy,
                        'batch_size': batch_size,
                        'create_snapshot': create_snapshot,
                        'snapshot_name': snapshot_name
                    }
                    
                    # Create rollback snapshot if requested
                    if create_snapshot and not dry_run:
                        with st.spinner("Creating rollback snapshot..."):
                            snapshot_id = self.rollback_manager.create_snapshot(
                                source='LGED',
                                version_id=None,
                                snapshot_name=snapshot_name,
                                created_by=st.session_state.get('username', 'admin'),
                                description=f"Auto-snapshot before LGED {edition_year} import",
                                is_auto=True
                            )
                            st.session_state.lged_rollback_snapshot = snapshot_id
                            st.success("✅ Rollback snapshot created")
                    
                    # Handle different import strategies - UPDATED
                    if import_strategy == "⚡ Quick Test (First 10 pages only)":
                        from utils.rate_import_helpers import parse_quick_test
                        result = parse_quick_test(
                            parser=self.parser,
                            settings=st.session_state.lged_import_settings,
                            source='LGED'
                        )
                        st.session_state.lged_import_data = result
                        st.session_state.lged_wizard_step = 3
                        st.rerun()
                        
                    elif import_strategy == "📑 Batch Import (Process in chunks with progress)":
                        from modules.progress_tracker import BatchProgressTracker
                        
                        # Initialize batch tracker
                        batch_tracker = BatchProgressTracker(self.db)
                        batch_tracker.set_source('lged')
                        batch_tracker.init_session(
                            total_pages=st.session_state.lged_total_pages,
                            batch_size=batch_size
                        )
                        st.session_state.lged_batch_tracker = batch_tracker
                        st.session_state.lged_wizard_step = 2
                        st.rerun()
                        
                    elif import_strategy == "💾 Persistent Import (Save progress, resume later)":
                        from utils.rate_import_helpers import init_persistent_import
                        init_persistent_import()
                        st.session_state.lged_wizard_step = 2
                        st.rerun()
                        
                    else:  # Full Import
                        from utils.rate_import_helpers import parse_full_document
                        result = parse_full_document(
                            parser=self.parser,
                            settings=st.session_state.lged_import_settings,
                            source='LGED'
                        )
                        st.session_state.lged_import_data = result
                        st.session_state.lged_wizard_step = 3
                        st.rerun()
            else:
                st.button("🚀 **Start Import**", disabled=True, use_container_width=True, key="lged_start_import_disabled")
    
    def _init_batch_import(self):
        """Initialize batch import session state"""
        
        settings = st.session_state.lged_import_settings
        total_pages = st.session_state.lged_total_pages
        batch_size = settings['batch_size']
        
        total_batches = (total_pages + batch_size - 1) // batch_size
        
        st.session_state.lged_batch_status = {
            'current_batch': 0,
            'total_batches': total_batches,
            'processed_pages': 0,
            'total_pages': total_pages,
            'items_found': 0,
            'rates_found': 0,
            'batch_size': batch_size,
            'batches_completed': [],
            'is_complete': False,
            'all_items': []
        }
    
    def _step2_incremental_import(self):
        """Step 2: Incremental batch import with progress"""
        
        st.markdown("### Step 2: Incremental Page Import")
        st.caption("Processing PDF in batches with progress tracking")
        
        # Initialize batch tracker
        if 'lged_batch_tracker' not in st.session_state:
            batch_tracker = BatchProgressTracker(self.db)
            batch_tracker.init_session(
                total_pages=st.session_state.lged_total_pages,
                batch_size=st.session_state.lged_import_settings.get('batch_size', 10)
            )
            st.session_state.lged_batch_tracker = batch_tracker
        else:
            batch_tracker = st.session_state.lged_batch_tracker
        
        # Define callback for batch processing - FIXED
        def process_batch(batch):
            start_page = batch['start_page']
            end_page = batch['end_page']
            
            with st.spinner(f"Processing pages {start_page} to {end_page}..."):
                # FIX: Pass all required parameters to parse_page_range
                from utils.rate_import_helpers import parse_page_range
                items = parse_page_range(
                    parser=self.parser,  # Pass parser
                    uploaded_file=st.session_state.lged_import_settings['file'],
                    start_page=start_page,
                    end_page=end_page,
                    source='LGED'  # Specify source
                )
                
                # Calculate rates count
                rates_count = sum(len(item.get('rates', {})) for item in items)
                
                # Complete the batch
                batch_tracker.complete_batch(
                    batch_number=batch['batch_number'],
                    items=items,
                    rates_count=rates_count,
                    end_page=end_page
                )
                
                st.success(f"✅ Batch {batch['batch_number']} complete! Found {len(items)} items, {rates_count} rates.")
                st.rerun()
        
        # Render batch control UI
        from modules.progress_tracker import render_batch_control_ui
        render_batch_control_ui(batch_tracker, process_batch)
        
        # Check if complete and build hierarchy
        if batch_tracker.is_complete():
            from utils.rate_import_helpers import build_hierarchy_from_items
            with st.spinner("Building parent-child hierarchy..."):
                hierarchy = build_hierarchy_from_items(
                    parser=self.parser,
                    items=batch_tracker.get_all_items()
                )
                
                st.session_state.lged_import_data = {
                    'hierarchy': hierarchy,
                    'settings': st.session_state.lged_import_settings,  # ← ADD THIS
                    'timestamp': datetime.now().isoformat()
                }
        
        # Navigation
        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            if st.button("◀️ Back to Settings", use_container_width=True, key="lged_back_to_settings"):
                st.session_state.lged_wizard_step = 1
                st.rerun()
    
    def _step3_review_and_edit(self):
        """Step 3: Review and edit extracted data"""
        
        st.markdown("### Step 3: Review & Edit Extracted Data")
        
        data = st.session_state.lged_import_data
        hierarchy = data['hierarchy']
        settings = data['settings']
        
        # Convert to editable format
        df = hierarchy_to_dataframe(hierarchy, source='LGED')  # ← SPECIFY SOURCE
        
        # Show summary
        total_parents = len(df[df['Type'] == 'Parent'])
        total_children = len(df[df['Type'] == 'Child'])
        
        st.info(f"📊 **Summary:** {total_parents} parents, {total_children} children")
        
        # Quick stats cards
        col1, col2, col3, col4 = st.columns(4)
        parent_codes = set(df[df['Type'] == 'Parent']['Code'])
        orphans = df[(df['Type'] == 'Child') & (~df['Parent Code'].isin(parent_codes))]
        
        col1.metric("Parents", total_parents)
        col2.metric("Children", total_children)
        col3.metric("Orphans", len(orphans), delta="⚠️" if len(orphans) > 0 else None)
        
        # FIX: Safely check if Zone-A column exists
        if 'Zone-A' in df.columns:
            has_rates = len(df[df['Zone-A'] != ''])
            col4.metric("Has Rates", has_rates)
        else:
            col4.metric("Has Rates", 0)
        
        # Quick action buttons
        st.markdown("#### 🔧 Quick Fixes")
        col_fix1, col_fix2, col_fix3 = st.columns(3)
        
        with col_fix1:
            if st.button("🔧 Fix Description Spacing", use_container_width=True, key="lged_fix_spacing"):
                df['Description'] = df['Description'].apply(fix_description_spacing)
                st.success("✅ Fixed spacing issues")
                st.rerun()
        
        with col_fix2:
            if len(orphans) > 0:
                if st.button(f"🔧 Auto-fix {len(orphans)} Orphans", use_container_width=True, key="lged_fix_orphans"):
                    first_parent = sorted(parent_codes)[0] if parent_codes else ""
                    df.loc[df['Type'] == 'Child', 'Parent Code'] = df.loc[df['Type'] == 'Child', 'Parent Code'].fillna(first_parent)
                    st.success(f"✅ Assigned orphans to {first_parent}")
                    st.rerun()
        
        with col_fix3:
            if data.get('quick_test', False):
                st.warning("⚠️ Quick Test Mode: Only first 10 pages were parsed")
                if st.button("📑 Import Remaining Pages", use_container_width=True, key="lged_import_remaining"):
                    st.session_state.lged_wizard_step = 2
                    st.rerun()
        
        st.markdown("---")
        
        # Main editable table
        st.markdown("#### 📝 Editable Data Table")
        st.caption("💡 Click any cell to edit. Changes are automatically saved.")
        
        # Get parent options
        parent_options = sorted(df[df['Type'] == 'Parent']['Code'].tolist())
        
        # Column configuration for LGED
        column_config = {
            "Type": st.column_config.SelectboxColumn("Type", options=["Parent", "Child"], width="small"),
            "Code": st.column_config.TextColumn("Code", width="small"),
            "Description": st.column_config.TextColumn("Description", width="large"),
            "Parent Code": st.column_config.SelectboxColumn("Parent", options=[""] + parent_options, width="small"),
            "Unit": st.column_config.SelectboxColumn("Unit", options=["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"], width="small"),
        }
        
        # Add zone columns only if they exist in the dataframe
        if 'PWD Reference' in df.columns:
            column_config["PWD Reference"] = st.column_config.TextColumn("PWD Ref", width="small")
        
        if 'Zone-A' in df.columns:
            column_config["Zone-A"] = st.column_config.NumberColumn("Zone-A (Dhaka)", format="%.2f", width="small")
        if 'Zone-B' in df.columns:
            column_config["Zone-B"] = st.column_config.NumberColumn("Zone-B (Chattogram)", format="%.2f", width="small")
        if 'Zone-C' in df.columns:
            column_config["Zone-C"] = st.column_config.NumberColumn("Zone-C (Rajshahi)", format="%.2f", width="small")
        if 'Zone-D' in df.columns:
            column_config["Zone-D"] = st.column_config.NumberColumn("Zone-D (Khulna)", format="%.2f", width="small")
        
        edited_df = st.data_editor(
            df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key="lged_editor_wizard"
        )
        
        # ✅ CORRECT: Show debug logs HERE (outside the save button)
        if st.session_state.get('show_debug', False):
            from utils.debug_logger import get_debug_logger
            debug_logger = get_debug_logger()
            debug_logger.display_in_streamlit()
        
        # Save changes button
        if st.button("💾 **Save Changes & Continue**", type="primary", use_container_width=True, key="lged_save_changes"):
            st.session_state.lged_import_data['edited_dataframe'] = edited_df
            st.session_state.lged_wizard_step = 4
            st.rerun()

    
    def _step4_validate_and_save(self):
        """Step 4: Validate before saving"""
        
        st.markdown("### Step 4: Validate & Confirm")
        
        data = st.session_state.lged_import_data
        df = data.get('edited_dataframe')
        settings = data.get('settings', {})
        edition_year = settings.get('edition_year')
        version_name = settings.get('version_name', f"LGED Schedule {edition_year}")
        dry_run = settings.get('dry_run', True)
        
        if df is None:
            st.error("No data found. Please go back to Step 3.")
            if st.button("◀️ Back to Review", use_container_width=True, key="lged_back_to_review"):
                st.session_state.lged_wizard_step = 3
                st.rerun()
            return
        
        # Validation checks
        st.markdown("#### ✅ Validation Results")
        
        issues = self._validate_data(df)
        
        if issues:
            st.warning(f"⚠️ Found {len(issues)} issues that need attention:")
            
            for issue in issues[:10]:
                with st.expander(f"📌 {issue['type']}: {issue['code']}"):
                    st.write(issue['message'])
                    if issue.get('suggestion'):
                        st.info(f"💡 Suggestion: {issue['suggestion']}")
            
            if len(issues) > 10:
                st.caption(f"... and {len(issues) - 10} more issues")
            
            if st.button("🔧 Attempt Auto-Fix All Issues", key="lged_attempt_auto_fix"):
                df = self._auto_fix_issues(df)
                st.session_state.lged_import_data['edited_dataframe'] = df
                st.success("✅ Applied auto-fixes")
                st.rerun()
        else:
            st.success("✅ All validation checks passed!")
        
        # Preview what will be saved
        st.markdown("---")
        st.markdown("#### 📋 Data to be Saved")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Parents**")
            parents_df = df[df['Type'] == 'Parent']
            if not parents_df.empty:
                st.dataframe(parents_df[['Code', 'Description']].head(10), use_container_width=True, hide_index=True)
            else:
                st.info("No parent items")
        
        with col2:
            st.markdown("**Children (Sample)**")
            children_df = df[df['Type'] == 'Child']
            if not children_df.empty:
                st.dataframe(children_df[['Code', 'Parent Code', 'Unit']].head(10), use_container_width=True, hide_index=True)
            else:
                st.info("No child items")
        
        st.markdown("---")
        
        # Summary statistics
        st.markdown("#### 📊 Summary Statistics")
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Parents", len(parents_df))
        with col_b:
            st.metric("Children", len(children_df))
        with col_c:
            total_rates = sum(1 for _, row in children_df.iterrows() 
                            for zone in ['Zone-A', 'Zone-B', 'Zone-C', 'Zone-D'] 
                            if row.get(zone) and row[zone] > 0)
            st.metric("Rate Entries", total_rates)
        
        st.markdown("---")
        
        # Action buttons
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            if st.button("◀️ Back to Edit", use_container_width=True, key="lged_back_to_edit"):
                st.session_state.lged_wizard_step = 3
                st.rerun()
        
        with col_btn2:
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Export as CSV",
                csv,
                f"lged_data_{edition_year}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col_btn3:
            if dry_run:
                st.warning("🔍 Dry Run Mode - Uncheck in Step 1 to save")
                st.button("💾 **Save to Database**", disabled=True, use_container_width=True, key="lged_save_to_database_disabled")
            else:
                if st.button("💾 **Save to Database**", type="primary", use_container_width=True, key="lged_save_to_database"):
                    with st.spinner("Saving to database..."):
                        success = self._save_to_database(df, edition_year, version_name)
                        if success:
                            st.success("✅ Data saved successfully!")
                            st.balloons()
                            # Move to rollback options step
                            st.session_state.lged_wizard_step = 5
                            st.rerun()
                        else:
                            st.error("❌ Failed to save data.")

    def _step5_rollback_options(self):
        """Step 5: Rollback and recovery options for LGED"""
        
        st.markdown("### Step 5: Rollback & Recovery")
        st.caption("Manage rollback points and recover previous LGED versions")
        
        from modules.unified_rollback_manager import UnifiedRollbackManager
        rollback_manager = UnifiedRollbackManager(self.db)
        
        # Get LGED versions from database
        conn = self.db.get_connection()
        versions_df = pd.read_sql_query("""
            SELECT id, version_name, edition_year, is_active, created_at
            FROM rate_versions
            WHERE source = 'LGED'
            ORDER BY created_at DESC
        """, conn)
        conn.close()
        
        # Show snapshots
        st.markdown("#### 📸 Available Rollback Snapshots")
        
        snapshots = rollback_manager.get_snapshots(source='LGED')
        
        if not snapshots.empty:
            for _, snapshot in snapshots.iterrows():
                with st.expander(f"📸 {snapshot['snapshot_name']} - {snapshot['created_at'][:16]}", expanded=False):
                    st.write(f"**Created By:** {snapshot['created_by']}")
                    st.write(f"**Description:** {snapshot['description']}")
                    
                    if st.button(f"🔄 Rollback to this snapshot", key=f"rollback_lged_{snapshot['id']}"):
                        success, message = rollback_manager.rollback_to_snapshot(
                            snapshot['id'],
                            st.session_state.get('username', 'admin')
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        else:
            st.info("No rollback snapshots found. Create one in the import settings.")
        
        st.markdown("---")
        
        # Show existing versions
        st.markdown("#### 📜 Previously Imported LGED Versions")
        
        if not versions_df.empty:
            for _, version in versions_df.iterrows():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.write(f"**{version['version_name']}**")
                with col2:
                    st.write(f"Year: {version['edition_year']}")
                with col3:
                    if version['is_active']:
                        st.markdown("✅ **Active**")
                    else:
                        st.markdown("📦 Archived")
                with col4:
                    if not version['is_active']:
                        if st.button(f"Activate", key=f"activate_lged_{version['id']}"):
                            from modules.unified_version_manager import UnifiedVersionManager
                            vm = UnifiedVersionManager(self.db)
                            vm.activate_version(version['id'], st.session_state.get('username', 'admin'))
                            st.success(f"Activated {version['version_name']}")
                            st.rerun()
        else:
            st.info("No previous LGED versions found")
        
        st.markdown("---")
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("◀️ Back to Validation", use_container_width=True, key="lged_back_to_validation"):
                st.session_state.lged_wizard_step = 4
                st.rerun()
        
        with col2:
            if st.button("➡️ Continue to Complete", type="primary", use_container_width=True, key="lged_continue_to_complete"):
                st.session_state.lged_wizard_step = 6
                st.rerun()

    def _excel_step6_complete(self):
        """Step 6: Completion for Excel Import"""
        
        st.markdown("### ✅ Import Complete!")
        
        config = st.session_state.lged_excel_config
        result = st.session_state.get('lged_import_result', {})
        
        st.balloons()
        
        st.success(f"""
        🎉 **Successfully imported {config['version_name']}!**
        
        The LGED rate schedule has been saved to the database and is now available for use.
        """)
        
        # Show saved version info
        st.markdown("#### 📊 Import Statistics")
        
        # Get actual stats from database
        if result.get('success'):
            version_id = result.get('version_id')
            if version_id:
                # Fetch actual stats from database
                conn = self.db.get_connection()
                cursor = conn.cursor()
                
                # Get version info
                cursor.execute("""
                    SELECT total_parents, total_children, total_rates 
                    FROM rate_versions WHERE id = ?
                """, (version_id,))
                stats = cursor.fetchone()
                
                if stats:
                    parents = stats[0] or 0
                    children = stats[1] or 0
                    rates = stats[2] or 0
                else:
                    # Fallback to result stats
                    parents = result.get('total_parents', 0)
                    children = result.get('total_children', 0)
                    rates = result.get('total_rates', 0)
                
                # Also get actual counts from lged_children and lged_parents
                cursor.execute("SELECT COUNT(*) FROM lged_parents WHERE version_id = ?", (version_id,))
                actual_parents = cursor.fetchone()[0] or 0
                
                cursor.execute("SELECT COUNT(*) FROM lged_children WHERE version_id = ?", (version_id,))
                actual_children = cursor.fetchone()[0] or 0
                
                conn.close()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Section Headers", actual_parents)
                    st.caption("(from lged_parents)")
                with col2:
                    st.metric("Rate Items", actual_children)
                    st.caption("(from lged_children)")
                with col3:
                    st.metric("Rate Entries", rates)
                    st.caption("(4 zones per item)")
                
                # Also show version info
                st.markdown("---")
                st.markdown("#### 📌 Version Details")
                st.write(f"**Version Number:** {result.get('version_number', 'N/A')}")
                st.write(f"**Version ID:** {version_id}")
                st.write(f"**Mode:** {result.get('mode', 'N/A')}")
                
        else:
            # Fallback to session state
            saved = st.session_state.get('lged_saved_version', {})
            col1, col2, col3 = st.columns(3)
            col1.metric("Parents", saved.get('parents', 0))
            col2.metric("Children", saved.get('children', 0))
            col3.metric("Rate Entries", saved.get('rates', 0))
        
        st.markdown("---")
        st.markdown("#### 🎯 What would you like to do next?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Import Another Excel File", use_container_width=True):
                # Reset Excel wizard state
                st.session_state.lged_excel_wizard_step = 1
                st.session_state.lged_excel_data = None
                st.session_state.lged_excel_edited_df = None
                if 'lged_import_result' in st.session_state:
                    del st.session_state.lged_import_result
                if 'lged_saved_version' in st.session_state:
                    del st.session_state.lged_saved_version
                st.rerun()
        
        with col2:
            if st.button("📊 Go to Rate Management", use_container_width=True):
                st.session_state.lged_excel_wizard_step = 1
                st.session_state.lged_excel_data = None
                st.rerun()
    # Add these updated methods to your LGEDImportWizard class
    def _save_to_database(self, df, edition_year, version_name):
        """Save LGED data to database"""
        
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
                    'parent_code': row['Parent Code'],
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
            
            final_hierarchy = {
                'parents': parents,
                'children': children
            }
            
            # Save using DatabaseManager (not separate LGERateDBManager)
            version_id = self.db.save_lged_hierarchy(
                final_hierarchy,
                version_name,
                edition_year,
                datetime.now().date()
            )
            
            # Register in unified version management
            total_rates = sum(len(c['rates']) for c in children)
            from modules.unified_version_manager import register_version_after_import
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
            
            st.success(f"✅ Saved {len(parents)} parents and {len(children)} children!")
            st.balloons()
            
            return True
            
        except Exception as e:
            st.error(f"Error saving: {str(e)}")
            return False
    def _clear_version_data(self, version_id):
        """Clear all data for a specific version"""
        return self.db.clear_lged_version_data(version_id)

    def _get_sections_from_db(self, chapter_num: str) -> pd.DataFrame:
        """Get sections for a chapter from LGED tables"""
        try:
            conn = self.db.get_connection()
            
            # Query directly from lged_sections table
            query = """
                SELECT section_number, section_name, description
                FROM lged_sections 
                WHERE chapter_number = ? OR chapter_number = ?
                ORDER BY section_number
            """
            
            df = pd.read_sql_query(query, conn, params=(chapter_num, chapter_num.zfill(2)))
            
            conn.close()
            return df
            
        except Exception as e:
            print(f"Error getting sections: {e}")
            return pd.DataFrame()


    def _get_next_section_number_from_db(self, chapter_num: str) -> str:
        """Get next available section number from database - LGED format like 3.01, 3.02"""
        try:
            conn = self.db.get_connection()
            
            # Get chapter ID
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM rate_chapters 
                WHERE source = 'LGED' AND chapter_number = ?
            """, (chapter_num,))
            
            chapter_row = cursor.fetchone()
            
            if chapter_row:
                chapter_id = chapter_row[0]
                cursor.execute("""
                    SELECT section_number FROM rate_sections 
                    WHERE source = 'LGED' AND chapter_id = ?
                    ORDER BY section_number DESC LIMIT 1
                """, (chapter_id,))
                
                last_section = cursor.fetchone()
                conn.close()
                
                if last_section:
                    last_num = last_section[0]
                    if '.' in last_num:
                        try:
                            # Extract the number after decimal (e.g., "3.01" -> 1, "3.10" -> 10)
                            last_value = int(last_num.split('.')[1])
                            next_num = last_value + 1
                            # Format with leading zero (01, 02, 03...)
                            return f"{chapter_num}.{next_num:02d}"
                        except:
                            pass
            
            conn.close()
            # Default to .01 if no sections exist
            return f"{chapter_num}.01"
            
        except Exception as e:
            print(f"Error getting next section number: {e}")
            return f"{chapter_num}.01"


    def _validate_section_number_format(self, section_number: str, chapter_num: str) -> bool:
        """Validate section number format - LGED uses format like 3.01, 3.02, 3.10"""
        if not section_number or '.' not in section_number:
            return False
        
        parts = section_number.split('.')
        if len(parts) != 2:
            return False
        
        # Check if chapter number matches (as string, case insensitive)
        chapter_match = parts[0] == chapter_num
        
        # Check if second part is valid (01, 02, 03...)
        try:
            section_part = int(parts[1])
            is_valid_section = 1 <= section_part <= 99
        except ValueError:
            is_valid_section = False
        
        return chapter_match and is_valid_section


    def _section_exists_in_db(self, chapter_num: str, section_number: str) -> bool:
        """Check if section exists in database"""
        try:
            conn = self.db.get_connection()
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM rate_sections s
                JOIN rate_chapters c ON s.chapter_id = c.id
                WHERE c.source = 'LGED' 
                AND (c.chapter_number = ? OR c.chapter_number = ?)
                AND s.section_number = ?
            """, (chapter_num, chapter_num.zfill(2), section_number))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
            
        except Exception as e:
            print(f"Error checking section existence: {e}")
            return False

    def generate_import_report(self, selected_chapters, selected_sections, extracted_items, version_name, edition_year):
        """Generate detailed HTML and JSON report of imported data"""
        
        import json
        from datetime import datetime
        
        # Calculate statistics
        total_items = len(extracted_items)
        total_rates = sum(len(item.get('rates', {})) for item in extracted_items)
        
        # Group items by chapter and section
        items_by_chapter = {}
        items_by_section = {}
        
        for item in extracted_items:
            code = item.get('item_code', '')
            if '.' in code:
                chapter = code.split('.')[0]
                section = code
            else:
                chapter = code
                section = 'No Section'
            
            # Group by chapter
            if chapter not in items_by_chapter:
                items_by_chapter[chapter] = []
            items_by_chapter[chapter].append(item)
            
            # Group by section
            if section not in items_by_section:
                items_by_section[section] = []
            items_by_section[section].append(item)
        
        # Generate HTML report
        html_report = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>LGED Import Report - {version_name}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    padding: 20px;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                .summary {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                }}
                .summary-card {{
                    background: rgba(255,255,255,0.2);
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                }}
                .summary-card h3 {{
                    margin: 0 0 10px 0;
                    font-size: 14px;
                    opacity: 0.9;
                }}
                .summary-card .number {{
                    font-size: 32px;
                    font-weight: bold;
                    margin: 0;
                }}
                .section {{
                    margin: 20px 0;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    overflow: hidden;
                }}
                .section-header {{
                    background-color: #3498db;
                    color: white;
                    padding: 10px 15px;
                    cursor: pointer;
                    font-weight: bold;
                }}
                .section-header:hover {{
                    background-color: #2980b9;
                }}
                .section-content {{
                    padding: 15px;
                    display: none;
                }}
                .section-content.show {{
                    display: block;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                th, td {{
                    padding: 10px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #f8f9fa;
                    font-weight: bold;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .rate-badge {{
                    background-color: #27ae60;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    display: inline-block;
                }}
                .zone-rates {{
                    font-size: 12px;
                    color: #666;
                }}
                .timestamp {{
                    text-align: right;
                    color: #666;
                    font-size: 12px;
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                }}
                .expand-all {{
                    background-color: #3498db;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 5px;
                    cursor: pointer;
                    margin-bottom: 10px;
                }}
                .expand-all:hover {{
                    background-color: #2980b9;
                }}
            </style>
            <script>
                function toggleSection(id) {{
                    var element = document.getElementById(id);
                    element.classList.toggle('show');
                }}
                
                function expandAll() {{
                    var contents = document.getElementsByClassName('section-content');
                    for(var i = 0; i < contents.length; i++) {{
                        contents[i].classList.add('show');
                    }}
                }}
                
                function collapseAll() {{
                    var contents = document.getElementsByClassName('section-content');
                    for(var i = 0; i < contents.length; i++) {{
                        contents[i].classList.remove('show');
                    }}
                }}
            </script>
        </head>
        <body>
            <div class="container">
                <h1>📊 LGED Rate Import Report</h1>
                <p><strong>Version:</strong> {version_name}</p>
                <p><strong>Edition Year:</strong> {edition_year}</p>
                <p><strong>Import Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <div class="summary">
                    <div class="summary-card">
                        <h3>📚 Chapters</h3>
                        <p class="number">{len(selected_chapters)}</p>
                    </div>
                    <div class="summary-card">
                        <h3>📑 Sections</h3>
                        <p class="number">{len(selected_sections)}</p>
                    </div>
                    <div class="summary-card">
                        <h3>📄 Items</h3>
                        <p class="number">{total_items}</p>
                    </div>
                    <div class="summary-card">
                        <h3>💰 Rate Entries</h3>
                        <p class="number">{total_rates}</p>
                    </div>
                </div>
                
                <div style="margin-bottom: 10px;">
                    <button class="expand-all" onclick="expandAll()">📖 Expand All</button>
                    <button class="expand-all" onclick="collapseAll()" style="background-color: #95a5a6;">📕 Collapse All</button>
                </div>
        """
        
        # Add selected chapters section
        if selected_chapters:
            html_report += f"""
                <div class="section">
                    <div class="section-header" onclick="toggleSection('chapters-content')">
                        📚 Selected Chapters ({len(selected_chapters)})
                    </div>
                    <div id="chapters-content" class="section-content">
                        <table>
                            <thead>
                                <tr><th>Chapter Number</th><th>Chapter Name</th><th>Description</th></tr>
                            </thead>
                            <tbody>
            """
            for chapter_num, chapter_info in selected_chapters.items():
                html_report += f"""
                    <tr>
                        <td><strong>{chapter_num}</strong></td>
                        <td>{chapter_info.get('name', '')}</td>
                        <td>{chapter_info.get('description', '')[:100]}</td>
                    </tr>
                """
            html_report += "</tbody></table></div></div>"
        
        # Add selected sections section
        if selected_sections:
            html_report += f"""
                <div class="section">
                    <div class="section-header" onclick="toggleSection('sections-content')">
                        📑 Selected Sections ({len(selected_sections)})
                    </div>
                    <div id="sections-content" class="section-content">
                        <table>
                            <thead><tr><th>Section Number</th><th>Section Name</th><th>Chapter</th><th>Description</th></tr></thead>
                            <tbody>
            """
            for section_num, section_info in selected_sections.items():
                html_report += f"""
                    <tr>
                        <td><strong>{section_num}</strong></td>
                        <td>{section_info.get('name', '')}</td>
                        <td>{section_info.get('chapter', '')}</td>
                        <td>{section_info.get('description', '')[:100]}</td>
                    </tr>
                """
            html_report += "</tbody></table></div></div>"
        
        # Add items by chapter
        html_report += f"""
            <div class="section">
                <div class="section-header" onclick="toggleSection('items-content')">
                    📄 Imported Items ({total_items})
                </div>
                <div id="items-content" class="section-content">
        """
        
        for chapter, items in items_by_chapter.items():
            html_report += f"""
                <h3>Chapter {chapter}</h3>
                <table>
                    <thead>
                        <tr><th>Code</th><th>Description</th><th>Unit</th><th>Zone Rates</th></tr>
                    </thead>
                    <tbody>
            """
            for item in items:
                rates = item.get('rates', {})
                rate_text = ', '.join([f"{k}: {v:,.2f}" for k, v in rates.items()]) if rates else "No rates"
                html_report += f"""
                    <tr>
                        <td><strong>{item.get('item_code', '')}</strong></td>
                        <td>{item.get('description', '')[:80]}...</td>
                        <td>{item.get('unit', '')}</td>
                        <td class="zone-rates">{rate_text}</td>
                    </tr>
                """
            html_report += "</tbody></table><br>"
        
        html_report += """
                </div>
            </div>
            
            <div class="timestamp">
                Report generated by TenderAI LGED Import Wizard
            </div>
            </div>
        </body>
        </html>
        """
        
        # Generate JSON report
        json_report = {
            "import_info": {
                "version_name": version_name,
                "edition_year": edition_year,
                "import_timestamp": datetime.now().isoformat(),
                "source": "LGED Excel Import"
            },
            "summary": {
                "total_chapters": len(selected_chapters),
                "total_sections": len(selected_sections),
                "total_items": total_items,
                "total_rate_entries": total_rates
            },
            "chapters": [
                {
                    "number": num,
                    "name": info.get('name', ''),
                    "description": info.get('description', '')
                }
                for num, info in selected_chapters.items()
            ],
            "sections": [
                {
                    "number": num,
                    "name": info.get('name', ''),
                    "chapter": info.get('chapter', ''),
                    "description": info.get('description', '')
                }
                for num, info in selected_sections.items()
            ],
            "items": [
                {
                    "code": item.get('item_code', ''),
                    "description": item.get('description', ''),
                    "unit": item.get('unit', ''),
                    "rates": item.get('rates', {})
                }
                for item in extracted_items
            ],
            "items_by_chapter": {
                chapter: [
                    {
                        "code": item.get('item_code', ''),
                        "description": item.get('description', ''),
                        "unit": item.get('unit', '')
                    }
                    for item in items
                ]
                for chapter, items in items_by_chapter.items()
            }
        }
        
        return html_report, json_report

    def save_import_report(self, html_report, json_report, version_name):
        """Save import reports to files"""
        import os
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"{version_name.replace(' ', '_')}_{timestamp}"
        
        # Save HTML report
        html_path = f"reports/{base_filename}.html"
        os.makedirs("reports", exist_ok=True)
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        # Save JSON report
        json_path = f"reports/{base_filename}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)
        
        return html_path, json_path

