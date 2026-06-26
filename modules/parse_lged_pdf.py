# modules/lged_parser.py

import re
import pdfplumber
import streamlit as st
import pandas as pd
from datetime import datetime
from utils.debug_logger import get_debug_logger, log_table_extraction, log_item_extraction, log_hierarchy
import os

class LGERateParser:
    def __init__(self, debug=True):
        self.debug = debug
        self.debug_logger = get_debug_logger(enabled=debug)
        self.zone_mapping = {
            'Zone-A': 'Dhaka & Mymensingh Division',
            'Zone-B': 'Chattogram & Sylhet Division',
            'Zone-C': 'Rajshahi & Rangpur Division',
            'Zone-D': 'Khulna & Barishal Division'
        }
    
    def parse_pdf(self, file_path, max_pages=None):
        """Parse LGED PDF with debugging"""
        import pdfplumber
        
        items = []
        
        self.debug_logger.log('PARSE_START', f"Starting LGED parse: {file_path}", {'max_pages': max_pages})
        
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = min(total_pages, max_pages) if max_pages else total_pages
            
            self.debug_logger.log('PAGES_INFO', f"Total pages: {total_pages}, Processing: {pages_to_process}")
            
            for page_num in range(pages_to_process):
                page = pdf.pages[page_num]
                text = page.extract_text()
                
                self.debug_logger.log('PAGE_PROCESS', f"Processing page {page_num + 1}", {
                    'has_text': bool(text),
                    'text_length': len(text) if text else 0
                })
                
                if not text:
                    continue
                
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5,
                })
                
                if tables:
                    self.debug_logger.log('TABLES_FOUND', f"Found {len(tables)} tables on page {page_num + 1}")
                    
                    for table_idx, table in enumerate(tables):
                        log_table_extraction(table, page_num + 1, table_idx + 1)
                        page_items = self._parse_table(table)
                        
                        self.debug_logger.log('ITEMS_FROM_TABLE', f"Extracted {len(page_items)} items from table {table_idx + 1}")
                        
                        items.extend(page_items)
                else:
                    self.debug_logger.log('NO_TABLES', f"No tables found on page {page_num + 1}, using text parsing")
                    page_items = self._parse_text(text)
                    items.extend(page_items)
        
        # Log total items before hierarchy
        self.debug_logger.log('TOTAL_ITEMS', f"Total items extracted: {len(items)}", {
            'sample_item': items[0] if items else None
        })
        
        hierarchy = self._organize_hierarchy(items)
        
        # Log hierarchy results
        log_hierarchy(hierarchy, 'LGED')
        
        return hierarchy

    def _parse_table(self, table):
        """Parse LGED table rows with proper multi-column description merging"""
        items = []
        
        # First, identify the column structure
        header_row = None
        code_col = None
        desc_start_col = None
        unit_col = None
        rate_start_col = None
        
        # Find header row
        for row_idx, row in enumerate(table[:10]):
            if not row:
                continue
            row_str = ' '.join([str(cell).lower() if cell else '' for cell in row])
            if 'item code' in row_str and 'description' in row_str:
                header_row = row_idx
                break
        
        # If no header found, use defaults
        if header_row is None:
            header_row = -1  # No header row, process all rows
            code_col = 0
            desc_start_col = 1
            unit_col = 3
            rate_start_col = 4
        else:
            # Parse header to find column positions
            header = table[header_row]
            for col, cell in enumerate(header):
                if not cell:
                    continue
                cell_lower = str(cell).lower()
                if 'item code' in cell_lower or 'code' in cell_lower:
                    code_col = col
                elif 'description' in cell_lower or 'brief' in cell_lower:
                    if desc_start_col is None:
                        desc_start_col = col
                elif 'unit' in cell_lower:
                    unit_col = col
                elif 'rate' in cell_lower:
                    rate_start_col = col
            
            # Set defaults if still None
            if code_col is None:
                code_col = 0
            if desc_start_col is None:
                desc_start_col = 1
            if unit_col is None:
                unit_col = 3
            if rate_start_col is None:
                rate_start_col = 4
        
        # Process data rows
        for row_idx, row in enumerate(table):
            # Skip header row and any rows before it
            if row_idx <= header_row:
                continue
            
            if not row or len(row) < 5:
                continue
            
            row_cells = [str(cell).strip() if cell else '' for cell in row]
            
            # Find item code
            pwd_code = None
            found_code_col = None
            for col in range(code_col, min(code_col + 3, len(row_cells))):
                cell = row_cells[col]
                if re.match(r'^\d{1,2}\.\d{1,2}(?:\.\d{1,2}(?:\.\d{1,2})?)?$', cell):
                    pwd_code = cell
                    found_code_col = col
                    break
            
            if not pwd_code:
                continue
            
            code_parts = pwd_code.split('.')
            level = len(code_parts)
            
            # Extract FULL description by merging multiple columns
            desc_parts = []
            desc_col = found_code_col + 1 if found_code_col is not None else desc_start_col
            
            while desc_col < len(row_cells):
                cell = row_cells[desc_col]
                if not cell or cell in ['', '-', '—']:
                    desc_col += 1
                    continue
                
                # Stop if we hit a column that looks like a unit or rate
                cell_lower = cell.lower()
                if re.match(r'^(cum|sqm|meter|each|job|set|kg|hour|month|day|km|ls|point)$', cell_lower):
                    unit_col = desc_col
                    break
                
                # Stop if we hit a numeric value (likely a rate)
                if re.match(r'^[\d,]+\.?\d*$', cell) or re.search(r'Tk', cell):
                    if rate_start_col is None:
                        rate_start_col = desc_col
                    break
                
                desc_parts.append(cell)
                desc_col += 1
                
                # Safety limit - don't go too far
                if desc_col > found_code_col + 8:
                    break
            
            desc = ' '.join(desc_parts).strip()
            
            # Clean description
            desc = re.sub(r'^\d+(?:\.\d+)?\s*$', '', desc)
            desc = re.sub(r'\s*\[PWD[^\]]+\]', '', desc).strip()
            
            # Log short descriptions for debugging
            if len(desc) < 20 and level == 2 and row_idx > header_row + 2:
                self.debug_logger.log('SHORT_DESCRIPTION_WARNING', 
                    f"Parent {pwd_code} has short description ({len(desc)} chars): '{desc[:50]}'",
                    {'row_idx': row_idx, 'desc_cols': desc_parts, 'raw_cells': row_cells[found_code_col:found_code_col+6] if found_code_col else []}
                )
            
            if not desc or len(desc) < 10:
                continue
            
            # Extract unit
            unit = ""
            unit_patterns = ['cum', 'sqm', 'meter', 'each', 'job', 'set', 'kg', 'hour', 
                            'month', 'day', 'km', 'ls', 'point']
            
            if unit_col is not None and unit_col < len(row_cells):
                unit_cell = row_cells[unit_col].lower()
                for pattern in unit_patterns:
                    if pattern in unit_cell:
                        unit = pattern
                        break
            
            # If unit not found, search in adjacent cells
            if not unit:
                search_start = found_code_col + 1 if found_code_col else desc_start_col
                for col in range(search_start, min(search_start + 5, len(row_cells))):
                    cell = row_cells[col].lower()
                    for pattern in unit_patterns:
                        if pattern in cell:
                            unit = pattern
                            break
                    if unit:
                        break
            
            # Extract rates
            rates = {}
            zone_names = list(self.zone_mapping.keys())
            
            # Find rate columns
            rate_col = rate_start_col if rate_start_col is not None else (found_code_col + 4 if found_code_col else 4)
            if unit:
                # Try to find rate column after unit
                for col in range(unit_col + 1, min(unit_col + 5, len(row_cells))):
                    if self._extract_numeric(row_cells[col]) is not None:
                        rate_col = col
                        break
            
            for idx, zone in enumerate(zone_names):
                current_rate_col = rate_col + idx
                if current_rate_col < len(row_cells):
                    rate_val = self._extract_numeric(row_cells[current_rate_col])
                    if rate_val and rate_val > 0:
                        rates[zone] = rate_val
            
            item = {
                'code': pwd_code,
                'level': level,
                'description': desc,
                'unit': unit,
                'rates': rates
            }
            
            # Log the extracted item
            self.debug_logger.log_item_extraction(item, 'LGED')
            
            items.append(item)
        
        return items

    def _parse_table_bak(self, table):
        """Parse LGED table rows with detailed debugging"""
        items = []
        
        self.debug_logger.log('TABLE_PARSE_START', f"Parsing table with {len(table)} rows")
        
        for row_idx, row in enumerate(table):
            if not row or len(row) < 5:
                continue
            
            row_cells = [str(cell).strip() if cell else '' for cell in row]
            
            # Log raw row for first few rows
            if row_idx < 3:
                self.debug_logger.log('RAW_ROW', f"Row {row_idx}", {
                    'cells': row_cells[:8]  # First 8 cells
                })
            
            # Find item code
            pwd_code = None
            code_col = None
            for col, cell in enumerate(row_cells[:3]):
                if re.match(r'^\d{1,2}\.\d{1,2}(?:\.\d{1,2}(?:\.\d{1,2})?)?$', cell):
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
                desc = re.sub(r'\s*\[PWD[^\]]+\]', '', desc).strip()
                
                # Log description length issue
                if len(desc) < 20 and level == 2:  # Parent with short description
                    self.debug_logger.log('SHORT_DESCRIPTION_WARNING', 
                        f"Parent {pwd_code} has short description ({len(desc)} chars): '{desc[:50]}'",
                        {'row_idx': row_idx, 'code_col': code_col, 'raw_cell': row_cells[code_col + 1][:100] if code_col + 1 < len(row_cells) else 'N/A'}
                    )
            
            if not desc or len(desc) < 10:
                continue
            
            # Extract unit
            unit = ""
            if code_col is not None and code_col + 2 < len(row_cells):
                unit_cell = row_cells[code_col + 2].lower()
                unit_patterns = ['cum', 'sqm', 'meter', 'each', 'job', 'set', 'kg', 'hour', 
                                'month', 'day', 'km', 'ls', 'point']
                for pattern in unit_patterns:
                    if pattern in unit_cell:
                        unit = pattern
                        break
            
            # Extract rates
            rates = {}
            zone_names = list(self.zone_mapping.keys())
            rate_start = 3 if code_col is None or code_col < 3 else code_col + 3
            
            for idx, zone in enumerate(zone_names):
                rate_col = rate_start + idx
                if rate_col < len(row_cells):
                    rate_val = self._extract_numeric(row_cells[rate_col])
                    if rate_val and rate_val > 0:
                        rates[zone] = rate_val
            
            item = {
                'code': pwd_code,
                'level': level,
                'description': desc,
                'unit': unit,
                'rates': rates
            }
            
            # Log the extracted item
            log_item_extraction(item, 'LGED')
            
            items.append(item)
        
        self.debug_logger.log('TABLE_PARSE_END', f"Extracted {len(items)} items from table")
        
        return items

    
    def _parse_text(self, text):
        """Fallback text parser for LGED"""
        items = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            code_match = re.match(r'^(\d{1,2}\.\d{1,2}(?:\.\d{1,2}(?:\.\d{1,2})?)?)\s+', line)
            if not code_match:
                continue
            
            pwd_code = code_match.group(1)
            code_parts = pwd_code.split('.')
            level = len(code_parts)
            
            remaining = line[len(code_match.group(0)):].strip()
            
            # Remove PWD reference text if present
            remaining = re.sub(r'\s*\[PWD[^\]]+\]', '', remaining).strip()
            
            # Find rates in the line (no "Tk." prefix in LGED)
            rate_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
            rate_matches = list(re.finditer(rate_pattern, remaining))
            
            if rate_matches:
                desc = remaining[:rate_matches[0].start()].strip()
                desc = re.sub(r'\s+', ' ', desc).strip()
                
                # Extract unit
                unit = "N/A"
                unit_match = re.search(r'\b(cum|sqm|meter|each|job|set|kg|hour|month|day|km|ls)\b', desc.lower())
                if unit_match:
                    unit = unit_match.group(1)
                    desc = re.sub(r'\b' + unit + r'\b', '', desc, flags=re.I).strip()
                
                # Extract rates
                zone_names = list(self.zone_mapping.keys())
                rates = {}
                for idx, match in enumerate(rate_matches[:4]):
                    if idx < len(zone_names):
                        try:
                            clean_rate = float(match.group(1).replace(',', ''))
                            if clean_rate > 0:
                                rates[zone_names[idx]] = clean_rate
                        except:
                            pass
            else:
                desc = remaining
                rates = {}
                unit = "N/A"
            
            if desc and desc != pwd_code:
                items.append({
                    'code': pwd_code,
                    'level': level,
                    'description': desc,  # ← Keep FULL description, no truncation
                    'unit': unit,
                    'rates': rates
                })
        
        return items

    def _extract_numeric(self, value):
        """Extract numeric rate from string - handles various formats"""
        if not value or value == '—' or value == '-':
            return None
        
        # Remove commas and currency symbols
        cleaned = re.sub(r'[^\d.-]', '', str(value).replace(',', ''))
        
        # Handle numbers like "1.5" (not rates)
        if cleaned and cleaned != '-':
            try:
                num = float(cleaned)
                # Skip small numbers that are likely page numbers or references (not rates)
                if num < 10 and '.' in str(num):
                    return None
                return num
            except:
                pass
        
        # Try with regex for complex patterns
        match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', str(value))
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except:
                pass
        
        return None

    
    def _organize_hierarchy(self, items):
        """Organize into parent-child structure"""
        
        hierarchy = {
            'parents': [],
            'children': [],
            'parent_child_map': {}
        }
        
        # First pass: collect parents (2-part codes like 1.01, 2.02)
        for item in items:
            code_parts = item['code'].split('.')
            if len(code_parts) == 2:
                hierarchy['parents'].append({
                    'code': item['code'],
                    'description': item['description'],
                    'chapter': code_parts[0]
                })
                hierarchy['parent_child_map'][item['code']] = []
        
        # Second pass: collect children (3+ part codes)
        for item in items:
            code_parts = item['code'].split('.')
            if len(code_parts) >= 3:
                parent_code = '.'.join(code_parts[:2])
                
                child_item = {
                    'code': item['code'],
                    'parent_code': parent_code,
                    'description': item['description'],
                    'unit': item['unit'],
                    'rates': item['rates'],
                    'pwd_reference': item.get('pwd_reference')
                }
                
                hierarchy['children'].append(child_item)
                
                if parent_code in hierarchy['parent_child_map']:
                    hierarchy['parent_child_map'][parent_code].append(child_item)
        
        return hierarchy



