"""
Autofill Data Management with Custom Field Support
Complete company data management for e-GP bids with auto-fill capabilities
"""
import streamlit as st
import pandas as pd
from datetime import datetime, date
import json
import os
from database.unified_db_manager import get_db_manager


def get_effective_company_id():
    """Get effective company_id for the current user"""
    db = get_db_manager()
    
    # If user has company_id in session, use it
    if st.session_state.get('company_id'):
        return st.session_state.company_id
    
    # If user is individual, create or get their company
    if st.session_state.get('user_role') == 'individual':
        user_id = st.session_state.get('user_id')
        if user_id:
            # Get user from database
            user = db.get_user_by_id(user_id)
            if user and user.get('company_id'):
                # User already has a company
                st.session_state.company_id = user['company_id']
                return user['company_id']
            
            # User doesn't have a company - create one
            full_name = st.session_state.get('full_name', 'Individual')
            company_name = f"{full_name} - Individual"
            
            # Check if company already exists for this user
            existing = db.query_one(
                "SELECT id FROM companies WHERE company_name = ? AND is_individual = true",
                (company_name,)
            )
            
            if existing:
                company_id = existing['id']
            else:
                # ✅ Create new company using direct SQL
                db.execute("""
                    INSERT INTO companies (company_name, is_individual, is_active, status, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (company_name, True, True, 'active'))
                
                # Get the company_id
                company_result = db.query_one(
                    "SELECT id FROM companies WHERE company_name = ? AND is_individual = true",
                    (company_name,)
                )
                company_id = company_result['id'] if company_result else None
                
                # Create company profile
                if company_id:
                    db.execute("""
                        INSERT INTO company_profile (company_id, legal_name, created_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    """, (company_id, full_name))
            
            if company_id:
                # ✅ Update user with company_id using the correct method
                db.update_user(user_id, {'company_id': company_id})
                st.session_state.company_id = company_id
                return company_id
    
    return None


def show():
    """Autofill Data Management - Complete company data for e-GP bids"""
    
    # Check access
    if st.session_state.user_role not in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst', 'individual']:
        st.error("🔒 Access denied. Company access required.")
        return
    
    # ✅ Get effective company_id
    company_id = get_effective_company_id()
    
    if not company_id:
        st.warning("⚠️ No company found. Please contact support.")
        return
    
    # Store in session for consistency
    st.session_state.company_id = company_id
    
    st.markdown("""
    <div class="main-header">
        <h1>🏢 Autofill Data Management</h1>
        <p>Manage all company information for e-GP tender submissions</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🏢 Basic Info",
        "📜 Licenses & Registrations",
        "💰 Financial Info",
        "👥 Key Personnel",
        "🏗️ Equipment",
        "📋 Experience",
        "📄 Documents",
        "🔧 Field Mappings"
    ])
    
    with tab1:
        render_basic_info(company_id)
    
    with tab2:
        render_licenses_registrations(company_id)
    
    with tab3:
        render_financial_info(company_id)
    
    with tab4:
        render_key_personnel(company_id)
    
    with tab5:
        render_equipment(company_id)
    
    with tab6:
        render_experience(company_id)
    
    with tab7:
        render_documents(company_id)
    
    with tab8:
        render_field_mappings(company_id)


def render_basic_info(company_id):
    """Render basic company information section with field mapping integration"""
    st.markdown("### 🏢 Basic Information")
    
    db = get_db_manager()
    company = db.get_company_by_id(company_id)
    
    if not company:
        st.error(f"Company with ID {company_id} not found")
        return
    
    # Get field mappings for basic info
    mappings = db.get_field_mappings(company_id, 'basic_info')
    
    col1, col2 = st.columns(2)
    
    # Display company info with mapping indicators
    with col1:
        display_mapped_field(db, "Company Name", company.get('company_name', 'N/A'), 'company_name', mappings)
        display_mapped_field(db, "Email", company.get('email', 'N/A'), 'email', mappings)
        display_mapped_field(db, "Phone", company.get('phone', 'N/A'), 'phone', mappings)
        display_mapped_field(db, "Mobile", company.get('mobile_number', 'N/A'), 'mobile_number', mappings)
        display_mapped_field(db, "Registration No", company.get('registration_number', 'N/A'), 'registration_number', mappings)
    
    with col2:
        display_mapped_field(db, "VAT Number", company.get('vat_number', 'N/A'), 'vat_number', mappings)
        display_mapped_field(db, "TIN Number", company.get('tin_number', 'N/A'), 'tin_number', mappings)
        display_mapped_field(db, "BIN Number", company.get('bin_number', 'N/A'), 'bin_number', mappings)
        display_mapped_field(db, "Division", company.get('division', 'N/A'), 'division', mappings)
        display_mapped_field(db, "District", company.get('district', 'N/A'), 'district', mappings)
        display_mapped_field(db, "Address", company.get('address', 'N/A'), 'address', mappings)
        display_mapped_field(db, "Website", company.get('website', 'N/A'), 'website', mappings)
    
    # Quick auto-fill test button
    if st.button("🧪 Test Auto-Fill for Basic Info"):
        test_auto_fill(db, company_id, 'basic_info')
    
    # Edit button
    if st.button("✏️ Edit Basic Information"):
        st.session_state.editing_basic_info = True
        st.rerun()
    
    # Edit form
    if st.session_state.get('editing_basic_info', False):
        with st.form("edit_basic_info_form"):
            new_company_name = st.text_input("Company Name", value=company.get('company_name', ''))
            new_email = st.text_input("Email", value=company.get('email', ''))
            new_phone = st.text_input("Phone", value=company.get('phone', ''))
            new_mobile = st.text_input("Mobile Number", value=company.get('mobile_number', ''))
            new_address = st.text_area("Address", value=company.get('address', ''))
            new_division = st.text_input("Division", value=company.get('division', ''))
            new_district = st.text_input("District", value=company.get('district', ''))
            new_registration = st.text_input("Registration Number", value=company.get('registration_number', ''))
            new_vat = st.text_input("VAT Number", value=company.get('vat_number', ''))
            new_tin = st.text_input("TIN Number", value=company.get('tin_number', ''))
            new_bin = st.text_input("BIN Number", value=company.get('bin_number', ''))
            new_website = st.text_input("Website", value=company.get('website', ''))
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Save Changes"):
                    data = {
                        'company_name': new_company_name,
                        'email': new_email,
                        'phone': new_phone,
                        'mobile_number': new_mobile,
                        'address': new_address,
                        'division': new_division,
                        'district': new_district,
                        'registration_number': new_registration,
                        'vat_number': new_vat,
                        'tin_number': new_tin,
                        'bin_number': new_bin,
                        'website': new_website
                    }
                    
                    if db.update_company(company_id, data):
                        st.success("✅ Company information updated successfully!")
                        st.session_state.editing_basic_info = False
                        st.rerun()
                    else:
                        st.error("❌ Failed to update company information")
            
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state.editing_basic_info = False
                    st.rerun()


