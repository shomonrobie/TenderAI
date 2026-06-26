# modules/system_config.py - NEW FILE

import json
import streamlit as st
from typing import Any, Optional, Dict

class SystemConfig:
    """Unified configuration manager for system and company settings"""
    
    def __init__(self, db):
        self.db = db
    
    def get(self, key: str, company_id: Optional[int] = None, default: Any = None) -> Any:
        """Get config value with fallback hierarchy"""
        # 1. Company-specific
        if company_id:
            value = self.db.get_company_config(company_id, key)
            if value is not None:
                return value
        
        # 2. System-wide
        value = self.db.get_config(key)
        if value is not None:
            return value
        
        # 3. Default
        return default
    
    def set_system(self, key: str, value: Any, user_id: Optional[int] = None) -> bool:
        """Set system-wide config"""
        return self.db.set_config(key, value, user_id)
    
    def set_company(self, company_id: int, key: str, value: Any, 
                    user_id: Optional[int] = None) -> bool:
        """Set company-specific config"""
        return self.db.set_company_config(company_id, key, value, user_id=user_id)
    
    def delete_company(self, company_id: int, key: str) -> bool:
        """Delete company-specific config"""
        return self.db.delete_company_config(company_id, key)
    
    def get_all_company(self, company_id: int) -> Dict[str, Any]:
        """Get all company configs"""
        return self.db.get_all_company_configs(company_id)