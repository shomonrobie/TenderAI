# modules/company_knowledge_repo.py
# Complete refactored version using only CRUD methods

import streamlit as st
import pandas as pd
from datetime import datetime
from modules.rbac import can_view_dashboard, can_manage_team
from database.unified_db_manager import get_db_manager


def render_company_knowledge_repo():
    """Render the centralized company knowledge repository"""
    
    company_id = st.session_state.company_id
    db = get_db_manager()
    
    st.markdown("""
    <div class="main-header">
        <h1>🏢 Company Knowledge Repository</h1>
        <p>Centralized repository for company information, documents, and intelligence</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sub-tabs for different knowledge areas
    tabs = st.tabs([
        "📊 Overview",
        "🏢 Company Info",
        "👥 Personnel",
        "🏗️ Equipment",
        "📋 Experience",
        "💰 Financial",
        "📄 Documents",
        "🔍 Search",
        "📜 Licenses",
        "🏦 Bank Details",
        "📞 References",
        "🔄 Ongoing Works",
        "⚙️ Auto-Fill Settings"
    ])
    
    with tabs[0]:
        render_overview_tab(company_id)
    
    with tabs[1]:
        render_company_info_tab(company_id)
    
    with tabs[2]:
        render_personnel_tab(company_id)
    
    with tabs[3]:
        render_equipment_tab(company_id)
    
    with tabs[4]:
        render_experience_tab(company_id)
    
    with tabs[5]:
        render_financial_tab(company_id)
    
    with tabs[6]:
        render_documents_tab(company_id)
    
    with tabs[7]:
        render_search_tab(company_id)
    
    with tabs[8]:
        render_licenses_tab(company_id)
    
    with tabs[9]:
        render_bank_details_tab(company_id)
    
    with tabs[10]:
        render_references_tab(company_id)
    
    with tabs[11]:
        render_ongoing_works_tab(company_id)
    
    with tabs[12]:
        render_auto_fill_settings_tab(company_id)


def render_overview_tab(company_id):
    """Render overview with statistics"""
    db = get_db_manager()
    
    # Get counts using CRUD methods
    personnel = db.get_company_personnel(company_id)
    personnel_count = len(personnel) if personnel else 0
    
    equipment = db.get_company_equipment(company_id)
    equipment_count = len(equipment) if equipment else 0
    
    experiences = db.get_company_experience(company_id)
    experience_count = len(experiences) if experiences else 0
    
    financials = db.get_company_financials(company_id)
    financial_count = len(financials) if financials else 0
    
    licenses = db.get_company_licenses(company_id)
    license_count = len(licenses) if licenses else 0
    
    documents = db.get_company_documents(company_id)
    document_count = len(documents) if documents else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Personnel", personnel_count)
        st.metric("🏗️ Equipment", equipment_count)
        st.metric("📋 Experience", experience_count)
    
    with col2:
        st.metric("💰 Financial", financial_count)
        st.metric("📄 Documents", document_count)
        st.metric("📜 Licenses", license_count)
    
    # Data completeness
    st.markdown("### Data Completeness")
    
    completeness = {
        'Company Profile': db.get_company_by_id(company_id) is not None,
        'Personnel': personnel_count > 0,
        'Equipment': equipment_count > 0,
        'Experience': experience_count > 0,
        'Financial': financial_count > 0,
        'Licenses': license_count > 0,
        'Documents': document_count > 0
    }
    
    for category, is_complete in completeness.items():
        status = "✅" if is_complete else "⚠️"
        st.write(f"{status} {category}")


def render_company_info_tab(company_id):
    """Render company information tab"""
    db = get_db_manager()
    
    st.markdown("### Company Information")
    
    company = db.get_company_by_id(company_id)
    
    if not company:
        st.error("Company not found")
        return
    
    with st.form("company_info_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            company_name = st.text_input("Company Name", value=company.get('company_name', ''))
            registration_number = st.text_input("Registration Number", value=company.get('registration_number', ''))
            vat_number = st.text_input("VAT Number", value=company.get('vat_number', ''))
            tin_number = st.text_input("TIN Number", value=company.get('tin_number', ''))
            bin_number = st.text_input("BIN Number", value=company.get('bin_number', ''))
            rjsc_number = st.text_input("RJSC Number", value=company.get('rjsc_number', ''))
            phone = st.text_input("Phone", value=company.get('phone', ''))
            mobile_number = st.text_input("Mobile Number", value=company.get('mobile_number', ''))
        
        with col2:
            email = st.text_input("Email", value=company.get('email', ''))
            address = st.text_area("Address", value=company.get('address', ''))
            division = st.text_input("Division", value=company.get('division', ''))
            district = st.text_input("District", value=company.get('district', ''))
            upazila = st.text_input("Upazila", value=company.get('upazila', ''))
            post_code = st.text_input("Post Code", value=company.get('post_code', ''))
            website = st.text_input("Website", value=company.get('website', ''))
            is_individual = st.checkbox("Is Individual", value=company.get('is_individual', False))
        
        if st.form_submit_button("💾 Save Company Info"):
            data = {
                'company_name': company_name,
                'registration_number': registration_number,
                'vat_number': vat_number,
                'tin_number': tin_number,
                'bin_number': bin_number,
                'rjsc_number': rjsc_number,
                'phone': phone,
                'mobile_number': mobile_number,
                'email': email,
                'address': address,
                'division': division,
                'district': district,
                'upazila': upazila,
                'post_code': post_code,
                'website': website,
                'is_individual': is_individual
            }
            
            if db.update_company(company_id, data):
                st.success("✅ Company information saved!")
                st.rerun()
            else:
                st.error("❌ Failed to save company information")


def render_personnel_tab(company_id):
    """Render personnel management tab with all new fields"""
    db = get_db_manager()
    
    st.markdown("### Personnel Management")
    
    # Add personnel form with all fields
    with st.expander("➕ Add New Personnel", expanded=False):
        with st.form("add_personnel_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name *")
                designation = st.text_input("Designation *")
                nid_number = st.text_input("NID Number")
                phone = st.text_input("Phone")
                email = st.text_input("Email")
                date_of_birth = st.date_input("Date of Birth", value=None)
            
            with col2:
                educational_qualification = st.text_input("Educational Qualification")
                experience_years = st.number_input("Years of Experience", min_value=0, step=1)
                years_with_company = st.number_input("Years with Company", min_value=0, step=1)
                present_employer = st.text_input("Present Employer (if not employed by tenderer)")
                present_job_title = st.text_input("Present Job Title")
                is_key_personnel = st.checkbox("Key Personnel")
                is_prime_candidate = st.checkbox("Prime Candidate")
            
            if st.form_submit_button("Add Personnel"):
                if name and designation:
                    data = {
                        'name': name,
                        'designation': designation,
                        'nid_number': nid_number,
                        'phone': phone,
                        'email': email,
                        'date_of_birth': date_of_birth,
                        'educational_qualification': educational_qualification,
                        'experience_years': experience_years,
                        'years_with_company': years_with_company,
                        'present_employer': present_employer,
                        'present_job_title': present_job_title,
                        'is_key_personnel': is_key_personnel,
                        'is_prime_candidate': is_prime_candidate
                    }
                    
                    if db.add_company_personnel(company_id, data):
                        st.success(f"✅ Added {name}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add personnel")
    
    # List personnel
    personnel = db.get_company_personnel(company_id)
    
    if personnel:
        for person in personnel:
            with st.expander(f"👤 {person['name']} - {person['designation']}" + 
                           (" ⭐ Prime Candidate" if person.get('is_prime_candidate') else "") +
                           (" 🔑 Key Personnel" if person.get('is_key_personnel') else "")):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**NID:** {person.get('nid_number', 'N/A')}")
                    st.write(f"**Phone:** {person.get('phone', 'N/A')}")
                    st.write(f"**Email:** {person.get('email', 'N/A')}")
                    st.write(f"**Date of Birth:** {person.get('date_of_birth', 'N/A')}")
                with col2:
                    st.write(f"**Experience:** {person.get('experience_years', 0)} years")
                    st.write(f"**With Company:** {person.get('years_with_company', 0)} years")
                    st.write(f"**Education:** {person.get('educational_qualification', 'N/A')}")
                with col3:
                    st.write(f"**Key Personnel:** {'✅' if person.get('is_key_personnel') else '❌'}")
                    st.write(f"**Prime Candidate:** {'✅' if person.get('is_prime_candidate') else '❌'}")
                    st.write(f"**Present Employer:** {person.get('present_employer', 'N/A')}")
    else:
        st.info("No personnel added yet.")


def render_equipment_tab(company_id):
    """Render equipment management tab"""
    db = get_db_manager()
    
    st.markdown("### Equipment Inventory")
    
    with st.expander("➕ Add Equipment", expanded=False):
        with st.form("add_equipment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                equipment_name = st.text_input("Equipment Name *")
                equipment_type = st.selectbox("Type", [
                    "Excavator", "Bulldozer", "Crane", "Loader", 
                    "Dump Truck", "Concrete Mixer", "Generator", 
                    "Pump", "Compressor", "Other"
                ])
                model = st.text_input("Model")
                capacity = st.text_input("Capacity", placeholder="e.g., 10 ton, 100 HP")
            
            with col2:
                ownership_type = st.selectbox("Ownership", ["Owned", "Leased", "Rented"])
                current_status = st.selectbox("Status", ["Available", "Deployed", "Maintenance"])
            
            if st.form_submit_button("Add Equipment"):
                if equipment_name:
                    data = {
                        'equipment_name': equipment_name,
                        'equipment_type': equipment_type,
                        'model': model,
                        'capacity': capacity,
                        'ownership_type': ownership_type,
                        'current_status': current_status
                    }
                    
                    if db.add_equipment(company_id, data):
                        st.success(f"✅ Added {equipment_name}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add equipment")
    
    equipment = db.get_company_equipment(company_id)
    
    if equipment:
        for equip in equipment:
            status_icon = {
                'Available': '🟢',
                'Deployed': '🔵',
                'Maintenance': '🟡'
            }.get(equip.get('current_status', 'Available'), '⚪')
            
            with st.expander(f"{status_icon} {equip['equipment_name']} - {equip.get('model', 'N/A')}"):
                st.write(f"**Type:** {equip.get('equipment_type', 'N/A')}")
                st.write(f"**Capacity:** {equip.get('capacity', 'N/A')}")
                st.write(f"**Ownership:** {equip.get('ownership_type', 'N/A')}")
                st.write(f"**Status:** {equip.get('current_status', 'N/A')}")
    else:
        st.info("No equipment added yet.")


def render_experience_tab(company_id):
    """Render experience/projects tab with all new fields"""
    db = get_db_manager()
    
    st.markdown("### Project Experience")
    
    with st.expander("➕ Add Experience", expanded=False):
        with st.form("add_experience_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                project_name = st.text_input("Project Name *")
                procuring_entity = st.text_input("Procuring Entity *")
                contract_number = st.text_input("Contract Number")
                contract_value = st.number_input("Contract Value (BDT)", min_value=0.0, step=100000.0)
            
            with col2:
                award_date = st.date_input("Award Date")
                completion_date = st.date_input("Completion Date")
                role = st.selectbox("Role", ["Prime Contractor", "Subcontractor", "JV Partner"])
                is_completed = st.checkbox("Completed", value=True)
            
            procuring_entity_address = st.text_area("Procuring Entity Address")
            procuring_entity_contact = st.text_input("Procuring Entity Contact")
            procuring_entity_email = st.text_input("Procuring Entity Email")
            similarity_justification = st.text_area("Similarity Justification")
            
            if st.form_submit_button("Add Experience"):
                if project_name and procuring_entity:
                    data = {
                        'project_name': project_name,
                        'procuring_entity': procuring_entity,
                        'contract_number': contract_number,
                        'contract_value': contract_value,
                        'award_date': award_date,
                        'completion_date': completion_date,
                        'role': role,
                        'procuring_entity_address': procuring_entity_address,
                        'procuring_entity_contact': procuring_entity_contact,
                        'procuring_entity_email': procuring_entity_email,
                        'similarity_justification': similarity_justification,
                        'is_completed': is_completed
                    }
                    
                    if db.add_experience(company_id, data):
                        st.success(f"✅ Added {project_name}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add experience")
    
    experiences = db.get_company_experience(company_id)
    
    if experiences:
        for exp in experiences:
            with st.expander(f"📋 {exp['project_name']} - {exp.get('procuring_entity', 'N/A')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Contract Number:** {exp.get('contract_number', 'N/A')}")
                    st.write(f"**Value:** ৳{exp.get('contract_value', 0):,.2f}")
                    st.write(f"**Award Date:** {exp.get('award_date', 'N/A')}")
                    st.write(f"**Completion Date:** {exp.get('completion_date', 'N/A')}")
                with col2:
                    st.write(f"**Role:** {exp.get('role', 'N/A')}")
                    st.write(f"**Completed:** {'✅' if exp.get('is_completed') else '❌'}")
                    st.write(f"**Procuring Entity:** {exp.get('procuring_entity', 'N/A')}")
                    if exp.get('similarity_justification'):
                        st.write(f"**Similarity:** {exp.get('similarity_justification', 'N/A')[:100]}...")
    else:
        st.info("No experience records added yet.")


def render_financial_tab(company_id):
    """Render financial capacity tab with all new fields"""
    db = get_db_manager()
    
    st.markdown("### Financial Capacity")
    
    with st.expander("➕ Add Financial Record", expanded=False):
        with st.form("add_financial_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                fiscal_year = st.text_input("Fiscal Year *")
                annual_turnover = st.number_input("Annual Turnover (BDT)", min_value=0.0, step=1000000.0)
                construction_turnover = st.number_input("Construction Turnover (BDT)", min_value=0.0, step=1000000.0)
                net_worth = st.number_input("Net Worth (BDT)", min_value=0.0, step=1000000.0)
                working_capital = st.number_input("Working Capital (BDT)", min_value=0.0, step=1000000.0)
            
            with col2:
                liquid_assets = st.number_input("Liquid Assets (BDT)", min_value=0.0, step=1000000.0)
                credit_limit = st.number_input("Credit Limit (BDT)", min_value=0.0, step=1000000.0)
                bank_guarantee_limit = st.number_input("Bank Guarantee Limit (BDT)", min_value=0.0, step=1000000.0)
                is_audited = st.checkbox("Audited")
                audit_firm = st.text_input("Audit Firm" if is_audited else "Audit Firm (optional)")
            
            st.divider()
            st.markdown("### Turnover Details (for e-PW2A-3B)")
            
            col3, col4 = st.columns(2)
            with col3:
                tender_id = st.text_input("Tender ID / Ref. No.")
                received_date = st.date_input("Received Date")
            with col4:
                payment_received = st.number_input("Payment Received (BDT)", min_value=0.0, step=100000.0)
                role_in_contract = st.selectbox("Role in Contract", ["Sole", "JV Partner", "Subcontractor"])
            
            contract_name = st.text_input("Contract Name")
            
            if st.form_submit_button("Add Financial Record"):
                if fiscal_year:
                    data = {
                        'fiscal_year': fiscal_year,
                        'annual_turnover': annual_turnover,
                        'construction_turnover': construction_turnover,
                        'net_worth': net_worth,
                        'working_capital': working_capital,
                        'liquid_assets': liquid_assets,
                        'credit_limit': credit_limit,
                        'bank_guarantee_limit': bank_guarantee_limit,
                        'is_audited': is_audited,
                        'audit_firm': audit_firm,
                        'tender_id': tender_id,
                        'reference_no': tender_id,
                        'received_date': received_date,
                        'payment_received': payment_received,
                        'role_in_contract': role_in_contract,
                        'contract_name': contract_name
                    }
                    
                    if db.add_company_financial(company_id, data):
                        st.success(f"✅ Added financial record for {fiscal_year}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add financial record")
    
    financials = db.get_company_financials(company_id)
    
    if financials:
        df = pd.DataFrame(financials)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No financial records added yet.")


def render_documents_tab(company_id):
    """Render document management tab"""
    db = get_db_manager()
    
    st.markdown("### Document Management")
    
    with st.expander("📤 Upload Document", expanded=False):
        uploaded_file = st.file_uploader("Choose file", type=['pdf', 'doc', 'docx', 'jpg', 'png', 'xlsx'])
        
        if uploaded_file:
            col1, col2 = st.columns(2)
            
            with col1:
                document_name = st.text_input("Document Name", value=uploaded_file.name)
                document_type = st.selectbox("Document Type", [
                    "Trade License", "TIN Certificate", "VAT Certificate", "BIN Certificate",
                    "Audit Report", "Bank Statement", "Experience Certificate",
                    "ISO Certificate", "Contract Agreement", "Other"
                ])
            
            with col2:
                document_date = st.date_input("Document Date")
                expiry_date = st.date_input("Expiry Date (if applicable)", value=None)
            
            description = st.text_area("Description")
            
            if st.button("📤 Upload"):
                import os
                
                doc_dir = f"data/documents/{company_id}"
                os.makedirs(doc_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = "".join(c for c in document_name if c.isalnum() or c in '._-')[:50]
                file_path = f"{doc_dir}/{timestamp}_{safe_name}.{uploaded_file.name.split('.')[-1]}"
                
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                data = {
                    'document_name': document_name,
                    'document_type': document_type,
                    'file_path': file_path,
                    'file_name': uploaded_file.name,
                    'description': description,
                    'document_date': document_date,
                    'expiry_date': expiry_date,
                    'uploaded_by': st.session_state.user_id
                }
                
                if db.add_company_document(company_id, data):
                    st.success(f"✅ Uploaded {document_name}")
                    st.rerun()
                else:
                    st.error("❌ Failed to upload document")
    
    documents = db.get_company_documents(company_id)
    
    if documents:
        for doc in documents:
            with st.expander(f"📄 {doc['document_name']} - {doc['document_type']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Date:** {doc.get('document_date', 'N/A')}")
                    if doc.get('expiry_date'):
                        st.write(f"**Expiry:** {doc['expiry_date']}")
                        if doc['expiry_date'] < datetime.now().date():
                            st.error("⚠️ EXPIRED")
                
                with col2:
                    st.write(f"**Description:** {doc.get('description', 'N/A')}")
                    st.write(f"**Uploaded:** {doc.get('uploaded_at', 'N/A')}")
                
                if st.button(f"🗑️ Delete", key=f"del_doc_{doc['id']}"):
                    if db.delete_company_document(doc['id']):
                        st.success("✅ Document deleted!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete document")
    else:
        st.info("No documents uploaded yet.")


def render_licenses_tab(company_id):
    """Render licenses and registrations tab"""
    db = get_db_manager()
    
    st.markdown("### 📜 Licenses & Registrations")
    
    with st.expander("➕ Add License", expanded=False):
        with st.form("add_license_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                license_type = st.selectbox("License Type *", [
                    "Trade License", "Contractor License", "ABC License", "Electric License",
                    "Environment Clearance", "Fire License", "Import License", "Export License",
                    "ISO Certificate", "Other"
                ])
                license_number = st.text_input("License Number *")
                issuing_authority = st.text_input("Issuing Authority")
            
            with col2:
                issue_date = st.date_input("Issue Date")
                expiry_date = st.date_input("Expiry Date")
            
            if st.form_submit_button("Add License"):
                if license_type and license_number:
                    data = {
                        'license_type': license_type,
                        'license_number': license_number,
                        'issuing_authority': issuing_authority,
                        'issue_date': issue_date,
                        'expiry_date': expiry_date
                    }
                    
                    if db.add_company_license(company_id, data):
                        st.success(f"✅ Added {license_type}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add license")
    
    licenses = db.get_company_licenses(company_id)
    
    if licenses:
        for lic in licenses:
            with st.expander(f"📜 {lic['license_type']} - {lic['license_number']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Issuing Authority:** {lic.get('issuing_authority', 'N/A')}")
                    st.write(f"**Issue Date:** {lic.get('issue_date', 'N/A')}")
                with col2:
                    st.write(f"**Expiry Date:** {lic.get('expiry_date', 'N/A')}")
                    if lic.get('expiry_date'):
                        days_left = (lic['expiry_date'] - datetime.now().date()).days
                        if days_left < 0:
                            st.error("⚠️ EXPIRED")
                        elif days_left < 90:
                            st.warning(f"⚠️ Expires in {days_left} days")
    else:
        st.info("No licenses added yet.")


def render_bank_details_tab(company_id):
    """Render bank details tab for liquid assets"""
    db = get_db_manager()
    
    st.markdown("### 🏦 Bank Details (Liquid Assets)")
    
    # Get bank details - we need to query this directly since there's no CRUD method
    # But we can use the existing CRUD method if available
    # For now, let's use a direct query since we don't have a specific CRUD method
    
    with st.expander("➕ Add Bank Detail", expanded=False):
        with st.form("add_bank_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                bank_name = st.text_input("Bank Name *")
                branch_name = st.text_input("Branch Name")
                account_number = st.text_input("Account Number")
                available_amount = st.number_input("Available Amount (BDT)", min_value=0.0, step=100000.0)
            
            with col2:
                contact_person = st.text_input("Contact Person")
                contact_designation = st.text_input("Contact Designation")
                contact_mobile = st.text_input("Contact Mobile")
                contact_email = st.text_input("Contact Email")
                is_primary = st.checkbox("Primary Account")
            
            if st.form_submit_button("Add Bank Detail"):
                if bank_name:
                    # Use direct execute since we need to add to company_bank_details
                    data = {
                        'bank_name': bank_name,
                        'branch_name': branch_name,
                        'account_number': account_number,
                        'available_amount': available_amount,
                        'contact_person': contact_person,
                        'contact_designation': contact_designation,
                        'contact_mobile': contact_mobile,
                        'contact_email': contact_email,
                        'is_primary': is_primary
                    }
                    
                    # Add using direct query
                    result = db.execute("""
                        INSERT INTO company_bank_details (
                            company_id, bank_name, branch_name, account_number,
                            available_amount, contact_person, contact_designation,
                            contact_mobile, contact_email, is_primary, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        company_id,
                        data['bank_name'],
                        data['branch_name'],
                        data['account_number'],
                        data['available_amount'],
                        data['contact_person'],
                        data['contact_designation'],
                        data['contact_mobile'],
                        data['contact_email'],
                        data['is_primary'],
                        datetime.now()
                    ))
                    
                    if result > 0:
                        st.success(f"✅ Added bank details for {bank_name}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add bank details")
    
    # Get bank details
    banks = db.query(
        "SELECT * FROM company_bank_details WHERE company_id = ? ORDER BY is_primary DESC",
        (company_id,)
    )
    
    if banks:
        for bank in banks:
            with st.expander(f"🏦 {bank['bank_name']} - {bank.get('branch_name', 'N/A')}" + 
                           (" ⭐ Primary" if bank.get('is_primary') else "")):
                st.write(f"**Account:** {bank.get('account_number', 'N/A')}")
                st.write(f"**Available Amount:** ৳{bank.get('available_amount', 0):,.2f}")
                st.write(f"**Contact:** {bank.get('contact_person', 'N/A')} ({bank.get('contact_designation', 'N/A')})")
                st.write(f"**Mobile:** {bank.get('contact_mobile', 'N/A')}")
                st.write(f"**Email:** {bank.get('contact_email', 'N/A')}")
    else:
        st.info("No bank details added yet.")


