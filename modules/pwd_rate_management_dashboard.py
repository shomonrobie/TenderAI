import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime

class PWDManagementDashboard:
    """Dedicated dashboard for managing PWD rate schedule parent-child relationships"""
    
    def __init__(self, db_instance, parser_instance):
        self.db = db_instance
        self.parser = parser_instance  # Use your existing PWDParserWithHierarchy
    
    def render(self):
        """Main dashboard render method"""
        
        st.markdown("""
        <div class="main-header">
            <h1>🏗️ PWD Rate Schedule Management</h1>
            <p>Import, edit, and manage parent-child relationships in PWD schedule</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize session state
        if 'pwd_edit_data' not in st.session_state:
            st.session_state.pwd_edit_data = None
        if 'pwd_edit_edition' not in st.session_state:
            st.session_state.pwd_edit_edition = 2022
        if 'pwd_dry_run' not in st.session_state:
            st.session_state.pwd_dry_run = True
        
        # Create tabs for workflow
        tab1, tab2, tab3 = st.tabs([
            "📥 1. Import & Parse",
            "✏️ 2. Edit Data",
            "🗄️ 3. Export & Save"
        ])
        
        with tab1:
            self.render_import_section()
        
        with tab2:
            if st.session_state.pwd_edit_data is not None:
                self.render_tabular_editor()
            else:
                st.info("📁 No data loaded. Please import a PDF in the 'Import & Parse' tab.")
        
        with tab3:
            self.render_export_section()
    
    def render_import_section(self):
        """Render import section with dry run and page selection"""
        
        st.markdown("### 📥 Import PWD Schedule")
        
        uploaded_file = st.file_uploader(
            "Upload PWD Rate Schedule PDF", 
            type=["pdf"], 
            key="pwd_import"
        )
        
        if not uploaded_file:
            st.info("📁 Please upload a PWD rate schedule PDF file")
            return
        
        # Configuration options
        st.markdown("#### Configuration")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            edition_year = st.number_input(
                "Edition Year", 
                min_value=2020, 
                max_value=2030, 
                value=2022,
                help="Select the year of the rate schedule"
            )
        
        with col2:
            # Page selection options
            parse_option = st.radio(
                "Pages to Parse",
                options=["All Pages", "First N Pages"],
                help="Choose which pages to parse"
            )
            
            if parse_option == "First N Pages":
                max_pages = st.number_input(
                    "Number of Pages", 
                    min_value=1, 
                    max_value=500, 
                    value=10,
                    help="Process only first N pages (faster for testing)"
                )
            else:
                max_pages = None  # All pages
        
        with col3:
            # Dry run mode
            dry_run = st.checkbox(
                "🔍 Dry Run Mode (Preview only, no database save)", 
                value=st.session_state.pwd_dry_run,
                help="Simulate parsing without writing to database"
            )
            st.session_state.pwd_dry_run = dry_run
            
            parse_clicked = st.button("🚀 Parse PDF", type="primary", use_container_width=True)
        
        # Parse button action
        if parse_clicked:
            temp_path = "temp_pwd_edit.pdf"
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            try:
                with st.spinner("Parsing PDF..."):
                    # Use your existing parser
                    hierarchy = self.parser.parse_pdf_with_hierarchy(temp_path, max_pages)
                    
                    if hierarchy.get('parents'):
                        # Convert to editable DataFrame
                        edit_data = self._convert_to_editable_dataframe(hierarchy)
                        
                        st.session_state.pwd_edit_data = edit_data
                        st.session_state.pwd_edit_edition = edition_year
                        st.session_state.pwd_original_hierarchy = hierarchy
                        st.session_state.pwd_parse_info = {
                            'pages_parsed': max_pages if max_pages else "All",
                            'parents_count': len(hierarchy['parents']),
                            'children_count': len(hierarchy['children']),
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        st.success(f"✅ Parsed {len(hierarchy['parents'])} parents and {len(hierarchy['children'])} children")
                        
                        # Show summary
                        self._show_parse_summary(hierarchy, parse_option, max_pages)
                        
                        if dry_run:
                            st.info("🔍 Dry Run Mode: Data is ready for review. Go to 'Edit Data' tab to verify.")
                        else:
                            st.info("✅ Data parsed successfully. Go to 'Edit Data' tab to review before saving.")
                    else:
                        st.warning("No items found. Try increasing pages.")
                        
            except Exception as e:
                st.error(f"Error: {str(e)}")
                import traceback
                with st.expander("Debug Information"):
                    st.code(traceback.format_exc())
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        # Show existing parsed data info
        if st.session_state.pwd_edit_data is not None and not parse_clicked:
            st.markdown("---")
            st.info("📦 Current data loaded from previous parse")
            if 'pwd_parse_info' in st.session_state:
                info = st.session_state.pwd_parse_info
                col1, col2, col3 = st.columns(3)
                col1.metric("Parents", info.get('parents_count', 0))
                col2.metric("Children", info.get('children_count', 0))
                col3.metric("Pages", info.get('pages_parsed', 'N/A'))
            
            if st.button("🗑️ Clear Current Data"):
                st.session_state.pwd_edit_data = None
                st.session_state.pwd_edit_edition = 2022
                if 'pwd_parse_info' in st.session_state:
                    del st.session_state.pwd_parse_info
                st.rerun()
    
    def _show_parse_summary(self, hierarchy, parse_option, max_pages):
        """Show summary of parsing results"""
        
        st.markdown("#### 📊 Parse Summary")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Parents", len(hierarchy['parents']))
        col2.metric("Children", len(hierarchy['children']))
        col3.metric("Total Items", len(hierarchy['parents']) + len(hierarchy['children']))
        
        # Show sample
        with st.expander("Preview First 5 Parents", expanded=False):
            for parent in hierarchy['parents'][:5]:
                child_count = len([c for c in hierarchy['children'] if c.get('parent_code') == parent['code']])
                st.text(f"📁 {parent['code']}: {parent['description'][:80]}... ({child_count} children)")
    
    def _convert_to_editable_dataframe(self, hierarchy):
        """Convert hierarchy to editable DataFrame format"""
        
        rows = []
        
        # Add parents first
        for parent in hierarchy['parents']:
            rows.append({
                'Type': 'Parent',
                'Code': parent['code'],
                'Description': self._fix_description_spacing(parent['description']),
                'Parent Code': '',
                'Unit': '',
                'Dhaka Rate': '',
                'Chattogram Rate': '',
                'Khulna Rate': '',
                'Rajshahi Rate': ''
            })
        
        # Add children
        for child in hierarchy['children']:
            row = {
                'Type': 'Child',
                'Code': child['pwd_code'],
                'Description': self._fix_description_spacing(child['description']),
                'Parent Code': child['parent_code'],
                'Unit': child['unit'],
                'Dhaka Rate': child['rates'].get('Dhaka', ''),
                'Chattogram Rate': child['rates'].get('Chattogram', ''),
                'Khulna Rate': child['rates'].get('Khulna', ''),
                'Rajshahi Rate': child['rates'].get('Rajshahi', '')
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def render_tabular_editor(self):
        """Render tabular editor for PWD data"""
        
        st.markdown("### ✏️ Edit Data")
        
        if st.session_state.pwd_dry_run:
            st.info("🔍 DRY RUN MODE: Changes are not saved to database. Use 'Save to Database' in Export tab when ready.")
        
        df = st.session_state.pwd_edit_data.copy()
        
        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            show_type = st.multiselect(
                "Show",
                options=['Parent', 'Child'],
                default=['Parent', 'Child'],
                key="type_filter_editor"
            )
        
        with col_f2:
            search = st.text_input("🔍 Search", placeholder="Code or description...")
        
        with col_f3:
            # Show orphan count
            parent_codes = set(df[df['Type'] == 'Parent']['Code'].tolist())
            children_df = df[df['Type'] == 'Child']
            orphans = children_df[~children_df['Parent Code'].isin(parent_codes)]
            st.metric("Orphan Items", len(orphans), delta="⚠️" if len(orphans) > 0 else None)
        
        # Filter dataframe
        filtered_df = df[df['Type'].isin(show_type)] if show_type else df
        if search:
            filtered_df = filtered_df[
                filtered_df['Code'].str.contains(search, case=False, na=False) |
                filtered_df['Description'].str.contains(search, case=False, na=False) |
                filtered_df['Parent Code'].str.contains(search, case=False, na=False)
            ]
        
        # Get parent options for dropdown
        parent_options = sorted(df[df['Type'] == 'Parent']['Code'].unique().tolist())
        
        # Editable columns configuration
        column_config = {
            "Type": st.column_config.SelectboxColumn(
                "Type",
                options=["Parent", "Child"],
                required=True,
                width="small"
            ),
            "Code": st.column_config.TextColumn(
                "Code",
                required=True,
                width="small"
            ),
            "Description": st.column_config.TextColumn(
                "Description",
                width="large",
                required=True
            ),
            "Parent Code": st.column_config.SelectboxColumn(
                "Parent",
                options=[""] + parent_options,
                width="small",
                help="Select parent for child items"
            ),
            "Unit": st.column_config.SelectboxColumn(
                "Unit",
                options=["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "tender", "point"],
                width="small"
            ),
            "Dhaka Rate": st.column_config.NumberColumn(
                "Dhaka (৳)",
                format="%.2f",
                width="small"
            ),
            "Chattogram Rate": st.column_config.NumberColumn(
                "Chattogram (৳)",
                format="%.2f",
                width="small"
            ),
            "Khulna Rate": st.column_config.NumberColumn(
                "Khulna (৳)",
                format="%.2f",
                width="small"
            ),
            "Rajshahi Rate": st.column_config.NumberColumn(
                "Rajshahi (৳)",
                format="%.2f",
                width="small"
            )
        }
        
        # Display editable dataframe
        st.markdown("#### Editable Data Table")
        st.caption("💡 Tip: Click any cell to edit. Use the 'Fix Description Spacing' button to clean up text.")
        
        edited_df = st.data_editor(
            filtered_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="pwd_editor"
        )
        
        # Action buttons for editing
        st.markdown("---")
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        
        with col_btn1:
            if st.button("💾 Save Changes to Session", type="primary", use_container_width=True):
                st.session_state.pwd_edit_data = edited_df
                st.success("✅ Changes saved to session")
                st.rerun()
        
        with col_btn2:
            if st.button("🔧 Fix Description Spacing", use_container_width=True):
                edited_df['Description'] = edited_df['Description'].apply(self._fix_description_spacing)
                st.session_state.pwd_edit_data = edited_df
                st.success("✅ Fixed description spacing")
                st.rerun()
        
        with col_btn3:
            if st.button("🔄 Reset to Original", use_container_width=True):
                if 'pwd_original_hierarchy' in st.session_state:
                    original_df = self._convert_to_editable_dataframe(st.session_state.pwd_original_hierarchy)
                    st.session_state.pwd_edit_data = original_df
                    st.success("✅ Reset to original parsed data")
                    st.rerun()
        
        with col_btn4:
            if len(orphans) > 0:
                if st.button(f"🔧 Fix {len(orphans)} Orphans", use_container_width=True):
                    first_parent = parent_options[0] if parent_options else ""
                    for idx in edited_df.index:
                        if edited_df.loc[idx, 'Type'] == 'Child':
                            if edited_df.loc[idx, 'Parent Code'] not in parent_options:
                                edited_df.loc[idx, 'Parent Code'] = first_parent
                    st.session_state.pwd_edit_data = edited_df
                    st.success(f"✅ Assigned orphans to {first_parent}")
                    st.rerun()
    
    def render_export_section(self):
        """Render export and save section"""
        
        st.markdown("### 🗄️ Export & Save to Database")
        
        if st.session_state.pwd_edit_data is None:
            st.info("No data to export. Please import a PDF first.")
            return
        
        df = st.session_state.pwd_edit_data
        edition_year = st.session_state.pwd_edit_edition
        dry_run = st.session_state.pwd_dry_run
        
        # Show data summary
        st.markdown("#### Current Data Summary")
        
        parent_count = len(df[df['Type'] == 'Parent'])
        child_count = len(df[df['Type'] == 'Child'])
        
        # Check for orphans
        parent_codes = set(df[df['Type'] == 'Parent']['Code'].tolist())
        children_df = df[df['Type'] == 'Child']
        orphans = children_df[~children_df['Parent Code'].isin(parent_codes)]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Parents", parent_count)
        col2.metric("Children", child_count)
        col3.metric("Orphans", len(orphans), delta="⚠️" if len(orphans) > 0 else None)
        col4.metric("Edition Year", edition_year)
        
        if len(orphans) > 0:
            st.warning(f"⚠️ {len(orphans)} orphan items found. Please fix them in the Edit tab before saving.")
        
        # Export options
        st.markdown("---")
        st.markdown("#### Export Options")
        
        col_e1, col_e2 = st.columns(2)
        
        with col_e1:
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Export as CSV",
                csv,
                f"pwd_data_{edition_year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col_e2:
            json_data = df.to_json(orient='records', indent=2)
            st.download_button(
                "📥 Export as JSON",
                json_data,
                f"pwd_data_{edition_year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json",
                use_container_width=True
            )
        
        # Save to database
        st.markdown("---")
        st.markdown("#### Save to Database")
        
        if dry_run:
            st.warning("🔍 DRY RUN MODE is enabled. Uncheck 'Dry Run Mode' in the Import tab to enable database saving.")
        
        if st.button("💾 Save to Database", type="primary", use_container_width=True, disabled=dry_run or len(orphans) > 0):
            self._save_to_database(df, edition_year)
    
    def _fix_description_spacing(self, text):
        """Fix missing spaces in descriptions"""
        if not isinstance(text, str):
            return text
        
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        text = re.sub(r',([A-Za-z])', r', \1', text)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s+\.', '.', text)
        
        return text.strip()
    
    def _save_to_database(self, df, edition_year):
        """Save edited dataframe to database"""
        
        try:
            parents_df = df[df['Type'] == 'Parent']
            children_df = df[df['Type'] == 'Child']
            
            # Ensure tables exist
            self.db.init_pwd_hierarchical_tables()
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Clear existing data for this edition
            cursor.execute("DELETE FROM pwd_rates WHERE edition_year = ?", (edition_year,))
            cursor.execute("DELETE FROM pwd_children WHERE edition_year = ?", (edition_year,))
            cursor.execute("DELETE FROM pwd_parents")
            
            # Insert parents
            parents_saved = 0
            for _, row in parents_df.iterrows():
                chapter = row['Code'].split('.')[0]
                cursor.execute("""
                    INSERT OR REPLACE INTO pwd_parents (pwd_code, description, chapter_number)
                    VALUES (?, ?, ?)
                """, (row['Code'], row['Description'][:2000], chapter))
                parents_saved += 1
            
            # Insert children and rates
            children_saved = 0
            rates_saved = 0
            
            for _, row in children_df.iterrows():
                parent_code = row['Parent Code'] if row['Parent Code'] else ''
                
                cursor.execute("""
                    INSERT OR REPLACE INTO pwd_children (pwd_code, parent_code, description, unit, edition_year)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    row['Code'],
                    parent_code,
                    row['Description'][:2000],
                    row['Unit'] if row['Unit'] else '',
                    edition_year
                ))
                children_saved += 1
                
                # Insert rates
                for zone in ['Dhaka', 'Chattogram', 'Khulna', 'Rajshahi']:
                    rate_col = f'{zone} Rate'
                    if rate_col in row and pd.notna(row[rate_col]) and row[rate_col]:
                        try:
                            rate = float(row[rate_col])
                            if rate > 0:
                                cursor.execute("""
                                    INSERT OR REPLACE INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year)
                                    VALUES (?, ?, ?, ?)
                                """, (row['Code'], zone, rate, edition_year))
                                rates_saved += 1
                        except:
                            pass
            
            conn.commit()
            conn.close()
            
            st.success(f"✅ Saved {parents_saved} parents, {children_saved} children, and {rates_saved} rates to database!")
            st.balloons()
            
        except Exception as e:
            st.error(f"Error saving to database: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


# Function to call in your admin dashboard
def render_pwd_management_dashboard(db, parser):
    """Render the PWD management dashboard"""
    dashboard = PWDManagementDashboard(db, parser)
    dashboard.render()

    

# Helper class for PDF parsing
class PWDParserWithHierarchy:
    """Parser that maintains parent-child relationships in PWD schedule"""
    
    def parse_pdf_with_hierarchy(self, file_path, max_pages=None):
        """Parse PDF while maintaining parent-child hierarchy"""
        import pdfplumber
        
        items = []
        
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = min(total_pages, max_pages) if max_pages else total_pages
            
            for page_num in range(pages_to_process):
                page = pdf.pages[page_num]
                text = page.extract_text()
                if not text:
                    continue
                
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5,
                })
                
                if tables:
                    for table in tables:
                        page_items = self._parse_table(table)
                        items.extend(page_items)
                else:
                    page_items = self._parse_text(text)
                    items.extend(page_items)
        
        return self._organize_hierarchy(items)
    
    def _parse_table(self, table):
        """Parse table rows - simplified version"""
        items = []
        
        for row in table:
            if not row or len(row) < 3:
                continue
            
            row_cells = [str(cell).strip() if cell else '' for cell in row]
            
            # Find item code
            pwd_code = None
            code_col = None
            for col, cell in enumerate(row_cells[:4]):
                if re.match(r'^\d{1,2}\.\d{1,2}(?:\.\d{1,2})?$', cell):
                    pwd_code = cell
                    code_col = col
                    break
            
            if not pwd_code:
                continue
            
            code_parts = pwd_code.split('.')
            level = len(code_parts)
            
            # Extract description
            desc = ""
            if code_col is not None and code_col + 1 < len(row_cells):
                desc = row_cells[code_col + 1].strip()
                desc = re.sub(r'^\d+(?:\.\d+)?\s*$', '', desc)
            
            if not desc:
                continue
            
            # Extract rates
            rates = self._extract_rates(row_cells, code_col)
            
            # Extract unit
            unit = self._extract_unit(row_cells, code_col)
            
            items.append({
                'pwd_code': pwd_code,
                'level': level,
                'description': desc,
                'has_rates': len(rates) > 0,
                'rates': rates,
                'unit': unit
            })
        
        return items
    
    def _parse_text(self, text):
        """Parse raw text - simplified version"""
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            code_match = re.match(r'^(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\s+', line)
            if not code_match:
                continue
            
            pwd_code = code_match.group(1)
            code_parts = pwd_code.split('.')
            level = len(code_parts)
            
            remaining = line[len(code_match.group(0)):].strip()
            
            rate_pattern = r'Tk\.?\s*([\d,]+(?:\.\d{2})?)'
            rate_matches = list(re.finditer(rate_pattern, remaining, re.I))
            
            if rate_matches:
                desc = remaining[:rate_matches[0].start()].strip()
                desc = re.sub(r'\s+', ' ', desc).strip()
                
                zone_names = ["Dhaka", "Chattogram", "Khulna", "Rajshahi"]
                rates = {}
                for idx, match in enumerate(rate_matches[:4]):
                    if idx < len(zone_names):
                        try:
                            clean_rate = float(match.group(1).replace(',', ''))
                            rates[zone_names[idx]] = clean_rate
                        except:
                            pass
                
                unit = "N/A"
                unit_match = re.search(r'\b(cum|sqm|meter|each|job|set|kg|hour|month|tender|point)\b', desc.lower())
                if unit_match:
                    unit = unit_match.group(1)
                    desc = re.sub(r'\b' + unit + r'\b', '', desc, flags=re.I).strip()
            else:
                desc = remaining
                rates = {}
                unit = "N/A"
            
            if desc:
                items.append({
                    'pwd_code': pwd_code,
                    'level': level,
                    'description': desc,
                    'has_rates': len(rates) > 0,
                    'rates': rates,
                    'unit': unit
                })
        
        return items
    
    def _extract_rates(self, row_cells, code_col):
        """Extract rates from row"""
        rates = {}
        zone_names = ["Dhaka", "Chattogram", "Khulna", "Rajshahi"]
        rate_start = 5 if code_col is None or code_col < 5 else code_col + 3
        
        for idx, zone in enumerate(zone_names):
            rate_col = rate_start + idx
            if rate_col < len(row_cells):
                rate_val = self._extract_numeric(row_cells[rate_col])
                if rate_val and rate_val > 0:
                    rates[zone] = rate_val
        
        return rates
    
    def _extract_unit(self, row_cells, code_col):
        """Extract unit from row"""
        if code_col is None or code_col + 2 >= len(row_cells):
            return "N/A"
        
        unit_cell = row_cells[code_col + 2].lower()
        unit_patterns = ['cum', 'sqm', 'meter', 'each', 'job', 'set', 'kg', 'hour', 'month', 'tender', 'point']
        
        for pattern in unit_patterns:
            if pattern in unit_cell:
                return pattern
        
        return "N/A"
    
    def _extract_numeric(self, value):
        """Extract numeric value"""
        if not value or value == '—':
            return None
        
        cleaned = re.sub(r'[^\d.-]', '', str(value).replace(',', ''))
        try:
            return float(cleaned) if cleaned and cleaned != '-' else None
        except:
            return None
    
    def _organize_hierarchy(self, items):
        """Organize into parent-child structure"""
        
        hierarchy = {
            'parents': [],
            'children': [],
            'parent_child_map': {}
        }
        
        # First pass: collect parents
        for item in items:
            code_parts = item['pwd_code'].split('.')
            if len(code_parts) == 2:
                hierarchy['parents'].append({
                    'code': item['pwd_code'],
                    'description': item['description'],
                    'chapter': code_parts[0]
                })
                hierarchy['parent_child_map'][item['pwd_code']] = []
        
        # Second pass: collect children
        for item in items:
            code_parts = item['pwd_code'].split('.')
            if len(code_parts) >= 3:
                parent_code = '.'.join(code_parts[:2])
                
                child_item = {
                    'pwd_code': item['pwd_code'],
                    'parent_code': parent_code,
                    'description': item['description'],
                    'unit': item['unit'],
                    'rates': item['rates']
                }
                
                hierarchy['children'].append(child_item)
                
                if parent_code in hierarchy['parent_child_map']:
                    hierarchy['parent_child_map'][parent_code].append(child_item)
        
        return hierarchy