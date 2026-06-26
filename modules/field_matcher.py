# modules/field_matcher.py
"""
AI-Powered Field Matcher for Form Auto-Fill
Supports English, Bangla, and misspelled field labels
"""

import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from difflib import SequenceMatcher
import unicodedata

logger = logging.getLogger(__name__)

class FieldMatcher:
    """
    Intelligent field matcher that can identify form fields and match them
    to company data sources, even with misspelled or Bangla labels.
    """
    
    def __init__(self):
        # Mapping of field patterns to data sources
        self.field_patterns = self._initialize_patterns()
        
        # Bangla to English mapping
        self.bangla_map = self._initialize_bangla_map()
        
        # Common misspellings and variations
        self.misspellings = self._initialize_misspellings()
        
    def _initialize_patterns(self) -> Dict:
        """Initialize field pattern mappings to data sources"""
        return {
            # Company Information
            'company_name': {
                'patterns': [
                    r'company\s*name', r'firm\s*name', r'name\s*of\s*(?:company|firm)',
                    r'নাম', r'প্রতিষ্ঠানের\s*নাম', r'কোম্পানির\s*নাম'
                ],
                'source': 'company_profile',
                'field': 'legal_name',
                'confidence': 0.95
            },
            'trade_license': {
                'patterns': [
                    r'trade\s*license', r'trade\s*licence', r'business\s*license',
                    r'ট্রেড\s*লাইসেন্স', r'ব্যবসায়িক\s*লাইসেন্স'
                ],
                'source': 'trade_license',
                'field': 'license_number',
                'confidence': 0.90
            },
            'tin_number': {
                'patterns': [
                    r'tin\s*(?:number|no)', r'tax\s*identification\s*number',
                    r'টিআইএন', r'ট্যাক্স\s*আইডি'
                ],
                'source': 'tin_certificate',
                'field': 'tin_number',
                'confidence': 0.95
            },
            'vat_number': {
                'patterns': [
                    r'vat\s*(?:number|no|registration)', r'value\s*added\s*tax',
                    r'ভ্যাট', r'ভ্যাট\s*নম্বর'
                ],
                'source': 'vat_registration',
                'field': 'vat_number',
                'confidence': 0.95
            },
            'bin_number': {
                'patterns': [
                    r'bin\s*(?:number|no)', r'business\s*identification\s*number',
                    r'বিআইএন'
                ],
                'source': 'tin_certificate',
                'field': 'bin_number',
                'confidence': 0.90
            },
            
            # Personnel Information
            'name': {
                'patterns': [
                    r'name\s*of\s*(?:applicant|bidder|contractor)', r'full\s*name',
                    r'নাম', r'পূর্ণ\s*নাম', r'আবেদনকারীর\s*নাম'
                ],
                'source': 'personnel',
                'field': 'full_name',
                'confidence': 0.85
            },
            'designation': {
                'patterns': [
                    r'designation', r'position', r'পদবি', r'পদ'
                ],
                'source': 'personnel',
                'field': 'designation',
                'confidence': 0.90
            },
            'nid': {
                'patterns': [
                    r'nid\s*(?:number|no)', r'national\s*id', r'জাতীয়\s*পরিচয়পত্র',
                    r'এনআইডি'
                ],
                'source': 'personnel',
                'field': 'nid_number',
                'confidence': 0.95
            },
            'mobile': {
                'patterns': [
                    r'mobile\s*(?:number|no)', r'phone\s*(?:number|no)',
                    r'মোবাইল', r'ফোন', r'যোগাযোগ'
                ],
                'source': 'personnel',
                'field': 'personal_phone',
                'confidence': 0.85
            },
            'email': {
                'patterns': [
                    r'email', r'e-mail', r'ইমেইল'
                ],
                'source': 'personnel',
                'field': 'personal_email',
                'confidence': 0.95
            },
            
            # Experience Information
            'project_name': {
                'patterns': [
                    r'project\s*name', r'name\s*of\s*project', r'প্রকল্পের\s*নাম',
                    r'work\s*description', r'nature\s*of\s*work'
                ],
                'source': 'experience',
                'field': 'project_name',
                'confidence': 0.85
            },
            'client_name': {
                'patterns': [
                    r'client\s*name', r'employer', r'procuring\s*entity',
                    r'গ্রাহকের\s*নাম', r'ক্লায়েন্ট'
                ],
                'source': 'experience',
                'field': 'client_name',
                'confidence': 0.90
            },
            'contract_value': {
                'patterns': [
                    r'contract\s*value', r'tender\s*price', r'bid\s*amount',
                    r'contract\s*price', r'চুক্তির\s*মূল্য', r'দরপত্রের\s*মূল্য'
                ],
                'source': 'experience',
                'field': 'contract_value',
                'confidence': 0.90
            },
            'completion_date': {
                'patterns': [
                    r'completion\s*date', r'date\s*of\s*completion',
                    r'substantial\s*completion', r'সমাপ্তির\s*তারিখ'
                ],
                'source': 'experience',
                'field': 'completion_date',
                'confidence': 0.90
            },
            
            # Equipment Information
            'equipment_name': {
                'patterns': [
                    r'equipment\s*name', r'machinery\s*name', r'যন্ত্রপাতির\s*নাম'
                ],
                'source': 'equipment',
                'field': 'equipment_name',
                'confidence': 0.85
            },
            'equipment_type': {
                'patterns': [
                    r'equipment\s*type', r'type\s*of\s*machinery', r'যন্ত্রের\s*ধরন'
                ],
                'source': 'equipment',
                'field': 'equipment_type',
                'confidence': 0.90
            },
            'capacity': {
                'patterns': [
                    r'capacity', r'রেটিং', r'ক্ষমতা'
                ],
                'source': 'equipment',
                'field': 'capacity',
                'confidence': 0.85
            },
            
            # Financial Information
            'annual_turnover': {
                'patterns': [
                    r'annual\s*turnover', r'yearly\s*turnover', r'বার্ষিক\s*টার্নওভার'
                ],
                'source': 'financial',
                'field': 'annual_turnover',
                'confidence': 0.95
            },
            'net_worth': {
                'patterns': [
                    r'net\s*worth', r'নেট\s*ওয়ার্থ', r'মোট\s*সম্পত্তি'
                ],
                'source': 'financial',
                'field': 'net_worth',
                'confidence': 0.90
            },
            'working_capital': {
                'patterns': [
                    r'working\s*capital', r'ওয়ার্কিং\s*ক্যাপিটাল', r'চলতি\s*পুঁজি'
                ],
                'source': 'financial',
                'field': 'working_capital',
                'confidence': 0.90
            },
            'credit_limit': {
                'patterns': [
                    r'credit\s*limit', r'bank\s*guarantee\s*limit',
                    r'ক্রেডিট\s*লিমিট', r'ব্যাংক\s*গ্যারান্টি\s*লিমিট'
                ],
                'source': 'financial',
                'field': 'credit_limit',
                'confidence': 0.90
            },
            
            # Certificate Information
            'certificate_name': {
                'patterns': [
                    r'certificate\s*name', r'name\s*of\s*certificate',
                    r'সনদপত্রের\s*নাম'
                ],
                'source': 'certificate',
                'field': 'certificate_name',
                'confidence': 0.85
            },
            'issuing_body': {
                'patterns': [
                    r'issuing\s*body', r'issuing\s*authority', r'প্রদানকারী\s*সংস্থা'
                ],
                'source': 'certificate',
                'field': 'issuing_body',
                'confidence': 0.90
            },
            'expiry_date': {
                'patterns': [
                    r'expiry\s*date', r'valid\s*until', r'মেয়াদ\s*উত্তীর্ণের\s*তারিখ'
                ],
                'source': 'certificate',
                'field': 'expiry_date',
                'confidence': 0.90
            }
        }
    
    def _initialize_bangla_map(self) -> Dict:
        """Initialize Bangla to English character mapping"""
        return {
            'অ': 'o', 'আ': 'a', 'ই': 'i', 'ঈ': 'ee', 'উ': 'u', 'ঊ': 'oo',
            'ঋ': 'ri', 'এ': 'e', 'ঐ': 'oi', 'ও': 'o', 'ঔ': 'ou',
            'ক': 'k', 'খ': 'kh', 'গ': 'g', 'ঘ': 'gh', 'ঙ': 'ng',
            'চ': 'ch', 'ছ': 'chh', 'জ': 'j', 'ঝ': 'jh', 'ঞ': 'ny',
            'ট': 't', 'ঠ': 'th', 'ড': 'd', 'ঢ': 'dh', 'ণ': 'n',
            'ত': 't', 'থ': 'th', 'দ': 'd', 'ধ': 'dh', 'ন': 'n',
            'প': 'p', 'ফ': 'ph', 'ব': 'b', 'ভ': 'bh', 'ম': 'm',
            'য': 'j', 'র': 'r', 'ল': 'l', 'শ': 'sh', 'ষ': 'sh',
            'স': 's', 'হ': 'h', 'ড়': 'r', 'ঢ়': 'rh', 'য়': 'y',
            'ৎ': 't', 'ং': 'ng', 'ঃ': 'h', 'ঁ': 'n',
            'া': 'a', 'ি': 'i', 'ী': 'ee', 'ু': 'u', 'ূ': 'oo',
            'ৃ': 'ri', 'ে': 'e', 'ৈ': 'oi', 'ো': 'o', 'ৌ': 'ou',
        }
    
    def _initialize_misspellings(self) -> Dict:
        """Initialize common misspellings and variations"""
        return {
            'license': ['licence', 'lisence', 'liscense'],
            'company': ['compnay', 'comapny', 'comany'],
            'certificate': ['certificat', 'certficate', 'certifcate'],
            'tin': ['tinn', 'tin no', 'tin number'],
            'vat': ['vatt', 'vat no', 'value added tax'],
            'turnover': ['turn over', 'turn-over', 'turnouver'],
            'designation': ['desig', 'designaton', 'desgnation'],
        }
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text for matching:
        - Convert to lowercase
        - Remove special characters
        - Handle Bangla transliteration
        - Handle common misspellings
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common separators
        text = re.sub(r'[:\-*/\\|,;]', ' ', text)
        
        # Handle Bangla characters
        bangla_chars = re.findall(r'[\u0980-\u09FF]+', text)
        if bangla_chars:
            for bangla in bangla_chars:
                transliterated = self._transliterate_bangla(bangla)
                text = text.replace(bangla, transliterated)
        
        return text
    
    def _transliterate_bangla(self, bangla_text: str) -> str:
        """Transliterate Bangla text to English approximation"""
        result = []
        for char in bangla_text:
            if char in self.bangla_map:
                result.append(self.bangla_map[char])
            elif char == ' ':
                result.append(' ')
            elif char == '':
                pass
            else:
                result.append(char)
        return ''.join(result)
    
    def calculate_similarity(self, label1: str, label2: str) -> float:
        """Calculate similarity between two field labels"""
        if not label1 or not label2:
            return 0.0
        
        # Normalize both labels
        norm1 = self.normalize_text(label1)
        norm2 = self.normalize_text(label2)
        
        # Exact match after normalization
        if norm1 == norm2:
            return 1.0
        
        # Check for word overlap
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if words1 and words2:
            overlap = len(words1.intersection(words2))
            union = len(words1.union(words2))
            jaccard = overlap / union if union > 0 else 0
        else:
            jaccard = 0
        
        # Sequence matching
        seq_match = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Combined similarity (weighted)
        similarity = (jaccard * 0.4) + (seq_match * 0.6)
        
        return similarity
    
    def match_field(self, field_label: str, field_type: str = None) -> Dict:
        """
        Match a field label to a data source
        
        Args:
            field_label: The label text from the form
            field_type: Optional type hint (text, number, date, etc.)
        
        Returns:
            Dictionary with match information
        """
        normalized_label = self.normalize_text(field_label)
        
        best_match = None
        best_score = 0.0
        
        for pattern_key, pattern_info in self.field_patterns.items():
            # Check pattern matches
            for pattern in pattern_info['patterns']:
                pattern_norm = self.normalize_text(pattern)
                
                # Check if pattern is in label
                if pattern_norm in normalized_label:
                    score = 0.95
                else:
                    # Calculate similarity
                    score = self.calculate_similarity(normalized_label, pattern_norm)
                
                # Boost score for exact matches
                if normalized_label == pattern_norm:
                    score = 1.0
                
                if score > best_score:
                    best_score = score
                    best_match = {
                        'match_key': pattern_key,
                        'source': pattern_info['source'],
                        'field': pattern_info['field'],
                        'confidence': pattern_info['confidence'] * score,
                        'matched_pattern': pattern,
                        'similarity_score': score
                    }
        
        # Handle field type hints
        if field_type and best_match:
            if field_type == 'number' and best_match.get('confidence', 0) < 0.7:
                # Try to find numeric field matches
                numeric_patterns = ['value', 'amount', 'price', 'limit', 'capacity']
                for np in numeric_patterns:
                    if np in normalized_label:
                        best_match['confidence'] = 0.8
                        break
        
        return best_match if best_match else {
            'match_key': None,
            'source': None,
            'field': None,
            'confidence': 0,
            'similarity_score': 0
        }
    
    def extract_form_fields(self, html_content: str) -> List[Dict]:
        """
        Extract form fields from HTML content
        
        Args:
            html_content: HTML content of the form
        
        Returns:
            List of field dictionaries with labels, selectors, etc.
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        fields = []
        
        # Find all input, select, textarea elements
        form_elements = soup.find_all(['input', 'select', 'textarea'])
        
        for element in form_elements:
            # Skip hidden inputs and buttons
            if element.get('type') in ['hidden', 'submit', 'button', 'reset']:
                continue
            
            field = {
                'tag': element.name,
                'type': element.get('type', 'text'),
                'name': element.get('name', ''),
                'id': element.get('id', ''),
                'class': element.get('class', []),
                'selector': self._generate_selector(element),
                'is_required': element.get('required') is not None,
                'placeholder': element.get('placeholder', ''),
                'value': element.get('value', '')
            }
            
            # Find associated label
            label = self._find_label(soup, element)
            field['label'] = label
            
            # Determine if this is a form field (likely part of tender form)
            if self._is_tender_form_field(field, label):
                field['is_tender_field'] = True
                # Match to company data
                match = self.match_field(label or field['name'] or field['placeholder'], field['type'])
                field['matched_data'] = match
            
            fields.append(field)
        
        # Handle nested forms (dynamic fields)
        dynamic_containers = soup.find_all(['div', 'fieldset'], class_=re.compile(r'(dynamic|repeat|clone|nested)'))
        for container in dynamic_containers:
            nested_fields = self._extract_nested_fields(container)
            for field in nested_fields:
                field['is_nested'] = True
                fields.append(field)
        
        return fields
    
    def _generate_selector(self, element) -> str:
        """Generate a CSS selector for an element"""
        if element.get('id'):
            return f"#{element['id']}"
        
        selectors = []
        if element.name:
            selectors.append(element.name)
        if element.get('class'):
            selectors.append('.' + '.'.join(element['class']))
        if element.get('name'):
            selectors.append(f'[name="{element["name"]}"]')
        
        return ' '.join(selectors) if selectors else element.name
    
    def _find_label(self, soup, element) -> str:
        """Find the label associated with a form element"""
        # Check for explicit label with 'for' attribute
        element_id = element.get('id')
        if element_id:
            label = soup.find('label', attrs={'for': element_id})
            if label:
                return label.get_text(strip=True)
        
        # Check for parent label
        parent_label = element.find_parent('label')
        if parent_label:
            return parent_label.get_text(strip=True)
        
        # Check for preceding text
        prev = element.find_previous_sibling()
        if prev and prev.name == 'label':
            return prev.get_text(strip=True)
        
        # Check for placeholder as fallback
        placeholder = element.get('placeholder', '')
        if placeholder:
            return placeholder
        
        # Check for name as fallback
        name = element.get('name', '')
        if name:
            # Convert name to readable label
            label = name.replace('_', ' ').replace('-', ' ').title()
            return label
        
        return ''
    
    def _is_tender_form_field(self, field: Dict, label: str) -> bool:
        """Determine if a field is likely part of a tender form"""
        tender_keywords = [
            'tender', 'bid', 'proposal', 'quotation', 'contract',
            'eoi', 'rfp', 'rfq', 'procurement', 'schedule',
            'offer', 'submission', 'envelope', 'seal'
        ]
        
        # Check field name
        field_name = (field.get('name') or '').lower()
        for keyword in tender_keywords:
            if keyword in field_name:
                return True
        
        # Check label
        label_lower = (label or '').lower()
        for keyword in tender_keywords:
            if keyword in label_lower:
                return True
        
        # Check for financial fields (often in tender forms)
        financial_keywords = ['price', 'amount', 'value', 'cost', 'rate']
        for keyword in financial_keywords:
            if keyword in field_name or keyword in label_lower:
                return True
        
        return False
    
    def _extract_nested_fields(self, container) -> List[Dict]:
        """Extract fields from nested/dynamic form structures"""
        from bs4 import BeautifulSoup
        
        fields = []
        form_elements = container.find_all(['input', 'select', 'textarea'])
        
        for element in form_elements:
            # Skip hidden
            if element.get('type') == 'hidden':
                continue
            
            field = {
                'tag': element.name,
                'type': element.get('type', 'text'),
                'name': element.get('name', ''),
                'id': element.get('id', ''),
                'class': element.get('class', []),
                'selector': self._generate_selector(element),
                'is_required': element.get('required') is not None,
                'placeholder': element.get('placeholder', ''),
                'value': element.get('value', ''),
                'parent_container': container.get('class', ['dynamic'])[0] if container.get('class') else 'dynamic'
            }
            
            # Try to find label within container
            label = self._find_label(container, element)
            field['label'] = label
            
            # Match to data
            match = self.match_field(label or field['name'] or field['placeholder'], field['type'])
            field['matched_data'] = match
            
            fields.append(field)
        
        return fields
    
    def get_confidence_score(self, field_match: Dict) -> Dict:
        """
        Calculate confidence score for auto-fill
        
        Returns:
            Dictionary with confidence details and recommended action
        """
        if not field_match or field_match.get('confidence', 0) == 0:
            return {
                'score': 0,
                'level': 'none',
                'recommendation': 'manual_entry',
                'message': 'No matching data found'
            }
        
        confidence = field_match.get('confidence', 0)
        
        if confidence >= 0.9:
            return {
                'score': confidence,
                'level': 'high',
                'recommendation': 'auto_fill',
                'message': 'High confidence match - will auto-fill'
            }
        elif confidence >= 0.7:
            return {
                'score': confidence,
                'level': 'medium',
                'recommendation': 'suggest',
                'message': 'Medium confidence - will suggest for review'
            }
        elif confidence >= 0.5:
            return {
                'score': confidence,
                'level': 'low',
                'recommendation': 'highlight',
                'message': 'Low confidence - highlight for manual review'
            }
        else:
            return {
                'score': confidence,
                'level': 'none',
                'recommendation': 'manual_entry',
                'message': 'No good match - manual entry required'
            }


# Global instance
field_matcher = FieldMatcher()