# modules/pwd_import_wizard.py - Fully Refactored to use SystemRateCRUD

import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from database.unified_db_manager import get_db_manager


class PWDImportWizard:
    """PWD Rate Schedule Import Wizard for Excel files with chapter-based replacement"""
    
    def __init__(self, db_instance=None):
        self.db = db_instance or get_db_manager()  # ✅ Use cached db manager
        self.rollback_manager = None
    
    def render(self):
        """Render the PWD import wizard"""
        
        st.markdown("""
        <div class="main-header">
            <h1>🏗️ PWD Rate Schedule Import Wizard</h1>
            <p>Step-by-step guide to import, validate, and update PWD rates from Excel files</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize session state
        if 'pwd_wizard_step' not in st.session_state:
            st.session_state.pwd_wizard_step = 1
        if 'pwd_excel_data' not in st.session_state:
            st.session_state.pwd_excel_data = None
        if 'pwd_excel_edited_df' not in st.session_state:
            st.session_state.pwd_excel_edited_df = None
        
        self._render_wizard()
    
    def _render_wizard(self):
        """Render the PWD import wizard with step indicators"""
        
        steps = [
            ("1️⃣ Upload", 1),
            ("2️⃣ Map Data", 2),
            ("3️⃣ Review & Edit", 3),
            ("4️⃣ Validate", 4),
            ("5️⃣ Rollback", 5),
            ("6️⃣ Complete", 6)
        ]
        
        cols = st.columns(len(steps))
        for i, (label, step_num) in enumerate(steps):
            with cols[i]:
                if step_num < st.session_state.pwd_wizard_step:
                    st.markdown(f"✅ **{label}**")
                elif step_num == st.session_state.pwd_wizard_step:
                    st.markdown(f"🔵 **{label}**")
                else:
                    st.markdown(f"⚪ {label}")
        
        st.markdown("---")
        
        # Render current step
        if st.session_state.pwd_wizard_step == 1:
            self._step1_upload()
        elif st.session_state.pwd_wizard_step == 2:
            self._step2_map_data()
        elif st.session_state.pwd_wizard_step == 3:
            self._step3_review_edit()
        elif st.session_state.pwd_wizard_step == 4:
            self._step4_validate()
        elif st.session_state.pwd_wizard_step == 5:
            self._step5_rollback()
        elif st.session_state.pwd_wizard_step == 6:
            self._step6_complete()
    
    # =========================================================
    # STEP 1: UPLOAD
    # =========================================================
    
    def _step1_upload(self):
        """Step 1: Upload Excel file with Chapter selection"""
        st.markdown("### Step 1: Upload Excel File")
        st.caption("Upload a PWD Excel file with rate data")

        uploaded_file = st.file_uploader(
            "📄 **Select PWD Excel File**",
            type=["xlsx", "xls"],
            help="Upload Excel file in PWD format",
            key="pwd_excel_upload"
        )

        if uploaded_file:
            temp_path = f"temp_pwd_excel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            try:
                preview_df = pd.read_excel(temp_path, nrows=5)
                st.markdown("#### 📋 File Preview")
                st.dataframe(preview_df, use_container_width=True)
                st.success(f"✅ File loaded: {uploaded_file.name}")

                st.session_state.pwd_excel_temp_path = temp_path
                st.session_state.pwd_excel_filename = uploaded_file.name
            except Exception as e:
                st.error(f"Error reading file: {e}")
                return

            st.markdown("---")
            st.markdown("### ⚙️ Import Configuration")

            col1, col2 = st.columns(2)
            with col1:
                edition_year = st.number_input("📅 Edition Year", min_value=2020, max_value=2030, value=2022)
            with col2:
                version_name = st.text_input("📌 Version Name", value=f"PWD Schedule {edition_year}")

            st.markdown("---")
            st.markdown("### 📚 Chapter Selection")

            # ✅ Use SystemRateCRUD for chapters
            chapters = self.db.get_pwd_chapters_dict()

            if not chapters:
                st.error("❌ No chapters found in database. Please add chapters first.")
                st.info("Go to **Rate Management → Chapters** tab to add PWD chapters.")
                return

            st.success(f"✅ Loaded {len(chapters)} chapters successfully")

            chapter_options = []
            for ch in chapters:
                ch_num = str(ch.get('chapter_number', '')).strip()
                ch_name = str(ch.get('chapter_name', '')).strip()
                if (ch_num and ch_name and 
                    ch_num.lower() not in ['nan', 'none', 'null', ''] and
                    ch_name.lower() not in ['nan', 'none', 'null', 'chapter_name']):
                    chapter_options.append(f"{ch_num} - {ch_name}")

            if not chapter_options:
                st.error("❌ No valid chapters found")
                return

            selected_chapter_option = st.selectbox(
                "Select Chapter (Required)",
                options=chapter_options,
                key="pwd_chapter_select"
            )

            if selected_chapter_option and st.button("➡️ Next: Extract & Map Data", type="primary", use_container_width=True):
                try:
                    chapter_num = selected_chapter_option.split(" - ")[0].strip()
                    if chapter_num.isdigit():
                        chapter_num = chapter_num.zfill(2)

                    st.session_state.pwd_excel_config = {
                        'edition_year': edition_year,
                        'version_name': version_name,
                        'chapter_num': chapter_num,
                        'temp_path': temp_path,
                        'filename': uploaded_file.name
                    }

                    with st.spinner("Extracting data from Excel..."):
                        extracted_items = self._extract_excel_data(temp_path, chapter_num)
                        if extracted_items:
                            st.session_state.pwd_excel_data = extracted_items
                            st.session_state.pwd_wizard_step = 2
                            st.rerun()
                        else:
                            st.error("No data extracted from Excel file")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    # =========================================================
    # EXCEL EXTRACTION
    # =========================================================
    
    def _extract_excel_data(self, file_path: str, chapter_num: str) -> List[Dict[str, Any]]:
        """Extract data from PWD Excel file"""
        import re
        
        df = pd.read_excel(file_path, sheet_name=0, header=None, dtype=str)
        extracted_items = []
        
        # Find the header row
        header_row_idx = None
        for idx, row in df.iterrows():
            row_values = row.astype(str).tolist()
            if 'Item No.' in str(row_values[0]) or 'Item Code' in str(row_values[0]):
                header_row_idx = idx
                break
        
        if header_row_idx is None:
            header_row_idx = 0
        
        def get_rate_value(val):
            if pd.isna(val) or val == 'nan' or val == '':
                return None
            try:
                cleaned = str(val).replace(',', '').replace('Tk.', '').replace('tk.', '').strip()
                match = re.search(r'[\d,]+\.?\d*', cleaned)
                if match:
                    cleaned = match.group().replace(',', '')
                return float(cleaned)
            except:
                return None
        
        # Process each row after header
        for idx in range(header_row_idx + 1, len(df)):
            row = df.iloc[idx]
            
            item_code = str(row[0]) if pd.notna(row[0]) else ''
            item_code = item_code.strip()
            
            if not item_code or item_code == 'nan':
                continue
            
            if re.match(r'^\d{4}-\d{2}-\d{2}', item_code):
                continue
            
            if item_code in ['1', '2', '3', '4', '5', '6', '7', '8', '9'] and '.' not in item_code:
                continue
            
            if '.' not in item_code:
                continue
            
            description = str(row[1]) if pd.notna(row[1]) else ''
            description = description.strip()
            if description == 'nan':
                description = ''
            description = ' '.join(description.split())
            
            unit = str(row[2]) if pd.notna(row[2]) else ''
            unit = unit.strip()
            if unit == 'nan':
                unit = ''
            
            zone_a = get_rate_value(row[3]) if len(row) > 3 else None
            zone_b = get_rate_value(row[4]) if len(row) > 4 else None
            zone_c = get_rate_value(row[5]) if len(row) > 5 else None
            zone_d = get_rate_value(row[6]) if len(row) > 6 else None
            
            has_rates = any([zone_a, zone_b, zone_c, zone_d])
            
            parent_code = None
            if '.' in item_code:
                parts = item_code.split('.')
                if len(parts) >= 2:
                    parent_code = '.'.join(parts[:-1])
            
            extracted_items.append({
                'item_code': item_code,
                'description': description,
                'unit': unit,
                'zone_a': zone_a,
                'zone_b': zone_b,
                'zone_c': zone_c,
                'zone_d': zone_d,
                'has_rates': has_rates,
                'parent_code': parent_code,
                'chapter_number': chapter_num
            })
        
        items_with_rates = len([i for i in extracted_items if i.get('has_rates')])
        items_without_rates = len([i for i in extracted_items if not i.get('has_rates')])
        
        st.info(f"✅ Extracted {len(extracted_items)} items ({items_with_rates} with rates, {items_without_rates} parent headers)")
        
        return extracted_items
    
    # =========================================================
    # STEP 2: MAP DATA
    # =========================================================
    
    def _step2_map_data(self):
        """Step 2: Map Data Fields & Define Relationships"""
        
        st.markdown("### Step 2: Map Data Fields & Define Relationships")
        st.caption("Verify extracted data and define parent-child relationships")
        
        extracted_items = st.session_state.pwd_excel_data
        config = st.session_state.pwd_excel_config
        
        if not extracted_items:
            st.error("No data found. Please go back to Step 1.")
            if st.button("◀️ Back to Upload"):
                st.session_state.pwd_wizard_step = 1
                st.rerun()
            return
        
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
            st.metric("Parent Headers", len(items_without_rates))
        
        with st.expander("📋 View Extracted Data Preview", expanded=False):
            preview_df = df[['item_code', 'description', 'unit', 'zone_a', 'zone_b', 'zone_c', 'zone_d', 'has_rates']].head(10)
            st.dataframe(preview_df, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🔗 Define Parent-Child Relationships")
        
        relationship_method = st.radio(
            "Select method:",
            options=[
                ("🤖 Auto-Detect (Recommended)", "auto"),
                ("✏️ Manual Assignment", "manual"),
                ("📝 Edit in Table", "table")
            ],
            format_func=lambda x: x[0],
            key="pwd_relationship_method"
        )
        
        if isinstance(relationship_method, tuple):
            relationship_method = relationship_method[1]
        
        assigned_items = []
        
        if relationship_method == "auto":
            st.info("🤖 **Auto-Detect Mode:** System will automatically assign parents based on code patterns.")
            st.caption("Example: '01.1.1' → Parent: '01.1'")
            
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
            st.info("✏️ **Manual Assignment Mode:** Select parent for each child item.")
            
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
                            key=f"pwd_parent_{row['temp_id']}"
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
            st.info("📝 **Table Edit Mode:** Edit parent_code directly in the table.")
            
            table_data = []
            for _, row in df.iterrows():
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
                key="pwd_parent_editor",
                column_config={
                    "item_code": st.column_config.TextColumn("Item Code", disabled=True, width="small"),
                    "description": st.column_config.TextColumn("Description", width="large"),
                    "unit": st.column_config.TextColumn("Unit", width="small"),
                    "has_rates": st.column_config.CheckboxColumn("Has Rates", disabled=True, width="small"),
                    "parent_code": st.column_config.TextColumn("Parent Code", width="small", 
                                                            help="Enter parent code"),
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
                st.metric("Parent Headers", parents_count)
            with col2:
                children_count = len(result_df[result_df['parent_code'].notna() & (result_df['parent_code'] != '')])
                st.metric("Child Items", children_count)
            with col3:
                orphan_count = len(result_df[result_df['has_rates'] & (result_df['parent_code'].isna() | result_df['parent_code'] == '')])
                st.metric("Leaf Items", orphan_count)
            with col4:
                st.metric("Total Items", len(result_df))
        
        if relationship_method != "table":
            if st.button("🔄 Switch to Different Method", use_container_width=True):
                st.rerun()
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("◀️ Back to Upload", use_container_width=True):
                if os.path.exists(config['temp_path']):
                    os.remove(config['temp_path'])
                st.session_state.pwd_wizard_step = 1
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
                        'has_rates': row['has_rates'],
                        'parent_code': row['parent_code'] if pd.notna(row['parent_code']) and row['parent_code'] != '' else None
                    })
                
                st.session_state.pwd_excel_data = final_items
                st.session_state.pwd_wizard_step = 3
                st.rerun()
    
    # =========================================================
    # STEP 3: REVIEW & EDIT
    # =========================================================
    
    def _step3_review_edit(self):
        """Step 3: Review and edit extracted data with export option"""
        
        st.markdown("### Step 3: Review & Edit Data")
        st.caption("Double-click any cell to edit values. Use export to verify against original Excel file.")
        
        extracted_items = st.session_state.pwd_excel_data
        config = st.session_state.pwd_excel_config
        
        if not extracted_items:
            st.error("No data found. Please go back to Step 2.")
            if st.button("◀️ Back to Map Data"):
                st.session_state.pwd_wizard_step = 2
                st.rerun()
            return
        
        df = pd.DataFrame(extracted_items)
        
        expected_cols = ['item_code', 'description', 'unit', 'zone_a', 'zone_b', 'zone_c', 'zone_d', 
                        'parent_code', 'has_rates', 'dot_count']
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
        st.caption("💡 Tip: Set 'parent_code' to establish parent-child relationships (e.g., '01.1' for '01.1.1')")
        
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            key="pwd_editor",
            column_config={
                "item_code": st.column_config.TextColumn("Item Code", width="small", disabled=True),
                "description": st.column_config.TextColumn("Description", width="large"),
                "unit": st.column_config.TextColumn("Unit", width="small"),
                "parent_code": st.column_config.TextColumn("Parent Code", width="small", 
                                                        help="Enter parent code (e.g., '01.1' for child items)"),
                "zone_a": st.column_config.NumberColumn("Zone-A (Dhaka)", format="%.2f", width="small"),
                "zone_b": st.column_config.NumberColumn("Zone-B (Chattogram)", format="%.2f", width="small"),
                "zone_c": st.column_config.NumberColumn("Zone-C (Khulna)", format="%.2f", width="small"),
                "zone_d": st.column_config.NumberColumn("Zone-D (Rajshahi)", format="%.2f", width="small"),
                "has_rates": st.column_config.CheckboxColumn("Has Rates", disabled=True, width="small"),
                "is_parent": st.column_config.CheckboxColumn("Is Parent", disabled=True, width="small"),
                "is_child": st.column_config.CheckboxColumn("Is Child", disabled=True, width="small"),
                "dot_count": st.column_config.NumberColumn("Dots", disabled=True, width="small"),
            }
        )
        
        st.session_state.pwd_excel_edited_df = edited_df
        
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
        
        st.markdown("---")
        st.markdown("#### 💾 Export Data for Verification")
        
        col_export1, col_export2, col_export3 = st.columns(3)
        
        with col_export1:
            csv_data = edited_df.to_csv(index=False)
            st.download_button(
                label="📥 Export to CSV",
                data=csv_data,
                file_name=f"pwd_export_{config['chapter_num']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="pwd_export_csv"
            )
        
        with col_export2:
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                edited_df.to_excel(writer, sheet_name='PWD_Data', index=False)
                summary_data = {
                    'Metric': ['Chapter', 'Total Items', 'With Rates', 'Parent Headers', 'Child Items', 'Leaf Items', 'Export Date'],
                    'Value': [config['chapter_num'], total_items, items_with_rates, parents, children_with_parents, leaf_items, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            output.seek(0)
            st.download_button(
                label="📊 Export to Excel",
                data=output.getvalue(),
                file_name=f"pwd_export_{config['chapter_num']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="pwd_export_excel"
            )
        
        with col_export3:
            json_data = edited_df.to_json(orient='records', indent=2)
            st.download_button(
                label="📋 Export to JSON",
                data=json_data,
                file_name=f"pwd_export_{config['chapter_num']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
                key="pwd_export_json"
            )
        
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
                st.session_state.pwd_wizard_step = 2
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
                
                st.session_state.pwd_wizard_step = 4
                st.rerun()
    
    # =========================================================
    # STEP 4: VALIDATE
    # =========================================================
    
    def _step4_validate(self):
        """Step 4: Validate and confirm with chapter-based replacement"""
        
        st.markdown("### Step 4: Validate & Confirm")
        
        edited_df = st.session_state.pwd_excel_edited_df
        config = st.session_state.pwd_excel_config
        
        if edited_df is None:
            st.error("No data found. Please go back to Step 3.")
            if st.button("◀️ Back to Review"):
                st.session_state.pwd_wizard_step = 3
                st.rerun()
            return
        
        total_items = len(edited_df)
        items_with_rates = len(edited_df[edited_df['has_rates'] == True])
        parents = len(edited_df[(edited_df['has_rates'] == False) & (edited_df['dot_count'] >= 1)])
        
        # ✅ Use SystemRateCRUD for version history
        versions = self.db.get_rate_versions_dict('PWD')
        versions_df = pd.DataFrame(versions) if versions else pd.DataFrame()
        if not versions_df.empty and 'edition_year' in versions_df.columns:
            versions_df = versions_df[versions_df['edition_year'] == config['edition_year']]
        
        st.markdown("### 🔄 Import Mode Selection")
        
        import_mode = st.radio(
            "Select import mode:",
            options=[
                ("🆕 Create New Version (Keep existing versions)", "new_version"),
                ("🔄 Update Chapter in Existing Version", "update_chapter")
            ],
            format_func=lambda x: x[0],
            key="pwd_import_mode"
        )
        
        if isinstance(import_mode, tuple):
            import_mode = import_mode[1]
        
        version_id = None
        version_number = None
        confirm_update = False
        
        if import_mode == "update_chapter":
            if versions_df.empty:
                st.error("❌ No existing versions found. Please create a new version first.")
                import_mode = "new_version"
            else:
                st.info(f"📊 Existing versions for PWD {config['edition_year']}:")
                display_df = versions_df.copy()
                if 'is_active' in display_df.columns:
                    display_df['is_active'] = display_df['is_active'].apply(lambda x: "✅ Active" if x else "📦 Archived")
                st.dataframe(display_df[['version_number', 'is_active', 'created_at', 'total_items']], 
                            use_container_width=True, hide_index=True)
                
                version_options = []
                for _, row in versions_df.iterrows():
                    version_options.append({
                        'id': row['id'],
                        'number': row['version_number'],
                        'label': f"Version {row['version_number']} ({'Active' if row['is_active'] else 'Archived'})"
                    })
                
                selected_version = st.selectbox(
                    "Select version to update:",
                    options=version_options,
                    format_func=lambda x: x['label'],
                    key="pwd_version_select"
                )
                
                version_id = selected_version['id']
                version_number = selected_version['number']
                
                st.warning(f"""
                ⚠️ **YOU ARE ABOUT TO REPLACE THE FOLLOWING DATA IN VERSION {version_number}:**
                
                | Item | Value |
                |------|-------|
                | **Edition Year** | {config['edition_year']} |
                | **Version** | {version_number} |
                | **Chapter** | **Chapter {config['chapter_num']}** |
                
                **What will be replaced:**
                - ✅ **ENTIRE Chapter {config['chapter_num']}** (all items in this chapter)
                - ✅ Other chapters will remain **UNCHANGED**
                
                **Data being imported:**
                - Total Items: {total_items}
                - Items with Rates: {items_with_rates}
                - Parent Headers: {parents}
                """)
                
                confirm_update = st.checkbox(
                    f"✓ I understand that I am REPLACING Chapter {config['chapter_num']} in Version {version_number}",
                    key="confirm_pwd_chapter_update"
                )
        
        st.markdown("---")
        st.markdown("#### 📋 Data to be Saved")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Configuration**")
            st.write(f"Version Name: {config['version_name']}")
            st.write(f"Edition Year: {config['edition_year']}")
            st.write(f"Chapter: {config['chapter_num']}")
            if import_mode == "update_chapter" and version_id:
                st.write(f"**Action:** Update Version {version_number}")
                st.write(f"**Scope:** Chapter {config['chapter_num']} (ENTIRE CHAPTER)")
            else:
                st.write(f"**Action:** Create New Version")
        
        with col2:
            st.markdown("**Statistics**")
            st.write(f"Total Items: {total_items}")
            st.write(f"Items with Rates: {items_with_rates}")
            st.write(f"Parent Headers: {parents}")
        
        notes = st.text_area("Notes (optional)", key="pwd_import_notes")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("◀️ Back to Edit", use_container_width=True):
                st.session_state.pwd_wizard_step = 3
                st.rerun()
        
        with col2:
            button_disabled = import_mode == "update_chapter" and not confirm_update
            if st.button("💾 **Import to Database**", type="primary", use_container_width=True, disabled=button_disabled):
                
                hierarchy = self._build_hierarchy_from_df(edited_df, config['chapter_num'])
                
                with st.spinner("Saving to database..."):
                    if import_mode == "update_chapter" and version_id:
                        # ✅ Use SystemRateCRUD for chapter update
                        result = self._update_pwd_chapter(
                            hierarchy, version_id, config['edition_year'], 
                            config['chapter_num'], notes
                        )
                    else:
                        # ✅ Use SystemRateCRUD for new version
                        try:
                            result_version_id = self.db.save_pwd_hierarchy_enhanced(
                                hierarchy=hierarchy,
                                version_name=config['version_name'],
                                edition_year=config['edition_year'],
                                effective_date=datetime.now().date(),
                                selected_chapters={config['chapter_num']: {'name': f"Chapter {config['chapter_num']}"}}
                            )
                            result = {
                                'success': True, 
                                'version_id': result_version_id, 
                                'message': "Import successful"
                            }
                        except Exception as e:
                            result = {'success': False, 'message': str(e)}
                    
                    if result.get('success'):
                        st.success("✅ Data imported successfully!")
                        st.balloons()
                        st.session_state.pwd_wizard_step = 6
                        st.rerun()
                    else:
                        st.error(f"❌ Import failed: {result.get('message', 'Unknown error')}")
    
    def _build_hierarchy_from_df(self, df, chapter_num):
        """Build hierarchy from DataFrame"""
        hierarchy = {
            'parents': [],
            'children': []
        }
        
        parent_codes = set()
        
        for _, row in df.iterrows():
            if row.get('has_rates', False):
                rates = {}
                if pd.notna(row.get('zone_a')) and row.get('zone_a'):
                    rates['Zone-A'] = row['zone_a']
                if pd.notna(row.get('zone_b')) and row.get('zone_b'):
                    rates['Zone-B'] = row['zone_b']
                if pd.notna(row.get('zone_c')) and row.get('zone_c'):
                    rates['Zone-C'] = row['zone_c']
                if pd.notna(row.get('zone_d')) and row.get('zone_d'):
                    rates['Zone-D'] = row['zone_d']
                
                parent_code = row.get('parent_code') if pd.notna(row.get('parent_code')) and row.get('parent_code') != '' else None
                
                hierarchy['children'].append({
                    'pwd_code': row['item_code'],
                    'parent_code': parent_code,
                    'description': row.get('description', '') if pd.notna(row.get('description')) else '',
                    'unit': row.get('unit', '') if pd.notna(row.get('unit')) else '',
                    'rates': rates
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
        
        for parent_code in parent_codes:
            if not any(p['code'] == parent_code for p in hierarchy['parents']):
                hierarchy['parents'].append({
                    'code': parent_code,
                    'description': f"Parent {parent_code}",
                    'chapter': chapter_num
                })
        
        return hierarchy
    
    def _update_pwd_chapter(self, hierarchy, version_id, edition_year, chapter_num, notes=""):
        """Update ONLY one chapter in an existing version using SystemRateCRUD"""
        try:
            # ✅ Use SystemRateCRUD method
            result = self.db.update_pwd_chapter(
                version_id=version_id,
                chapter_num=chapter_num,
                hierarchy=hierarchy,
                edition_year=edition_year,
                notes=notes,
                updated_by=st.session_state.get('username', 'admin')
            )
            
            return result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': str(e)}
    
    # =========================================================
    # STEP 5: ROLLBACK
    # =========================================================
    
    def _step5_rollback(self):
        """Step 5: Rollback options"""
        
        st.markdown("### Step 5: Rollback & Recovery")
        st.caption("Manage rollback points and recover previous versions")
        
        st.info("Rollback functionality: You can restore previous versions from the Rate Management section.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("◀️ Back to Validate", use_container_width=True):
                st.session_state.pwd_wizard_step = 4
                st.rerun()
        
        with col2:
            if st.button("➡️ Complete Import", type="primary", use_container_width=True):
                st.session_state.pwd_wizard_step = 6
                st.rerun()
    
    # =========================================================
    # STEP 6: COMPLETE
    # =========================================================
    
    def _step6_complete(self):
        """Step 6: Completion"""
        
        st.markdown("### ✅ Import Complete!")
        
        config = st.session_state.pwd_excel_config
        
        st.balloons()
        
        st.success(f"""
        🎉 **Successfully imported {config['version_name']}!**
        
        The PWD rate schedule has been saved to the database and is now available for use.
        """)
        
        st.markdown("---")
        st.markdown("#### 🎯 What would you like to do next?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Import Another PWD File", use_container_width=True):
                st.session_state.pwd_wizard_step = 1
                st.session_state.pwd_excel_data = None
                st.session_state.pwd_excel_edited_df = None
                st.rerun()
        
        with col2:
            if st.button("📊 Go to Rate Management", use_container_width=True):
                st.session_state.pwd_wizard_step = 1
                st.session_state.pwd_excel_data = None
                st.rerun()


def render_pwd_import_wizard(db=None):
    """Convenience function to render PWD import wizard"""
    if db is None:
        db = get_db_manager()
    wizard = PWDImportWizard(db)
    wizard.render()