# pages/enhanced_company_dashboard.py
"""
Enhanced Company Dashboard with Knowledge Repository
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, date
from database.unified_db_manager import UnifiedDatabaseManager

db = UnifiedDatabaseManager()
def show():
    """Enhanced Company Dashboard with Knowledge Repository"""
    
    # Verify access
    if st.session_state.user_role not in ['company_admin', 'admin', 'manager']:
        st.error("🔒 Access denied. Company access required.")
        return
    
    company_id = st.session_state.company_id
    
    st.markdown("""
    <div class="main-header">
        <h1>🏢 Company Knowledge Repository</h1>
        <p>Centralized repository for company information, documents, and intelligence</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs for different knowledge areas
    tabs = st.tabs([
        "📊 Dashboard",
        "🏢 Company Profile",
        "👥 Personnel",
        "🏗️ Equipment",
        "📋 Experience",
        "💰 Financial",
        "📄 Documents",
        "🔍 Search",
        "📊 Analytics"
    ])
    
    with tabs[0]:
        render_knowledge_dashboard(company_id)
    
    with tabs[1]:
        render_company_profile(company_id)
    
    with tabs[2]:
        render_personnel_management(company_id)
    
    with tabs[3]:
        render_equipment_management(company_id)
    
    with tabs[4]:
        render_experience_management(company_id)
    
    with tabs[5]:
        render_financial_management(company_id)
    
    with tabs[6]:
        render_document_management(company_id)
    
    with tabs[7]:
        render_knowledge_search(company_id)
    
    with tabs[8]:
        render_knowledge_analytics(company_id)

def render_knowledge_dashboard(company_id):
    """Render knowledge repository dashboard with KPIs"""
    st.markdown("### Knowledge Repository Dashboard")
    
    # Get counts
    conn = db.get_connection()
    cursor = conn.cursor()
    
    counts = {}
    tables = ['personnel', 'equipment', 'experience_record', 'financial_capacity', 'document_registry']
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE company_id = ?", (company_id,))
        counts[table] = cursor.fetchone()[0]
    
    # Documents by type
    cursor.execute("""
        SELECT document_type, COUNT(*) 
        FROM document_registry 
        WHERE company_id = ? AND is_latest_version = 1
        GROUP BY document_type
    """, (company_id,))
    doc_types = cursor.fetchall()
    
    # Recent documents
    cursor.execute("""
        SELECT document_name, document_type, uploaded_at, file_name
        FROM document_registry 
        WHERE company_id = ? AND is_latest_version = 1
        ORDER BY uploaded_at DESC
        LIMIT 5
    """, (company_id,))
    recent_docs = cursor.fetchall()
    
    conn.close()
    
    # KPIs
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("👥 Personnel", counts.get('personnel', 0))
    with col2:
        st.metric("🏗️ Equipment", counts.get('equipment', 0))
    with col3:
        st.metric("📋 Experience", counts.get('experience_record', 0))
    with col4:
        st.metric("💰 Financial Records", counts.get('financial_capacity', 0))
    with col5:
        st.metric("📄 Documents", counts.get('document_registry', 0))
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Documents by Type")
        if doc_types:
            doc_df = pd.DataFrame(doc_types, columns=['Type', 'Count'])
            st.bar_chart(doc_df.set_index('Type'))
        else:
            st.info("No documents uploaded yet")
    
    with col2:
        st.markdown("### 📋 Recent Documents")
        if recent_docs:
            for doc in recent_docs:
                st.caption(f"📄 **{doc[0]}** ({doc[1]})")
                st.caption(f"   Uploaded: {doc[2][:16] if doc[2] else 'N/A'}")
                st.divider()
        else:
            st.info("No recent documents")
    
    # Data completeness
    st.markdown("### 📊 Data Completeness")
    
    completeness = {
        'Company Profile': db.get_company_profile(company_id) is not None,
        'Personnel Records': counts.get('personnel', 0) > 0,
        'Equipment Records': counts.get('equipment', 0) > 0,
        'Experience Records': counts.get('experience_record', 0) > 0,
        'Financial Records': counts.get('financial_capacity', 0) > 0,
        'Documents': counts.get('document_registry', 0) > 0
    }
    
    for category, is_complete in completeness.items():
        status = "✅" if is_complete else "⚠️"
        st.write(f"{status} {category}")