def render_licenses_registrations(company_id):
    """Manage licenses and registrations with field mapping"""
    st.markdown("### 📜 Licenses & Registrations")
    st.caption("Add trade licenses, certificates, and registrations")
    
    db = get_db_manager()
    licenses = db.get_company_licenses(company_id)
    mappings = db.get_field_mappings(company_id, 'licenses')
    
    # Display mapping info
    if mappings:
        with st.expander("🔧 Field Mappings for Licenses", expanded=False):
            for m in mappings:
                st.write(f"**{m['field_label']}** → `{m['source_table']}.{m['source_column']}`")
    
    # Add new license
    with st.expander("➕ Add New License / Registration", expanded=False):
        with st.form("add_license_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                license_type = st.selectbox(
                    "License Type *",
                    ["Trade License", "Contractor License", "ABC License", "Electric License", 
                     "Environment Clearance", "Fire License", "Import License", "Export License", 
                     "ISO Certificate", "Other"]
                )
                license_number = st.text_input("License Number *")
                issuing_authority = st.text_input("Issuing Authority")
            
            with col2:
                issue_date = st.date_input("Issue Date")
                expiry_date = st.date_input("Expiry Date")
            
            submitted = st.form_submit_button("Add License")
            
            if submitted and license_type and license_number:
                data = {
                    'license_type': license_type,
                    'license_number': license_number,
                    'issuing_authority': issuing_authority,
                    'issue_date': issue_date,
                    'expiry_date': expiry_date
                }
                
                if db.add_company_license(company_id, data):
                    st.success(f"✅ {license_type} added successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to add license")
    
    # Display existing licenses
    if licenses:
        st.markdown("### 📋 Existing Licenses")
        
        for license_item in licenses:
            with st.expander(f"📜 {license_item['license_type']} - {license_item['license_number']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**License Number:** {license_item['license_number']}")
                    st.write(f"**Issuing Authority:** {license_item.get('issuing_authority', 'N/A')}")
                    # Show mapping if exists
                    show_field_mapping_hint('license_type', license_item['license_type'], mappings)
                
                with col2:
                    st.write(f"**Issue Date:** {license_item.get('issue_date', 'N/A')}")
                    st.write(f"**Expiry Date:** {license_item.get('expiry_date', 'N/A')}")
                    if license_item.get('expiry_date'):
                        days_left = (license_item['expiry_date'] - datetime.now().date()).days
                        if days_left < 0:
                            st.error("⚠️ EXPIRED")
                        elif days_left < 90:
                            st.warning(f"⚠️ Expires in {days_left} days")
                
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button("🗑️ Delete", key=f"del_license_{license_item['id']}"):
                        if db.delete_license(license_item['id']):
                            st.success("✅ License deleted successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete license")
    else:
        st.info("No licenses added yet. Add your trade license and other registrations.")


