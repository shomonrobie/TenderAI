# modules/pwd_data_manager.py

import re
import pandas as pd
from collections import defaultdict
import pdfplumber
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()


class PWDParserWithHierarchy:
    """Parser that maintains parent-child relationships in PWD schedule"""
    
    def __init__(self):
        self.parent_items = []
        self.child_items = []
    
    def parse_pdf_with_hierarchy(self, file_path, max_pages=None):
        """Parse PDF while maintaining parent-child hierarchy"""
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
        """Parse table rows"""
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
            
            # Determine level
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
        """Parse raw text"""
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
            
            # Find rates
            rate_pattern = r'Tk\.?\s*([\d,]+(?:\.\d{2})?)'
            rate_matches = list(re.finditer(rate_pattern, remaining, re.I))
            
            if rate_matches:
                desc = remaining[:rate_matches[0].start()].strip()
                desc = re.sub(r'\s+', ' ', desc).strip()
                
                # Extract rates
                zone_names = ["Dhaka", "Chattogram", "Khulna", "Rajshahi"]
                rates = {}
                for idx, match in enumerate(rate_matches[:4]):
                    if idx < len(zone_names):
                        try:
                            clean_rate = float(match.group(1).replace(',', ''))
                            rates[zone_names[idx]] = clean_rate
                        except:
                            pass
                
                # Extract unit
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
            if len(code_parts) == 2:  # Parent
                hierarchy['parents'].append({
                    'code': item['pwd_code'],
                    'description': item['description'],
                    'chapter': code_parts[0]
                })
                hierarchy['parent_child_map'][item['pwd_code']] = []
        
        # Second pass: collect children
        for item in items:
            code_parts = item['pwd_code'].split('.')
            if len(code_parts) >= 3:  # Child
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


class PWDExtractorForVerification:
    """Extract and analyze PWD structure for manual verification"""
    
    def __init__(self):
        self.all_items = []
        self.parents = {}
        self.children = defaultdict(list)
        self.orphans = []
        self.items_without_children = set()
    
    def extract_from_pdf(self, file_path, max_pages=None):
        """Extract all items from PDF with hierarchy analysis"""
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
                        self._process_table(table)
                else:
                    self._process_text(text)
        
        # Analyze hierarchy
        self._analyze_hierarchy()
        
        return self._generate_report()
    
    def _process_table(self, table):
        """Process table rows"""
        for row in table:
            if not row or len(row) < 2:
                continue
            
            row_cells = [str(cell).strip() if cell else '' for cell in row]
            
            # Find item code
            pwd_code = None
            description = ""
            
            for col, cell in enumerate(row_cells[:4]):
                if re.match(r'^\d{1,2}\.\d{1,2}(?:\.\d{1,2})?$', cell):
                    pwd_code = cell
                    if col + 1 < len(row_cells):
                        description = row_cells[col + 1]
                        description = re.sub(r'^\d+(?:\.\d+)?\s*$', '', description)
                        description = re.sub(r'\s+', ' ', description).strip()
                    break
            
            if pwd_code and description:
                self.all_items.append({
                    'code': pwd_code,
                    'description': description[:500],
                    'has_rates': self._check_has_rates(row_cells)
                })
    
    def _process_text(self, text):
        """Process raw text lines"""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            code_match = re.match(r'^(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\s+', line)
            if not code_match:
                continue
            
            pwd_code = code_match.group(1)
            remaining = line[len(code_match.group(0)):].strip()
            
            has_rates = bool(re.search(r'Tk\.?\s*[\d,]+', remaining, re.I))
            
            if has_rates:
                rate_match = re.search(r'Tk\.?\s*[\d,]+', remaining, re.I)
                if rate_match:
                    description = remaining[:rate_match.start()].strip()
                else:
                    description = remaining
            else:
                description = remaining
            
            description = re.sub(r'\s+', ' ', description).strip()
            
            if description:
                self.all_items.append({
                    'code': pwd_code,
                    'description': description[:500],
                    'has_rates': has_rates
                })
    
    def _check_has_rates(self, row_cells):
        """Check if row contains rate values"""
        for cell in row_cells[5:9]:
            if cell and re.search(r'Tk\.?\s*[\d,]+', str(cell), re.I):
                return True
        return False
    
    def _analyze_hierarchy(self):
        """Analyze parent-child relationships"""
        
        # First pass: identify parents
        for item in self.all_items:
            code_parts = item['code'].split('.')
            if len(code_parts) == 2:
                self.parents[item['code']] = {
                    'code': item['code'],
                    'description': item['description'],
                    'has_rates': item['has_rates'],
                    'child_count': 0
                }
        
        # Second pass: assign children
        for item in self.all_items:
            code_parts = item['code'].split('.')
            if len(code_parts) >= 3:
                parent_code = '.'.join(code_parts[:2])
                if parent_code in self.parents:
                    self.children[parent_code].append(item)
                    self.parents[parent_code]['child_count'] += 1
                else:
                    self.orphans.append({
                        'code': item['code'],
                        'description': item['description'],
                        'parent_expected': parent_code
                    })
        
        # Find parents with no children
        for parent_code, parent_data in self.parents.items():
            if parent_data['child_count'] == 0:
                self.items_without_children.add(parent_code)
    
    def _generate_report(self):
        """Generate comprehensive verification report"""
        
        report = {
            'summary': {
                'total_items': len(self.all_items),
                'total_parents': len(self.parents),
                'total_children': sum(len(children) for children in self.children.values()),
                'orphans': len(self.orphans),
                'parents_without_children': len(self.items_without_children)
            },
            'parents': [],
            'children': [],
            'orphans_list': self.orphans,
            'parents_without_children_list': []
        }
        
        # Parents list
        for code, data in sorted(self.parents.items()):
            report['parents'].append({
                'Item Code': code,
                'Description': data['description'][:200],
                'Has Direct Rates?': 'Yes' if data['has_rates'] else 'No',
                'Child Count': data['child_count'],
                'Status': '⚠️ NO CHILDREN' if data['child_count'] == 0 else '✅ Has Children'
            })
        
        # Parents without children
        for code in sorted(self.items_without_children):
            parent_data = self.parents[code]
            report['parents_without_children_list'].append({
                'Item Code': code,
                'Description': parent_data['description'][:200],
                'Has Direct Rates?': 'Yes' if parent_data['has_rates'] else 'No',
                'Action Required': 'Verify if this should have child items'
            })
        
        return report

