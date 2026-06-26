# database/enhanced_schema.py
"""
Enhanced Database Schema for Centralized Company Knowledge Repository
"""

SCHEMA_VERSION = 3

CREATE_TABLES = {
    # =========================================================
    # 1. CORE COMPANY TABLES (ENHANCED)
    # =========================================================
    
    "company_profile": """
        CREATE TABLE IF NOT EXISTS company_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            -- Basic Information
            legal_name TEXT NOT NULL,
            trade_name TEXT,
            registration_number TEXT UNIQUE,
            date_of_incorporation DATE,
            business_nature TEXT,
            business_category TEXT,
            
            -- Contact Information
            registered_address TEXT,
            corporate_address TEXT,
            phone_primary TEXT,
            phone_secondary TEXT,
            email_primary TEXT,
            email_secondary TEXT,
            website TEXT,
            fax TEXT,
            
            -- Location
            division TEXT,
            district TEXT,
            upazila TEXT,
            post_code TEXT,
            
            -- Status
            status TEXT DEFAULT 'active',
            is_verified BOOLEAN DEFAULT 0,
            verified_at TIMESTAMP,
            verified_by INTEGER,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            updated_by INTEGER,
            
            UNIQUE(company_id)
        )
    """,
    
    "trade_license": """
        CREATE TABLE IF NOT EXISTS trade_license (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            license_number TEXT NOT NULL,
            issuing_authority TEXT,
            issue_date DATE,
            expiry_date DATE,
            license_type TEXT,
            business_type TEXT,
            
            -- Document
            document_path TEXT,
            document_hash TEXT,
            
            -- Status
            is_valid BOOLEAN DEFAULT 1,
            verification_status TEXT DEFAULT 'pending',
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            
            UNIQUE(company_id, license_number)
        )
    """,
    
    "tin_certificate": """
        CREATE TABLE IF NOT EXISTS tin_certificate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            tin_number TEXT NOT NULL UNIQUE,
            bin_number TEXT,
            vat_registration_number TEXT,
            rjsc_number TEXT,
            
            -- Certificate Details
            certificate_path TEXT,
            issue_date DATE,
            expiry_date DATE,
            tax_circle TEXT,
            tax_zone TEXT,
            
            -- Status
            is_valid BOOLEAN DEFAULT 1,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(company_id, tin_number)
        )
    """,
    
    "vat_registration": """
        CREATE TABLE IF NOT EXISTS vat_registration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            vat_number TEXT NOT NULL,
            vat_registration_number TEXT,
            musak_number TEXT,
            
            -- Registration Details
            registration_date DATE,
            effective_date DATE,
            vat_circle TEXT,
            vat_zone TEXT,
            
            -- Document
            certificate_path TEXT,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(company_id, vat_number)
        )
    """,
    
    # =========================================================
    # 2. FINANCIAL TABLES
    # =========================================================
    
    "financial_capacity": """
        CREATE TABLE IF NOT EXISTS financial_capacity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            -- Financial Year
            fiscal_year TEXT NOT NULL,
            
            -- Turnover
            annual_turnover REAL,
            construction_turnover REAL,
            export_turnover REAL,
            
            -- Assets & Liabilities
            total_assets REAL,
            current_assets REAL,
            fixed_assets REAL,
            total_liabilities REAL,
            current_liabilities REAL,
            net_worth REAL,
            
            -- Liquidity
            liquid_assets REAL,
            cash_and_bank REAL,
            working_capital REAL,
            
            -- Ratios
            current_ratio REAL,
            quick_ratio REAL,
            debt_to_equity_ratio REAL,
            profit_margin REAL,
            
            -- Credit Facilities
            credit_limit REAL,
            bank_guarantee_limit REAL,
            overdraft_limit REAL,
            letter_of_credit_limit REAL,
            
            -- Audit Information
            audited_by TEXT,
            audit_firm TEXT,
            audit_report_path TEXT,
            audit_date DATE,
            
            -- Status
            is_audited BOOLEAN DEFAULT 0,
            verification_status TEXT DEFAULT 'pending',
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(company_id, fiscal_year)
        )
    """,
    
    "bank_account": """
        CREATE TABLE IF NOT EXISTS bank_account (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            bank_name TEXT NOT NULL,
            branch_name TEXT,
            account_name TEXT NOT NULL,
            account_number TEXT NOT NULL,
            account_type TEXT, -- Current, Savings, etc.
            routing_number TEXT,
            swift_code TEXT,
            iban TEXT,
            
            -- Currency
            currency TEXT DEFAULT 'BDT',
            
            -- Signatories
            authorized_signatories TEXT, -- JSON array
            
            -- Document
            confirmation_letter_path TEXT,
            
            -- Status
            is_primary BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(company_id, account_number)
        )
    """,
    
    # =========================================================
    # 3. EXPERIENCE & PROJECT TABLES
    # =========================================================
    
    "experience_record": """
        CREATE TABLE IF NOT EXISTS experience_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            -- Project Information
            project_name TEXT NOT NULL,
            project_location TEXT,
            client_name TEXT NOT NULL,
            client_type TEXT, -- Government, Private, NGO, etc.
            procuring_entity TEXT,
            
            -- Contract Details
            contract_number TEXT,
            contract_date DATE,
            completion_date DATE,
            contract_value REAL,
            currency TEXT DEFAULT 'BDT',
            
            -- Scope
            nature_of_work TEXT,
            scope_of_work TEXT,
            key_deliverables TEXT,
            
            -- Performance
            is_completed BOOLEAN DEFAULT 0,
            is_running BOOLEAN DEFAULT 0,
            completion_percentage REAL DEFAULT 0,
            delay_days INTEGER DEFAULT 0,
            liquidated_damages REAL DEFAULT 0,
            
            -- Quality & Safety
            quality_rating REAL, -- 1-5
            safety_rating REAL, -- 1-5
            client_satisfaction TEXT,
            defects_liability_period TEXT,
            
            -- Key Personnel
            project_manager TEXT,
            site_engineer TEXT,
            qa_qc_officer TEXT,
            safety_officer TEXT,
            
            -- Documentation
            contract_document_path TEXT,
            completion_certificate_path TEXT,
            performance_certificate_path TEXT,
            
            -- Verification
            verification_status TEXT DEFAULT 'pending',
            verified_by INTEGER,
            verified_at TIMESTAMP,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            
            UNIQUE(company_id, contract_number)
        )
    """,
    
    "project_image": """
        CREATE TABLE IF NOT EXISTS project_image (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experience_id INTEGER NOT NULL REFERENCES experience_record(id) ON DELETE CASCADE,
            
            image_path TEXT NOT NULL,
            image_type TEXT, -- before, during, after, aerial, etc.
            caption TEXT,
            description TEXT,
            geo_location TEXT,
            capture_date DATE,
            
            -- EXIF Data (JSON)
            exif_data TEXT,
            
            -- Ordering
            display_order INTEGER DEFAULT 0,
            
            -- Metadata
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER
        )
    """,
    
    "completion_certificate": """
        CREATE TABLE IF NOT EXISTS completion_certificate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experience_id INTEGER NOT NULL REFERENCES experience_record(id) ON DELETE CASCADE,
            
            certificate_number TEXT NOT NULL,
            issuing_authority TEXT NOT NULL,
            issue_date DATE,
            certificate_type TEXT, -- completion, performance, substantial
            certificate_path TEXT,
            certificate_hash TEXT,
            
            -- Ratings
            quality_rating TEXT,
            timeliness_rating TEXT,
            safety_rating TEXT,
            overall_rating TEXT,
            
            -- Remarks
            remarks TEXT,
            recommendations TEXT,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(experience_id, certificate_number)
        )
    """,
    
    # =========================================================
    # 4. PERSONNEL & ORGANIZATION TABLES
    # =========================================================
    
    "personnel": """
        CREATE TABLE IF NOT EXISTS personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            -- Personal Information
            full_name TEXT NOT NULL,
            father_name TEXT,
            mother_name TEXT,
            spouse_name TEXT,
            date_of_birth DATE,
            nationality TEXT DEFAULT 'Bangladeshi',
            nid_number TEXT,
            passport_number TEXT,
            birth_certificate_number TEXT,
            
            -- Contact
            personal_phone TEXT,
            personal_email TEXT,
            present_address TEXT,
            permanent_address TEXT,
            
            -- Professional
            designation TEXT NOT NULL,
            department TEXT,
            employee_id TEXT,
            joining_date DATE,
            confirmation_date DATE,
            
            -- Qualifications
            educational_qualification TEXT,
            professional_certifications TEXT,
            skills TEXT,
            languages TEXT,
            
            -- Documents
            cv_path TEXT,
            photo_path TEXT,
            nid_copy_path TEXT,
            passport_copy_path TEXT,
            academic_certificates TEXT, -- JSON array of paths
            training_certificates TEXT, -- JSON array of paths
            
            -- Status
            employment_status TEXT DEFAULT 'active', -- active, resigned, terminated, retired
            is_key_personnel BOOLEAN DEFAULT 0,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            
            UNIQUE(company_id, employee_id),
            UNIQUE(company_id, nid_number)
        )
    """,
    
    "personnel_experience": """
        CREATE TABLE IF NOT EXISTS personnel_experience (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel_id INTEGER NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
            
            organization_name TEXT NOT NULL,
            designation TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE,
            is_current BOOLEAN DEFAULT 0,
            
            responsibilities TEXT,
            achievements TEXT,
            
            verification_status TEXT DEFAULT 'pending',
            verification_document_path TEXT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    # =========================================================
    # 5. EQUIPMENT & RESOURCES TABLES
    # =========================================================
    
    "equipment": """
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            -- Basic Information
            equipment_name TEXT NOT NULL,
            equipment_type TEXT,
            model TEXT,
            manufacturer TEXT,
            serial_number TEXT UNIQUE,
            
            -- Specifications
            capacity REAL,
            power_rating REAL,
            fuel_type TEXT,
            year_of_manufacture INTEGER,
            country_of_origin TEXT,
            
            -- Ownership
            ownership_type TEXT, -- owned, leased, rented
            owner_name TEXT,
            registration_number TEXT,
            chassis_number TEXT,
            engine_number TEXT,
            
            -- Acquisition
            purchase_date DATE,
            purchase_cost REAL,
            currency TEXT DEFAULT 'BDT',
            supplier_name TEXT,
            invoice_number TEXT,
            
            -- Operational Status
            current_status TEXT DEFAULT 'available', -- available, deployed, maintenance, repair, idle
            location TEXT,
            operator_name TEXT,
            operating_hours INTEGER DEFAULT 0,
            last_maintenance_date DATE,
            next_maintenance_date DATE,
            
            -- Documents
            registration_certificate_path TEXT,
            insurance_document_path TEXT,
            tax_token_path TEXT,
            fitness_certificate_path TEXT,
            route_permit_path TEXT,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER
        )
    """,
    
    "equipment_maintenance": """
        CREATE TABLE IF NOT EXISTS equipment_maintenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
            
            maintenance_date DATE NOT NULL,
            maintenance_type TEXT,
            description TEXT,
            cost REAL,
            performed_by TEXT,
            next_maintenance_date DATE,
            
            document_path TEXT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    # =========================================================
    # 6. DOCUMENT MANAGEMENT & VERSIONING
    # =========================================================
    
    "document_registry": """
        CREATE TABLE IF NOT EXISTS document_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            -- Document Identification
            document_uuid TEXT UNIQUE NOT NULL,
            document_name TEXT NOT NULL,
            document_type TEXT NOT NULL, -- trade_license, tin, vat, certificate, etc.
            reference_id INTEGER, -- ID in related table
            reference_table TEXT, -- Name of related table
            
            -- Version Control
            version_number INTEGER DEFAULT 1,
            is_latest_version BOOLEAN DEFAULT 1,
            previous_version_id INTEGER,
            
            -- File Information
            file_path TEXT NOT NULL,
            file_name TEXT,
            file_size INTEGER,
            file_hash TEXT, -- SHA-256 for integrity
            mime_type TEXT,
            
            -- Content for Search
            extracted_text TEXT, -- OCR/PDF extracted text
            content_hash TEXT, -- For similarity search
            
            -- Metadata
            description TEXT,
            tags TEXT, -- JSON array of tags
            category TEXT,
            language TEXT DEFAULT 'en',
            
            -- Dates
            document_date DATE, -- Original document date
            expiry_date DATE,
            effective_date DATE,
            
            -- Status
            verification_status TEXT DEFAULT 'pending',
            is_public BOOLEAN DEFAULT 0,
            
            -- Audit
            uploaded_by INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (previous_version_id) REFERENCES document_registry(id)
        )
    """,
    
    "document_tag": """
        CREATE TABLE IF NOT EXISTS document_tag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag_name TEXT UNIQUE NOT NULL,
            tag_category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    "document_tag_map": """
        CREATE TABLE IF NOT EXISTS document_tag_map (
            document_id INTEGER REFERENCES document_registry(id) ON DELETE CASCADE,
            tag_id INTEGER REFERENCES document_tag(id) ON DELETE CASCADE,
            PRIMARY KEY (document_id, tag_id)
        )
    """,
    
    # =========================================================
    # 7. AI & SEARCH TABLES
    # =========================================================
    
    "vector_embeddings": """
        CREATE TABLE IF NOT EXISTS vector_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            -- Reference
            entity_type TEXT NOT NULL, -- document, personnel, experience, tender
            entity_id INTEGER NOT NULL,
            field_name TEXT, -- Which field this embedding represents
            
            -- Embedding Data
            embedding_model TEXT NOT NULL,
            embedding_dimension INTEGER,
            embedding_vector BLOB NOT NULL, -- Stored as pickle/bytes
            
            -- Content
            original_text TEXT,
            content_hash TEXT,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(company_id, entity_type, entity_id, field_name, embedding_model)
        )
    """,
    
    "fts_documents": """
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_documents USING fts5(
            company_id UNINDEXED,
            document_uuid UNINDEXED,
            entity_type,
            entity_id UNINDEXED,
            field_name,
            content,
            metadata,
            tokenize='porter unicode61'
        )
    """,
    
    "semantic_search_log": """
        CREATE TABLE IF NOT EXISTS semantic_search_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            
            query_text TEXT NOT NULL,
            query_embedding BLOB,
            result_count INTEGER,
            search_type TEXT, -- semantic, hybrid, keyword
            
            response_time_ms INTEGER,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    
    # =========================================================
    # 8. TENDER RESPONSE TEMPLATES
    # =========================================================
    
    "tender_response_template": """
        CREATE TABLE IF NOT EXISTS tender_response_template (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            template_name TEXT NOT NULL,
            template_type TEXT, -- technical, financial, qualification
            description TEXT,
            
            -- Structure
            sections TEXT, -- JSON array of sections
            field_mappings TEXT, -- JSON mapping to company data
            
            -- Version
            version INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT 1,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            
            UNIQUE(company_id, template_name)
        )
    """,
    
    "past_tender_response": """
        CREATE TABLE IF NOT EXISTS past_tender_response (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            tender_id TEXT,
            
            response_type TEXT, -- technical, financial, qualification
            response_data TEXT, -- JSON of submitted response
            response_file_path TEXT,
            
            -- Outcome
            was_successful BOOLEAN DEFAULT 0,
            award_amount REAL,
            feedback TEXT,
            
            -- Learning
            lessons_learned TEXT,
            improvement_points TEXT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted_by INTEGER
        )
    """,
    
    # =========================================================
    # 9. CERTIFICATES & QUALIFICATIONS
    # =========================================================
    
    "certificate": """
        CREATE TABLE IF NOT EXISTS certificate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            certificate_name TEXT NOT NULL,
            certificate_number TEXT,
            issuing_body TEXT NOT NULL,
            issue_date DATE,
            expiry_date DATE,
            
            certificate_type TEXT, -- ISO, quality, safety, environmental, etc.
            grade TEXT,
            scope TEXT,
            
            document_path TEXT,
            verification_status TEXT DEFAULT 'pending',
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(company_id, certificate_number)
        )
    """,
    
    "work_program": """
        CREATE TABLE IF NOT EXISTS work_program (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            program_name TEXT NOT NULL,
            program_type TEXT, -- construction, maintenance, design, etc.
            description TEXT,
            
            methodology TEXT,
            quality_control_plan TEXT,
            safety_plan TEXT,
            environmental_plan TEXT,
            
            resource_requirements TEXT, -- JSON
            timeline TEXT, -- JSON
            milestones TEXT, -- JSON
            
            document_path TEXT,
            is_standard BOOLEAN DEFAULT 0,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(company_id, program_name)
        )
    """,
    
    "extension_auto_fill_log": """
        CREATE TABLE IF NOT EXISTS extension_auto_fill_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            field_label TEXT,
            confidence_score REAL,
            page_url TEXT,
            filled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,

    "methodology": """
        CREATE TABLE IF NOT EXISTS methodology (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            
            methodology_name TEXT NOT NULL,
            methodology_type TEXT, -- construction, piling, finishing, etc.
            description TEXT,
            
            steps TEXT, -- JSON array of steps
            equipment_needed TEXT, -- JSON
            personnel_needed TEXT, -- JSON
            safety_measures TEXT,
            quality_checks TEXT,
            
            document_path TEXT,
            is_standard BOOLEAN DEFAULT 0,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(company_id, methodology_name)
        )
    """
}

# =========================================================
# INDEXES
# =========================================================

CREATE_INDEXES = """
    -- Company indexes
    CREATE INDEX IF NOT EXISTS idx_company_profile_company ON company_profile(company_id);
    CREATE INDEX IF NOT EXISTS idx_company_profile_status ON company_profile(status);
    
    -- Document indexes
    CREATE INDEX IF NOT EXISTS idx_document_registry_company ON document_registry(company_id);
    CREATE INDEX IF NOT EXISTS idx_document_registry_type ON document_registry(document_type);
    CREATE INDEX IF NOT EXISTS idx_document_registry_date ON document_registry(document_date);
    CREATE INDEX IF NOT EXISTS idx_document_registry_expiry ON document_registry(expiry_date);
    CREATE INDEX IF NOT EXISTS idx_document_registry_version ON document_registry(reference_id, reference_table, version_number);
    
    -- Experience indexes
    CREATE INDEX IF NOT EXISTS idx_experience_company ON experience_record(company_id);
    CREATE INDEX IF NOT EXISTS idx_experience_client ON experience_record(client_name);
    CREATE INDEX IF NOT EXISTS idx_experience_completion ON experience_record(completion_date);
    CREATE INDEX IF NOT EXISTS idx_experience_value ON experience_record(contract_value);
    
    -- Personnel indexes
    CREATE INDEX IF NOT EXISTS idx_personnel_company ON personnel(company_id);
    CREATE INDEX IF NOT EXISTS idx_personnel_designation ON personnel(designation);
    CREATE INDEX IF NOT EXISTS idx_personnel_status ON personnel(employment_status);
    
    -- Equipment indexes
    CREATE INDEX IF NOT EXISTS idx_equipment_company ON equipment(company_id);
    CREATE INDEX IF NOT EXISTS idx_equipment_type ON equipment(equipment_type);
    CREATE INDEX IF NOT EXISTS idx_equipment_status ON equipment(current_status);
    
    -- Financial indexes
    CREATE INDEX IF NOT EXISTS idx_financial_company ON financial_capacity(company_id);
    CREATE INDEX IF NOT EXISTS idx_financial_year ON financial_capacity(fiscal_year);
    
    -- Vector search indexes
    CREATE INDEX IF NOT EXISTS idx_vector_entity ON vector_embeddings(entity_type, entity_id);
    CREATE INDEX IF NOT EXISTS idx_vector_company_model ON vector_embeddings(company_id, embedding_model);
    
    -- Certificate indexes
    CREATE INDEX IF NOT EXISTS idx_certificate_company ON certificate(company_id);
    CREATE INDEX IF NOT EXISTS idx_certificate_expiry ON certificate(expiry_date);
    CREATE INDEX IF NOT EXISTS idx_certificate_issuer ON certificate(issuing_body);
