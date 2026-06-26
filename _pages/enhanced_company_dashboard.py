# _pages/enhanced_company_dashboard.py - NEW FILE

import streamlit as st
import pandas as pd
from datetime import datetime

from modules.rbac import can_view_dashboard, can_manage_team, can_export_data
from modules.subscription_manager import check_subscription_and_permission
from database.unified_db_manager import UnifiedDatabaseManager
db = UnifiedDatabaseManager()

def show():
    """Enhanced Company Dashboard with Knowledge Repository"""
    
    # Verify access
    if st.session_state.user_role not in ['company_admin', 'admin', 'system_admin', 'manager', 'analyst', 'viewer']:
        st.error("🔒 Access denied. Company access required.")
        return
    
    company_id = st.session_state.company_id
    
    st.markdown("""
    <div class="main-header">
        <h1>🏢 Enhanced Company Knowledge Repository</h1>
        <p>Centralized repository for company information, documents, and AI-powered search</p>
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
        "🔍 AI Search"
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
        render_ai_search(company_id)

def render_knowledge_dashboard(company_id):
    """Render knowledge repository dashboard"""
    st.markdown("### Knowledge Repository Overview")
    
    # Get counts from enhanced_db
    conn = db.get_connection()
    cursor = conn.cursor()
    
    counts = {}
    tables = ['personnel', 'equipment', 'experience_record', 'financial_capacity', 'document_registry']
    
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE company_id = ?", (company_id,))
        counts[table] = cursor.fetchone()[0]
    
    # Get extension usage
    cursor.execute("""
        SELECT COUNT(*) FROM extension_auto_fill_log 
        WHERE company_id = ? AND filled_at >= date('now', 'start of month')
    """, (company_id,))
    extension_used = cursor.fetchone()[0] or 0
    
    conn.close()
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("👥 Personnel", counts.get('personnel', 0))
    with col2:
        st.metric("🏗️ Equipment", counts.get('equipment', 0))
    with col3:
        st.metric("📋 Experience", counts.get('experience_record', 0))
    with col4:
        st.metric("💰 Financial", counts.get('financial_capacity', 0))
    with col5:
        st.metric("📄 Documents", counts.get('document_registry', 0))
    with col6:
        st.metric("🤖 Extension Fills", extension_used)
    
    st.markdown("---")
    
    # Data completeness
    st.markdown("### Data Completeness")
    
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
    
    profile = db.get_company_profile(company_id)
    
    with st.form("company_profile_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            legal_name = st.text_input("Legal Name *", value=profile.get('legal_name', '') if profile else '')
            trade_name = st.text_input("Trade Name", value=profile.get('trade_name', '') if profile else '')
            registration_number = st.text_input("Registration Number", value=profile.get('registration_number', '') if profile else '')
            phone_primary = st.text_input("Primary Phone", value=profile.get('phone_primary', '') if profile else '')
            email_primary = st.text_input("Primary Email", value=profile.get('email_primary', '') if profile else '')
        
        with col2:
            registered_address = st.text_area("Registered Address", value=profile.get('registered_address', '') if profile else '')
            division = st.selectbox("Division", 
                ["Dhaka", "Chattogram", "Khulna", "Rajshahi", "Rangpur", "Barishal", "Sylhet", "Mymensingh"],
                index=0 if not profile or not profile.get('division') else 
                      ["Dhaka", "Chattogram", "Khulna", "Rajshahi", "Rangpur", "Barishal", "Sylhet", "Mymensingh"].index(profile.get('division', 'Dhaka')))
            district = st.text_input("District", value=profile.get('district', '') if profile else '')
            website = st.text_input("Website", value=profile.get('website', '') if profile else '')
        
        submitted = st.form_submit_button("Save Profile")
        
        if submitted and legal_name:
            profile_data = {
                'legal_name': legal_name,
                'trade_name': trade_name,
                'registration_number': registration_number,
                'phone_primary': phone_primary,
                'email_primary': email_primary,
                'registered_address': registered_address,
                'division': division,
                'district': district,
                'website': website,
                'updated_by': st.session_state.user_id
            }
            
            if db.save_company_profile(company_id, profile_data):
                st.success("Company profile saved!")
                st.rerun()
            else:
                st.error("Failed to save profile")

def render_personnel_management(company_id):
    """Render personnel management"""
    st.markdown("### Personnel Management")
    
    # Check permission for adding
    can_edit = st.session_state.user_role in ['admin', 'system_admin', 'company_admin', 'manager']
    
    if can_edit:
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
    else:
        st.info("No personnel records found")

def render_equipment_management(company_id):
    """Render equipment management"""
    st.markdown("### Equipment Inventory")
    
    can_edit = st.session_state.user_role in ['admin', 'system_admin', 'company_admin', 'manager']
    
    if can_edit:
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
    else:
        st.info("No equipment records found")

def render_experience_management(company_id):
    """Render experience/projects"""
    st.markdown("### Project Experience")
    
    can_edit = st.session_state.user_role in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst']
    
    if can_edit:
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
    
    experiences = db.get_experiences(company_id)
    
    if not experiences.empty:
        for _, exp in experiences.iterrows():
            with st.expander(f"📋 {exp['project_name']} - {exp['client_name']}"):
                st.write(f"**Value:** ৳{exp.get('contract_value', 0):,.0f}")
                st.write(f"**Completed:** {exp.get('completion_date', 'N/A')}")
                st.write(f"**Nature:** {exp.get('nature_of_work', 'N/A')}")
    else:
        st.info("No experience records found")

def render_financial_management(company_id):
    """Render financial capacity"""
    st.markdown("### Financial Capacity")
    
    can_edit = st.session_state.user_role in ['admin', 'system_admin', 'company_admin']
    
    if can_edit:
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
    
    financial = db.get_financial_records(company_id)
    
    if not financial.empty:
        st.dataframe(financial, use_container_width=True)
    else:
        st.info("No financial records found")

def render_document_management(company_id):
    """Render document management"""
    st.markdown("### Document Management")
    
    can_upload = st.session_state.user_role in ['admin', 'system_admin', 'company_admin', 'manager', 'analyst', 'data_entry']
    
    if can_upload:
        with st.expander("📤 Upload Document", expanded=False):
            uploaded_file = st.file_uploader("Choose file", type=['pdf', 'doc', 'docx', 'jpg', 'png', 'xlsx', 'csv'])
            
            if uploaded_file:
                col1, col2 = st.columns(2)
                
                with col1:
                    document_name = st.text_input("Document Name", value=uploaded_file.name)
                    document_type = st.selectbox("Document Type", 
                        ["trade_license", "tin", "vat", "certificate", "experience", "financial_report", "other"])
                
                with col2:
                    tags = st.text_input("Tags (comma-separated)")
                    description = st.text_area("Description")
                
                if st.button("Upload"):
                    import os
                    from datetime import datetime
                    
                    doc_dir = f"data/documents/{company_id}"
                    os.makedirs(doc_dir, exist_ok=True)
                    
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
    else:
        st.info("No documents uploaded")

def render_ai_search(company_id):
    """Render AI-powered search"""
    st.markdown("### 🔍 AI-Powered Knowledge Search")
    
    st.caption("Search across all company data using semantic and keyword search")
    
    search_type = st.radio("Search Type", ["Keyword Search", "Semantic Search", "Hybrid Search"], horizontal=True)
    
    query = st.text_input("Enter your search query", placeholder="e.g., concrete mixing equipment, bridge construction experience, key personnel with PMP...")
    
    if query:
        with st.spinner("Searching..."):
            if search_type == "Semantic Search" or search_type == "Hybrid Search":
                # For now, use keyword search as semantic requires embeddings
                results = db.keyword_search(company_id, query)
            else:
                results = db.keyword_search(company_id, query)
            
            if results:
                st.markdown(f"### Found {len(results)} results")
                
                for result in results:
                    with st.container():
                        st.markdown(f"""
                        <div style="padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 10px;">
                            <strong>{result.get('entity_type', 'Document').upper()}</strong>
                            <div style="margin-top: 8px;">{result.get('content', 'No content')[:300]}...</div>
                            <small style="color: #888;">Relevance: {result.get('relevance', 0):.2%}</small>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No results found. Try different search terms.")