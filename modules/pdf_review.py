"""
PDF Review Module - Display extracted tender data for user confirmation
"""
import streamlit as st
from utils.helpers import get_compact_css, format_currency_bd

def generate_review_html(extracted_data):
    """Generate HTML preview of extracted tender information"""
    
    # Format dates
    submission_deadline = extracted_data.get('submission_deadline', '')
    if submission_deadline and hasattr(submission_deadline, 'strftime'):
        submission_deadline = submission_deadline.strftime('%d-%b-%Y %H:%M')
    
    security_valid = extracted_data.get('security_valid_upto', '')
    if security_valid and hasattr(security_valid, 'strftime'):
        security_valid = security_valid.strftime('%d-%b-%Y')
    
    tender_valid = extracted_data.get('tender_valid_upto', '')
    if tender_valid and hasattr(tender_valid, 'strftime'):
        tender_valid = tender_valid.strftime('%d-%b-%Y')
    
    # Create HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Tender Information Review</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f5f5f5;
                padding: 20px;
            }}
            .review-container {{
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            .review-header {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 20px;
                text-align: center;
            }}
            .review-header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .review-header p {{
                margin: 10px 0 0;
                opacity: 0.9;
            }}
            .review-content {{
                padding: 25px;
            }}
            .section {{
                margin-bottom: 25px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                overflow: hidden;
            }}
            .section-title {{
                background: #f8f9fa;
                padding: 12px 20px;
                font-weight: bold;
                font-size: 16px;
                color: #1e3c72;
                border-bottom: 2px solid #667eea;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                padding: 20px;
            }}
            .info-item {{
                display: flex;
                flex-direction: column;
            }}
            .info-label {{
                font-size: 11px;
                text-transform: uppercase;
                color: #666;
                letter-spacing: 0.5px;
                margin-bottom: 5px;
            }}
            .info-value {{
                font-size: 14px;
                font-weight: 500;
                color: #333;
                word-break: break-word;
            }}
            .full-width {{
                grid-column: span 2;
            }}
            .missing-field {{
                background-color: #fff3cd;
                border-left: 3px solid #ffc107;
                padding: 10px;
                margin: 10px 0;
            }}
            .found-field {{
                background-color: #d4edda;
                border-left: 3px solid #28a745;
                padding: 10px;
                margin: 10px 0;
            }}
            .lot-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            .lot-table th, .lot-table td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
                font-size: 12px;
            }}
            .lot-table th {{
                background-color: #f2f2f2;
                font-weight: bold;
            }}
            .status-badge {{
                display: inline-block;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            .status-found {{
                background-color: #d4edda;
                color: #155724;
            }}
            .status-missing {{
                background-color: #f8d7da;
                color: #721c24;
            }}
            .review-actions {{
                padding: 20px;
                background: #f8f9fa;
                border-top: 1px solid #e0e0e0;
                text-align: center;
            }}
            hr {{
                margin: 15px 0;
                border: none;
                border-top: 1px solid #e0e0e0;
            }}
        </style>
    </head>
    <body>
        <div class="review-container">
            <div class="review-header">
                <h1>📄 Tender Information Review</h1>
                <p>Please verify the extracted information before proceeding</p>
            </div>
            
            <div class="review-content">
    """
    
    # Check for missing required fields
    missing_fields = []
    if not extracted_data.get('tender_id'):
        missing_fields.append('Tender ID')
    if not extracted_data.get('tender_title'):
        missing_fields.append('Tender Title / Description of Works')
    if not extracted_data.get('procuring_entity'):
        missing_fields.append('Procuring Entity')
    if extracted_data.get('official_estimate', 0) <= 0:
        missing_fields.append('Official Estimate')
    if not extracted_data.get('submission_deadline'):
        missing_fields.append('Submission Deadline')
    
    if missing_fields:
        html += f"""
        <div class="missing-field">
            <strong>⚠️ Attention:</strong> The following fields could not be extracted and need to be entered manually:<br>
            {', '.join(missing_fields)}
        </div>
        <hr>
        """
    
    # Section 1: Basic Tender Information
    html += """
        <div class="section">
            <div class="section-title">📋 Basic Tender Information</div>
            <div class="info-grid">
    """
    
    # Tender ID
    tender_id = extracted_data.get('tender_id', '')
    status_class = "status-found" if tender_id else "status-missing"
    status_text = "✓ Extracted" if tender_id else "⚠️ Missing"
    html += f"""
                <div class="info-item">
                    <div class="info-label">Tender ID <span class="status-badge {status_class}">{status_text}</span></div>
                    <div class="info-value">{tender_id if tender_id else '<em>Not extracted</em>'}</div>
                </div>
    """
    
    # Tender Title
    tender_title = extracted_data.get('tender_title', '')[:200]
    status_class = "status-found" if tender_title else "status-missing"
    status_text = "✓ Extracted" if tender_title else "⚠️ Missing"
    html += f"""
                <div class="info-item full-width">
                    <div class="info-label">Tender Title <span class="status-badge {status_class}">{status_text}</span></div>
                    <div class="info-value">{tender_title if tender_title else '<em>Not extracted</em>'}</div>
                </div>
    """
    
    # Procuring Entity
    procuring_entity = extracted_data.get('procuring_entity', '')
    status_class = "status-found" if procuring_entity else "status-missing"
    status_text = "✓ Extracted" if procuring_entity else "⚠️ Missing"
    html += f"""
                <div class="info-item">
                    <div class="info-label">Procuring Entity <span class="status-badge {status_class}">{status_text}</span></div>
                    <div class="info-value">{procuring_entity if procuring_entity else '<em>Not extracted</em>'}</div>
                </div>
    """
    
    # Official Estimate
    official_estimate = extracted_data.get('official_estimate', 0)
    status_class = "status-found" if official_estimate > 0 else "status-missing"
    status_text = "✓ Extracted" if official_estimate > 0 else "⚠️ Missing"
    estimate_display = format_currency_bd(official_estimate) if official_estimate > 0 else '<em>Not extracted</em>'
    html += f"""
                <div class="info-item">
                    <div class="info-label">Official Estimate <span class="status-badge {status_class}">{status_text}</span></div>
                    <div class="info-value">{estimate_display}</div>
                </div>
    """
    
    # Submission Deadline
    submission_deadline_display = submission_deadline if submission_deadline else '<em>Not extracted</em>'
    status_class = "status-found" if submission_deadline else "status-missing"
    status_text = "✓ Extracted" if submission_deadline else "⚠️ Missing"
    html += f"""
                <div class="info-item">
                    <div class="info-label">Submission Deadline <span class="status-badge {status_class}">{status_text}</span></div>
                    <div class="info-value">{submission_deadline_display}</div>
                </div>
    """
    
    # Division
    division = extracted_data.get('division', '')
    html += f"""
                <div class="info-item">
                    <div class="info-label">Division</div>
                    <div class="info-value">{division if division else '<em>Not extracted</em>'}</div>
                </div>
    """
    
    # Procurement Type
    procurement_type = extracted_data.get('procurement_type', '')
    html += f"""
                <div class="info-item">
                    <div class="info-label">Procurement Type</div>
                    <div class="info-value">{procurement_type if procurement_type else '<em>Not extracted</em>'}</div>
                </div>
    """
    
    html += """
            </div>
        </div>
    """
    
    # Section 2: Financial Information
    if extracted_data.get('tender_security') or extracted_data.get('document_fee'):
        html += """
        <div class="section">
            <div class="section-title">💰 Financial Information</div>
            <div class="info-grid">
        """
        
        tender_security = extracted_data.get('tender_security', 0)
        if tender_security > 0:
            html += f"""
                <div class="info-item">
                    <div class="info-label">Tender Security</div>
                    <div class="info-value">{format_currency_bd(tender_security)}</div>
                </div>
            """
        
        document_fee = extracted_data.get('document_fee', 0)
        if document_fee > 0:
            html += f"""
                <div class="info-item">
                    <div class="info-label">Document Fee</div>
                    <div class="info-value">{format_currency_bd(document_fee)}</div>
                </div>
            """
        
        html += """
            </div>
        </div>
        """
    
    # Section 3: Lot Information
    lots = extracted_data.get('lots', [])
    if lots:
        html += """
        <div class="section">
            <div class="section-title">📦 Lot Information</div>
            <div class="info-grid">
                <div class="info-item full-width">
                    <table class="lot-table">
                        <thead>
                            <tr><th>Lot No.</th><th>Description</th><th>Location</th><th>Security (BDT)</th><th>Start Date</th><th>Completion Date</th></tr>
                        </thead>
                        <tbody>
        """
        for lot in lots:
            html += f"""
                            <tr>
                                <td>{lot.get('lot_no', '')}</td>
                                <td>{lot.get('identification', '')[:50]}</td>
                                <td>{lot.get('location', '')}</td>
                                <td>{format_currency_bd(lot.get('security_amount', 0))}</td>
                                <td>{lot.get('start_date', '')}</td>
                                <td>{lot.get('completion_date', '')}</td>
                            </tr>
            """
        html += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """
    
    html += """
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def display_review_page(extracted_data, on_confirm_callback):
    """Display review page with extracted data"""
    
    # Apply compact CSS
    st.markdown(get_compact_css(), unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 1rem;">
        <h2>📄 Review Extracted Tender Information</h2>
        <p style="color: #666;">Please verify the automatically extracted information below</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Display extracted data in a structured way
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📋 Basic Information**")
        st.info(f"""
        - **Tender ID:** {extracted_data.get('tender_id', 'N/A')}
        - **Procuring Entity:** {extracted_data.get('procuring_entity', 'N/A')}
        - **Division:** {extracted_data.get('division', 'N/A')}
        - **Procurement Type:** {extracted_data.get('procurement_type', 'N/A')}
        """)
    
    with col2:
        st.markdown("**💰 Financial Information**")
        st.info(f"""
        - **Official Estimate:** {format_currency_bd(extracted_data.get('official_estimate', 0))}
        - **Tender Security:** {format_currency_bd(extracted_data.get('tender_security', 0))}
        - **Document Fee:** {format_currency_bd(extracted_data.get('document_fee', 0))}
        """)
    
    st.markdown("**📝 Tender Title**")
    st.info(extracted_data.get('tender_title', 'N/A')[:200])
    
    st.markdown("**📅 Important Dates**")
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"""
        - **Submission Deadline:** {extracted_data.get('submission_deadline', 'N/A')}
        - **Publication Date:** {extracted_data.get('tender_publication_date', 'N/A')}
        - **Bid Opening Date:** {extracted_data.get('bid_opening_date', 'N/A')}
        """)
    with col2:
        st.info(f"""
        - **Document Selling End:** {extracted_data.get('document_selling_end_date', 'N/A')}
        - **Security Valid Upto:** {extracted_data.get('security_valid_upto', 'N/A')}
        - **Tender Valid Upto:** {extracted_data.get('tender_valid_upto', 'N/A')}
        """)
    
    # Show lots if available
    lots = extracted_data.get('lots', [])
    if lots:
        st.markdown("**📦 Lot Information**")
        lot_df = pd.DataFrame(lots)
        st.dataframe(lot_df, use_container_width=True, hide_index=True)
    
    # Show missing fields warning
    missing_fields = []
    if not extracted_data.get('tender_id'):
        missing_fields.append('Tender ID')
    if not extracted_data.get('tender_title'):
        missing_fields.append('Tender Title')
    if not extracted_data.get('procuring_entity'):
        missing_fields.append('Procuring Entity')
    if not extracted_data.get('tender_security'):
        missing_fields.append('Tender Security')
    if extracted_data.get('official_estimate', 0) <= 0:
        missing_fields.append('Official Estimate')
    if extracted_data.get('official_estimate', 0) <= 0:
        st.warning("⚠️ Official Estimate was not found in the PDF. Please enter manually:")
        official_estimate = st.number_input("Official Estimate (BDT)", min_value=0.0, step=10000.0, format="%0.3f")
        if official_estimate > 0:
            extracted_data['official_estimate'] = official_estimate

    if missing_fields:
        st.warning(f"⚠️ The following required fields are missing and need to be entered: {', '.join(missing_fields)}")
    
    # User action buttons
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("✏️ Edit Manually", use_container_width=True):
            st.session_state.skip_review = True
            st.rerun()

    with col2:
        if st.button("🗑️ Clear & Upload New", use_container_width=True):
            # Complete clear of PDF-related session state
            for key in ['extracted_data', 'skip_review', '_last_pdf_name', '_tender_pdf_upload_new']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    with col3:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear everything and go back
            for key in ['extracted_data', 'skip_review', '_last_pdf_name', '_tender_pdf_upload_new']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    with col4:
        if st.button("✅ Confirm & Continue", use_container_width=True, type="primary"):
            on_confirm_callback()
