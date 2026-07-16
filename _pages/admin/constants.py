"""
Constants and helper functions for admin dashboard
"""

ROLE_HIERARCHY = {
    'system_admin': '👑 Full platform access',
    'system_support': '🛠️ Can view all companies, support access',
    'system_auditor': '📊 Read-only across platform',
    'company_admin': '🏢 Full company management',
    'manager': '📋 Can manage tenders and create users',
    'analyst': '🔬 Can run analyses and view reports',
    'viewer': '👁️ Read-only access',
    'user': '👤 Regular user'
}

PERMISSION_CATEGORIES = {
    "👤 User Management": ['manage_users', 'manage_team', 'create_user', 'delete_user'],
    "📄 Content Management": ['manage_tenders', 'view_reports', 'export_data'],
    "🔬 Analysis": ['run_analysis', 'view_rates', 'edit_rates'],
    "⚙️ System": ['manage_zones', 'manage_versions', 'change_plans', 'delete_any']
}

ALL_PERMISSION_KEYS = [
    'manage_users', 'manage_team', 'create_user', 'delete_user',
    'manage_tenders', 'view_reports', 'export_data',
    'run_analysis', 'view_rates', 'edit_rates',
    'manage_zones', 'manage_versions', 'change_plans', 'delete_any'
]

PWD_VERSION_ROLES = ['system_admin', 'company_admin']

DEFAULT_FALLBACK_TABLES = [
    "users", "companies", "subscriptions", "user_oauth",
    "boq_templates", "boq_items", "boq_approval_history",
    "rates", "system_rates", "price_change_logs",
    "company_profile", "company_onboarding_status", "company_documents",
    "company_financials", "company_licenses", "company_personnel",
    "company_nppi", "certificate",
    "competitors", "competitor_rates", "competitor_master",
    "competitor_bids", "competitor_bid_history",
    "tenders", "tender_milestones", "tender_documents", "bid_submissions",
    "analysis_history", "otp_verification", "system_config",
    "user_activity_log", "version_history", "migrations",
    "pwd_import_history", "extension_downloads", "demo_data_generation_log"
]

# ==================== HELPER FUNCTIONS ====================

def get_role_description(role_name: str) -> str:
    """Get description for a role"""
    return ROLE_HIERARCHY.get(role_name, 'Custom role')


def categorize_tables(all_tables):
    """Categorize tables into groups for better UX"""
    table_groups = {}
    
    for table in all_tables:
        if table in ["users", "companies", "subscriptions", "user_oauth"]:
            group = "Core Tables"
        elif table in ["boq_templates", "boq_items", "boq_approval_history"]:
            group = "BOQ Tables"
        elif table in ["rates", "system_rates", "price_change_logs"]:
            group = "Rate Tables"
        elif table in ["company_profile", "company_onboarding_status", "company_documents", 
                     "company_financials", "company_licenses", "company_personnel", 
                     "company_nppi", "certificate"]:
            group = "Company Tables"
        elif table in ["competitors", "competitor_rates", "competitor_master", 
                    "competitor_bids", "competitor_bid_history"]:
            group = "Competitor Tables"
        elif table in ["tenders", "tender_milestones", "tender_documents", "bid_submissions"]:
            group = "Tender Tables"
        elif table in ["otp_verification", "system_config", "user_activity_log", 
                    "version_history", "migrations", "pwd_import_history"]:
            group = "System Tables"
        else:
            group = "Other Tables"
        
        if group not in table_groups:
            table_groups[group] = []
        table_groups[group].append(table)
    
    return table_groups