def save_hierarchy_to_database(hierarchy, edition_year):
    """Save hierarchical data to database"""
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
                
        # Tables already exist in unified database manager
        
        # Clear existing data for this edition year
        cursor.execute("DELETE FROM pwd_rates WHERE edition_year = ?", (edition_year,))
        cursor.execute("DELETE FROM pwd_children WHERE edition_year = ?", (edition_year,))
        cursor.execute("DELETE FROM pwd_parents")
        
        # Insert parents
        for parent in hierarchy['parents']:
            cursor.execute("""
                INSERT OR REPLACE INTO pwd_parents (pwd_code, description, chapter_number)
                VALUES (?, ?, ?)
            """, (parent['code'], parent['description'][:2000], parent['chapter']))
        
        # Insert children and rates
        for child in hierarchy['children']:
            cursor.execute("""
                INSERT OR REPLACE INTO pwd_children (pwd_code, parent_code, description, unit, edition_year)
                VALUES (?, ?, ?, ?, ?)
            """, (child['pwd_code'], child['parent_code'], child['description'][:2000], child['unit'], edition_year))
            
            for zone, rate in child['rates'].items():
                cursor.execute("""
                    INSERT OR REPLACE INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year)
                    VALUES (?, ?, ?, ?)
                """, (child['pwd_code'], zone, rate, edition_year))
        
        conn.commit()
        conn.close()
        
        return True, len(hierarchy['parents']), len(hierarchy['children'])
        
    except Exception as e:
        return False, 0, str(e)


def get_rate_versions(db_instance):
    """Get rate versions from database"""
    try:
        conn = db_instance.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, version_name, edition_year, effective_from, is_active, 
                   created_at as imported_at
            FROM rate_versions 
            WHERE source = 'PWD'
            ORDER BY edition_year DESC
        """)
        versions = cursor.fetchall()
        conn.close()
        
        result = []
        for v in versions:
            result.append({
                'id': v[0],
                'name': v[1],
                'year': v[2],
                'effective_date': v[3],
                'is_active': v[4],
                'imported_at': v[5],
                'parent_count': 0,
                'child_count': 0
            })
        return result
    except:
        return []


def archive_version(db_instance, version_id):
    """Archive a version"""
    try:
        conn = db_instance.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE rate_versions SET is_active = 0 WHERE id = ?", (version_id,))
        conn.commit()
        conn.close()
        return True
    except:
        return False