# config/navigation.py
from typing import Dict, List, Optional

class NavItem:
    def __init__(self, label: str, page_key: str, icon: Optional[str] = None):
        self.label = label
        self.page_key = page_key
        self.icon = icon or ""

class NavGroup:
    def __init__(self, label: str, page_key: str, icon: str, items: List[NavItem]):
        self.label = label
        self.page_key = page_key
        self.icon = icon
        self.items = items

NAVIGATION_CONFIG: Dict[str, List[NavGroup]] = {
    "system_admin": [
        # Dashboard Group
        NavGroup("Dashboard", "dashboard", "🏠", [
            NavItem("Analytics", "admin_analytics", "📊"),
            NavItem("Subscriptions", "subscription", "💳"),
            NavItem("Onboarding", "company_onboarding", "🚀"),
            NavItem("Rate Mgmt", "company_rate_management", "⚙️"),
            NavItem("Tutorial", "tutorial", "📖"),
            NavItem("Import Wizard", "import_wizard", "📥"),
            NavItem("Competitor Master", "competitor_master", "🤖"),
            NavItem("Reports", "analysis_history", "📈"),
        ]),
        
        # Rates Group - No sub-items
        NavGroup("Rates", "rate_management", "📝", []),
        
        # Tenders Group - No sub-items
        NavGroup("Tenders", "tender_management", "📋", []),
        
        # Bid Simulator Group (was BOQ)
        NavGroup("Bid Simulator", "boq_generator", "📊", [
            NavItem("Basic", "quick_bid", "📈"),
            NavItem("Advanced Optimizer", "advanced_bid", "🎯"),
            NavItem("Simulator", "competitive_intel", "🔮"),
            NavItem("AI Advisor", "ai_advisor", "🎯"),
        ]),
        
        # AutoFill Group
        NavGroup("AutoFill", "company_knowledge", "🏢", [
            NavItem("AutoFill Data", "company_knowledge", "🏢"),
            NavItem("Download Ext", "extension_download", "📥"),
            NavItem("Extension", "extension_admin", "🤖"),
        ]),
        
        # Admin Group - No sub-items
        NavGroup("Admin", "admin_dashboard", "⚙️", []),
    ],
    
    "admin": [
        NavGroup("Dashboard", "dashboard", "🏠", [
            NavItem("Subscriptions", "subscription", "💳"),
            NavItem("Onboarding", "company_onboarding", "🚀"),
            NavItem("Rate Mgmt", "company_rate_management", "⚙️"),
            NavItem("Tutorial", "tutorial", "📖"),
            NavItem("Import Wizard", "import_wizard", "📥"),
            NavItem("Competitor Master", "competitor_master", "🤖"),
            NavItem("Reports", "analysis_history", "📈"),
        ]),
        NavGroup("Rates", "rate_management", "📝", []),
        NavGroup("Tenders", "tender_management", "📋", []),
        NavGroup("Bid Simulator", "boq_generator", "📊", [
            NavItem("Basic", "quick_bid", "📈"),
            NavItem("Advanced Optimizer", "advanced_bid", "🎯"),
            NavItem("Simulator", "competitive_intel", "🔮"),
            NavItem("AI Advisor", "ai_advisor", "🎯"),
        ]),
        NavGroup("AutoFill", "company_knowledge", "🏢", [
            NavItem("AutoFill Data", "company_knowledge", "🏢"),
            NavItem("Download Ext", "extension_download", "📥"),
            NavItem("Extension", "extension_usage", "🤖"),
        ]),
        NavGroup("Admin", "admin_dashboard", "⚙️", []),
    ],
    
    "company_admin": [
        NavGroup("Dashboard", "dashboard", "🏠", [
            NavItem("Analytics", "company_analytics", "📊"),
            NavItem("Team", "user_management", "👥"),
            NavItem("Plan", "subscription", "💳"),
            NavItem("Onboarding", "company_onboarding", "🚀"),
            NavItem("Rate Mgmt", "company_rate_management", "⚙️"),
            NavItem("Tutorial", "tutorial", "📖"),
            NavItem("Competitor Master", "competitor_master", "🤖"),
            NavItem("Reports", "analysis_history", "📈"),
        ]),
        NavGroup("Rates", "rate_viewer", "📊", []),
        NavGroup("Tenders", "tender_management", "📋", []),
        NavGroup("Bid Simulator", "boq_generator", "📊", [
            NavItem("Basic", "quick_bid", "📈"),
            NavItem("Advanced Optimizer", "advanced_bid", "🎯"),
            NavItem("Simulator", "competitive_intel", "🔮"),
            NavItem("AI Advisor", "ai_advisor", "🎯"),
        ]),
        NavGroup("AutoFill", "company_knowledge", "🏢", [
            NavItem("AutoFill Data", "company_knowledge", "🏢"),
            NavItem("Download Ext", "extension_download", "📥"),
            NavItem("Extension", "extension_usage", "🤖"),
        ]),
    ],
    
    "manager": [
        NavGroup("Dashboard", "dashboard", "🏠", [
            NavItem("Reports", "analysis_history", "📈"),
            NavItem("Plan", "subscription", "💳"),
            NavItem("Rate Mgmt", "company_rate_management", "⚙️"),
            NavItem("Tutorial", "tutorial", "📖"),
        ]),
        NavGroup("Rates", "rate_viewer", "📊", []),
        NavGroup("Tenders", "tender_management", "📋", []),
        NavGroup("Bid Simulator", "boq_generator", "📊", [
            NavItem("Basic", "quick_bid", "📈"),
            NavItem("Advanced Optimizer", "advanced_bid", "🎯"),
            NavItem("Simulator", "competitive_intel", "🔮"),
            NavItem("AI Advisor", "ai_advisor", "🎯"),
        ]),
        NavGroup("AutoFill", "company_knowledge", "🏢", [
            NavItem("AutoFill Data", "company_knowledge", "🏢"),
            NavItem("Download Ext", "extension_download", "📥"),
            NavItem("Extension", "extension_usage", "🤖"),
        ]),
    ],
    
    "analyst": [
        NavGroup("Dashboard", "dashboard", "🏠", [
            NavItem("Reports", "analysis_history", "📈"),
            NavItem("Plan", "subscription", "💳"),
            NavItem("Tutorial", "tutorial", "📖"),
        ]),
        NavGroup("Rates", "rate_viewer", "📊", []),
        NavGroup("Tenders", "tender_management", "📋", []),
        NavGroup("Bid Simulator", "boq_generator", "📊", [
            NavItem("Basic", "quick_bid", "📈"),
        ]),
        NavGroup("AutoFill", "company_knowledge", "🏢", [
            NavItem("AutoFill Data", "company_knowledge", "🏢"),
            NavItem("Download Ext", "extension_download", "📥"),
            NavItem("Extension", "extension_usage", "🤖"),
        ]),
    ],
    
    "viewer": [
        NavGroup("Dashboard", "dashboard", "🏠", [
            NavItem("Reports", "analysis_history", "📈"),
            NavItem("Tutorial", "tutorial", "📖"),
        ]),
        NavGroup("Rates", "rate_viewer", "📊", []),
        NavGroup("Tenders", "tender_management", "📋", []),
        NavGroup("Bid Simulator", "boq_generator", "📊", [
            NavItem("Basic", "quick_bid", "📈"),
        ]),
        NavGroup("AutoFill", "company_knowledge", "🏢", [
            NavItem("AutoFill Data", "company_knowledge", "🏢"),
            NavItem("Download Ext", "extension_download", "📥"),
        ]),
    ],
}