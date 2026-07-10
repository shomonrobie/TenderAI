"""
Auto-Fill CRUD Operations
Comprehensive data access for e-GP form auto-filling
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class AutoFillCRUD:
    """Comprehensive CRUD operations for auto-fill functionality"""
    
    def __init__(self, db_manager=None):
        """Initialize with database manager instance"""
        self._db_manager = db_manager
    
    def _get_db(self):
        """Get the database manager"""
        if hasattr(self, 'query') and callable(getattr(self, 'query', None)):
            return self
        elif self._db_manager:
            return self._db_manager
        else:
            from database.unified_db_manager import get_db_manager
            return get_db_manager()
    
    # =========================================================================
    # COMPANY DATA
    # =========================================================================
    
    def get_company_data(self, company_id: int) -> Dict:
        """Get basic company profile data"""
        db = self._get_db()
        
        result = db.query_one("""
            SELECT 
                c.company_name, 
                c.registration_number, 
                c.vat_number, 
                c.tin_number, 
                c.bin_number,
                c.email, 
                c.phone, 
                c.mobile_number, 
                c.address, 
                c.division, 
                c.district, 
                c.upazila, 
                c.post_code, 
                c.website, 
                c.rjsc_number, 
                c.is_individual,
                af.auto_fill_email
            FROM companies c
            LEFT JOIN company_auto_fill_settings af ON c.id = af.company_id
            WHERE c.id = ?
        """, (company_id,))
        
        if result:
            return {
                'company': {
                    'name': result.get('company_name'),
                    'registration_number': result.get('registration_number'),
                    'vat_number': result.get('vat_number'),
                    'tin_number': result.get('tin_number'),
                    'bin_number': result.get('bin_number'),
                    'email': result.get('email'),
                    'auto_fill_email': result.get('auto_fill_email'),
                    'phone': result.get('phone'),
                    'mobile_number': result.get('mobile_number'),
                    'address': result.get('address'),
                    'division': result.get('division'),
                    'district': result.get('district'),
                    'upazila': result.get('upazila'),
                    'post_code': result.get('post_code'),
                    'website': result.get('website'),
                    'rjsc_number': result.get('rjsc_number'),
                    'is_individual': result.get('is_individual')
                }
            }
        return {}
    
    def get_company_extended_data(self, company_id: int) -> Dict:
        """Get extended company profile from company_profile table"""
        db = self._get_db()
        
        result = db.query_one("""
            SELECT 
                legal_name, trade_name, registered_address, phone_primary,
                email_primary, division, district, website
            FROM company_profile
            WHERE company_id = ?
        """, (company_id,))
        
        if result:
            return {
                'company_extended': {
                    'legal_name': result.get('legal_name'),
                    'trade_name': result.get('trade_name'),
                    'registered_address': result.get('registered_address'),
                    'phone_primary': result.get('phone_primary'),
                    'email_primary': result.get('email_primary'),
                    'division': result.get('division'),
                    'district': result.get('district'),
                    'website': result.get('website')
                }
            }
        return {}
    
    # =========================================================================
    # PERSONNEL DATA
    # =========================================================================
    
    def get_personnel_data(self, company_id: int, search_term: str = None, limit: int = 50) -> Dict:
        """Get basic personnel data"""
        db = self._get_db()
        
        query = """
            SELECT 
                id, name, designation, nid_number, phone, email,
                educational_qualification, experience_years, is_key_personnel,
                date_of_birth, years_with_company, present_employer,
                present_job_title, is_prime_candidate
            FROM company_personnel
            WHERE company_id = ?
        """
        params = [company_id]
        
        if search_term:
            query += " AND (name LIKE ? OR designation LIKE ? OR nid_number LIKE ?)"
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        query += " ORDER BY is_key_personnel DESC, name LIMIT ?"
        params.append(limit)
        
        rows = db.query(query, tuple(params))
        
        personnel = []
        for row in rows:
            personnel.append({
                'id': row.get('id'),
                'name': row.get('name'),
                'designation': row.get('designation'),
                'nid_number': row.get('nid_number'),
                'phone': row.get('phone'),
                'email': row.get('email'),
                'educational_qualification': row.get('educational_qualification'),
                'experience_years': row.get('experience_years'),
                'is_key_personnel': row.get('is_key_personnel'),
                'date_of_birth': row.get('date_of_birth'),
                'years_with_company': row.get('years_with_company'),
                'present_employer': row.get('present_employer'),
                'present_job_title': row.get('present_job_title'),
                'is_prime_candidate': row.get('is_prime_candidate')
            })
        
        return {'personnel': personnel}
    
    def get_key_personnel_data(self, company_id: int) -> Dict:
        """Get key personnel data for Form e-PW2A-5"""
        db = self._get_db()
        
        rows = db.query("""
            SELECT 
                id, name, designation, nid_number, phone, email,
                educational_qualification, experience_years,
                date_of_birth, years_with_company,
                present_employer, present_job_title, is_prime_candidate
            FROM company_personnel
            WHERE company_id = ? AND is_key_personnel = TRUE
            ORDER BY is_prime_candidate DESC, name
        """, (company_id,))
        
        personnel = []
        for row in rows:
            personnel.append({
                'id': row.get('id'),
                'name': row.get('name'),
                'designation': row.get('designation'),
                'nid_number': row.get('nid_number'),
                'phone': row.get('phone'),
                'email': row.get('email'),
                'educational_qualification': row.get('educational_qualification'),
                'experience_years': row.get('experience_years'),
                'date_of_birth': row.get('date_of_birth'),
                'years_with_company': row.get('years_with_company'),
                'present_employer': row.get('present_employer'),
                'present_job_title': row.get('present_job_title'),
                'is_prime_candidate': row.get('is_prime_candidate')
            })
        
        return {'key_personnel': personnel}
    
    def get_personnel_detailed_data(self, company_id: int, search_term: str = None, limit: int = 50) -> Dict:
        """Get detailed personnel data with experience"""
        personnel_data = self.get_personnel_data(company_id, search_term, limit)
        
        if not personnel_data.get('personnel'):
            return {'personnel': []}
        
        db = self._get_db()
        
        for person in personnel_data['personnel']:
            experiences = db.query("""
                SELECT 
                    from_date, to_date, project_name, company_name,
                    position, relevant_experience_description, is_current
                FROM personnel_experience
                WHERE personnel_id = ?
                ORDER BY from_date DESC
            """, (person['id'],))
            
            person['experiences'] = []
            for exp in experiences:
                person['experiences'].append({
                    'from_date': exp.get('from_date'),
                    'to_date': exp.get('to_date'),
                    'project_name': exp.get('project_name'),
                    'company_name': exp.get('company_name'),
                    'position': exp.get('position'),
                    'relevant_experience_description': exp.get('relevant_experience_description'),
                    'is_current': exp.get('is_current')
                })
        
        return personnel_data
    
    # =========================================================================
    # EQUIPMENT DATA
    # =========================================================================
    
    def get_equipment_data(self, company_id: int, search_term: str = None, limit: int = 50) -> Dict:
        """Get equipment data"""
        db = self._get_db()
        
        query = """
            SELECT 
                id, equipment_name, equipment_type, model, capacity,
                ownership_type, current_status
            FROM company_equipment
            WHERE company_id = ?
        """
        params = [company_id]
        
        if search_term:
            query += " AND (equipment_name LIKE ? OR equipment_type LIKE ? OR model LIKE ?)"
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        query += " ORDER BY equipment_name LIMIT ?"
        params.append(limit)
        
        rows = db.query(query, tuple(params))
        
        equipment = []
        for row in rows:
            equipment.append({
                'id': row.get('id'),
                'name': row.get('equipment_name'),
                'type': row.get('equipment_type'),
                'model': row.get('model'),
                'capacity': row.get('capacity'),
                'ownership_type': row.get('ownership_type'),
                'status': row.get('current_status')
            })
        
        return {'equipment': equipment}
    
    # =========================================================================
    # EXPERIENCE DATA - CORRECTED (Using company_experience table)
    # =========================================================================
    
    def get_experience_data(self, company_id: int, search_term: str = None, limit: int = 50) -> Dict:
        """Get experience data"""
        db = self._get_db()
        
        query = """
            SELECT 
                id, project_name, procuring_entity, contract_number,
                award_date, completion_date, contract_value,
                role, procuring_entity_address, procuring_entity_contact,
                procuring_entity_email, similarity_justification, is_completed
            FROM company_experience
            WHERE company_id = ?
        """
        params = [company_id]
        
        if search_term:
            query += " AND (project_name LIKE ? OR procuring_entity LIKE ? OR contract_number LIKE ?)"
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        query += " ORDER BY award_date DESC LIMIT ?"
        params.append(limit)
        
        rows = db.query(query, tuple(params))
        
        experiences = []
        for row in rows:
            experiences.append({
                'id': row.get('id'),
                'project_name': row.get('project_name'),
                'procuring_entity': row.get('procuring_entity'),
                'contract_number': row.get('contract_number'),
                'award_date': row.get('award_date'),
                'completion_date': row.get('completion_date'),
                'contract_value': row.get('contract_value'),
                'role': row.get('role'),
                'procuring_entity_address': row.get('procuring_entity_address'),
                'procuring_entity_contact': row.get('procuring_entity_contact'),
                'procuring_entity_email': row.get('procuring_entity_email'),
                'similarity_justification': row.get('similarity_justification'),
                'is_completed': row.get('is_completed')
            })
        
        return {'experiences': experiences}
    
    def get_experience_for_comparison(self, company_id: int, min_value: float = 0) -> Dict:
        """Get experience for similarity comparison"""
        db = self._get_db()
        
        rows = db.query("""
            SELECT 
                id, project_name, procuring_entity, contract_number,
                award_date, completion_date, contract_value,
                role, procuring_entity_address, procuring_entity_contact,
                procuring_entity_email, similarity_justification
            FROM company_experience
            WHERE company_id = ? AND is_completed = TRUE AND contract_value >= ?
            ORDER BY contract_value DESC
        """, (company_id, min_value))
        
        experiences = []
        for row in rows:
            experiences.append({
                'id': row.get('id'),
                'project_name': row.get('project_name'),
                'procuring_entity': row.get('procuring_entity'),
                'contract_number': row.get('contract_number'),
                'award_date': row.get('award_date'),
                'completion_date': row.get('completion_date'),
                'contract_value': row.get('contract_value'),
                'role': row.get('role'),
                'procuring_entity_address': row.get('procuring_entity_address'),
                'procuring_entity_contact': row.get('procuring_entity_contact'),
                'procuring_entity_email': row.get('procuring_entity_email'),
                'similarity_justification': row.get('similarity_justification')
            })
        
        return {'experiences': experiences}
    
    def add_experience(self, company_id: int, data: Dict) -> bool:
        """Add a new experience record"""
        db = self._get_db()
        
        result = db.execute("""
            INSERT INTO company_experience (
                company_id, project_name, procuring_entity, contract_number,
                contract_value, award_date, completion_date, role,
                procuring_entity_address, procuring_entity_contact, procuring_entity_email,
                similarity_justification, is_completed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            data.get('project_name'),
            data.get('procuring_entity'),
            data.get('contract_number'),
            data.get('contract_value'),
            data.get('award_date'),
            data.get('completion_date'),
            data.get('role'),
            data.get('procuring_entity_address'),
            data.get('procuring_entity_contact'),
            data.get('procuring_entity_email'),
            data.get('similarity_justification'),
            data.get('is_completed', True)
        ))
        
        return result > 0
    
    def update_experience(self, experience_id: int, data: Dict) -> bool:
        """Update an experience record"""
        db = self._get_db()
        
        set_clause = []
        params = []
        
        allowed_fields = [
            'project_name', 'procuring_entity', 'contract_number',
            'contract_value', 'award_date', 'completion_date', 'role',
            'procuring_entity_address', 'procuring_entity_contact',
            'procuring_entity_email', 'similarity_justification', 'is_completed'
        ]
        
        for field in allowed_fields:
            if field in data:
                set_clause.append(f"{field} = ?")
                params.append(data[field])
        
        if not set_clause:
            return False
        
        params.append(experience_id)
        query = f"""
            UPDATE company_experience 
            SET {', '.join(set_clause)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        result = db.execute(query, tuple(params))
        return result > 0
    
    def delete_experience(self, experience_id: int) -> bool:
        """Delete an experience record"""
        db = self._get_db()
        result = db.execute(
            "DELETE FROM company_experience WHERE id = ?",
            (experience_id,)
        )
        return result > 0
    
    # =========================================================================
    # FINANCIAL DATA
    # =========================================================================
    
    def get_financial_data(self, company_id: int) -> Dict:
        """Get basic financial data"""
        db = self._get_db()
        
        rows = db.query("""
            SELECT 
                fiscal_year, annual_turnover, construction_turnover,
                net_worth, working_capital, liquid_assets, credit_limit,
                bank_guarantee_limit, is_audited, audit_firm
            FROM company_financials
            WHERE company_id = ?
            ORDER BY fiscal_year DESC
            LIMIT 5
        """, (company_id,))
        
        financial = []
        for row in rows:
            financial.append({
                'year': row.get('fiscal_year'),
                'annual_turnover': row.get('annual_turnover'),
                'construction_turnover': row.get('construction_turnover'),
                'net_worth': row.get('net_worth'),
                'working_capital': row.get('working_capital'),
                'liquid_assets': row.get('liquid_assets'),
                'credit_limit': row.get('credit_limit'),
                'bank_guarantee_limit': row.get('bank_guarantee_limit'),
                'is_audited': row.get('is_audited'),
                'audit_firm': row.get('audit_firm')
            })
        
        return {'financial': financial}
    
    def get_financial_detailed_data(self, company_id: int) -> Dict:
        """Get detailed financial data with turnover details"""
        db = self._get_db()
        
        rows = db.query("""
            SELECT 
                fiscal_year, annual_turnover, construction_turnover,
                net_worth, working_capital, liquid_assets, credit_limit,
                bank_guarantee_limit, is_audited, audit_firm,
                tender_id, reference_no, received_date, payment_received,
                role_in_contract, contract_name
            FROM company_financials
            WHERE company_id = ?
            ORDER BY fiscal_year DESC
            LIMIT 5
        """, (company_id,))
        
        financial = []
        for row in rows:
            financial.append({
                'year': row.get('fiscal_year'),
                'annual_turnover': row.get('annual_turnover'),
                'construction_turnover': row.get('construction_turnover'),
                'net_worth': row.get('net_worth'),
                'working_capital': row.get('working_capital'),
                'liquid_assets': row.get('liquid_assets'),
                'credit_limit': row.get('credit_limit'),
                'bank_guarantee_limit': row.get('bank_guarantee_limit'),
                'is_audited': row.get('is_audited'),
                'audit_firm': row.get('audit_firm'),
                'tender_id': row.get('tender_id'),
                'reference_no': row.get('reference_no'),
                'received_date': row.get('received_date'),
                'payment_received': row.get('payment_received'),
                'role_in_contract': row.get('role_in_contract'),
                'contract_name': row.get('contract_name')
            })
        
        return {'financial': financial}
    
    def get_liquid_assets(self, company_id: int) -> Dict:
        """Get liquid assets with bank details for Form 2.6"""
        db = self._get_db()
        
        rows = db.query("""
            SELECT 
                id, bank_name, branch_name, account_number,
                available_amount, contact_person, contact_designation,
                contact_mobile, contact_email, is_primary
            FROM company_bank_details
            WHERE company_id = ?
            ORDER BY is_primary DESC, available_amount DESC
        """, (company_id,))
        
        banks = []
        for i, row in enumerate(rows, 1):
            banks.append({
                'sl_no': i,
                'id': row.get('id'),
                'bank_name': row.get('bank_name'),
                'branch_name': row.get('branch_name'),
                'account_number': row.get('account_number'),
                'available_amount': row.get('available_amount'),
                'contact_person': row.get('contact_person'),
                'contact_designation': row.get('contact_designation'),
                'contact_mobile': row.get('contact_mobile'),
                'contact_email': row.get('contact_email'),
                'is_primary': row.get('is_primary')
            })
        
        return {'liquid_assets': banks}
    
    # =========================================================================
    # LICENSE DATA
    # =========================================================================
    
    def get_license_data(self, company_id: int) -> Dict:
        """Get license/registration data"""
        db = self._get_db()
        
        rows = db.query("""
            SELECT 
                id, license_type, license_number, issuing_authority,
                issue_date, expiry_date, status, license_file_path
            FROM company_licenses
            WHERE company_id = ? AND status = 'active'
            ORDER BY expiry_date ASC
        """, (company_id,))
        
        licenses = []
        today = date.today()
        
        for row in rows:
            expiry_status = 'valid'
            expiry_date = row.get('expiry_date')
            if expiry_date:
                if isinstance(expiry_date, str):
                    try:
                        expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                if isinstance(expiry_date, date):
                    days_left = (expiry_date - today).days
                    if days_left < 0:
                        expiry_status = 'expired'
                    elif days_left < 90:
                        expiry_status = 'expiring_soon'
            
            licenses.append({
                'id': row.get('id'),
                'type': row.get('license_type'),
                'number': row.get('license_number'),
                'issuing_authority': row.get('issuing_authority'),
                'issue_date': row.get('issue_date'),
                'expiry_date': expiry_date,
                'status': row.get('status'),
                'file_path': row.get('license_file_path'),
                'expiry_status': expiry_status
            })
        
        return {'licenses': licenses}
    
    # =========================================================================
    # ONGOING WORKS DATA (Form e-PW2A-6A)
    # =========================================================================
    
    def get_ongoing_works_data(self, company_id: int) -> Dict:
        """Get ongoing works data for e-PW2A-6A"""
        db = self._get_db()
        
        rows = db.query("""
            SELECT 
                id, tender_id, reference_no, contract_amount,
                noa_date, intended_completion_date, procuring_entity,
                organization, payment_received, status,
                contract_agreement_file_path, contract_agreement_file_name
            FROM ongoing_works
            WHERE company_id = ? AND status = 'ongoing'
            ORDER BY noa_date DESC
        """, (company_id,))
        
        works = []
        for i, row in enumerate(rows, 1):
            works.append({
                'sl_no': i,
                'id': row.get('id'),
                'tender_id': row.get('tender_id'),
                'reference_no': row.get('reference_no'),
                'contract_amount': row.get('contract_amount'),
                'noa_date': row.get('noa_date'),
                'intended_completion_date': row.get('intended_completion_date'),
                'procuring_entity': row.get('procuring_entity'),
                'organization': row.get('organization'),
                'payment_received': row.get('payment_received'),
                'status': row.get('status'),
                'contract_agreement_file_path': row.get('contract_agreement_file_path'),
                'contract_agreement_file_name': row.get('contract_agreement_file_name')
            })
        
        return {'ongoing_works': works}
    
    # =========================================================================
    # REFERENCES DATA (Form 2.7)
    # =========================================================================
    
    def get_references_data(self, company_id: int) -> Dict:
        """Get references data for Form 2.7"""
        db = self._get_db()
        
        rows = db.query("""
            SELECT 
                id, referee_name, organization, designation,
                mobile, email, reference_type, address, is_primary
            FROM company_references
            WHERE company_id = ?
            ORDER BY reference_type, is_primary DESC
        """, (company_id,))
        
        references = []
        for row in rows:
            references.append({
                'id': row.get('id'),
                'referee_name': row.get('referee_name'),
                'organization': row.get('organization'),
                'designation': row.get('designation'),
                'mobile': row.get('mobile'),
                'email': row.get('email'),
                'reference_type': row.get('reference_type'),
                'address': row.get('address'),
                'is_primary': row.get('is_primary')
            })
        
        return {'references': references}
    
    # =========================================================================
    # AUTO-FILL SETTINGS
    # =========================================================================
    
    def get_auto_fill_settings(self, company_id: int) -> Dict:
        """Get auto-fill settings for a company"""
        db = self._get_db()
        
        result = db.query_one("""
            SELECT 
                id,
                company_id,
                auto_fill_email,
                default_bid_amount,
                default_contract_role,
                created_at,
                updated_at
            FROM company_auto_fill_settings
            WHERE company_id = ?
        """, (company_id,))
        
        if result:
            return {
                'auto_fill_settings': {
                    'id': result.get('id'),
                    'company_id': result.get('company_id'),
                    'auto_fill_email': result.get('auto_fill_email'),
                    'default_bid_amount': result.get('default_bid_amount'),
                    'default_contract_role': result.get('default_contract_role'),
                    'created_at': result.get('created_at'),
                    'updated_at': result.get('updated_at')
                }
            }
        return {'auto_fill_settings': None}
    
    def update_auto_fill_settings(self, company_id: int, data: Dict) -> bool:
        """Update auto-fill settings for a company"""
        db = self._get_db()
        
        result = db.execute("""
            INSERT INTO company_auto_fill_settings (
                company_id,
                auto_fill_email,
                default_bid_amount,
                default_contract_role,
                updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (company_id) DO UPDATE 
            SET 
                auto_fill_email = EXCLUDED.auto_fill_email,
                default_bid_amount = EXCLUDED.default_bid_amount,
                default_contract_role = EXCLUDED.default_contract_role,
                updated_at = CURRENT_TIMESTAMP
        """, (
            company_id,
            data.get('auto_fill_email'),
            data.get('default_bid_amount'),
            data.get('default_contract_role', 'Sole'),
            datetime.now()
        ))
        
        return result > 0
    
    # =========================================================================
    # ALL DATA
    # =========================================================================
    
    def get_all_company_data(self, company_id: int) -> Dict:
        """Get ALL company data at once"""
        data = {}
        data.update(self.get_company_data(company_id))
        data.update(self.get_company_extended_data(company_id))
        data.update(self.get_personnel_data(company_id))
        data.update(self.get_equipment_data(company_id))
        data.update(self.get_experience_data(company_id))
        data.update(self.get_financial_data(company_id))
        data.update(self.get_license_data(company_id))
        data.update(self.get_ongoing_works_data(company_id))
        data.update(self.get_liquid_assets(company_id))
        data.update(self.get_references_data(company_id))
        data.update(self.get_key_personnel_data(company_id))
        return data
    
    # =========================================================================
    # FIELD MATCHING
    # =========================================================================
    
    def match_field_to_data(self, label: str, field_type: str = 'text') -> Dict:
        """Match a form field label to data source"""
        label_lower = label.lower()
        
        # Company matches
        company_matches = {
            'company name': {'source': 'company', 'field': 'company_name', 'confidence': 0.9},
            'company address': {'source': 'company', 'field': 'address', 'confidence': 0.8},
            'company phone': {'source': 'company', 'field': 'phone', 'confidence': 0.8},
            'company email': {'source': 'company', 'field': 'email', 'confidence': 0.8},
            'registration number': {'source': 'company', 'field': 'registration_number', 'confidence': 0.9},
            'tin number': {'source': 'company', 'field': 'tin_number', 'confidence': 0.9},
            'vat number': {'source': 'company', 'field': 'vat_number', 'confidence': 0.9},
            'bin number': {'source': 'company', 'field': 'bin_number', 'confidence': 0.9},
            'mobile number': {'source': 'company', 'field': 'mobile_number', 'confidence': 0.8},
        }
        
        # Personnel matches
        personnel_matches = {
            'name': {'source': 'personnel', 'field': 'name', 'confidence': 0.7},
            'full name': {'source': 'personnel', 'field': 'name', 'confidence': 0.8},
            'designation': {'source': 'personnel', 'field': 'designation', 'confidence': 0.8},
            'nid': {'source': 'personnel', 'field': 'nid_number', 'confidence': 0.7},
            'nid number': {'source': 'personnel', 'field': 'nid_number', 'confidence': 0.9},
            'phone': {'source': 'personnel', 'field': 'phone', 'confidence': 0.7},
            'experience': {'source': 'personnel', 'field': 'experience_years', 'confidence': 0.6},
            'education': {'source': 'personnel', 'field': 'educational_qualification', 'confidence': 0.6},
            'date of birth': {'source': 'personnel', 'field': 'date_of_birth', 'confidence': 0.8},
        }
        
        # Check company matches
        for key, match in company_matches.items():
            if key in label_lower:
                return match
        
        # Check personnel matches
        for key, match in personnel_matches.items():
            if key in label_lower:
                return match
        
        # Default match by type
        if 'email' in label_lower:
            return {'source': 'company', 'field': 'email', 'confidence': 0.6}
        elif 'phone' in label_lower:
            return {'source': 'company', 'field': 'phone', 'confidence': 0.6}
        elif 'address' in label_lower:
            return {'source': 'company', 'field': 'address', 'confidence': 0.6}
        
        return None
    
    def get_field_value(self, company_id: int, source: str, field: str) -> Any:
        """Get actual value from database for a matched field"""
        try:
            db = self._get_db()
            
            if source == 'company':
                result = db.query_one(
                    f"SELECT {field} FROM companies WHERE id = ?",
                    (company_id,)
                )
                if result:
                    return result.get(field)
            
            elif source == 'personnel':
                result = db.query_one(
                    f"""
                    SELECT {field} FROM company_personnel 
                    WHERE company_id = ? AND is_key_personnel = TRUE
                    ORDER BY name
                    LIMIT 1
                    """,
                    (company_id,)
                )
                if result:
                    return result.get(field)
                
                result = db.query_one(
                    f"""
                    SELECT {field} FROM company_personnel 
                    WHERE company_id = ?
                    LIMIT 1
                    """,
                    (company_id,)
                )
                if result:
                    return result.get(field)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting field value: {e}")
            return None
    
    # =========================================================================
    # SEARCH
    # =========================================================================
    
    def search_company_data(self, company_id: int, query: str, categories: List[str] = None) -> List[Dict]:
        """Search across company data"""
        results = []
        search_term = f"%{query}%"
        db = self._get_db()
        
        # Search personnel
        if not categories or 'personnel' in categories:
            rows = db.query("""
                SELECT 'personnel' as source, id, name, designation, is_key_personnel
                FROM company_personnel
                WHERE company_id = ? 
                AND (name LIKE ? OR designation LIKE ? OR nid_number LIKE ?)
                LIMIT 10
            """, (company_id, search_term, search_term, search_term))
            
            for row in rows:
                results.append({
                    'source': row.get('source'),
                    'id': row.get('id'),
                    'name': row.get('name'),
                    'designation': row.get('designation'),
                    'is_key_personnel': row.get('is_key_personnel')
                })
        
        # Search equipment
        if not categories or 'equipment' in categories:
            rows = db.query("""
                SELECT 'equipment' as source, id, equipment_name, equipment_type
                FROM company_equipment
                WHERE company_id = ?
                AND (equipment_name LIKE ? OR model LIKE ? OR equipment_type LIKE ?)
                LIMIT 10
            """, (company_id, search_term, search_term, search_term))
            
            for row in rows:
                results.append({
                    'source': row.get('source'),
                    'id': row.get('id'),
                    'name': row.get('equipment_name'),
                    'type': row.get('equipment_type')
                })
        
        # Search experiences - USING CORRECT TABLE
        if not categories or 'experience' in categories:
            rows = db.query("""
                SELECT 'experience' as source, id, project_name, procuring_entity
                FROM company_experience
                WHERE company_id = ?
                AND (project_name LIKE ? OR procuring_entity LIKE ? OR contract_number LIKE ?)
                ORDER BY award_date DESC
                LIMIT 10
            """, (company_id, search_term, search_term, search_term))
            
            for row in rows:
                results.append({
                    'source': row.get('source'),
                    'id': row.get('id'),
                    'name': row.get('project_name'),
                    'client': row.get('procuring_entity')
                })
        
        # Search licenses
        if not categories or 'licenses' in categories:
            rows = db.query("""
                SELECT 'license' as source, id, license_type, license_number
                FROM company_licenses
                WHERE company_id = ? AND status = 'active'
                AND (license_type LIKE ? OR license_number LIKE ?)
                LIMIT 10
            """, (company_id, search_term, search_term))
            
            for row in rows:
                results.append({
                    'source': row.get('source'),
                    'id': row.get('id'),
                    'name': row.get('license_type'),
                    'number': row.get('license_number')
                })
        
        return results
    
    # =========================================================================
    # TRACKING
    # =========================================================================
    
    def track_form_fill(self, company_id: int, user_id: int, data: Dict) -> bool:
        """Track form fill event"""
        try:
            db = self._get_db()
            
            result = db.execute("""
                INSERT INTO extension_auto_fill_log 
                (company_id, user_id, field_label, field_value, confidence_score, 
                 page_url, form_type, filled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                user_id,
                data.get('field_label', ''),
                data.get('field_value', ''),
                data.get('confidence', 0),
                data.get('url', ''),
                data.get('form_type', ''),
                datetime.now()
            ))
            
            return result > 0
            
        except Exception as e:
            logger.error(f"Error tracking form fill: {e}")
            return False
    
    def track_tender_submission(self, company_id: int, data: Dict) -> bool:
        """Track tender submission"""
        try:
            db = self._get_db()
            
            result = db.execute("""
                INSERT INTO company_tender_submissions 
                (company_id, tender_id, tender_title, procuring_entity, 
                 submission_date, bid_amount, status, auto_fill_used, auto_fill_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                data.get('tender_id'),
                data.get('tender_title'),
                data.get('procuring_entity'),
                data.get('submission_date', date.today()),
                data.get('bid_amount'),
                data.get('status', 'submitted'),
                data.get('auto_fill_used', False),
                data.get('auto_fill_count', 0)
            ))
            
            return result > 0
            
        except Exception as e:
            logger.error(f"Error tracking tender submission: {e}")
            return False
    
    def get_usage_stats(self, company_id: int, user_id: int = None) -> Dict:
        """Get usage statistics"""
        try:
            db = self._get_db()
            
            this_month = datetime.now().replace(day=1).strftime('%Y-%m-%d')
            
            params = [company_id, this_month]
            if user_id:
                query = """
                    SELECT COUNT(*) FROM extension_auto_fill_log 
                    WHERE company_id = ? AND filled_at >= ? AND user_id = ?
                """
                params.append(user_id)
            else:
                query = """
                    SELECT COUNT(*) FROM extension_auto_fill_log 
                    WHERE company_id = ? AND filled_at >= ?
                """
            
            result = db.query_one(query, tuple(params))
            used = result.get('count') if result else 0
            
            return {'used': used}
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {'used': 0}
    
    # =========================================================================
    # DOCUMENT UPLOAD
    # =========================================================================
    
    def update_contract_agreement(self, company_id: int, work_id: int, file_path: str, file_name: str) -> bool:
        """Update contract agreement file for ongoing work"""
        try:
            db = self._get_db()
            
            result = db.execute("""
                UPDATE ongoing_works 
                SET contract_agreement_file_path = ?, 
                    contract_agreement_file_name = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND company_id = ?
            """, (file_path, file_name, work_id, company_id))
            
            return result > 0
            
        except Exception as e:
            logger.error(f"Error updating contract agreement: {e}")
            return False
    
    def update_experience_contract(self, company_id: int, contract_number: str, file_path: str) -> bool:
        """Update contract agreement for experience record"""
        try:
            db = self._get_db()
            
            result = db.execute("""
                UPDATE company_experience 
                SET contract_agreement_file_path = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE contract_number = ? AND company_id = ?
            """, (file_path, contract_number, company_id))
            
            return result > 0
            
        except Exception as e:
            logger.error(f"Error updating experience contract: {e}")
            return False
        
    # =========================================================================
    # EQUIPMENT DATA - CORRECTED (Using company_equipment table)
    # =========================================================================

    def get_company_equipment(self, company_id: int) -> List[Dict]:
        """Get equipment for a specific company"""
        db = self._get_db()
        return db.query(
            "SELECT id, company_id, equipment_name, equipment_type, model, "
            "capacity, ownership_type, current_status, created_at, updated_at "
            "FROM company_equipment WHERE company_id = ? "
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
                "FROM company_equipment WHERE equipment_type = ? AND company_id = ? "
                "ORDER BY equipment_name",
                (equipment_type, company_id)
            )
        else:
            return db.query(
                "SELECT id, company_id, equipment_name, equipment_type, model, "
                "capacity, ownership_type, current_status, created_at, updated_at "
                "FROM company_equipment WHERE equipment_type = ? "
                "ORDER BY equipment_name",
                (equipment_type,)
            )

    def get_available_equipment(self, company_id: int) -> List[Dict]:
        """Get available equipment for a company"""
        db = self._get_db()
        return db.query(
            "SELECT id, company_id, equipment_name, equipment_type, model, "
            "capacity, ownership_type, current_status, created_at, updated_at "
            "FROM company_equipment WHERE company_id = ? AND current_status = 'Available' "
            "ORDER BY equipment_name",
            (company_id,)
        )

    def add_equipment(self, company_id: int, data: Dict) -> bool:
        """Add equipment record"""
        db = self._get_db()
        
        result = db.execute("""
            INSERT INTO company_equipment (
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
            UPDATE company_equipment 
            SET {', '.join(set_clause)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        result = db.execute(query, tuple(params))
        return result > 0

    def delete_equipment(self, equipment_id: int) -> bool:
        """Delete equipment record"""
        db = self._get_db()
        result = db.execute(
            "DELETE FROM company_equipment WHERE id = ?",
            (equipment_id,)
        )
        return result > 0

    def get_equipment_for_tender(self, tender_id: int) -> List[Dict]:
        """Get equipment associated with a tender"""
        db = self._get_db()
        # Assuming there's a tender_equipment junction table
        # If the junction table doesn't exist, you may need to create it
        return db.query("""
            SELECT e.* FROM company_equipment e
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
    
    # =========================================================================
    # EXPERIENCE DATA - COMPLETE (Using company_experience table)
    # =========================================================================

    def get_company_experience(self, company_id: int) -> List[Dict]:
        """Get experience records for a company"""
        db = self._get_db()
        results = db.query(
            "SELECT id, company_id, project_name, procuring_entity, contract_number, "
            "contract_value, award_date, completion_date, role, "
            "procuring_entity_address, procuring_entity_contact, procuring_entity_email, "
            "similarity_justification, is_completed, created_at, updated_at "
            "FROM company_experience WHERE company_id = ? "
            "ORDER BY award_date DESC",
            (company_id,)
        )
        return results if results else []

    def get_completed_projects(self, company_id: int) -> List[Dict]:
        """Get completed projects for a company"""
        db = self._get_db()
        results = db.query(
            "SELECT id, company_id, project_name, procuring_entity, contract_number, "
            "contract_value, award_date, completion_date, role, "
            "procuring_entity_address, procuring_entity_contact, procuring_entity_email, "
            "similarity_justification, is_completed, created_at, updated_at "
            "FROM company_experience WHERE company_id = ? AND is_completed = TRUE "
            "ORDER BY award_date DESC",
            (company_id,)
        )
        return results if results else []

    def get_experience_by_value_range(self, company_id: int, min_value: float, max_value: float) -> List[Dict]:
        """Get experience records within a contract value range"""
        db = self._get_db()
        results = db.query("""
            SELECT id, company_id, project_name, procuring_entity, contract_number,
            contract_value, award_date, completion_date, role,
            procuring_entity_address, procuring_entity_contact, procuring_entity_email,
            similarity_justification, is_completed, created_at, updated_at
            FROM company_experience 
            WHERE company_id = ? AND contract_value BETWEEN ? AND ?
            ORDER BY contract_value DESC
        """, (company_id, min_value, max_value))
        return results if results else []

    def add_experience(self, company_id: int, data: Dict) -> bool:
        """Add a new experience record"""
        db = self._get_db()
        
        result = db.execute("""
            INSERT INTO company_experience (
                company_id, project_name, procuring_entity, contract_number,
                contract_value, award_date, completion_date, role,
                procuring_entity_address, procuring_entity_contact, procuring_entity_email,
                similarity_justification, is_completed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            data.get('project_name'),
            data.get('procuring_entity'),
            data.get('contract_number'),
            data.get('contract_value'),
            data.get('award_date'),
            data.get('completion_date'),
            data.get('role'),
            data.get('procuring_entity_address'),
            data.get('procuring_entity_contact'),
            data.get('procuring_entity_email'),
            data.get('similarity_justification'),
            data.get('is_completed', True)
        ))
        
        return result > 0

    def update_experience(self, experience_id: int, data: Dict) -> bool:
        """Update an experience record"""
        db = self._get_db()
        
        set_clause = []
        params = []
        
        allowed_fields = [
            'project_name', 'procuring_entity', 'contract_number',
            'contract_value', 'award_date', 'completion_date', 'role',
            'procuring_entity_address', 'procuring_entity_contact',
            'procuring_entity_email', 'similarity_justification', 'is_completed'
        ]
        
        for field in allowed_fields:
            if field in data:
                set_clause.append(f"{field} = ?")
                params.append(data[field])
        
        if not set_clause:
            return False
        
        params.append(experience_id)
        query = f"""
            UPDATE company_experience 
            SET {', '.join(set_clause)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        result = db.execute(query, tuple(params))
        return result > 0

    def delete_experience(self, experience_id: int) -> bool:
        """Delete an experience record"""
        db = self._get_db()
        result = db.execute(
            "DELETE FROM company_experience WHERE id = ?",
            (experience_id,)
        )
        return result > 0

    def get_similar_experience(self, company_id: int, project_type: str, min_value: float = 0) -> List[Dict]:
        """Get similar experience based on project type/scope keywords"""
        db = self._get_db()
        search_term = f"%{project_type}%"
        results = db.query("""
            SELECT id, company_id, project_name, procuring_entity, contract_number,
            contract_value, award_date, completion_date, role,
            procuring_entity_address, procuring_entity_contact, procuring_entity_email,
            similarity_justification, is_completed, created_at, updated_at
            FROM company_experience 
            WHERE company_id = ? AND similarity_justification LIKE ? AND contract_value >= ?
            ORDER BY contract_value DESC
        """, (company_id, search_term, min_value))
        return results if results else []
    

    # =========================================================================
    # FIELD MAPPING - CORRECTED (Using ? for Supabase compatibility)
    # =========================================================================

    def get_field_mappings(self, company_id: int, form_type: str = None) -> List[Dict]:
        """Get field mappings for a company"""
        try:
            db = self._get_db()
            
            # Use ? for all parameters (Supabase compatible)
            query = """
                SELECT * FROM custom_field_mappings 
                WHERE company_id = ? AND is_active = TRUE
            """
            params = [company_id]
            
            if form_type:
                query += " AND form_type = ?"
                params.append(form_type)
            
            query += " ORDER BY form_type, field_label"
            
            results = db.query(query, tuple(params))
            return results if results else []
        except Exception as e:
            logger.error(f"Error getting field mappings: {e}")
            return []

    def create_field_mapping(self, company_id: int, data: Dict) -> bool:
        """Create a new field mapping"""
        try:
            db = self._get_db()
            
            # Use ? for all parameters
            result = db.execute("""
                INSERT INTO custom_field_mappings (
                    company_id, form_type, field_id, field_label, field_type,
                    source_table, source_column, source_query, default_value,
                    mapping_rule, confidence_score, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                data.get('form_type'),
                data.get('field_id'),
                data.get('field_label'),
                data.get('field_type', 'text'),
                data.get('source_table'),
                data.get('source_column'),
                data.get('source_query'),
                data.get('default_value'),
                data.get('mapping_rule'),
                data.get('confidence_score', 1.0),
                data.get('created_by')
            ))
            
            return result > 0
        except Exception as e:
            logger.error(f"Error creating field mapping: {e}")
            return False

    def update_field_mapping(self, mapping_id: int, data: Dict) -> bool:
        """Update a field mapping"""
        try:
            db = self._get_db()
            
            set_clause = []
            params = []
            
            allowed_fields = [
                'field_id', 'field_label', 'field_type', 'source_table',
                'source_column', 'source_query', 'default_value',
                'mapping_rule', 'confidence_score', 'is_active'
            ]
            
            for field in allowed_fields:
                if field in data:
                    set_clause.append(f"{field} = ?")
                    params.append(data[field])
            
            if not set_clause:
                return False
            
            params.append(mapping_id)
            query = f"""
                UPDATE custom_field_mappings 
                SET {', '.join(set_clause)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            
            result = db.execute(query, tuple(params))
            return result > 0
        except Exception as e:
            logger.error(f"Error updating field mapping: {e}")
            return False

    def delete_field_mapping(self, mapping_id: int) -> bool:
        """Soft delete a field mapping"""
        try:
            db = self._get_db()
            result = db.execute(
                "UPDATE custom_field_mappings SET is_active = FALSE WHERE id = ?",
                (mapping_id,)
            )
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting field mapping: {e}")
            return False

    def get_auto_fill_value(self, company_id: int, mapping: Dict) -> Any:
        """Get auto-fill value for a mapping"""
        try:
            db = self._get_db()
            
            # If custom query is provided
            if mapping.get('source_query'):
                result = db.query_one(mapping['source_query'])
                if result:
                    return result.get('value') or result.get(mapping.get('source_column'))
                return mapping.get('default_value')
            
            # If source table and column are provided
            if mapping.get('source_table') and mapping.get('source_column'):
                table = mapping['source_table']
                column = mapping['source_column']
                
                # Use ? for all parameters
                if table == 'companies':
                    query = f"SELECT {column} FROM companies WHERE id = ?"
                    result = db.query_one(query, (company_id,))
                    if result:
                        value = result.get(column)
                        if value and mapping.get('mapping_rule'):
                            value = self._apply_mapping_rule(value, mapping['mapping_rule'])
                        return value or mapping.get('default_value')
                
                elif table == 'company_financials':
                    query = f"""
                        SELECT {column} FROM company_financials 
                        WHERE company_id = ? 
                        ORDER BY fiscal_year DESC, created_at DESC 
                        LIMIT 1
                    """
                    result = db.query_one(query, (company_id,))
                    if result:
                        value = result.get(column)
                        if value and mapping.get('mapping_rule'):
                            value = self._apply_mapping_rule(value, mapping['mapping_rule'])
                        return value or mapping.get('default_value')
                
                elif table == 'company_personnel':
                    # Get key personnel first
                    query = f"""
                        SELECT {column} FROM company_personnel 
                        WHERE company_id = ? AND is_key_personnel = TRUE
                        ORDER BY created_at LIMIT 1
                    """
                    result = db.query_one(query, (company_id,))
                    if not result:
                        # Fallback to any personnel
                        query = f"""
                            SELECT {column} FROM company_personnel 
                            WHERE company_id = ?
                            ORDER BY created_at LIMIT 1
                        """
                        result = db.query_one(query, (company_id,))
                    
                    if result:
                        value = result.get(column)
                        if value and mapping.get('mapping_rule'):
                            value = self._apply_mapping_rule(value, mapping['mapping_rule'])
                        return value or mapping.get('default_value')
                
                elif table == 'company_experience':
                    query = f"""
                        SELECT {column} FROM company_experience 
                        WHERE company_id = ? AND is_completed = TRUE
                        ORDER BY award_date DESC LIMIT 1
                    """
                    result = db.query_one(query, (company_id,))
                    if result:
                        value = result.get(column)
                        if value and mapping.get('mapping_rule'):
                            value = self._apply_mapping_rule(value, mapping['mapping_rule'])
                        return value or mapping.get('default_value')
                
                elif table == 'company_equipment':
                    if column == 'count':
                        query = "SELECT COUNT(*) as count FROM company_equipment WHERE company_id = ?"
                        result = db.query_one(query, (company_id,))
                        if result:
                            return result.get('count')
                    else:
                        query = f"SELECT {column} FROM company_equipment WHERE company_id = ? LIMIT 1"
                        result = db.query_one(query, (company_id,))
                        if result:
                            value = result.get(column)
                            if value and mapping.get('mapping_rule'):
                                value = self._apply_mapping_rule(value, mapping['mapping_rule'])
                            return value or mapping.get('default_value')
                
                elif table == 'company_licenses':
                    query = f"""
                        SELECT {column} FROM company_licenses 
                        WHERE company_id = ? AND status = 'active'
                        ORDER BY created_at DESC LIMIT 1
                    """
                    result = db.query_one(query, (company_id,))
                    if result:
                        value = result.get(column)
                        if value and mapping.get('mapping_rule'):
                            value = self._apply_mapping_rule(value, mapping['mapping_rule'])
                        return value or mapping.get('default_value')
            
            return mapping.get('default_value')
        except Exception as e:
            logger.error(f"Error getting auto-fill value: {e}")
            return mapping.get('default_value')
        
    def _apply_mapping_rule(self, value: Any, rule: str) -> Any:
        """Apply transformation rules to values"""
        if not value:
            return value
        
        try:
            if rule == 'format_currency':
                try:
                    val = float(value)
                    return f"৳{val:,.2f}"
                except:
                    return value
            
            elif rule == 'format_date':
                if isinstance(value, (datetime, date)):
                    return value.strftime('%d/%m/%Y')
                elif isinstance(value, str):
                    try:
                        dt = datetime.strptime(value, '%Y-%m-%d')
                        return dt.strftime('%d/%m/%Y')
                    except:
                        return value
                return value
            
            elif rule == 'format_date_english':
                if isinstance(value, (datetime, date)):
                    return value.strftime('%d-%m-%Y')
                elif isinstance(value, str):
                    try:
                        dt = datetime.strptime(value, '%Y-%m-%d')
                        return dt.strftime('%d-%m-%Y')
                    except:
                        return value
                return value
            
            elif rule == 'uppercase':
                return str(value).upper()
            
            elif rule == 'lowercase':
                return str(value).lower()
            
            elif rule == 'title_case':
                return str(value).title()
            
            elif rule == 'clean_phone':
                return ''.join(filter(str.isdigit, str(value)))
            
            elif rule == 'format_nid':
                val = str(value).replace('-', '')
                if len(val) >= 10:
                    return f"{val[:4]}-{val[4:8]}-{val[8:]}"
                return value
            
            elif rule == 'join_with_comma':
                if isinstance(value, list):
                    return ', '.join(str(v) for v in value)
                return value
            
            else:
                return value
        except Exception as e:
            logger.error(f"Error applying mapping rule {rule}: {e}")
