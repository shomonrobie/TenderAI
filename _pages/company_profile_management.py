# _pages/company_profile_management.py

import streamlit as st
import pandas as pd
from datetime import datetime
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()

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


# _pages/company_profile_management.py - FIXED VERSION

def render_basic_info(company_id):
    """Render basic company information section"""
    
    st.markdown("### 🏢 Basic Information")
    
    # Use context manager properly
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Get company data
        cursor.execute("""
            SELECT company_name, email, phone, mobile_number, address, 
                   district, division, registration_number, vat_number, website,
                   is_active, created_at
            FROM companies 
            WHERE id = ?
        """, (company_id,))
        
        company = cursor.fetchone()
    
    if not company:
        st.error("Company not found")
        return
    
    # Display company info (convert row to dict first)
    company_dict = dict(company)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Company Name:**", company_dict.get('company_name', 'N/A'))
        st.write("**Email:**", company_dict.get('email', 'N/A'))
        st.write("**Phone:**", company_dict.get('phone', 'N/A'))
        st.write("**Mobile:**", company_dict.get('mobile_number', 'N/A'))
        st.write("**Registration No:**", company_dict.get('registration_number', 'N/A'))
    
    with col2:
        st.write("**VAT Number:**", company_dict.get('vat_number', 'N/A'))
        st.write("**Division:**", company_dict.get('division', 'N/A'))
        st.write("**District:**", company_dict.get('district', 'N/A'))
        st.write("**Address:**", company_dict.get('address', 'N/A'))
        st.write("**Website:**", company_dict.get('website', 'N/A'))
    
    # Edit button
    if st.button("✏️ Edit Basic Information"):
        st.session_state.editing_basic_info = True
        st.rerun()
    
    # Edit form
    if st.session_state.get('editing_basic_info', False):
        with st.form("edit_basic_info_form"):
            new_company_name = st.text_input("Company Name", value=company_dict.get('company_name', ''))
            new_email = st.text_input("Email", value=company_dict.get('email', ''))
            new_phone = st.text_input("Phone", value=company_dict.get('phone', ''))
            new_mobile = st.text_input("Mobile Number", value=company_dict.get('mobile_number', ''))
            new_address = st.text_area("Address", value=company_dict.get('address', ''))
            new_division = st.text_input("Division", value=company_dict.get('division', ''))
            new_district = st.text_input("District", value=company_dict.get('district', ''))
            new_registration = st.text_input("Registration Number", value=company_dict.get('registration_number', ''))
            new_vat = st.text_input("VAT Number", value=company_dict.get('vat_number', ''))
            new_website = st.text_input("Website", value=company_dict.get('website', ''))
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Save Changes"):
                    # Update using context manager
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE companies 
                            SET company_name = ?, email = ?, phone = ?, mobile_number = ?,
                                address = ?, division = ?, district = ?,
                                registration_number = ?, vat_number = ?, website = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (new_company_name, new_email, new_phone, new_mobile,
                              new_address, new_division, new_district,
                              new_registration, new_vat, new_website, company_id))
                    
                    st.success("Company information updated!")
                    st.session_state.editing_basic_info = False
                    st.rerun()
            
            with col2:
                if st.form_submit_button("Cancel"):
                    st.session_state.editing_basic_info = False
                    st.rerun()


