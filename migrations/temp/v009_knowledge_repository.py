version = "v009_knowledge_repository"

# migrations/v009_knowledge_repository.py - NEW FILE

import sqlite3
import os
from datetime import datetime

def upgrade(db_path="data/tender_system.db"):
    """Add knowledge repository tables"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔧 Running migration v009: Knowledge Repository Tables")
    
    # =========================================================
    # 1. ENHANCED COMPANY PROFILE
    # =========================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS company_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL UNIQUE,
            legal_name TEXT,
            trade_name TEXT,
            registration_number TEXT,
            date_of_incorporation DATE,
            business_nature TEXT,
            business_category TEXT,
            registered_address TEXT,
            corporate_address TEXT,
            phone_primary TEXT,
            phone_secondary TEXT,
            email_primary TEXT,
            email_secondary TEXT,
            website TEXT,
            fax TEXT,
            division TEXT,
            district TEXT,
            upazila TEXT,
            post_code TEXT,
            status TEXT DEFAULT 'active',
            is_verified BOOLEAN DEFAULT 0,
            verified_at TIMESTAMP,
            verified_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            updated_by INTEGER,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        )
    """)
    print("  ✅ Created company_profile table")
    
    # =========================================================
    # 2. PERSONNEL TABLE
    # =========================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            father_name TEXT,
            mother_name TEXT,
            spouse_name TEXT,
            date_of_birth DATE,
            nationality TEXT DEFAULT 'Bangladeshi',
            nid_number TEXT,
            passport_number TEXT,
            birth_certificate_number TEXT,
            personal_phone TEXT,
            personal_email TEXT,
            present_address TEXT,
            permanent_address TEXT,
            designation TEXT NOT NULL,
            department TEXT,
            employee_id TEXT,
            joining_date DATE,
            confirmation_date DATE,
            educational_qualification TEXT,
            professional_certifications TEXT,
            skills TEXT,
            languages TEXT,
            cv_path TEXT,
            photo_path TEXT,
            nid_copy_path TEXT,
            passport_copy_path TEXT,
            academic_certificates TEXT,
            training_certificates TEXT,
            employment_status TEXT DEFAULT 'active',
            is_key_personnel BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            UNIQUE(company_id, employee_id),
            UNIQUE(company_id, nid_number)
        )
    """)
    print("  ✅ Created personnel table")
    
    # =========================================================
    # 3. EQUIPMENT TABLE
    # =========================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            equipment_name TEXT NOT NULL,
            equipment_type TEXT,
            model TEXT,
            manufacturer TEXT,
            serial_number TEXT UNIQUE,
            capacity REAL,
            power_rating REAL,
            fuel_type TEXT,
            year_of_manufacture INTEGER,
            country_of_origin TEXT,
            ownership_type TEXT,
            owner_name TEXT,
            registration_number TEXT,
            chassis_number TEXT,
            engine_number TEXT,
            purchase_date DATE,
            purchase_cost REAL,
            currency TEXT DEFAULT 'BDT',
            supplier_name TEXT,
            invoice_number TEXT,
            current_status TEXT DEFAULT 'available',
            location TEXT,
            operator_name TEXT,
            operating_hours INTEGER DEFAULT 0,
            last_maintenance_date DATE,
            next_maintenance_date DATE,
            registration_certificate_path TEXT,
            insurance_document_path TEXT,
            tax_token_path TEXT,
            fitness_certificate_path TEXT,
            route_permit_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        )
    """)
    print("  ✅ Created equipment table")
    
    # =========================================================
    # 4. EXPERIENCE RECORD TABLE
    # =========================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experience_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            project_name TEXT NOT NULL,
            project_location TEXT,
            client_name TEXT NOT NULL,
            client_type TEXT,
            procuring_entity TEXT,
            contract_number TEXT,
            contract_date DATE,
            completion_date DATE,
            contract_value REAL,
            currency TEXT DEFAULT 'BDT',
            nature_of_work TEXT,
            scope_of_work TEXT,
            key_deliverables TEXT,
            is_completed BOOLEAN DEFAULT 0,
            is_running BOOLEAN DEFAULT 0,
            completion_percentage REAL DEFAULT 0,
            delay_days INTEGER DEFAULT 0,
            liquidated_damages REAL DEFAULT 0,
            quality_rating REAL,
            safety_rating REAL,
            client_satisfaction TEXT,
            defects_liability_period TEXT,
            project_manager TEXT,
            site_engineer TEXT,
            qa_qc_officer TEXT,
            safety_officer TEXT,
            contract_document_path TEXT,
            completion_certificate_path TEXT,
            performance_certificate_path TEXT,
            verification_status TEXT DEFAULT 'pending',
            verified_by INTEGER,
            verified_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            UNIQUE(company_id, contract_number)
        )
    """)
    print("  ✅ Created experience_record table")
    
    # =========================================================
    # 5. FINANCIAL CAPACITY TABLE
    # =========================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_capacity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            fiscal_year TEXT NOT NULL,
            annual_turnover REAL,
            construction_turnover REAL,
            export_turnover REAL,
            total_assets REAL,
            current_assets REAL,
            fixed_assets REAL,
            total_liabilities REAL,
            current_liabilities REAL,
            net_worth REAL,
            liquid_assets REAL,
            cash_and_bank REAL,
            working_capital REAL,
            current_ratio REAL,
            quick_ratio REAL,
            debt_to_equity_ratio REAL,
            profit_margin REAL,
            credit_limit REAL,
            bank_guarantee_limit REAL,
            overdraft_limit REAL,
            letter_of_credit_limit REAL,
            audited_by TEXT,
            audit_firm TEXT,
            audit_report_path TEXT,
            audit_date DATE,
            is_audited BOOLEAN DEFAULT 0,
            verification_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            UNIQUE(company_id, fiscal_year)
        )
    """)
    print("  ✅ Created financial_capacity table")
    
    # =========================================================
    # 6. DOCUMENT REGISTRY WITH VERSIONING
    # =========================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            document_uuid TEXT UNIQUE NOT NULL,
            document_name TEXT NOT NULL,
            document_type TEXT NOT NULL,
            reference_id INTEGER,
            reference_table TEXT,
            version_number INTEGER DEFAULT 1,
            is_latest_version BOOLEAN DEFAULT 1,
            previous_version_id INTEGER,
            file_path TEXT NOT NULL,
            file_name TEXT,
            file_size INTEGER,
            file_hash TEXT,
            mime_type TEXT,
            extracted_text TEXT,
            description TEXT,
            tags TEXT,
            category TEXT,
            language TEXT DEFAULT 'en',
            document_date DATE,
            expiry_date DATE,
            effective_date DATE,
            verification_status TEXT DEFAULT 'pending',
            is_public BOOLEAN DEFAULT 0,
            uploaded_by INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (previous_version_id) REFERENCES document_registry(id)
        )
    """)
    print("  ✅ Created document_registry table")
    
    # =========================================================
    # 7. INDEXES FOR PERFORMANCE
    # =========================================================
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_personnel_company ON personnel(company_id)",
        "CREATE INDEX IF NOT EXISTS idx_personnel_designation ON personnel(designation)",
        "CREATE INDEX IF NOT EXISTS idx_equipment_company ON equipment(company_id)",
        "CREATE INDEX IF NOT EXISTS idx_equipment_status ON equipment(current_status)",
        "CREATE INDEX IF NOT EXISTS idx_experience_company ON experience_record(company_id)",
        "CREATE INDEX IF NOT EXISTS idx_financial_company ON financial_capacity(company_id)",
        "CREATE INDEX IF NOT EXISTS idx_document_company ON document_registry(company_id)",
        "CREATE INDEX IF NOT EXISTS idx_document_type ON document_registry(document_type)",
    ]
    
    for index in indexes:
        try:
            cursor.execute(index)
            print(f"  ✅ Created index: {index.split('ON')[1].strip() if 'ON' in index else index}")
        except Exception as e:
            print(f"  ⚠️ Could not create index: {e}")
    
    conn.commit()
    conn.close()
    
    print("✅ Migration v009 completed successfully!")

def downgrade(db_path="data/tender_system.db"):
    """Rollback migration"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = [
        'document_registry',
        'financial_capacity',
        'experience_record',
        'equipment',
        'personnel',
        'company_profile'
    ]
    
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"  ✅ Dropped {table} table")
    
    conn.commit()
    conn.close()
    print("✅ Downgrade completed!")

if __name__ == "__main__":
    upgrade()