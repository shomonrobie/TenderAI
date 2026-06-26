# utils/pwd_helpers.py

import streamlit as st
import pandas as pd
import os
import re
import pdfplumber
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple


def save_temp_file(uploaded_file, prefix="temp") -> str:
    """Save uploaded file to temporary location"""
    temp_path = f"{prefix}_import.pdf"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return temp_path


def get_pdf_total_pages(uploaded_file) -> int:
    """Get total number of pages in PDF"""
    temp_path = save_temp_file(uploaded_file, "temp_pages")
    with pdfplumber.open(temp_path) as pdf:
        total_pages = len(pdf.pages)
    os.remove(temp_path)
    return total_pages

# Add this method to your PWDImportWizard class

def _hierarchy_to_dataframe(self, hierarchy):
    """Convert hierarchy to editable dataframe"""
    
    rows = []
    
    # Add parents first
    for parent in hierarchy.get('parents', []):
        rows.append({
            'Type': 'Parent',
            'Code': parent['code'],
            'Description': parent['description'],
            'Parent Code': '',
            'Unit': '',
            'Dhaka Rate': '',
            'Chattogram Rate': '',
            'Khulna Rate': '',
            'Rajshahi Rate': ''
        })
    
    # Add children
    for child in hierarchy.get('children', []):
        row = {
            'Type': 'Child',
            'Code': child['pwd_code'],
            'Description': child['description'],
            'Parent Code': child['parent_code'],
            'Unit': child['unit'],
            'Dhaka Rate': child['rates'].get('Dhaka', ''),
            'Chattogram Rate': child['rates'].get('Chattogram', ''),
            'Khulna Rate': child['rates'].get('Khulna', ''),
            'Rajshahi Rate': child['rates'].get('Rajshahi', '')
        }
        rows.append(row)
    
    return pd.DataFrame(rows)

def parse_page_range(parser, uploaded_file, start_page: int, end_page: int, source: str = 'PWD') -> List[Dict]:
    """Parse a specific range of pages"""
    
    temp_path = save_temp_file(uploaded_file, "temp_range")
    items = []
    
    with pdfplumber.open(temp_path) as pdf:
        for page_num in range(start_page - 1, end_page):
            if page_num < len(pdf.pages):
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
                        if source == 'PWD':
                            page_items = parser._parse_table(table)
                        else:
                            page_items = parser._parse_table(table)
                        items.extend(page_items)
                else:
                    if source == 'PWD':
                        page_items = parser._parse_text(text)
                    else:
                        page_items = parser._parse_text(text)
                    items.extend(page_items)
    
    os.remove(temp_path)
    return items


def build_hierarchy_from_items(parser, items: List) -> Dict:
    """Build hierarchy from collected items"""
    return parser._organize_hierarchy(items)

# modules/parse_lged_pdf.py - _organize_hierarchy