def render_references_tab(company_id):
    """Render references tab (Bankers and Procuring Entities)"""
    db = get_db_manager()
    
    st.markdown("### 📞 References (Bankers & Procuring Entities)")
    
    with st.expander("➕ Add Reference", expanded=False):
        with st.form("add_reference_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                referee_name = st.text_input("Referee Name *")
                organization = st.text_input("Organization *")
                designation = st.text_input("Designation")
            
            with col2:
                mobile = st.text_input("Mobile")
                email = st.text_input("Email")
                reference_type = st.selectbox("Reference Type", ["Banker", "Procuring Entity"])
                is_primary = st.checkbox("Primary Reference")
            
            address = st.text_area("Address")
            
            if st.form_submit_button("Add Reference"):
                if referee_name and organization:
                    result = db.execute("""
                        INSERT INTO company_references (
                            company_id, referee_name, organization, designation,
                            mobile, email, reference_type, address, is_primary, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        company_id,
                        referee_name,
                        organization,
                        designation,
                        mobile,
                        email,
                        reference_type,
                        address,
                        is_primary,
                        datetime.now()
                    ))
                    
                    if result > 0:
                        st.success(f"✅ Added reference for {referee_name}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add reference")
    
    references = db.query(
        "SELECT * FROM company_references WHERE company_id = ? ORDER BY reference_type, is_primary DESC",
        (company_id,)
    )
    
    if references:
        for ref in references:
            with st.expander(f"📞 {ref['referee_name']} - {ref['organization']}" + 
                           (" ⭐ Primary" if ref.get('is_primary') else "")):
                st.write(f"**Designation:** {ref.get('designation', 'N/A')}")
                st.write(f"**Type:** {ref.get('reference_type', 'N/A')}")
                st.write(f"**Mobile:** {ref.get('mobile', 'N/A')}")
                st.write(f"**Email:** {ref.get('email', 'N/A')}")
                st.write(f"**Address:** {ref.get('address', 'N/A')}")
    else:
        st.info("No references added yet.")


def render_ongoing_works_tab(company_id):
    """Render ongoing works tab (Form e-PW2A-6A)"""
    db = get_db_manager()
    
    st.markdown("### 🔄 Ongoing Works / Current Commitment")
    
    with st.expander("➕ Add Ongoing Work", expanded=False):
        with st.form("add_ongoing_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                tender_id = st.text_input("Tender ID / Ref. No. *")
                contract_amount = st.number_input("Contract Amount (BDT)", min_value=0.0, step=100000.0)
                noa_date = st.date_input("Date of Issuance of NOA/Signing Contract")
            
            with col2:
                intended_completion_date = st.date_input("Intended Completion Date")
                procuring_entity = st.text_input("Procuring Entity *")
                organization = st.text_input("Organization")
                payment_received = st.number_input("Payment Received (BDT)", min_value=0.0, step=100000.0)
            
            if st.form_submit_button("Add Ongoing Work"):
                if tender_id and procuring_entity:
                    result = db.execute("""
                        INSERT INTO ongoing_works (
                            company_id, tender_id, reference_no, contract_amount,
                            noa_date, intended_completion_date, procuring_entity,
                            organization, payment_received, status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        company_id,
                        tender_id,
                        tender_id,  # reference_no same as tender_id
                        contract_amount,
                        noa_date,
                        intended_completion_date,
                        procuring_entity,
                        organization or procuring_entity,
                        payment_received,
                        'ongoing',
                        datetime.now()
                    ))
                    
                    if result > 0:
                        st.success(f"✅ Added ongoing work: {tender_id}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add ongoing work")
    
    works = db.query(
        "SELECT * FROM ongoing_works WHERE company_id = ? AND status = 'ongoing' ORDER BY noa_date DESC",
        (company_id,)
    )
    
    if works:
        for work in works:
            with st.expander(f"🔄 {work['tender_id']} - {work['procuring_entity']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Contract Amount:** ৳{work.get('contract_amount', 0):,.2f}")
                    st.write(f"**NOA Date:** {work.get('noa_date', 'N/A')}")
                    st.write(f"**Intended Completion:** {work.get('intended_completion_date', 'N/A')}")
                with col2:
                    st.write(f"**Payment Received:** ৳{work.get('payment_received', 0):,.2f}")
                    remaining = work.get('contract_amount', 0) - work.get('payment_received', 0)
                    st.write(f"**Remaining:** ৳{remaining:,.2f}")
                    st.write(f"**Status:** {work.get('status', 'N/A')}")
    else:
        st.info("No ongoing works added yet.")


def render_auto_fill_settings_tab(company_id):
    """Render auto-fill settings tab"""
    db = get_db_manager()
    
    st.markdown("### ⚙️ Auto-Fill Settings")
    st.caption("Configure default values for form auto-filling")
    
    # Get current settings - query directly
    settings = db.query_one(
        "SELECT * FROM company_auto_fill_settings WHERE company_id = ?",
        (company_id,)
    )
    
    with st.form("auto_fill_settings_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            auto_fill_email = st.text_input(
                "Auto-Fill Email",
                value=settings.get('auto_fill_email', '') if settings else '',
                help="Email address to use when auto-filling email fields (different from company email)"
            )
            
            default_bid_amount = st.number_input(
                "Default Bid Amount (BDT)",
                min_value=0.0,
                step=100000.0,
                value=float(settings.get('default_bid_amount', 0) or 0) if settings else 0.0,
                help="Default bid amount to pre-fill in tender forms"
            )
        
        with col2:
            default_contract_role = st.selectbox(
                "Default Contract Role",
                ['Sole', 'JV Partner', 'Subcontractor'],
                index=['Sole', 'JV Partner', 'Subcontractor'].index(
                    settings.get('default_contract_role', 'Sole')
                ) if settings and settings.get('default_contract_role') in ['Sole', 'JV Partner', 'Subcontractor'] else 0
            )
        
        if st.form_submit_button("💾 Save Auto-Fill Settings"):
            # Insert or update using direct query
            result = db.execute("""
                INSERT INTO company_auto_fill_settings (
                    company_id, auto_fill_email, default_bid_amount, default_contract_role, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (company_id) DO UPDATE 
                SET 
                    auto_fill_email = EXCLUDED.auto_fill_email,
                    default_bid_amount = EXCLUDED.default_bid_amount,
                    default_contract_role = EXCLUDED.default_contract_role,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                company_id,
                auto_fill_email,
                default_bid_amount,
                default_contract_role,
                datetime.now()
            ))
            
            if result > 0:
                st.success("✅ Auto-fill settings saved successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to save auto-fill settings")
    
    # Display current settings
    st.markdown("### Current Settings")
    
    if settings:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Auto-Fill Email", settings.get('auto_fill_email', 'Not set'))
        with col2:
            st.metric("Default Bid Amount", f"৳{settings.get('default_bid_amount', 0):,.2f}" if settings.get('default_bid_amount') else "Not set")
        with col3:
            st.metric("Default Contract Role", settings.get('default_contract_role', 'Not set'))
    else:
        st.info("No auto-fill settings configured yet.")


def render_search_tab(company_id):
    """Render AI-powered search tab"""
    db = get_db_manager()
    
    st.markdown("### 🔍 Search Knowledge Base")
    
    search_query = st.text_input("Search", placeholder="e.g., concrete mixing equipment, bridge construction experience...")
    
    if search_query:
        with st.spinner("Searching..."):
            # Search across different tables
            results = []
            
            # Search personnel
            personnel = db.get_company_personnel(company_id)
            if personnel:
                for p in personnel:
                    if search_query.lower() in p.get('name', '').lower() or \
                       search_query.lower() in p.get('designation', '').lower() or \
                       search_query.lower() in p.get('educational_qualification', '').lower():
                        results.append({
                            'source': 'personnel',
                            'id': p.get('id'),
                            'name': p.get('name'),
                            'designation': p.get('designation'),
                            'is_key_personnel': p.get('is_key_personnel')
                        })
            
            # Search equipment
            equipment = db.get_company_equipment(company_id)
            if equipment:
                for e in equipment:
                    if search_query.lower() in e.get('equipment_name', '').lower() or \
                       search_query.lower() in e.get('equipment_type', '').lower() or \
                       search_query.lower() in e.get('model', '').lower():
                        results.append({
                            'source': 'equipment',
                            'id': e.get('id'),
                            'name': e.get('equipment_name'),
                            'type': e.get('equipment_type')
                        })
            
            # Search experience
            experiences = db.get_company_experience(company_id)
            if experiences:
                for exp in experiences:
                    if search_query.lower() in exp.get('project_name', '').lower() or \
                       search_query.lower() in exp.get('procuring_entity', '').lower():
                        results.append({
                            'source': 'experience',
                            'id': exp.get('id'),
                            'name': exp.get('project_name'),
                            'client': exp.get('procuring_entity')
                        })
            
            if results:
                st.markdown(f"### Found {len(results)} results")
                
                for result in results:
                    with st.container():
                        source_type = result.get('source', 'Unknown').upper()
                        icon = {
                            'PERSONNEL': '👤',
                            'EQUIPMENT': '🏗️',
                            'EXPERIENCE': '📋'
                        }.get(source_type, '📄')
                        
                        st.markdown(f"""
                        <div style="padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 10px;">
                            <strong>{icon} {source_type}</strong>
                            <div style="margin-top: 8px;"><strong>{result.get('name', '')}</strong></div>
                            <small>{result.get('designation', result.get('type', result.get('client', '')))}</small>
                            {f"<div style='margin-top: 4px;'><span style='background: #e8f0fe; padding: 2px 8px; border-radius: 12px; font-size: 12px;'>ID: {result.get('id')}</span></div>" if result.get('id') else ""}
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No results found")