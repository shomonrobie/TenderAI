# database/enhanced_db_manager.py
"""
Enhanced Database Manager with Knowledge Repository Support
"""

import sqlite3
import json
import hashlib
import pickle
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List, Union, Tuple
from pathlib import Path
import pandas as pd
import numpy as np
import os

from database.enhanced_schema import (
    CREATE_TABLES, CREATE_INDEXES, CREATE_TRIGGERS, 
    SCHEMA_VERSION, get_all_create_statements
)

logger = logging.getLogger(__name__)

class EnhancedDatabaseManager:
    """Enhanced database manager with company knowledge repository"""
    
    def __init__(self, db_path="data/enhanced_tender_system.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize enhanced schema
        self.init_enhanced_schema()
        
        # Migrate existing data if needed
        self.migrate_from_legacy()
    
    def get_connection(self):
        """Get database connection with foreign keys enabled"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_enhanced_schema(self):
        """Initialize all enhanced schema tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create schema version table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Check current version
        cursor.execute("SELECT MAX(version) FROM schema_version")
        result = cursor.fetchone()
        current_version = result[0] if result and result[0] else 0
        
        if current_version < SCHEMA_VERSION:
            # Create all tables
            for create_stmt in get_all_create_statements():
                try:
                    cursor.execute(create_stmt)
                except sqlite3.OperationalError as e:
                    if "already exists" not in str(e):
                        logger.warning(f"Table creation warning: {e}")
            
            # Create indexes
            for index_stmt in CREATE_INDEXES.split(';'):
                if index_stmt.strip():
                    try:
                        cursor.execute(index_stmt)
                    except sqlite3.OperationalError as e:
                        if "already exists" not in str(e):
                            logger.warning(f"Index creation warning: {e}")
            
            # Create triggers
            for trigger_stmt in CREATE_TRIGGERS.split(';'):
                if trigger_stmt.strip():
                    try:
                        cursor.execute(trigger_stmt)
                    except sqlite3.OperationalError as e:
                        if "already exists" not in str(e):
                            logger.warning(f"Trigger creation warning: {e}")
            
            # Record schema version
            cursor.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,)
            )
            conn.commit()
            print(f"✅ Enhanced schema v{SCHEMA_VERSION} initialized")
        
        conn.close()
    
    # =========================================================
    # COMPANY PROFILE MANAGEMENT
    # =========================================================
    
    def save_company_profile(self, company_id: int, profile_data: Dict) -> bool:
        """Save or update company profile"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO company_profile (
                    company_id, legal_name, trade_name, registration_number,
                    date_of_incorporation, business_nature, business_category,
                    registered_address, corporate_address, phone_primary,
                    phone_secondary, email_primary, email_secondary, website,
                    fax, division, district, upazila, post_code, status,
                    updated_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving company profile: {e}")
            return False
        finally:
            conn.close()
    
    def get_company_profile(self, company_id: int) -> Optional[Dict]:
        """Get company profile"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM company_profile WHERE company_id = ?", (company_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    # =========================================================
    # DOCUMENT MANAGEMENT WITH VERSIONING
    # =========================================================
    
    def add_document(self, company_id: int, document_data: Dict, file_content: bytes = None) -> Optional[int]:
        """
        Add a new document with version control
        
        Args:
            company_id: Company ID
            document_data: Document metadata
            file_content: Optional file content for hash generation
        
        Returns:
            Document ID if successful
        """
        import uuid
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            doc_uuid = str(uuid.uuid4())
            file_hash = None
            extracted_text = document_data.get('extracted_text', '')
            
            if file_content:
                file_hash = hashlib.sha256(file_content).hexdigest()
            
            cursor.execute("""
                INSERT INTO document_registry (
                    company_id, document_uuid, document_name, document_type,
                    reference_id, reference_table, version_number, is_latest_version,
                    file_path, file_name, file_size, file_hash, mime_type,
                    extracted_text, description, tags, category, language,
                    document_date, expiry_date, effective_date, verification_status,
                    uploaded_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id, doc_uuid, document_data['document_name'],
                document_data['document_type'], document_data.get('reference_id'),
                document_data.get('reference_table'), 1, 1,
                document_data['file_path'], document_data.get('file_name'),
                document_data.get('file_size'), file_hash, document_data.get('mime_type'),
                extracted_text, document_data.get('description'),
                json.dumps(document_data.get('tags', [])), document_data.get('category'),
                document_data.get('language', 'en'), document_data.get('document_date'),
                document_data.get('expiry_date'), document_data.get('effective_date'),
                document_data.get('verification_status', 'pending'),
                document_data.get('uploaded_by')
            ))
            
            doc_id = cursor.lastrowid
            conn.commit()
            
            # Add to FTS
            self._index_document_for_search(doc_id, extracted_text, document_data)
            
            return doc_id
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def update_document(self, document_id: int, new_version_data: Dict, file_content: bytes = None) -> Optional[int]:
        """
        Create a new version of an existing document
        
        Args:
            document_id: Existing document ID
            new_version_data: New version metadata
            file_content: New file content
        
        Returns:
            New document version ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get current document
            cursor.execute(
                "SELECT * FROM document_registry WHERE id = ?",
                (document_id,)
            )
            current = cursor.fetchone()
            
            if not current:
                return None
            
            # Mark current as not latest
            cursor.execute(
                "UPDATE document_registry SET is_latest_version = 0 WHERE id = ?",
                (document_id,)
            )
            
            # Create new version
            new_doc_id = self.add_document(
                current['company_id'],
                {
                    'document_name': new_version_data.get('document_name', current['document_name']),
                    'document_type': current['document_type'],
                    'reference_id': current['reference_id'],
                    'reference_table': current['reference_table'],
                    'file_path': new_version_data.get('file_path', current['file_path']),
                    'file_name': new_version_data.get('file_name', current['file_name']),
                    'file_size': new_version_data.get('file_size', current['file_size']),
                    'mime_type': new_version_data.get('mime_type', current['mime_type']),
                    'description': new_version_data.get('description', current['description']),
                    'tags': new_version_data.get('tags', json.loads(current['tags'] or '[]')),
                    'category': new_version_data.get('category', current['category']),
                    'document_date': new_version_data.get('document_date', current['document_date']),
                    'expiry_date': new_version_data.get('expiry_date', current['expiry_date']),
                    'effective_date': new_version_data.get('effective_date', current['effective_date']),
                    'uploaded_by': new_version_data.get('uploaded_by', current['uploaded_by']),
                    'extracted_text': new_version_data.get('extracted_text', current['extracted_text'])
                },
                file_content
            )
            
            # Link versions
            cursor.execute("""
                UPDATE document_registry 
                SET previous_version_id = ? 
                WHERE id = ?
            """, (document_id, new_doc_id))
            
            conn.commit()
            return new_doc_id
            
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def _index_document_for_search(self, doc_id: int, content: str, metadata: Dict):
        """Index document for full-text search"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO fts_documents (
                    company_id, document_uuid, entity_type, entity_id,
                    field_name, content, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.get('company_id'),
                metadata.get('document_uuid'),
                'document',
                doc_id,
                'full_text',
                content,
                json.dumps({'document_name': metadata.get('document_name'), 'tags': metadata.get('tags')})
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error indexing document: {e}")
        finally:
            conn.close()
    
    # =========================================================
    # SEMANTIC SEARCH WITH VECTOR EMBEDDINGS
    # =========================================================
    
    def store_embedding(self, company_id: int, entity_type: str, entity_id: int,
                       field_name: str, text: str, embedding: List[float],
                       model_name: str = "text-embedding-3-small") -> bool:
        """Store vector embedding for semantic search"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            embedding_blob = pickle.dumps(embedding)
            content_hash = hashlib.sha256(text.encode()).hexdigest()
            
            cursor.execute("""
                INSERT OR REPLACE INTO vector_embeddings (
                    company_id, entity_type, entity_id, field_name,
                    embedding_model, embedding_dimension, embedding_vector,
                    original_text, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id, entity_type, entity_id, field_name,
                model_name, len(embedding), embedding_blob,
                text[:5000], content_hash
            ))
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error storing embedding: {e}")
            return False
        finally:
            conn.close()
    
    def semantic_search(self, company_id: int, query: str, 
                       query_embedding: List[float],
                       entity_types: List[str] = None,
                       limit: int = 20) -> List[Dict]:
        """
        Perform semantic search using vector similarity
        
        Args:
            company_id: Company ID
            query: Original query text
            query_embedding: Query vector embedding
            entity_types: Filter by entity types
            limit: Max results
        
        Returns:
            List of search results
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Note: SQLite doesn't have native vector similarity
            # For production, use PostgreSQL with pgvector or a dedicated vector DB
            # This is a simplified version that loads embeddings and computes similarity
            
            # Build query
            sql = """
                SELECT entity_type, entity_id, field_name, original_text, embedding_vector
                FROM vector_embeddings
                WHERE company_id = ?
            """
            params = [company_id]
            
            if entity_types:
                placeholders = ','.join(['?'] * len(entity_types))
                sql += f" AND entity_type IN ({placeholders})"
                params.extend(entity_types)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Compute cosine similarity
            import numpy as np
            
            results = []
            query_vec = np.array(query_embedding)
            
            for row in rows:
                stored_vec = np.array(pickle.loads(row[4]))
                similarity = self._cosine_similarity(query_vec, stored_vec)
                
                results.append({
                    'entity_type': row[0],
                    'entity_id': row[1],
                    'field_name': row[2],
                    'content': row[3][:500],
                    'similarity_score': float(similarity)
                })
            
            # Sort by similarity and limit
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            results = results[:limit]
            
            # Log search
            self._log_semantic_search(company_id, query, len(results))
            
            return results
            
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return []
        finally:
            conn.close()
    
    def hybrid_search(self, company_id: int, query: str, query_embedding: List[float],
                     entity_types: List[str] = None, limit: int = 20) -> List[Dict]:
        """
        Hybrid search combining semantic and keyword (FTS) search
        """
        # Get semantic results
        semantic_results = self.semantic_search(company_id, query, query_embedding, entity_types, limit * 2)
        
        # Get keyword results from FTS
        keyword_results = self.keyword_search(company_id, query, entity_types, limit * 2)
        
        # Combine and deduplicate with weighted scoring
        combined = {}
        
        for r in semantic_results:
            key = f"{r['entity_type']}_{r['entity_id']}_{r['field_name']}"
            combined[key] = {
                **r,
                'semantic_score': r['similarity_score'],
                'keyword_score': 0,
                'combined_score': r['similarity_score'] * 0.7
            }
        
        for r in keyword_results:
            key = f"{r['entity_type']}_{r['entity_id']}_{r['field_name']}"
            if key in combined:
                combined[key]['keyword_score'] = r.get('relevance', 0)
                combined[key]['combined_score'] = (
                    combined[key]['semantic_score'] * 0.5 + 
                    r.get('relevance', 0) * 0.5
                )
            else:
                combined[key] = {
                    **r,
                    'semantic_score': 0,
                    'keyword_score': r.get('relevance', 0),
                    'combined_score': r.get('relevance', 0) * 0.3
                }
        
        results = list(combined.values())
        results.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return results[:limit]
    
    def keyword_search(self, company_id: int, query: str, 
                      entity_types: List[str] = None, limit: int = 20) -> List[Dict]:
        """Keyword search using FTS5"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            sql = """
                SELECT 
                    entity_type, entity_id, field_name, content,
                    rank as relevance
                FROM fts_documents 
                WHERE fts_documents MATCH ? AND company_id = ?
            """
            params = [query, company_id]
            
            if entity_types:
                placeholders = ','.join(['?'] * len(entity_types))
                sql += f" AND entity_type IN ({placeholders})"
                params.extend(entity_types)
            
            sql += f" LIMIT {limit}"
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            return [
                {
                    'entity_type': row[0],
                    'entity_id': row[1],
                    'field_name': row[2],
                    'content': row[3][:500] if row[3] else '',
                    'relevance': float(row[4]) if row[4] else 0
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
        finally:
            conn.close()
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    def _log_semantic_search(self, company_id: int, query: str, result_count: int):
        """Log semantic search for analytics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO semantic_search_log (company_id, query_text, result_count)
                VALUES (?, ?, ?)
            """, (company_id, query[:500], result_count))
            conn.commit()
        except Exception as e:
            logger.error(f"Error logging search: {e}")
        finally:
            conn.close()
    
    # =========================================================
    # EXPERIENCE & PROJECT MANAGEMENT
    # =========================================================
    
    def add_experience(self, company_id: int, experience_data: Dict) -> Optional[int]:
        """Add experience record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO experience_record (
                    company_id, project_name, project_location, client_name,
                    client_type, procuring_entity, contract_number, contract_date,
                    completion_date, contract_value, currency, nature_of_work,
                    scope_of_work, key_deliverables, is_completed, is_running,
                    completion_percentage, quality_rating, safety_rating,
                    client_satisfaction, project_manager, site_engineer,
                    contract_document_path, completion_certificate_path,
                    performance_certificate_path, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                experience_data.get('project_name'),
                experience_data.get('project_location'),
                experience_data.get('client_name'),
                experience_data.get('client_type'),
                experience_data.get('procuring_entity'),
                experience_data.get('contract_number'),
                experience_data.get('contract_date'),
                experience_data.get('completion_date'),
                experience_data.get('contract_value'),
                experience_data.get('currency', 'BDT'),
                experience_data.get('nature_of_work'),
                experience_data.get('scope_of_work'),
                experience_data.get('key_deliverables'),
                experience_data.get('is_completed', 0),
                experience_data.get('is_running', 0),
                experience_data.get('completion_percentage', 0),
                experience_data.get('quality_rating'),
                experience_data.get('safety_rating'),
                experience_data.get('client_satisfaction'),
                experience_data.get('project_manager'),
                experience_data.get('site_engineer'),
                experience_data.get('contract_document_path'),
                experience_data.get('completion_certificate_path'),
                experience_data.get('performance_certificate_path'),
                experience_data.get('created_by')
            ))
            
            exp_id = cursor.lastrowid
            conn.commit()
            return exp_id
            
        except Exception as e:
            logger.error(f"Error adding experience: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def get_experiences(self, company_id: int, limit: int = 100) -> pd.DataFrame:
        """Get all experiences for a company"""
        conn = self.get_connection()
        
        try:
            df = pd.read_sql_query("""
                SELECT * FROM experience_record 
                WHERE company_id = ? 
                ORDER BY completion_date DESC
                LIMIT ?
            """, conn, params=[company_id, limit])
            return df
            
        except Exception as e:
            logger.error(f"Error getting experiences: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    # =========================================================
    # PERSONNEL MANAGEMENT
    # =========================================================
    
    def add_personnel(self, company_id: int, personnel_data: Dict) -> Optional[int]:
        """Add personnel record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO personnel (
                    company_id, full_name, father_name, mother_name, spouse_name,
                    date_of_birth, nationality, nid_number, passport_number,
                    birth_certificate_number, personal_phone, personal_email,
                    present_address, permanent_address, designation, department,
                    employee_id, joining_date, confirmation_date,
                    educational_qualification, professional_certifications,
                    skills, languages, cv_path, photo_path, employment_status,
                    is_key_personnel, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                personnel_data.get('full_name'),
                personnel_data.get('father_name'),
                personnel_data.get('mother_name'),
                personnel_data.get('spouse_name'),
                personnel_data.get('date_of_birth'),
                personnel_data.get('nationality', 'Bangladeshi'),
                personnel_data.get('nid_number'),
                personnel_data.get('passport_number'),
                personnel_data.get('birth_certificate_number'),
                personnel_data.get('personal_phone'),
                personnel_data.get('personal_email'),
                personnel_data.get('present_address'),
                personnel_data.get('permanent_address'),
                personnel_data.get('designation'),
                personnel_data.get('department'),
                personnel_data.get('employee_id'),
                personnel_data.get('joining_date'),
                personnel_data.get('confirmation_date'),
                personnel_data.get('educational_qualification'),
                json.dumps(personnel_data.get('professional_certifications', [])),
                json.dumps(personnel_data.get('skills', [])),
                json.dumps(personnel_data.get('languages', [])),
                personnel_data.get('cv_path'),
                personnel_data.get('photo_path'),
                personnel_data.get('employment_status', 'active'),
                personnel_data.get('is_key_personnel', 0),
                personnel_data.get('created_by')
            ))
            
            personnel_id = cursor.lastrowid
            conn.commit()
            return personnel_id
            
        except Exception as e:
            logger.error(f"Error adding personnel: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    # =========================================================
    # EQUIPMENT MANAGEMENT
    # =========================================================
    
    def add_equipment(self, company_id: int, equipment_data: Dict) -> Optional[int]:
        """Add equipment record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO equipment (
                    company_id, equipment_name, equipment_type, model,
                    manufacturer, serial_number, capacity, power_rating,
                    fuel_type, year_of_manufacture, country_of_origin,
                    ownership_type, owner_name, registration_number,
                    chassis_number, engine_number, purchase_date,
                    purchase_cost, currency, supplier_name, invoice_number,
                    current_status, location, operator_name, operating_hours,
                    last_maintenance_date, next_maintenance_date, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                equipment_data.get('equipment_name'),
                equipment_data.get('equipment_type'),
                equipment_data.get('model'),
                equipment_data.get('manufacturer'),
                equipment_data.get('serial_number'),
                equipment_data.get('capacity'),
                equipment_data.get('power_rating'),
                equipment_data.get('fuel_type'),
                equipment_data.get('year_of_manufacture'),
                equipment_data.get('country_of_origin'),
                equipment_data.get('ownership_type'),
                equipment_data.get('owner_name'),
                equipment_data.get('registration_number'),
                equipment_data.get('chassis_number'),
                equipment_data.get('engine_number'),
                equipment_data.get('purchase_date'),
                equipment_data.get('purchase_cost'),
                equipment_data.get('currency', 'BDT'),
                equipment_data.get('supplier_name'),
                equipment_data.get('invoice_number'),
                equipment_data.get('current_status', 'available'),
                equipment_data.get('location'),
                equipment_data.get('operator_name'),
                equipment_data.get('operating_hours', 0),
                equipment_data.get('last_maintenance_date'),
                equipment_data.get('next_maintenance_date'),
                equipment_data.get('created_by')
            ))
            
            equipment_id = cursor.lastrowid
            conn.commit()
            return equipment_id
            
        except Exception as e:
            logger.error(f"Error adding equipment: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    # =========================================================
    # FINANCIAL CAPACITY MANAGEMENT
    # =========================================================
    
    def add_financial_capacity(self, company_id: int, financial_data: Dict) -> Optional[int]:
        """Add financial capacity record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO financial_capacity (
                    company_id, fiscal_year, annual_turnover, construction_turnover,
                    export_turnover, total_assets, current_assets, fixed_assets,
                    total_liabilities, current_liabilities, net_worth,
                    liquid_assets, cash_and_bank, working_capital,
                    current_ratio, quick_ratio, debt_to_equity_ratio,
                    profit_margin, credit_limit, bank_guarantee_limit,
                    overdraft_limit, letter_of_credit_limit, audited_by,
                    audit_firm, audit_report_path, audit_date, is_audited
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                financial_data.get('fiscal_year'),
                financial_data.get('annual_turnover'),
                financial_data.get('construction_turnover'),
                financial_data.get('export_turnover'),
                financial_data.get('total_assets'),
                financial_data.get('current_assets'),
                financial_data.get('fixed_assets'),
                financial_data.get('total_liabilities'),
                financial_data.get('current_liabilities'),
                financial_data.get('net_worth'),
                financial_data.get('liquid_assets'),
                financial_data.get('cash_and_bank'),
                financial_data.get('working_capital'),
                financial_data.get('current_ratio'),
                financial_data.get('quick_ratio'),
                financial_data.get('debt_to_equity_ratio'),
                financial_data.get('profit_margin'),
                financial_data.get('credit_limit'),
                financial_data.get('bank_guarantee_limit'),
                financial_data.get('overdraft_limit'),
                financial_data.get('letter_of_credit_limit'),
                financial_data.get('audited_by'),
                financial_data.get('audit_firm'),
                financial_data.get('audit_report_path'),
                financial_data.get('audit_date'),
                financial_data.get('is_audited', 0)
            ))
            
            fin_id = cursor.lastrowid
            conn.commit()
            return fin_id
            
        except Exception as e:
            logger.error(f"Error adding financial capacity: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    # Add to database/enhanced_db_manager.py after line 700 (around the tracking methods)

    # =========================================================
    # EXTENSION USAGE TRACKING METHODS
    # =========================================================
    
    def get_extension_fill_usage(self, company_id: int, period: str = 'monthly') -> Dict:
        """
        Get extension auto-fill usage for a company.
        
        Args:
            company_id: Company ID
            period: 'monthly' or 'yearly'
        
        Returns:
            Dict with used count, limit, remaining
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get subscription plan
        sub = self.get_company_subscription(company_id)
        plan = sub.get('plan', 'free')
        
        # Define limits per plan
        plan_limits = {
            'free': 5,
            'basic': 30,
            'professional': 100,
            'enterprise': -1  # Unlimited
        }
        
        limit = plan_limits.get(plan, 5)
        
        # Get current period usage
        now = datetime.now()
        if period == 'monthly':
            start_date = datetime(now.year, now.month, 1)
        else:
            start_date = datetime(now.year, 1, 1)
        
        cursor.execute("""
            SELECT COUNT(*) FROM extension_auto_fill_log
            WHERE company_id = ? AND filled_at >= ?
        """, (company_id, start_date))
        
        used = cursor.fetchone()[0] or 0
        conn.close()
        
        return {
            'used': used,
            'limit': limit,
            'remaining': -1 if limit == -1 else max(0, limit - used),
            'is_unlimited': limit == -1
        }
    
    def log_extension_fill(self, company_id: int, user_id: int, field_label: str, 
                          confidence: float, page_url: str) -> bool:
        """Log an auto-fill action from the extension"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO extension_auto_fill_log (
                    company_id, user_id, field_label, confidence_score, 
                    page_url, filled_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (company_id, user_id, field_label, confidence, page_url, datetime.now()))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error logging extension fill: {e}")
            return False
        finally:
            conn.close()
    
    def can_use_extension_fill(self, company_id: int) -> Tuple[bool, str, int]:
        """
        Check if company can use extension auto-fill.
        
        Returns:
            (can_use, message, remaining)
        """
        usage = self.get_extension_fill_usage(company_id)
        
        if usage['is_unlimited']:
            return True, "Unlimited fills available", -1
        
        if usage['remaining'] > 0:
            return True, f"{usage['remaining']} fills remaining this month", usage['remaining']
        else:
            return False, f"You've used all {usage['limit']} auto-fills this month. Upgrade to continue.", 0
    
    # Add to database/enhanced_db_manager.py in the EnhancedDatabaseManager class
# Add this after the __init__ method or before the get_connection method

    # =========================================================
    # SUBSCRIPTION METHODS (Required for extension tracking)
    # =========================================================
    
    def get_company_subscription(self, company_id: int) -> Dict[str, Any]:
        """Get subscription details for a company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if subscriptions table has the required columns
            cursor.execute("PRAGMA table_info(subscriptions)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Build query based on available columns
            select_fields = ['id', 'plan', 'status', 'start_date', 'end_date']
            
            # Add optional fields if they exist
            if 'analyses_used' in columns:
                select_fields.append('analyses_used')
            else:
                select_fields.append('0 as analyses_used')
                
            if 'analyses_limit' in columns:
                select_fields.append('analyses_limit')
            else:
                select_fields.append('5 as analyses_limit')
                
            if 'payment_method' in columns:
                select_fields.append('payment_method')
            else:
                select_fields.append('NULL as payment_method')
                
            if 'transaction_id' in columns:
                select_fields.append('transaction_id')
            else:
                select_fields.append('NULL as transaction_id')
                
            if 'updated_at' in columns:
                select_fields.append('updated_at')
            else:
                select_fields.append('NULL as updated_at')
                
            if 'created_at' in columns:
                select_fields.append('created_at')
            else:
                select_fields.append('CURRENT_TIMESTAMP as created_at')
                
            if 'boq_used' in columns:
                select_fields.append('boq_used')
            else:
                select_fields.append('0 as boq_used')
                
            if 'bid_optimizations_used' in columns:
                select_fields.append('bid_optimizations_used')
            else:
                select_fields.append('0 as bid_optimizations_used')
            
            query = f"""
                SELECT {', '.join(select_fields)}
                FROM subscriptions 
                WHERE company_id = ? AND company_id IS NOT NULL
                ORDER BY created_at DESC LIMIT 1
            """
            
            cursor.execute(query, (company_id,))
            result = cursor.fetchone()
            
            if result:
                # Get column names for mapping
                cursor.execute(f"PRAGMA table_info(subscriptions)")
                col_names = [col[1] for col in cursor.fetchall()]
                
                subscription = {}
                for i, field in enumerate(select_fields):
                    # Handle aliased fields (like '0 as analyses_used')
                    if ' as ' in field:
                        field_name = field.split(' as ')[1].strip()
                    else:
                        field_name = field
                    subscription[field_name] = result[i] if result[i] is not None else (0 if 'used' in field_name or 'limit' in field_name else None)
                
                conn.close()
                return subscription
            
            conn.close()
            # Return default free plan
            return {
                'id': None,
                'plan': 'free',
                'status': 'active',
                'analyses_used': 0,
                'analyses_limit': 5,
                'boq_used': 0,
                'bid_optimizations_used': 0,
                'payment_method': None,
                'transaction_id': None
            }
            
        except Exception as e:
            logger.error(f"Error getting company subscription: {e}")
            conn.close()
            return {
                'plan': 'free',
                'status': 'active',
                'analyses_used': 0,
                'analyses_limit': 5,
                'boq_used': 0,
                'bid_optimizations_used': 0
            }
    
    def get_extension_fill_usage(self, company_id: int, period: str = 'monthly') -> Dict:
        """Get extension auto-fill usage for a company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get subscription plan
        sub = self.get_company_subscription(company_id)
        plan = sub.get('plan', 'free')
        
        # Define limits per plan
        plan_limits = {
            'free': 5,
            'basic': 30,
            'professional': 100,
            'enterprise': -1
        }
        
        limit = plan_limits.get(plan, 5)
        
        # Get current period usage
        now = datetime.now()
        if period == 'monthly':
            start_date = datetime(now.year, now.month, 1)
        else:
            start_date = datetime(now.year, 1, 1)
        
        # Check if extension_auto_fill_log table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='extension_auto_fill_log'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            cursor.execute("""
                SELECT COUNT(*) FROM extension_auto_fill_log
                WHERE company_id = ? AND filled_at >= ?
            """, (company_id, start_date))
            used = cursor.fetchone()[0] or 0
        else:
            used = 0
        
        conn.close()
        
        return {
            'used': used,
            'limit': limit,
            'remaining': -1 if limit == -1 else max(0, limit - used),
            'is_unlimited': limit == -1,
            'plan': plan
        }
    
    def log_extension_fill(self, company_id: int, user_id: int, field_label: str, 
                          confidence: float, page_url: str) -> bool:
        """Log an auto-fill action from the extension"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Create table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extension_auto_fill_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    field_label TEXT,
                    confidence_score REAL,
                    page_url TEXT,
                    filled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                INSERT INTO extension_auto_fill_log (
                    company_id, user_id, field_label, confidence_score, page_url, filled_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (company_id, user_id, field_label, confidence, page_url, datetime.now()))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error logging extension fill: {e}")
            return False
        finally:
            conn.close()
    
    # =========================================================
    # TENDER RESPONSE TEMPLATES & AUTO-FILL
    # =========================================================
    
    def get_auto_fill_data(self, company_id: int, data_type: str, 
                          search_term: str = None) -> Dict:
        """
        Get data for auto-filling forms
        
        Args:
            company_id: Company ID
            data_type: Type of data (personnel, equipment, experience, financial)
            search_term: Optional search term
        
        Returns:
            Dictionary with categorized auto-fill data
        """
        result = {}
        conn = self.get_connection()
        
        try:
            if data_type == 'personnel':
                # Get key personnel
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, full_name, designation, employee_id,
                           educational_qualification, skills
                    FROM personnel
                    WHERE company_id = ? AND employment_status = 'active'
                    AND is_key_personnel = 1
                    ORDER BY full_name
                """, (company_id,))
                
                personnel = []
                for row in cursor.fetchall():
                    personnel.append({
                        'id': row[0], 'name': row[1], 'designation': row[2],
                        'employee_id': row[3], 'qualification': row[4],
                        'skills': json.loads(row[5] or '[]')
                    })
                result['personnel'] = personnel
                
            elif data_type == 'equipment':
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, equipment_name, equipment_type, model,
                           capacity, current_status, ownership_type
                    FROM equipment
                    WHERE company_id = ? AND current_status = 'available'
                    ORDER BY equipment_name
                """, (company_id,))
                
                equipment = []
                for row in cursor.fetchall():
                    equipment.append({
                        'id': row[0], 'name': row[1], 'type': row[2],
                        'model': row[3], 'capacity': row[4],
                        'status': row[5], 'ownership': row[6]
                    })
                result['equipment'] = equipment
                
            elif data_type == 'experience':
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, project_name, client_name, contract_value,
                           completion_date, nature_of_work
                    FROM experience_record
                    WHERE company_id = ? AND is_completed = 1
                    ORDER BY completion_date DESC
                    LIMIT 20
                """, (company_id,))
                
                experiences = []
                for row in cursor.fetchall():
                    experiences.append({
                        'id': row[0], 'project': row[1], 'client': row[2],
                        'value': row[3], 'completion_date': row[4],
                        'nature_of_work': row[5]
                    })
                result['experiences'] = experiences
                
            elif data_type == 'financial':
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT fiscal_year, annual_turnover, net_worth,
                           working_capital, credit_limit, bank_guarantee_limit
                    FROM financial_capacity
                    WHERE company_id = ?
                    ORDER BY fiscal_year DESC
                    LIMIT 3
                """, (company_id,))
                
                financial = []
                for row in cursor.fetchall():
                    financial.append({
                        'year': row[0], 'turnover': row[1], 'net_worth': row[2],
                        'working_capital': row[3], 'credit_limit': row[4],
                        'bg_limit': row[5]
                    })
                result['financial'] = financial
                
            elif data_type == 'all':
                # Get all data types
                result = {
                    **self.get_auto_fill_data(company_id, 'personnel', search_term),
                    **self.get_auto_fill_data(company_id, 'equipment', search_term),
                    **self.get_auto_fill_data(company_id, 'experience', search_term),
                    **self.get_auto_fill_data(company_id, 'financial', search_term)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting auto-fill data: {e}")
            return {}
        finally:
            conn.close()
    
    def search_knowledge_base(self, company_id: int, query: str, 
                             categories: List[str] = None) -> List[Dict]:
        """
        Unified search across all knowledge base entities
        
        Args:
            company_id: Company ID
            query: Search query
            categories: Filter by categories (personnel, equipment, experience, financial, documents)
        
        Returns:
            List of search results with source information
        """
        results = []
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            query_like = f"%{query}%"
            
            if not categories or 'personnel' in categories:
                cursor.execute("""
                    SELECT 'personnel' as source, id, full_name as name, 
                           designation, phone, email
                    FROM personnel
                    WHERE company_id = ? AND employment_status = 'active'
                    AND (full_name LIKE ? OR designation LIKE ? OR employee_id LIKE ?)
                    LIMIT 10
                """, (company_id, query_like, query_like, query_like))
                
                for row in cursor.fetchall():
                    results.append({
                        'source': 'personnel',
                        'id': row[1],
                        'name': row[2],
                        'designation': row[3],
                        'phone': row[4],
                        'email': row[5],
                        'relevance': 1.0
                    })
            
            if not categories or 'equipment' in categories:
                cursor.execute("""
                    SELECT 'equipment' as source, id, equipment_name as name,
                           equipment_type, model, capacity, current_status
                    FROM equipment
                    WHERE company_id = ? AND current_status != 'scrapped'
                    AND (equipment_name LIKE ? OR model LIKE ? OR serial_number LIKE ?)
                    LIMIT 10
                """, (company_id, query_like, query_like, query_like))
                
                for row in cursor.fetchall():
                    results.append({
                        'source': 'equipment',
                        'id': row[1],
                        'name': row[2],
                        'type': row[3],
                        'model': row[4],
                        'capacity': row[5],
                        'status': row[6],
                        'relevance': 1.0
                    })
            
            if not categories or 'experience' in categories:
                cursor.execute("""
                    SELECT 'experience' as source, id, project_name as name,
                           client_name, contract_value, completion_date, nature_of_work
                    FROM experience_record
                    WHERE company_id = ? AND is_completed = 1
                    AND (project_name LIKE ? OR client_name LIKE ? OR nature_of_work LIKE ?)
                    ORDER BY completion_date DESC
                    LIMIT 10
                """, (company_id, query_like, query_like, query_like))
                
                for row in cursor.fetchall():
                    results.append({
                        'source': 'experience',
                        'id': row[1],
                        'name': row[2],
                        'client': row[3],
                        'value': row[4],
                        'date': row[5],
                        'nature': row[6],
                        'relevance': 1.0
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []
        finally:
            conn.close()
    
    # =========================================================
    # MIGRATION FROM LEGACY DATABASE
    # =========================================================
    
    def migrate_from_legacy(self, legacy_db_path="data/tender_system.db"):
        """Migrate data from legacy database to enhanced schema"""
        if not os.path.exists(legacy_db_path):
            print("No legacy database found for migration")
            return
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if already migrated
        cursor.execute("SELECT COUNT(*) FROM company_profile")
        count = cursor.fetchone()[0]
        
        if count > 0:
            print("Migration already performed or data exists")
            conn.close()
            return
        
        try:
            legacy_conn = sqlite3.connect(legacy_db_path)
            legacy_conn.row_factory = sqlite3.Row
            legacy_cursor = legacy_conn.cursor()
            
            # Migrate companies to company_profile
            legacy_cursor.execute("""
                SELECT id, company_name, email, phone, division, district,
                       address, registration_number, vat_number, created_at
                FROM companies
            """)
            
            for row in legacy_cursor.fetchall():
                self.save_company_profile(
                    row['id'],
                    {
                        'legal_name': row['company_name'],
                        'email_primary': row['email'],
                        'phone_primary': row['phone'],
                        'division': row['division'],
                        'district': row['district'],
                        'registered_address': row['address'],
                        'registration_number': row['registration_number']
                    }
                )
            
            # Migrate historical tenders to experience records
            legacy_cursor.execute("""
                SELECT id, company_id, tender_title, procuring_entity,
                       official_estimate, awarded_price, award_date
                FROM historical_tenders
                WHERE winning_company_type = 'Our Company'
            """)
            
            for row in legacy_cursor.fetchall():
                self.add_experience(
                    row['company_id'],
                    {
                        'project_name': row['tender_title'],
                        'client_name': row['procuring_entity'],
                        'contract_value': row['awarded_price'] or row['official_estimate'],
                        'completion_date': row['award_date'],
                        'is_completed': 1
                    }
                )
            
            print("✅ Migration from legacy database completed")
            
            legacy_conn.close()
            
        except Exception as e:
            logger.error(f"Migration error: {e}")
        finally:
            conn.close()
    # =========================================================
    # PERSONNEL METHODS
    # =========================================================
    
    def get_personnel(self, company_id: int, limit: int = 100) -> pd.DataFrame:
        """Get all personnel for a company"""
        try:
            conn = self.get_connection()
            df = pd.read_sql_query("""
                SELECT * FROM personnel 
                WHERE company_id = ? AND employment_status = 'active'
                ORDER BY full_name
                LIMIT ?
            """, conn, params=[company_id, limit])
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error getting personnel: {e}")
            return pd.DataFrame()
    
    def get_personnel_by_id(self, personnel_id: int) -> Optional[Dict]:
        """Get personnel by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM personnel WHERE id = ?", (personnel_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting personnel by ID: {e}")
            return None
    
    # =========================================================
    # EQUIPMENT METHODS
    # =========================================================
    
    def get_equipment(self, company_id: int, limit: int = 100) -> pd.DataFrame:
        """Get all equipment for a company"""
        try:
            conn = self.get_connection()
            df = pd.read_sql_query("""
                SELECT * FROM equipment 
                WHERE company_id = ?
                ORDER BY equipment_name
                LIMIT ?
            """, conn, params=[company_id, limit])
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error getting equipment: {e}")
            return pd.DataFrame()
    
    def get_equipment_by_id(self, equipment_id: int) -> Optional[Dict]:
        """Get equipment by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM equipment WHERE id = ?", (equipment_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting equipment by ID: {e}")
            return None
    
    # =========================================================
    # EXPERIENCE METHODS
    # =========================================================
    
    def get_experiences(self, company_id: int, limit: int = 100) -> pd.DataFrame:
        """Get all experience records for a company"""
        try:
            conn = self.get_connection()
            df = pd.read_sql_query("""
                SELECT * FROM experience_record 
                WHERE company_id = ?
                ORDER BY completion_date DESC
                LIMIT ?
            """, conn, params=[company_id, limit])
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error getting experiences: {e}")
            return pd.DataFrame()
    
    def get_experience_by_id(self, experience_id: int) -> Optional[Dict]:
        """Get experience by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM experience_record WHERE id = ?", (experience_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting experience by ID: {e}")
            return None
    
    # =========================================================
    # FINANCIAL METHODS
    # =========================================================
    
    def get_financial_records(self, company_id: int, limit: int = 10) -> pd.DataFrame:
        """Get financial records for a company"""
        try:
            conn = self.get_connection()
            df = pd.read_sql_query("""
                SELECT * FROM financial_capacity 
                WHERE company_id = ?
                ORDER BY fiscal_year DESC
                LIMIT ?
            """, conn, params=[company_id, limit])
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error getting financial records: {e}")
            return pd.DataFrame()
    
    # =========================================================
    # DOCUMENT METHODS
    # =========================================================
    
    def get_documents(self, company_id: int, doc_type: str = None, 
                     show_expired: bool = False, limit: int = 50) -> List[Dict]:
        """Get documents for a company"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM document_registry 
                WHERE company_id = ? AND is_latest_version = 1
            """
            params = [company_id]
            
            if doc_type:
                query += " AND document_type = ?"
                params.append(doc_type)
            
            if not show_expired:
                query += " AND (expiry_date IS NULL OR expiry_date >= date('now'))"
            
            query += " ORDER BY uploaded_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            documents = [dict(zip(columns, row)) for row in rows]
            
            conn.close()
            return documents
        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            return []
    
    # =========================================================
    # KEYWORD SEARCH METHOD
    # =========================================================
    
    def keyword_search(self, company_id: int, query: str, 
                      entity_types: List[str] = None, limit: int = 20) -> List[Dict]:
        """Keyword search across knowledge base"""
        results = []
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            search_term = f"%{query}%"
            
            # Search personnel
            if not entity_types or 'personnel' in entity_types:
                cursor.execute("""
                    SELECT 'personnel' as entity_type, id, full_name as name,
                           designation, personal_phone, personal_email
                    FROM personnel
                    WHERE company_id = ? AND employment_status = 'active'
                    AND (full_name LIKE ? OR designation LIKE ? OR skills LIKE ?)
                    LIMIT ?
                """, (company_id, search_term, search_term, search_term, limit))
                
                for row in cursor.fetchall():
                    results.append({
                        'entity_type': row[0],
                        'entity_id': row[1],
                        'content': f"{row[2]} - {row[3]}",
                        'relevance': 0.8
                    })
            
            # Search equipment
            if not entity_types or 'equipment' in entity_types:
                cursor.execute("""
                    SELECT 'equipment' as entity_type, id, equipment_name as name,
                           equipment_type, model, current_status
                    FROM equipment
                    WHERE company_id = ?
                    AND (equipment_name LIKE ? OR model LIKE ? OR serial_number LIKE ?)
                    LIMIT ?
                """, (company_id, search_term, search_term, search_term, limit))
                
                for row in cursor.fetchall():
                    results.append({
                        'entity_type': row[0],
                        'entity_id': row[1],
                        'content': f"{row[2]} - {row[3]}",
                        'relevance': 0.8
                    })
            
            # Search experiences
            if not entity_types or 'experience' in entity_types:
                cursor.execute("""
                    SELECT 'experience' as entity_type, id, project_name as name,
                           client_name, nature_of_work
                    FROM experience_record
                    WHERE company_id = ?
                    AND (project_name LIKE ? OR client_name LIKE ? OR nature_of_work LIKE ?)
                    ORDER BY completion_date DESC
                    LIMIT ?
                """, (company_id, search_term, search_term, search_term, limit))
                
                for row in cursor.fetchall():
                    results.append({
                        'entity_type': row[0],
                        'entity_id': row[1],
                        'content': f"{row[2]} - {row[3]}",
                        'relevance': 0.8
                    })
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
        finally:
            conn.close()

# Initialize global instance
enhanced_db = EnhancedDatabaseManager()