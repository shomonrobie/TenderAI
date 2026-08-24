# _pages/gdpr.py

import streamlit as st

def show():
    """GDPR Compliance Page"""
    
    st.markdown("""
    <style>
    .gdpr-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 1rem;
    }
    .gdpr-highlight {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
        border-left: 4px solid #667eea;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .gdpr-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 2.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
            🔒 GDPR Compliance
        </h1>
        <p style="color: #64748b; font-size: 1.1rem;">Your Data Privacy & Protection Rights</p>
        <span class="gdpr-badge">GDPR Compliant</span>
        <span class="gdpr-badge" style="margin-left: 0.5rem;">Data Protection</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("""
    <div class="gdpr-container">
        <h2>📋 GDPR Overview</h2>
        <p>We are committed to protecting your personal data and complying with the General Data Protection Regulation (GDPR) (EU) 2016/679. This page outlines your rights and how we protect your data.</p>
        
        <div class="gdpr-highlight">
            <strong>Data Protection Officer (DPO):</strong><br>
            📧 dpo@itenderbd.com<br>
            📞 +880 1234 567890
        </div>
        
        <h2>🛡️ Your Rights Under GDPR</h2>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1rem 0;">
            <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                <h4>1️⃣ Right to Access</h4>
                <p style="color: #94a3b8; font-size: 0.9rem;">Request a copy of your personal data</p>
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                <h4>2️⃣ Right to Rectification</h4>
                <p style="color: #94a3b8; font-size: 0.9rem;">Correct inaccurate or incomplete data</p>
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                <h4>3️⃣ Right to Erasure</h4>
                <p style="color: #94a3b8; font-size: 0.9rem;">Request deletion of your data (right to be forgotten)</p>
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                <h4>4️⃣ Right to Restrict Processing</h4>
                <p style="color: #94a3b8; font-size: 0.9rem;">Limit how we use your data</p>
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                <h4>5️⃣ Right to Data Portability</h4>
                <p style="color: #94a3b8; font-size: 0.9rem;">Receive your data in a portable format</p>
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                <h4>6️⃣ Right to Object</h4>
                <p style="color: #94a3b8; font-size: 0.9rem;">Object to data processing for marketing</p>
            </div>
        </div>
        
        <h2>🔐 Data Protection Measures</h2>
        
        <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
            <h4>Technical Measures</h4>
            <ul style="color: #94a3b8;">
                <li>SSL/TLS encryption for all data in transit</li>
                <li>Passwords encrypted using bcrypt</li>
                <li>Role-based access control</li>
                <li>Comprehensive audit logging</li>
                <li>Regular security assessments</li>
            </ul>
            
            <h4>Organizational Measures</h4>
            <ul style="color: #94a3b8;">
                <li>GDPR-compliant data processing agreements</li>
                <li>Staff data protection training</li>
                <li>Data protection impact assessments</li>
                <li>Incident response procedures</li>
                <li>Data minimization principles</li>
            </ul>
        </div>
        
        <h2>📊 Data Retention</h2>
        <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
            <table style="width: 100%; color: #94a3b8; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #2a2a35;">
                    <th style="text-align: left; padding: 0.5rem;">Data Type</th>
                    <th style="text-align: left; padding: 0.5rem;">Retention Period</th>
                </tr>
                <tr style="border-bottom: 1px solid #2a2a35;">
                    <td style="padding: 0.5rem;">Account Information</td>
                    <td style="padding: 0.5rem;">Active account + 12 months</td>
                </tr>
                <tr style="border-bottom: 1px solid #2a2a35;">
                    <td style="padding: 0.5rem;">Tender Analysis</td>
                    <td style="padding: 0.5rem;">7 years (audit trail)</td>
                </tr>
                <tr style="border-bottom: 1px solid #2a2a35;">
                    <td style="padding: 0.5rem;">Payment Records</td>
                    <td style="padding: 0.5rem;">7 years (legal requirement)</td>
                </tr>
                <tr>
                    <td style="padding: 0.5rem;">Activity Logs</td>
                    <td style="padding: 0.5rem;">2 years</td>
                </tr>
            </table>
        </div>
        
        <h2>📝 Data Processing Agreements</h2>
        <p style="color: #94a3b8;">We have DPAs with all our data processors, including:</p>
        <ul style="color: #94a3b8;">
            <li>Cloud hosting providers (AWS, Azure)</li>
            <li>Analytics providers (Google Analytics)</li>
            <li>Payment processors (SSLCommerz, bKash)</li>
            <li>Email service providers (SendGrid)</li>
        </ul>
        
        <h2>📞 Contact Us</h2>
        <div style="background: rgba(255,255,255,0.03); padding: 1rem; border-radius: 8px; border-left: 4px solid #667eea; margin: 1rem 0;">
            <p><strong>Data Protection Officer:</strong><br>
            📧 dpo@itenderbd.com<br>
            📞 +880 1234 567890</p>
            <p><strong>Privacy Team:</strong><br>
            📧 privacy@itenderbd.com</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
    from modules.footer import render_footer
    render_footer()        