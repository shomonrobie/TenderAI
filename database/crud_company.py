"""
Company CRUD Operations
Core company profile management
"""
from typing import Dict, List, Optional
import logging
from datetime import datetime
logger = logging.getLogger(__name__)


class CompanyCRUD:
    """Company-specific CRUD operations"""
    
    def __init__(self, db_manager=None):
        self._db_manager = db_manager
    
    def _get_db(self):
        """Get database manager instance"""
        if self._db_manager:
            return self._db_manager
        from database.unified_db_manager import get_db_manager
        return get_db_manager()
    
    # ============ Basic Company Info ============
    
    def get_company_by_id(self, company_id: int) -> Optional[Dict]:
        """Get company information by ID"""
        db = self._get_db()
        return db.query_one(
            "SELECT id, company_name, email, phone, mobile_number, address, "
            "district, division, registration_number, vat_number, website, "
            "is_active, created_at, updated_at FROM companies WHERE id = ?",
            (company_id,)
        )
    
    def update_company(self, company_id: int, data: Dict) -> bool:
        """Update company information"""
        db = self._get_db()
        
        set_clause = []
        params = []
        
        allowed_fields = [
            'company_name', 'email', 'phone', 'mobile_number', 'address',
            'district', 'division', 'registration_number', 'vat_number', 'website'
        ]
        
        for field in allowed_fields:
            if field in data:
                set_clause.append(f"{field} = ?")
                params.append(data[field])
        
        if not set_clause:
            return False
        
        params.append(company_id)
        query = f"""
            UPDATE companies 
            SET {', '.join(set_clause)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        result = db.execute(query, tuple(params))
        print(f"Company Update result: {result}")
        return result > 0
    
    def get_all_companies_filtered(self, search: str = None, status: int = None, 
                                limit: int = 50, offset: int = 0) -> tuple:
        """
        Get all companies with filters
        Returns (companies_list, total_count)
        """
        db = self._get_db()
        
        # ✅ If using Supabase, use direct client
        if hasattr(db, '_use_supabase') and db._use_supabase and hasattr(db, 'supabase') and db.supabase:
            try:
                # Build query
                query = db.supabase.table('companies').select('*', count='exact')
                
                # Apply filters
                if search:
                    query = query.or_(f"company_name.ilike.*{search}*,email.ilike.*{search}*,phone.ilike.*{search}*")
                
                if status is not None:
                    query = query.eq('is_active', status)
                
                # Get total count first
                count_response = query.execute()
                total = count_response.count if hasattr(count_response, 'count') else 0
                
                # Apply pagination
                query = query.range(offset, offset + limit - 1)
                query = query.order('created_at', desc=True)
                
                response = query.execute()
                companies = response.data if response.data else []
                
                return companies, total
                
            except Exception as e:
                print(f"Supabase query error: {e}")
                # Fall through to SQLite fallback
        
        # ✅ Fallback: SQLite or generic query
        # Build WHERE clause
        where_clauses = ["1=1"]
        params = []
        
        if search:
            where_clauses.append("(company_name LIKE ? OR email LIKE ? OR phone LIKE ?)")
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        if status is not None:
            where_clauses.append("is_active = ?")
            params.append(status)
        
        where_clause = " AND ".join(where_clauses)
        
        # Get total count
        try:
            count_sql = f"SELECT COUNT(*) as total FROM companies WHERE {where_clause}"
            count_result = db.query_one(count_sql, tuple(params) if params else None)
            total = count_result.get('total', 0) if count_result else 0
        except Exception as e:
            print(f"Count query error: {e}")
            total = 0
        
        # Get companies with pagination using string formatting for LIMIT/OFFSET
        query = f"""
            SELECT id, company_name, email, phone, division, district, address,
                registration_number, vat_number, created_at, is_active,
                status, is_individual, mobile_number
            FROM companies
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT {limit} OFFSET {offset}
        """
        
        try:
            companies = db.query(query, tuple(params) if params else None)
            return companies if companies else [], total
        except Exception as e:
            print(f"Error getting companies: {e}")
            return [], total
    # def get_all_companies_filtered(self, search: str = "", status: int = None, limit: int = 20, offset: int = 0):
    #     """Get all companies with pagination and filtering"""
    #     with self.get_connection() as conn:
    #         cursor = self.db_conn.get_cursor(conn)
            
    #         # Build WHERE clause
    #         where_clauses = []
    #         params = []
            
    #         if search:
    #             where_clauses.append("(company_name LIKE ? OR email LIKE ? OR phone LIKE ?)")
    #             params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
            
    #         if status is not None:
    #             where_clauses.append("is_active = ?")
    #             params.append(1 if status else 0)
            
    #         where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
    #         # Get total count
    #         cursor.execute(f"SELECT COUNT(*) FROM companies WHERE {where_sql}", params)
    #         row = cursor.fetchone()
    #         if row:
    #             if hasattr(row, 'keys'):  # It's a dict
    #                 total = list(row.values())[0] if row else 0
    #             else:  # It's a tuple
    #                 total = row[0] if row else 0
    #         else:
    #             total = 0

    #         # Get paginated companies
    #         query = f"""
    #             SELECT id, company_name, email, phone, division, district, address,
    #                 registration_number, vat_number, created_at, is_active,
    #                 status, is_individual, mobile_number
    #             FROM companies
    #             WHERE {where_sql}
    #             ORDER BY created_at DESC
    #             LIMIT ? OFFSET ?
    #         """
    #         params.extend([limit, offset])
    #         cursor.execute(query, params)
    #         rows = cursor.fetchall()
            
    #         companies = []
    #         for row in rows:
    #             companies.append({
    #                 'id': row['id'],
    #                 'company_name': row['company_name'],
    #                 'email': row['email'],
    #                 'phone': row['phone'],
    #                 'division': row['division'],
    #                 'district': row['district'],
    #                 'address': row['address'],
    #                 'registration_number': row['registration_number'],
    #                 'vat_number': row['vat_number'],
    #                 'created_at': row['created_at'],
    #                 'is_active': row['is_active'],
    #                 'status': row.get('status', 'active'),
    #                 'is_individual': row.get('is_individual', 0),
    #                 'mobile_number': row.get('mobile_number', '')
    #             })
            
    #         return companies, total
    # # ============ Company Licenses ============
    
    def get_company_licenses(self, company_id: int, status: str = 'active') -> List[Dict]:
        """Get company licenses with date conversion"""
        db = self._get_db()
        results = db.query(
            "SELECT id, company_id, license_type, license_number, issuing_authority, "
            "issue_date, expiry_date, status, created_at, updated_at "
            "FROM company_licenses WHERE company_id = ? AND status = ? "
            "ORDER BY created_at DESC",
            (company_id, status)
        )
        
        # Convert date strings to date objects
        for result in results:
            if result.get('issue_date') and isinstance(result['issue_date'], str):
                try:
                    result['issue_date'] = datetime.strptime(result['issue_date'], '%Y-%m-%d').date()
                except ValueError:
                    pass
            if result.get('expiry_date') and isinstance(result['expiry_date'], str):
                try:
                    result['expiry_date'] = datetime.strptime(result['expiry_date'], '%Y-%m-%d').date()
                except ValueError:
                    pass
        
        return results
    
    
    def add_company_license(self, company_id: int, data: Dict) -> bool:
        """Add a new license/registration"""
        db = self._get_db()
        
        result = db.execute("""
            INSERT INTO company_licenses (
                company_id, license_type, license_number, issuing_authority,
                issue_date, expiry_date, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            data.get('license_type'),
            data.get('license_number'),
            data.get('issuing_authority'),
            data.get('issue_date'),
            data.get('expiry_date'),
            'active'
        ))
        
        return result > 0
    
    def delete_license(self, license_id: int) -> bool:
        """Delete a license"""
        db = self._get_db()
        result = db.execute(
            "DELETE FROM company_licenses WHERE id = ?",
            (license_id,)
        )
        return result > 0
    
    # ============ Company Financials ============
    
    def get_company_financials(self, company_id: int) -> List[Dict]:
        """Get company financial records"""
        db = self._get_db()
        return db.query(
            "SELECT id, company_id, fiscal_year, annual_turnover, construction_turnover, "
            "net_worth, working_capital, liquid_assets, credit_limit, "
            "bank_guarantee_limit, is_audited, audit_firm, created_at, updated_at "
            "FROM company_financials WHERE company_id = ? "
            "ORDER BY fiscal_year DESC",
            (company_id,)
        )
    
    def add_company_financial(self, company_id: int, data: Dict) -> bool:
        """Add a financial record"""
        db = self._get_db()
        
        result = db.execute("""
            INSERT INTO company_financials (
                company_id, fiscal_year, annual_turnover, construction_turnover,
                net_worth, working_capital, liquid_assets, credit_limit,
                bank_guarantee_limit, is_audited, audit_firm
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            data.get('fiscal_year'),
            data.get('annual_turnover'),
            data.get('construction_turnover'),
            data.get('net_worth'),
            data.get('working_capital'),
            data.get('liquid_assets'),
            data.get('credit_limit'),
            data.get('bank_guarantee_limit'),
            data.get('is_audited', False),
            data.get('audit_firm')
        ))
        
        return result > 0
    
    def delete_company_financial(self, financial_id: int) -> bool:
        """Delete a financial record"""
        db = self._get_db()
        result = db.execute(
            "DELETE FROM company_financials WHERE id = ?",
            (financial_id,)
        )
        return result > 0
    
    # ============ Company Personnel ============
    
    def get_company_personnel(self, company_id: int) -> List[Dict]:
        """Get company personnel"""
        db = self._get_db()
        return db.query(
            "SELECT id, company_id, name, designation, nid_number, phone, email, "
            "educational_qualification, experience_years, is_key_personnel, "
            "created_at, updated_at "
            "FROM company_personnel WHERE company_id = ? "
            "ORDER BY is_key_personnel DESC, name",
            (company_id,)
        )
    
    def add_company_personnel(self, company_id: int, data: Dict) -> bool:
        """Add a personnel record"""
        db = self._get_db()
        
        result = db.execute("""
            INSERT INTO company_personnel (
                company_id, name, designation, nid_number, phone, email,
                educational_qualification, experience_years, is_key_personnel
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            data.get('name'),
            data.get('designation'),
            data.get('nid_number'),
            data.get('phone'),
            data.get('email'),
            data.get('educational_qualification'),
            data.get('experience_years', 0),
            data.get('is_key_personnel', False)
        ))
        
        return result > 0
    
    def update_company_personnel(self, personnel_id: int, data: Dict) -> bool:
        """Update a personnel record"""
        db = self._get_db()
        
        set_clause = []
        params = []
        
        allowed_fields = [
            'name', 'designation', 'nid_number', 'phone', 'email',
            'educational_qualification', 'experience_years', 'is_key_personnel'
        ]
        
        for field in allowed_fields:
            if field in data:
                set_clause.append(f"{field} = ?")
                params.append(data[field])
        
        if not set_clause:
            return False
        
        params.append(personnel_id)
        query = f"""
            UPDATE company_personnel 
            SET {', '.join(set_clause)}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """
        
        result = db.execute(query, tuple(params))
        return result > 0
    
    def delete_company_personnel(self, personnel_id: int) -> bool:
        """Delete a personnel record"""
        db = self._get_db()
        result = db.execute(
            "DELETE FROM company_personnel WHERE id = ?",
            (personnel_id,)
        )
        return result > 0
    
    # ============ Company Documents ============
    
    def get_company_documents(self, company_id: int) -> List[Dict]:
        """Get company documents"""
        db = self._get_db()
        return db.query(
            "SELECT id, company_id, document_name, document_type, file_path, file_name, "
            "description, document_date, expiry_date, uploaded_by, uploaded_at "
            "FROM company_documents WHERE company_id = ? "
            "ORDER BY uploaded_at DESC",
            (company_id,)
        )
    
    def add_company_document(self, company_id: int, data: Dict) -> bool:
        """Add document record"""
        db = self._get_db()
        
        result = db.execute("""
            INSERT INTO company_documents (
                company_id, document_name, document_type, file_path, file_name,
                description, document_date, expiry_date, uploaded_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_id,
            data.get('document_name'),
            data.get('document_type'),
            data.get('file_path'),
            data.get('file_name'),
            data.get('description'),
            data.get('document_date'),
            data.get('expiry_date'),
            data.get('uploaded_by')
        ))
        
        return result > 0
    
    def delete_company_document(self, document_id: int) -> bool:
        """Delete document record"""
        db = self._get_db()
        result = db.execute(
            "DELETE FROM company_documents WHERE id = ?",
            (document_id,)
        )
        return result > 0
    def get_company_stats_by_id(self, company_id: int) -> Dict:
        """Get statistics for a specific company"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            try:
                # Get total users
                cursor.execute('SELECT COUNT(*) as total FROM users WHERE company_id = ?', (company_id,))
                row = cursor.fetchone()
                total_users = row['total'] if row else 0
                print(f"📊 total_users: {total_users}")
                
                # Get total analyses
                cursor.execute('SELECT COUNT(*) as total FROM tender_analyses WHERE company_id = ?', (company_id,))
                row = cursor.fetchone()
                total_analyses = row['total'] if row else 0
                print(f"📊 total_analyses: {total_analyses}")
                
                # Get won tenders
                cursor.execute('''
                    SELECT COUNT(*) as total FROM tender_analyses 
                    WHERE company_id = ? AND bid_status = 'Won'
                ''', (company_id,))
                row = cursor.fetchone()
                won_tenders = row['total'] if row else 0
                print(f"📊 won_tenders: {won_tenders}")
                
                win_rate = (won_tenders / total_analyses * 100) if total_analyses > 0 else 0
                print(f"📊 win_rate: {win_rate:.1f}%")
                
                return {
                    'total_users': total_users,
                    'total_analyses': total_analyses,
                    'won_tenders': won_tenders,
                    'win_rate': win_rate
                }
                
            except Exception as e:
                print(f"❌ Error in get_company_stats_by_id: {e}")
                import traceback
                traceback.print_exc()
                return {
                    'total_users': 0,
                    'total_analyses': 0,
                    'won_tenders': 0,
                    'win_rate': 0
                }

    def get_company_profile(self, company_id: int) -> Optional[Dict]:
        """Get company profile information"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute("""
                SELECT id, company_name, registration_number, vat_number, address,
                    district, division, phone, email, website, created_at, is_active
                FROM companies 
                WHERE id = ?
            """, (company_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_company_profile(self, company_id: int, profile_data: Dict) -> bool:
        """Update company profile information"""
        allowed_fields = ['company_name', 'registration_number', 'vat_number', 'address',
                        'district', 'division', 'phone', 'email', 'website']
        updates = []
        values = []
        for key, value in profile_data.items():
            if key in allowed_fields and value is not None:
                updates.append(f"{key} = ?")
                values.append(value)
        if not updates:
            return False
        values.append(company_id)
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            cursor.execute(f"UPDATE companies SET {', '.join(updates)} WHERE id = ?", values)
            return True

    # =========================================================
    # COMPANY PROFILE MANAGEMENT
    # =========================================================

    def save_company_profile(self, company_id: int, profile_data: Dict) -> bool:
        """Save or update company profile"""
        with self.get_connection() as conn:
            cursor = self.db_conn.get_cursor(conn)
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO company_profile (
                        company_id, legal_name, trade_name, registration_number,
                        date_of_incorporation, business_nature, business_category,
                        registered_address, corporate_address, phone_primary,
                        phone_secondary, email_primary, email_secondary, website,
                        fax, division, district, upazila, post_code, status,
                        updated_by, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    company_id,
                    profile_data.get('legal_name'),
                    profile_data.get('trade_name'),
                    profile_data.get('registration_number'),
                    profile_data.get('date_of_incorporation'),
                    profile_data.get('business_nature'),
                    profile_data.get('business_category'),
                    profile_data.get('registered_address'),
                    profile_data.get('corporate_address'),
                    profile_data.get('phone_primary'),
                    profile_data.get('phone_secondary'),
                    profile_data.get('email_primary'),
                    profile_data.get('email_secondary'),
                    profile_data.get('website'),
                    profile_data.get('fax'),
                    profile_data.get('division'),
                    profile_data.get('district'),
                    profile_data.get('upazila'),
                    profile_data.get('post_code'),
                    profile_data.get('status', 'active'),
                    profile_data.get('updated_by')
                ))
                return True
            except Exception as e:
                logger.error(f"Error saving company profile: {e}")
                return False
    def check_company_name_exists(self, company_name: str, exclude_id: int = None) -> bool:
        """Check if company name already exists"""
        db = self._get_db()
        query = "SELECT id FROM companies WHERE company_name = ?"
        params = [company_name]
        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)
        return db.query_one(query, tuple(params)) is not None

    def check_company_mobile_exists(self, mobile: str, exclude_id: int = None) -> bool:
        """Check if company mobile number already exists"""
        db = self._get_db()
        query = "SELECT id FROM companies WHERE mobile_number = ?"
        params = [mobile]
        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)
        return db.query_one(query, tuple(params)) is not None

    def check_company_email_exists(self, email: str, exclude_id: int = None) -> bool:
        """Check if company email already exists"""
        if not email:
            return False
        db = self._get_db()
        query = "SELECT id FROM companies WHERE email = ?"
        params = [email]
        if exclude_id:
            query += " AND id != ?"
            params.append(exclude_id)
        return db.query_one(query, tuple(params)) is not None
    # ============ Company Access Management ============
    
    def get_company_users(self, company_id: int) -> List[Dict]:
        """Get all users associated with a company"""
        db = self._get_db()
        
        return db.query("""
            SELECT 
                id,
                username,
                full_name,
                email,
                phone,
                role,
                is_active,
                is_approved,
                is_company_admin,
                created_at,
                last_login_at,
                approved_by,
                approved_at,
                company_admin_approved_by,
                company_admin_approved_at
            FROM users
            WHERE company_id = ? 
                AND is_active = true
            ORDER BY is_company_admin DESC, full_name
        """, (company_id,))
    # Updated CompanyCRUD methods for Supabase/PostgreSQL

    def get_company_users(self, company_id: int) -> List[Dict]:
        """Get all users associated with a company"""
        db = self._get_db()
        
        return db.query("""
            SELECT 
                id,
                username,
                full_name,
                email,
                phone,
                role,
                is_active,
                is_approved,
                is_company_admin,
                created_at,
                last_login_at,
                approved_by,
                approved_at,
                company_admin_approved_by,
                company_admin_approved_at
            FROM users
            WHERE company_id = ? 
                AND is_active = true
            ORDER BY is_company_admin DESC, full_name
        """, (company_id,))

    def get_pending_access_requests(self, company_id: int) -> List[Dict]:
        """Get pending access requests for a company"""
        db = self._get_db()
        
        return db.query("""
            SELECT 
                id as user_id,
                username,
                full_name,
                email,
                phone,
                role as current_role,
                created_at as user_created_at,
                is_approved,
                is_company_admin,
                company_admin_approved_by,
                company_admin_approved_at
            FROM users
            WHERE company_id = ? 
                AND is_approved = false
                AND is_active = true
                AND role != 'individual'
            ORDER BY created_at DESC
        """, (company_id,))

    def get_company_access_stats(self, company_id: int) -> Dict:
        """Get access statistics for a company"""
        db = self._get_db()
        
        stats = {
            'total_users': 0,
            'approved_users': 0,
            'pending_requests': 0,
            'company_admins': 0,
            'company_users': 0
        }
        
        # Total users in company - use integer comparison with boolean
        result = db.query_one(
            "SELECT COUNT(*) as count FROM users WHERE company_id = ? AND is_active = true", 
            (company_id,)
        )
        stats['total_users'] = result.get('count', 0) if result else 0
        
        # Approved users - is_approved = true
        result = db.query_one(
            "SELECT COUNT(*) as count FROM users WHERE company_id = ? AND is_approved = true AND is_active = true", 
            (company_id,)
        )
        stats['approved_users'] = result.get('count', 0) if result else 0
        
        # Pending requests - is_approved = false and not individual
        result = db.query_one(
            "SELECT COUNT(*) as count FROM users WHERE company_id = ? AND is_approved = false AND is_active = true AND role != 'individual'", 
            (company_id,)
        )
        stats['pending_requests'] = result.get('count', 0) if result else 0
        
        # Company admins - is_company_admin = true
        result = db.query_one(
            "SELECT COUNT(*) as count FROM users WHERE company_id = ? AND is_company_admin = true AND is_active = true", 
            (company_id,)
        )
        stats['company_admins'] = result.get('count', 0) if result else 0
        
        # Company users (non-admins)
        stats['company_users'] = stats['approved_users'] - stats['company_admins']
        
        return stats

    def approve_user_access(self, user_id: int, company_id: int, admin_id: int, 
                        make_admin: bool = False) -> bool:
        """Approve a user's access to the company"""
        db = self._get_db()
        
        try:
            # Update user approval status - use boolean true/false for Supabase
            result = db.execute("""
                UPDATE users 
                SET is_approved = true,
                    approved_by = ?,
                    approved_at = CURRENT_TIMESTAMP,
                    is_company_admin = ?,
                    company_admin_approved_by = ?,
                    company_admin_approved_at = CURRENT_TIMESTAMP,
                    role = ?
                WHERE id = ? AND company_id = ?
            """, (
                admin_id, 
                make_admin,  # true/false boolean
                admin_id if make_admin else None,
                'company_admin' if make_admin else 'company_user',
                user_id, 
                company_id
            ))
            
            if result > 0:
                # Log the action
                self._log_access_action(
                    user_id, company_id, admin_id, 'approved', 
                    f"Access approved. Admin status: {make_admin}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to approve user access: {e}")
            return False

    def reject_user_access(self, user_id: int, company_id: int, admin_id: int) -> bool:
        """Reject a user's access request"""
        db = self._get_db()
        
        try:
            # Remove user from company
            result = db.execute("""
                UPDATE users 
                SET company_id = NULL,
                    is_approved = false,
                    approved_by = NULL,
                    approved_at = NULL,
                    is_company_admin = false,
                    company_admin_approved_by = NULL,
                    company_admin_approved_at = NULL,
                    role = 'individual'
                WHERE id = ? AND company_id = ?
            """, (user_id, company_id))
            
            if result > 0:
                self._log_access_action(
                    user_id, company_id, admin_id, 'rejected', 
                    "Access request rejected by admin"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to reject user access: {e}")
            return False

    def revoke_user_access(self, user_id: int, company_id: int, admin_id: int) -> bool:
        """Revoke a user's company access"""
        db = self._get_db()
        
        try:
            # Remove user from company
            result = db.execute("""
                UPDATE users 
                SET company_id = NULL,
                    is_approved = false,
                    approved_by = NULL,
                    approved_at = NULL,
                    is_company_admin = false,
                    company_admin_approved_by = NULL,
                    company_admin_approved_at = NULL,
                    role = 'individual'
                WHERE id = ? AND company_id = ?
            """, (user_id, company_id))
            
            if result > 0:
                self._log_access_action(
                    user_id, company_id, admin_id, 'revoked', 
                    "Access revoked by admin"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to revoke user access: {e}")
            return False

    def update_user_admin_status(self, user_id: int, company_id: int, 
                                admin_id: int, make_admin: bool) -> bool:
        """Update user's company admin status"""
        db = self._get_db()
        
        try:
            result = db.execute("""
                UPDATE users 
                SET is_company_admin = ?,
                    company_admin_approved_by = ?,
                    company_admin_approved_at = CURRENT_TIMESTAMP,
                    role = ?
                WHERE id = ? AND company_id = ?
            """, (
                make_admin,  # true/false boolean
                admin_id if make_admin else None,
                'company_admin' if make_admin else 'company_user',
                user_id,
                company_id
            ))
            
            if result > 0:
                self._log_access_action(
                    user_id, company_id, admin_id, 'updated', 
                    f"Admin status updated to: {'company_admin' if make_admin else 'company_user'}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update user admin status: {e}")
            return False

    def check_user_company_access(self, user_id: int, company_id: int) -> Dict:
        """Check if user has access to a company"""
        db = self._get_db()
        
        user = db.query_one("""
            SELECT 
                id, 
                is_approved, 
                is_company_admin,
                role,
                is_active
            FROM users 
            WHERE id = ? AND company_id = ?
        """, (user_id, company_id))
        
        if not user:
            return {'has_access': False, 'reason': 'User not found in this company'}
        
        if not user.get('is_active'):
            return {'has_access': False, 'reason': 'User is inactive'}
        
        if not user.get('is_approved'):
            return {'has_access': False, 'reason': 'User access pending approval'}
        
        return {
            'has_access': True,
            'is_admin': user.get('is_company_admin', False) == True,
            'role': user.get('role', 'company_user'),
            'user_data': user
        }
    def invite_user_to_company(self, email: str, company_id: int, 
                              admin_id: int, make_admin: bool = False) -> Dict:
        """Invite a user to join the company"""
        db = self._get_db()
        
        try:
            # Check if user exists
            user = db.query_one("SELECT id, company_id, is_approved FROM users WHERE email = ?", (email,))
            
            if user:
                if user.get('company_id') == company_id:
                    return {'success': False, 'message': 'User is already associated with this company.'}
                elif user.get('company_id'):
                    return {'success': False, 'message': 'User is already associated with another company.'}
                else:
                    # Update user's company
                    result = db.execute("""
                        UPDATE users 
                        SET company_id = ?,
                            is_approved = 0,
                            approved_by = NULL,
                            approved_at = NULL,
                            is_company_admin = ?,
                            company_admin_approved_by = ?,
                            company_admin_approved_at = NULL
                        WHERE id = ?
                    """, (
                        company_id,
                        1 if make_admin else 0,
                        admin_id if make_admin else None,
                        user['id']
                    ))
                    
                    if result > 0:
                        return {'success': True, 'message': f'User {email} has been invited to the company!'}
                    return {'success': False, 'message': 'Failed to invite user.'}
            else:
                return {'success': False, 'message': f'User with email {email} not found. Please ask them to register first.'}
        except Exception as e:
            logger.error(f"Failed to invite user: {e}")
            return {'success': False, 'message': f'Error: {str(e)}'}
    
   
    def get_user_companies(self, user_id: int) -> List[Dict]:
        """Get all companies a user has access to"""
        db = self._get_db()
        
        return db.query("""
            SELECT 
                c.id,
                c.company_name,
                c.registration_number,
                c.email,
                c.phone,
                u.is_approved,
                u.is_company_admin,
                u.role,
                u.approved_at
            FROM companies c
            JOIN users u ON u.company_id = c.id
            WHERE u.id = ? AND u.is_approved = 1 AND u.is_active = 1
            ORDER BY u.is_company_admin DESC, c.company_name
        """, (user_id,))
    
    def _log_access_action(self, user_id: int, company_id: int, 
                          admin_id: int, action: str, notes: str = ''):
        """Log access action to audit trail"""
        try:
            db = self._get_db()
            # Check if audit_logs table exists, if not, create a simple log
            db.execute("""
                INSERT INTO company_access_logs 
                (user_id, company_id, admin_id, action, notes, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, company_id, admin_id, action, notes))
        except Exception as e:
            # Table might not exist, just log to console
            logger.info(f"Access action: {action} - User: {user_id}, Company: {company_id}, Admin: {admin_id}, Notes: {notes}")
    
    def get_access_logs(self, company_id: int, limit: int = 50) -> List[Dict]:
        """Get access logs for a company"""
        db = self._get_db()
        
        try:
            return db.query("""
                SELECT 
                    l.*,
                    u.full_name as user_name,
                    u.email as user_email,
                    a.full_name as admin_name,
                    a.email as admin_email
                FROM company_access_logs l
                LEFT JOIN users u ON l.user_id = u.id
                LEFT JOIN users a ON l.admin_id = a.id
                WHERE l.company_id = ?
                ORDER BY l.created_at DESC
                LIMIT ?
            """, (company_id, limit))
        except Exception as e:
            # Table might not exist
            logger.warning(f"Access logs table may not exist: {e}")
            return []
    
    def get_user_access_level(self, user_id: int, company_id: int) -> Optional[str]:
        """Get user's access level for a company"""
        db = self._get_db()
        
        user = db.query_one("""
            SELECT 
                CASE 
                    WHEN is_company_admin = 1 THEN 'admin'
                    WHEN role = 'company_admin' THEN 'admin'
                    WHEN role = 'manager' THEN 'manager'
                    WHEN role = 'analyst' THEN 'analyst'
                    ELSE 'viewer'
                END as access_level
            FROM users 
            WHERE id = ? AND company_id = ? AND is_approved = 1 AND is_active = 1
        """, (user_id, company_id))
        
        return user.get('access_level') if user else None
    
    def can_user_edit_company_data(self, user_id: int, company_id: int) -> bool:
        """Check if user can edit company data"""
        db = self._get_db()
        
        user = db.query_one("""
            SELECT is_company_admin, role
            FROM users 
            WHERE id = ? AND company_id = ? AND is_approved = 1 AND is_active = 1
        """, (user_id, company_id))
        
        if not user:
            return False
        
        # Admin or manager level roles can edit
        return user.get('is_company_admin', 0) == 1 or user.get('role') in ['manager', 'company_admin']

