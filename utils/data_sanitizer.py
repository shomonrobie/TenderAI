# utils/data_sanitizer.py
import re
import pandas as pd

def sanitize_text(text: str) -> str:
    """
    Cleans raw strings by removing hidden formatting, symbols, 
    and duplicated spacing to prepare text for fuzzy matching.
    """
    if not text or pd.isna(text):
        return ""
    
    # 1. Convert to string and enforce unicode encoding
    clean = str(text)
    
    # 2. Replace hidden non-breaking spaces (\xa0, \t, \r, \n) with standard spaces
    clean = re.sub(r'[\xa0\t\r\n]+', ' ', clean)
    
    # 3. Strip leading list indicators, common bullet types, or prefix codes (e.g., "1.", "a)", "•")
    clean = re.sub(r'^[•\-\*]\s*', '', clean)
    clean = re.sub(r'^\d+[\.\)]\s*', '', clean)
    
    # 4. Remove aggressive punctuation clutter but preserve chemical/ratio markers (e.g., 1:2:4, 12mm)
    clean = re.sub(r'[;,\.\*\|\_]', ' ', clean)
    
    # 5. Collapse duplicate consecutive white spaces into a single space
    clean = re.sub(r'\s+', ' ', clean)
    
    # 6. Uniform trailing trim
    return clean.strip()

def sanitize_item_code(code: str) -> str:
    """
    Cleans structural PWD/e-GP item code paths, preserving string parameters 
    and stripping spaces without dropping crucial leading zeros.
    """
    if not code or pd.isna(code):
        return "N/A"
    
    clean = str(code).strip()
    # Normalize variants like "n/a", "na", or empty whitespace fields to uniform string tokens
    if clean.lower() in ['nan', 'n/a', 'na', '', 'null']:
        return "N/A"
        
    return clean
