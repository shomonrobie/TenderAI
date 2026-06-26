# modules/unified_import_wizard.py

import streamlit as st
from modules.pwd_import_wizard import PWDImportWizard
from modules.lged_import_wizard import LGEDImportWizard


class UnifiedImportWizard:
    """
    Unified import wizard for both PWD and LGED rate schedules.
    Provides a single interface to access both importers.
    """
    
    def __init__(self, db_instance):
        self.db = db_instance
    
    def render_pwd_import(self):
        """Render PWD import wizard"""
        wizard = PWDImportWizard(self.db)
        wizard.render()
    
    def render_lged_import(self):
        """Render LGED import wizard"""
        wizard = LGEDImportWizard(self.db)
        wizard.render()
    
    def render_unified_interface(self):
        """
        Render a unified interface with tabs for PWD and LGED.
        This is what you'll call from your admin dashboard.
        """
        st.markdown("## 🏗️ Unified Rate Schedule Import")
        st.caption("Import PWD or LGED rate schedules from Excel files")
        
        # Create tabs for each source
        tab_pwd, tab_lged = st.tabs([
            "🏗️ PWD Schedule",
            "🛣️ LGED Schedule"
        ])
        
        with tab_pwd:
            self.render_pwd_import()
        
        with tab_lged:
            self.render_lged_import()


# Convenience function for admin dashboard
def render_unified_import_wizard(db):
    """Render the unified import wizard in admin dashboard"""
    wizard = UnifiedImportWizard(db)
    wizard.render_unified_interface()