def _organize_hierarchy(self, items):
    """Organize into parent-child structure - KEEP FULL DESCRIPTIONS"""
    
    hierarchy = {
        'parents': [],
        'children': [],
        'parent_child_map': {}
    }
    
    # First pass: collect parents (2-part codes)
    for item in items:
        code_parts = item['code'].split('.')
        if len(code_parts) == 2:
            hierarchy['parents'].append({
                'code': item['code'],
                'description': item['description'],  # FULL description
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
                'description': item['description'],  # FULL description
                'unit': item['unit'],
                'rates': item['rates']
            }
            
            hierarchy['children'].append(child_item)
            
            if parent_code in hierarchy['parent_child_map']:
                hierarchy['parent_child_map'][parent_code].append(child_item)
    
    return hierarchy

def fix_description_spacing(text: str) -> str:
    """Fix missing spaces in descriptions - PRESERVE proper spacing"""
    if not isinstance(text, str):
        return text
    
    # Add space before capital letters (camelCase to words)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    # Add space after periods
    text = re.sub(r'\.([A-Z])', r'. \1', text)
    # Add space after commas
    text = re.sub(r',([A-Za-z])', r', \1', text)
    # Fix multiple spaces (but keep at least one space)
    text = re.sub(r'\s+', ' ', text)
    # Fix period spacing
    text = re.sub(r'\s+\.', '.', text)
    # Fix space before punctuation
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    
    return text.strip()



def infer_unit_from_description(description: str) -> str:
    """Infer measurement unit from description text"""
    desc_lower = description.lower()
    
    unit_patterns = {
        'cum': ['cum', 'cubic meter', 'cubic metre'],
        'sqm': ['sqm', 'square meter', 'square metre'],
        'meter': ['meter', 'metre', 'm length'],
        'each': ['each', 'piece', 'per piece'],
        'job': ['job', 'lump sum'],
        'set': ['set', 'kit'],
        'kg': ['kg', 'kilogram', 'kilogramme'],
        'hour': ['hour', 'hr'],
        'month': ['month', 'per month'],
        'day': ['day', 'per day'],
        'km': ['km', 'kilometer', 'kilometre'],
        'tender': ['tender', 'per tender']
    }
    
    for unit, patterns in unit_patterns.items():
        for pattern in patterns:
            if pattern in desc_lower:
                return unit
    
    return ""


def find_issues(df: pd.DataFrame, source: str = 'PWD') -> List[Dict]:
    """
    Find all issues in the data (orphans, missing units, zero rates)
    This is the main function for finding issues - used by validate_data
    """
    issues = []
    parent_codes = set(df[df['Type'] == 'Parent']['Code'])
    
    # Check for orphans (children without valid parent)
    orphans = df[(df['Type'] == 'Child') & (~df['Parent Code'].isin(parent_codes))]
    for _, row in orphans.iterrows():
        issues.append({
            'type': 'Orphan Item',
            'code': row['Code'],
            'message': f"Child item '{row['Code']}' has no valid parent",
            'suggestion': "Assign to a parent using the dropdown"
        })
    
    # Check for missing units
    missing_unit = df[(df['Type'] == 'Child') & (df['Unit'] == '')]
    for _, row in missing_unit.iterrows():
        issues.append({
            'type': 'Missing Unit',
            'code': row['Code'],
            'message': f"Item '{row['Code']}' has no measurement unit",
            'suggestion': "Select a unit from dropdown"
        })
    
    # Check for zero rates based on source
    if source == 'PWD':
        zone_columns = ['Dhaka Rate', 'Chattogram Rate', 'Khulna Rate', 'Rajshahi Rate']
    else:
        zone_columns = ['Zone-A', 'Zone-B', 'Zone-C', 'Zone-D']
    
    for zone in zone_columns:
        if zone in df.columns:
            zero_rates = df[(df['Type'] == 'Child') & (df[zone] == 0)]
            for _, row in zero_rates.iterrows():
                issues.append({
                    'type': 'Zero Rate',
                    'code': row['Code'],
                    'message': f"Item '{row['Code']}' has zero rate for {zone}",
                    'suggestion': "Check if this is correct or update the rate"
                })
    
    # Check for missing descriptions (very short or empty)
    short_desc = df[df['Description'].str.len() < 10]
    for _, row in short_desc.iterrows():
        issues.append({
            'type': 'Short Description',
            'code': row['Code'],
            'message': f"Item '{row['Code']}' has very short description: '{row['Description']}'",
            'suggestion': "Review and expand the description"
        })
    
    return issues


def validate_pwd_data(df: pd.DataFrame, source: str = 'PWD') -> bool:
    """
    Validate PWD/LGED data quality.
    Returns True if valid, False if issues found.
    Also displays issues in the UI.
    """
    issues = find_issues(df, source)
    
    if issues:
        st.warning(f"⚠️ Found {len(issues)} issues that need attention:")
        
        for issue in issues[:10]:
            with st.expander(f"📌 {issue['type']}: {issue['code']}"):
                st.write(issue['message'])
                if issue.get('suggestion'):
                    st.info(f"💡 Suggestion: {issue['suggestion']}")
        
        if len(issues) > 10:
            st.caption(f"... and {len(issues) - 10} more issues")
        
        return False
    else:
        st.success("✅ All validation checks passed!")
        return True


def auto_fix_pwd_issues(df: pd.DataFrame, source: str = 'PWD') -> pd.DataFrame:
    """Auto-fix common PWD/LGED issues"""
    
    # Fix spacing
    df['Description'] = df['Description'].apply(fix_description_spacing)
    
    # Fix orphans - assign to first parent
    parent_codes = set(df[df['Type'] == 'Parent']['Code'])
    if parent_codes:
        first_parent = sorted(parent_codes)[0]
        df.loc[(df['Type'] == 'Child') & (~df['Parent Code'].isin(parent_codes)), 'Parent Code'] = first_parent
    
    # Fix missing units - try to infer from description
    for idx in df[df['Type'] == 'Child'].index:
        if df.loc[idx, 'Unit'] == '':
            inferred_unit = infer_unit_from_description(df.loc[idx, 'Description'])
            if inferred_unit:
                df.loc[idx, 'Unit'] = inferred_unit
    
    return df


def hierarchy_to_dataframe(hierarchy: Dict, source: str = 'PWD') -> pd.DataFrame:
    """Convert hierarchy to editable dataframe"""
    
    rows = []
    
    # Zone column names based on source
    if source == 'PWD':
        zone_columns = ['Dhaka Rate', 'Chattogram Rate', 'Khulna Rate', 'Rajshahi Rate']
    else:
        zone_columns = ['Zone-A', 'Zone-B', 'Zone-C', 'Zone-D']
    
    # Add parents
    for parent in hierarchy.get('parents', []):
        row = {
            'Type': 'Parent',
            'Code': parent['code'],
            'Description': fix_description_spacing(parent['description']),
            'Parent Code': '',
            'Unit': '',
        }
        for zone in zone_columns:
            row[zone] = ''
        rows.append(row)
    
    # Add children
    for child in hierarchy.get('children', []):
        row = {
            'Type': 'Child',
            'Code': child.get('pwd_code') or child.get('code'),
            'Description': fix_description_spacing(child['description']),
            'Parent Code': child['parent_code'],
            'Unit': child.get('unit', ''),
        }
        
        # Add rates based on source
        if source == 'PWD':
            row['Dhaka Rate'] = child.get('rates', {}).get('Dhaka', '')
            row['Chattogram Rate'] = child.get('rates', {}).get('Chattogram', '')
            row['Khulna Rate'] = child.get('rates', {}).get('Khulna', '')
            row['Rajshahi Rate'] = child.get('rates', {}).get('Rajshahi', '')
        else:
            row['Zone-A'] = child.get('rates', {}).get('Zone-A', '')
            row['Zone-B'] = child.get('rates', {}).get('Zone-B', '')
            row['Zone-C'] = child.get('rates', {}).get('Zone-C', '')
            row['Zone-D'] = child.get('rates', {}).get('Zone-D', '')
        
        rows.append(row)
    
    return pd.DataFrame(rows)



def get_column_config(source: str = 'PWD') -> Dict:
    """Get column configuration for data editor based on source"""
    
    if source == 'PWD':
        return {
            "Type": st.column_config.SelectboxColumn("Type", options=["Parent", "Child"], width="small"),
            "Code": st.column_config.TextColumn("Code", width="small"),
            "Description": st.column_config.TextColumn("Description", width="large"),
            "Parent Code": st.column_config.TextColumn("Parent", width="small"),
            "Unit": st.column_config.SelectboxColumn(
                "Unit", 
                options=["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "tender"],
                width="small"
            ),
            "Dhaka Rate": st.column_config.NumberColumn("Dhaka (৳)", format="%.2f", width="small"),
            "Chattogram Rate": st.column_config.NumberColumn("Chattogram (৳)", format="%.2f", width="small"),
            "Khulna Rate": st.column_config.NumberColumn("Khulna (৳)", format="%.2f", width="small"),
            "Rajshahi Rate": st.column_config.NumberColumn("Rajshahi (৳)", format="%.2f", width="small"),
        }
    else:
        return {
            "Type": st.column_config.SelectboxColumn("Type", options=["Parent", "Child"], width="small"),
            "Code": st.column_config.TextColumn("Code", width="small"),
            "Description": st.column_config.TextColumn("Description", width="large"),
            "Parent Code": st.column_config.TextColumn("Parent", width="small"),
            "Unit": st.column_config.SelectboxColumn(
                "Unit", 
                options=["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "day", "km"],
                width="small"
            ),
            "PWD Reference": st.column_config.TextColumn("PWD Ref", width="small"),
            "Zone-A": st.column_config.NumberColumn("Zone-A (Dhaka)", format="%.2f", width="small"),
            "Zone-B": st.column_config.NumberColumn("Zone-B (Chattogram)", format="%.2f", width="small"),
            "Zone-C": st.column_config.NumberColumn("Zone-C (Rajshahi)", format="%.2f", width="small"),
            "Zone-D": st.column_config.NumberColumn("Zone-D (Khulna)", format="%.2f", width="small"),
        }


def display_validation_summary(df: pd.DataFrame, source: str = 'PWD') -> None:
    """Display validation summary in UI"""
    validate_pwd_data(df, source)


def get_issues_summary(df: pd.DataFrame, source: str = 'PWD') -> Dict:
    """Get summary counts of issues"""
    issues = find_issues(df, source)
    
    summary = {
        'total_issues': len(issues),
        'orphans': len([i for i in issues if i['type'] == 'Orphan Item']),
        'missing_units': len([i for i in issues if i['type'] == 'Missing Unit']),
        'zero_rates': len([i for i in issues if i['type'] == 'Zero Rate']),
        'short_descriptions': len([i for i in issues if i['type'] == 'Short Description'])
    }
    
    return summary
def parse_quick_test(parser, settings, source: str = 'PWD') -> Dict:
    """
    Parse only first 10 pages for quick validation
    """
    import streamlit as st
    from datetime import datetime
    import os
    
    temp_file = save_temp_file(settings['file'], f"{source.lower()}_quick")
    
    with st.spinner("Parsing first 10 pages..."):
        # Different method names for PWD vs LGED
        if source == 'PWD':
            hierarchy = parser.parse_pdf_with_hierarchy(temp_file, max_pages=10)
        else:
            hierarchy = parser.parse_pdf(temp_file, max_pages=10)
    
    # Clean up temp file
    if os.path.exists(temp_file):
        os.remove(temp_file)
    
    # ========== RESTORE SPACES IN DESCRIPTIONS ==========
    from utils.rate_import_helpers import restore_text_spaces
    
    # Fix parent descriptions
    for parent in hierarchy.get('parents', []):
        if 'description' in parent:
            parent['description'] = restore_text_spaces(parent['description'])
    
    # Fix child descriptions
    for child in hierarchy.get('children', []):
        if 'description' in child:
            child['description'] = restore_text_spaces(child['description'])
    # ====================================================
    
    return {
        'hierarchy': hierarchy,
        'settings': settings,
        'edition_year': settings['edition_year'],
        'version_name': settings['version_name'],
        'dry_run': settings['dry_run'],
        'timestamp': datetime.now().isoformat(),
        'quick_test': True
    }



def parse_full_document(parser, settings, source: str = 'PWD') -> Dict:
    """
    Parse entire document at once
    """
    import streamlit as st
    from datetime import datetime
    import os
    
    temp_file = save_temp_file(settings['file'], f"{source.lower()}_full")
    
    with st.spinner("Parsing entire document... This may take a few minutes."):
        # Different method names for PWD vs LGED
        if source == 'PWD':
            hierarchy = parser.parse_pdf_with_hierarchy(temp_file, max_pages=None)
        else:
            hierarchy = parser.parse_pdf(temp_file, max_pages=None)
    
    # Clean up temp file
    if os.path.exists(temp_file):
        os.remove(temp_file)
    
    # ========== RESTORE SPACES IN DESCRIPTIONS ==========
    from utils.rate_import_helpers import restore_text_spaces
    
    # Fix parent descriptions
    for parent in hierarchy.get('parents', []):
        if 'description' in parent:
            parent['description'] = restore_text_spaces(parent['description'])
    
    # Fix child descriptions
    for child in hierarchy.get('children', []):
        if 'description' in child:
            child['description'] = restore_text_spaces(child['description'])
    # ====================================================
    
    return {
        'hierarchy': hierarchy,
        'settings': settings,
        'edition_year': settings['edition_year'],
        'version_name': settings['version_name'],
        'dry_run': settings['dry_run'],
        'timestamp': datetime.now().isoformat(),
        'quick_test': False
    }


def init_persistent_import():
    """Initialize persistent import session (placeholder)"""
    import streamlit as st
    st.info("💾 Persistent import feature coming soon...")
    # You can implement this later using the session manager
    return None

def restore_text_spaces(text: str) -> str:
    """
    Restore missing spaces in continuous text extracted from PDF.
    """
    if not isinstance(text, str):
        return text
    
    # Add space before capital letters (camelCase detection)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    
    # Add space after periods (but not for decimal points)
    text = re.sub(r'\.([A-Z])', r'. \1', text)
    text = re.sub(r'\.([a-z])', r'. \1', text)
    
    # Add space after commas
    text = re.sub(r',([A-Za-z])', r', \1', text)
    
    # Add space between number and word
    text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
    text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
    
    # Add space after colon
    text = re.sub(r':([A-Za-z])', r': \1', text)
    
    # Add space before common words that might be glued
    common_words = ['of', 'the', 'and', 'for', 'with', 'from', 'by', 'to', 'in', 'on', 'at', 'each', 'per', 'set', 'job', 'kit', 'additional', 'lump', 'sum', 'work', 'length', 'square', 'cubic', 'meter', 'metre', 'kilogram', 'kilogramme', 'hour', 'hr', 'month', 'day', 'km', 'tender', 'layout', 'construction', 'supply', 'installation', 'marking', 'removal', 'earthwork', 'excavation', 'filling', 'compaction', 'concrete', 'reinforcement', 'formwork', 'finishing', 'painting', 'coating']
    for word in common_words:
        text = re.sub(r'([a-z])(' + word + r')([A-Za-z])', r'\1 \2 \3', text, flags=re.I)
    
    # Fix multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Fix spaces before punctuation
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    
    return text.strip()