"""

# =========================================================
# TRIGGERS
# =========================================================

CREATE_TRIGGERS = """
    -- Update timestamp on company_profile
    CREATE TRIGGER IF NOT EXISTS update_company_profile_timestamp 
    AFTER UPDATE ON company_profile
    BEGIN
        UPDATE company_profile SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;
    
    -- Update timestamp on experience_record
    CREATE TRIGGER IF NOT EXISTS update_experience_timestamp
    AFTER UPDATE ON experience_record
    BEGIN
        UPDATE experience_record SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;
    
    -- Document versioning trigger
    CREATE TRIGGER IF NOT EXISTS document_versioning
    BEFORE UPDATE ON document_registry
    WHEN NEW.is_latest_version = 1 AND OLD.is_latest_version = 1
    BEGIN
        UPDATE document_registry SET is_latest_version = 0 WHERE id = OLD.id;
    END;
"""

# =========================================================
# FULL-TEXT SEARCH CONFIGURATION
# =========================================================

FTS_CONFIG = """
    -- Configure FTS5 for Bengali + English support
    -- Note: Requires custom tokenizer or use simple with Unicode
"""

def get_all_create_statements():
    """Return all CREATE TABLE statements"""
    return list(CREATE_TABLES.values())

def get_schema_version():
    """Return current schema version"""
    return SCHEMA_VERSION