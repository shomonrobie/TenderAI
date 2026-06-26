# modules/company_knowledge_repo.py

import streamlit as st
import pandas as pd
from datetime import datetime
from modules.rbac import can_view_dashboard, can_manage_team
from database.unified_db_manager import UnifiedDatabaseManager
db = UnifiedDatabaseManager()
def render_company_knowledge_repo():
    """Render the centralized company knowledge repository"""
    
    company_id = st.session_state.company_id
    
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
        "🔍 Search"
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

def render_overview_tab(company_id):
    """Render overview with statistics"""
    
    # Get counts
    conn = db.get_connection()
    cursor = conn.cursor()
    
    stats = {}
    tables = ['personnel', 'equipment', 'experience_record', 'financial_capacity', 'document_registry']
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE company_id = ?", (company_id,))
        stats[table] = cursor.fetchone()[0]
    
    conn.close()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("👥 Personnel", stats.get('personnel', 0))
    with col2:
        st.metric("🏗️ Equipment", stats.get('equipment', 0))
    with col3:
        st.metric("📋 Experience", stats.get('experience_record', 0))
    with col4:
        st.metric("💰 Financial", stats.get('financial_capacity', 0))
    with col5:
        st.metric("📄 Documents", stats.get('document_registry', 0))
    
    # Data completeness
    st.markdown("### Data Completeness")
    
    completeness = {
        'Company Profile': db.get_company_profile(company_id) is not None,
        'Personnel': stats.get('personnel', 0) > 0,
        'Equipment': stats.get('equipment', 0) > 0,
        'Experience': stats.get('experience_record', 0) > 0,
        'Financial': stats.get('financial_capacity', 0) > 0
    }
    
    for category, is_complete in completeness.items():
        status = "✅" if is_complete else "⚠️"
        st.write(f"{status} {category}")

