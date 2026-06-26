# modules/pwd_import_session.py

import streamlit as st
import sqlite3
from datetime import datetime
import json
import pandas as pd
import os

class PWDImportSessionManager:
    """Manages persistent import sessions across multiple days"""
    
    def __init__(self, db_instance):
        self.db = db_instance
        
    
    def _init_session_tables(self):
        """Create tables for tracking import sessions"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Main sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_import_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT NOT NULL,
                edition_year INTEGER NOT NULL,
                version_name TEXT,
                file_name TEXT,
                total_pages INTEGER,
                processed_pages INTEGER DEFAULT 0,
                total_batches INTEGER,
                completed_batches INTEGER DEFAULT 0,
                status TEXT DEFAULT 'in_progress',
                current_batch_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT
            )
        """)
        
        # Batch details table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_import_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                batch_number INTEGER,
                start_page INTEGER,
                end_page INTEGER,
                items_count INTEGER DEFAULT 0,
                rates_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                completed_at TIMESTAMP,
                extracted_data TEXT,
                FOREIGN KEY (session_id) REFERENCES pwd_import_sessions(id) ON DELETE CASCADE
            )
        """)
        
        # Extracted items table (temporary storage)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_import_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                pwd_code TEXT,
                parent_code TEXT,
                description TEXT,
                unit TEXT,
                rates_json TEXT,
                batch_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES pwd_import_sessions(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_session(self, session_name, edition_year, version_name, file_name, total_pages, created_by="system"):
        """Create a new import session"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        batch_size = 10
        total_batches = (total_pages + batch_size - 1) // batch_size
        
        cursor.execute("""
            INSERT INTO pwd_import_sessions 
            (session_name, edition_year, version_name, file_name, total_pages, total_batches, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_name, edition_year, version_name, file_name, total_pages, total_batches, 'in_progress', created_by))
        
        session_id = cursor.lastrowid
        
        # Create batch records
        for batch_num in range(1, total_batches + 1):
            start_page = (batch_num - 1) * batch_size + 1
            end_page = min(batch_num * batch_size, total_pages)
            
            cursor.execute("""
                INSERT INTO pwd_import_batches (session_id, batch_number, start_page, end_page, status)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, batch_num, start_page, end_page, 'pending'))
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def get_active_sessions(self):
        """Get all in-progress sessions"""
        conn = self.db.get_connection()
        df = pd.read_sql_query("""
            SELECT 
                s.id,
                s.session_name,
                s.edition_year,
                s.version_name,
                s.processed_pages,
                s.total_pages,
                s.completed_batches,
                s.total_batches,
                s.last_updated,
                (s.processed_pages * 100.0 / s.total_pages) as progress_percent
            FROM pwd_import_sessions s
            WHERE s.status = 'in_progress'
            ORDER BY s.last_updated DESC
        """, conn)
        conn.close()
        return df
    
    def get_completed_sessions(self):
        """Get completed sessions"""
        conn = self.db.get_connection()
        df = pd.read_sql_query("""
            SELECT 
                s.id,
                s.session_name,
                s.edition_year,
                s.version_name,
                s.processed_pages,
                s.total_pages,
                s.created_at,
                s.last_updated
            FROM pwd_import_sessions s
            WHERE s.status = 'completed'
            ORDER BY s.last_updated DESC
            LIMIT 20
        """, conn)
        conn.close()
        return df
    
    def get_session(self, session_id):
        """Get session details"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM pwd_import_sessions WHERE id = ?", (session_id,))
        session = cursor.fetchone()
        
        if session:
            session_dict = {
                'id': session[0],
                'session_name': session[1],
                'edition_year': session[2],
                'version_name': session[3],
                'file_name': session[4],
                'total_pages': session[5],
                'processed_pages': session[6],
                'total_batches': session[7],
                'completed_batches': session[8],
                'status': session[9],
                'current_batch_data': session[10],
                'created_at': session[11],
                'last_updated': session[12],
                'created_by': session[13]
            }
            
            # Get batches
            cursor.execute("""
                SELECT * FROM pwd_import_batches 
                WHERE session_id = ? 
                ORDER BY batch_number
            """, (session_id,))
            batches = cursor.fetchall()
            
            batch_list = []
            for batch in batches:
                batch_list.append({
                    'id': batch[0],
                    'batch_number': batch[2],
                    'start_page': batch[3],
                    'end_page': batch[4],
                    'items_count': batch[5],
                    'status': batch[7],
                    'completed_at': batch[8]
                })
            
            session_dict['batches'] = batch_list
            
            # Get extracted items
            cursor.execute("""
                SELECT pwd_code, parent_code, description, unit, rates_json, batch_number
                FROM pwd_import_items
                WHERE session_id = ?
                ORDER BY batch_number, pwd_code
            """, (session_id,))
            items = cursor.fetchall()
            
            item_list = []
            for item in items:
                item_list.append({
                    'pwd_code': item[0],
                    'parent_code': item[1],
                    'description': item[2],
                    'unit': item[3],
                    'rates': json.loads(item[4]) if item[4] else {},
                    'batch_number': item[5]
                })
            
            session_dict['items'] = item_list
            
            conn.close()
            return session_dict
        
        conn.close()
        return None
    
    def save_batch_data(self, session_id, batch_number, items):
        """Save extracted batch data"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Save items
        for item in items:
            cursor.execute("""
                INSERT INTO pwd_import_items 
                (session_id, pwd_code, parent_code, description, unit, rates_json, batch_number)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                item.get('pwd_code', ''),
                item.get('parent_code', ''),
                item.get('description', '')[:2000],
                item.get('unit', ''),
                json.dumps(item.get('rates', {})),
                batch_number
            ))
        
        # Update batch status
        cursor.execute("""
            UPDATE pwd_import_batches 
            SET status = 'completed', 
                items_count = ?,
                completed_at = ?
            WHERE session_id = ? AND batch_number = ?
        """, (len(items), datetime.now(), session_id, batch_number))
        
        # Update session progress
        cursor.execute("""
            UPDATE pwd_import_sessions 
            SET completed_batches = completed_batches + 1,
                processed_pages = (SELECT MAX(end_page) FROM pwd_import_batches 
                                   WHERE session_id = ? AND status = 'completed'),
                last_updated = ?
            WHERE id = ?
        """, (session_id, datetime.now(), session_id))
        
        conn.commit()
        conn.close()
    
    def complete_session(self, session_id):
        """Mark session as completed"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE pwd_import_sessions 
            SET status = 'completed', last_updated = ?
            WHERE id = ?
        """, (datetime.now(), session_id))
        conn.commit()
        conn.close()
    
    def delete_session(self, session_id):
        """Delete a session (clean up)"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Delete related data (cascade should handle, but explicit for safety)
        cursor.execute("DELETE FROM pwd_import_items WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM pwd_import_batches WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM pwd_import_sessions WHERE id = ?", (session_id,))
        
        conn.commit()
        conn.close()
    
    def get_next_batch(self, session_id):
        """Get the next pending batch to process"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, batch_number, start_page, end_page
            FROM pwd_import_batches
            WHERE session_id = ? AND status = 'pending'
            ORDER BY batch_number
            LIMIT 1
        """, (session_id,))
        
        batch = cursor.fetchone()
        conn.close()
        
        if batch:
            return {
                'id': batch[0],
                'batch_number': batch[1],
                'start_page': batch[2],
                'end_page': batch[3]
            }
        return None

