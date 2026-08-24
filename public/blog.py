# _pages/blog.py

import streamlit as st

def show():
    """Blog Page"""
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 2.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
            📝 Blog
        </h1>
        <p style="color: #64748b;">Insights and updates from the TenderAI team</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("📰 Our blog is coming soon. Stay tuned for articles on tender intelligence, AI, and industry insights!")
    
    # Show some placeholder blog cards
    st.markdown("### 📌 Upcoming Topics")
    
    topics = [
        "How AI is Transforming Tender Management in Bangladesh",
        "5 Tips for Winning More Government Tenders",
        "Understanding PPR 2025: What You Need to Know",
        "The Future of e-GP: AI-Powered Bid Optimization",
        "Case Study: How TenderAI Helped a Company Win 3x More Tenders"
    ]
    
    for topic in topics:
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 3px solid #667eea;">
            <p style="color: #e0e0e0; margin: 0;">📄 {topic}</p>
            <p style="color: #64748b; font-size: 0.8rem; margin: 0.3rem 0 0 0;">Coming soon...</p>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
    from modules.footer import render_footer
    render_footer()        