def render_company_info_tab(company_id):
    """Render company information tab"""
    
    st.markdown("### Company Information")
    
    profile = db.get_company_profile(company_id)
    
    with st.form("company_info_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            legal_name = st.text_input("Legal Name", value=profile.get('legal_name', '') if profile else '')
            trade_name = st.text_input("Trade Name", value=profile.get('trade_name', '') if profile else '')
            registration_number = st.text_input("Registration Number", value=profile.get('registration_number', '') if profile else '')
            phone_primary = st.text_input("Primary Phone", value=profile.get('phone_primary', '') if profile else '')
            email_primary = st.text_input("Primary Email", value=profile.get('email_primary', '') if profile else '')
        
        with col2:
            address = st.text_area("Registered Address", value=profile.get('registered_address', '') if profile else '')
            division = st.text_input("Division", value=profile.get('division', '') if profile else '')
            district = st.text_input("District", value=profile.get('district', '') if profile else '')
            website = st.text_input("Website", value=profile.get('website', '') if profile else '')
        
        if st.form_submit_button("Save Company Info"):
            profile_data = {
                'legal_name': legal_name,
                'trade_name': trade_name,
                'registration_number': registration_number,
                'phone_primary': phone_primary,
                'email_primary': email_primary,
                'registered_address': address,
                'division': division,
                'district': district,
                'website': website,
                'updated_by': st.session_state.user_id
            }
            
            if db.save_company_profile(company_id, profile_data):
                st.success("Company information saved!")
                st.rerun()

def render_personnel_tab(company_id):
    """Render personnel management tab"""
    
    st.markdown("### Personnel Management")
    
    # Add personnel form
    with st.expander("➕ Add New Personnel", expanded=False):
        with st.form("add_personnel_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                full_name = st.text_input("Full Name *")
                designation = st.text_input("Designation *")
                employee_id = st.text_input("Employee ID")
                phone = st.text_input("Phone")
            
            with col2:
                email = st.text_input("Email")
                joining_date = st.date_input("Joining Date")
                skills = st.text_input("Skills (comma-separated)")
                is_key = st.checkbox("Key Personnel")
            
            if st.form_submit_button("Add Personnel"):
                if full_name and designation:
                    personnel_data = {
                        'full_name': full_name,
                        'designation': designation,
                        'employee_id': employee_id,
                        'personal_phone': phone,
                        'personal_email': email,
                        'joining_date': joining_date,
                        'skills': skills.split(',') if skills else [],
                        'is_key_personnel': is_key,
                        'created_by': st.session_state.user_id
                    }
                    
                    result = db.add_personnel(company_id, personnel_data)
                    if result:
                        st.success(f"Added {full_name}")
                        st.rerun()
    
    # List personnel
    personnel = db.get_personnel(company_id)
    
    if not personnel.empty:
        for _, person in personnel.iterrows():
            with st.expander(f"👤 {person['full_name']} - {person['designation']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Employee ID:** {person.get('employee_id', 'N/A')}")
                    st.write(f"**Phone:** {person.get('personal_phone', 'N/A')}")
                with col2:
                    st.write(f"**Email:** {person.get('personal_email', 'N/A')}")
                    st.write(f"**Key Personnel:** {'✅' if person.get('is_key_personnel') else '❌'}")

def render_equipment_tab(company_id):
    """Render equipment management tab"""
    
    st.markdown("### Equipment Inventory")
    
    with st.expander("➕ Add Equipment", expanded=False):
        with st.form("add_equipment_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                equipment_name = st.text_input("Equipment Name *")
                equipment_type = st.selectbox("Type", ["Excavator", "Bulldozer", "Crane", "Loader", "Dump Truck", "Other"])
                model = st.text_input("Model")
                serial_number = st.text_input("Serial Number")
            
            with col2:
                capacity = st.number_input("Capacity", min_value=0.0, step=0.1)
                ownership_type = st.selectbox("Ownership", ["Owned", "Leased", "Rented"])
                purchase_date = st.date_input("Purchase Date")
                purchase_cost = st.number_input("Purchase Cost (BDT)", min_value=0.0, step=10000.0)
            
            if st.form_submit_button("Add Equipment"):
                if equipment_name:
                    equipment_data = {
                        'equipment_name': equipment_name,
                        'equipment_type': equipment_type,
                        'model': model,
                        'serial_number': serial_number,
                        'capacity': capacity,
                        'ownership_type': ownership_type.lower(),
                        'purchase_date': purchase_date,
                        'purchase_cost': purchase_cost,
                        'current_status': 'available',
                        'created_by': st.session_state.user_id
                    }
                    
                    result = db.add_equipment(company_id, equipment_data)
                    if result:
                        st.success(f"Added {equipment_name}")
                        st.rerun()
    
    # List equipment
    equipment = db.get_equipment(company_id)
    
    if not equipment.empty:
        for _, equip in equipment.iterrows():
            status_icon = {
                'available': '🟢',
                'deployed': '🔵',
                'maintenance': '🟡',
                'repair': '🔴'
            }.get(equip.get('current_status', 'idle'), '⚪')
            
            with st.expander(f"{status_icon} {equip['equipment_name']} - {equip.get('model', 'N/A')}"):
                st.write(f"**Type:** {equip.get('equipment_type', 'N/A')}")
                st.write(f"**Serial:** {equip.get('serial_number', 'N/A')}")
                st.write(f"**Capacity:** {equip.get('capacity', 'N/A')}")

def render_experience_tab(company_id):
    """Render experience/projects tab"""
    
    st.markdown("### Project Experience")
    
    with st.expander("➕ Add Experience", expanded=False):
        with st.form("add_experience_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                project_name = st.text_input("Project Name *")
                client_name = st.text_input("Client Name *")
                contract_value = st.number_input("Contract Value (BDT)", min_value=0.0, step=100000.0)
            
            with col2:
                completion_date = st.date_input("Completion Date")
                nature_of_work = st.text_area("Nature of Work")
                is_completed = st.checkbox("Completed")
            
            if st.form_submit_button("Add Experience"):
                if project_name and client_name:
                    experience_data = {
                        'project_name': project_name,
                        'client_name': client_name,
                        'contract_value': contract_value,
                        'completion_date': completion_date,
                        'nature_of_work': nature_of_work,
                        'is_completed': is_completed,
                        'created_by': st.session_state.user_id
                    }
                    
                    result = db.add_experience(company_id, experience_data)
                    if result:
                        st.success(f"Added {project_name}")
                        st.rerun()
    
    # List experiences
    experiences = db.get_experiences(company_id)
    
    if not experiences.empty:
        for _, exp in experiences.iterrows():
            with st.expander(f"📋 {exp['project_name']} - {exp['client_name']}"):
                st.write(f"**Value:** ৳{exp.get('contract_value', 0):,.0f}")
                st.write(f"**Completed:** {exp.get('completion_date', 'N/A')}")
                st.write(f"**Nature:** {exp.get('nature_of_work', 'N/A')}")

def render_financial_tab(company_id):
    """Render financial capacity tab"""
    
    st.markdown("### Financial Capacity")
    
    with st.expander("➕ Add Financial Record", expanded=False):
        with st.form("add_financial_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                fiscal_year = st.text_input("Fiscal Year *")
                annual_turnover = st.number_input("Annual Turnover (BDT)", min_value=0.0, step=1000000.0)
                net_worth = st.number_input("Net Worth (BDT)", min_value=0.0, step=1000000.0)
            
            with col2:
                working_capital = st.number_input("Working Capital (BDT)", min_value=0.0, step=1000000.0)
                credit_limit = st.number_input("Credit Limit (BDT)", min_value=0.0, step=1000000.0)
                is_audited = st.checkbox("Audited")
            
            if st.form_submit_button("Add Financial Record"):
                if fiscal_year:
                    financial_data = {
                        'fiscal_year': fiscal_year,
                        'annual_turnover': annual_turnover,
                        'net_worth': net_worth,
                        'working_capital': working_capital,
                        'credit_limit': credit_limit,
                        'is_audited': is_audited
                    }
                    
                    result = db.add_financial_capacity(company_id, financial_data)
                    if result:
                        st.success(f"Added financial record for {fiscal_year}")
                        st.rerun()
    
    # List financial records
    financial = db.get_financial_records(company_id)
    
    if not financial.empty:
        st.dataframe(financial, use_container_width=True)

def render_documents_tab(company_id):
    """Render document management tab"""
    
    st.markdown("### Document Management")
    
    with st.expander("📤 Upload Document", expanded=False):
        uploaded_file = st.file_uploader("Choose file", type=['pdf', 'doc', 'docx', 'jpg', 'png', 'xlsx'])
        
        if uploaded_file:
            col1, col2 = st.columns(2)
            
            with col1:
                document_name = st.text_input("Document Name", value=uploaded_file.name)
                document_type = st.selectbox("Document Type", 
                    ["trade_license", "tin", "vat", "certificate", "experience", "other"])
            
            with col2:
                tags = st.text_input("Tags (comma-separated)")
                description = st.text_area("Description")
            
            if st.button("Upload"):
                import os
                from datetime import datetime
                
                # Create directory
                doc_dir = f"data/documents/{company_id}"
                os.makedirs(doc_dir, exist_ok=True)
                
                # Save file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = "".join(c for c in document_name if c.isalnum() or c in '._-')[:50]
                file_path = f"{doc_dir}/{timestamp}_{safe_name}"
                
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                document_data = {
                    'document_name': document_name,
                    'document_type': document_type,
                    'file_path': file_path,
                    'file_name': uploaded_file.name,
                    'file_size': len(uploaded_file.getvalue()),
                    'mime_type': uploaded_file.type,
                    'description': description,
                    'tags': [t.strip() for t in tags.split(',')] if tags else [],
                    'uploaded_by': st.session_state.user_id
                }
                
                doc_id = db.add_document(company_id, document_data, uploaded_file.getvalue())
                
                if doc_id:
                    st.success(f"Uploaded {document_name}")
                    st.rerun()
    
    # List documents
    documents = db.get_documents(company_id)
    
    if documents:
        for doc in documents:
            with st.expander(f"📄 {doc['document_name']}"):
                st.write(f"**Type:** {doc['document_type']}")
                st.write(f"**Tags:** {doc.get('tags', 'N/A')}")
                st.write(f"**Uploaded:** {doc.get('uploaded_at', 'N/A')[:16] if doc.get('uploaded_at') else 'N/A'}")
                
                if st.button(f"Download", key=f"download_{doc['id']}"):
                    with open(doc['file_path'], 'rb') as f:
                        st.download_button(
                            "Click to Download",
                            data=f,
                            file_name=doc['file_name'],
                            key=f"download_btn_{doc['id']}"
                        )

def render_search_tab(company_id):
    """Render AI-powered search tab"""
    
    st.markdown("### 🔍 Search Knowledge Base")
    
    search_query = st.text_input("Search", placeholder="e.g., concrete mixing equipment, bridge construction experience...")
    
    if search_query:
        with st.spinner("Searching..."):
            results = db.search_knowledge_base(company_id, search_query)
            
            if results:
                st.markdown(f"### Found {len(results)} results")
                
                for result in results:
                    with st.container():
                        st.markdown(f"""
                        <div style="padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 10px;">
                            <strong>{result.get('source', 'Unknown').upper()}</strong>
                            <div style="margin-top: 8px;">{result.get('name', '')}</div>
                            <small>{result.get('designation', result.get('type', result.get('client', '')))}</small>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No results found")