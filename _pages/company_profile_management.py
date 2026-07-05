"""
Company Profile Management
Complete company data management for e-GP bids
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from database.unified_db_manager import get_db_manager


def show():
    """Company Profile Management - Complete company data for e-GP bids"""
    
    # Check access
    if st.session_state.user_role not in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst']:
        st.error("🔒 Access denied. Company access required.")
        return
    
    company_id = st.session_state.company_id
    
    st.markdown("""
    <div class="main-header">
        <h1>🏢 Company Profile Management</h1>
        <p>Manage all company information for e-GP tender submissions</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🏢 Basic Info",
        "📜 Licenses & Registrations",
        "💰 Financial Info",
        "👥 Key Personnel",
        "🏗️ Equipment",
        "📋 Experience",
        "📄 Documents"
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


def render_basic_info(company_id):
    """Render basic company information section"""
    st.markdown("### 🏢 Basic Information")
    
    db = get_db_manager()
    company = db.get_company_by_id(company_id)
    
    if not company:
        st.error("Company not found")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Company Name:**", company.get('company_name', 'N/A'))
        st.write("**Email:**", company.get('email', 'N/A'))
        st.write("**Phone:**", company.get('phone', 'N/A'))
        st.write("**Mobile:**", company.get('mobile_number', 'N/A'))
        st.write("**Registration No:**", company.get('registration_number', 'N/A'))
    
    with col2:
        st.write("**VAT Number:**", company.get('vat_number', 'N/A'))
        st.write("**Division:**", company.get('division', 'N/A'))
        st.write("**District:**", company.get('district', 'N/A'))
        st.write("**Address:**", company.get('address', 'N/A'))
        st.write("**Website:**", company.get('website', 'N/A'))
    
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
    """Manage licenses and registrations"""
    st.markdown("### 📜 Licenses & Registrations")
    st.caption("Add trade licenses, certificates, and registrations")
    
    db = get_db_manager()
    licenses = db.get_company_licenses(company_id)
    
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
                
                with col2:
                    st.write(f"**Issue Date:** {license_item.get('issue_date', 'N/A')}")
                    st.write(f"**Expiry Date:** {license_item.get('expiry_date', 'N/A')}")
                    if license_item.get('expiry_date'):
                        days_left = (license_item['expiry_date'] - datetime.now().date()).days
                        if days_left < 0:
                            st.error("⚠️ EXPIRED")
                        elif days_left < 90:
                            st.warning(f"⚠️ Expires in {days_left} days")
                
                if st.button("🗑️ Delete", key=f"del_license_{license_item['id']}"):
                    if db.delete_license(license_item['id']):
                        st.success("✅ License deleted successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete license")
    else:
        st.info("No licenses added yet. Add your trade license and other registrations.")


def render_financial_info(company_id):
    """Financial information for bid capacity"""
    st.markdown("### 💰 Financial Information")
    st.caption("Financial data for bid capacity calculation")
    
    db = get_db_manager()
    financials = db.get_company_financials(company_id)
    
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
    """Key personnel management"""
    st.markdown("### 👥 Key Personnel")
    st.caption("Add key personnel for tender submissions")
    
    db = get_db_manager()
    personnel = db.get_company_personnel(company_id)
    
    # Add new personnel
    with st.expander("➕ Add Personnel", expanded=False):
        with st.form("add_personnel_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name *")
                designation = st.text_input("Designation *")
                nid_number = st.text_input("NID Number")
            
            with col2:
                phone = st.text_input("Phone")
                email = st.text_input("Email")
                experience_years = st.number_input("Years of Experience", min_value=0, max_value=50, step=1)
            
            educational_qualification = st.text_area("Educational Qualification")
            is_key_personnel = st.checkbox("Key Personnel (for tender evaluation)")
            
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
                    'is_key_personnel': is_key_personnel
                }
                
                if db.add_company_personnel(company_id, data):
                    st.success(f"✅ {name} added successfully!")
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
                
                with col2:
                    st.write(f"**Experience:** {p.get('experience_years', 0)} years")
                    st.write(f"**Education:** {p.get('educational_qualification', 'N/A')}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✏️ Edit", key=f"edit_person_{p['id']}"):
                        st.session_state.edit_personnel = p['id']
                        st.rerun()
                with col2:
                    if st.button(f"🗑️ Delete", key=f"del_person_{p['id']}"):
                        if db.delete_company_personnel(p['id']):
                            st.success("✅ Personnel deleted successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete personnel")
                
                # Edit form if this person is being edited
                if st.session_state.get('edit_personnel') == p['id']:
                    with st.form(f"edit_personnel_form_{p['id']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            edit_name = st.text_input("Full Name", value=p['name'])
                            edit_designation = st.text_input("Designation", value=p['designation'])
                            edit_nid = st.text_input("NID Number", value=p.get('nid_number', ''))
                        
                        with col2:
                            edit_phone = st.text_input("Phone", value=p.get('phone', ''))
                            edit_email = st.text_input("Email", value=p.get('email', ''))
                            edit_experience = st.number_input(
                                "Years of Experience", 
                                min_value=0, 
                                max_value=50, 
                                step=1, 
                                value=p.get('experience_years', 0)
                            )
                        
                        edit_education = st.text_area(
                            "Educational Qualification", 
                            value=p.get('educational_qualification', '')
                        )
                        edit_key_personnel = st.checkbox("Key Personnel", value=p['is_key_personnel'])
                        
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
                                    'is_key_personnel': edit_key_personnel
                                }
                                
                                if db.update_company_personnel(p['id'], data):
                                    st.success("✅ Personnel updated successfully!")
                                    st.session_state.edit_personnel = None
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to update personnel")
                        
                        with col2:
                            if st.form_submit_button("Cancel"):
                                st.session_state.edit_personnel = None
                                st.rerun()
    else:
        st.info("No personnel added. Add your key personnel for tender submissions.")