def render_persistent_import_ui(db, parser):
    """Render persistent import UI with session management"""
    
    session_manager = PWDImportSessionManager(db)
    
    st.markdown("### 🔄 Persistent PWD Import")
    st.caption("Save progress and resume later - import large PDFs over multiple days")
    
    # Check if we have pre-saved settings from the wizard
    if hasattr(st.session_state, 'pwd_persistent_settings'):
        settings = st.session_state.pwd_persistent_settings
        default_session_name = f"PWD Import {settings['edition_year']}"
        default_version_name = settings['version_name']
        default_file = settings['file']
    else:
        settings = None
        default_session_name = f"PWD Import {datetime.now().year}"
        default_version_name = f"PWD Schedule {datetime.now().year}"
        default_file = None
    
    # Check for active sessions
    active_sessions = session_manager.get_active_sessions()
    
    if not active_sessions.empty:
        st.markdown("#### 🔄 Resume Previous Import")
        
        for _, session in active_sessions.iterrows():
            with st.expander(f"📂 {session['session_name']} - {session['progress_percent']:.1f}% Complete", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Edition", session['edition_year'])
                with col2:
                    st.metric("Progress", f"{session['processed_pages']}/{session['total_pages']} pages")
                with col3:
                    st.metric("Batches", f"{session['completed_batches']}/{session['total_batches']}")
                with col4:
                    st.metric("Last Active", session['last_updated'][:16])
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button(f"▶️ Resume", key=f"resume_{session['id']}"):
                        st.session_state.pwd_resume_session_id = session['id']
                        st.rerun()
                with col_b:
                    if st.button(f"🗑️ Delete", key=f"delete_{session['id']}"):
                        session_manager.delete_session(session['id'])
                        st.rerun()
        
        st.markdown("---")
        st.markdown("#### 🆕 Start New Import")
    
    # New import form
    col1, col2 = st.columns(2)
    
    with col1:
        session_name = st.text_input(
            "Session Name",
            value=default_session_name,
            placeholder="e.g., PWD Import Dec 2024",
            help="Give this import session a name to identify it later"
        )
        edition_year = st.number_input(
            "Edition Year", 
            min_value=2020, 
            max_value=2030, 
            value=settings['edition_year'] if settings else datetime.now().year
        )
    
    with col2:
        version_name = st.text_input(
            "Version Name",
            value=default_version_name,
            placeholder="e.g., PWD Schedule 2025"
        )
        created_by = st.text_input("Created By", value=st.session_state.get('username', 'admin'))
    
    # File upload - use pre-loaded file if available
    if default_file:
        st.info(f"📁 File already selected: {default_file.name}")
        uploaded_file = default_file
    else:
        uploaded_file = st.file_uploader("Upload PWD PDF", type=["pdf"])
    
    if uploaded_file and session_name and st.button("🚀 Start New Persistent Import", type="primary"):
        # Get total pages
        temp_path = "temp_pdf.pdf"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        import pdfplumber
        with pdfplumber.open(temp_path) as pdf:
            total_pages = len(pdf.pages)
        os.remove(temp_path)
        
        # Create session
        session_id = session_manager.create_session(
            session_name=session_name,
            edition_year=edition_year,
            version_name=version_name,
            file_name=uploaded_file.name,
            total_pages=total_pages,
            created_by=created_by
        )
        
        # Store file in session for processing
        st.session_state.pwd_active_import_session = {
            'session_id': session_id,
            'file': uploaded_file,
            'total_pages': total_pages,
            'batch_size': 10,
            'edition_year': edition_year,
            'version_name': version_name
        }
        
        # Clear the temporary settings
        if hasattr(st.session_state, 'pwd_persistent_settings'):
            del st.session_state.pwd_persistent_settings
        
        st.success(f"✅ Session '{session_name}' created! Total pages: {total_pages}")
        st.rerun()
    
    # Process active import session
    if 'pwd_active_import_session' in st.session_state:
        render_active_import_processor(st.session_state.pwd_active_import_session, session_manager, parser)

def render_active_import_processor(session_data, session_manager, parser):
    """Process the active import session"""
    
    st.markdown("---")
    st.markdown("### 📥 Processing Import Session")
    
    session_id = session_data['session_id']
    session = session_manager.get_session(session_id)
    
    if not session:
        st.error("Session not found")
        del st.session_state.pwd_active_import_session
        st.rerun()
    
    # Show session info
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Session", session['session_name'])
    with col2:
        st.metric("Progress", f"{session['processed_pages']}/{session['total_pages']} pages")
    with col3:
        st.metric("Batches Done", f"{session['completed_batches']}/{session['total_batches']}")
    with col4:
        st.metric("Items Found", len(session.get('items', [])))
    
    # Progress bar
    progress_pct = (session['processed_pages'] / session['total_pages']) * 100
    st.progress(progress_pct / 100)
    
    # Get next batch to process
    next_batch = session_manager.get_next_batch(session_id)
    
    if next_batch:
        st.markdown(f"#### 📄 Next Batch: Pages {next_batch['start_page']} - {next_batch['end_page']}")
        
        if st.button(f"▶️ Process Batch {next_batch['batch_number']}", type="primary", use_container_width=True):
            with st.spinner(f"Processing pages {next_batch['start_page']} to {next_batch['end_page']}..."):
                # Parse the batch
                items = parse_page_range(session_data['file'], next_batch['start_page'], next_batch['end_page'], parser)
                
                # Save to session
                session_manager.save_batch_data(session_id, next_batch['batch_number'], items)
                
                st.success(f"✅ Batch {next_batch['batch_number']} complete! Found {len(items)} items.")
                st.rerun()
    
    # Check if complete
    if session['completed_batches'] >= session['total_batches']:
        st.balloons()
        st.success("🎉 All batches processed successfully!")
        
        if st.button("📊 Build Hierarchy & Continue to Review"):
            # Build hierarchy from all items
            hierarchy = build_hierarchy_from_items(session.get('items', []), parser)
            
            st.session_state.pwd_import_data = {
                'hierarchy': hierarchy,
                'edition_year': session['edition_year'],
                'version_name': session['version_name'],
                'dry_run': False,
                'timestamp': datetime.now().isoformat(),
                'session_id': session_id
            }
            
            # Mark session as completed
            session_manager.complete_session(session_id)
            
            # Clean up
            del st.session_state.pwd_active_import_session
            st.session_state.pwd_wizard_step = 3
            st.rerun()
    
    # Show completed batches
    if session.get('batches'):
        st.markdown("---")
        st.markdown("#### ✅ Completed Batches")
        
        completed = [b for b in session['batches'] if b['status'] == 'completed']
        if completed:
            completed_df = pd.DataFrame(completed)
            st.dataframe(completed_df[['batch_number', 'start_page', 'end_page', 'items_count']], 
                        use_container_width=True, hide_index=True)
    
    # Cancel option
    if st.button("❌ Cancel Import", use_container_width=True):
        if st.button("Confirm Cancel", type="secondary"):
            session_manager.delete_session(session_id)
            del st.session_state.pwd_active_import_session
            st.rerun()


def parse_page_range(uploaded_file, start_page, end_page, parser):
    """Parse a specific page range"""
    
    temp_path = "temp_parse.pdf"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    items = []
    import pdfplumber
    
    with pdfplumber.open(temp_path) as pdf:
        for page_num in range(start_page - 1, end_page):
            if page_num < len(pdf.pages):
                page = pdf.pages[page_num]
                text = page.extract_text()
                if not text:
                    continue
                
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5,
                })
                
                if tables:
                    for table in tables:
                        page_items = parser._parse_table(table)
                        items.extend(page_items)
                else:
                    page_items = parser._parse_text(text)
                    items.extend(page_items)
    
    os.remove(temp_path)
    return items


def build_hierarchy_from_items(items, parser):
    """Build hierarchy from collected items"""
    return parser._organize_hierarchy(items)