# LGED Import Wizard
class LGEDImportWizard:
    """Step-by-step wizard for LGED rate schedule import"""
    
    def __init__(self, db_instance):
        self.db = db_instance
        self.parser = LGERateParser()
        self.db_manager = LGERateDBManager(db_instance)
    
    def render(self):
        """Render LGED import wizard"""
        
        st.markdown("""
        <div class="main-header">
            <h1>🏗️ LGED Rate Schedule Import Wizard</h1>
            <p>Import LGED Schedule of Rates (August 2025)</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Step indicators
        if 'lged_wizard_step' not in st.session_state:
            st.session_state.lged_wizard_step = 1
        if 'lged_import_data' not in st.session_state:
            st.session_state.lged_import_data = None
        
        self._show_step_indicator()
        
        if st.session_state.lged_wizard_step == 1:
            self._step1_upload_and_config()
        elif st.session_state.lged_wizard_step == 2:
            self._step2_parse_and_preview()
        elif st.session_state.lged_wizard_step == 3:
            self._step3_review_and_save()
    
    def _show_step_indicator(self):
        steps = [
            ("1️⃣ Upload & Config", 1),
            ("2️⃣ Parse & Preview", 2),
            ("3️⃣ Review & Save", 3)
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
        """Step 1: Upload LGED PDF and configure"""
        
        uploaded_file = st.file_uploader(
            "📄 **Upload LGED Rate Schedule PDF**",
            type=["pdf"],
            help="Upload the official LGED Rate Schedule PDF (August 2025)",
            key="lged_upload"
        )
        
        if uploaded_file:
            # Get total pages
            temp_path = "temp_lged.pdf"
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
            edition_year = st.number_input("Edition Year", min_value=2020, max_value=2030, value=2025)
            version_name = st.text_input("Version Name", value=f"LGED Schedule {edition_year}")
        
        with col2:
            effective_date = st.date_input("Effective From", value=datetime.now().date())
            max_pages = st.number_input("Pages to Parse", min_value=1, max_value=500, value=50,
                                        help="First N pages. Set to 500 for full document.")
        
        st.markdown("---")
        
        # Debug Options - Moved BEFORE the button
        st.markdown("### 🐛 Debug Options")
        
        show_debug = st.checkbox(
            "Show Debug Information",
            value=False,
            help="Display detailed extraction logs for troubleshooting"
        )
        
        if show_debug:
            from utils.debug_logger import get_debug_logger
            debug_logger = get_debug_logger(enabled=True, log_to_file=True)
            st.session_state.show_debug = True
            st.info("🔍 Debug mode enabled. Logs will be shown after parsing.")
        else:
            st.session_state.show_debug = False
        
        st.markdown("---")
        
        # Zone Information
        st.info("**Zone Information:**\n"
                "- Zone-A: Dhaka & Mymensingh Division\n"
                "- Zone-B: Chattogram & Sylhet Division\n"
                "- Zone-C: Rajshahi & Rangpur Division\n"
                "- Zone-D: Khulna & Barishal Division\n"
                "- Accessibility Bonus: 5% for remote/offshore areas")
        
        # Action button - This should be the last thing before returning
        if uploaded_file:
            if st.button("🚀 **Parse & Continue**", type="primary", use_container_width=True):
                st.session_state.lged_import_settings = {
                    'file': uploaded_file,
                    'edition_year': edition_year,
                    'version_name': version_name,
                    'effective_date': effective_date,
                    'max_pages': max_pages
                }
                st.session_state.lged_wizard_step = 2
                st.rerun()
        else:
            st.button("🚀 **Parse & Continue**", disabled=True, use_container_width=True)

    def _step2_parse_and_preview(self):
        """Step 2: Parse PDF and preview results"""
        
        st.markdown("### Step 2: Parsing PDF")
        
        settings = st.session_state.lged_import_settings
        
        with st.spinner("Parsing LGED rate schedule..."):
            temp_path = "temp_lged_parse.pdf"
            with open(temp_path, "wb") as f:
                f.write(settings['file'].getbuffer())
            
            hierarchy = self.parser.parse_pdf(temp_path, max_pages=settings['max_pages'])
            os.remove(temp_path)
        
        if hierarchy.get('parents'):
            st.session_state.lged_import_data = {
                'hierarchy': hierarchy,
                'settings': settings
            }
            
            st.success(f"✅ Parsed {len(hierarchy['parents'])} parents and {len(hierarchy['children'])} children")
            
            # Display preview
            st.markdown("#### Preview")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Parents", len(hierarchy['parents']))
                st.metric("Children", len(hierarchy['children']))
            
            # Sample items
            with st.expander("Sample Items", expanded=True):
                sample_data = []
                for child in hierarchy['children'][:10]:
                    sample_data.append({
                        'Code': child['code'],
                        'Description': child['description'][:60] + "...",
                        'Unit': child['unit'],
                        'Zone-A': child['rates'].get('Zone-A', 'N/A')
                    })
                st.dataframe(pd.DataFrame(sample_data), use_container_width=True, hide_index=True)
            
            # PWD cross-references
            pwd_refs = [c for c in hierarchy['children'] if c.get('pwd_reference')]
            if pwd_refs:
                st.info(f"📎 Found {len(pwd_refs)} items with PWD cross-references")
            
            if st.button("➡️ **Continue to Review & Save**", type="primary"):
                st.session_state.lged_wizard_step = 3
                st.rerun()
        else:
            st.error("No items found. Try increasing pages.")
            if st.button("◀️ Back to Settings"):
                st.session_state.lged_wizard_step = 1
                st.rerun()
    
    def _step3_review_and_save(self):
        """Step 3: Review and save to database"""
        
        st.markdown("### Step 3: Review & Save")
        
        data = st.session_state.lged_import_data
        hierarchy = data['hierarchy']
        settings = data['settings']
        
        # Editable preview table
        st.markdown("#### Editable Preview")
        
        # Convert to display format
        display_data = []
        for child in hierarchy['children'][:20]:
            row = {
                'Code': child['code'],
                'Description': child['description'][:80],
                'Unit': child['unit'],
                'Parent': child['parent_code'],
                'Zone-A': child['rates'].get('Zone-A', ''),
                'Zone-B': child['rates'].get('Zone-B', ''),
                'Zone-C': child['rates'].get('Zone-C', ''),
                'Zone-D': child['rates'].get('Zone-D', ''),
            }
            if child.get('pwd_reference'):
                row['PWD Ref'] = child['pwd_reference']
            display_data.append(row)
        
        st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Export as CSV"):
                export_data = []
                for child in hierarchy['children']:
                    row = {
                        'code': child['code'],
                        'parent_code': child['parent_code'],
                        'description': child['description'],
                        'unit': child['unit'],
                        'pwd_reference': child.get('pwd_reference', '')
                    }
                    for zone, rate in child['rates'].items():
                        row[zone] = rate
                    export_data.append(row)
                
                df = pd.DataFrame(export_data)
                csv = df.to_csv(index=False)
                st.download_button("Download CSV", csv, f"lged_export_{settings['edition_year']}.csv")
        
        with col2:
            if st.button("💾 **Save to Database**", type="primary"):
                version_id = self.db_manager.save_hierarchy(
                    hierarchy,
                    settings['version_name'],
                    settings['edition_year'],
                    settings['effective_date']
                )
                st.success(f"✅ Saved to database! Version ID: {version_id}")
                st.balloons()
                
                if st.button("🔄 Start New Import"):
                    st.session_state.lged_wizard_step = 1
                    st.session_state.lged_import_data = None
                    st.rerun()


# Function to integrate into admin dashboard
def render_lged_management(db):
    """Render LGED management interface in admin dashboard"""
    
    st.markdown("## 🏗️ LGED Rate Schedule Management")
    st.caption("LGED Schedule of Rates (August 2025) - Separate from PWD rates")
    
    tab1, tab2, tab3 = st.tabs([
        "📥 Import LGED Schedule",
        "📊 View LGED Rates",
        "🔗 PWD Cross-Reference"
    ])
    
    with tab1:
        wizard = LGEDImportWizard(db)
        wizard.render()
    
    with tab2:
        render_lged_viewer(db)
    
    with tab3:
        render_lged_pwd_crossref(db)


def render_lged_viewer(db):
    """View imported LGED rates"""
    
    st.markdown("### LGED Rate Viewer")
    
    conn = db.get_connection()
    
    # Get active version
    versions = pd.read_sql_query("""
        SELECT id, version_name, edition_year, is_active 
        FROM rate_versions 
        ORDER BY edition_year DESC
    """, conn)
    
    if versions.empty:
        st.info("No LGED data found. Please import first.")
        conn.close()
        return
    
    # Version selector
    selected_version = st.selectbox(
        "Select Version",
        options=versions['id'].tolist(),
        format_func=lambda x: f"{versions[versions['id']==x]['version_name'].iloc[0]} ({versions[versions['id']==x]['edition_year'].iloc[0]})"
    )
    
    # Search
    search = st.text_input("Search", placeholder="Item code or description...")
    
    # Query items
    query = """
        SELECT c.code, c.description, c.unit, c.parent_code, c.pwd_reference,
               r.zone_name, r.unit_rate
        FROM lged_children c
        JOIN lged_zone_rates r ON c.id = r.child_id
        WHERE c.version_id = ?
    """
    params = [selected_version]
    
    if search:
        query += " AND (c.code LIKE ? OR c.description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if not df.empty:
        # Pivot to show zones as columns
        pivot_df = df.pivot_table(
            index=['code', 'description', 'unit', 'parent_code', 'pwd_reference'],
            columns='zone_name',
            values='unit_rate'
        ).reset_index()
        
        st.dataframe(pivot_df, use_container_width=True, hide_index=True)
        
        # Export
        csv = pivot_df.to_csv(index=False)
        st.download_button("📥 Export Data", csv, "lged_rates.csv")
    else:
        st.info("No items found")


def render_lged_pwd_crossref(db):
    """Show cross-references between LGED and PWD rates"""
    
    st.markdown("### LGED ↔ PWD Cross-Reference")
    st.caption("Items where LGED references PWD codes")
    
    conn = db.get_connection()
    
    # Get LGED items with PWD references
    df = pd.read_sql_query("""
        SELECT c.code, c.description, c.unit, c.pwd_reference,
               GROUP_CONCAT(r.zone_name || ': ' || r.unit_rate) as rates
        FROM lged_children c
        JOIN lged_zone_rates r ON c.id = r.child_id
        WHERE c.pwd_reference IS NOT NULL AND c.pwd_reference != ''
        GROUP BY c.id
        LIMIT 100
    """, conn)
    
    conn.close()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.info(f"📊 Found {len(df)} items with PWD references")
    else:
        st.info("No cross-references found")