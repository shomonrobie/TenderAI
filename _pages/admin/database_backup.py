"""
Database Backup Module - Supabase Export
"""

import streamlit as st
import pandas as pd
import os
import datetime
import json
from io import BytesIO
import zipfile

from database.connection import get_supabase_client, is_supabase
from .constants import DEFAULT_FALLBACK_TABLES, categorize_tables


def render_database_backup():
    """Render database backup interface for Supabase"""
    
    st.markdown("### 💾 Database Backup & Export")
    st.markdown("Export your Supabase database to JSON format for backup or migration.")
    
    from config.database import DB_TYPE
    
    if not is_supabase():
        st.warning("⚠️ This feature is only available when using Supabase as the database backend.")
        st.info("📌 You are currently using: " + (DB_TYPE.upper() if DB_TYPE else "SQLite"))
        return
    
    st.success("✅ Connected to Supabase database")
    
    try:
        supabase = get_supabase_client()
        
        response = supabase.rpc("get_table_names").execute()
        
        if hasattr(response, 'data') and response.data:
            ALL_TABLES = [row['table_name'] for row in response.data]
            st.success(f"✅ Found {len(ALL_TABLES)} tables in the database")
        else:
            st.warning("⚠️ Could not fetch table names. Using fallback list.")
            ALL_TABLES = DEFAULT_FALLBACK_TABLES
            
    except Exception as e:
        st.warning(f"⚠️ Could not fetch table names: {str(e)}")
        st.info("📌 Using fallback table list")
        ALL_TABLES = DEFAULT_FALLBACK_TABLES
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 📋 Export Options")
        
        export_format = st.selectbox(
            "Export Format",
            ["JSON", "CSV", "Both (JSON + CSV)"],
            key="backup_export_format",
            help="JSON is recommended for full data preservation"
        )
        
        table_groups = categorize_tables(ALL_TABLES)
        
        all_table_names = []
        for group, tables in table_groups.items():
            all_table_names.extend(tables)
        
        tables_to_export = st.multiselect(
            "Select Tables to Export",
            all_table_names,
            default=["users", "companies", "subscriptions"] if "users" in all_table_names else all_table_names[:3],
            key="backup_tables_select"
        )
        
        include_metadata = st.checkbox(
            "Include metadata (timestamp, table structure, counts)",
            value=True,
            key="backup_include_metadata"
        )
        
        st.caption(f"📊 {len(tables_to_export)} tables selected out of {len(ALL_TABLES)} total")
    
    with col2:
        st.markdown("#### 📊 Table Status")
        
        try:
            st.markdown('<div class="backup-status">', unsafe_allow_html=True)
            
            for table in tables_to_export[:8]:
                try:
                    response = supabase.table(table).select("*", count="exact").limit(0).execute()
                    count = response.count if hasattr(response, 'count') else 0
                    status_icon = "✅" if count > 0 else "📭"
                    st.caption(f"{status_icon} **{table}**: {count:,} records")
                except Exception as e:
                    st.caption(f"⚠️ **{table}**: Could not fetch")
            
            if len(tables_to_export) > 8:
                st.caption(f"... and {len(tables_to_export) - 8} more tables")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.caption(f"⚠️ Could not fetch stats: {str(e)}")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        export_btn = st.button(
            "🚀 Export Selected",
            key="export_selected_btn",
            type="primary",
            use_container_width=True
        )
    
    with col2:
        export_all_btn = st.button(
            "📦 Export All Tables",
            key="export_all_btn",
            use_container_width=True
        )
    
    with col3:
        if st.button("🗑️ Clear Backup History", key="clear_backup_history", use_container_width=True):
            if 'backup_history' in st.session_state:
                del st.session_state['backup_history']
            st.success("Backup history cleared!")
            st.rerun()
    
    if export_btn or export_all_btn:
        if export_all_btn:
            tables_to_export = ALL_TABLES
        
        if not tables_to_export:
            st.error("❌ Please select at least one table to export.")
            return
        
        with st.spinner(f"⏳ Exporting {len(tables_to_export)} tables from Supabase..."):
            try:
                export_data = {}
                table_stats = {}
                export_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                errors = []
                exported_count = 0
                
                for idx, table in enumerate(tables_to_export):
                    status_text.text(f"📊 Exporting: {table}... ({idx+1}/{len(tables_to_export)})")
                    progress_bar.progress((idx + 1) / len(tables_to_export))
                    
                    try:
                        response = supabase.table(table).select("*").execute()
                        data = response.data if hasattr(response, 'data') and response.data else []
                        
                        if data and len(data) > 0:
                            export_data[table] = data
                            table_stats[table] = {
                                'count': len(data),
                                'columns': list(data[0].keys()) if data else []
                            }
                            exported_count += 1
                        else:
                            export_data[table] = []
                            table_stats[table] = {'count': 0, 'columns': []}
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "PGRST" not in error_msg:
                            errors.append(f"Table '{table}': {error_msg}")
                        export_data[table] = []
                        table_stats[table] = {'count': 0, 'error': error_msg}
                
                status_text.text("✅ Export complete!")
                progress_bar.progress(1.0)
                
                if errors:
                    with st.expander("⚠️ Export Warnings"):
                        for err in errors:
                            st.warning(err)
                
                final_export = {
                    'exported_at': export_timestamp,
                    'database_type': 'supabase',
                    'tables_exported': len(tables_to_export),
                    'total_records': sum(stat.get('count', 0) for stat in table_stats.values() if isinstance(stat, dict)),
                    'table_stats': table_stats,
                    'include_metadata': include_metadata,
                    'data': export_data
                }
                
                st.session_state['latest_backup'] = final_export
                st.session_state['backup_timestamp'] = export_timestamp
                
                backup_filename = f"backup_supabase_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                backup_path = os.path.join('data', 'backups')
                os.makedirs(backup_path, exist_ok=True)
                
                json_file = os.path.join(backup_path, backup_filename)
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(final_export, f, indent=2, default=str)
                
                st.success(f"✅ Export successful! {exported_count} tables with data exported.")
                st.info(f"📁 Backup saved locally: `{json_file}`")
                
                st.markdown("#### 📊 Export Summary")
                summary_cols = st.columns(4)
                with summary_cols[0]:
                    st.metric("Tables Exported", len(tables_to_export))
                with summary_cols[1]:
                    total_records = sum(len(data) for data in export_data.values() if data)
                    st.metric("Total Records", f"{total_records:,}")
                with summary_cols[2]:
                    st.metric("Format", export_format)
                with summary_cols[3]:
                    st.metric("Timestamp", export_timestamp.split(" ")[1])
                
                with st.expander("📋 Per-Table Breakdown", expanded=True):
                    table_data = []
                    for table in tables_to_export:
                        data = export_data.get(table, [])
                        stats = table_stats.get(table, {})
                        record_count = len(data) if data else 0
                        table_data.append({
                            'Table': table,
                            'Records': record_count,
                            'Columns': len(stats.get('columns', [])) if stats.get('columns') else 0,
                            'Status': '✅' if record_count > 0 else '📭 Empty'
                        })
                    
                    if table_data:
                        st.dataframe(
                            pd.DataFrame(table_data),
                            use_container_width=True,
                            hide_index=True
                        )
                
                st.markdown("#### 📥 Download Backup")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    json_str = json.dumps(final_export, indent=2, default=str)
                    st.download_button(
                        label="📄 Download JSON",
                        data=json_str,
                        file_name=f"backup_supabase_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True,
                        type="primary",
                        key="download_json_backup"
                    )
                
                with col2:
                    if export_format in ["CSV", "Both (JSON + CSV)"]:
                        try:
                            zip_buffer = BytesIO()
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                for table, data in export_data.items():
                                    if data and len(data) > 0:
                                        df = pd.DataFrame(data)
                                        csv_data = df.to_csv(index=False)
                                        zip_file.writestr(f"{table}.csv", csv_data)
                            
                            zip_buffer.seek(0)
                            
                            st.download_button(
                                label="📊 Download CSV (ZIP)",
                                data=zip_buffer,
                                file_name=f"backup_supabase_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                                mime="application/zip",
                                use_container_width=True,
                                key="download_csv_backup"
                            )
                        except Exception as e:
                            st.warning(f"⚠️ Could not create CSV: {str(e)}")
                
                with col3:
                    if st.button("📂 View Backup History", key="view_backup_history", use_container_width=True):
                        st.session_state.show_backup_history = True
                
            except Exception as e:
                st.error(f"❌ Export failed: {str(e)}")
                import traceback
                traceback.print_exc()
    
    if st.session_state.get('show_backup_history', False):
        st.markdown("---")
        st.markdown("#### 📂 Backup History")
        
        backup_dir = os.path.join('data', 'backups')
        if os.path.exists(backup_dir):
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith('backup_supabase_')]
            if backup_files:
                backup_files.sort(reverse=True)
                
                history_data = []
                for file in backup_files[:20]:
                    file_path = os.path.join(backup_dir, file)
                    file_size = os.path.getsize(file_path)
                    file_mtime = os.path.getmtime(file_path)
                    history_data.append({
                        'File': file,
                        'Size': f"{file_size / 1024:.1f} KB",
                        'Created': datetime.datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        'Path': file_path
                    })
                
                st.dataframe(
                    pd.DataFrame(history_data),
                    use_container_width=True,
                    hide_index=True
                )
                
                selected_backup = st.selectbox(
                    "Select a backup to download",
                    [f['File'] for f in history_data],
                    key="select_old_backup"
                )
                
                if selected_backup:
                    file_path = os.path.join(backup_dir, selected_backup)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    
                    st.download_button(
                        label=f"📥 Download {selected_backup}",
                        data=file_content,
                        file_name=selected_backup,
                        mime="application/json",
                        use_container_width=True,
                        key="download_old_backup"
                    )
                
                if st.button("🗑️ Delete Selected Backup", key="delete_selected_backup", type="secondary"):
                    if selected_backup:
                        try:
                            os.remove(os.path.join(backup_dir, selected_backup))
                            st.success(f"✅ Deleted: {selected_backup}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Could not delete: {str(e)}")
            else:
                st.info("No backups found.")
        else:
            st.info("No backups directory found. Create one by exporting data.")
        
        if st.button("🔙 Close History", key="close_backup_history", use_container_width=True):
            st.session_state.show_backup_history = False
            st.rerun()