def render_licenses_registrations(company_id):
    """Manage licenses and registrations"""
    st.markdown("### 📜 Licenses & Registrations")
    st.caption("Add trade licenses, certificates, and registrations")
    
    # Get existing licenses
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM company_licenses 
        WHERE company_id = ? AND status = 'active'
        ORDER BY created_at DESC
    """, (company_id,))
    
    licenses = cursor.fetchall()
    conn.close()
    
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
                conn = db.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO company_licenses (
                        company_id, license_type, license_number, issuing_authority,
                        issue_date, expiry_date
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (company_id, license_type, license_number, issuing_authority, issue_date, expiry_date))
                
                conn.commit()
                conn.close()
                
                st.success(f"✅ {license_type} added successfully!")
                st.rerun()
    
    # Display existing licenses
    if licenses:
        st.markdown("### 📋 Existing Licenses")
        
        for license_item in licenses:
            with st.expander(f"📜 {license_item[2]} - {license_item[3]}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**License Number:** {license_item[3]}")
                    st.write(f"**Issuing Authority:** {license_item[4] or 'N/A'}")
                
                with col2:
                    st.write(f"**Issue Date:** {license_item[5] if license_item[5] else 'N/A'}")
                    st.write(f"**Expiry Date:** {license_item[6] if license_item[6] else 'N/A'}")
                    if license_item[6]:
                        days_left = (license_item[6] - datetime.now().date()).days
                        if days_left < 0:
                            st.error("⚠️ EXPIRED")
                        elif days_left < 90:
                            st.warning(f"⚠️ Expires in {days_left} days")
                
                if st.button("🗑️ Delete", key=f"del_license_{license_item[0]}"):
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("UPDATE company_licenses SET status = 'inactive' WHERE id = ?", (license_item[0],))
                    conn.commit()
                    conn.close()
                    st.rerun()
    else:
        st.info("No licenses added yet. Add your trade license and other registrations.")


def render_financial_info(company_id):
    """Financial information for bid capacity"""
    st.markdown("### 💰 Financial Information")
    st.caption("Financial data for bid capacity calculation")
    
    # Get existing financial records
    conn = db.get_connection()
    cursor = conn.cursor()
    
    
    cursor.execute("""
        SELECT * FROM company_financials 
        WHERE company_id = ?
        ORDER BY fiscal_year DESC
    """, (company_id,))
    
    financials = cursor.fetchall()
    conn.close()
    
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
                conn = db.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO company_financials (
                        company_id, fiscal_year, annual_turnover, construction_turnover,
                        net_worth, working_capital, liquid_assets, credit_limit,
                        bank_guarantee_limit, is_audited, audit_firm
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    company_id, fiscal_year, annual_turnover, construction_turnover,
                    net_worth, working_capital, liquid_assets, credit_limit,
                    bank_guarantee_limit, 1 if is_audited else 0, audit_firm
                ))
                
                conn.commit()
                conn.close()
                
                st.success(f"✅ Financial record for {fiscal_year} added!")
                st.rerun()
    
    # Display financial records
    if financials:
        st.markdown("### 📊 Financial History")
        
        financial_data = []
        for f in financials:
            financial_data.append({
                'Fiscal Year': f[2],
                'Annual Turnover': f"৳{f[3]:,.0f}" if f[3] else "N/A",
                'Construction Turnover': f"৳{f[4]:,.0f}" if f[4] else "N/A",
                'Net Worth': f"৳{f[5]:,.0f}" if f[5] else "N/A",
                'Working Capital': f"৳{f[6]:,.0f}" if f[6] else "N/A",
                'Audited': "✅" if f[9] else "❌",
                'ID': f[0]
            })
        
        df = pd.DataFrame(financial_data)
        st.dataframe(df.drop(columns=['ID']), use_container_width=True, hide_index=True)
        
        # Delete option
        for f in financials:
            if st.button(f"🗑️ Delete {f[2]}", key=f"del_fin_{f[0]}"):
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM company_financials WHERE id = ?", (f[0],))
                conn.commit()
                conn.close()
                st.rerun()
    else:
        st.info("No financial records added. Add your financial data for bid capacity calculation.")


def render_key_personnel(company_id):
    """Key personnel management"""
    st.markdown("### 👥 Key Personnel")
    st.caption("Add key personnel for tender submissions")
    
    # Get existing personnel
    conn = db.get_connection()
    cursor = conn.cursor()
    
    
    cursor.execute("""
        SELECT * FROM company_personnel 
        WHERE company_id = ?
        ORDER BY is_key_personnel DESC, name
    """, (company_id,))
    
    personnel = cursor.fetchall()
    conn.close()
    
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
                conn = db.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO company_personnel (
                        company_id, name, designation, nid_number, phone, email,
                        educational_qualification, experience_years, is_key_personnel
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (company_id, name, designation, nid_number, phone, email,
                      educational_qualification, experience_years, 1 if is_key_personnel else 0))
                
                conn.commit()
                conn.close()
                
                st.success(f"✅ {name} added successfully!")
                st.rerun()
    
    # Display personnel
    if personnel:
        st.markdown("### 📋 Personnel List")
        
        for p in personnel:
            with st.expander(f"👤 {p[2]} - {p[3]}" + (" ⭐ Key Personnel" if p[9] else "")):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**NID:** {p[4] or 'N/A'}")
                    st.write(f"**Phone:** {p[5] or 'N/A'}")
                    st.write(f"**Email:** {p[6] or 'N/A'}")
                
                with col2:
                    st.write(f"**Experience:** {p[8] if p[8] else 0} years")
                    st.write(f"**Education:** {p[7] or 'N/A'}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✏️ Edit", key=f"edit_person_{p[0]}"):
                        st.session_state.edit_personnel = p[0]
                        st.rerun()
                with col2:
                    if st.button(f"🗑️ Delete", key=f"del_person_{p[0]}"):
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM company_personnel WHERE id = ?", (p[0],))
                        conn.commit()
                        conn.close()
                        st.rerun()
    else:
        st.info("No personnel added. Add your key personnel for tender submissions.")


def render_equipment(company_id):
    """Equipment inventory management"""
    st.markdown("### 🏗️ Equipment Inventory")
    st.caption("Add equipment for tender submissions")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM equipment 
        WHERE company_id = ?
        ORDER BY equipment_name
    """, (company_id,))
    
    equipment_list = cursor.fetchall()
    conn.close()
    
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
                conn = db.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO equipment (
                        company_id, equipment_name, equipment_type, model,
                        capacity, ownership_type, current_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (company_id, equipment_name, equipment_type, model, capacity, ownership_type, current_status))
                
                conn.commit()
                conn.close()
                
                st.success(f"✅ {equipment_name} added!")
                st.rerun()
    
    # Display equipment
    if equipment_list:
        st.markdown("### 📋 Equipment List")
        
        for e in equipment_list:
            with st.expander(f"🏗️ {e[2]} - {e[3]}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Model:** {e[4] or 'N/A'}")
                    st.write(f"**Capacity:** {e[6] or 'N/A'}")
                
                with col2:
                    st.write(f"**Ownership:** {e[7] or 'N/A'}")
                    st.write(f"**Status:** {e[8] or 'N/A'}")
                
                if st.button(f"🗑️ Delete", key=f"del_equip_{e[0]}"):
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM equipment WHERE id = ?", (e[0],))
                    conn.commit()
                    conn.close()
                    st.rerun()
    else:
        st.info("No equipment added. Add your equipment inventory.")


