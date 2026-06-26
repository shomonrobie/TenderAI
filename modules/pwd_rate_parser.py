"""
PWD Rate Schedule 2022-2026 Parser Module for TenderAI
Extracts item codes, descriptions, and regional rates from PWD PDF documents
"""

import re
import sqlite3
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")


@dataclass
class PWDRateItem:
    """Represents a single PWD rate schedule item"""
    pwd_code: str
    parent_code: Optional[str]
    chapter_number: str
    description: str
    unit: str
    rates: Dict[str, float]  # zone_name -> rate


@dataclass
class ParseReport:
    """Reports parsing results"""
    status: str = "Success"
    total_pages_scanned: int = 0
    total_items_found: int = 0
    total_rates_found: int = 0
    validation_errors: List[Dict] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []


class PWDRateParser:
    """
    Parser for PWD (Public Works Department) Rate Schedule PDFs.
    
    Handles the specific format of Bangladeshi PWD rate schedules including:
    - Multi-row descriptions
    - Variable zone columns (Dhaka, Chattogram, Khulna, Rajshahi)
    - Custom formatting with Tk. currency
    """
    
    # Standard zone names as per PWD schedule
    ZONE_NAMES = [
        "Dhaka, Mymensingh",
        "Chattogram, Sylhet", 
        "Khulna, Barisal, Gopalgonj",
        "Rajshahi, Rangpur"
    ]
    
    # Short zone names for database storage
    ZONE_SHORT_NAMES = ["Dhaka", "Chattogram", "Khulna", "Rajshahi"]
    
    def __init__(self, db_instance=None, db_path: Optional[str] = None):
        """
        Initialize the parser.
        
        Args:
            db_instance: Database manager instance (preferred)
            db_path: Path to SQLite database (legacy, use db_instance instead)
        """
        self.db = db_instance
        
        # Legacy support for db_path
        if db_path is None and db_instance is None:
            from database.unified_db_manager import db
            self.db = db
        elif db_path:
            import warnings
            warnings.warn("db_path is deprecated. Use db_instance instead.", DeprecationWarning)
            self._legacy_db_path = db_path
    
    def get_connection(self):
        """Get database connection from unified manager."""
        if self.db:
            return self.db.get_connection()
        elif hasattr(self, '_legacy_db_path'):
            # Legacy fallback
            db_dir = Path(self._legacy_db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            return sqlite3.connect(str(self._legacy_db_path))
        else:
            from database.unified_db_manager import db
            return db.get_connection()
    
    # ❌ REMOVED: init_database() - Tables already exist in unified manager
    
    def import_pdf(self, file_path: str, edition_year: int = 2022, 
                   dry_run: bool = False) -> ParseReport:
        """
        Import PWD rate schedule from PDF.
        
        Args:
            file_path: Path to the PDF file
            edition_year: Year of the rate schedule (default: 2022)
            dry_run: If True, don't save to database
            
        Returns:
            ParseReport with statistics and any errors
        """
        report = ParseReport()
        
        conn = None if dry_run else self.get_connection()
        cursor = None if dry_run else conn.cursor()
        
        try:
            with pdfplumber.open(file_path) as pdf:
                report.total_pages_scanned = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    # Try table extraction first
                    tables = page.extract_tables(table_settings={
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                        "snap_tolerance": 5,
                    })
                    
                    if tables and len(tables) > 0:
                        self._process_tables(tables, edition_year, report, dry_run, cursor)
                    else:
                        # Fallback to raw line parsing
                        self._parse_raw_lines(text, edition_year, report, dry_run, cursor)
                        
        except Exception as e:
            report.status = "Failed"
            report.validation_errors.append({"page": "Global", "error": str(e)})
            import traceback
            traceback.print_exc()
        
        if not dry_run and conn:
            conn.commit()
            conn.close()
        
        return report
    
    def _process_tables(self, tables: List, edition_year: int, 
                        report: ParseReport, dry_run: bool, cursor):
        """Process extracted tables from PDF."""
        for table in tables:
            if not table or len(table) < 2:
                continue
            
            for row in table:
                if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                    continue
                
                row_cells = [str(cell).strip() if cell else '' for cell in row]
                
                # Find item code
                pwd_code = None
                code_col = None
                for col, cell in enumerate(row_cells):
                    if re.match(r'^\d{1,2}\.\d{1,2}(?:\.\d{1,2})?$', cell):
                        pwd_code = cell
                        code_col = col
                        break
                
                if not pwd_code:
                    continue
                
                # Determine parent code (for 3-part codes)
                code_parts = pwd_code.split('.')
                parent_code = None
                if len(code_parts) >= 2:
                    parent_code = '.'.join(code_parts[:2])
                
                chapter_num = code_parts[0]
                
                # Extract description
                desc = ""
                if code_col is not None and code_col + 1 < len(row_cells):
                    desc = row_cells[code_col + 1]
                    # Clean up description
                    desc = re.sub(r'\s+', ' ', desc).strip()
                
                if not desc or len(desc) < 5:
                    continue
                
                report.total_items_found += 1
                
                # Find unit
                unit = self._extract_unit(row_cells, code_col)
                
                # Zone columns (adjust based on your PDF structure)
                zone_indices = [5, 6, 7, 8] if code_col is None or code_col < 5 else [code_col + 3, code_col + 4, code_col + 5, code_col + 6]
                
                rates = {}
                for idx, zone_idx in enumerate(zone_indices):
                    if idx < len(self.ZONE_SHORT_NAMES) and zone_idx < len(row_cells):
                        clean_rate = self._extract_rate(row_cells[zone_idx])
                        
                        if clean_rate is not None and clean_rate > 0:
                            rates[self.ZONE_SHORT_NAMES[idx]] = clean_rate
                            report.total_rates_found += 1
                
                if not dry_run and cursor and rates:
                    self._save_to_database(cursor, pwd_code, parent_code, chapter_num,
                                          desc, unit, rates, edition_year)
    
    def _parse_raw_lines(self, text: str, edition_year: int, 
                         report: ParseReport, dry_run: bool, cursor):
        """Fallback parser for raw text lines."""
        if not text:
            return
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for item code pattern at start of line
            code_match = re.match(r'^(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\s+', line)
            if code_match:
                pwd_code = code_match.group(1)
                code_parts = pwd_code.split('.')
                
                # Determine parent code
                parent_code = None
                if len(code_parts) >= 2:
                    parent_code = '.'.join(code_parts[:2])
                
                chapter_num = code_parts[0]
                
                # Remove the code from the beginning
                remaining = line[len(code_match.group(0)):].strip()
                
                # Find all rate patterns
                rate_pattern = r'Tk\.?\s*([\d,]+(?:\.\d{2})?)'
                rate_matches = list(re.finditer(rate_pattern, remaining, re.I))
                
                if rate_matches:
                    # Description is everything before the first rate
                    first_rate_pos = rate_matches[0].start()
                    desc = remaining[:first_rate_pos].strip()
                    
                    # Extract rates
                    rates = {}
                    for idx, match in enumerate(rate_matches[:4]):
                        if idx < len(self.ZONE_SHORT_NAMES):
                            rate_str = match.group(1).replace(',', '')
                            try:
                                rates[self.ZONE_SHORT_NAMES[idx]] = float(rate_str)
                            except ValueError:
                                pass
                else:
                    desc = remaining
                    rates = {}
                
                # Clean up description
                desc = re.sub(r'\s+', ' ', desc).strip()
                
                # Extract unit (common patterns)
                unit = self._extract_unit_from_text(desc)
                # Remove unit from description if present
                if unit and unit in desc.lower():
                    desc = re.sub(r'\s+' + re.escape(unit) + r'\s*$', '', desc, flags=re.I)
                
                # Only process if we have a meaningful description
                if desc and len(desc) > 5 and rates:
                    report.total_items_found += 1
                    report.total_rates_found += len(rates)
                    
                    if not dry_run and cursor:
                        self._save_to_database(cursor, pwd_code, parent_code, chapter_num,
                                              desc, unit, rates, edition_year)
    
    def _extract_unit(self, row_cells: List[str], code_col: Optional[int]) -> str:
        """Extract measurement unit from table row."""
        if code_col is None:
            return ""
        
        unit_patterns = ['cum', 'sqm', 'meter', 'each', 'job', 'set', 'kg', 
                        'hour', 'point', 'per month', 'per tender', 'per set per site']
        
        for col in range(code_col + 2, min(code_col + 5, len(row_cells))):
            if col < len(row_cells):
                cell = row_cells[col].lower()
                for pattern in unit_patterns:
                    if pattern in cell:
                        return pattern
        return ""
    
    def _extract_unit_from_text(self, text: str) -> str:
        """Extract unit from text description."""
        text_lower = text.lower()
        unit_patterns = {
            'cum': r'\bcum\b',
            'sqm': r'\bsqm\b',
            'meter': r'\bmeter\b',
            'each': r'\beach\b',
            'job': r'\bjob\b',
            'set': r'\bset\b',
            'kg': r'\bkg\b',
        }
        
        for unit, pattern in unit_patterns.items():
            if re.search(pattern, text_lower):
                return unit
        return ""
    
    def _extract_rate(self, raw_rate: str) -> Optional[float]:
        """Extract numeric rate from string."""
        if not raw_rate:
            return None
        
        # Pattern for Tk. amount with commas and decimals
        match = re.search(r'(?:Tk\.?\s*)?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', str(raw_rate), re.I)
        if match:
            clean = match.group(1).replace(',', '')
            try:
                return float(clean)
            except ValueError:
                pass
        
        # Fallback: any number with optional decimal
        match = re.search(r'(\d+(?:\.\d+)?)', str(raw_rate))
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        
        return None
    
    def _save_to_database(self, cursor, pwd_code: str, parent_code: Optional[str], 
                         chapter_num: str, description: str, unit: str, 
                         rates: Dict[str, float], edition_year: int):
        """Save parsed data to unified database tables."""
        try:
            # Insert into pwd_parents (for parent items, 2-part codes)
            if parent_code is None or len(pwd_code.split('.')) == 2:
                cursor.execute("""
                    INSERT OR REPLACE INTO pwd_parents 
                    (pwd_code, description, chapter_number)
                    VALUES (?, ?, ?)
                """, (pwd_code, description[:2000], chapter_num))
            
            # Insert into pwd_children (for child items, 3-part codes)
            if parent_code:
                cursor.execute("""
                    INSERT OR REPLACE INTO pwd_children 
                    (pwd_code, parent_code, description, unit, edition_year)
                    VALUES (?, ?, ?, ?, ?)
                """, (pwd_code, parent_code, description[:2000], unit, edition_year))
            
            # Insert rates into pwd_rates
            for zone_name, rate in rates.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO pwd_rates 
                    (pwd_code, zone_name, unit_rate, edition_year)
                    VALUES (?, ?, ?, ?)
                """, (pwd_code, zone_name, rate, edition_year))
                
        except Exception as e:
            # Don't fail the whole import for a single item
            print(f"Warning: Failed to save {pwd_code}: {e}")
            pass


# Convenience function for quick import
def import_pwd_rates(pdf_path: str, edition_year: int = 2022, 
                     dry_run: bool = False) -> ParseReport:
    """
    Quick import function for PWD rate schedules.
    
    Args:
        pdf_path: Path to the PDF file
        edition_year: Edition year of the rate schedule
        dry_run: If True, don't save to database
        
    Returns:
        ParseReport with import statistics
    """
    from database.unified_db_manager import db
    parser = PWDRateParser(db_instance=db)
    return parser.import_pdf(pdf_path, edition_year, dry_run)


# Example usage
if __name__ == "__main__":
    # Test the parser
    from database.unified_db_manager import db
    parser = PWDRateParser(db_instance=db)
    
    # Import PDF (replace with your file path)
    report = parser.import_pdf("PWD_RATE_SCHEDULE_2022_2026.pdf", edition_year=2022)
    
    print(f"Status: {report.status}")
    print(f"Pages scanned: {report.total_pages_scanned}")
    print(f"Items found: {report.total_items_found}")
    print(f"Rates found: {report.total_rates_found}")
    
    if report.validation_errors:
        print(f"Errors: {len(report.validation_errors)}")