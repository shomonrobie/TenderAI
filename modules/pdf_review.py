"""
PDF Review Module - Display extracted tender data for user confirmation
Allows editing of extracted fields before database insertion.
"""
import streamlit as st
from datetime import datetime
from utils.helpers import get_compact_css, format_currency_bd

def generate_review_html(extracted_data):
    """Generate HTML preview of extracted tender information"""

    # Format dates
    def format_date(val):
        if val and hasattr(val, 'strftime'):
            return val.strftime('%d-%b-%Y %H:%M')
        return str(val) if val else 'N/A'

    submission_deadline = format_date(extracted_data.get('submission_deadline'))
    security_valid = format_date(extracted_data.get('security_valid_upto'))
    tender_valid = format_date(extracted_data.get('tender_valid_upto'))
    pub_date = format_date(extracted_data.get('tender_publication_date'))
    opening_date = format_date(extracted_data.get('bid_opening_date'))

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

    # App ID
    app_id = extracted_data.get('app_id', '')
    html += f"""
                <div class="info-item">
                    <div class="info-label">App ID</div>
                    <div class="info-value">{app_id if app_id else '<em>Not extracted</em>'}</div>
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
    submission_deadline_display = submission_deadline if submission_deadline != 'N/A' else '<em>Not extracted</em>'
    status_class = "status-found" if submission_deadline != 'N/A' else "status-missing"
    status_text = "✓ Extracted" if submission_deadline != 'N/A' else "⚠️ Missing"
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

    # Procurement Nature
    procurement_nature = extracted_data.get('procurement_nature', '')
    html += f"""
                <div class="info-item">
                    <div class="info-label">Procurement Nature</div>
                    <div class="info-value">{procurement_nature if procurement_nature else '<em>Not extracted</em>'}</div>
                </div>
    """

    html += """
            </div>
        </div>
    """

    # Section 2: Financial Information
    html += """
        <div class="section">
            <div class="section-title">💰 Financial Information</div>
            <div class="info-grid">
    """

    tender_security = extracted_data.get('tender_security', 0)
    html += f"""
                <div class="info-item">
                    <div class="info-label">Tender Security</div>
                    <div class="info-value">{format_currency_bd(tender_security) if tender_security > 0 else '<em>Not extracted</em>'}</div>
                </div>
    """

    document_fee = extracted_data.get('document_fee', 0)
    html += f"""
                <div class="info-item">
                    <div class="info-label">Document Fee</div>
                    <div class="info-value">{format_currency_bd(document_fee) if document_fee > 0 else '<em>Not extracted</em>'}</div>
                </div>
    """

    html += """
            </div>
        </div>
    """

    # Section 3: Important Dates
    html += """
        <div class="section">
            <div class="section-title">📅 Important Dates</div>
            <div class="info-grid">
    """

    html += f"""
                <div class="info-item">
                    <div class="info-label">Publication Date</div>
                    <div class="info-value">{pub_date}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Bid Opening Date</div>
                    <div class="info-value">{opening_date}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Security Valid Up To</div>
                    <div class="info-value">{security_valid}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Tender Valid Up To</div>
                    <div class="info-value">{tender_valid}</div>
                </div>
    """

    html += """
            </div>
        </div>
    """

    # Section 4: Lot Information
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


def display_review_page(extracted_data, on_confirm_callback=None):
    """
    Display review page with extracted data and editable fields.
    Allows user to review and edit before database insertion.
    """

    # Apply compact CSS
    st.markdown(get_compact_css(), unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center; margin-bottom: 1rem;">
        <h2>📄 Review Extracted Tender Information</h2>
        <p style="color: #666;">Please verify and edit the automatically extracted information below</p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize editable data in session state
    if 'editable_tender_data' not in st.session_state:
        st.session_state.editable_tender_data = dict(extracted_data)

    editable_data = st.session_state.editable_tender_data

    # Display extracted data in editable form
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📋 Basic Information**")

        # Tender ID (editable)
        tender_id = st.text_input(
            "Tender ID *",
            value=editable_data.get('tender_id', ''),
            key="review_tender_id"
        )
        editable_data['tender_id'] = tender_id

        # App ID
        app_id = st.text_input(
            "App ID",
            value=editable_data.get('app_id', ''),
            key="review_app_id"
        )
        editable_data['app_id'] = app_id

        # Procuring Entity
        procuring_entity = st.text_input(
            "Procuring Entity *",
            value=editable_data.get('procuring_entity', ''),
            key="review_procuring_entity"
        )
        editable_data['procuring_entity'] = procuring_entity

        # Division
        divisions = ["", "Dhaka", "Chittagong", "Rajshahi", "Khulna", "Barisal", "Sylhet", "Rangpur", "Mymensingh"]
        division_index = divisions.index(editable_data.get('division', '')) if editable_data.get('division') in divisions else 0
        division = st.selectbox(
            "Division",
            divisions,
            index=division_index,
            key="review_division"
        )
        editable_data['division'] = division

    with col2:
        st.markdown("**💰 Financial Information**")

        # Official Estimate (required, may need manual entry)
        official_estimate = st.number_input(
            "Official Estimate (BDT) *",
            min_value=0.0,
            step=100000.0,
            value=float(editable_data.get('official_estimate', 0)),
            key="review_official_estimate",
            format="%0.2f"
        )
        editable_data['official_estimate'] = official_estimate

        if official_estimate <= 0:
            st.warning("⚠️ Official Estimate is required. Please enter manually.")

        # Tender Security
        tender_security = st.number_input(
            "Tender Security (BDT)",
            min_value=0.0,
            step=1000.0,
            value=float(editable_data.get('tender_security', 0)),
            key="review_tender_security",
            format="%0.2f"
        )
        editable_data['tender_security'] = tender_security

        # Document Fee
        document_fee = st.number_input(
            "Document Fee (BDT)",
            min_value=0.0,
            step=100.0,
            value=float(editable_data.get('document_fee', 0)),
            key="review_document_fee",
            format="%0.2f"
        )
        editable_data['document_fee'] = document_fee

    # Tender Title (full width)
    st.markdown("**📝 Tender Title**")
    tender_title = st.text_area(
        "Tender Title *",
        value=editable_data.get('tender_title', ''),
        height=80,
        key="review_tender_title"
    )
    editable_data['tender_title'] = tender_title

    # Important Dates
    st.markdown("**📅 Important Dates**")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Submission Deadline
        current_deadline = editable_data.get('submission_deadline')
        if current_deadline and hasattr(current_deadline, 'date'):
            deadline_default = current_deadline.date()
        else:
            deadline_default = datetime.now().date() + __import__('datetime').timedelta(days=14)

        submission_deadline = st.date_input(
            "Submission Deadline *",
            value=deadline_default,
            key="review_submission_deadline"
        )
        editable_data['submission_deadline'] = submission_deadline

    with col2:
        # Publication Date
        current_pub = editable_data.get('tender_publication_date')
        if current_pub and hasattr(current_pub, 'date'):
            pub_default = current_pub.date()
        else:
            pub_default = None

        tender_publication_date = st.date_input(
            "Publication Date",
            value=pub_default,
            key="review_publication_date"
        )
        editable_data['tender_publication_date'] = tender_publication_date

    with col3:
        # Bid Opening Date
        current_opening = editable_data.get('bid_opening_date')
        if current_opening and hasattr(current_opening, 'date'):
            opening_default = current_opening.date()
        else:
            opening_default = None

        bid_opening_date = st.date_input(
            "Bid Opening Date",
            value=opening_default,
            key="review_bid_opening_date"
        )
        editable_data['bid_opening_date'] = bid_opening_date

    # Additional fields
    with st.expander("📋 Additional Fields (Optional)"):
        col1, col2 = st.columns(2)

        with col1:
            project_code = st.text_input(
                "Project Code",
                value=editable_data.get('project_code', ''),
                key="review_project_code"
            )
            editable_data['project_code'] = project_code

            package_no = st.text_input(
                "Package No.",
                value=editable_data.get('package_no', ''),
                key="review_package_no"
            )
            editable_data['package_no'] = package_no

            procurement_nature = st.text_input(
                "Procurement Nature",
                value=editable_data.get('procurement_nature', ''),
                key="review_procurement_nature"
            )
            editable_data['procurement_nature'] = procurement_nature

        with col2:
            inviting_official_name = st.text_input(
                "Inviting Official Name",
                value=editable_data.get('inviting_official_name', ''),
                key="review_inviting_official_name"
            )
            editable_data['inviting_official_name'] = inviting_official_name

            inviting_official_designation = st.text_input(
                "Inviting Official Designation",
                value=editable_data.get('inviting_official_designation', ''),
                key="review_inviting_official_designation"
            )
            editable_data['inviting_official_designation'] = inviting_official_designation

            inviting_official_phone = st.text_input(
                "Phone No",
                value=editable_data.get('inviting_official_phone', ''),
                key="review_inviting_official_phone"
            )
            editable_data['inviting_official_phone'] = inviting_official_phone

    # Show lots if available
    lots = editable_data.get('lots', [])
    if lots:
        st.markdown("**📦 Lot Information**")
        lot_df = __import__('pandas').DataFrame(lots)
        st.dataframe(lot_df, use_container_width=True, hide_index=True)

    # Show missing fields warning
    missing_fields = []
    if not editable_data.get('tender_id'):
        missing_fields.append('Tender ID')
    if not editable_data.get('tender_title'):
        missing_fields.append('Tender Title')
    if not editable_data.get('procuring_entity'):
        missing_fields.append('Procuring Entity')
    if editable_data.get('official_estimate', 0) <= 0:
        missing_fields.append('Official Estimate')
    if not editable_data.get('submission_deadline'):
        missing_fields.append('Submission Deadline')

    if missing_fields:
        st.warning(f"⚠️ The following required fields are missing: {', '.join(missing_fields)}")

    # User action buttons
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("✏️ Edit Complete", use_container_width=True):
            st.session_state.extracted_data = editable_data
            st.session_state.pdf_data_confirmed = True
            st.rerun()

    with col2:
        if st.button("🗑️ Clear & Upload New", use_container_width=True):
            # Complete clear of PDF-related session state
            for key in ['extracted_data', 'editable_tender_data', 'skip_review', '_last_pdf_name', '_tender_pdf_upload_new', 'pdf_parsed', 'pdf_data_confirmed']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    with col3:
        if st.button("❌ Cancel", use_container_width=True):
            # Clear everything and go back
            for key in ['extracted_data', 'editable_tender_data', 'skip_review', '_last_pdf_name', '_tender_pdf_upload_new', 'pdf_parsed', 'pdf_data_confirmed']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.page = "tender_management"
            st.rerun()

    with col4:
        if st.button("✅ Confirm & Continue", use_container_width=True, type="primary"):
            if missing_fields:
                st.error(f"❌ Cannot proceed. Please fill required fields: {', '.join(missing_fields)}")
            else:
                st.session_state.extracted_data = editable_data
                st.session_state.pdf_data_confirmed = True
                if on_confirm_callback:
                    on_confirm_callback()
                st.rerun()

    return editable_data