def render_equipment(company_id):
    """Equipment inventory management"""
    st.markdown("### 🏗️ Equipment Inventory")
    st.caption("Add equipment for tender submissions")
    
    db = get_db_manager()
    equipment_list = db.get_company_equipment(company_id)
    
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
                
                if db.add_equipment(company_id, data):
                    st.success(f"✅ {equipment_name} added successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to add equipment")
    
    # Display equipment
    if equipment_list:
        st.markdown("### 📋 Equipment List")
        
        for e in equipment_list:
            with st.expander(f"🏗️ {e['equipment_name']} - {e['equipment_type']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Model:** {e.get('model', 'N/A')}")
                    st.write(f"**Capacity:** {e.get('capacity', 'N/A')}")
                
                with col2:
                    st.write(f"**Ownership:** {e.get('ownership_type', 'N/A')}")
                    st.write(f"**Status:** {e.get('current_status', 'N/A')}")
                
                # Add edit option
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✏️ Edit", key=f"edit_equip_{e['id']}"):
                        st.session_state.edit_equipment = e['id']
                        st.rerun()
                with col2:
                    if st.button(f"🗑️ Delete", key=f"del_equip_{e['id']}"):
                        if db.delete_equipment(e['id']):
                            st.success("✅ Equipment deleted successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete equipment")
                
                # Edit form if this equipment is being edited
                if st.session_state.get('edit_equipment') == e['id']:
                    with st.form(f"edit_equipment_form_{e['id']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            edit_name = st.text_input("Equipment Name", value=e['equipment_name'])
                            edit_type = st.selectbox(
                                "Equipment Type",
                                ["Excavator", "Bulldozer", "Crane", "Loader", "Dump Truck", 
                                 "Concrete Mixer", "Generator", "Pump", "Compressor", "Other"],
                                index=["Excavator", "Bulldozer", "Crane", "Loader", "Dump Truck", 
                                       "Concrete Mixer", "Generator", "Pump", "Compressor", "Other"].index(e['equipment_type']) 
                                if e['equipment_type'] in ["Excavator", "Bulldozer", "Crane", "Loader", "Dump Truck", 
                                                          "Concrete Mixer", "Generator", "Pump", "Compressor", "Other"] 
                                else 9
                            )
                            edit_model = st.text_input("Model", value=e.get('model', ''))
                        
                        with col2:
                            edit_capacity = st.text_input("Capacity", value=e.get('capacity', ''))
                            edit_ownership = st.selectbox(
                                "Ownership",
                                ["Owned", "Leased", "Rented"],
                                index=["Owned", "Leased", "Rented"].index(e['ownership_type']) 
                                if e['ownership_type'] in ["Owned", "Leased", "Rented"] 
                                else 0
                            )
                            edit_status = st.selectbox(
                                "Status",
                                ["Available", "Deployed", "Maintenance"],
                                index=["Available", "Deployed", "Maintenance"].index(e['current_status']) 
                                if e['current_status'] in ["Available", "Deployed", "Maintenance"] 
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
                                
                                if db.update_equipment(e['id'], data):
                                    st.success("✅ Equipment updated successfully!")
                                    st.session_state.edit_equipment = None
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to update equipment")
                        
                        with col2:
                            if st.form_submit_button("Cancel"):
                                st.session_state.edit_equipment = None
                                st.rerun()
    else:
        st.info("No equipment added. Add your equipment inventory.")


def render_experience(company_id):
    """Project experience management"""
    st.markdown("### 📋 Project Experience")
    st.caption("Add completed projects for experience requirements")
    
    db = get_db_manager()
    experiences = db.get_company_experience(company_id)
    
    # Add new experience
    with st.expander("➕ Add Project Experience", expanded=False):
        with st.form("add_experience_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                project_name = st.text_input("Project Name *")
                client_name = st.text_input("Client Name *")
                contract_value = st.number_input("Contract Value (BDT)", min_value=0.0, step=100000.0)
            
            with col2:
                contract_date = st.date_input("Contract Date")
                completion_date = st.date_input("Completion Date")
                nature_of_work = st.text_area("Nature of Work / Scope")
            
            is_completed = st.checkbox("Project Completed", value=True)
            
            submitted = st.form_submit_button("Add Experience")
            
            if submitted and project_name and client_name:
                data = {
                    'project_name': project_name,
                    'client_name': client_name,
                    'contract_value': contract_value,
                    'contract_date': contract_date,
                    'completion_date': completion_date,
                    'nature_of_work': nature_of_work,
                    'is_completed': is_completed
                }
                
                if db.add_experience(company_id, data):
                    st.success(f"✅ {project_name} added successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to add experience")
    
    # Display experiences
    if experiences:
        st.markdown("### 📋 Project History")
        
        for exp in experiences:
            with st.expander(f"📋 {exp['project_name']} - {exp['client_name']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Client:** {exp['client_name']}")
                    st.write(f"**Contract Value:** ৳{exp['contract_value']:,.0f}" if exp['contract_value'] else "N/A")
                
                with col2:
                    st.write(f"**Completed:** {exp.get('completion_date', 'N/A')}")
                    st.write(f"**Status:** {'✅ Completed' if exp['is_completed'] else '🔄 In Progress'}")
                
                st.write(f"**Scope:** {exp.get('nature_of_work', 'N/A')}")
                
                # Add edit option
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✏️ Edit", key=f"edit_exp_{exp['id']}"):
                        st.session_state.edit_experience = exp['id']
                        st.rerun()
                with col2:
                    if st.button(f"🗑️ Delete", key=f"del_exp_{exp['id']}"):
                        if db.delete_experience(exp['id']):
                            st.success("✅ Experience record deleted successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete experience")
                
                # Edit form if this experience is being edited
                if st.session_state.get('edit_experience') == exp['id']:
                    with st.form(f"edit_experience_form_{exp['id']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            edit_project = st.text_input("Project Name", value=exp['project_name'])
                            edit_client = st.text_input("Client Name", value=exp['client_name'])
                            edit_value = st.number_input(
                                "Contract Value (BDT)", 
                                min_value=0.0, 
                                step=100000.0,
                                value=float(exp['contract_value']) if exp['contract_value'] else 0.0
                            )
                        
                        with col2:
                            edit_contract = st.date_input(
                                "Contract Date", 
                                value=exp.get('contract_date') or datetime.now().date()
                            )
                            edit_completion = st.date_input(
                                "Completion Date",
                                value=exp.get('completion_date') or datetime.now().date()
                            )
                            edit_completed = st.checkbox("Project Completed", value=exp['is_completed'])
                        
                        edit_scope = st.text_area("Nature of Work / Scope", value=exp.get('nature_of_work', ''))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Save Changes"):
                                data = {
                                    'project_name': edit_project,
                                    'client_name': edit_client,
                                    'contract_value': edit_value,
                                    'contract_date': edit_contract,
                                    'completion_date': edit_completion,
                                    'nature_of_work': edit_scope,
                                    'is_completed': edit_completed
                                }
                                
                                if db.update_experience(exp['id'], data):
                                    st.success("✅ Experience record updated successfully!")
                                    st.session_state.edit_experience = None
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to update experience")
                        
                        with col2:
                            if st.form_submit_button("Cancel"):
                                st.session_state.edit_experience = None
                                st.rerun()
    else:
        st.info("No experience records added. Add your completed projects.")


def render_documents(company_id):
    """Document management for company"""
    st.markdown("### 📄 Company Documents")
    st.caption("Upload important company documents")
    
    db = get_db_manager()
    
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
            import os
            from datetime import datetime
            
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
                    st.write(f"**Date:** {doc.get('document_date', 'N/A')}")
                    if doc.get('expiry_date'):
                        st.write(f"**Expiry:** {doc['expiry_date']}")
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