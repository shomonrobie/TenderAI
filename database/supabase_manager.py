from typing import List, Union, Dict, Callable, Optional

def get_company_by_name(self, company_name: str) -> Optional[Dict]:
    """Get company by name"""
    if not self.conn:
        return None
    try:
        result = self.conn.table('companies').select('*').eq('company_name', company_name).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"❌ Error getting company by name: {e}")
        return None