"""
PDF Tender Notice Parser - Production-Ready v5.1
Handles both: (1) e-GP PDF text extraction and (2) tab-separated text paste.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import streamlit as st
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup
from utils.helpers import debug_print
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


class TenderPDFParser:
    """Parse Bangladeshi e-GP tender notices from PDF or tab-separated text."""

    def __init__(self):
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

        # Field name mapping: normalized -> canonical
        self.FIELD_MAP = {
            'ministry': 'ministry',
            'division': 'division',
            'organization': 'organization',
            'procuring entity name': 'procuring_entity',
            'procuring entity code': 'procuring_entity_code',
            'procuring entity district': 'procuring_entity_district',
            'procurement nature': 'procurement_nature',
            'procurement type': 'procurement_type',
            'event type': 'event_type',
            'invitation for': 'invitation_for',
            'invitation reference no.': 'invitation_ref_no',
            'invitation reference no': 'invitation_ref_no',
            'tender/proposal status': 'tender_status',
            'app id': 'app_id',
            'tender/proposal id': 'tender_id',
            'key information and funding information': 'key_info',
            'procurement method': 'procurement_method',
            'budget type': 'budget_type',
            'source of funds': 'source_of_funds',
            'particular information': 'particular_info',
            'project code': 'project_code',
            'project name': 'project_name',
            'tender/proposal package no. and description': 'package_no',
            'category': 'category',
            'scheduled tender/proposal publication date and time': 'tender_publication_date',
            'tender/proposal document last selling / downloading date and time': 'document_selling_end_date',
            'pre - tender/proposal meeting start date and time': 'pre_bid_meeting_start',
            'pre - tender/proposal meeting end date and time': 'pre_bid_meeting_end',
            'tender/proposal closing date and time': 'submission_deadline',
            'tender/proposal opening date and time': 'bid_opening_date',
            'last date and time for tender/proposal security submission': 'security_submission_deadline',
            'information for tenderer/consultant': 'info_for_tenderer',
            'eligibility of tenderer': 'eligibility_criteria',
            'brief description of works': 'tender_title',
            'brief description of goods and related service': 'tender_title',
            'evaluation type': 'evaluation_type',
            'document available': 'document_available',
            'document fees': 'document_fees',
            'tender/proposal document price (in bdt)': 'document_fee',
            'mode of payment': 'mode_of_payment',
            'tender/proposal security valid up to': 'security_valid_upto',
            'tender/proposal valid up to': 'tender_valid_upto',
            'tender/proposal security (amount in bdt)': 'tender_security',
            'name of official inviting tender/proposal': 'inviting_official_name',
            'designation of official inviting tender/proposal': 'inviting_official_designation',
            'address of official inviting tender/proposal': 'inviting_official_address',
            'contact details of official inviting tender/proposal': 'contact_details',
            'phone no': 'inviting_official_phone',
            'phone no.': 'inviting_official_phone',
            'fax no': 'fax_no',
            'fax no.': 'fax_no',
            'city': 'inviting_official_city',
            'thana': 'inviting_official_thana',
            'district': 'inviting_official_district',
            'country': 'country',
            'note': 'notes',
        }

    def _detect_format(self, text: str) -> str:
        """Detect if text is PDF-extracted or tab-separated."""
        # Tab-separated format has labels and values on same line with tabs/spaces
        # Check for pattern: "Label : Value" or "Label\tValue" on same line
        tab_lines = 0
        for line in text.split('\n'):
            if ':' in line and len(line.split(':')[0].strip()) > 10:
                tab_lines += 1
        # If >50% of lines have "Label : Value" pattern, it's tab-separated
        total_lines = len([l for l in text.split('\n') if l.strip()])
        if total_lines > 0 and tab_lines / total_lines > 0.3:
            return 'tab'
        return 'pdf'

    def _parse_tab_separated(self, text: str) -> Dict[str, str]:
        """Parse tab-separated or space-separated label:value text."""
        result = {}
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Split on first ':' or first 2+ spaces or tab
            if ':' in line:
                parts = line.split(':', 1)
                label = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else ''
            elif '\t' in line:
                parts = line.split('\t', 1)
                label = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else ''
            else:
                # Try splitting on 2+ spaces
                parts = re.split(r'\s{2,}', line, 1)
                if len(parts) == 2 and len(parts[0]) > 5:
                    label = parts[0].strip()
                    value = parts[1].strip()
                else:
                    continue
            
            # Normalize label
            normalized = label.lower().rstrip('.').rstrip(':').strip()
            if normalized in self.FIELD_MAP:
                canonical = self.FIELD_MAP[normalized]
                result[canonical] = value
        
        return result

    def _join_split_labels(self, text: str) -> str:
        """Join labels split across lines (PDF format only)."""
        nl = chr(10)
        
        replacements = [
            (r'Procuring Entity\s*' + nl + r'\s*Name\s*:', 'Procuring Entity Name :'),
            (r'Procuring Entity\s*' + nl + r'\s*Code\s*:', 'Procuring Entity Code :'),
            (r'Procuring Entity\s*' + nl + r'\s*District\s*:', 'Procuring Entity District :'),
            (r'Tender/Proposal\s*' + nl + r'\s*ID\s*:', 'Tender/Proposal ID :'),
            (r'Tender/Proposal\s*' + nl + r'\s*Package No\. and\s*' + nl + r'\s*Description\s*:', 'Tender/Proposal Package No. and Description :'),
            (r'Tender/Proposal\s*' + nl + r'\s*Closing\s*' + nl + r'\s*Date and Time\s*:', 'Tender/Proposal Closing Date and Time :'),
            (r'Tender/Proposal\s*' + nl + r'\s*Opening\s*' + nl + r'\s*Date and Time\s*:', 'Tender/Proposal Opening Date and Time :'),
            (r'Tender/Proposal\s*' + nl + r'\s*Publication\s*' + nl + r'\s*Date and Time\s*:', 'Tender/Proposal Publication Date and Time :'),
            (r'Scheduled\s*' + nl + r'\s*Tender/Proposal\s*' + nl + r'\s*Publication\s*' + nl + r'\s*Date and Time\s*:', 'Scheduled Tender/Proposal Publication Date and Time :'),
            (r'Tender/Proposal\s*' + nl + r'\s*Document last selling /\s*' + nl + r'\s*downloading Date and\s*' + nl + r'\s*Time\s*:', 'Tender/Proposal Document last selling / downloading Date and Time :'),
            (r'Tender/Proposal\s*' + nl + r'\s*Security Valid Up to\s*:', 'Tender/Proposal Security Valid Up to :'),
            (r'Tender/Proposal\s*' + nl + r'\s*Valid\s*' + nl + r'\s*Up to\s*:', 'Tender/Proposal Valid Up to :'),
            (r'Tender/Proposal\s*' + nl + r'\s*Document Price \(In\s*' + nl + r'\s*BDT\)\s*:', 'Tender/Proposal Document Price (In BDT) :'),
            (r'Tender/Proposal\s*' + nl + r'\s*security\s*' + nl + r'\s*\(Amount in\s*' + nl + r'\s*BDT\)\s*:', 'Tender/Proposal security (Amount in BDT) :'),
            (r'Pre - Tender/Proposal\s*' + nl + r'\s*meeting Start\s*' + nl + r'\s*Date and Time\s*:', 'Pre - Tender/Proposal meeting Start Date and Time :'),
            (r'Pre - Tender/Proposal\s*' + nl + r'\s*meeting End\s*' + nl + r'\s*Date and Time\s*:', 'Pre - Tender/Proposal meeting End Date and Time :'),
            (r'Last Date and Time for\s*' + nl + r'\s*Tender/Proposal\s*' + nl + r'\s*Security\s*' + nl + r'\s*Submission\s*:', 'Last Date and Time for Tender/Proposal Security Submission :'),
            (r'Brief Description of\s*' + nl + r'\s*Works\s*:', 'Brief Description of Works :'),
            (r'Brief Description of\s*' + nl + r'\s*Goods and Related Service\s*:', 'Brief Description of Goods and Related Service :'),
            (r'Invitation Reference\s*' + nl + r'\s*No\.\s*:', 'Invitation Reference No. :'),
            (r'Invitation for\s*' + nl + r'\s*:', 'Invitation for :'),
            (r'Name of Official\s*' + nl + r'\s*Inviting\s*' + nl + r'\s*Tender/Proposal\s*:', 'Name of Official Inviting Tender/Proposal :'),
            (r'Designation of Official Inviting\s*' + nl + r'\s*Tender/Proposal\s*:', 'Designation of Official Inviting Tender/Proposal :'),
            (r'Address of\s*' + nl + r'\s*Official Inviting\s*' + nl + r'\s*Tender/Proposal\s*:', 'Address of Official Inviting Tender/Proposal :'),
            (r'Contact details of Official Inviting\s*' + nl + r'\s*Tender/Proposal\s*:', 'Contact details of Official Inviting Tender/Proposal :'),
            (r'Phone\s*' + nl + r'\s*No\s*:', 'Phone No :'),
            (r'Pho\s*' + nl + r'\s*No\s*:', 'Phone No :'),
            (r'Fax\s*' + nl + r'\s*No\s*:', 'Fax No :'),
            (r'City\s*' + nl + r'\s*Thana\s*:', 'City Thana :'),
            (r'City\s*' + nl + r'\s*:', 'City :'),
            (r'Thana\s*' + nl + r'\s*:', 'Thana :'),
            (r'District\s*' + nl + r'\s*:', 'District :'),
            (r'Country\s*' + nl + r'\s*:', 'Country :'),
            (r'Evaluation Type\s*' + nl + r'\s*:', 'Evaluation Type :'),
            (r'Document Available\s*' + nl + r'\s*:', 'Document Available :'),
            (r'Document Fees\s*' + nl + r'\s*:', 'Document Fees :'),
            (r'Mode of Payment\s*' + nl + r'\s*:', 'Mode of Payment :'),
            (r'Eligibility of Tenderer\s*' + nl + r'\s*:', 'Eligibility of Tenderer :'),
            (r'Key Information and Funding Information\s*' + nl + r'\s*:', 'Key Information and Funding Information :'),
            (r'Budget Type\s*' + nl + r'\s*:', 'Budget Type :'),
            (r'Procurement Method\s*' + nl + r'\s*:', 'Procurement Method :'),
            (r'Source of Funds\s*' + nl + r'\s*:', 'Source of Funds :'),
            (r'Particular Information\s*' + nl + r'\s*:', 'Particular Information :'),
            (r'Project Code\s*' + nl + r'\s*:', 'Project Code :'),
            (r'Project Name\s*' + nl + r'\s*:', 'Project Name :'),
            (r'Event Type\s*' + nl + r'\s*:', 'Event Type :'),
            (r'Procurement Nature\s*' + nl + r'\s*:', 'Procurement Nature :'),
            (r'Procurement Type\s*' + nl + r'\s*:', 'Procurement Type :'),
            (r'App ID\s*' + nl + r'\s*:', 'App ID :'),
            (r'Lot\s*' + nl + r'\s*No\.\s*' + nl + r'\s*Identification of Lot\s*' + nl + r'\s*Location\s*' + nl + r'\s*Tender/Proposal\s*' + nl + r'\s*security\s*' + nl + r'\s*\(Amount in\s*' + nl + r'\s*BDT\)\s*' + nl + r'\s*Tentative\s*' + nl + r'\s*Start\s*' + nl + r'\s*Date\s*' + nl + r'\s*Tentative\s*' + nl + r'\s*Completion\s*' + nl + r'\s*Date\s*', 'Lot No. Identification of Lot Location Tender/Proposal security (Amount in BDT) Tentative Start Date Tentative Completion Date'),
        ]
        
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Fix special case: date embedded in label
        text = re.sub(
            r'Last Date and Time for Tender/Proposal Security\s+(\d{2}-[A-Za-z]{3}-\d{4}\s+\d{2}:\d{2})\s*Submission\s*:',
            r'Last Date and Time for Tender/Proposal Security Submission : \1',
            text, flags=re.IGNORECASE
        )
        
        return text

    def _extract_field(self, text: str, label: str, next_labels: List[str], default: Any = "") -> str:
        """Extract field value using regex."""
        if not next_labels:
            next_labels = [""]
        stop_pattern = '|'.join(re.escape(l) for l in next_labels if l)
        nl = chr(10)
        pattern = rf'{re.escape(label)}\s*[:.]?\s*([\s\S]+?)(?={nl}\s*(?:{stop_pattern})|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            val = match.group(1).strip()
            val = re.sub(r'[ \t]+', ' ', val)
            val = re.sub(r'[\|,\n\r]+$', '', val).strip()
            return val if val else str(default)
        return str(default)

    def _extract_tender_id(self, text: str) -> str:
        patterns = [
            r'Tender/Proposal ID\s*:\s*(\d+)',
            r'Tender/Proposal ID\s*:\s*(\d{7,})',
            r'ID\s*:\s*(\d{7,})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _safe_float(self, val: str) -> float:
        try:
            return float(val.replace(',', '').replace('BDT', '').replace('Tk.', '').strip())
        except (ValueError, AttributeError, TypeError):
            return 0.0

    def parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str or date_str.lower() in ('not applicable', 'n/a', ''):
            return None
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

    def _extract_lots_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract lot info from tab-separated text."""
        lots = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for lot data line: starts with number, has tabs, ends with dates
            if re.match(r'^\d+\s+', line) and re.search(r'\d{2}-[A-Za-z]{3}-\d{4}', line):
                parts = re.split(r'\s{2,}|\t', line)
                parts = [p.strip() for p in parts if p.strip()]
                
                if len(parts) >= 6:
                    try:
                        security = self._safe_float(parts[3])
                        lots.append({
                            'lot_no': parts[0],
                            'identification': parts[1][:200],
                            'location': parts[2],
                            'security_amount': security,
                            'start_date': parts[4] if len(parts) > 4 else '',
                            'completion_date': parts[5] if len(parts) > 5 else ''
                        })
                    except:
                        pass
        
        return lots

    def _extract_lots_from_pdf(self, text: str) -> List[Dict[str, Any]]:
        """Extract lot info from PDF format."""
        lots = []
        nl = chr(10)
        
        lot_match = re.search(
            r'Lot\s+No\.\s+Identification.*?Completion\s+Date\s*\n(.+?)(?=\n\s*#?\s*Procuring|\n\s*Procuring\s+Entity|$)',
            text, re.IGNORECASE | re.DOTALL
        )
        
        if not lot_match:
            return lots
        
        lot_text = lot_match.group(1)
        lines = [l.strip() for l in lot_text.split(nl) if l.strip()]
        
        lot_no = "1"
        security_amount = 0.0
        location = ""
        description_lines = []
        dates = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            if line_stripped.isdigit() and len(line_stripped) == 1:
                lot_no = line_stripped
                continue
            
            if re.match(r'^\d{4,6}$', line_stripped) and line_stripped not in ['1215']:
                security_amount = self._safe_float(line_stripped)
                continue
            
            if re.match(r'^\d{2}-[A-Za-z]{3}-\d{4}$', line_stripped):
                dates.append(line_stripped)
                continue
            
            if re.match(r'^\d{2}-[A-Za-z]{3}-$', line_stripped):
                if i + 1 < len(lines) and re.match(r'^\d{4}$', lines[i + 1].strip()):
                    dates.append(f"{line_stripped}{lines[i + 1].strip()}")
                continue
            
            if re.match(r'^\d{4}$', line_stripped):
                continue
            
            if not location and (',' in line_stripped or 'Institute' in line_stripped or 'Savar' in line_stripped):
                if not any(w in line_stripped.lower() for w in ['repair', 'maintenance', 'construction', 'building', 'work', 'supply', 'installation']):
                    location = line_stripped
                    continue
            
            if line_stripped and not line_stripped.isdigit():
                description_lines.append(line_stripped)
        
        description = ' '.join(description_lines)
        description = re.sub(r'\s+', ' ', description).strip()
        
        if security_amount > 0 or description:
            lots.append({
                'lot_no': lot_no,
                'identification': description[:200] if len(description) > 200 else description,
                'location': location or 'Dhaka',
                'security_amount': security_amount,
                'start_date': dates[0] if dates else "",
                'completion_date': dates[1] if len(dates) > 1 else ""
            })
        
        return lots

    def extract_text_from_pdf(self, pdf_file) -> str:
        """Extract text from uploaded PDF file."""
        if not PDF_SUPPORT:
            st.error("PyPDF2 not installed. Run: `pip install PyPDF2`")
            return ""
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception as e:
            st.error(f"Error reading PDF: {str(e)}")
            return ""

    def extract_tender_info(self, text: str) -> Dict[str, Any]:
        """Extract all tender information from text (auto-detects format)."""
        fmt = self._detect_format(text)
        
        if fmt == 'tab':
            return self._extract_from_tab(text)
        else:
            return self._extract_from_pdf(text)

    def _extract_from_tab(self, text: str) -> Dict[str, Any]:
        """Extract from tab-separated text."""
        parsed = self._parse_tab_separated(text)
        
        # Build info
        info = {
            'ministry': parsed.get('ministry', ''),
            'organization': parsed.get('organization', ''),
            'procuring_entity': parsed.get('procuring_entity', ''),
            'procuring_entity_district': parsed.get('procuring_entity_district', ''),
            'procurement_nature': parsed.get('procurement_nature', ''),
            'procurement_type': parsed.get('procurement_type', '').lower().replace(' ', '_'),
            'event_type': parsed.get('event_type', ''),
            'invitation_ref_no': parsed.get('invitation_ref_no', ''),
            'app_id': parsed.get('app_id', ''),
            'tender_id': parsed.get('tender_id', ''),
            'project_code': parsed.get('project_code', '') if parsed.get('project_code', '').lower() not in ('not applicable', 'n/a') else '',
            'project_name': parsed.get('project_name', '') if parsed.get('project_name', '').lower() not in ('not applicable', 'n/a') else '',
            'package_no': parsed.get('package_no', ''),
            'tender_title': parsed.get('tender_title', ''),
            'evaluation_type': parsed.get('evaluation_type', ''),
            'mode_of_payment': parsed.get('mode_of_payment', ''),
            'eligibility_criteria': parsed.get('eligibility_criteria', ''),
            'inviting_official_name': parsed.get('inviting_official_name', ''),
            'inviting_official_designation': parsed.get('inviting_official_designation', ''),
            'inviting_official_phone': parsed.get('inviting_official_phone', ''),
            'inviting_official_email': '',
            'inviting_official_address': parsed.get('inviting_official_address', ''),
            'inviting_official_city': parsed.get('inviting_official_city', ''),
            'inviting_official_thana': parsed.get('inviting_official_thana', ''),
            'inviting_official_district': parsed.get('inviting_official_district', ''),
            'country': parsed.get('country', 'Bangladesh'),
            'tender_security': 0.0,
            'document_fee': 0.0,
            'official_estimate': 0.0,
            'lots': []
        }
        
        # Clean
        info['procuring_entity'] = re.sub(r'\s+', ' ', info['procuring_entity']).strip()
        
        # Parse dates
        date_fields = {
            'tender_publication_date': 'tender_publication_date',
            'document_selling_end_date': 'document_selling_end_date',
            'pre_bid_meeting_start': 'pre_bid_meeting_start',
            'pre_bid_meeting_end': 'pre_bid_meeting_end',
            'submission_deadline': 'submission_deadline',
            'security_submission_deadline': 'security_submission_deadline',
            'bid_opening_date': 'bid_opening_date',
            'security_valid_upto': 'security_valid_upto',
            'tender_valid_upto': 'tender_valid_upto',
        }
        
        for key, field in date_fields.items():
            info[key] = self.parse_date(parsed.get(field, ''))
        
        # Financials
        info['document_fee'] = self._safe_float(parsed.get('document_fee', ''))
        info['tender_security'] = self._safe_float(parsed.get('tender_security', ''))
        
        # Lots
        info['lots'] = self._extract_lots_from_text(text)
        if not info['tender_security'] and info['lots']:
            info['tender_security'] = info['lots'][0].get('security_amount', 0)
        
        # District
        district_raw = info['inviting_official_district'] or info['procuring_entity_district'] or ''
        district = district_raw.split('\n')[0].split('-')[0].strip().title()
        info['district'] = district
        info['thana'] = info.get('inviting_official_thana', '').split('\n')[0].strip().title()
        info['division'] = self.division_map.get(district, '')
        
        return info

    def _extract_from_pdf(self, text: str) -> Dict[str, Any]:
        """Extract from PDF format."""
        text = self._join_split_labels(text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        info = {
            'ministry': self._extract_field(text, 'Ministry', ['Division', 'Organization']),
            'organization': self._extract_field(text, 'Organization', ['Procuring Entity Name']),
            'procuring_entity': self._extract_field(text, 'Procuring Entity Name', ['Procuring Entity Code', 'Procurement Nature']),
            'procuring_entity_district': self._extract_field(text, 'Procuring Entity District', ['Procurement Nature']),
            'procurement_nature': self._extract_field(text, 'Procurement Nature', ['Procurement Type']),
            'procurement_type': self._extract_field(text, 'Procurement Type', ['Event Type']).lower().replace(' ', '_'),
            'event_type': self._extract_field(text, 'Event Type', ['Invitation Reference']),
            'invitation_ref_no': self._extract_field(text, 'Invitation Reference No.', ['App ID']),
            'app_id': self._extract_field(text, 'App ID', ['Tender/Proposal ID']),
            'tender_id': self._extract_tender_id(text) or self._extract_field(text, 'Tender/Proposal ID', ['Re-Tendered ID', 'Key Information']),
            'project_code': self._extract_field(text, 'Project Code', ['Project Name']),
            'project_name': self._extract_field(text, 'Project Name', ['Tender/Proposal Package']),
            'package_no': self._extract_field(text, 'Tender/Proposal Package No. and Description', ['Brief Description', 'Category']),
            'tender_title': self._extract_field(text, 'Brief Description of Works', ['Category', 'Evaluation']) or self._extract_field(text, 'Brief Description of Goods and Related Service', ['Category', 'Evaluation']),
            'evaluation_type': self._extract_field(text, 'Evaluation Type', ['Document Available']),
            'mode_of_payment': self._extract_field(text, 'Mode of Payment', ['Tender/Proposal Security Valid']),
            'eligibility_criteria': self._extract_field(text, 'Eligibility of Tenderer', ['Brief Description']),
            'inviting_official_name': self._extract_field(text, 'Name of Official Inviting Tender/Proposal', ['Designation']),
            'inviting_official_designation': self._extract_field(text, 'Designation of Official Inviting Tender/Proposal', ['Address']),
            'inviting_official_phone': self._extract_field(text, 'Phone No', ['Fax No', 'Address', 'Thana', 'City']),
            'inviting_official_email': '',
            'inviting_official_address': self._extract_multiline_field(text, 'Address of Official Inviting Tender/Proposal', ['Contact details', 'The procuring entity']),
            'inviting_official_city': self._extract_field(text, 'City', ['Thana']),
            'inviting_official_thana': self._extract_field(text, 'Thana', ['District']),
            'inviting_official_district': self._extract_field(text, 'District', ['Country']),
            'country': 'Bangladesh',
            'tender_security': 0.0,
            'document_fee': 0.0,
            'official_estimate': 0.0,
            'lots': []
        }
        
        info['procuring_entity'] = re.sub(r'\s+', ' ', info['procuring_entity']).strip()
        
        # Dates
        date_patterns = {
            'tender_publication_date': [r'Scheduled Tender/Proposal Publication Date and Time\s*:\s*(.+?)(?=\s*(?:Tender/Proposal Document last|Pre - Tender))'],
            'document_selling_end_date': [r'Tender/Proposal Document last selling / downloading Date and Time\s*:\s*(.+?)(?=\s*(?:Pre - Tender))'],
            'pre_bid_meeting_start': [r'Pre - Tender/Proposal meeting Start Date and Time\s*:\s*(.+?)(?=\s*(?:Pre - Tender/Proposal meeting End))'],
            'pre_bid_meeting_end': [r'Pre - Tender/Proposal meeting End Date and Time\s*:\s*(.+?)(?=\s*(?:Tender/Proposal Closing))'],
            'submission_deadline': [r'Tender/Proposal Closing Date and Time\s*:\s*(.+?)(?=\s*(?:Tender/Proposal Opening))', r'Closing Date and Time\s*:\s*(.+?)(?=\s*(?:Tender/Proposal|$))'],
            'security_submission_deadline': [r'Last Date and Time for Tender/Proposal Security Submission\s*:\s*(.+?)(?=\s*(?:Information for Tenderer|Eligibility))'],
            'bid_opening_date': [r'Tender/Proposal Opening Date and Time\s*:\s*(.+?)(?=\s*(?:Last Date and Time|Information for Tenderer))', r'Opening Date and Time\s*:\s*(.+?)(?=\s*(?:Last Date|$))'],
            'security_valid_upto': [r'Tender/Proposal Security Valid Up to\s*:\s*(.+?)(?=\s*(?:Tender/Proposal Valid|Mode of Payment))'],
            'tender_valid_upto': [r'Tender/Proposal Valid\s*\n?\s*Up to\s*:\s*\n?\s*(\d{2}-[A-Za-z]{3}-\d{4})', r'Tender/Proposal Valid Up to\s*:\s*(.+?)(?=\s*(?:Information for Tenderer|Eligibility|Note))'],
        }
        
        for key, patterns in date_patterns.items():
            val = ""
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    val = match.group(1).strip()
                    break
            info[key] = self.parse_date(val)
        
        # Financials
        security_patterns = [
            r'Tender/Proposal\s*security\s*\(Amount in BDT\)\s*:\s*([\d,]+)',
            r'security\s*\(Amount in\s*BDT\)\s*[:\)]?\s*\n?\s*(\d{4,})',
        ]
        security_val = ""
        for pattern in security_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                security_val = match.group(1).strip()
                break
        
        if not security_val:
            security_val = self._extract_lot_security_from_pdf(text)
        
        info['tender_security'] = self._safe_float(security_val)
        
        info['document_fee'] = self._safe_float(
            re.search(r'Tender/Proposal Document Price\s*\(In BDT\)\s*:\s*([\d,]+)', text, re.IGNORECASE).group(1).strip() if re.search(r'Tender/Proposal Document Price\s*\(In BDT\)\s*:\s*([\d,]+)', text, re.IGNORECASE) else ''
        )
        
        info['lots'] = self._extract_lots_from_pdf(text)
        
        if info['tender_security'] <= 0 and info['lots']:
            info['tender_security'] = info['lots'][0].get('security_amount', 0)
        
        district_raw = info['inviting_official_district'] or info['procuring_entity_district'] or ''
        district_clean = district_raw.split('\n')[0].split('-')[0].strip()
        district = district_clean.title() if district_clean else ''
        info['district'] = district
        info['thana'] = info.get('inviting_official_thana', '').split('\n')[0].strip().title()
        info['division'] = self.division_map.get(district, '')
        
        return info

    def _extract_lot_security_from_pdf(self, text: str) -> str:
        lot_section = re.search(
            r'Lot\s+No\.\s+Identification.*?Completion\s+Date\s*\n(.+?)(?=\n\s*#?\s*Procuring|\n\s*Procuring\s+Entity|$)',
            text, re.IGNORECASE | re.DOTALL
        )
        if lot_section:
            lot_text = lot_section.group(1)
            amounts = re.findall(r'\b(\d{4,6})\b', lot_text)
            if amounts:
                return amounts[0]
        return ""

    def _extract_multiline_field(self, text: str, label: str, stop_labels: List[str], default: str = "") -> str:
        stop_pattern = '|'.join(re.escape(l) for l in stop_labels if l)
        nl = chr(10)
        pattern = rf'{re.escape(label)}\s*[:.]?\s*([\s\S]+?)(?={nl}\s*(?:{stop_pattern})|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            val = match.group(1).strip()
            val = re.sub(r'[ \t]+', ' ', val)
            val = re.sub(r'\s*[:.]\s*', ': ', val)
            val = re.sub(r'^Address\s*:\s*', '', val)
            return val if val else default
        return default

    def fill_tender_form(self, info: Dict[str, Any]) -> Dict[str, Any]:
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


def parse_tender_text(text: str) -> Optional[Dict[str, Any]]:
    """Parse tender notice text pasted into a text box."""
    if not text or not text.strip():
        return None
    
    parser = TenderPDFParser()
    info = parser.extract_tender_info(text)
    return parser.fill_tender_form(info)
def parse_tender_url(url: str) -> Optional[Dict[str, Any]]:
    """Bulletproof parser: Fetches e-GP URL, fixes HTML artifacts, and extracts all data."""
    if not url or not url.strip():
        return None
        
    try:
        print(f"\n🔍🔍🔍 [DEBUG] STARTING URL FETCH: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        print(f"✅ [DEBUG] Successfully fetched URL. Status: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Replace <br> tags with spaces
        for br in soup.find_all('br'):
            br.replace_with(' ')
            
        text_parts = []
        rows = soup.find_all('tr')
        
        # 2. Pair cells and FIX THE LEADING COLON BUG
        for row in rows:
            cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
            if not cells:
                continue
                
            for i in range(0, len(cells), 2):
                key = cells[i].replace('\n', ' ').replace('\r', '').strip()
                val = cells[i+1].replace('\n', ' ').replace('\r', '').strip() if i + 1 < len(cells) else ''
                
                # FIX: Remove trailing colon from key and leading colon from value
                if key.endswith(':'):
                    key = key[:-1].strip()
                if val.startswith(':'):
                    val = val[1:].strip()
                
                if key:
                    text_parts.append(f"{key} : {val}")
                        
        text = '\n'.join(text_parts)
        
        # 3. Parse the structured text
        parser = TenderDataParser()
        parsed_data = parser._parse_structured_text(text)
        
        # 4. FALLBACK: Extract dates using regex on the full HTML text if missing
        # This fixes the issue where e-GP splits date labels across multiple cells
        html_text = soup.get_text()
        date_patterns = {
            'tender_publication_date': r'Scheduled\s+Tender/Proposal\s+Publication\s+Date\s+and\s+Time\s*:\s*([0-9]{2}-[A-Za-z]{3}-[0-9]{4}\s+[0-9]{2}:[0-9]{2})',
            'document_selling_end_date': r'Tender/Proposal\s+Document\s+last\s+selling\s*/\s*downloading\s+Date\s+and\s+Time\s*:\s*([0-9]{2}-[A-Za-z]{3}-[0-9]{4}\s+[0-9]{2}:[0-9]{2})',
            'submission_deadline': r'Tender/Proposal\s+Closing\s+Date\s+and\s+Time\s*:\s*([0-9]{2}-[A-Za-z]{3}-[0-9]{4}\s+[0-9]{2}:[0-9]{2})',
            'bid_opening_date': r'Tender/Proposal\s+Opening\s+Date\s+and\s+Time\s*:\s*([0-9]{2}-[A-Za-z]{3}-[0-9]{4}\s+[0-9]{2}:[0-9]{2})',
            'security_submission_deadline': r'Last\s+Date\s+and\s+Time\s+for\s+Tender/Proposal\s+Security\s+Submission\s*:\s*([0-9]{2}-[A-Za-z]{3}-[0-9]{4}\s+[0-9]{2}:[0-9]{2})',
            'pre_bid_meeting_start': r'Pre\s*-\s*Tender/Proposal\s+meeting\s+Start\s+Date\s+and\s+Time\s*:\s*([0-9]{2}-[A-Za-z]{3}-[0-9]{4}\s+[0-9]{2}:[0-9]{2})',
            'pre_bid_meeting_end': r'Pre\s*-\s*Tender/Proposal\s+meeting\s+End\s+Date\s+and\s+Time\s*:\s*([0-9]{2}-[A-Za-z]{3}-[0-9]{4}\s+[0-9]{2}:[0-9]{2})',
        }
        
        for key, pattern in date_patterns.items():
            if not parsed_data.get(key): # Only if not already found
                match = re.search(pattern, html_text, re.IGNORECASE)
                if match:
                    parsed_data[key] = match.group(1).strip()
        
        # 5. Extract lots
        lots = []
        for table in soup.find_all('table'):
            rows_in_table = table.find_all('tr')
            if not rows_in_table:
                continue
            header_text = ' '.join([th.get_text(strip=True).lower() for th in rows_in_table[0].find_all(['th', 'td'])])
            if 'lot no' in header_text:
                for row in rows_in_table[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                    if len(cells) >= 6:
                        try:
                            security = parser._safe_float(cells[3])
                            lots.append({
                                'lot_no': cells[0],
                                'identification': cells[1][:200],
                                'location': cells[2],
                                'security_amount': security,
                                'start_date': cells[4],
                                'completion_date': cells[5]
                            })
                        except Exception:
                            pass
                break
        
        # 6. Build final info
        info = parser._extract_from_structured_text(parsed_data, lots)
        final_form = parser.fill_tender_form(info)
        
        print(f"✅ [DEBUG] Final form has {len([v for v in final_form.values() if v])} non-empty fields.")
        return final_form
        
    except Exception as e:
        print(f"❌ [DEBUG] CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None