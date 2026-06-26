# modules/language_manager.py

import streamlit as st
import json
import os
from typing import Dict, Any

class LanguageManager:
    """Multi-lingual support manager"""
    
    SUPPORTED_LANGUAGES = {
        'en': {'name': 'English', 'flag': '🇬🇧', 'dir': 'ltr'},
        'bn': {'name': 'বাংলা', 'flag': '🇧🇩', 'dir': 'ltr'}
    }
    
    def __init__(self, locale_dir='locales'):
        self.locale_dir = locale_dir
        self.translations = {}
        self._load_translations()
    
    def _load_translations(self):
        """Load all translation files"""
        for lang_code in self.SUPPORTED_LANGUAGES:
            file_path = os.path.join(self.locale_dir, f"{lang_code}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.translations[lang_code] = json.load(f)
    
    def get_current_language(self) -> str:
        """Get current language from session state"""
        return st.session_state.get('language', 'en')
    
    def set_language(self, lang_code: str):
        """Set current language"""
        if lang_code in self.SUPPORTED_LANGUAGES:
            st.session_state.language = lang_code
            st.rerun()
    
    def translate(self, key: str, default: str = None) -> str:
        """Translate a key to current language"""
        lang = self.get_current_language()
        keys = key.split('.')
        
        value = self.translations.get(lang, {})
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                break
        
        if value is None and default:
            return default
        return value or key
    
    def render_language_selector(self):
        """Render language selector in sidebar"""
        current_lang = self.get_current_language()
        
        st.markdown("---")
        st.markdown("### 🌐 Language / ভাষা")
        
        cols = st.columns(len(self.SUPPORTED_LANGUAGES))
        for idx, (code, info) in enumerate(self.SUPPORTED_LANGUAGES.items()):
            with cols[idx]:
                is_active = current_lang == code
                button_label = f"{info['flag']} {info['name']}"
                
                if st.button(
                    button_label, 
                    key=f"lang_{code}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary"
                ):
                    self.set_language(code)
    
    def get_direction(self) -> str:
        """Get text direction for current language"""
        lang = self.get_current_language()
        return self.SUPPORTED_LANGUAGES.get(lang, {}).get('dir', 'ltr')


# Create global instance
lang = LanguageManager()

# Helper function for easy translation
def _(key: str, default: str = None) -> str:
    """Shortcut for translation"""
    return lang.translate(key, default)