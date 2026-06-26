# modules/pwd_import_wizard.py

import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime
import pdfplumber
from modules.unified_version_manager import register_version_after_import
from modules.unified_rollback_manager import UnifiedRollbackManager
from modules.progress_tracker import ProgressTracker, BatchProgressTracker, render_batch_control_ui

from utils.rate_import_helpers import (
    save_temp_file,
    parse_quick_test,
    parse_full_document,
    init_persistent_import,
    fix_description_spacing, 
    get_pdf_total_pages,
    parse_page_range,
    build_hierarchy_from_items,
    hierarchy_to_dataframe,
    restore_text_spaces,
    get_column_config,
    find_issues,           # NEW - for finding issues
    validate_pwd_data,     # For validation with UI display
    auto_fix_pwd_issues,
    get_issues_summary     # Optional - for summary stats
)

class PWDImportWizard:
    """Step-by-step wizard for PWD rate schedule import with incremental parsing"""
    
    def __init__(self, db_instance, parser_instance=None):
        self.db = db_instance
        # Allow passing parser or create default (for consistency with LGED)
        from modules.parse_pwd_pdf import PWDParserWithHierarchy
        self.parser = parser_instance if parser_instance else PWDParserWithHierarchy()
        self.rollback_manager = UnifiedRollbackManager(db_instance)
        # Add db_manager for consistency (optional, for future use)
        self.db_manager = None  # PWD may not need this yet

    def render(self):
        """Render the wizard interface"""
        
        st.markdown("""
        <div class="main-header">
            <h1>🏗️ PWD Rate Schedule Import Wizard</h1>
            <p>Step-by-step guide to import, validate, and update PWD rates</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Track current step
        if 'pwd_wizard_step' not in st.session_state:
            st.session_state.pwd_wizard_step = 1
        if 'pwd_import_data' not in st.session_state:
            st.session_state.pwd_import_data = None
        if 'pwd_batch_status' not in st.session_state:
            st.session_state.pwd_batch_status = {}
        
        # Step indicators
        self._show_step_indicator()
        
        # Render current step
        if st.session_state.pwd_wizard_step == 1:
            self._step1_upload_and_config()
        elif st.session_state.pwd_wizard_step == 2:
            self._step2_incremental_import()
        elif st.session_state.pwd_wizard_step == 3:
            self._step3_review_and_edit()
        elif st.session_state.pwd_wizard_step == 4:
            self._step4_validate_and_save()  # Your existing validation step
        elif st.session_state.pwd_wizard_step == 5:
            self._step5_rollback_options()   # New rollback step
        elif st.session_state.pwd_wizard_step == 6:
            self._step6_complete()            # Completion step

    
    def _show_step_indicator(self):
        """Show progress steps"""
        
        steps = [
            ("1️⃣ Upload", 1),
            ("2️⃣ Import Pages", 2),
            ("3️⃣ Review & Edit", 3),
            ("4️⃣ Validate", 4),
            ("5️⃣ Rollback", 5),
            ("6️⃣ Complete", 6)
        ]
        
        cols = st.columns(len(steps))
        for i, (label, step_num) in enumerate(steps):
            with cols[i]:
                if step_num < st.session_state.pwd_wizard_step:
                    st.markdown(f"✅ **{label}**")
                elif step_num == st.session_state.pwd_wizard_step:
                    st.markdown(f"🔵 **{label}**")
                else:
                    st.markdown(f"⚪ {label}")
        
        st.markdown("---")

    
    def _step1_upload_and_config(self):
        """Step 1: Upload PDF and configure import settings"""
        
        st.markdown("### Step 1: Upload PWD Rate Schedule")
        
        uploaded_file = st.file_uploader(
            "📄 **Select PWD PDF File**",
            type=["pdf"],
            help="Upload the official PWD Rate Schedule PDF",
            key="pwd_upload"
        )
        
        if uploaded_file:
            # Get total pages
            temp_path = "temp_pwd_pages.pdf"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            with pdfplumber.open(temp_path) as pdf:
                total_pages = len(pdf.pages)
            
            os.remove(temp_path)
            
            st.info(f"📁 File: {uploaded_file.name} | 📄 Total Pages: {total_pages}")
            st.session_state.pwd_total_pages = total_pages
        
        st.markdown("---")
        st.markdown("### ⚙️ Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            edition_year = st.number_input(
                "📅 Edition Year",
                min_value=2020,
                max_value=2030,
                value=2022,
                help="Select the year of this rate schedule"
            )
        
        with col2:
            version_name = st.text_input(
                "📌 Version Name",
                value=f"PWD Schedule {edition_year}",
                help="Give this version a descriptive name"
            )
        
        st.markdown("---")
        st.markdown("### 🚀 Import Strategy")
        
        import_strategy = st.radio(
            "Choose import method:",
            options=[
                "⚡ Quick Test (First 10 pages only)",
                "📑 Batch Import (Process in chunks with progress)",
                "💾 Persistent Import (Save progress, resume later)",
                "🎯 Full Import (All pages at once)"
            ],
            help="Quick Test is fastest for validation. Batch Import lets you monitor progress. Persistent Import saves progress across sessions."
        )
        
        # Show additional options based on strategy
        batch_size = 10  # Default
        if import_strategy == "📑 Batch Import (Process in chunks with progress)":
            batch_size = st.slider("Batch Size (pages per batch)", min_value=5, max_value=50, value=10)
        
        st.markdown("---")
        st.markdown("### 🔄 Rollback Options")
        
        col_r1, col_r2 = st.columns(2)
        
        with col_r1:
            create_snapshot = st.checkbox(
                "📸 Create rollback snapshot before import",
                value=True,
                help="Saves current state so you can rollback if needed"
            )
        
        with col_r2:
            snapshot_name = st.text_input(
                "Snapshot name (if enabled)",
                value=f"Before PWD Import {edition_year}",
                disabled=not create_snapshot
            )
        
        st.info("**Zone Information:**\n"
                "- Dhaka & Mymensingh Division\n"
                "- Chattogram & Sylhet Division\n"
                "- Khulna & Barishal Division\n"
                "- Rajshahi & Rangpur Division")
        
        st.markdown("---")
        
        # Action buttons
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            dry_run = st.checkbox(
                "🔍 Dry Run (Preview only, no database save)",
                value=True,
                help="Test parsing without saving to database"
            )
        
        with col_btn2:
            if uploaded_file:
                if st.button("🚀 **Start Import**", type="primary", use_container_width=True):
                    # Store settings
                    st.session_state.pwd_import_settings = {
                        'file': uploaded_file,
                        'edition_year': edition_year,
                        'version_name': version_name,
                        'dry_run': dry_run,
                        'import_strategy': import_strategy,
                        'batch_size': batch_size,
                        'create_snapshot': create_snapshot,
                        'snapshot_name': snapshot_name
                    }
                    
                    # Create rollback snapshot if requested
                    if create_snapshot and not dry_run:
                        with st.spinner("Creating rollback snapshot..."):
                            from modules.unified_rollback_manager import UnifiedRollbackManager
                            rollback_manager = UnifiedRollbackManager(self.db)
                            snapshot_id = rollback_manager.create_snapshot(
                                source='PWD',
                                version_id=None,
                                snapshot_name=snapshot_name,
                                created_by=st.session_state.get('username', 'admin'),
                                description=f"Auto-snapshot before PWD {edition_year} import",
                                is_auto=True
                            )
                            st.session_state.pwd_rollback_snapshot = snapshot_id
                            st.success("✅ Rollback snapshot created")
                    
                    # Handle different import strategies
                    if import_strategy == "⚡ Quick Test (First 10 pages only)":
                        result = parse_quick_test(
                            parser=self.parser,
                            settings=st.session_state.pwd_import_settings,
                            source='PWD'
                        )
                        st.session_state.pwd_import_data = result
                        st.session_state.pwd_wizard_step = 3
                        st.rerun()
                        
                    elif import_strategy == "📑 Batch Import (Process in chunks with progress)":
                        from modules.progress_tracker import BatchProgressTracker
                        
                        # Initialize batch tracker
                        batch_tracker = BatchProgressTracker(self.db)
                        batch_tracker.set_source('pwd')
                        batch_tracker.init_session(
                            total_pages=st.session_state.pwd_total_pages,
                            batch_size=batch_size
                        )
                        st.session_state.pwd_batch_tracker = batch_tracker
                        st.session_state.pwd_wizard_step = 2
                        st.rerun()
                        
                    elif import_strategy == "💾 Persistent Import (Save progress, resume later)":
                        init_persistent_import()
                        # For now, treat like batch import until fully implemented
                        st.session_state.pwd_wizard_step = 2
                        st.rerun()
                        
                    else:  # Full Import
                        result = parse_full_document(
                            parser=self.parser,
                            settings=st.session_state.pwd_import_settings,
                            source='PWD'
                        )
                        st.session_state.pwd_import_data = result
                        st.session_state.pwd_wizard_step = 3
                        st.rerun()

            else:
                st.button("🚀 **Start Import**", disabled=True, use_container_width=True)


    
    def _init_batch_import(self):
        """Initialize batch import session state"""
        
        st.session_state.pwd_batch_status = {
            'current_batch': 0,
            'total_batches': 0,
            'processed_pages': 0,
            'total_pages': st.session_state.pwd_total_pages,
            'items_found': 0,
            'rates_found': 0,
            'batches_completed': [],
            'is_complete': False,
            'all_items': []
        }
        
        # Calculate batches (10 pages per batch)
        batch_size = 10
        total_batches = (st.session_state.pwd_total_pages + batch_size - 1) // batch_size
        st.session_state.pwd_batch_status['total_batches'] = total_batches
        st.session_state.pwd_batch_status['batch_size'] = batch_size
    
    # modules/pwd_import_wizard.py



    def _step2_incremental_import(self):
        """Step 2: Incremental batch import with progress"""
        
        st.markdown("### Step 2: Incremental Page Import")
        st.caption("Processing PDF in batches with progress tracking")
        
        # Initialize batch tracker
        if 'pwd_batch_tracker' not in st.session_state:
            batch_tracker = BatchProgressTracker(self.db)
            batch_tracker.init_session(
                total_pages=st.session_state.pwd_total_pages,
                batch_size=st.session_state.pwd_import_settings.get('batch_size', 10)
            )
            st.session_state.pwd_batch_tracker = batch_tracker
        else:
            batch_tracker = st.session_state.pwd_batch_tracker
        
        # Define callback for batch processing
        def process_batch(batch):
            start_page = batch['start_page']
            end_page = batch['end_page']
            
            with st.spinner(f"Processing pages {start_page} to {end_page}..."):
                # FIX: Pass all required parameters to parse_page_range
                items = parse_page_range(
                    parser=self.parser,  # Pass parser
                    uploaded_file=st.session_state.pwd_import_settings['file'],
                    start_page=start_page,
                    end_page=end_page,
                    source='PWD'  # Specify source
                )
                
                # Calculate rates count
                rates_count = sum(len(item.get('rates', {})) for item in items)
                
                # Complete the batch
                batch_tracker.complete_batch(
                    batch_number=batch['batch_number'],
                    items=items,
                    rates_count=rates_count,
                    end_page=end_page
                )
                
                st.success(f"✅ Batch {batch['batch_number']} complete! Found {len(items)} items, {rates_count} rates.")
                st.rerun()
        
        # Render batch control UI
        render_batch_control_ui(batch_tracker, process_batch)
        
        # Check if complete and build hierarchy
        if batch_tracker.is_complete():
            from utils.rate_import_helpers import build_hierarchy_from_items
            with st.spinner("Building parent-child hierarchy..."):
                hierarchy = build_hierarchy_from_items(
                    parser=self.parser,
                    items=batch_tracker.get_all_items()
                )
                
                st.session_state.pwd_import_data = {
                    'hierarchy': hierarchy,
                    'settings': st.session_state.pwd_import_settings,  # ← ADD THIS
                    'timestamp': datetime.now().isoformat()
                }

        
        # Navigation
        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            if st.button("◀️ Back to Settings", use_container_width=True):
                st.session_state.pwd_wizard_step = 1
                st.rerun()
        
    def _step3_review_and_edit(self):
        """Step 3: Review and edit extracted data"""
    
        st.markdown("### Step 3: Review & Edit Extracted Data")
        
        data = st.session_state.pwd_import_data
        hierarchy = data['hierarchy']
        
        # Convert to editable format
        df = hierarchy_to_dataframe(hierarchy, source='PWD')

        
        # Add a button to fix description spacing
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔧 Fix All Descriptions", use_container_width=True):
                df['Description'] = df['Description'].apply(fix_description_spacing)
                st.success("✅ Fixed description spacing for all items")
                st.rerun()
        
        # Show summary
        total_parents = len(df[df['Type'] == 'Parent'])
        total_children = len(df[df['Type'] == 'Child'])
        
        st.info(f"📊 **Summary:** {total_parents} parents, {total_children} children")
        
        # Quick stats cards
        col1, col2, col3, col4 = st.columns(4)
        parent_codes = set(df[df['Type'] == 'Parent']['Code'])
        orphans = df[(df['Type'] == 'Child') & (~df['Parent Code'].isin(parent_codes))]
        
        col1.metric("Parents", total_parents)
        col2.metric("Children", total_children)
        col3.metric("Orphans", len(orphans), delta="⚠️" if len(orphans) > 0 else None)
        col4.metric("Has Rates", len(df[df['Dhaka Rate'] != '']))
        
        # Quick action buttons
        st.markdown("#### 🔧 Quick Fixes")
        col_fix1, col_fix2, col_fix3 = st.columns(3)
        
        with col_fix1:
            if st.button("🔧 Fix Description Spacing", use_container_width=True):
                df['Description'] = df['Description'].apply(fix_description_spacing)
                st.success("✅ Fixed spacing issues")
                st.rerun()
        
        with col_fix2:
            if len(orphans) > 0:
                if st.button(f"🔧 Auto-fix {len(orphans)} Orphans", use_container_width=True):
                    first_parent = sorted(parent_codes)[0] if parent_codes else ""
                    df.loc[df['Type'] == 'Child', 'Parent Code'] = df.loc[df['Type'] == 'Child', 'Parent Code'].fillna(first_parent)
                    st.success(f"✅ Assigned orphans to {first_parent}")
                    st.rerun()
        
        with col_fix3:
            if data.get('quick_test', False):
                st.warning("⚠️ Quick Test Mode: Only first 10 pages were parsed")
                if st.button("📑 Import Remaining Pages", use_container_width=True):
                    st.session_state.pwd_wizard_step = 2
                    st.rerun()
        
        st.markdown("---")
        
        # Main editable table
        st.markdown("#### 📝 Editable Data Table")
        st.caption("💡 Click any cell to edit. Changes are automatically saved.")
        
        # Get parent options
        parent_options = sorted(df[df['Type'] == 'Parent']['Code'].tolist())
        
        # Column configuration
        column_config = {
            "Type": st.column_config.SelectboxColumn("Type", options=["Parent", "Child"], width="small"),
            "Code": st.column_config.TextColumn("Code", width="small"),
            "Description": st.column_config.TextColumn("Description", width="large"),
            "Parent Code": st.column_config.SelectboxColumn("Parent", options=[""] + parent_options, width="small"),
            "Unit": st.column_config.SelectboxColumn("Unit", options=["", "cum", "sqm", "meter", "each", "job", "set", "kg", "hour", "month", "tender"], width="small"),
            "Dhaka Rate": st.column_config.NumberColumn("Dhaka (৳)", format="%.2f", width="small"),
            "Chattogram Rate": st.column_config.NumberColumn("Chattogram (৳)", format="%.2f", width="small"),
            "Khulna Rate": st.column_config.NumberColumn("Khulna (৳)", format="%.2f", width="small"),
            "Rajshahi Rate": st.column_config.NumberColumn("Rajshahi (৳)", format="%.2f", width="small"),
        }
        
        edited_df = st.data_editor(
            df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            key="pwd_editor_wizard"
        )
        
        # Save changes
        if st.button("💾 **Save Changes & Continue**", type="primary", use_container_width=True):
            st.session_state.pwd_import_data['edited_dataframe'] = edited_df
            st.session_state.pwd_wizard_step = 4
            st.rerun()
    
    def _step4_validate_and_save(self):
        """Step 4: Validate before saving"""
        
        st.markdown("### Step 4: Validate & Confirm")
        
        data = st.session_state.pwd_import_data
        df = data.get('edited_dataframe')
        edition_year = data.get('edition_year')
        version_name = data.get('version_name', f"PWD Schedule {edition_year}")
        dry_run = data.get('dry_run', True)
        
        if df is None:
            st.error("No data found. Please go back to Step 3.")
            if st.button("◀️ Back to Review"):
                st.session_state.pwd_wizard_step = 3
                st.rerun()
            return
        
        # Validation checks
        st.markdown("#### ✅ Validation Results")
        
        issues = self._validate_data(df)
        
        if issues:
            st.warning(f"⚠️ Found {len(issues)} issues that need attention:")
            
            for issue in issues[:10]:
                with st.expander(f"📌 {issue['type']}: {issue['code']}"):
                    st.write(issue['message'])
                    if issue.get('suggestion'):
                        st.info(f"💡 Suggestion: {issue['suggestion']}")
            
            if len(issues) > 10:
                st.caption(f"... and {len(issues) - 10} more issues")
            
            if st.button("🔧 Attempt Auto-Fix All Issues"):
                df = self._auto_fix_issues(df)
                st.session_state.pwd_import_data['edited_dataframe'] = df
                st.success("✅ Applied auto-fixes")
                st.rerun()
        else:
            st.success("✅ All validation checks passed!")
        
        # Preview what will be saved
        st.markdown("---")
        st.markdown("#### 📋 Data to be Saved")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Parents**")
            parents_df = df[df['Type'] == 'Parent']
            if not parents_df.empty:
                st.dataframe(parents_df[['Code', 'Description']].head(10), use_container_width=True, hide_index=True)
            else:
                st.info("No parent items")
        
        with col2:
            st.markdown("**Children (Sample)**")
            children_df = df[df['Type'] == 'Child']
            if not children_df.empty:
                st.dataframe(children_df[['Code', 'Parent Code', 'Unit']].head(10), use_container_width=True, hide_index=True)
            else:
                st.info("No child items")
        
        st.markdown("---")
        
        # Summary statistics
        st.markdown("#### 📊 Summary Statistics")
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Parents", len(parents_df))
        with col_b:
            st.metric("Children", len(children_df))
        with col_c:
            total_rates = sum(1 for _, row in children_df.iterrows() 
                            for zone in ['Zone-A', 'Zone-B', 'Zone-C', 'Zone-D'] 
                            if row.get(zone) and row[zone] > 0)
            st.metric("Rate Entries", total_rates)
        
        st.markdown("---")
        
        # Action buttons
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            if st.button("◀️ Back to Edit", use_container_width=True):
                st.session_state.pwd_wizard_step = 3
                st.rerun()
        
        with col_btn2:
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Export as CSV",
                csv,
                f"pwd_data_{edition_year}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col_btn3:
            if dry_run:
                st.warning("🔍 Dry Run Mode - Uncheck in Step 1 to save")
                st.button("💾 **Save to Database**", disabled=True, use_container_width=True)
            else:
                if st.button("💾 **Save to Database**", type="primary", use_container_width=True):
                    with st.spinner("Saving to database..."):
                        success = self._save_to_database(df, edition_year, version_name)
                        if success:
                            st.success("✅ Data saved successfully!")
                            st.balloons()
                            # Move to rollback options step
                            st.session_state.pwd_wizard_step = 5
                            st.rerun()
                        else:
                            st.error("❌ Failed to save data.")
            
    
    def _step5_rollback_options(self):
        """Step 5: Rollback and recovery options for PWD"""
        
        st.markdown("### Step 5: Rollback & Recovery")
        st.caption("Manage rollback points and recover previous PWD versions")
        
        from modules.unified_rollback_manager import UnifiedRollbackManager
        rollback_manager = UnifiedRollbackManager(self.db)
        
        # Get PWD versions from database
        conn = self.db.get_connection()
        versions_df = pd.read_sql_query("""
            SELECT id, version_name, edition_year, is_active, created_at
            FROM rate_versions
            WHERE source = 'PWD'
            ORDER BY created_at DESC
        """, conn)
        conn.close()
        
        # Show snapshots
        st.markdown("#### 📸 Available Rollback Snapshots")
        
        snapshots = rollback_manager.get_snapshots(source='PWD')
        
        if not snapshots.empty:
            for _, snapshot in snapshots.iterrows():
                with st.expander(f"📸 {snapshot['snapshot_name']} - {snapshot['created_at'][:16]}", expanded=False):
                    st.write(f"**Created By:** {snapshot['created_by']}")
                    st.write(f"**Description:** {snapshot['description']}")
                    
                    if st.button(f"🔄 Rollback to this snapshot", key=f"rollback_pwd_{snapshot['id']}"):
                        success, message = rollback_manager.rollback_to_snapshot(
                            snapshot['id'],
                            st.session_state.get('username', 'admin')
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        else:
            st.info("No rollback snapshots found. Create one in the import settings.")
        
        st.markdown("---")
        
        # Show existing versions
        st.markdown("#### 📜 Previously Imported PWD Versions")
        
        if not versions_df.empty:
            for _, version in versions_df.iterrows():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.write(f"**{version['version_name']}**")
                with col2:
                    st.write(f"Year: {version['edition_year']}")
                with col3:
                    if version['is_active']:
                        st.markdown("✅ **Active**")
                    else:
                        st.markdown("📦 Archived")
                with col4:
                    if not version['is_active']:
                        if st.button(f"Activate", key=f"activate_pwd_{version['id']}"):
                            from modules.unified_version_manager import UnifiedVersionManager
                            vm = UnifiedVersionManager(self.db)
                            vm.activate_version(version['id'], st.session_state.get('username', 'admin'))
                            st.success(f"Activated {version['version_name']}")
                            st.rerun()
        else:
            st.info("No previous PWD versions found")
        
        st.markdown("---")
        
        # Navigation buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("◀️ Back to Validation", use_container_width=True):
                st.session_state.pwd_wizard_step = 4
                st.rerun()
        
        with col2:
            if st.button("➡️ Continue to Complete", type="primary", use_container_width=True):
                st.session_state.pwd_wizard_step = 6
                st.rerun()

    def _step6_complete(self):
        """Step 6: Completion"""
        
        st.markdown("### ✅ Import Complete!")
        
        data = st.session_state.pwd_import_data
        edition_year = data['settings']['edition_year']
        version_name = data['settings']['version_name']
        
        st.balloons()
        
        st.success(f"""
        🎉 **Successfully imported {version_name}!**
        
        The PWD rate schedule has been saved to the database and is now available for use.
        """)
        
        st.markdown("---")
        st.markdown("#### 🎯 What would you like to do next?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Import Another Schedule", use_container_width=True):
                # Reset all session state
                st.session_state.pwd_wizard_step = 1
                st.session_state.pwd_import_data = None
                st.session_state.pwd_batch_status = {}
                st.rerun()
        
        with col2:
            if st.button("📊 Go to Version Management", use_container_width=True):
                st.session_state.pwd_wizard_step = 1
                st.session_state.pwd_import_data = None
                st.rerun()
    
   
    def _save_to_database(self, df, edition_year, version_name):
        """Save to database with unified version tracking"""
        
        try:
            # Use unified version manager
            from modules.unified_version_manager import UnifiedVersionManager
            from datetime import date
            
            # Initialize unified version manager
            version_manager = UnifiedVersionManager(self.db)
            version_manager.init_unified_tables()
            
            # Check if this edition already exists for PWD
            existing_versions = version_manager.get_all_versions(source='PWD')
            existing = existing_versions[existing_versions['edition_year'] == edition_year] if not existing_versions.empty else pd.DataFrame()
            
            if not existing.empty:
                st.warning(f"⚠️ Version for year {edition_year} already exists!")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📝 Overwrite Existing Version", use_container_width=True):
                        version_id = existing.iloc[0]['id']
                        # Clear existing data for this version using db_manager method
                        self.db.clear_pwd_version_data(version_id)
                        # Continue with save
                        return self._save_to_database(df, edition_year, version_name)
                with col2:
                    if st.button("➕ Create New Version", use_container_width=True):
                        new_version_name = st.text_input(
                            "New Version Name", 
                            value=f"{version_name} (Alternate)",
                            key="new_version_name"
                        )
                        if st.button("Save as New Version"):
                            return self._save_to_database(df, edition_year, new_version_name)
                        return False
                return False
            
            # Separate parents and children
            parents_df = df[df['Type'] == 'Parent']
            children_df = df[df['Type'] == 'Child']
            
            if parents_df.empty and children_df.empty:
                st.error("No data to save!")
                return False
            
            # Save to database using db_manager methods
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # Create version record in unified table
            cursor.execute("""
                INSERT INTO rate_versions (source, version_name, edition_year, effective_from, is_active, release_date, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ('PWD', version_name, edition_year, date.today(), True, datetime.now(), st.session_state.get('username', 'admin')))
            
            version_id = cursor.lastrowid
            
            # Clear existing data for this version - using CORRECT table names
            cursor.execute("DELETE FROM pwd_rates WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM pwd_children WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM pwd_parents WHERE version_id = ?", (version_id,))
            
            # Insert parents
            parents_saved = 0
            for _, row in parents_df.iterrows():
                chapter = row['Code'].split('.')[0]
                cursor.execute("""
                    INSERT INTO pwd_parents (pwd_code, description, chapter_number, version_id)
                    VALUES (?, ?, ?, ?)
                """, (row['Code'], row['Description'][:2000], chapter, version_id))
                parents_saved += 1
            
            # Insert children and rates
            children_saved = 0
            rates_saved = 0
            
            for _, row in children_df.iterrows():
                parent_code = row['Parent Code'] if row['Parent Code'] else ''
                
                cursor.execute("""
                    INSERT INTO pwd_children (pwd_code, parent_code, description, unit, edition_year, version_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (row['Code'], parent_code, row['Description'][:2000], row['Unit'], edition_year, version_id))
                children_saved += 1
                
                # Use CORRECT table name: pwd_rates (not pwd_rates)
                for zone in ['Dhaka', 'Chattogram', 'Khulna', 'Rajshahi']:
                    rate_col = f'{zone} Rate'
                    if rate_col in row and row[rate_col] and row[rate_col] > 0:
                        cursor.execute("""
                            INSERT INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year, version_id)
                            VALUES (?, ?, ?, ?, ?)
                        """, (row['Code'], zone, float(row[rate_col]), edition_year, version_id))
                        rates_saved += 1
            
            # Update version record with statistics
            cursor.execute("""
                UPDATE rate_versions 
                SET total_parents = ?, total_children = ?, total_rates = ?
                WHERE id = ?
            """, (parents_saved, children_saved, rates_saved, version_id))
            
            conn.commit()
            conn.close()
            
            st.success(f"✅ Saved {parents_saved} parents, {children_saved} children, and {rates_saved} rates as version: {version_name}")
            st.balloons()
            
            # Store version info in session for rollback step
            st.session_state.pwd_saved_version = {
                'version_id': version_id,
                'version_name': version_name,
                'edition_year': edition_year,
                'parents': parents_saved,
                'children': children_saved,
                'rates': rates_saved
            }
            
            return True
            
        except Exception as e:
            st.error(f"Error saving: {str(e)}")
            import traceback
            with st.expander("Debug Information"):
                st.code(traceback.format_exc())
            return False


    def _clear_version_data(self, version_id):
        """Clear all data for a specific version - using db_manager method"""
        try:
            # Use the db_manager method instead of direct SQL
            self.db.clear_pwd_version_data(version_id)
            st.info(f"Cleared data for version ID: {version_id}")
            return True
            
        except Exception as e:
            st.error(f"Error clearing version data: {str(e)}")
            return False



# Usage in admin dashboard
def render_pwd_wizard(db, parser):
    wizard = PWDImportWizard(db, parser)
    wizard.render()