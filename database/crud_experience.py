"""
Experience CRUD Operations
Manages project experience records
"""
from typing import Dict, List, Optional


class ExperienceCRUD:
    """Experience-specific CRUD operations"""
    
    def __init__(self, db_manager=None):
        self._db_manager = db_manager
    
    def _get_db(self):
        """Get database manager instance"""
        if self._db_manager:
            return self._db_manager
        from database.unified_db_manager import get_db_manager
        return get_db_manager()
    
    def get_company_experience(self, company_id: int) -> List[Dict]:
        """Get experience records for a specific company"""
        db = self._get_db()
        return db.query(
            "SELECT id, company_id, project_name, client_name, contract_value, "
            "contract_date, completion_date, nature_of_work, is_completed, "
            "created_at, updated_at "
            "FROM experience_record WHERE company_id = ? "
            "ORDER BY completion_date DESC",
            (company_id,)
        )
    
    def get_completed_projects(self, company_id: int) -> List[Dict]:
        """Get completed projects for a company"""
        db = self._get_db()
        return db.query(
            "SELECT id, company_id, project_name, client_name, contract_value, "
            "contract_date, completion_date, nature_of_work, is_completed, "
            "created_at, updated_at "
            "FROM experience_record WHERE company_id = ? AND is_completed = TRUE "
            "ORDER BY completion_date DESC",
            (company_id,)
        )
    
    def get_experience_by_value_range(self, company_id: int, min_value: float, max_value: float) -> List[Dict]:
        """Get experience records within a contract value range"""
        db = self._get_db()
        return db.query("""
            SELECT id, company_id, project_name, client_name, contract_value, 
            contract_date, completion_date, nature_of_work, is_completed,
            created_at, updated_at
            FROM experience_record 
            WHERE company_id = ? AND contract_value BETWEEN ? AND ?
            ORDER BY contract_value DESC
        """, (company_id, min_value, max_value))
    
    def add_experience(self, company_id: int, data: Dict) -> bool:
        """Add experience record"""
        db = self._get_db()
        
        result = db.execute("""
            INSERT INTO experience_record (
                company_id, project_name, client_name, contract_value,
                contract_date, completion_date, nature_of_work, is_completed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            data.get('project_name'),
            data.get('client_name'),
            data.get('contract_value'),
            data.get('contract_date'),
            data.get('completion_date'),
            data.get('nature_of_work'),
            data.get('is_completed', True)
        ))
        
        return result > 0
    
    def update_experience(self, experience_id: int, data: Dict) -> bool:
        """Update experience record"""
        db = self._get_db()
        
        set_clause = []
        params = []
        
        allowed_fields = [
            'project_name', 'client_name', 'contract_value',
            'contract_date', 'completion_date', 'nature_of_work', 'is_completed'
        ]
        
        for field in allowed_fields:
            if field in data:
                set_clause.append(f"{field} = ?")
                params.append(data[field])
        
        if not set_clause:
            return False
        
        params.append(experience_id)
        query = f"""
            UPDATE experience_record 
            SET {', '.join(set_clause)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        result = db.execute(query, tuple(params))
        return result > 0
    
    def delete_experience(self, experience_id: int) -> bool:
        """Delete experience record"""
        db = self._get_db()
        result = db.execute(
            "DELETE FROM experience_record WHERE id = ?",
            (experience_id,)
        )
        return result > 0
    
    def get_similar_experience(self, company_id: int, project_type: str, min_value: float = 0) -> List[Dict]:
        """Get similar experience based on project type/scope keywords"""
        db = self._get_db()
        # Using LIKE for keyword matching on nature_of_work
        search_term = f"%{project_type}%"
        return db.query("""
            SELECT id, company_id, project_name, client_name, contract_value,
            contract_date, completion_date, nature_of_work, is_completed,
            created_at, updated_at
            FROM experience_record 
            WHERE company_id = ? AND nature_of_work LIKE ? AND contract_value >= ?
            ORDER BY contract_value DESC
        """, (company_id, search_term, min_value))