import streamlit as st

def show():
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 3rem; border-radius: 20px; text-align: center; margin-bottom: 2rem;">
        <h1 style="color: white; font-size: 3rem;">🏗️ TenderAI</h1>
        <p style="color: white; font-size: 1.5rem;">AI-Powered Tender Management System</p>
        <p style="color: white; font-size: 1.2rem;">For Construction Companies in Bangladesh</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Features section
    st.markdown("## 🚀 Key Features")
    
    col1, col2, col3 = st.columns(3)
    
    features = [
        ("🤖", "AI-Powered Analysis", "85% accurate winning bid predictions using advanced machine learning"),
        ("📊", "Real-time Market Intelligence", "Live market data and competitor tracking for better decisions"),
        ("👥", "Team Collaboration", "Multi-user access with role-based permissions"),
        ("📈", "Advanced Analytics", "Comprehensive reports and performance insights"),
        ("💳", "Flexible Payments", "Support for bKash, Nagad, Rocket, and Credit Cards"),
        ("🔒", "Secure Platform", "Bank-grade security with data encryption")
    ]
    
    for idx, (icon, title, desc) in enumerate(features):
        with [col1, col2, col3][idx % 3]:
            st.markdown(f"""
            <div style="background: white; padding: 1.5rem; border-radius: 10px; 
                        text-align: center; margin: 0.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="font-size: 3rem;">{icon}</div>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Call to action
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h2>Ready to Transform Your Tendering Process?</h2>
            <p style="font-size: 1.1rem;">Join hundreds of construction companies already using TenderAI</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🚀 Start Free Trial", use_container_width=True):
                st.session_state.page = "register"
                st.rerun()
        with col_btn2:
            if st.button("💰 View Pricing", use_container_width=True):
                st.session_state.page = "pricing"
                st.rerun()
    
    # Trust section
    st.markdown("---")
    st.markdown("## 🌟 Trusted By")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    companies = ["ABC Construction", "BuildTech BD", "Metro Developers", "Bridge Builders", "Road Masters"]
    
    for idx, company in enumerate(companies):
        with [col1, col2, col3, col4, col5][idx]:
            st.markdown(f"<p style='text-align: center; font-weight: bold;'>{company}</p>", unsafe_allow_html=True)