# modules/footer.py

import streamlit as st
from datetime import datetime
import urllib.parse

def render_footer():
    """Render enhanced footer with working gradient background"""
    
    share_url = "https://www.itenderbd.com"
    share_title = "TenderAI - AI-Powered Tender Intelligence Platform"
    
    share_links = {
        "facebook_share": f"https://www.facebook.com/sharer/sharer.php?u={urllib.parse.quote(share_url)}",
        "linkedin_share": f"https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote(share_url)}",
        "twitter_share": f"https://twitter.com/intent/tweet?text={urllib.parse.quote(share_title)}&url={urllib.parse.quote(share_url)}",
        "whatsapp_share": f"https://api.whatsapp.com/send?text={urllib.parse.quote(share_title + ' ' + share_url)}",        
    }
    
    st.markdown("""
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
        """, unsafe_allow_html=True)
    
    footer_code = f"""
    <style>
    
    .footer-container {{
        background: linear-gradient(145deg, #0a0a1a 0%, #1a1a2e 30%, #16213e 65%, #0f0f23 100%) !important;
        border-radius: 20px;
        padding: 2.8rem 2rem 2rem;
        margin: 3rem 1rem 2rem 1rem;
        border: 1px solid rgba(102, 126, 234, 0.3);
        box-shadow: 0 15px 50px rgba(0,0,0,0.7);
        position: relative;
        overflow: hidden;
        color: #e2e8f0;
    }}

    .footer-container::before {{
        content: '';
        position: absolute;
        inset: 0;
        background: radial-gradient(circle at 25% 35%, rgba(102, 126, 234, 0.12) 0%, transparent 60%),
                    radial-gradient(circle at 75% 65%, rgba(118, 75, 162, 0.12) 0%, transparent 60%);
        animation: gradientShift 25s ease-in-out infinite;
        z-index: 1;
        border-radius: 20px;
    }}

    @keyframes gradientShift {{
        0%, 100% {{ transform: translate(0, 0); }}
        50% {{ transform: translate(8%, 6%); }}
    }}

    .footer-content {{ position: relative; z-index: 2; }}

    .footer-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
        gap: 2rem;
        margin: 2rem 0;
    }}

    .footer-column h4 {{
        color: #e8e8e8;
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 1.2rem;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}

    .footer-column a {{
        color: #94a3b8;
        text-decoration: none;
        display: block;
        padding: 0.45rem 0;
        transition: all 0.3s ease;
    }}

    .footer-column a:hover {{
        color: #667eea;
        transform: translateX(8px);
    }}

    .contact-info-row {{
        display: flex;
        justify-content: center;
        gap: 2rem;
        flex-wrap: wrap;
        margin-bottom: 1.5rem;
    }}

    .contact-info-row a {{
        color: #94a3b8;
        padding: 0.6rem 1.2rem;
        border-radius: 12px;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 0.7rem;
    }}

    .trust-badge-footer {{
        display: flex;
        justify-content: center;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 2rem;
    }}

    .trust-badge-footer span {{
        background: rgba(255,255,255,0.05);
        padding: 0.5rem 1.1rem;
        border-radius: 30px;
        font-size: 0.85rem;
        border: 1px solid rgba(255,255,255,0.1);
        color: #94a3b8;
    }}

    .footer-divider {{
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(102,126,234,0.4), transparent);
        border: none;
        margin: 2rem 0;
    }}

    .footer-social-section {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 2rem;
    }}

    .social-icons {{ display: flex; gap: 1rem; }}

    .social-icon {{
        width: 46px; height: 46px;
        border-radius: 50%;
        background: rgba(255,255,255,0.06);
        color: #94a3b8;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.3rem;
        transition: all 0.3s ease;
    }}

    .social-icon:hover {{
        background: rgba(102, 126, 234, 0.25);
        color: #667eea;
        transform: translateY(-5px) scale(1.1);
    }}

    .demo-button {{
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 0.85rem 2.2rem;
        border-radius: 12px;
        font-weight: 600;
        text-decoration: none;
        box-shadow: 0 6px 25px rgba(102, 126, 234, 0.4);
    }}

    .demo-button:hover {{ transform: translateY(-4px); box-shadow: 0 10px 35px rgba(102, 126, 234, 0.5); }}

    .footer-bottom {{
        margin-top: 1.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid rgba(255,255,255,0.1);
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
        font-size: 0.85rem;
        color: #64748b;
    }}
    .social-icons {{
        display: flex !important;
        flex-wrap: wrap;
        gap: 1rem;
        justify-content: flex-start;
    }}

    .social-icon {{
        width: 46px;
        height: 46px;
        border-radius: 50%;
        background: rgba(255,255,255,0.06);
        color: #94a3b8;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.35rem;
        transition: all 0.3s ease;
        border: 1px solid rgba(255,255,255,0.1);
    }}

    .social-icon:hover {{
        background: rgba(102, 126, 234, 0.25);
        color: #667eea;
        transform: translateY(-5px) scale(1.12);
        border-color: #667eea;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
    }}
    @media (max-width: 768px) {{
        .footer-container {{ margin: 2rem 0.5rem; padding: 2rem 1.2rem; }}
        .footer-social-section {{ flex-direction: column; text-align: center; }}
    }}
    </style>
    
    <div class="footer-container">
        <div class="footer-content">
            <!-- Contact, Trust, Grid, etc. remain same -->

            <!-- Footer Grid with FIXED LINKS -->
            <div class="footer-grid">
                <div class="footer-column">
                    <h4>🏗️ TenderAI</h4>
                    <a href="/?page=dashboard" onclick="window.location.href='/?page=dashboard'; return false;">🏠 Home</a>
                    <a href="/?page=about" onclick="window.location.href='/?page=about'; return false;">ℹ️ About Us</a>
                    <a href="/?page=features" onclick="window.location.href='/?page=features'; return false;">⚡ Features</a>
                    <a href="/?page=pricing" onclick="window.location.href='/?page=pricing'; return false;">💰 Pricing</a>
                </div>
                <div class="footer-column">
                    <h4>📚 Resources</h4>
                    <a href="/?page=knowledge_base" onclick="window.location.href='/?page=knowledge_base'; return false;">📖 Knowledge Base</a>
                    <a href="/?page=faq" onclick="window.location.href='/?page=faq'; return false;">❓ FAQ</a>
                    <a href="/?page=blog" onclick="window.location.href='/?page=blog'; return false;">📝 Blog</a>
                    <a href="/?page=support" onclick="window.location.href='/?page=support'; return false;">🆘 Support</a>
                </div>
                <div class="footer-column">
                    <h4>⚖️ Legal</h4>
                    <a href="/?page=terms" onclick="window.location.href='/?page=terms'; return false;">📋 Terms & Conditions</a>
                    <a href="/?page=privacy" onclick="window.location.href='/?page=privacy'; return false;">🔒 Privacy Policy</a>
                    <a href="/?page=cookies" onclick="window.location.href='/?page=cookies'; return false;">🍪 Cookie Policy</a>
                    <a href="/?page=gdpr" onclick="window.location.href='/?page=gdpr'; return false;">🛡️ GDPR Compliance</a>
                </div>
                <div class="footer-column">
                    <h4>📞 Contact</h4>
                    <a href="tel:+8801234567890">📞 +880 1234 567890</a>
                    <a href="mailto:sales@itenderbd.com">✉️ sales@itenderbd.com</a>
                    <a href="/?page=contact" onclick="window.location.href='/?page=contact'; return false;">📬 Contact Us</a>
                    <a href="/?page=book_demo" onclick="window.location.href='/?page=book_demo'; return false;">📅 Book a Demo</a>
                </div>
            </div>

            <!-- Social Section (unchanged) -->
            <div class="footer-social-section">
                <div>
                    <div style="color:#94a3b8; margin-bottom:0.8rem; font-weight:500;">🌐 Share TenderAI with your network</div>
                    <div class="social-icons">
                        <a href="{share_links['facebook_share']}" target="_blank" class="social-icon" title="Facebook"><i class="fab fa-facebook-f"></i></a>
                        <a href="{share_links['linkedin_share']}" target="_blank" class="social-icon" title="LinkedIn"><i class="fab fa-linkedin-in"></i></a>
                        <a href="{share_links['twitter_share']}" target="_blank" class="social-icon" title="Twitter/X"><i class="fab fa-x-twitter"></i></a>
                        <a href="{share_links['whatsapp_share']}" target="_blank" class="social-icon" title="WhatsApp"><i class="fab fa-whatsapp"></i></a>                        
                    </div>
                </div>
                <a href="/?page=book_demo" onclick="window.location.href='/?page=book_demo'; return false;" class="demo-button">🚀 Book a Demo</a>
            </div>

            <!-- Bottom -->
            <div class="footer-bottom">
                <div>© {datetime.now().year} TenderAI (BD). All rights reserved. | Bangladesh's First AI-Powered Tender Intelligence Platform</div>
                <div style="display:flex; gap:1.8rem; flex-wrap:wrap;">
                    <a href="/?page=terms" onclick="window.location.href='/?page=terms'; return false;">Terms</a>
                    <a href="/?page=privacy" onclick="window.location.href='/?page=privacy'; return false;">Privacy</a>
                    <a href="/?page=gdpr" onclick="window.location.href='/?page=gdpr'; return false;">GDPR</a>
                </div>
            </div>
        </div>
    </div>

    
    """

    st.html(footer_code)