def render_financial_info(company_id):
    """Financial information with field mapping"""
    st.markdown("### 💰 Financial Information")
    st.caption("Financial data for bid capacity calculation")
    
    db = get_db_manager()
    financials = db.get_company_financials(company_id)
    mappings = db.get_field_mappings(company_id, 'financial')
    
    # Display mapping info
    if mappings:
        with st.expander("🔧 Field Mappings for Financial Data", expanded=False):
            for m in mappings:
                st.write(f"**{m['field_label']}** → `{m['source_table']}.{m['source_column']}`")
    
    # Quick auto-fill for financial fields
    if st.button("💰 Auto-Fill Financial Data"):
        fill_financial_data(db, company_id, financials, mappings)
    
    # Add new financial record
    with st.expander("➕ Add Financial Record", expanded=False):
        with st.form("add_financial_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                fiscal_year = st.text_input("Fiscal Year *", placeholder="2023-2024")
                annual_turnover = st.number_input("Annual Turnover (BDT)", min_value=0.0, step=100000.0, format="%.2f")
                construction_turnover = st.number_input("Construction Turnover (BDT)", min_value=0.0, step=100000.0, format="%.2f")
                net_worth = st.number_input("Net Worth (BDT)", min_value=0.0, step=100000.0, format="%.2f")
            
            with col2:
                working_capital = st.number_input("Working Capital (BDT)", min_value=0.0, step=100000.0, format="%.2f")
                liquid_assets = st.number_input("Liquid Assets (BDT)", min_value=0.0, step=100000.0, format="%.2f")
                credit_limit = st.number_input("Credit Limit (BDT)", min_value=0.0, step=100000.0, format="%.2f")
                bank_guarantee_limit = st.number_input("Bank Guarantee Limit (BDT)", min_value=0.0, step=100000.0, format="%.2f")
            
            is_audited = st.checkbox("Audited Financials")
            audit_firm = st.text_input("Audit Firm Name" if is_audited else "Audit Firm (optional)")
            
            submitted = st.form_submit_button("Add Financial Record")
            
            if submitted and fiscal_year:
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
                    'audit_firm': audit_firm
                }
                
                if db.add_company_financial(company_id, data):
                    st.success(f"✅ Financial record for {fiscal_year} added!")
                    st.rerun()
                else:
                    st.error("❌ Failed to add financial record")
    
    # Display financial records
    if financials:
        st.markdown("### 📊 Financial History")
        
        financial_data = []
        for f in financials:
            financial_data.append({
                'Fiscal Year': f['fiscal_year'],
                'Annual Turnover': f"৳{f['annual_turnover']:,.0f}" if f['annual_turnover'] else "N/A",
                'Construction Turnover': f"৳{f['construction_turnover']:,.0f}" if f['construction_turnover'] else "N/A",
                'Net Worth': f"৳{f['net_worth']:,.0f}" if f['net_worth'] else "N/A",
                'Working Capital': f"৳{f['working_capital']:,.0f}" if f['working_capital'] else "N/A",
                'Audited': "✅" if f['is_audited'] else "❌",
                'ID': f['id']
            })
        
        df = pd.DataFrame(financial_data)
        st.dataframe(df.drop(columns=['ID']), use_container_width=True, hide_index=True)
        
        # Delete option
        for f in financials:
            if st.button(f"🗑️ Delete {f['fiscal_year']}", key=f"del_fin_{f['id']}"):
                if db.delete_company_financial(f['id']):
                    st.success("✅ Financial record deleted successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to delete financial record")
    else:
        st.info("No financial records added. Add your financial data for bid capacity calculation.")


