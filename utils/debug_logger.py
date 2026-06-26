# utils/debug_logger.py

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

class DebugLogger:
    """Debug logging for PWD/LGED extraction"""
    
    def __init__(self, enabled=True, log_to_file=False):
        self.enabled = enabled
        self.log_to_file = log_to_file
        self.logs = []
        
        if log_to_file:
            self.log_file = f"debug_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    def log(self, category, message, data=None):
        """Log a debug message"""
        if not self.enabled:
            return
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'message': message,
            'data': data
        }
        
        self.logs.append(log_entry)
        
        # Print to console
        print(f"[DEBUG][{category}] {message}")
        if data:
            print(f"  Data: {str(data)[:200]}")
        
        # Optionally show in Streamlit
        if st.session_state.get('show_debug', False):
            with st.expander(f"🔍 {category}: {message[:100]}", expanded=False):
                st.write(f"**Message:** {message}")
                if data:
                    st.json(data)
    
    def log_table_sample(self, table, page_num, table_num, max_rows=5):
        """Log a sample of extracted table"""
        if not self.enabled:
            return
        
        sample = []
        for i, row in enumerate(table[:max_rows]):
            if row:
                sample.append({
                    'row': i,
                    'cells': [str(cell)[:100] if cell else '' for cell in row[:10]]
                })
        
        self.log(
            'TABLE_EXTRACTION',
            f"Page {page_num}, Table {table_num}: {len(table)} rows",
            {
                'total_rows': len(table),
                'sample': sample,
                'table_shape': f"{len(table)} x {len(table[0]) if table else 0}"
            }
        )
    
    def log_item_extraction(self, item, source):
        """Log each extracted item"""
        if not self.enabled:
            return
        
        self.log(
            'ITEM_EXTRACTED',
            f"{source} item: {item.get('code', 'N/A')}",
            {
                'code': item.get('code'),
                'level': item.get('level'),
                'description_length': len(item.get('description', '')),
                'description_preview': item.get('description', '')[:100],
                'unit': item.get('unit'),
                'rates_count': len(item.get('rates', {})),
                'rates': item.get('rates', {})
            }
        )
    
    def log_hierarchy(self, hierarchy, source):
        """Log hierarchy statistics"""
        if not self.enabled:
            return
        
        self.log(
            'HIERARCHY_BUILT',
            f"{source} hierarchy built",
            {
                'parents_count': len(hierarchy.get('parents', [])),
                'children_count': len(hierarchy.get('children', [])),
                'sample_parents': [
                    {
                        'code': p['code'],
                        'description_length': len(p.get('description', '')),
                        'description_preview': p.get('description', '')[:100]
                    }
                    for p in hierarchy.get('parents', [])[:5]
                ],
                'sample_children': [
                    {
                        'code': c['code'],
                        'parent_code': c.get('parent_code'),
                        'description_length': len(c.get('description', '')),
                        'description_preview': c.get('description', '')[:100]
                    }
                    for c in hierarchy.get('children', [])[:5]
                ]
            }
        )
    
    def save_to_file(self):
        """Save logs to file"""
        if self.log_to_file and self.logs:
            with open(self.log_file, 'w') as f:
                json.dump(self.logs, f, indent=2)
            print(f"Debug logs saved to: {self.log_file}")
    
    def display_in_streamlit(self):
        """Display logs in Streamlit UI"""
        if not self.enabled:
            return
        
        st.markdown("### 🔍 Debug Logs")
        
        # Filter controls
        col1, col2 = st.columns(2)
        with col1:
            categories = list(set(log['category'] for log in self.logs))
            selected_category = st.selectbox("Filter by Category", ["All"] + categories)
        
        with col2:
            show_details = st.checkbox("Show Details", value=False)
        
        # Filter logs
        filtered_logs = self.logs
        if selected_category != "All":
            filtered_logs = [log for log in self.logs if log['category'] == selected_category]
        
        # Display logs
        for log in filtered_logs[-50:]:  # Last 50 logs
            with st.expander(f"[{log['category']}] {log['message'][:80]}", expanded=False):
                st.write(f"**Time:** {log['timestamp']}")
                st.write(f"**Message:** {log['message']}")
                if show_details and log.get('data'):
                    st.json(log['data'])
        
        # Export option
        if st.button("Export Debug Logs"):
            json_str = json.dumps(self.logs, indent=2)
            st.download_button(
                "Download Logs",
                json_str,
                f"debug_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json"
            )


# Global debug instance
_debug_instance = None

def get_debug_logger(enabled=True, log_to_file=False):
    """Get or create debug logger instance"""
    global _debug_instance
    if _debug_instance is None:
        _debug_instance = DebugLogger(enabled, log_to_file)
    return _debug_instance


def log_table_extraction(table, page_num, table_num):
    """Convenience function to log table extraction"""
    logger = get_debug_logger()
    logger.log_table_sample(table, page_num, table_num)


def log_item_extraction(item, source):
    """Convenience function to log item extraction"""
    logger = get_debug_logger()
    logger.log_item_extraction(item, source)


def log_hierarchy(hierarchy, source):
    """Convenience function to log hierarchy"""
    logger = get_debug_logger()
    logger.log_hierarchy(hierarchy, source)