def render_company_profile(company_id):
    """Render company profile management"""
    st.markdown("### Company Profile")
    
    # Get existing profile
    profile = db.get_company_profile(company_id)
    
    with st.form("company_profile_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            legal_name = st.text_input("Legal Name *", value=profile.get('legal_name', '') if profile else '')
            trade_name = st.text_input("Trade Name", value=profile.get('trade_name', '') if profile else '')
            registration_number = st.text_input("Registration Number", value=profile.get('registration_number', '') if profile else '')
            date_of_incorporation = st.date_input("Date of Incorporation", 
                value=datetime.strptime(profile['date_of_incorporation'], '%Y-%m-%d').date() if profile and profile.get('date_of_incorporation') else date.today())
            business_nature = st.text_area("Nature of Business", value=profile.get('business_nature', '') if profile else '')
            business_category = st.selectbox("Business Category", 
                ["Contractor", "Supplier", "Consultant", "Manufacturer", "Trader", "Other"],
                index=0)
        
        with col2:
            registered_address = st.text_area("Registered Address", value=profile.get('registered_address', '') if profile else '')
            corporate_address = st.text_area("Corporate Address", value=profile.get('corporate_address', '') if profile else '')
            phone_primary = st.text_input("Primary Phone", value=profile.get('phone_primary', '') if profile else '')
            phone_secondary = st.text_input("Secondary Phone", value=profile.get('phone_secondary', '') if profile else '')
            email_primary = st.text_input("Primary Email", value=profile.get('email_primary', '') if profile else '')
            email_secondary = st.text_input("Secondary Email", value=profile.get('email_secondary', '') if profile else '')
            website = st.text_input("Website", value=profile.get('website', '') if profile else '')
            
            division = st.selectbox("Division", 
                ["Dhaka", "Chattogram", "Khulna", "Rajshahi", "Rangpur", "Barishal", "Sylhet", "Mymensingh"],
                index=0)
            district = st.text_input("District", value=profile.get('district', '') if profile else '')
        
        submitted = st.form_submit_button("Save Profile")
        
        if submitted:
            profile_data = {
                'legal_name': legal_name,
                'trade_name': trade_name,
                'registration_number': registration_number,
                'date_of_incorporation': date_of_incorporation,
                'business_nature': business_nature,
                'business_category': business_category,
                'registered_address': registered_address,
                'corporate_address': corporate_address,
                'phone_primary': phone_primary,
                'phone_secondary': phone_secondary,
                'email_primary': email_primary,
                'email_secondary': email_secondary,
                'website': website,
                'division': division,
                'district': district,
                'updated_by': st.session_state.user_id
            }
            
            if db.save_company_profile(company_id, profile_data):
                st.success("Company profile saved successfully!")
                st.rerun()
            else:
                st.error("Failed to save profile")

def render_personnel_management(company_id):
    """Render personnel management interface"""
    st.markdown("### Personnel Management")
    
    # Add new personnel
    with st.expander("➕ Add New Personnel", expanded=False):
        with st.form("add_personnel_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                full_name = st.text_input("Full Name *")
                designation = st.text_input("Designation *")
                employee_id = st.text_input("Employee ID")
                nid_number = st.text_input("NID Number")
            
            with col2:
                date_of_birth = st.date_input("Date of Birth")
                phone = st.text_input("Phone")
                email = st.text_input("Email")
                joining_date = st.date_input("Joining Date")
            
            with col3:
                educational_qualification = st.text_area("Educational Qualification")
                skills = st.text_input("Skills (comma-separated)")
                is_key_personnel = st.checkbox("Key Personnel")
            
            submitted = st.form_submit_button("Add Personnel")
            
            if submitted and full_name and designation:
                personnel_data = {
                    'full_name': full_name,
                    'designation': designation,
                    'employee_id': employee_id,
                    'nid_number': nid_number,
                    'date_of_birth': date_of_birth,
                    'personal_phone': phone,
                    'personal_email': email,
                    'joining_date': joining_date,
                    'educational_qualification': educational_qualification,
                    'skills': skills.split(',') if skills else [],
                    'is_key_personnel': is_key_personnel,
                    'created_by': st.session_state.user_id
                }
                
                result = enhanced_db.add_personnel(company_id, personnel_data)
                if result:
                    st.success(f"Personnel {full_name} added successfully!")
                    st.rerun()
                else:
                    st.error("Failed to add personnel")
    
    # List personnel
    personnel_df = enhanced_db.get_personnel(company_id)
    
    if not personnel_df.empty:
        st.markdown("### Personnel List")
        
        for _, person in personnel_df.iterrows():
            with st.expander(f"👤 {person['full_name']} - {person['designation']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Employee ID:** {person.get('employee_id', 'N/A')}")
                    st.write(f"**Phone:** {person.get('personal_phone', 'N/A')}")
                    st.write(f"**Email:** {person.get('personal_email', 'N/A')}")
                    st.write(f"**Joining Date:** {person.get('joining_date', 'N/A')}")
                
                with col2:
                    st.write(f"**Key Personnel:** {'✅' if person.get('is_key_personnel') else '❌'}")
                    st.write(f"**Status:** {person.get('employment_status', 'active')}")
                    st.write(f"**Skills:** {person.get('skills', 'N/A')}")
                
                if st.button("Edit", key=f"edit_person_{person['id']}"):
                    st.session_state.edit_personnel = person['id']
                    st.rerun()
    else:
        st.info("No personnel records found. Add your first team member above.")

def render_equipment_management(company_id):
    """Render equipment management interface"""
    st.markdown("### Equipment Management")
    
    with st.expander("➕ Add New Equipment", expanded=False):
        with st.form("add_equipment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                equipment_name = st.text_input("Equipment Name *")
                equipment_type = st.selectbox("Equipment Type", 
                    ["Excavator", "Bulldozer", "Crane", "Loader", "Dump Truck", "Concrete Mixer", "Generator", "Pump", "Other"])
                model = st.text_input("Model")
                manufacturer = st.text_input("Manufacturer")
                serial_number = st.text_input("Serial Number")
            
            with col2:
                capacity = st.number_input("Capacity", min_value=0.0, step=0.1)
                year_of_manufacture = st.number_input("Year of Manufacture", min_value=1950, max_value=datetime.now().year)
                ownership_type = st.selectbox("Ownership Type", ["Owned", "Leased", "Rented"])
                purchase_date = st.date_input("Purchase Date")
                purchase_cost = st.number_input("Purchase Cost (BDT)", min_value=0.0, step=10000.0)
            
            current_status = st.selectbox("Current Status", ["available", "deployed", "maintenance", "repair", "idle"])
            location = st.text_input("Current Location")
            
            submitted = st.form_submit_button("Add Equipment")
            
            if submitted and equipment_name:
                equipment_data = {
                    'equipment_name': equipment_name,
                    'equipment_type': equipment_type,
                    'model': model,
                    'manufacturer': manufacturer,
                    'serial_number': serial_number,
                    'capacity': capacity,
                    'year_of_manufacture': year_of_manufacture,
                    'ownership_type': ownership_type,
                    'purchase_date': purchase_date,
                    'purchase_cost': purchase_cost,
                    'current_status': current_status,
                    'location': location,
                    'created_by': st.session_state.user_id
                }
                
                result = enhanced_db.add_equipment(company_id, equipment_data)
                if result:
                    st.success(f"Equipment {equipment_name} added successfully!")
                    st.rerun()
                else:
                    st.error("Failed to add equipment")
    
    # List equipment
    equipment_df = enhanced_db.get_equipment(company_id)
    
    if not equipment_df.empty:
        st.markdown("### Equipment Inventory")
        
        # Status filter
        status_filter = st.multiselect("Filter by Status", 
            ["available", "deployed", "maintenance", "repair", "idle"],
            default=["available"])
        
        filtered_df = equipment_df[equipment_df['current_status'].isin(status_filter)] if status_filter else equipment_df
        
        for _, equip in filtered_df.iterrows():
            status_color = {
                'available': '🟢',
                'deployed': '🔵',
                'maintenance': '🟡',
                'repair': '🔴',
                'idle': '⚪'
            }.get(equip['current_status'], '⚪')
            
            with st.expander(f"{status_color} {equip['equipment_name']} - {equip.get('model', 'N/A')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Type:** {equip.get('equipment_type', 'N/A')}")
                    st.write(f"**Serial Number:** {equip.get('serial_number', 'N/A')}")
                    st.write(f"**Capacity:** {equip.get('capacity', 'N/A')}")
                
                with col2:
                    st.write(f"**Ownership:** {equip.get('ownership_type', 'N/A')}")
                    st.write(f"**Status:** {equip['current_status']}")
                    st.write(f"**Location:** {equip.get('location', 'N/A')}")
    else:
        st.info("No equipment records found")

def render_experience_management(company_id):
    """Render experience/project management interface"""
    st.markdown("### Experience & Project Records")
    
    with st.expander("➕ Add New Experience Record", expanded=False):
        with st.form("add_experience_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                project_name = st.text_input("Project Name *")
                client_name = st.text_input("Client Name *")
                client_type = st.selectbox("Client Type", ["Government", "Semi-Government", "Private", "NGO", "International"])
                contract_number = st.text_input("Contract Number")
                contract_date = st.date_input("Contract Date")
            
            with col2:
                contract_value = st.number_input("Contract Value (BDT)", min_value=0.0, step=100000.0)
                completion_date = st.date_input("Completion Date")
                nature_of_work = st.text_area("Nature of Work")
                is_completed = st.checkbox("Project Completed")
            
            scope_of_work = st.text_area("Scope of Work")
            
            submitted = st.form_submit_button("Add Experience")
            
            if submitted and project_name and client_name:
                experience_data = {
                    'project_name': project_name,
                    'client_name': client_name,
                    'client_type': client_type,
                    'contract_number': contract_number,
                    'contract_date': contract_date,
                    'contract_value': contract_value,
                    'completion_date': completion_date,
                    'nature_of_work': nature_of_work,
                    'scope_of_work': scope_of_work,
                    'is_completed': is_completed,
                    'created_by': st.session_state.user_id
                }
                
                result = enhanced_db.add_experience(company_id, experience_data)
                if result:
                    st.success(f"Experience record for {project_name} added successfully!")
                    st.rerun()
                else:
                    st.error("Failed to add experience record")
    
    # List experiences
    experience_df = enhanced_db.get_experiences(company_id)
    
    if not experience_df.empty:
        st.markdown("### Project History")
        
        for _, exp in experience_df.iterrows():
            with st.expander(f"📋 {exp['project_name']} - {exp['client_name']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Contract Value:** BDT {exp.get('contract_value', 0):,.0f}")
                    st.write(f"**Contract Date:** {exp.get('contract_date', 'N/A')}")
                    st.write(f"**Completion Date:** {exp.get('completion_date', 'N/A')}")
                
                with col2:
                    st.write(f"**Status:** {'✅ Completed' if exp.get('is_completed') else '🔄 In Progress'}")
                    st.write(f"**Client Type:** {exp.get('client_type', 'N/A')}")
                
                st.write(f"**Nature of Work:** {exp.get('nature_of_work', 'N/A')}")
    else:
        st.info("No experience records found")

def render_financial_management(company_id):
    """Render financial capacity management"""
    st.markdown("### Financial Capacity Management")
    
    with st.expander("➕ Add Financial Record", expanded=False):
        with st.form("add_financial_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                fiscal_year = st.text_input("Fiscal Year (e.g., 2023-2024) *")
                annual_turnover = st.number_input("Annual Turnover (BDT)", min_value=0.0, step=1000000.0)
                net_worth = st.number_input("Net Worth (BDT)", min_value=0.0, step=1000000.0)
                working_capital = st.number_input("Working Capital (BDT)", min_value=0.0, step=1000000.0)
            
            with col2:
                credit_limit = st.number_input("Credit Limit (BDT)", min_value=0.0, step=1000000.0)
                bank_guarantee_limit = st.number_input("Bank Guarantee Limit (BDT)", min_value=0.0, step=1000000.0)
                is_audited = st.checkbox("Audited Financials")
                audit_firm = st.text_input("Audit Firm")
            
            submitted = st.form_submit_button("Add Financial Record")
            
            if submitted and fiscal_year:
                financial_data = {
                    'fiscal_year': fiscal_year,
                    'annual_turnover': annual_turnover,
                    'net_worth': net_worth,
                    'working_capital': working_capital,
                    'credit_limit': credit_limit,
                    'bank_guarantee_limit': bank_guarantee_limit,
                    'is_audited': is_audited,
                    'audit_firm': audit_firm
                }
                
                result = enhanced_db.add_financial_capacity(company_id, financial_data)
                if result:
                    st.success(f"Financial record for {fiscal_year} added successfully!")
                    st.rerun()
                else:
                    st.error("Failed to add financial record")
    
    # List financial records
    financial_df = enhanced_db.get_financial_records(company_id)
    
    if not financial_df.empty:
        st.markdown("### Financial History")
        st.dataframe(financial_df, use_container_width=True)
        
        # Trend chart
        if 'annual_turnover' in financial_df.columns and 'fiscal_year' in financial_df.columns:
            st.markdown("### Turnover Trend")
            turnover_data = financial_df[['fiscal_year', 'annual_turnover']].dropna()
            if not turnover_data.empty:
                st.line_chart(turnover_data.set_index('fiscal_year'))
    else:
        st.info("No financial records found")

def render_document_management(company_id):
    """Render document management with versioning"""
    st.markdown("### Document Management")
    
    # Upload document
    with st.expander("📤 Upload Document", expanded=False):
        uploaded_file = st.file_uploader("Choose file", type=['pdf', 'doc', 'docx', 'jpg', 'png', 'xlsx', 'csv'])
        
        if uploaded_file:
            col1, col2 = st.columns(2)
            
            with col1:
                document_name = st.text_input("Document Name", value=uploaded_file.name)
                document_type = st.selectbox("Document Type", 
                    ["trade_license", "tin", "vat", "financial_report", "certificate", "experience", "personnel", "other"])
                category = st.selectbox("Category", ["Legal", "Financial", "Technical", "Administrative", "Other"])
            
            with col2:
                document_date = st.date_input("Document Date", value=date.today())
                expiry_date = st.date_input("Expiry Date (if applicable)", value=None)
                tags = st.text_input("Tags (comma-separated)")
                description = st.text_area("Description")
            
            if st.button("Upload Document"):
                # Save file and record
                import hashlib
                import os
                from datetime import datetime
                
                # Create documents directory
                doc_dir = f"data/documents/{company_id}"
                os.makedirs(doc_dir, exist_ok=True)
                
                # Generate unique filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = "".join(c for c in document_name if c.isalnum() or c in '._-')[:50]
                file_path = f"{doc_dir}/{timestamp}_{safe_name}"
                
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Extract text from PDF if applicable
                extracted_text = ""
                if uploaded_file.type == "application/pdf":
                    try:
                        import PyPDF2
                        pdf_reader = PyPDF2.PdfReader(uploaded_file)
                        for page in pdf_reader.pages:
                            extracted_text += page.extract_text()
                    except:
                        pass
                
                document_data = {
                    'document_name': document_name,
                    'document_type': document_type,
                    'file_path': file_path,
                    'file_name': uploaded_file.name,
                    'file_size': len(uploaded_file.getvalue()),
                    'mime_type': uploaded_file.type,
                    'description': description,
                    'tags': [t.strip() for t in tags.split(',')] if tags else [],
                    'category': category,
                    'document_date': document_date,
                    'expiry_date': expiry_date,
                    'extracted_text': extracted_text,
                    'uploaded_by': st.session_state.user_id
                }
                
                doc_id = enhanced_db.add_document(company_id, document_data, uploaded_file.getvalue())
                
                if doc_id:
                    st.success(f"Document '{document_name}' uploaded successfully!")
                else:
                    st.error("Failed to upload document")
    
    # List documents
    st.markdown("### Document Library")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        type_filter = st.selectbox("Filter by Type", ["All"] + ["trade_license", "tin", "vat", "financial_report", "certificate", "experience", "personnel", "other"])
    with col2:
        show_expired = st.checkbox("Show Expired Documents")
    
    documents = enhanced_db.get_documents(company_id, type_filter if type_filter != "All" else None, show_expired)
    
    if documents:
        for doc in documents:
            with st.expander(f"📄 {doc['document_name']} ({doc['document_type']})"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Version:** v{doc.get('version_number', 1)}")
                    st.write(f"**Type:** {doc['document_type']}")
                    st.write(f"**Category:** {doc.get('category', 'N/A')}")
                
                with col2:
                    st.write(f"**Document Date:** {doc.get('document_date', 'N/A')}")
                    st.write(f"**Expiry Date:** {doc.get('expiry_date', 'N/A')}")
                    status = "Valid" if not doc.get('expiry_date') or doc['expiry_date'] >= date.today() else "Expired"
                    st.write(f"**Status:** {status}")
                
                with col3:
                    st.write(f"**Uploaded:** {doc.get('uploaded_at', 'N/A')[:16] if doc.get('uploaded_at') else 'N/A'}")
                    tags = json.loads(doc.get('tags', '[]')) if doc.get('tags') else []
                    st.write(f"**Tags:** {', '.join(tags) if tags else 'None'}")
                
                if doc.get('description'):
                    st.write(f"**Description:** {doc['description']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📥 Download", key=f"download_{doc['id']}"):
                        with open(doc['file_path'], 'rb') as f:
                            st.download_button(
                                label="Click to Download",
                                data=f,
                                file_name=doc['file_name'],
                                mime=doc.get('mime_type', 'application/octet-stream')
                            )
                
                with col2:
                    if st.button("🔄 New Version", key=f"version_{doc['id']}"):
                        st.session_state.version_doc = doc['id']
                        st.rerun()
    else:
        st.info("No documents found")

def render_knowledge_search(company_id):
    """Render AI-powered knowledge search"""
    st.markdown("### 🔍 AI-Powered Knowledge Search")
    
    st.caption("Search across all company data including documents, personnel, equipment, and experience records")
    
    search_type = st.radio("Search Type", ["Keyword Search", "Semantic Search", "Hybrid Search"], horizontal=True)
    
    query = st.text_input("Enter your search query", placeholder="e.g., concrete mixing equipment, bridge construction experience, key personnel with PMP certification...")
    
    if query:
        with st.spinner("Searching..."):
            if search_type == "Semantic Search" or search_type == "Hybrid Search":
                # Generate embedding (simplified - would use actual embedding model)
                import hashlib
                import numpy as np
                
                # Simple mock embedding - replace with actual embedding generation
                def mock_embedding(text):
                    hash_obj = hashlib.md5(text.encode())
                    hash_bytes = hash_obj.digest()
                    return [float(b) / 255.0 for b in hash_bytes[:384]]  # 384-dim mock
                
                query_embedding = mock_embedding(query)
                
                if search_type == "Semantic Search":
                    results = enhanced_db.semantic_search(company_id, query, query_embedding)
                else:
                    results = enhanced_db.hybrid_search(company_id, query, query_embedding)
            else:
                # Keyword search
                results = enhanced_db.keyword_search(company_id, query)
            
            if results:
                st.markdown(f"### Found {len(results)} results")
                
                for result in results:
                    with st.container():
                        st.markdown(f"""
                        <div style="padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 10px;">
                            <strong>{result.get('entity_type', 'Unknown')}</strong>
                            <div style="margin-top: 8px;">{result.get('content', 'No content')[:300]}...</div>
                            <small style="color: #888;">Relevance: {result.get('similarity_score', result.get('relevance', 0)):.2%}</small>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No results found. Try different search terms.")

def render_knowledge_analytics(company_id):
    """Render knowledge repository analytics"""
    st.markdown("### Knowledge Repository Analytics")
    
    # Get analytics data
    analytics = enhanced_db.get_knowledge_analytics(company_id)
    
    if analytics:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Document Growth")
            st.line_chart(analytics.get('document_growth', pd.DataFrame()))
        
        with col2:
            st.markdown("#### Search Activity")
            st.line_chart(analytics.get('search_activity', pd.DataFrame()))
        
        st.markdown("#### Most Searched Terms")
        if analytics.get('top_searches'):
            st.bar_chart(pd.DataFrame(analytics['top_searches']).set_index('term'))
    else:
        st.info("Not enough data for analytics yet")