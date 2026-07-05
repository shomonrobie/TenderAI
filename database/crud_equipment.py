"""
Equipment CRUD Operations
Manages equipment across companies and tenders
"""
from typing import Dict, List, Optional


class EquipmentCRUD:
    """Equipment-specific CRUD operations"""
    
    def __init__(self, db_manager=None):
        self._db_manager = db_manager
    
    def _get_db(self):
        """Get database manager instance"""
        if self._db_manager:
            return self._db_manager
        from database.unified_db_manager import get_db_manager
        return get_db_manager()
    
    def get_company_equipment(self, company_id: int) -> List[Dict]:
        """Get equipment for a specific company"""
        db = self._get_db()
        return db.query(
            "SELECT id, company_id, equipment_name, equipment_type, model, "
            "capacity, ownership_type, current_status, created_at, updated_at "
            "FROM equipment WHERE company_id = ? "
            "ORDER BY equipment_name",
            (company_id,)
        )
    
    def get_equipment_by_type(self, equipment_type: str, company_id: Optional[int] = None) -> List[Dict]:
        """Get equipment by type, optionally filtered by company"""
        db = self._get_db()
        if company_id:
            return db.query(
                "SELECT id, company_id, equipment_name, equipment_type, model, "
                "capacity, ownership_type, current_status, created_at, updated_at "
                "FROM equipment WHERE equipment_type = ? AND company_id = ? "
                "ORDER BY equipment_name",
                (equipment_type, company_id)
            )
        else:
            return db.query(
                "SELECT id, company_id, equipment_name, equipment_type, model, "
                "capacity, ownership_type, current_status, created_at, updated_at "
                "FROM equipment WHERE equipment_type = ? "
                "ORDER BY equipment_name",
                (equipment_type,)
            )
    
    def get_available_equipment(self, company_id: int) -> List[Dict]:
        """Get available equipment for a company"""
        db = self._get_db()
        return db.query(
            "SELECT id, company_id, equipment_name, equipment_type, model, "
            "capacity, ownership_type, current_status, created_at, updated_at "
            "FROM equipment WHERE company_id = ? AND current_status = 'Available' "
            "ORDER BY equipment_name",
            (company_id,)
        )
    
    def add_equipment(self, company_id: int, data: Dict) -> bool:
        """Add equipment record"""
        db = self._get_db()
        
        result = db.execute("""
            INSERT INTO equipment (
                company_id, equipment_name, equipment_type, model,
                capacity, ownership_type, current_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            data.get('equipment_name'),
            data.get('equipment_type'),
            data.get('model'),
            data.get('capacity'),
            data.get('ownership_type'),
            data.get('current_status')
        ))
        
        return result > 0
    
    def update_equipment(self, equipment_id: int, data: Dict) -> bool:
        """Update equipment record"""
        db = self._get_db()
        
        set_clause = []
        params = []
        
        allowed_fields = [
            'equipment_name', 'equipment_type', 'model', 'capacity',
            'ownership_type', 'current_status'
        ]
        
        for field in allowed_fields:
            if field in data:
                set_clause.append(f"{field} = ?")
                params.append(data[field])
        
        if not set_clause:
            return False
        
        params.append(equipment_id)
        query = f"""
            UPDATE equipment 
            SET {', '.join(set_clause)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        result = db.execute(query, tuple(params))
        return result > 0
    
    def delete_equipment(self, equipment_id: int) -> bool:
        """Delete equipment record"""
        db = self._get_db()
        result = db.execute(
            "DELETE FROM equipment WHERE id = ?",
            (equipment_id,)
        )
        return result > 0
    
    def get_equipment_for_tender(self, tender_id: int) -> List[Dict]:
        """Get equipment associated with a tender"""
        db = self._get_db()
        # Assuming there's a tender_equipment junction table
        return db.query("""
            SELECT e.* FROM equipment e
            JOIN tender_equipment te ON e.id = te.equipment_id
            WHERE te.tender_id = ?
            ORDER BY e.equipment_name
        """, (tender_id,))
    
    def assign_equipment_to_tender(self, equipment_id: int, tender_id: int) -> bool:
        """Assign equipment to a tender"""
        db = self._get_db()
        result = db.execute("""
            INSERT INTO tender_equipment (tender_id, equipment_id)
            VALUES (?, ?)
        """, (tender_id, equipment_id))
        return result > 0