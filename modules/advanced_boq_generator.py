# modules/advanced_boq_matcher.py

import pandas as pd
import re
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import Levenshtein  # pip install python-Levenshtein
import streamlit as st


class AdvancedBOQMatcher:
    """Advanced BOQ matching with fuzzy logic and NLP techniques"""
    
    def __init__(self):
        # Common words to ignore during matching
        self.stop_words = {
            'the', 'and', 'for', 'with', 'of', 'to', 'in', 'on', 'at', 'by', 
            'from', 'up', 'off', 'over', 'under', 'including', 'etc', 'all',
            'complete', 'respect', 'accepted', 'engineer', 'charge', 'supply',
            'material', 'necessary', 'water', 'electricity', 'charges', 'cost',
            'use', 'before', 'after', 'during', 'between', 'through', 'without',
            'cement', 'sand', 'mortar', 'work', 'works', 'thick', 'mm', 'sqm',
            'cum', 'floor', 'plinth', 'foundation', 'superstructure', 'walls'
        }
        
        # Special characters to clean
        self.special_chars = re.compile(r'[^a-zA-Z0-9\s\+\-\*]')
        
        # Variation patterns for normalization
        self.variation_patterns = [
            (r'\b(fitting|fixing|fixtures?)\s+&\s+(fixing|fitting|fixtures?)', 'fitting and fixing'),
            (r'\b(u[pP][vV][cC])\b', 'upvc'),
            (r'\b(kg/sqm|kg/m2|kg per sqm)\b', 'kg/sqm'),
            (r'\b(mobilization|mobilisation|mobilize|mobilise)\b', 'mobilization'),
            (r'\b(colour|color)\b', 'colour'),
            (r'\b(metre|meter)\b', 'meter'),
            (r'\b(centre|center)\b', 'center'),
            (r'\b(sqm|m2|square meter|square metre)\b', 'sqm'),
            (r'\b(cum|m3|cubic meter|cubic metre)\b', 'cum'),
        ]
        
        # Suffix patterns to normalize
        self.suffix_patterns = [
            (r'[\*\-\–\—\•]\s*(with\s+)?(?:indian\s+)?(?:chips?|glass\s+strip|red\s+strip|beige\s+strip|matt\s+glazed\s+textured\s+strip|klinker\s+facing).*$', ''),
            (r'\(cement\s*:\s*[^)]+\)', ''),
            (r'\([^)]*(?:size|mm|cm|m|kg)[^)]*\)', ''),
            (r'\s+etc\.?\s*', ''),
            (r'\s+complete\s+in\s+all\s+respect', ''),
            (r'\s+accepted\s+by\s+the\s+engineer-in-charge\.?', ''),
            (r'\s*\.\s*$', ''),
        ]
        
        # Child detection patterns (for parent-child splitting)
        self.child_patterns = [
            r'(?:^|\n|\s+)(?:\*{1,2}|-{1,2}|•|●|○|→|➜|➤|▶|✓|✔|•)\s*[A-Za-z]?\.?\s*',
            r'(?:^|\n|\s+)(?:[0-9]+\.|[a-z]\.|[0-9]+\)|[a-z]\))\s*',
            r'(?:^|\n|\s+)(?:Approx\.?|Approximately|Size|Size:|Min\.?|Minimum|Weight|Equivalent|Brand|Similar)',
            r'(?:^|\n|\s+)(?:\d{2,3}\s*[x×*]\s*\d{2,3}\s*(?:mm|cm|m))',
            r'(?:^|\n|\s+)(?:\d+\.?\d*\s*(?:mm|cm|m|kg|kg/m|sqm|meter|ft)\s*(?:size|weight)?)',
            r'(?:^|\n|\s+)(?:Equivalent to|Brand:|Manufacturer:|Model:|Type:)',
            r'(?:^|\n|\s+)(?:RAK\s*:|Stella\s*:|COTTO\s*:|CHARU\s*:)',
            r'(?:^|\n|\s+)(?:[A-Z]\s*[0-9]{2,}\s*[x×*]\s*[A-Z]\s*[0-9]{2,})',
            r'(?:^|\n|\s+)(?:[A-Z][a-z]+(?:\s*[A-Z][a-z]+)*\s*[0-9]{3,4})',
        ]

    def clean_description(self, text: str) -> str:
        """Clean and normalize description text"""
        if not text or pd.isna(text):
            return ""
        
        text = str(text).lower().strip()
        text = self.special_chars.sub(' ', text)
        
        for pattern, replacement in self.variation_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        for pattern, replacement in self.suffix_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        text = ' '.join(text.split())
        return text

    def extract_key_features(self, text: str) -> str:
        """Extract key features from description for matching"""
        if not text:
            return ""
        
        cleaned = self.clean_description(text)
        words = cleaned.split()
        words = [w for w in words if w not in self.stop_words and len(w) > 2]
        
        return ' '.join(words)

    def calculate_similarity(self, text1: str, text2: str, method: str = 'combined') -> float:
        """Calculate similarity between two texts using multiple methods"""
        if not text1 or not text2:
            return 0.0
        
        clean1 = self.clean_description(text1)
        clean2 = self.clean_description(text2)
        
        if method == 'levenshtein':
            distance = Levenshtein.distance(clean1, clean2)
            max_len = max(len(clean1), len(clean2))
            return 1 - (distance / max_len) if max_len > 0 else 0
            
        elif method == 'sequence':
            return SequenceMatcher(None, clean1, clean2).ratio()
            
        elif method == 'token':
            tokens1 = set(clean1.split())
            tokens2 = set(clean2.split())
            if not tokens1 or not tokens2:
                return 0.0
            intersection = len(tokens1.intersection(tokens2))
            union = len(tokens1.union(tokens2))
            return intersection / union
            
        elif method == 'combined':
            lev_sim = self.calculate_similarity(text1, text2, 'levenshtein')
            seq_sim = self.calculate_similarity(text1, text2, 'sequence')
            tok_sim = self.calculate_similarity(text1, text2, 'token')
            return 0.3 * lev_sim + 0.3 * seq_sim + 0.4 * tok_sim
        
        return 0.0

    def split_parent_child(self, description: str) -> Dict[str, str]:
        """
        Split a BOQ description into parent and child parts.
        Handles ALL possible formats.
        """
        if not description:
            return {'parent': '', 'child': ''}
        
        text = str(description)
        
        # Try to find where child description starts
        split_index = -1
        
        # Method 1: Look for child indicators in order of reliability
        for pattern in self.child_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                for match in matches:
                    if match.start() > 20:  # Not at the very beginning
                        split_index = match.start()
                        break
                if split_index != -1:
                    break
        
        # Method 2: If no pattern found, try to split by keywords
        if split_index == -1:
            child_keywords = ['approx', 'approx.', 'size', 'weight', 'equivalent', 'brand', 
                              'similar', 'minimum', 'max', 'mm', 'cm', 'kg', 'model']
            text_lower = text.lower()
            for keyword in child_keywords:
                idx = text_lower.find(keyword)
                if idx > 50:  # At least 50 chars in for parent part
                    split_index = idx
                    break
        
        if split_index != -1:
            parent_part = text[:split_index].strip()
            child_part = text[split_index:].strip()
            
            # Clean up the parts
            parent_part = re.sub(r'\s+', ' ', parent_part)
            child_part = re.sub(r'\s+', ' ', child_part)
            
            # Remove leading separators from child
            child_part = re.sub(r'^[\*\-–—•○●→➜➤▶✓✔\s]+', '', child_part)
            child_part = re.sub(r'^[0-9a-z][\.\)]\s*', '', child_part, flags=re.IGNORECASE)
            
            return {
                'parent': parent_part,
                'child': child_part
            }
        
        # Method 3: If still no split, treat as both (fallback)
        # Check if text contains both long description AND size info
        has_size = any(kw in text.lower() for kw in ['approx', 'size', 'weight', 'equivalent'])
        has_long_description = len(text) > 200
        
        if has_long_description and has_size:
            # Try to split at sentence boundaries
            sentences = re.split(r'[.!?]\s+', text)
            if len(sentences) > 1:
                for i, sent in enumerate(sentences):
                    if any(kw in sent.lower() for kw in ['approx', 'size', 'weight', 'equivalent', 'brand']):
                        parent_part = ' '.join(sentences[:i])
                        child_part = ' '.join(sentences[i:])
                        return {
                            'parent': parent_part.strip(),
                            'child': child_part.strip()
                        }
        
        # Method 4: Check if description matches child pattern (standalone child)
        child_indicators = ['approx', 'size:', 'weight:', 'equivalent to', 'brand:', 'model:']
        if any(indicator in text.lower() for indicator in child_indicators) and len(text) < 300:
            # This is likely a child item without parent
            return {'parent': '', 'child': text}
        
        # If all else fails, use the whole thing as parent
        return {'parent': text, 'child': ''}

    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key numerical terms and important keywords from description"""
        if not text:
            return []
        
        # Find numeric values with units
        pattern = r'(\d+(?:\.\d+)?)\s*(?:mm|cm|m|kg|sqm|cum|thick|mm\s*thick)'
        numbers = re.findall(pattern, text.lower())
        
        # Find important material keywords
        material_keywords = [
            'brick', 'cement', 'sand', 'mortar', 'concrete', 'steel', 'rod', 
            'bar', 'tile', 'marble', 'granite', 'glass', 'paint', 'plaster',
            'mosaic', 'strip', 'chip', 'upvc', 'aluminum', 'wood', 'timber',
            'closet', 'basin', 'sink', 'urinal', 'toilet', 'sanitary', 'pipe',
            'valve', 'cock', 'mixer', 'shower', 'tank', 'pump', 'motor',
            'bracket', 'holder', 'rail', 'shelf', 'mirror', 'glass', 'ceramic'
        ]
        
        keywords = []
        for word in material_keywords:
            if word in text.lower():
                keywords.append(word)
        
        return numbers + keywords

    def _find_best_match(self, text: str, df: pd.DataFrame, threshold: float = 0.3) -> Optional[Dict]:
        """Find best matching item in a DataFrame"""
        if not text or df.empty:
            return None
        
        best_match = None
        best_score = 0
        best_method = ''
        
        cleaned_text = self.clean_description(text)
        features = self.extract_key_features(text)
        
        for idx, row in df.iterrows():
            # Calculate similarity using combined method
            similarity = self.calculate_similarity(text, row.get('description', ''), 'combined')
            
            if similarity > best_score:
                best_score = similarity
                best_match = row.to_dict()
                best_method = 'combined'
        
        # Only return if similarity exceeds threshold
        if best_score >= threshold:
            best_match['similarity'] = best_score
            best_match['match_method'] = best_method
            return best_match
        
        return None

    def match_boq_items(self, df_boq: pd.DataFrame, rates_df: pd.DataFrame, threshold: float = 0.45) -> Dict:
        """
        Match BOQ items with PWD rates using advanced fuzzy matching.
        Automatically handles BOTH standalone items AND parent-child relationships.
        """
        matched_items = []
        unmatched_items = []
        auto_detected_parent_child = 0
        auto_detected_standalone = 0
        
        # Separate parent and child data
        # Assuming rates_df has 'is_parent' column or we detect it
        if 'is_parent' in rates_df.columns:
            parents_df = rates_df[rates_df['is_parent'] == True].copy()
            children_df = rates_df[rates_df['is_parent'] == False].copy()
        else:
            # If no is_parent column, assume all are children (standalone)
            parents_df = pd.DataFrame()
            children_df = rates_df.copy()
        
        # Prepare children data
        if not children_df.empty:
            children_df['clean_desc'] = children_df['description'].apply(self.clean_description)
            children_df['features'] = children_df['clean_desc'].apply(self.extract_key_features)
        
        # Prepare parent data
        if not parents_df.empty:
            parents_df['clean_desc'] = parents_df['description'].apply(self.clean_description)
            parents_df['features'] = parents_df['clean_desc'].apply(self.extract_key_features)
        
        # Process each BOQ item
        for idx, row in df_boq.iterrows():
            description = str(row.get('description', '')).strip()
            item_code = str(row.get('item_code', '')).strip()
            
            if not description:
                continue
                
            quantity = float(row.get('quantity', 0)) if pd.notna(row.get('quantity')) else 0
            unit = str(row.get('unit', '')).strip()
            
            # Step 1: Try exact code match first
            if item_code:
                exact_match = children_df[children_df['pwd_code'].astype(str).str.upper() == item_code.upper()]
                if not exact_match.empty:
                    row_data = exact_match.iloc[0]
                    matched_items.append(self._create_item_data(
                        row, row_data.get('unit_rate', 0), row_data.get('unit', unit),
                        "Exact Code Match", row_data
                    ))
                    auto_detected_standalone += 1
                    continue
            
            # Step 2: Try to split parent-child
            parts = self.split_parent_child(description)
            parent_text = parts.get('parent', '')
            child_text = parts.get('child', '')
            
            # If we have both parent and child text, try parent-child matching
            if parent_text and child_text and not parents_df.empty:
                # Match parent
                parent_match = self._find_best_match(parent_text, parents_df, threshold=0.3)
                # Match child
                child_match = self._find_best_match(child_text, children_df, threshold=0.3)
                
                if child_match and child_match.get('unit_rate', 0) > 0:
                    matched_items.append(self._create_item_data(
                        row,
                        child_match.get('unit_rate', 0),
                        child_match.get('unit', unit),
                        f"Parent-Child Split (Parent: {parent_match.get('pwd_code', 'N/A') if parent_match else 'N/A'}, Child: {child_match.get('pwd_code', 'N/A')})",
                        child_match,
                        parent_match=parent_match
                    ))
                    auto_detected_parent_child += 1
                    continue
                elif parent_match:
                    # Parent matched but child didn't - try child as standalone
                    pass
            
            # Step 3: Try direct child match (standalone)
            if not children_df.empty:
                direct_match = self._find_best_match(description, children_df, threshold=threshold)
                if direct_match and direct_match.get('unit_rate', 0) > 0:
                    matched_items.append(self._create_item_data(
                        row,
                        direct_match.get('unit_rate', 0),
                        direct_match.get('unit', unit),
                        f"Direct Match ({direct_match.get('similarity', 0):.1%})",
                        direct_match
                    ))
                    auto_detected_standalone += 1
                    continue
            
            # Step 4: Try TF-IDF for better contextual matching (if large dataset)
            if len(children_df) > 100 and not children_df.empty:
                vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
                rate_vectors = vectorizer.fit_transform(children_df['features'])
                query_vector = vectorizer.transform([self.extract_key_features(description)])
                similarities = cosine_similarity(query_vector, rate_vectors).flatten()
                best_idx = np.argmax(similarities)
                best_score = similarities[best_idx]
                
                if best_score > 0.3:
                    row_data = children_df.iloc[best_idx]
                    matched_items.append(self._create_item_data(
                        row,
                        row_data.get('unit_rate', 0),
                        row_data.get('unit', unit),
                        f"TF-IDF Match ({best_score:.1%})",
                        row_data
                    ))
                    auto_detected_standalone += 1
                    continue
            
            # Step 5: Try key terms matching (fallback)
            key_terms = self._extract_key_terms(description)
            if key_terms and not children_df.empty:
                found = False
                for _, rate_row in children_df.iterrows():
                    rate_terms = self._extract_key_terms(rate_row['description'])
                    if rate_terms:
                        common_terms = set(key_terms).intersection(set(rate_terms))
                        if common_terms:
                            matched_items.append(self._create_item_data(
                                row,
                                rate_row.get('unit_rate', 0),
                                rate_row.get('unit', unit),
                                f"Key Terms Match ({len(common_terms)} terms)",
                                rate_row
                            ))
                            auto_detected_standalone += 1
                            found = True
                            break
                if found:
                    continue
            
            # No match found
            unmatched_items.append(self._create_item_data(row, 0, unit, 'Not Found', None))
        
        # Calculate totals
        total_cost = sum(item['Total'] for item in matched_items if item.get('Total', 0))
        
        return {
            'matched': matched_items,
            'unmatched': unmatched_items,
            'total_matched': len(matched_items),
            'total_unmatched': len(unmatched_items),
            'total_cost': total_cost,
            'auto_detected_parent_child': auto_detected_parent_child,
            'auto_detected_standalone': auto_detected_standalone,
            'match_summary': {
                'Total Items': len(df_boq),
                'Matched': len(matched_items),
                'Unmatched': len(unmatched_items),
                'Parent-Child Detected': auto_detected_parent_child,
                'Standalone Matched': auto_detected_standalone,
                'Match Rate': f"{(len(matched_items) / len(df_boq) * 100):.1f}%"
            }
        }

    def _create_item_data(self, row: pd.Series, rate: float, unit: str, match_method: str, 
                          child_data: Optional[Dict] = None, parent_match: Optional[Dict] = None) -> Dict:
        """Create standardized item data dictionary"""
        return {
            'Item Code': row.get('item_code', 'N/A'),
            'Description': row.get('description', ''),
            'Unit': unit or row.get('unit', 'N/A'),
            'Quantity': row.get('quantity', 0),
            'Unit Rate': rate,
            'Total': row.get('quantity', 0) * rate,
            'Match Method': match_method,
            'Parent Code': parent_match.get('pwd_code', 'N/A') if parent_match else 'N/A',
            'Child Code': child_data.get('pwd_code', 'N/A') if child_data else 'N/A',
            'Zone-A': child_data.get('zone_a', 0) if child_data else 0,
            'Zone-B': child_data.get('zone_b', 0) if child_data else 0,
            'Zone-C': child_data.get('zone_c', 0) if child_data else 0,
            'Zone-D': child_data.get('zone_d', 0) if child_data else 0,
            'Parent Match Score': parent_match.get('similarity', 0) if parent_match else 0,
            'Child Match Score': child_data.get('similarity', 0) if child_data else 0,
        }

    def get_match_summary(self, result: Dict) -> str:
        """Get a formatted summary of matching results"""
        summary = result.get('match_summary', {})
        return f"""
        📊 **BOQ Matching Summary**
        --------------------------
        Total Items: {summary.get('Total Items', 0)}
        Matched: {summary.get('Matched', 0)} ✅
        Unmatched: {summary.get('Unmatched', 0)} ❌
        Match Rate: {summary.get('Match Rate', '0%')}
        
        🔍 **Detection Methods:**
        Parent-Child Detected: {summary.get('Parent-Child Detected', 0)}
        Standalone Matched: {summary.get('Standalone Matched', 0)}
        
        💰 **Total Cost: {result.get('total_cost', 0):,.2f}**
        """