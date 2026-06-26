import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime

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
    
    def _extract_continuous_text(self, text):
        """
        Restore spaces in continuous text by adding spaces before capital letters
        and after periods.
        """
        if not text:
            return text
        
        # Add space before capital letters (but not if already has space)
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        # Add space after periods
        text = re.sub(r'\.([A-Z])', r'. \1', text)
        # Add space after commas
        text = re.sub(r',([A-Za-z])', r', \1', text)
        # Add space after numbers followed by letters
        text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
        # Fix multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _parse_table(self, table):
        """Parse PWD table rows - RESTORE MISSING SPACES"""
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
            
            # Extract description - RESTORE SPACES
            desc = ""
            if code_col is not None and code_col + 1 < len(row_cells):
                desc = row_cells[code_col + 1]
                # Remove any item code pattern
                desc = re.sub(r'^\d+(?:\.\d+)?\s*$', '', desc)
                # RESTORE MISSING SPACES
                desc = self._extract_continuous_text(desc)
            
            if not desc or len(desc) < 5:
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
        """Parse raw text - RESTORE MISSING SPACES"""
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
                # RESTORE MISSING SPACES
                desc = self._extract_continuous_text(desc)
                
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
                    desc = re.sub(r'\s+', ' ', desc).strip()
            else:
                desc = remaining
                # RESTORE MISSING SPACES
                desc = self._extract_continuous_text(desc)
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