def render_key_personnel(company_id):
    """Key personnel management with field mapping"""
    st.markdown("### 👥 Key Personnel")
    st.caption("Add key personnel for tender submissions")
    
    db = get_db_manager()
    personnel = db.get_company_personnel(company_id)
    mappings = db.get_field_mappings(company_id, 'personnel')
    
    # Display mapping info
    if mappings:
        with st.expander("🔧 Field Mappings for Personnel", expanded=False):
            for m in mappings:
                st.write(f"**{m['field_label']}** → `{m['source_table']}.{m['source_column']}`")
    
    # Add new personnel
    with st.expander("➕ Add Personnel", expanded=False):
        with st.form("add_personnel_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name *")
                designation = st.text_input("Designation *")
                nid_number = st.text_input("NID Number")
                date_of_birth = st.date_input("Date of Birth")
            
            with col2:
                phone = st.text_input("Phone")
                email = st.text_input("Email")
                experience_years = st.number_input("Years of Experience", min_value=0, max_value=50, step=1)
                years_with_company = st.number_input("Years with Company", min_value=0, max_value=50, step=1)
            
            educational_qualification = st.text_area("Educational Qualification")
            present_employer = st.text_input("Present Employer")
            present_job_title = st.text_input("Present Job Title")
            is_key_personnel = st.checkbox("Key Personnel (for tender evaluation)")
            is_prime_candidate = st.checkbox("Prime Candidate")
            
            submitted = st.form_submit_button("Add Personnel")
            
            if submitted and name and designation:
                data = {
                    'name': name,
                    'designation': designation,
                    'nid_number': nid_number,
                    'phone': phone,
                    'email': email,
                    'educational_qualification': educational_qualification,
                    'experience_years': experience_years,
                    'is_key_personnel': is_key_personnel,
                    'date_of_birth': date_of_birth,
                    'years_with_company': years_with_company,
                    'present_employer': present_employer,
                    'present_job_title': present_job_title,
                    'is_prime_candidate': is_prime_candidate
                }
                
                if db.add_company_personnel(company_id, data):
                    st.success(f"✅ {name} added successfully!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Failed to add personnel")
    
    # Display personnel
    if personnel:
        st.markdown("### 📋 Personnel List")
        
        for p in personnel:
            with st.expander(f"👤 {p['name']} - {p['designation']}" + (" ⭐ Key Personnel" if p['is_key_personnel'] else "")):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**NID:** {p.get('nid_number', 'N/A')}")
                    st.write(f"**Phone:** {p.get('phone', 'N/A')}")
                    st.write(f"**Email:** {p.get('email', 'N/A')}")
                    st.write(f"**Date of Birth:** {p.get('date_of_birth', 'N/A')}")
                
                with col2:
                    st.write(f"**Experience:** {p.get('experience_years', 0)} years")
                    st.write(f"**Years with Company:** {p.get('years_with_company', 0)} years")
                    st.write(f"**Education:** {p.get('educational_qualification', 'N/A')}")
                    st.write(f"**Prime Candidate:** {'✅' if p.get('is_prime_candidate') else '❌'}")
                
                if p.get('present_employer'):
                    st.write(f"**Present Employer:** {p.get('present_employer', 'N/A')}")
                    st.write(f"**Job Title:** {p.get('present_job_title', 'N/A')}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"✏️ Edit", key=f"edit_person_{p['id']}"):
                        st.session_state.edit_personnel = p['id']
                        st.rerun()
                with col2:
                    if st.button(f"🧪 Test Auto-Fill", key=f"test_person_{p['id']}"):
                        test_personnel_auto_fill(db, p, mappings)
                with col3:
                    if st.button(f"🗑️ Delete", key=f"del_person_{p['id']}"):
                        if db.delete_company_personnel(p['id']):
                            st.success("✅ Personnel deleted successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete personnel")
                
                # Edit form if this person is being edited
                if st.session_state.get('edit_personnel') == p['id']:
                    render_personnel_edit_form(p, db)
    else:
        st.info("No personnel added. Add your key personnel for tender submissions.")


def render_personnel_edit_form(person, db):
    """Render personnel edit form"""
    with st.form(f"edit_personnel_form_{person['id']}"):
        col1, col2 = st.columns(2)
        
        with col1:
            edit_name = st.text_input("Full Name", value=person['name'])
            edit_designation = st.text_input("Designation", value=person['designation'])
            edit_nid = st.text_input("NID Number", value=person.get('nid_number', ''))
            edit_dob = st.date_input("Date of Birth", value=person.get('date_of_birth') or datetime.now().date())
        
        with col2:
            edit_phone = st.text_input("Phone", value=person.get('phone', ''))
            edit_email = st.text_input("Email", value=person.get('email', ''))
            edit_experience = st.number_input(
                "Years of Experience", 
                min_value=0, 
                max_value=50, 
                step=1, 
                value=person.get('experience_years', 0)
            )
            edit_years_company = st.number_input(
                "Years with Company",
                min_value=0,
                max_value=50,
                step=1,
                value=person.get('years_with_company', 0)
            )
        
        edit_education = st.text_area(
            "Educational Qualification", 
            value=person.get('educational_qualification', '')
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            edit_key_personnel = st.checkbox("Key Personnel", value=person.get('is_key_personnel', False))
        with col2:
            edit_prime_candidate = st.checkbox("Prime Candidate", value=person.get('is_prime_candidate', False))
        
        edit_present_employer = st.text_input("Present Employer", value=person.get('present_employer', ''))
        edit_present_job_title = st.text_input("Present Job Title", value=person.get('present_job_title', ''))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Save Changes"):
                data = {
                    'name': edit_name,
                    'designation': edit_designation,
                    'nid_number': edit_nid,
                    'phone': edit_phone,
                    'email': edit_email,
                    'educational_qualification': edit_education,
                    'experience_years': edit_experience,
                    'is_key_personnel': edit_key_personnel,
                    'date_of_birth': edit_dob,
                    'years_with_company': edit_years_company,
                    'present_employer': edit_present_employer,
                    'present_job_title': edit_present_job_title,
                    'is_prime_candidate': edit_prime_candidate
                }
                
                if db.update_company_personnel(person['id'], data):
                    st.success("✅ Personnel updated successfully!")
                    st.session_state.edit_personnel = None
                    st.rerun()
                else:
                    st.error("❌ Failed to update personnel")
        
        with col2:
            if st.form_submit_button("Cancel"):
                st.session_state.edit_personnel = None
                st.rerun()


def render_equipment(company_id):
    """Equipment inventory management with field mapping"""
    st.markdown("### 🏗️ Equipment Inventory")
    st.caption("Add equipment for tender submissions")
    
    db = get_db_manager()
    
    # ✅ Try to get equipment using the correct method
    try:
        equipment_list = db.get_equipment_by_company(company_id)
    except AttributeError:
        # Fallback: try alternative method names
        try:
            equipment_list = db.get_company_equipment(company_id)
        except AttributeError:
            equipment_list = []
            st.warning("Equipment management is not fully configured. Please contact support.")
    
    mappings = db.get_field_mappings(company_id, 'equipment')
    
    # Display mapping info
    if mappings:
        with st.expander("🔧 Field Mappings for Equipment", expanded=False):
            for m in mappings:
                st.write(f"**{m['field_label']}** → `{m['source_table']}.{m['source_column']}`")
    
    # Add new equipment
    with st.expander("➕ Add Equipment", expanded=False):
        with st.form("add_equipment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                equipment_name = st.text_input("Equipment Name *")
                equipment_type = st.selectbox("Equipment Type", 
                    ["Excavator", "Bulldozer", "Crane", "Loader", "Dump Truck", 
                     "Concrete Mixer", "Generator", "Pump", "Compressor", "Other"])
                model = st.text_input("Model")
            
            with col2:
                capacity = st.text_input("Capacity", placeholder="e.g., 10 ton, 100 HP")
                ownership_type = st.selectbox("Ownership", ["Owned", "Leased", "Rented"])
                current_status = st.selectbox("Status", ["Available", "Deployed", "Maintenance"])
            
            submitted = st.form_submit_button("Add Equipment")
            
            if submitted and equipment_name:
                data = {
                    'equipment_name': equipment_name,
                    'equipment_type': equipment_type,
                    'model': model,
                    'capacity': capacity,
                    'ownership_type': ownership_type,
                    'current_status': current_status
                }
                
                # ✅ Try to add equipment using available method
                try:
                    if hasattr(db, 'add_equipment'):
                        if db.add_equipment(company_id, data):
                            st.success(f"✅ {equipment_name} added successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to add equipment")
                    else:
                        # Try alternative method
                        st.warning("Equipment add method not available. Please contact support.")
                except Exception as e:
                    st.error(f"Error adding equipment: {e}")
    
    # Display equipment
    if equipment_list:
        st.markdown("### 📋 Equipment List")
        
        # Show summary stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Equipment", len(equipment_list))
        with col2:
            owned = sum(1 for e in equipment_list if e.get('ownership_type') == 'Owned')
            st.metric("Owned", owned)
        with col3:
            available = sum(1 for e in equipment_list if e.get('current_status') == 'Available')
            st.metric("Available", available)
        
        for e in equipment_list:
            with st.expander(f"🏗️ {e['equipment_name']} - {e['equipment_type']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Model:** {e.get('model', 'N/A')}")
                    st.write(f"**Capacity:** {e.get('capacity', 'N/A')}")
                
                with col2:
                    st.write(f"**Ownership:** {e.get('ownership_type', 'N/A')}")
                    st.write(f"**Status:** {e.get('current_status', 'N/A')}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✏️ Edit", key=f"edit_equip_{e['id']}"):
                        st.session_state.edit_equipment = e['id']
                        st.rerun()
                with col2:
                    if st.button(f"🗑️ Delete", key=f"del_equip_{e['id']}"):
                        try:
                            if hasattr(db, 'delete_equipment'):
                                if db.delete_equipment(e['id']):
                                    st.success("✅ Equipment deleted successfully!")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to delete equipment")
                        except Exception as ex:
                            st.error(f"Error deleting equipment: {ex}")
                
                # Edit form if this equipment is being edited
                if st.session_state.get('edit_equipment') == e['id']:
                    render_equipment_edit_form(e, db)
    else:
        st.info("No equipment added. Add your equipment inventory.")


def render_equipment_edit_form(equipment, db):
    """Render equipment edit form"""
    with st.form(f"edit_equipment_form_{equipment['id']}"):
        col1, col2 = st.columns(2)
        
        with col1:
            edit_name = st.text_input("Equipment Name", value=equipment['equipment_name'])
            edit_type = st.selectbox(
                "Equipment Type",
                ["Excavator", "Bulldozer", "Crane", "Loader", "Dump Truck", 
                 "Concrete Mixer", "Generator", "Pump", "Compressor", "Other"],
                index=["Excavator", "Bulldozer", "Crane", "Loader", "Dump Truck", 
                       "Concrete Mixer", "Generator", "Pump", "Compressor", "Other"].index(equipment['equipment_type']) 
                if equipment['equipment_type'] in ["Excavator", "Bulldozer", "Crane", "Loader", "Dump Truck", 
                                                  "Concrete Mixer", "Generator", "Pump", "Compressor", "Other"] 
                else 9
            )
            edit_model = st.text_input("Model", value=equipment.get('model', ''))
        
        with col2:
            edit_capacity = st.text_input("Capacity", value=equipment.get('capacity', ''))
            edit_ownership = st.selectbox(
                "Ownership",
                ["Owned", "Leased", "Rented"],
                index=["Owned", "Leased", "Rented"].index(equipment['ownership_type']) 
                if equipment['ownership_type'] in ["Owned", "Leased", "Rented"] 
                else 0
            )
            edit_status = st.selectbox(
                "Status",
                ["Available", "Deployed", "Maintenance"],
                index=["Available", "Deployed", "Maintenance"].index(equipment['current_status']) 
                if equipment['current_status'] in ["Available", "Deployed", "Maintenance"] 
                else 0
            )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Save Changes"):
                data = {
                    'equipment_name': edit_name,
                    'equipment_type': edit_type,
                    'model': edit_model,
                    'capacity': edit_capacity,
                    'ownership_type': edit_ownership,
                    'current_status': edit_status
                }
                
                if hasattr(db, 'update_equipment'):
                    if db.update_equipment(equipment['id'], data):
                        st.success("✅ Equipment updated successfully!")
                        st.session_state.edit_equipment = None
                        st.rerun()
                    else:
                        st.error("❌ Failed to update equipment")
                else:
                    st.warning("Equipment update method not available")
        
        with col2:
            if st.form_submit_button("Cancel"):
                st.session_state.edit_equipment = None
                st.rerun()


def render_experience(company_id):
    """Project experience management with field mapping"""
    st.markdown("### 📋 Project Experience")
    st.caption("Add completed projects for experience requirements")
    
    db = get_db_manager()
    
    # ✅ Try to get experiences using the correct method
    try:
        experiences = db.get_experience_by_company(company_id)
    except AttributeError:
        try:
            experiences = db.get_company_experience(company_id)
        except AttributeError:
            experiences = []
            st.warning("Experience management is not fully configured. Please contact support.")
    
    if experiences is None:
        experiences = []
    
    mappings = db.get_field_mappings(company_id, 'experience')
    
    # Display mapping info
    if mappings:
        with st.expander("🔧 Field Mappings for Experience", expanded=False):
            for m in mappings:
                st.write(f"**{m['field_label']}** → `{m['source_table']}.{m['source_column']}`")
    
    # Quick auto-fill for experience
    if experiences and st.button("📋 Auto-Fill Experience Data"):
        fill_experience_data(db, experiences, mappings)
    
    # Add new experience
    with st.expander("➕ Add Project Experience", expanded=False):
        with st.form("add_experience_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                project_name = st.text_input("Project Name *")
                procuring_entity = st.text_input("Procuring Entity *")
                contract_number = st.text_input("Contract Number")
                contract_value = st.number_input("Contract Value (BDT)", min_value=0.0, step=100000.0, format="%.2f")
            
            with col2:
                award_date = st.date_input("Award Date")
                completion_date = st.date_input("Completion Date")
                role = st.selectbox("Role", ["Prime Contractor", "Subcontractor", "JV Partner"])
                is_completed = st.checkbox("Project Completed", value=True)
            
            procuring_entity_address = st.text_area("Procuring Entity Address")
            procuring_entity_contact = st.text_input("Procuring Entity Contact")
            procuring_entity_email = st.text_input("Procuring Entity Email")
            similarity_justification = st.text_area("Similarity Justification")
            
            submitted = st.form_submit_button("Add Experience")
            
            if submitted and project_name and procuring_entity:
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
                
                try:
                    if hasattr(db, 'add_experience'):
                        if db.add_experience(company_id, data):
                            st.success(f"✅ {project_name} added successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to add experience")
                    else:
                        st.warning("Experience add method not available. Please contact support.")
                except Exception as e:
                    st.error(f"Error adding experience: {e}")
    
    # Display experiences
    if experiences and len(experiences) > 0:
        st.markdown("### 📋 Project History")
        
        # Show summary stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Projects", len(experiences))
        with col2:
            completed = sum(1 for exp in experiences if exp.get('is_completed'))
            st.metric("Completed", completed)
        with col3:
            total_value = sum(exp.get('contract_value', 0) for exp in experiences if exp.get('contract_value'))
            st.metric("Total Value", f"৳{total_value:,.0f}")
        
        # Create display dataframe
        display_data = []
        for exp in experiences:
            award_date = format_date(exp.get('award_date'))
            completion_date = format_date(exp.get('completion_date'))
            
            display_data.append({
                'Project': exp.get('project_name', 'Unknown'),
                'Procuring Entity': exp.get('procuring_entity', 'N/A'),
                'Contract #': exp.get('contract_number', 'N/A'),
                'Value (BDT)': f"৳{exp.get('contract_value', 0):,.2f}" if exp.get('contract_value') else 'N/A',
                'Role': exp.get('role', 'N/A'),
                'Award Date': award_date if award_date else 'N/A',
                'Completion': completion_date if completion_date else 'N/A',
                'Completed': '✅' if exp.get('is_completed') else '❌',
                'ID': exp.get('id')
            })
        
        df = pd.DataFrame(display_data)
        st.dataframe(df.drop(columns=['ID']), use_container_width=True, hide_index=True)
        
        # Show detailed view
        st.markdown("### 📋 Detailed View")
        for exp in experiences:
            with st.expander(f"📋 {exp.get('project_name', 'Unknown')} - {exp.get('procuring_entity', 'N/A')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Procuring Entity:** {exp.get('procuring_entity', 'N/A')}")
                    st.write(f"**Contract Number:** {exp.get('contract_number', 'N/A')}")
                    st.write(f"**Contract Value:** ৳{exp.get('contract_value', 0):,.2f}" if exp.get('contract_value') else "N/A")
                    st.write(f"**Award Date:** {format_date(exp.get('award_date', 'N/A'))}")
                
                with col2:
                    st.write(f"**Completion Date:** {format_date(exp.get('completion_date', 'N/A'))}")
                    st.write(f"**Role:** {exp.get('role', 'N/A')}")
                    st.write(f"**Completed:** {'✅' if exp.get('is_completed') else '❌'}")
                    st.write(f"**Similarity:** {exp.get('similarity_justification', 'N/A')}")
                
                if exp.get('procuring_entity_address'):
                    st.write(f"**PE Address:** {exp.get('procuring_entity_address', 'N/A')}")
                if exp.get('procuring_entity_contact'):
                    st.write(f"**PE Contact:** {exp.get('procuring_entity_contact', 'N/A')}")
                if exp.get('procuring_entity_email'):
                    st.write(f"**PE Email:** {exp.get('procuring_entity_email', 'N/A')}")
                
                if st.button(f"🗑️ Delete", key=f"del_exp_{exp.get('id')}"):
                    try:
                        if hasattr(db, 'delete_experience'):
                            if db.delete_experience(exp.get('id')):
                                st.success("✅ Experience record deleted successfully!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete experience")
                    except Exception as e:
                        st.error(f"Error deleting experience: {e}")
    else:
        st.info("No experience records added. Add your completed projects.")


def render_documents(company_id):
    """Document management for company with field mapping"""
    st.markdown("### 📄 Company Documents")
    st.caption("Upload important company documents")
    
    db = get_db_manager()
    mappings = db.get_field_mappings(company_id, 'documents')
    
    # Display mapping info
    if mappings:
        with st.expander("🔧 Field Mappings for Documents", expanded=False):
            for m in mappings:
                st.write(f"**{m['field_label']}** → `{m['source_table']}.{m['source_column']}`")
    
    uploaded_file = st.file_uploader(
        "Upload Document",
        type=['pdf', 'doc', 'docx', 'jpg', 'png'],
        help="Upload trade license, TIN certificate, VAT certificate, etc."
    )
    
    if uploaded_file:
        col1, col2 = st.columns(2)
        
        with col1:
            doc_type = st.selectbox("Document Type", [
                "Trade License", "TIN Certificate", "VAT Certificate",
                "Audit Report", "Bank Statement", "Experience Certificate",
                "ISO Certificate", "Other"
            ])
            doc_name = st.text_input("Document Name", value=uploaded_file.name)
        
        with col2:
            doc_date = st.date_input("Document Date")
            expiry_date = st.date_input("Expiry Date (if applicable)", value=None)
        
        description = st.text_area("Description")
        
        if st.button("📤 Upload Document", type="primary"):
            doc_dir = f"data/documents/{company_id}"
            os.makedirs(doc_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c for c in doc_name if c.isalnum() or c in '._-')[:50]
            file_path = f"{doc_dir}/{timestamp}_{safe_name}.{uploaded_file.name.split('.')[-1]}"
            
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            data = {
                'document_name': doc_name,
                'document_type': doc_type,
                'file_path': file_path,
                'file_name': uploaded_file.name,
                'description': description,
                'document_date': doc_date,
                'expiry_date': expiry_date,
                'uploaded_by': st.session_state.user_id
            }
            
            if db.add_company_document(company_id, data):
                st.success(f"✅ {doc_name} uploaded successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to upload document")
    
    # List documents
    documents = db.get_company_documents(company_id)
    
    if documents:
        st.markdown("### 📋 Document Library")
        
        for doc in documents:
            with st.expander(f"📄 {doc['document_name']} - {doc['document_type']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Date:** {format_date(doc.get('document_date', 'N/A'))}")
                    if doc.get('expiry_date'):
                        st.write(f"**Expiry:** {format_date(doc['expiry_date'])}")
                        if doc['expiry_date'] < datetime.now().date():
                            st.error("⚠️ EXPIRED")
                
                with col2:
                    st.write(f"**Description:** {doc.get('description', 'N/A')}")
                    if doc.get('uploaded_by'):
                        st.write(f"**Uploaded By:** {doc['uploaded_by']}")
                
                if st.button(f"🗑️ Delete", key=f"del_doc_{doc['id']}"):
                    if db.delete_company_document(doc['id']):
                        st.success("✅ Document deleted successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete document")
    else:
        st.info("No documents uploaded.")


# =============================================================================
# FIELD MAPPING MANAGEMENT
# =============================================================================

def render_field_mappings(company_id):
    """Render field mapping management interface"""
    st.markdown("### 🔧 Custom Field Mappings")
    st.caption("Map form fields to company data for auto-fill")
    
    db = get_db_manager()
    
    # Get existing mappings
    mappings = db.get_field_mappings(company_id)
    
    # Form type selector
    form_types = [
        'basic_info', 'licenses', 'financial', 'personnel', 
        'equipment', 'experience', 'documents', 'tender_submission',
        'technical_offer', 'financial_offer'
    ]
    
    selected_form_type = st.selectbox(
        "Select Form Type",
        form_types,
        format_func=lambda x: x.replace('_', ' ').title()
    )
    
    # Filter mappings by form type
    filtered_mappings = [m for m in mappings if m.get('form_type') == selected_form_type] if mappings else []
    
    # Create new mapping
    with st.expander("➕ Create New Field Mapping", expanded=False):
        with st.form("create_mapping_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                field_id = st.text_input("Field ID *", help="Unique identifier for the field")
                field_label = st.text_input("Field Label *", help="Display label for the field")
                field_type = st.selectbox(
                    "Field Type",
                    ['text', 'number', 'date', 'select', 'checkbox', 'file', 'textarea']
                )
                source_table = st.selectbox(
                    "Source Table",
                    ['', 'companies', 'company_financials', 'company_personnel', 
                     'company_equipment', 'company_experience', 'company_licenses']
                )
            
            with col2:
                source_column = st.text_input("Source Column", help="Column name in the source table")
                default_value = st.text_input("Default Value", help="Default value if no data found")
                mapping_rule = st.selectbox(
                    "Mapping Rule",
                    ['', 'format_currency', 'format_date', 'format_date_english', 
                     'uppercase', 'lowercase', 'title_case', 'clean_phone', 
                     'format_nid', 'join_with_comma']
                )
                confidence_score = st.slider(
                    "Confidence Score",
                    min_value=0.0,
                    max_value=1.0,
                    value=1.0,
                    step=0.05
                )
            
            source_query = st.text_area(
                "Custom Query (Optional)",
                help="Custom SQL query to fetch data (overrides source_table/source_column)"
            )
            
            submitted = st.form_submit_button("Create Mapping")
            
            if submitted and field_id and field_label:
                data = {
                    'form_type': selected_form_type,
                    'field_id': field_id,
                    'field_label': field_label,
                    'field_type': field_type,
                    'source_table': source_table if source_table else None,
                    'source_column': source_column if source_column else None,
                    'source_query': source_query if source_query else None,
                    'default_value': default_value if default_value else None,
                    'mapping_rule': mapping_rule if mapping_rule else None,
                    'confidence_score': confidence_score,
                    'created_by': st.session_state.user_id
                }
                
                if db.create_field_mapping(company_id, data):
                    st.success("✅ Field mapping created successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to create field mapping")
    
    # Display existing mappings
    if filtered_mappings:
        st.markdown(f"### 📋 Existing Mappings for {selected_form_type.replace('_', ' ').title()}")
        
        for mapping in filtered_mappings:
            with st.expander(f"🔗 {mapping['field_label']} ({mapping['field_id']})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Field ID:** {mapping['field_id']}")
                    st.write(f"**Field Type:** {mapping.get('field_type', 'text')}")
                    st.write(f"**Source Table:** {mapping.get('source_table', 'N/A')}")
                    st.write(f"**Source Column:** {mapping.get('source_column', 'N/A')}")
                
                with col2:
                    st.write(f"**Default Value:** {mapping.get('default_value', 'N/A')}")
                    st.write(f"**Mapping Rule:** {mapping.get('mapping_rule', 'N/A')}")
                    st.write(f"**Confidence:** {mapping.get('confidence_score', 0) * 100:.0f}%")
                    st.write(f"**Active:** {'✅' if mapping.get('is_active') else '❌'}")
                
                # Test auto-fill
                if st.button(f"🧪 Test Auto-Fill", key=f"test_mapping_{mapping['id']}"):
                    value = db.get_auto_fill_value(company_id, mapping)
                    if value:
                        st.success(f"✅ Value found: {value}")
                    else:
                        st.warning("⚠️ No value found for this mapping")
                
                # Delete mapping
                if st.button(f"🗑️ Delete Mapping", key=f"del_mapping_{mapping['id']}"):
                    if db.delete_field_mapping(mapping['id']):
                        st.success("✅ Mapping deleted successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete mapping")
    else:
        st.info(f"No mappings found for {selected_form_type.replace('_', ' ').title()}. Create your first mapping above.")


# =============================================================================
# HELPER FUNCTIONS FOR FIELD MAPPING
# =============================================================================

def display_mapped_field(db, label, value, field_id, mappings):
    """Display a field with mapping indicator"""
    mapping = next((m for m in mappings if m.get('field_id') == field_id), None)
    icon = "🔗" if mapping else "📝"
    st.write(f"**{label}:** {value} {icon}")
    if mapping:
        st.caption(f"Mapped to: {mapping.get('source_table', 'N/A')}.{mapping.get('source_column', 'N/A')}")


def show_field_mapping_hint(field_id, value, mappings):
    """Show mapping hint for a field"""
    mapping = next((m for m in mappings if m.get('field_id') == field_id), None)
    if mapping:
        st.caption(f"🔗 Mapped to: {mapping.get('source_table', 'N/A')}.{mapping.get('source_column', 'N/A')}")


def format_date(date_value):
    """Format date for display"""
    if not date_value:
        return None
    if isinstance(date_value, (datetime, date)):
        return date_value.strftime('%d-%b-%Y')
    if isinstance(date_value, str):
        try:
            dt = datetime.strptime(date_value, '%Y-%m-%d')
            return dt.strftime('%d-%b-%Y')
        except:
            return date_value
    return date_value


def test_auto_fill(db, company_id, form_type):
    """Test auto-fill for a form type"""
    mappings = db.get_field_mappings(company_id, form_type)
    if not mappings:
        st.warning(f"No mappings found for {form_type}")
        return
    
    results = {}
    for mapping in mappings:
        value = db.get_auto_fill_value(company_id, mapping)
        if value:
            results[mapping['field_label']] = value
    
    if results:
        st.success(f"✅ Auto-fill found {len(results)} values")
        st.json(results)
    else:
        st.warning("No values found for auto-fill")


def test_personnel_auto_fill(db, person, mappings):
    """Test auto-fill for a personnel record"""
    for mapping in mappings:
        if mapping.get('source_table') == 'company_personnel':
            field = mapping.get('source_column')
            value = person.get(field)
            if value:
                st.success(f"✅ {mapping['field_label']}: {value}")
            else:
                st.info(f"ℹ️ {mapping['field_label']}: No value")


def fill_financial_data(db, company_id, financials, mappings):
    """Fill financial data using mappings"""
    if not financials:
        st.warning("No financial records found")
        return
    
    latest = financials[0]  # Most recent
    for mapping in mappings:
        field = mapping.get('source_column')
        if field in latest:
            value = latest.get(field)
            if value:
                st.success(f"✅ {mapping['field_label']}: {value}")


def fill_experience_data(db, experiences, mappings):
    """Fill experience data using mappings"""
    if not experiences:
        st.warning("No experience records found")
        return
    
    latest = experiences[0]  # Most recent
    for mapping in mappings:
        field = mapping.get('source_column')
        if field in latest:
            value = latest.get(field)
            if value:
                st.success(f"✅ {mapping['field_label']}: {value}")