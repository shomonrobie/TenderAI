# modules/footer.py
import streamlit as st
from datetime import datetime
import urllib.parse

def navigate_to(page: str):
    """Central navigation handler"""
    st.session_state.page = page
    st.rerun()


def footer_css():
    """Footer styles"""
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
    .footer-container {
        background: linear-gradient(145deg, #0a0a1a 0%, #1a1a2e 30%, #16213e 65%, #0f0f23 100%) !important;
        border-radius: 20px;
        padding: 2.8rem 2rem 2rem;
        margin: 3rem 1rem 2rem 1rem;
        border: 1px solid rgba(102, 126, 234, 0.3);
        box-shadow: 0 15px 50px rgba(0,0,0,0.7);
        position: relative;
        overflow: hidden;
        color: #e2e8f0;
    }
    
    .footer-container::before {
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(circle at 25% 35%, rgba(102, 126, 234, 0.12) 0%, transparent 60%),
                    radial-gradient(circle at 75% 65%, rgba(118, 75, 162, 0.12) 0%, transparent 60%);
        animation: gradientShift 25s ease-in-out infinite;
        z-index: 1;
    }

    @keyframes gradientShift {
        0%, 100% { transform: translate(0, 0); }
        50% { transform: translate(8%, 6%); }
    }

    .footer-content { position: relative; z-index: 2; }
    
    .footer-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 2.2rem;
        margin: 2rem 0;
    }
    
    .footer-column h4 {
        color: #e8e8e8;
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 1.4rem;
    }

    /* Strong button reset to look like links */
    .footer-column [data-testid="stButton"] button,
    .footer-column .stButton button,
    .footer-column button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #94a3b8 !important;
        padding: 0.45rem 0 !important;
        font-size: 0.97rem !important;
        text-align: left !important;
        width: 100% !important;
        height: auto !important;
        border-radius: 0 !important;
    }
    
    .footer-column [data-testid="stButton"] button:hover,
    .footer-column .stButton button:hover {
        color: #667eea !important;
        transform: translateX(12px) !important;
    }

    .footer-social-section {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 2rem;
        margin-top: 2rem;
    }

    .social-icons { display: flex; gap: 1.2rem; flex-wrap: wrap; }
    
    .social-icon {
        width: 48px; height: 48px;
        border-radius: 50%;
        background: rgba(255,255,255,0.07);
        color: #94a3b8;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.45rem;
        border: 1px solid rgba(255,255,255,0.1);
        transition: all 0.3s ease;
    }
    
    .social-icon:hover {
        background: rgba(102, 126, 234, 0.3);
        color: #667eea;
        transform: translateY(-4px) scale(1.1);
    }

    .demo-button-wrapper button {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: white !important;
        padding: 0.9rem 2.5rem !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        box-shadow: 0 8px 30px rgba(102, 126, 234, 0.4) !important;
    }

    .footer-bottom {
        margin-top: 2rem;
        padding-top: 1.6rem;
        border-top: 1px solid rgba(255,255,255,0.12);
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
        font-size: 0.88rem;
        color: #64748b;
    }

    @media (max-width: 768px) {
        .footer-grid { grid-template-columns: 1fr 1fr; }
        .footer-social-section { flex-direction: column; text-align: center; }
    }
    </style>
    """, unsafe_allow_html=True)


def footer_links_column(title: str, links: list[tuple[str, str]]):
    """Reusable column component"""
    st.markdown(f'<div class="footer-column"><h4>{title}</h4>', unsafe_allow_html=True)
    
    for label, page in links:
        if st.button(label, key=f"ft_{page}", use_container_width=True):
            navigate_to(page)
    
    st.markdown('</div>', unsafe_allow_html=True)


def footer_social_section(share_links: dict):
    """Social icons + Demo button"""
    st.markdown('<div class="footer-social-section">', unsafe_allow_html=True)
    
    # Share Section
    st.markdown(f"""
    <div>
        <div style="color:#94a3b8; margin-bottom:0.8rem; font-weight:500;">🌐 Share TenderAI with your network</div>
        <div class="social-icons">
            <a href="{share_links['facebook_share']}" target="_blank" class="social-icon"><i class="fab fa-facebook-f"></i></a>
            <a href="{share_links['linkedin_share']}" target="_blank" class="social-icon"><i class="fab fa-linkedin-in"></i></a>
            <a href="{share_links['twitter_share']}" target="_blank" class="social-icon"><i class="fab fa-x-twitter"></i></a>
            <a href="{share_links['whatsapp_share']}" target="_blank" class="social-icon"><i class="fab fa-whatsapp"></i></a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Demo Button
    st.markdown('<div class="demo-button-wrapper">', unsafe_allow_html=True)
    if st.button("🚀 Book a Demo", key="footer_main_demo", type="primary"):
        navigate_to("book_demo")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def footer_bottom():
    """Bottom copyright and legal links"""
    st.markdown(f"""
    <div class="footer-bottom">
        <div>© {datetime.now().year} TenderAI (BD). All rights reserved. | Bangladesh's First AI-Powered Tender Intelligence Platform</div>
    """, unsafe_allow_html=True)

    bottom_links = [("Terms", "terms"), ("Privacy", "privacy"), ("GDPR", "gdpr")]
    for label, page in bottom_links:
        if st.button(label, key=f"fb_{page}"):
            navigate_to(page)

    st.markdown('</div>', unsafe_allow_html=True)


# ===================== MAIN FOOTER =====================
def render_public_footer():
    """Main footer composed of components"""
    
    share_links = {
        "facebook_share": f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote('https://www.itenderbd.com')}",
        "linkedin_share": f"https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote('https://www.itenderbd.com')}",
        "twitter_share": f"https://twitter.com/intent/tweet?text={urllib.parse.quote('TenderAI - AI-Powered Tender Intelligence Platform')}&url={urllib.parse.quote('https://www.itenderbd.com')}",
        "whatsapp_share": f"https://api.whatsapp.com/send?text={urllib.parse.quote('TenderAI - AI-Powered Tender Intelligence Platform https://www.itenderbd.com')}",        
    }

    footer_css()

    st.markdown('<div class="footer-container"><div class="footer-content">', unsafe_allow_html=True)

    # Grid with columns
    st.markdown('<div class="footer-grid">', unsafe_allow_html=True)
    
    sections = [
        ("🏗️ TenderAI", [
            ("🏠 Home", "home"), ("ℹ️ About Us", "about"),
            ("⚡ Features", "features"), ("💰 Pricing", "pricing")
        ]),
        ("📚 Resources", [
            ("📖 Knowledge Base", "knowledge_base"), ("❓ FAQ", "faq"),
            ("📝 Blog", "blog"), ("🆘 Support", "support")
        ]),
        ("⚖️ Legal", [
            ("📋 Terms & Conditions", "terms"), ("🔒 Privacy Policy", "privacy"),
            ("🍪 Cookie Policy", "cookies"), ("🛡️ GDPR Compliance", "gdpr")
        ]),
        ("📞 Contact", [
            ("📬 Contact Us", "contact"), ("📅 Book a Demo", "book_demo")
        ])
    ]

    for title, links in sections:
        footer_links_column(title, links)

    st.markdown('</div>', unsafe_allow_html=True)

    # Social + Demo
    footer_social_section(share_links)

    # Bottom
    footer_bottom()

    st.markdown('</div></div>', unsafe_allow_html=True)  # Close containers