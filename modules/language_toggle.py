# modules/language_toggle.py

import streamlit as st
from modules.language_manager import LanguageManager

def render_language_toggle():
    """Render a simple language toggle in the header"""
    
    lang_manager = LanguageManager()
    current_lang = lang_manager.get_current_language()
    
    # Create two buttons side by side
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(
            "🇬🇧 English", 
            key="toggle_en",
            use_container_width=True,
            type="primary" if current_lang == 'en' else "secondary"
        ):
            lang_manager.set_language('en')
    
    with col2:
        if st.button(
            "🇧🇩 বাংলা", 
            key="toggle_bn",
            use_container_width=True,
            type="primary" if current_lang == 'bn' else "secondary"
        ):
            lang_manager.set_language('bn')