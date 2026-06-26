# modules/progress_tracker.py

import streamlit as st
import time
from datetime import datetime
from typing import Callable, List, Dict, Any, Optional

class ProgressTracker:
    """Reusable progress tracker for batch imports"""
    
    def __init__(self, title: str = "Processing"):
        self.title = title
        self.start_time = None
        self.progress_bar = None
        self.status_text = None
        self.detail_text = None
    
    def start(self, total_items: int, description: str = "Starting..."):
        """Initialize and display progress bar"""
        self.start_time = datetime.now()
        
        # Create progress containers
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        self.detail_text = st.empty()
        
        # Show initial status
        self.status_text.info(f"🔄 {description}")
        self.detail_text.caption(f"0 / {total_items} completed")
        
        return self
    
    def update(self, current: int, total: int, current_item: str = "", extra_info: str = ""):
        """Update progress bar with current status"""
        if self.progress_bar is None:
            return
        
        progress = current / total if total > 0 else 0
        self.progress_bar.progress(progress)
        
        # Calculate ETA
        eta_text = ""
        if self.start_time and current > 0:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > 0:
                rate = current / elapsed
                if rate > 0:
                    remaining = (total - current) / rate
                    eta_text = f" | ETA: {self._format_time(remaining)}"
        
        # Update detail text
        detail_parts = [f"📄 {current}/{total} pages"]
        if current_item:
            detail_parts.append(f"| 📌 {current_item}")
        if extra_info:
            detail_parts.append(f"| {extra_info}")
        detail_parts.append(f"⏱️ Elapsed: {self._format_time(elapsed)}" + eta_text)
        
        self.detail_text.caption(" ".join(detail_parts))
    
    def update_batch(self, batch_num: int, total_batches: int, 
                     batch_items: int, batch_rates: int,
                     current_page: int = None, total_pages: int = None):
        """Update for batch processing"""
        if self.progress_bar is None:
            return
        
        progress = batch_num / total_batches if total_batches > 0 else 0
        self.progress_bar.progress(progress)
        
        # Build status message
        status_parts = []
        if current_page and total_pages:
            status_parts.append(f"📄 Pages: {current_page}/{total_pages}")
        status_parts.append(f"📦 Batch {batch_num}/{total_batches}")
        status_parts.append(f"📊 Items: {batch_items} | Rates: {batch_rates}")
        
        self.detail_text.caption(" | ".join(status_parts))
        
        # Update progress percentage in status
        self.status_text.info(f"🔄 Processing... {int(progress * 100)}% complete")
    
    def update_step(self, step_name: str, step_num: int, total_steps: int):
        """Update for multi-step processes"""
        if self.progress_bar is None:
            return
        
        progress = step_num / total_steps
        self.progress_bar.progress(progress)
        self.status_text.info(f"🔄 {step_name}... ({step_num}/{total_steps})")
    
    def complete(self, success: bool = True, message: str = ""):
        """Mark progress as complete"""
        if self.progress_bar is None:
            return
        
        self.progress_bar.progress(1.0)
        
        if success:
            elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            self.status_text.success(f"✅ {message or 'Complete!'} (took {self._format_time(elapsed)})")
        else:
            self.status_text.error(f"❌ {message or 'Failed!'}")
        
        self.detail_text.empty()
    
    def _format_time(self, seconds: float) -> str:
        """Format time duration"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"


class BatchProgressTracker:
    """Specialized tracker for batch import processes"""
    
    def __init__(self, db_instance):
        self.db = db_instance
        self.current_batch = 0
        self.total_batches = 0
        self.processed_pages = 0
        self.total_pages = 0
        self.items_found = 0
        self.rates_found = 0
        self.batch_results = []
    
    def init_session(self, total_pages: int, batch_size: int = 10):
        """Initialize batch tracking in session state"""
        total_batches = (total_pages + batch_size - 1) // batch_size
        
        self.total_pages = total_pages
        self.total_batches = total_batches
        
        st.session_state[self._get_tracker_key()] = {
            'current_batch': 0,
            'total_batches': total_batches,
            'processed_pages': 0,
            'total_pages': total_pages,
            'batch_size': batch_size,
            'items_found': 0,
            'rates_found': 0,
            'batches_completed': [],
            'is_complete': False,
            'all_items': []
        }
        
        return self._get_tracker()
    
    def _get_tracker_key(self) -> str:
        """Get session state key based on source"""
        # This can be set by the wizard
        if hasattr(self, 'source'):
            return f"{self.source}_batch_tracker_data"
        return 'batch_tracker_data'
    
    def set_source(self, source: str):
        """Set source (PWD or LGED) for session key"""
        self.source = source
    
    def _get_tracker(self):
        """Get tracker from session state"""
        key = self._get_tracker_key()
        return st.session_state.get(key)
    
    def _set_tracker(self, tracker):
        """Set tracker in session state"""
        key = self._get_tracker_key()
        st.session_state[key] = tracker
    
    def get_next_batch(self) -> Optional[Dict[str, Any]]:
        """Get next batch to process"""
        tracker = self._get_tracker()
        if not tracker:
            return None
        
        if tracker['current_batch'] >= tracker['total_batches']:
            return None
        
        next_batch_num = tracker['current_batch'] + 1
        start_page = (next_batch_num - 1) * tracker['batch_size'] + 1
        end_page = min(next_batch_num * tracker['batch_size'], tracker['total_pages'])
        
        return {
            'batch_number': next_batch_num,
            'start_page': start_page,
            'end_page': end_page,
            'is_last': next_batch_num == tracker['total_batches']
        }
    
    def complete_batch(self, batch_number: int, items: list, rates_count: int, 
                       end_page: int):
        """Mark a batch as complete"""
        tracker = self._get_tracker()
        if not tracker:
            return
        
        tracker['current_batch'] = batch_number
        tracker['processed_pages'] = end_page
        tracker['items_found'] += len(items)
        tracker['rates_found'] += rates_count
        tracker['batches_completed'].append({
            'batch': batch_number,
            'items': len(items),
            'rates': rates_count,
            'pages_processed': end_page,
            'timestamp': datetime.now().isoformat()
        })
        tracker['all_items'].extend(items)
        
        # Check if complete
        if tracker['current_batch'] >= tracker['total_batches']:
            tracker['is_complete'] = True
        
        self._set_tracker(tracker)
    
    def display_progress(self):
        """Display current progress in UI"""
        tracker = self._get_tracker()
        if not tracker:
            return
        
        # Overall progress bar
        progress_pct = (tracker['processed_pages'] / tracker['total_pages']) * 100 if tracker['total_pages'] > 0 else 0
        st.progress(progress_pct / 100)
        
        # Statistics row
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Pages Processed", f"{tracker['processed_pages']} / {tracker['total_pages']}")
        col2.metric("Batches Done", f"{tracker['current_batch']} / {tracker['total_batches']}")
        col3.metric("Items Found", tracker['items_found'])
        col4.metric("Rates Found", tracker['rates_found'])
        
        return tracker
    
    def display_completed_batches(self):
        """Show table of completed batches"""
        tracker = self._get_tracker()
        if not tracker or not tracker['batches_completed']:
            return
        
        st.markdown("##### ✅ Completed Batches")
        completed_df = pd.DataFrame(tracker['batches_completed'])
        st.dataframe(completed_df, use_container_width=True, hide_index=True)
    
    def is_complete(self) -> bool:
        """Check if all batches are complete"""
        tracker = self._get_tracker()
        return tracker['is_complete'] if tracker else False
    
    def get_all_items(self) -> list:
        """Get all collected items"""
        tracker = self._get_tracker()
        return tracker['all_items'] if tracker else []


def render_batch_control_ui(batch_tracker: BatchProgressTracker, on_process_callback: Callable):
    """Render batch control UI with process button"""
    
    # Display progress
    batch_tracker.display_progress()
    
    # Show current batch status
    if not batch_tracker.is_complete():
        st.markdown("---")
        st.markdown("#### 🔄 Current Batch Processing")
        
        next_batch = batch_tracker.get_next_batch()
        if next_batch:
            st.info(f"📄 **Next Batch {next_batch['batch_number']}:** Pages {next_batch['start_page']} - {next_batch['end_page']}")
            
            if st.button(f"▶️ Process Batch {next_batch['batch_number']}", type="primary", use_container_width=True):
                on_process_callback(next_batch)
    
    # Show completed batches
    batch_tracker.display_completed_batches()
