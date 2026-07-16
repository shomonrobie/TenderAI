# debug_methods.py - Run this with streamlit
import streamlit as st
from database.unified_db_manager import get_db_manager

st.set_page_config(page_title="Debug Methods", layout="wide")

st.title("🔍 Database Method Checker")

try:
    db = get_db_manager()
    
    # Get all methods
    methods = [method for method in dir(db) if not method.startswith('_')]
    
    st.subheader("Available Methods")
    st.code("\n".join(sorted(methods)), language="python")
    
    # Check specific methods
    st.subheader("Specific Method Check")
    important_methods = [
        'get_company_experience',
        'add_experience',
        'delete_experience',
        'get_company_licenses',
        'get_company_financials',
        'get_company_personnel',
        'get_company_equipment',
        'get_company_documents',
        'update_company'
    ]
    
    for method in important_methods:
        status = "✅" if hasattr(db, method) else "❌"
        st.write(f"{status} {method}")
        
except Exception as e:
    st.error(f"Error: {e}")
    st.code(str(e))