def render_experience(company_id):
    """Project experience management"""
    st.markdown("### 📋 Project Experience")
    st.caption("Add completed projects for experience requirements")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM experience_record 
        WHERE company_id = ?
        ORDER BY completion_date DESC
    """, (company_id,))
    
    experiences = cursor.fetchall()
    conn.close()
    
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
                conn = db.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO experience_record (
                        company_id, project_name, client_name, contract_value,
                        contract_date, completion_date, nature_of_work, is_completed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (company_id, project_name, client_name, contract_value,
                      contract_date, completion_date, nature_of_work, 1 if is_completed else 0))
                
                conn.commit()
                conn.close()
                
                st.success(f"✅ {project_name} added!")
                st.rerun()
    
    # Display experiences
    if experiences:
        st.markdown("### 📋 Project History")
        
        for exp in experiences:
            with st.expander(f"📋 {exp[2]} - {exp[3]}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Client:** {exp[3]}")
                    st.write(f"**Contract Value:** ৳{exp[5]:,.0f}" if exp[5] else "N/A")
                
                with col2:
                    st.write(f"**Completed:** {exp[7] if exp[7] else 'N/A'}")
                    st.write(f"**Status:** {'✅ Completed' if exp[9] else '🔄 In Progress'}")
                
                st.write(f"**Scope:** {exp[8] or 'N/A'}")
                
                if st.button(f"🗑️ Delete", key=f"del_exp_{exp[0]}"):
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM experience_record WHERE id = ?", (exp[0],))
                    conn.commit()
                    conn.close()
                    st.rerun()
    else:
        st.info("No experience records added. Add your completed projects.")


def render_documents(company_id):
    """Document management for company"""
    st.markdown("### 📄 Company Documents")
    st.caption("Upload important company documents")
    
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
            
            # Save to database
            conn = db.get_connection()
            cursor = conn.cursor()
            
            
            cursor.execute("""
                INSERT INTO company_documents (
                    company_id, document_name, document_type, file_path, file_name,
                    description, document_date, expiry_date, uploaded_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (company_id, doc_name, doc_type, file_path, uploaded_file.name,
                  description, doc_date, expiry_date, st.session_state.user_id))
            
            conn.commit()
            conn.close()
            
            st.success(f"✅ {doc_name} uploaded successfully!")
            st.rerun()
    
    # List documents
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM company_documents 
        WHERE company_id = ?
        ORDER BY uploaded_at DESC
    """, (company_id,))
    
    documents = cursor.fetchall()
    conn.close()
    
    if documents:
        st.markdown("### 📋 Document Library")
        
        for doc in documents:
            with st.expander(f"📄 {doc[2]} - {doc[3]}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Date:** {doc[7] if doc[7] else 'N/A'}")
                    if doc[8]:
                        st.write(f"**Expiry:** {doc[8]}")
                        if doc[8] < datetime.now().date():
                            st.error("⚠️ EXPIRED")
                
                with col2:
                    st.write(f"**Description:** {doc[6] or 'N/A'}")
                
                if st.button(f"🗑️ Delete", key=f"del_doc_{doc[0]}"):
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM company_documents WHERE id = ?", (doc[0],))
                    conn.commit()
                    conn.close()
                    st.rerun()
    else:
        st.info("No documents uploaded.")