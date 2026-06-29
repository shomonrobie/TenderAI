"""
Tender Data Parser - Production-Ready v7.3 (selectolax)
Full diagnostic version.
"""
import re
import requests
import traceback
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import selectolax

# Try selectolax
try:
    from selectolax.parser import HTMLParser
    USE_SELECTOLAX = True
    
except ImportError:
    from bs4 import BeautifulSoup
    USE_SELECTOLAX = False

class TenderDataParser:
    def __init__(self):
        print("✅ TenderDataParser class initialized", file=sys.stderr)
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

        self.FIELD_MAP = {
            'ministry': 'ministry', 'division': 'division', 'organization': 'organization',
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
            'procurement method': 'procurement_method',
            'budget type': 'budget_type',
            'source of funds': 'source_of_funds',
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
            'name of official inviting tender/proposal': 'inviting_official_name',
            'designation of official inviting tender/proposal': 'inviting_official_designation',
            'address of official inviting tender/proposal': 'inviting_official_address',
            'phone no': 'inviting_official_phone',
            'email': 'inviting_official_email',
            'address': 'inviting_official_address',
            'city': 'inviting_official_city',
            'thana': 'inviting_official_thana',
            'district': 'inviting_official_district',
            'country': 'country',
            'note': 'notes',
        }

    def _clean_text(self, text: str) -> str:
        if not text: return ''
        text = str(text).strip()
        text = re.sub(r'^[:\-\s•]+', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
   
   
    def _parse_structured_text(self, text: str) -> Dict[str, str]:
        result = {}
        for line in text.split('\n'):
            if ':' not in line:
                continue
            label, value = line.split(':', 1)
            label = self._clean_text(label)
            value = self._clean_text(value)

            normalized = label.lower().strip()
            normalized = normalized.rstrip('.').rstrip(':').strip()
            normalized = ' '.join(normalized.split())

            # Generic regex fixes: insert spaces before glued tokens
            normalized = re.sub(r'([a-z])date', r'\1 date', normalized)
            normalized = re.sub(r'([a-z])time', r'\1 time', normalized)
            normalized = re.sub(r'([a-z])submission', r'\1 submission', normalized)
            normalized = re.sub(r'([a-z])deadline', r'\1 deadline', normalized)

            # Special case for /downloading
            normalized = normalized.replace('/downloading', '/ downloading')

            if 'date' in normalized or 'time' in normalized:
                print(f"📅 Date label found: '{normalized}' -> '{value}'", file=sys.stderr)

            if normalized in self.FIELD_MAP:
                result[self.FIELD_MAP[normalized]] = value
            elif 'address' in normalized:
                result['inviting_official_address'] = value
            elif 'city' in normalized:
                result['inviting_official_city'] = value
            elif 'thana' in normalized:
                result['inviting_official_thana'] = value
            elif 'district' in normalized:
                result['inviting_official_district'] = value
            elif 'email' in normalized:
                result['inviting_official_email'] = value
            else:
                # Debug unmatched labels
                print(f"⚠️ Unmatched label: '{normalized}'", file=sys.stderr)

        return result




    def _parse_structured_text_bak(self, text: str) -> Dict[str, str]:
        result = {}
        for line in text.split('\n'):
            line = line.strip()
            if ':' not in line:
                continue
            parts = line.split(':', 1)
            label = self._clean_text(parts[0])
            value = self._clean_text(parts[1]) if len(parts) > 1 else ''
            
            # Normalize the label - remove extra spaces, convert to lowercase
            normalized = label.lower().strip()
            # Remove trailing punctuation
            normalized = normalized.rstrip('.').rstrip(':').strip()
            # Remove extra spaces between words
            normalized = ' '.join(normalized.split())
            
            # Debug: print date-related labels
            if 'date' in normalized or 'time' in normalized:
                print(f"📅 Date label found: '{normalized}' -> '{value}'", file=sys.stderr)
            
            # Check for exact matches in FIELD_MAP
            if normalized in self.FIELD_MAP:
                result[self.FIELD_MAP[normalized]] = value
            elif 'address' in normalized:
                result['inviting_official_address'] = value
            elif 'city' in normalized:
                result['inviting_official_city'] = value
            elif 'thana' in normalized:
                result['inviting_official_thana'] = value
            elif 'district' in normalized:
                result['inviting_official_district'] = value
            elif 'email' in normalized:
                result['inviting_official_email'] = value
            # Add flexible date matching
            elif 'scheduled tender/proposal publication date and time' in normalized:
                result['tender_publication_date'] = value
            elif 'tender/proposal document last selling / downloading date and time' in normalized:
                result['document_selling_end_date'] = value
            elif 'pre - tender/proposal meeting start date and time' in normalized:
                result['pre_bid_meeting_start'] = value
            elif 'pre - tender/proposal meeting end date and time' in normalized:
                result['pre_bid_meeting_end'] = value
            elif 'tender/proposal closing date and time' in normalized:
                result['submission_deadline'] = value
            elif 'tender/proposal opening date and time' in normalized:
                result['bid_opening_date'] = value
            elif 'last date and time for tender/proposal security submission' in normalized:
                result['security_submission_deadline'] = value
            elif 'tender/proposal security valid up to' in normalized:
                result['security_valid_upto'] = value
            elif 'tender/proposal valid up to' in normalized:
                result['tender_valid_upto'] = value

        return result

    def _parse_structured_tex_bakt(self, text: str) -> Dict[str, str]:
        result = {}
        for line in text.split('\n'):
            line = line.strip()
            if ':' not in line:
                continue
            parts = line.split(':', 1)
            label = self._clean_text(parts[0])
            value = self._clean_text(parts[1]) if len(parts) > 1 else ''
            
            normalized = label.lower().rstrip('.').rstrip(':').strip()
            
            if normalized in self.FIELD_MAP:
                result[self.FIELD_MAP[normalized]] = value
            elif 'address' in normalized:
                result['inviting_official_address'] = value
            elif 'city' in normalized:
                result['inviting_official_city'] = value
            elif 'thana' in normalized:
                result['inviting_official_thana'] = value
            elif 'district' in normalized:
                result['inviting_official_district'] = value
            elif 'email' in normalized:
                result['inviting_official_email'] = value

        return result

    def parse_date(self, date_str: str) -> Optional[str]:
        if not date_str or date_str.lower() in ('not applicable', 'n/a', ''):
            return None
        date_str = re.sub(r'\s+', ' ', date_str).strip()
        formats = [
            '%d-%b-%Y %H:%M', '%d-%b-%Y', '%d-%B-%Y %H:%M', '%d-%B-%Y',
            '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M', '%d/%m/%Y'
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.isoformat()  # Convert to ISO string
            except ValueError:
                continue
        return None

    def parse_date_bak(self, date_str: str) -> Optional[datetime]:
        if not date_str or date_str.lower() in ('not applicable', 'n/a', ''):
            return None
        date_str = re.sub(r'\s+', ' ', date_str).strip()
        formats = ['%d-%b-%Y %H:%M', '%d-%b-%Y', '%d-%B-%Y %H:%M', '%d-%B-%Y',
                   '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M', '%d/%m/%Y']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _safe_float(self, val: str) -> float:
        try:
            return float(str(val).replace(',', '').replace('BDT', '').replace('Tk.', '').strip())
        except:
            return 0.0

    def _extract_lots_from_html(self, tree) -> List[Dict[str, Any]]:
        lots = []
        try:
            if USE_SELECTOLAX:
                for table in tree.css('table'):
                    first_row = table.css_first('tr')
                    if first_row and 'lot no' in first_row.text(strip=True).lower():
                        for row in table.css('tr')[1:]:
                            cells = [cell.text(strip=True) for cell in row.css('td, th')]
                            if len(cells) >= 6:
                                try:
                                    security = self._safe_float(cells[3])
                                    lots.append({
                                        'lot_no': cells[0],
                                        'identification': cells[1][:200],
                                        'location': cells[2],
                                        'security_amount': security,
                                        'start_date': cells[4],
                                        'completion_date': cells[5]
                                    })
                                except:
                                    pass
        except Exception as e:
            print(f"Lot extraction error: {e}", file=sys.stderr)
        return lots

    def _extract_from_structured_text(self, parsed: Dict[str, str], lots: List) -> Dict[str, Any]:
        info = {
            'ministry': self._clean_text(parsed.get('ministry', '')),
            'organization': self._clean_text(parsed.get('organization', '')),
            'procuring_entity': self._clean_text(parsed.get('procuring_entity', '')),
            'procuring_entity_code': self._clean_text(parsed.get('procuring_entity_code', '')),
            'procuring_entity_district': self._clean_text(parsed.get('procuring_entity_district', '')),
            'procurement_nature': self._clean_text(parsed.get('procurement_nature', '')),
            'procurement_type': self._clean_text(parsed.get('procurement_type', '')).lower().replace(' ', '_'),
            'event_type': self._clean_text(parsed.get('event_type', '')),
            'invitation_ref_no': self._clean_text(parsed.get('invitation_ref_no', '')),
            'app_id': self._clean_text(parsed.get('app_id', '')),
            'tender_id': self._clean_text(parsed.get('tender_id', '')),
            'project_code': self._clean_text(parsed.get('project_code', '')),
            'project_name': self._clean_text(parsed.get('project_name', '')),
            'package_no': self._clean_text(parsed.get('package_no', '')),
            'tender_title': self._clean_text(parsed.get('tender_title', '')),
            'evaluation_type': self._clean_text(parsed.get('evaluation_type', '')),
            'mode_of_payment': self._clean_text(parsed.get('mode_of_payment', '')),
            'eligibility_criteria': self._clean_text(parsed.get('eligibility_criteria', '')),
            'inviting_official_name': self._clean_text(parsed.get('inviting_official_name', '')),
            'inviting_official_designation': self._clean_text(parsed.get('inviting_official_designation', '')),
            'inviting_official_phone': self._clean_text(parsed.get('inviting_official_phone', '')),
            'inviting_official_address': self._clean_text(parsed.get('inviting_official_address', '')),
            'inviting_official_city': self._clean_text(parsed.get('inviting_official_city', '')),
            'inviting_official_thana': self._clean_text(parsed.get('inviting_official_thana', '')),
            'inviting_official_district': self._clean_text(parsed.get('inviting_official_district', '')),
            'inviting_official_email': self._clean_text(parsed.get('inviting_official_email', '')), 
            'country': self._clean_text(parsed.get('country', 'Bangladesh')),
            'budget_type': self._clean_text(parsed.get('budget_type', '')),
            'source_of_funds': self._clean_text(parsed.get('source_of_funds', '')),
            'category': self._clean_text(parsed.get('category', '')),
            'tender_security': 0.0,
            'document_fee': 0.0,
            'official_estimate': 0.0,
            'lots': lots
        }

        # Clean project fields
        for f in ['project_code', 'project_name']:
            if info[f].lower() in ('not applicable', 'n/a', ''):
                info[f] = ''

        # Dates
        date_fields = ['tender_publication_date','document_selling_end_date','pre_bid_meeting_start',
                       'pre_bid_meeting_end','submission_deadline','security_submission_deadline',
                       'bid_opening_date','security_valid_upto','tender_valid_upto']
        for field in date_fields:
            info[field] = self.parse_date(parsed.get(field, ''))

        info['document_fee'] = self._safe_float(parsed.get('document_fee', ''))
        info['tender_security'] = self._safe_float(parsed.get('tender_security', ''))
        if info['tender_security'] <= 0 and lots:
            info['tender_security'] = lots[0].get('security_amount', 0.0)

        # District logic
        district_raw = info['inviting_official_district'] or info['procuring_entity_district'] or ''
        district = self._clean_text(district_raw.split('\n')[0].split('-')[0])
        info['district'] = district.title()
        info['thana'] = self._clean_text(info.get('inviting_official_thana', '')).title()
        info['division'] = self.division_map.get(district, '')

        return info

    def fill_tender_form(self, info: Dict[str, Any]) -> Dict[str, Any]:
        default_deadline = datetime.now() + timedelta(days=14)
        return {
            'tender_id': self._clean_text(info.get('tender_id', '')),
            'app_id': self._clean_text(info.get('app_id', '')),
            'tender_title': self._clean_text(info.get('tender_title', '')),
            'procuring_entity': self._clean_text(info.get('procuring_entity', '')),
            'division': info.get('division', ''),
            'district': info.get('district', ''),
            'thana': info.get('thana', ''),
            'country': info.get('country', 'Bangladesh'),
            'procurement_type': info.get('procurement_type', 'works'),
            'official_estimate': info.get('official_estimate', 0),
            'submission_deadline': info.get('submission_deadline') or default_deadline,
            'tender_security': info.get('tender_security', 0),
            'document_fee': info.get('document_fee', 0),
            'evaluation_type': self._clean_text(info.get('evaluation_type', 'Lot wise')),
            'eligibility_criteria': self._clean_text(info.get('eligibility_criteria', 'As Per Tender Documents')),
            'mode_of_payment': self._clean_text(info.get('mode_of_payment', 'Payment through Bank')),
            'invitation_ref_no': self._clean_text(info.get('invitation_ref_no', '')),
            'project_code': self._clean_text(info.get('project_code', '')),
            'project_name': self._clean_text(info.get('project_name', '')),
            'package_no': self._clean_text(info.get('package_no', '')),
            'lots': info.get('lots', []),
            'notes': f"Auto-extracted on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            # Add other fields as needed from previous versions
            'procuring_entity_code': self._clean_text(info.get('procuring_entity_code', '')),
            'event_type': self._clean_text(info.get('event_type', '')),
            'budget_type': self._clean_text(info.get('budget_type', '')),
            'source_of_funds': self._clean_text(info.get('source_of_funds', '')),
            'category': self._clean_text(info.get('category', '')),
            'procurement_nature': self._clean_text(info.get('procurement_nature', '')),
            'inviting_official_address': info.get('inviting_official_address', ''),
            'tender_publication_date': info.get('tender_publication_date'),
            'document_selling_end_date': info.get('document_selling_end_date'),
            'pre_bid_meeting_start': info.get('pre_bid_meeting_start'),
            'pre_bid_meeting_end': info.get('pre_bid_meeting_end'),
            'bid_opening_date': info.get('bid_opening_date'),
            'security_submission_deadline': info.get('security_submission_deadline'),
        }
        


def parse_tender_url(url: str) -> Optional[Dict[str, Any]]:
    """Full diagnostic parse_tender_url"""
    print(f"\n🔍🔍🔍 [DEBUG] parse_tender_url called with URL: {url}", file=sys.stderr)
    try:
        if not url or not url.strip():
            print("❌ Empty URL", file=sys.stderr)
            return None

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        print(f"✅ HTTP Success - {len(response.text)} bytes received", file=sys.stderr)

        if USE_SELECTOLAX:
            tree = HTMLParser(response.text)
            print("✅ selectolax HTMLParser created", file=sys.stderr)
        else:
            tree = BeautifulSoup(response.text, 'html.parser')
            print("✅ BeautifulSoup fallback used", file=sys.stderr)

        # Extract text
        text_parts = []
        rows = tree.css('tr') if USE_SELECTOLAX else tree.find_all('tr')
        print(f"📊 Found {len(rows)} <tr> rows", file=sys.stderr)

        for row in rows:
            cells = [cell.text(strip=True) for cell in (row.css('td, th') if USE_SELECTOLAX else row.find_all(['td','th']))]
            for i in range(0, len(cells), 2):
                key = cells[i]
                val = cells[i+1] if i+1 < len(cells) else ''
                if key:
                    val = re.sub(r'^[:\-\s]+', '', val).strip()
                    text_parts.append(f"{key} : {val}")

        print(f"📝 Generated {len(text_parts)} key-value pairs", file=sys.stderr)

        parser = TenderDataParser()
        parsed_data = parser._parse_structured_text('\n'.join(text_parts))
        print(f"🗝️ Matched {len(parsed_data)} fields", file=sys.stderr)

        lots = parser._extract_lots_from_html(tree)
        print(f"📦 Extracted {len(lots)} lots", file=sys.stderr)

        info = parser._extract_from_structured_text(parsed_data, lots)
        final_form = parser.fill_tender_form(info)
        # Debug: print all extracted fields
        print("\n🔎 Extracted Tender Data:", file=sys.stderr)
        for k, v in final_form.items():
            print(f"   {k}: {v}", file=sys.stderr)
        print("✅ Parser completed successfully!", file=sys.stderr)
        return final_form

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {type(e).__name__} - {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None