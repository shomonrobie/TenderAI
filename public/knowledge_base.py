# _pages/knowledge_base.py

import streamlit as st

def show():
    """Knowledge Base Page"""
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 2.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
            📚 Knowledge Base
        </h1>
        <p style="color: #64748b;">Coming Soon - Help articles and guides</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("📖 Our knowledge base is under construction. Check back soon for articles, guides, and tutorials!")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()