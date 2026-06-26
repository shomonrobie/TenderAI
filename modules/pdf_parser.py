"""
PDF Tender Notice Parser - Refactored & Production-Ready
Extracts all fields from Bangladeshi e-GP tender notices with robust regex & fallbacks.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import streamlit as st

try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


class TenderPDFParser:
    """Parse Bangladeshi e-GP tender notice PDFs and extract structured information."""
    
    def __init__(self):
        # District to Division mapping for automatic location resolution
        self.division_map = {
            'Dhaka': 'Dhaka', 'Gazipur': 'Dhaka', 'Narayanganj': 'Dhaka', 'Munshiganj': 'Dhaka',
            'Chittagong': 'Chittagong', 'Cumilla': 'Chittagong', "Cox's Bazar": 'Chittagong',
            'Rajshahi': 'Rajshahi', 'Bogura': 'Rajshahi', 'Pabna': 'Rajshahi', 'Natore': 'Rajshahi',
            'Rangpur': 'Rangpur', 'Dinajpur': 'Rangpur', 'Thakurgaon': 'Rangpur', 'Kurigram': 'Rangpur',
            'Khulna': 'Khulna', 'Jessore': 'Khulna', 'Satkhira': 'Khulna', 'Bagerhat': 'Khulna',
            'Barisal': 'Barisal', 'Bhola': 'Barisal', 'Patuakhali': 'Barisal', 'Pirojpur': 'Barisal',
            'Sylhet': 'Sylhet', 'Moulvibazar': 'Sylhet', 'Habiganj': 'Sylhet', 'Sunamganj': 'Sylhet',
            'Mymensingh': 'Mymensingh', 'Netrokona': 'Mymensingh', 'Sherpur': 'Mymensingh', 'Jamalpur': 'Mymensingh'
        }

    def normalize_text(self, text: str) -> str:
        """Clean PDF-extracted text to handle common extraction artifacts."""
        if not text:
            return ""
        # Replace multiple spaces/newlines with single space
        text = re.sub(r'\s+', ' ', text)
        # Fix common PDF date artifacts: "30- A p r -2026" -> "30-Apr-2026"
        text = re.sub(r'(\d)\s*-\s*([A-Za-z])\s*([A-Za-z])\s*([A-Za-z])\s*-', r'\1-\2\3\4-', text)
        # Remove stray spaces around hyphens in dates
        text = re.sub(r'(\d)\s*-\s*(\d)', r'\1-\2', text)
        return text.strip()

    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from various formats, handling PDF artifacts."""
        if not date_str:
            return None
        # Clean up spaces
        date_str = re.sub(r'\s+', ' ', date_str).strip()
        formats = [
            '%d-%b-%Y %H:%M', '%d-%b-%Y', '%d-%B-%Y %H:%M', '%d-%B-%Y',
            '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M', '%d/%m/%Y',
            '%d %b %Y %H:%M', '%d %B %Y %H:%M'
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def extract_field(self, text: str, label: str, next_labels: List[str], default: Any = "") -> str:
        """
        Extract a field by looking for its label and stopping before the next known label.
        Much more robust than simple regex for normalized PDF text.
        """
        if not next_labels:
            next_labels = [""]
            
        # ✅ FIX: Handle colons with optional spaces and handle line breaks
        # Build lookahead pattern: stop at any next label or end of string
        stop_pattern = '|'.join(re.escape(l) for l in next_labels if l)
        
        # More flexible pattern with optional colon and spaces
        pattern = rf'{re.escape(label)}\s*[:\.]?\s*(.+?)(?=\s*(?:{stop_pattern})|$)'
        
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            val = match.group(1).strip()
            # Clean trailing punctuation/whitespace
            val = re.sub(r'[\|,\n\r]+$', '', val).strip()
            # Clean multiple spaces
            val = re.sub(r'\s+', ' ', val)
            return val if val else str(default)
        return str(default)

    def _extract_tender_id(self, text: str) -> str:
        """Extract Tender ID using multiple patterns"""
        patterns = [
            r'Tender/Proposal ID\s*:\s*(\d+)',
            r'Tender/Proposal ID\s*:\s*(\d{7,})',
            r'ID\s*:\s*(\d{7,})',
            r'Tender ID\s*:\s*(\d+)',
            r'Proposal ID\s*:\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback: look for 7+ digit numbers near "ID"
        fallback_pattern = r'(?:Tender|Proposal)?\s*ID[^\d]*(\d{7,})'
        match = re.search(fallback_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return ""

    def extract_field_bak(self, text: str, label: str, next_labels: List[str], default: Any = "") -> str:
        """
        Extract a field by looking for its label and stopping before the next known label.
        Much more robust than simple regex for normalized PDF text.
        """
        if not next_labels:
            next_labels = [""]
            
        # Build lookahead pattern: stop at any next label or end of string
        stop_pattern = '|'.join(re.escape(l) for l in next_labels)
        pattern = rf'{re.escape(label)}\s*[:\.]?\s*(.+?)(?=\s*(?:{stop_pattern})|$)'
        
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            val = match.group(1).strip()
            # Clean trailing punctuation/whitespace
            val = re.sub(r'[\|,\n\r]+$', '', val).strip()
            return val if val else str(default)
        return str(default)

    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extract text from uploaded PDF file."""
        if not PDF_SUPPORT:
            st.error("PyPDF2 not installed. Run: `pip install PyPDF2`")
            return ""
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return self.normalize_text(text)
        except Exception as e:
            st.error(f"Error reading PDF: {str(e)}")
            return ""

    def extract_lots(self, text: str) -> List[Dict[str, Any]]:
        """Extract lot information from the tender table."""
        lots = []
        # Regex to capture: Lot No | Description | Location | Security | Start | End
        lot_pattern = re.compile(
            r'Lot\s*No[\.\s]*?(\d+)\s*\|?\s*(.*?)\s*\|?\s*(.*?)\s*\|?\s*([\d,]+)\s*\|?\s*(\d{2}[-/]\w+[-/]\d{4})\s*\|?\s*(\d{2}[-/]\w+[-/]\d{4})',
            re.IGNORECASE | re.DOTALL
        )

        for match in lot_pattern.finditer(text):
            lot = {
                'lot_no': match.group(1),
                'identification': match.group(2).strip().rstrip('|').strip(),
                'location': match.group(3).strip().rstrip('|').strip(),
                'security_amount': self._safe_float(match.group(4)),
                'start_date': match.group(5).strip(),
                'completion_date': match.group(6).strip()
            }
            lots.append(lot)

        # Fallback: Pipe-delimited line parser
        if not lots and '|' in text:
            lines = text.split('\n')
            for line in lines:
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if len(parts) >= 6 and parts[0].isdigit():
                    try:
                        lots.append({
                            'lot_no': parts[0],
                            'identification': parts[1],
                            'location': parts[2],
                            'security_amount': self._safe_float(parts[3]),
                            'start_date': parts[4],
                            'completion_date': parts[5]
                        })
                    except (ValueError, IndexError):
                        continue
        return lots

    def _extract_package_description(self, text: str) -> str:
        """Extract package description/tender title"""
        # Look for package no and description
        pattern = r'Tender/Proposal Package No\. and Description\s*:\s*(.+?)(?=\s*(?:Category|Scheduled Tender|$))'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            desc = match.group(1).strip()
            # Clean up extra whitespace and newlines
            desc = re.sub(r'\s+', ' ', desc)
            # Limit length
            return desc[:200] if len(desc) > 200 else desc
        return ""

    def extract_tender_info(self, text: str) -> Dict[str, Any]:
        """Extract all tender information from normalized text with fallbacks"""
        
        # === BASIC INFO ===
        info = {
            'ministry': self.extract_field(text, 'Ministry', ['Division', 'Organization']),
            'organization': self.extract_field(text, 'Organization', ['Procuring Entity Name']),
            'procuring_entity': self.extract_field(text, 'Procuring Entity Name', ['Procuring Entity Code', 'Procurement Nature']),
            'procuring_entity_district': self.extract_field(text, 'Procuring Entity District', ['Procurement Nature']),
            'procurement_nature': self.extract_field(text, 'Procurement Nature', ['Procurement Type']),
            'procurement_type': self.extract_field(text, 'Procurement Type', ['Event Type']).lower().replace(' ', '_'),
            'event_type': self.extract_field(text, 'Event Type', ['Invitation Reference']),
            'invitation_ref_no': self.extract_field(text, 'Invitation Reference No.', ['App ID']),
            'app_id': self.extract_field(text, 'App ID', ['Tender/Proposal ID']),
            'tender_id': self._extract_tender_id(text) or self.extract_field(text, 'Tender/Proposal ID', ['Re-Tendered ID', 'Key Information']),
            're_tendered_id': self.extract_field(text, 'Re-Tendered ID', ['Key Information']),
            'project_code': self.extract_field(text, 'Project Code', ['Project Name']),
            'project_name': self.extract_field(text, 'Project Name', ['Tender/Proposal Package']),
            'package_no': self.extract_field(text, 'Tender/Proposal Package No.', ['Brief Description']),
            
            # ✅ IMPROVED: Tender title from multiple possible labels
            'tender_title': (
                self.extract_field(text, 'Brief Description of Goods and Related Service', ['Category', 'Evaluation']) or
                self.extract_field(text, 'Brief Description of Works', ['Category', 'Evaluation']) or
                self._extract_package_description(text) or
                self.extract_field(text, 'PROCUREMENT OF', ['Category', 'Evaluation'], default='').strip() or
                ''
            ),

            
            'evaluation_type': self.extract_field(text, 'Evaluation Type', ['Document Available']),
            'mode_of_payment': self.extract_field(text, 'Mode of Payment', ['Tender/Proposal Security Valid']),
            'eligibility_criteria': self.extract_field(text, 'Eligibility of Tenderer', ['Brief Description']),
            
            # Official contact
            'inviting_official_name': self.extract_field(text, 'Name of Official Inviting Tender/Proposal', ['Designation']),
            'inviting_official_designation': self.extract_field(text, 'Designation of Official Inviting Tender/Proposal', ['Address']),
            'inviting_official_phone': self.extract_field(text, 'Phone No', ['Fax No', 'Address', 'Thana']),
            'inviting_official_email': self.extract_field(text, 'Email', ['Address', 'Contact details'], default=''),
            
            # ✅ IMPROVED: Multi-line address extraction
            'inviting_official_address': self._extract_multiline_field(text, 'Address of Official Inviting Tender/Proposal', ['Contact details', 'The procuring entity']),
            'inviting_official_city': self.extract_field(text, 'City', ['Thana']),
            'inviting_official_thana': self.extract_field(text, 'Thana', ['District']),
            'inviting_official_district': self.extract_field(text, 'District', ['Country']),
            'country': 'Bangladesh'
        }
        
        # === DATES ===
        date_fields = {
            'tender_publication_date': r'Scheduled Tender/Proposal Publication Date and Time\s*:\s*(.+?)(?=\s*(?:Tender/Proposal Document last|Pre - Tender))',
            'document_selling_end_date': r'Tender/Proposal Document last selling / downloading Date and Time\s*:\s*(.+?)(?=\s*(?:Pre - Tender))',
            'pre_bid_meeting_start': r'Pre - Tender/Proposal meeting Start Date and Time\s*:\s*(.+?)(?=\s*(?:Pre - Tender/Proposal meeting End))',
            'pre_bid_meeting_end': r'Pre - Tender/Proposal meeting End Date and Time\s*:\s*(.+?)(?=\s*(?:Tender/Proposal Closing))',
            'submission_deadline': r'Tender/Proposal Closing Date and Time\s*:\s*(.+?)(?=\s*(?:Tender/Proposal Opening))',
            'security_submission_deadline': r'Last Date and Time for Tender/Proposal Security Submission\s*:\s*(.+?)(?=\s*(?:Information for Tenderer|Eligibility))',
            'bid_opening_date': r'Tender/Proposal Opening Date and Time\s*:\s*(.+?)(?=\s*(?:Last Date and Time|Information for Tenderer))',
            'security_valid_upto': r'Tender/Proposal Security Valid Up to\s*:\s*(.+?)(?=\s*(?:Tender/Proposal Valid))',
            'tender_valid_upto': r'Tender/Proposal Valid Up to\s*:\s*(.+?)(?=\s*(?:Information for Tenderer|Eligibility|Note))'  # ✅ ADDED
        }
        for key, pattern in date_fields.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            val = match.group(1).strip() if match else ""
            info[key] = self.parse_date(val)
        
        # === FINANCIALS ===
        # Tender security: try lot table first, then direct field
        info['tender_security'] = self._safe_float(
            self._extract_by_pattern(text, r'Tender/Proposal\s*security\s*\(Amount in BDT\)\s*:\s*([\d,]+)') or
            self._extract_lot_security(text)  # ✅ NEW: fallback to lot table
        )
        
        info['document_fee'] = self._safe_float(
            self._extract_by_pattern(text, r'Tender/Proposal Document Price\s*\(In BDT\)\s*:\s*([\d,]+)')
        )
        info['official_estimate'] = 0  # Usually not in e-GP notices
        
        # === LOTS ===
        info['lots'] = self.extract_lots(text)
        
        # === LOCATION RESOLUTION ===
        district_raw = info['inviting_official_district'] or info['procuring_entity_district'] or ''
        district = re.split(r'[-\s]', district_raw)[0].title() if district_raw else ''
        info['district'] = district
        info['thana'] = info.get('inviting_official_thana', '').title()
        info['division'] = self.division_map.get(info['district'], '')
        
        return info
    def _extract_multiline_field(self, text: str, label: str, stop_labels: List[str], default: str = "") -> str:
        """Extract multi-line field values (like addresses)"""
        pattern = rf'{re.escape(label)}\s*[:\.]?\s*(.+?)(?=\s*(?:{"|".join(re.escape(l) for l in stop_labels)})|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            val = match.group(1).strip()
            # Clean up PDF artifacts: remove extra spaces, normalize line breaks
            val = re.sub(r'\s+', ' ', val)
            val = re.sub(r'\s*[:\.]\s*', ': ', val)
            return val if val else default
        return default


    def _extract_lot_security(self, text: str) -> str:
        """Extract tender security from lot table when not in main field"""
        # Pattern for single-lot tables: | Single Lot | ... | 500000 | ...
        lot_pattern = r'(?:Single Lot|\d+)\s*\|?\s*[^\|]+\s*\|?\s*[^\|]+\s*\|?\s*([\d,]+)\s*\|?'
        match = re.search(lot_pattern, text, re.IGNORECASE)
        return match.group(1).strip() if match else ""


    def _extract_by_pattern(self, text: str, pattern: str) -> str:
        """Helper for simple regex extraction"""
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""
        
    def fill_tender_form(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Create a complete dictionary ready for database insertion/form filling."""
        default_deadline = datetime.now() + timedelta(days=14)
        return {
            'tender_id': info.get('tender_id', ''),
            'app_id': info.get('app_id', ''),
            'tender_title': info.get('tender_title', ''),
            'procuring_entity': info.get('procuring_entity', ''),
            'division': info.get('division', ''),
            'district': info.get('district', ''),
            'thana': info.get('thana', ''),
            'country': info.get('country', 'Bangladesh'),
            'procurement_type': info.get('procurement_type', 'works').lower().replace(' ', '_'),
            'official_estimate': info.get('official_estimate', 0),
            'submission_deadline': info.get('submission_deadline') or default_deadline,
            'tender_security': info.get('tender_security', 0),
            'document_fee': info.get('document_fee', 0),
            'evaluation_type': info.get('evaluation_type', 'Lot wise'),
            'eligibility_criteria': info.get('eligibility_criteria', 'As Per Tender Documents'),
            'mode_of_payment': info.get('mode_of_payment', 'Payment through Bank'),
            'invitation_ref_no': info.get('invitation_ref_no', ''),
            'project_code': info.get('project_code', ''),
            'project_name': info.get('project_name', ''),
            'package_no': info.get('package_no', ''),
            'security_valid_upto': info.get('security_valid_upto'),
            'tender_valid_upto': info.get('tender_valid_upto'),
            'inviting_official_name': info.get('inviting_official_name', ''),
            'inviting_official_designation': info.get('inviting_official_designation', ''),
            'inviting_official_phone': info.get('inviting_official_phone', ''),
            'inviting_official_city': info.get('inviting_official_city', ''),
            'inviting_official_thana': info.get('inviting_official_thana', ''),
            'inviting_official_district': info.get('inviting_official_district', ''),
            'lots': info.get('lots', []),
            'notes': f"Auto-extracted from tender notice on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }

    # ==================== HELPER METHODS ====================
    
    def _extract_by_pattern(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    def _safe_float(self, val: str) -> float:
        try:
            return float(val.replace(',', ''))
        except (ValueError, AttributeError, TypeError):
            return 0.0


def parse_tender_pdf(uploaded_file) -> Optional[Dict[str, Any]]:
    """Main function to parse tender PDF and return structured data."""
    if not PDF_SUPPORT:
        st.error("PyPDF2 is required for PDF parsing. Install with: `pip install PyPDF2`")
        return None

    parser = TenderPDFParser()
    text = parser.extract_text_from_pdf(uploaded_file)
    if not text.strip():
        st.warning("No text extracted from PDF. Ensure it's not a scanned image-only file.")
        return None

    info = parser.extract_tender_info(text)
    return parser.fill_tender_form(info)