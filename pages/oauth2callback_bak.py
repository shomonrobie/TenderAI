# pages/oauth2callback.py
"""
OAuth2 Callback Handler for Google Sign-In
"""
import streamlit as st

# ✅ Check if code is in the URL
query_params = st.query_params

if 'code' in query_params:
    # Show a clean Streamlit loading UI
    st.markdown("## 🔄 Authenticating...")
    
    with st.spinner("Processing Google Sign-In..."):
        # Process the callback directly
        from modules.google_auth import handle_google_callback
        user_data = handle_google_callback()
        
    # Handle the result and set the routing state
    if user_data and user_data.get('logged_in'):
        user_role = st.session_state.get('user_role', 'viewer')
        if user_role in ['admin', 'system_admin']:
            st.session_state.page = "admin_dashboard"
        elif user_role == 'company_admin':
            st.session_state.page = "company_dashboard"
        else:
            st.session_state.page = "dashboard"
    elif user_data and user_data.get('show_registration'):
        st.session_state.page = "register"
    else:
        st.session_state.page = "login"
        
    # ✅ CRITICAL: Clear query params BEFORE rerunning to prevent infinite loop
    st.query_params.clear()
    
    # Rerun the main app script. 
    # Because we cleared the params, it won't trigger this callback logic again.
    # The main app will see the updated st.session_state.page and route correctly.
    st.rerun()
    
else:
    # No code in URL - redirect to login
    st.session_state.page = "login"
    st.query_params.clear()
    st.rerun()