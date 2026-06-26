import streamlit as st
import sqlite3
import os
import logging
from database.crud_operations import DatabaseCRUD
from migrations.v012_update_user_profile import MigrationV012
from migrations.v013_tenant_rate_management import MigrationV013
from migrations.v014_demo_data_framework import MigrationV014
from migrations.v015_archive_framework import MigrationV015
from migrations.v016_company_onboarding_wizard import MigrationV016
from migrations.v017_add_step_data_column import MigrationV017
from migrations.v018_add_custom_source_column import MigrationV018  # ✅ ADDED
from migrations.v019_add_version_id_to_boq import MigrationV019  # ✅ ADDED

from migrations.v020_rename_cost_levels import MigrationV020
from migrations.v022_company_config import MigrationV022
from migrations.v023_add_quick_boq import MigrationV023  # ✅ ADD THIS

logger = logging.getLogger(__name__)

class DatabaseSchema:
    """Handles all database schema creation and initialization"""
    
    def __init__(self, db_path="data/tender_system.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    def get_connection(self):
        """Get database connection with row_factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_all_tables(self):
        """Create ALL tables from all migrations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        self._create_all_tables()

        self.run_migrations()
        conn.commit()
        conn.close()
        print("✅ All tables created successfully")
    
    def run_migrations(self):
        """Run all pending migrations"""
        db = DatabaseCRUD(self.db_path)
        
        # ========== Run v012 Migration ==========
        migration_v012 = MigrationV012(db)
        if not db.table_exists('social_links'):
            print("🔄 Running v012 migration...")
            migration_v012.up()
        else:
            print("✅ v012 migration already applied")
        
        # ========== Run v013 Migration ==========
        migration_v013 = MigrationV013(db)
        if not db.table_exists('tenant_rate_books'):
            print("🔄 Running v013 migration...")
            migration_v013.up()
        else:
            print("✅ v013 migration already applied")
        
        # ========== Run v014 Migration ==========
        migration_v014 = MigrationV014(db)
        if not db.table_exists('demo_data_generation_log'):
            print("🔄 Running v014 migration...")
            migration_v014.up()
        else:
            print("✅ v014 migration already applied")
        
        # ========== Run v015 Migration ==========
        migration_v015 = MigrationV015(db)
        if not db.table_exists('archive_records'):
            print("🔄 Running v015 migration...")
            migration_v015.up()
        else:
            print("✅ v015 migration already applied")
        
        # ========== Run v016 Migration ==========
        migration_v016 = MigrationV016(db)
        if not db.table_exists('onboarding_wizard_sessions'):
            print("🔄 Running v016 migration...")
            migration_v016.up()
        else:
            print("✅ v016 migration already applied")

        # ========== Run v017 Migration ==========
        migration_v017 = MigrationV017(db)
        # ✅ Check for the column that v017 adds
        if not db.column_exists('company_onboarding_status', 'step_data'):
            print("🔄 Running v017 migration...")
            migration_v017.up()
        else:
            print("✅ v017 migration already applied")

        # ========== Run v018 Migration ==========
        migration_v018 = MigrationV018(db)
        # ✅ Check for the column that v018 adds
        if not db.column_exists('tenant_rate_books', 'custom_source'):
            print("🔄 Running v018 migration...")
            migration_v018.up()
        else:
            print("✅ v018 migration already applied")
         # ========== Run v019 Migration ==========
        migration_v019 = MigrationV019(db)
        if not db.column_exists('boq_generation_history', 'rate_book_id'):
            print("🔄 Running v019 migration...")
            migration_v019.up()
        else:
            print("✅ v019 migration already applied")
        # ========== Run v020 Migration ==========
        migration_v020 = MigrationV020(db)
        # ✅ FIX: Check for the table that v020 adds
        if not db.table_exists('company_cost_profiles'):
            print("🔄 Running v020 migration...")
            migration_v020.up()
        else:
            print("✅ v020 migration already applied")

        migration_v022 = MigrationV022(db)
        # ✅ FIX: Check for the table that v022 adds
        if not db.table_exists('company_config'):
            print("🔄 Running v022 migration...")
            migration_v022.up()
        else:
            print("✅ v022 migration already applied")
        # ========== Run v023 Migration ==========
        migration_v023 = MigrationV023(db)
        if not db.column_exists('boq_generation_history', 'is_quick_boq'):
            print("🔄 Running v023 migration...")
            migration_v023.up()
        else:
            print("✅ v023 migration already applied")

     
    def insert_default_data(self):
        """Insert default data if tables are empty"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        
    def _create_all_tables(self):
        """Create ALL tables from all migrations"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # =========================================================
        # v001_initial_schema.py - CORE TABLES
        # =========================================================
        
        # Companies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT UNIQUE NOT NULL,
                mobile_number TEXT UNIQUE NOT NULL,  -- UNIQUE - primary identifier
                mobile_verified BOOLEAN DEFAULT 0,
                mobile_verified_at TIMESTAMP,                      
                registration_number TEXT,
                vat_number TEXT,
                tin_number TEXT,
                bin_number TEXT,
                rjsc_number TEXT,
                address TEXT,
                district TEXT,
                division TEXT,
                upazila TEXT,
                post_code TEXT,
                phone TEXT,
                email TEXT,
                website TEXT,
                is_individual BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                phone TEXT,
                mobile_number TEXT UNIQUE NOT NULL,  -- UNIQUE - primary identifier
                mobile_verified BOOLEAN DEFAULT 0,
                mobile_verified_at TIMESTAMP,                       
                role TEXT DEFAULT 'user',
                is_active BOOLEAN DEFAULT 1,
                is_approved BOOLEAN DEFAULT 0,
                account_type TEXT DEFAULT 'company',
                auth_provider TEXT DEFAULT 'email',
                email_verified BOOLEAN DEFAULT 0,
                email_verified_at TIMESTAMP,
                verification_token TEXT,
                reset_token TEXT,
                reset_token_expires TIMESTAMP,
                specialization TEXT,
                years_experience INTEGER,
                is_company_admin BOOLEAN DEFAULT 0,
                company_admin_approved_by INTEGER,
                company_admin_approved_at TIMESTAMP,
                registration_complete BOOLEAN DEFAULT 0,
                approved_by INTEGER,
                approved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        # Companies table - add mobile columns if not exist
        try:
            cursor.execute("ALTER TABLE companies ADD COLUMN mobile_number TEXT UNIQUE")
            cursor.execute("ALTER TABLE companies ADD COLUMN mobile_verified BOOLEAN DEFAULT 0")
            cursor.execute("ALTER TABLE companies ADD COLUMN mobile_verified_at TIMESTAMP")
            cursor.execute("ALTER TABLE companies ADD COLUMN email_verified BOOLEAN DEFAULT 0")
            cursor.execute("ALTER TABLE companies ADD COLUMN email_verified_at TIMESTAMP")
            print("✅ Added mobile columns to companies")
        except sqlite3.OperationalError:
            pass  # Columns already exist
        
        # Users table - add mobile columns if not exist
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN mobile_number TEXT UNIQUE")
            cursor.execute("ALTER TABLE users ADD COLUMN mobile_verified BOOLEAN DEFAULT 0")
            cursor.execute("ALTER TABLE users ADD COLUMN mobile_verified_at TIMESTAMP")
            cursor.execute("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 0")
            cursor.execute("ALTER TABLE users ADD COLUMN email_verified_at TIMESTAMP")
            print("✅ Added mobile columns to users")
        except sqlite3.OperationalError:
            pass  # Columns already exist
        
        # Create unique indexes
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_mobile 
            ON users(mobile_number) WHERE mobile_number IS NOT NULL
        """)
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_mobile 
            ON companies(mobile_number) WHERE mobile_number IS NOT NULL
        """)
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_company_name_mobile 
            ON companies(company_name, mobile_number)
        """)
        
        # =========================================================
        # OTP VERIFICATION TABLES
        # =========================================================
        
        # OTP verification table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otp_verification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                contact_type TEXT NOT NULL,
                contact_value TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                purpose TEXT DEFAULT 'verification',
                expires_at TIMESTAMP NOT NULL,
                attempts INTEGER DEFAULT 0,
                is_used BOOLEAN DEFAULT 0,
                used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Verification history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verification_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                contact_type TEXT NOT NULL,
                contact_value TEXT NOT NULL,
                verification_method TEXT,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_by INTEGER,
                ip_address TEXT,
                user_agent TEXT
            )
        """)
        
        # System configuration table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER,
                FOREIGN KEY (updated_by) REFERENCES users(id)
            )
        """)
        
        # Create indexes for OTP lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_otp_lookup 
            ON otp_verification(contact_type, contact_value, otp_code, is_used)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_otp_expiry 
            ON otp_verification(expires_at)
        """)

        # Subscriptions table (v001 + v002 + v004 columns)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                company_id INTEGER,
                plan TEXT DEFAULT 'free',
                status TEXT DEFAULT 'active',
                start_date DATE,
                end_date DATE,
                analyses_used INTEGER DEFAULT 0,
                analyses_limit INTEGER DEFAULT 5,
                payment_method TEXT,
                transaction_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                max_boq_generations INTEGER DEFAULT 5,
                max_bid_optimizations INTEGER DEFAULT 5,
                boq_used INTEGER DEFAULT 0,
                bid_optimizations_used INTEGER DEFAULT 0,
                can_edit_rates BOOLEAN DEFAULT 0,
                can_delete_rates BOOLEAN DEFAULT 0,
                can_create_versions BOOLEAN DEFAULT 0,
                can_export_data BOOLEAN DEFAULT 0,
                can_manage_team BOOLEAN DEFAULT 0,
                last_reset_date DATE,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Subscription Plans table (v004)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscription_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_name TEXT UNIQUE NOT NULL,
                plan_type TEXT DEFAULT 'company',
                monthly_price REAL DEFAULT 0,
                yearly_price REAL DEFAULT 0,
                max_boq_generations INTEGER DEFAULT 5,
                max_bid_optimizations INTEGER DEFAULT 5,
                max_tender_analyses INTEGER DEFAULT 5,
                max_users INTEGER DEFAULT 1,
                extension_auto_fills INTEGER DEFAULT 5,
                can_export_data BOOLEAN DEFAULT 0,
                can_edit_rates BOOLEAN DEFAULT 0,
                can_delete_rates BOOLEAN DEFAULT 0,
                can_create_versions BOOLEAN DEFAULT 0,
                can_manage_team BOOLEAN DEFAULT 0,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Consultant clients mapping table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consultant_clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultant_user_id INTEGER REFERENCES users(id),
                client_company_id INTEGER REFERENCES companies(id),
                role TEXT DEFAULT 'manager',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(consultant_user_id, client_company_id)
            )
        """)
        
        # Tender analyses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tender_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                company_id INTEGER,
                tender_id TEXT,
                tender_title TEXT,
                procuring_entity TEXT,
                division TEXT,
                district TEXT,
                thana TEXT,
                construction_type TEXT,
                official_estimate REAL,
                recommended_bid REAL,
                actual_bid REAL,
                success_probability REAL,
                risk_level TEXT,
                competitor_count INTEGER,
                bid_status TEXT,
                analysis_type TEXT,
                competitor_bids TEXT,
                risk_strategy TEXT,
                confidence_score REAL,
                expected_profit REAL,
                expected_value REAL,
                slt_threshold REAL,
                nppi_factor REAL,
                weighted_average REAL,
                final_submitted_bid REAL,
                is_final_submitted BOOLEAN DEFAULT 0,
                actual_winning_bid REAL,
                actual_winner TEXT,
                our_rank_actual INTEGER,
                total_bidders_actual INTEGER,
                bid_accuracy_score REAL,
                lessons_learned TEXT,
                post_evaluation_date TIMESTAMP,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Contact messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                subject TEXT,
                message TEXT,
                status TEXT DEFAULT 'unread',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Historical tenders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historical_tenders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                company_id INTEGER,
                tender_id TEXT,
                tender_title TEXT,
                procuring_entity TEXT,
                procurement_type TEXT,
                official_estimate REAL,
                awarded_price REAL,
                our_awarded_price REAL,
                num_competitors INTEGER,
                total_bidders INTEGER,
                our_rank INTEGER,
                award_date DATE,
                competitors_data TEXT,
                winning_competitor TEXT,
                winning_company_type TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Activity logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                actor_user_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id),
                FOREIGN KEY (actor_user_id) REFERENCES users(id)
            )
        """)
        
        # Company NPPI table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_nppi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                procurement_type TEXT,
                nppi_factor REAL,
                data_points INTEGER,
                calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Competitor master table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitor_master (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                competitor_name TEXT,
                business_type TEXT,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                notes TEXT,
                first_seen DATE,
                last_seen DATE,
                total_bids INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                avg_bid_ratio REAL DEFAULT 0.90,
                preferred_strategy TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id),
                UNIQUE(company_id, competitor_name)
            )
        """)
        
        # Role permissions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT UNIQUE NOT NULL,
                permissions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Company tenders table (full e-GP fields)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_tenders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                tender_id TEXT,
                tender_title TEXT,
                procuring_entity TEXT,
                division TEXT,
                district TEXT,
                thana TEXT,
                country TEXT DEFAULT 'Bangladesh',
                procurement_type TEXT,
                official_estimate REAL,
                submission_deadline TIMESTAMP,
                tender_security REAL,
                document_fee REAL,
                evaluation_type TEXT,
                mode_of_payment TEXT,
                eligibility_criteria TEXT,
                invitation_ref_no TEXT,
                package_no TEXT,
                project_code TEXT,
                project_name TEXT,
                inviting_official_name TEXT,
                inviting_official_designation TEXT,
                inviting_official_phone TEXT,
                inviting_official_email TEXT,
                inviting_official_address TEXT,
                inviting_official_city TEXT,
                inviting_official_thana TEXT,
                inviting_official_district TEXT,
                our_bid_amount REAL,
                bid_submitted_by INTEGER,
                bid_submission_date TIMESTAMP,
                bid_status TEXT DEFAULT 'draft',
                evaluation_status TEXT DEFAULT 'pending',
                winning_bid_amount REAL,
                winning_competitor TEXT,
                our_rank INTEGER,
                total_bidders INTEGER,
                award_date DATE,
                notes TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                is_locked BOOLEAN DEFAULT 0,
                locked_at TIMESTAMP,
                locked_by INTEGER,
                is_copy BOOLEAN DEFAULT 0,
                original_tender_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                deleted_at TIMESTAMP,
                deleted_by INTEGER,
                app_id TEXT,
                procuring_entity_code TEXT,
                procurement_nature TEXT,
                event_type TEXT,
                budget_type TEXT,
                source_of_funds TEXT,
                category TEXT,
                tender_publication_date TIMESTAMP,
                document_selling_end_date TIMESTAMP,
                pre_bid_meeting_start TIMESTAMP,
                pre_bid_meeting_end TIMESTAMP,
                bid_opening_date TIMESTAMP,
                security_submission_deadline TIMESTAMP,
                security_valid_upto DATE,
                tender_valid_upto DATE
            )
        """)
        
        # Tender team assignments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tender_team_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id INTEGER,
                user_id INTEGER,
                role TEXT,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (tender_id) REFERENCES company_tenders(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Tender milestones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tender_milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id INTEGER,
                milestone_name TEXT,
                due_date DATE,
                completed BOOLEAN DEFAULT 0,
                completed_at TIMESTAMP,
                assigned_to INTEGER,
                notes TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tender_id) REFERENCES company_tenders(id),
                FOREIGN KEY (assigned_to) REFERENCES users(id)
            )
        """)
        
        # Bid revisions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bid_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id INTEGER,
                revision_number INTEGER,
                bid_amount REAL,
                revised_by INTEGER,
                reason TEXT,
                revised_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tender_id) REFERENCES company_tenders(id),
                FOREIGN KEY (revised_by) REFERENCES users(id)
            )
        """)
        
        # Tender lots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tender_lots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id INTEGER,
                lot_no TEXT,
                lot_description TEXT,
                location TEXT,
                security_amount REAL,
                estimated_value REAL,
                start_date DATE,
                completion_date DATE,
                our_bid_amount REAL,
                bid_status TEXT,
                FOREIGN KEY (tender_id) REFERENCES company_tenders(id)
            )
        """)
        
        # Tender notifications
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tender_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id INTEGER,
                notification_type TEXT,
                notification_date TIMESTAMP,
                sent BOOLEAN DEFAULT 0,
                sent_at TIMESTAMP,
                FOREIGN KEY (tender_id) REFERENCES company_tenders(id)
            )
        """)
        
        # Tender documents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tender_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id INTEGER,
                document_name TEXT,
                document_type TEXT,
                file_path TEXT,
                uploaded_by INTEGER,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tender_id) REFERENCES company_tenders(id),
                FOREIGN KEY (uploaded_by) REFERENCES users(id)
            )
        """)
        
        # =========================================================
        # v003_add_rate_chapters_sections.py - RATE MANAGEMENT
        # =========================================================
        
        # Rate versions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                version_name TEXT NOT NULL,
                edition_year INTEGER NOT NULL,
                version_number INTEGER DEFAULT 1,
                effective_from DATE,
                effective_to DATE,
                is_active BOOLEAN DEFAULT 0,
                released_by TEXT,
                release_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                total_parents INTEGER DEFAULT 0,
                total_children INTEGER DEFAULT 0,
                total_rates INTEGER DEFAULT 0,
                created_by TEXT,
                has_sections BOOLEAN DEFAULT FALSE,
                chapter_numbers TEXT,
                section_numbers TEXT,
                updated_at TIMESTAMP,
                created_at TIMESTAMP
            )
        """)
        
        # Rate chapters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source VARCHAR(20) NOT NULL,
                version_id INTEGER NOT NULL,
                chapter_number VARCHAR(20) NOT NULL,
                chapter_name TEXT,
                description TEXT,
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (version_id) REFERENCES rate_versions(id) ON DELETE CASCADE,
                UNIQUE(source, chapter_number, version_id)
            )
        """)
        
        # Rate sections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source VARCHAR(20) NOT NULL,
                version_id INTEGER NOT NULL,
                chapter_id INTEGER NOT NULL,
                section_number VARCHAR(20) NOT NULL,
                section_name TEXT,
                description TEXT,
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (version_id) REFERENCES rate_versions(id) ON DELETE CASCADE,
                FOREIGN KEY (chapter_id) REFERENCES rate_chapters(id) ON DELETE CASCADE,
                UNIQUE(source, chapter_id, section_number, version_id)
            )
        """)
        
        # Rate audit log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                role TEXT,
                action TEXT,
                entity_type TEXT,
                entity_id TEXT,
                old_data TEXT,
                new_data TEXT,
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Rate import history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_import_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                version_id INTEGER,
                version_name TEXT,
                edition_year INTEGER,
                import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                imported_by TEXT,
                total_parents INTEGER,
                total_children INTEGER,
                total_rates INTEGER,
                status TEXT DEFAULT 'active',
                notes TEXT
            )
        """)
        
        # Rate change log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_change_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                version_id INTEGER,
                action TEXT,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            )
        """)
        
        # Rate snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                version_id INTEGER,
                snapshot_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                description TEXT,
                data_json TEXT,
                is_auto BOOLEAN DEFAULT 0
            )
        """)
        
        # =========================================================
        # PWD TABLES (from db_manager.py)
        # =========================================================
        
        # PWD chapters
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_chapters (
                chapter_number TEXT PRIMARY KEY,
                chapter_name TEXT NOT NULL,
                total_items INTEGER DEFAULT 0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # PWD parents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_parents (
                pwd_code TEXT PRIMARY KEY,
                description TEXT,
                chapter_number TEXT,
                version_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (version_id) REFERENCES rate_versions(id)
            )
        """)
        
        # PWD children
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_children (
                pwd_code TEXT PRIMARY KEY,
                parent_code TEXT NOT NULL,
                description TEXT,
                unit TEXT,
                edition_year INTEGER,
                version_id INTEGER,
                chapter_id INTEGER,
                is_parent BOOLEAN DEFAULT FALSE,
                parent_item_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_code) REFERENCES pwd_parents(pwd_code) ON DELETE CASCADE,
                FOREIGN KEY (version_id) REFERENCES rate_versions(id)
            )
        """)
        
        # PWD rates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pwd_code TEXT NOT NULL,
                zone_name TEXT NOT NULL,
                unit_rate REAL NOT NULL,
                edition_year INTEGER NOT NULL,
                version_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(pwd_code, zone_name, edition_year),
                FOREIGN KEY (pwd_code) REFERENCES pwd_children(pwd_code) ON DELETE CASCADE,
                FOREIGN KEY (version_id) REFERENCES rate_versions(id)
            )
        """)
        
        # PWD import history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_import_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id INTEGER,
                version_name TEXT,
                edition_year INTEGER,
                import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                imported_by TEXT,
                total_parents INTEGER,
                total_children INTEGER,
                total_rates INTEGER,
                status TEXT DEFAULT 'active',
                notes TEXT
            )
        """)
        
        # PWD snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_name TEXT,
                version_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                description TEXT,
                data_json TEXT,
                is_auto BOOLEAN DEFAULT 0
            )
        """)
        
        # PWD change log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_change_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_history_id INTEGER,
                table_name TEXT,
                record_id TEXT,
                action TEXT,
                old_data TEXT,
                new_data TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                changed_by TEXT
            )
        """)
        
        # =========================================================
        # LGED TABLES (from db_manager.py)
        # =========================================================
        
        # LGED chapters
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lged_chapters (
                chapter_number TEXT PRIMARY KEY,
                chapter_name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # LGED sections
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lged_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_number TEXT NOT NULL,
                section_number TEXT NOT NULL,
                section_name TEXT NOT NULL,
                description TEXT,
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chapter_number, section_number)
            )
        """)
        
        # LGED parents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lged_parents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                description TEXT,
                chapter_number TEXT,
                section_number TEXT,
                parent_type TEXT DEFAULT 'section_header',
                has_children BOOLEAN DEFAULT 0,
                unit TEXT,
                version_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (version_id) REFERENCES rate_versions(id)
            )
        """)
        
        # LGED children
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lged_children (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                parent_code TEXT NOT NULL,
                description TEXT,
                unit TEXT,
                edition_year INTEGER,
                version_id INTEGER,
                chapter_number TEXT,
                section_number TEXT,
                zone_a REAL,
                zone_b REAL,
                zone_c REAL,
                zone_d REAL,
                is_parent BOOLEAN DEFAULT 0,
                parent_item_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (version_id) REFERENCES rate_versions(id)
            )
        """)
        
        # LGED zone rates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lged_zone_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                child_id INTEGER,
                zone_name TEXT NOT NULL,
                unit_rate REAL NOT NULL,
                version_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES lged_parents(id),
                FOREIGN KEY (child_id) REFERENCES lged_children(id),
                FOREIGN KEY (version_id) REFERENCES rate_versions(id)
            )
        """)
        
        # LGED zone mapping
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lged_zone_mapping (
                zone_code TEXT PRIMARY KEY,
                zone_name TEXT,
                divisions TEXT,
                accessibility_bonus REAL DEFAULT 0.05,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Regional rates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regional_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pwd_code TEXT NOT NULL,
                zone_name TEXT NOT NULL,
                unit_rate REAL NOT NULL,
                edition_year INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # =========================================================
        # v006_boq_tables.py - BOQ MANAGEMENT
        # =========================================================
        
        # Tenders BOQ meta
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenders_boq_meta (
                tender_id TEXT PRIMARY KEY,
                ministry_or_agency TEXT,
                selected_zone TEXT,
                workflow_status TEXT CHECK(workflow_status IN ('Draft', 'Pending Approval', 'Approved')) DEFAULT 'Draft',
                official_budget_cap REAL DEFAULT 0.0,
                created_by TEXT,
                approved_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tender BOQ items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tender_boq_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id TEXT,
                item_no TEXT,
                group_name TEXT,
                item_code TEXT,
                description TEXT,
                unit TEXT,
                quantity REAL,
                unit_rate REAL,
                last_modified_by TEXT,
                FOREIGN KEY(tender_id) REFERENCES tenders_boq_meta(tender_id) ON DELETE CASCADE
            )
        """)
        
        # Price change logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_change_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id TEXT,
                item_code TEXT,
                item_no TEXT,
                old_rate REAL,
                new_rate REAL,
                modified_by TEXT,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tender_id) REFERENCES tenders_boq_meta(tender_id) ON DELETE CASCADE
            )
        """)
        
        # Competitor bids (BOQ)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitor_bids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id TEXT,
                competitor_name TEXT NOT NULL,
                total_bid_amount REAL NOT NULL,
                submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_winner INTEGER DEFAULT 0 CHECK(is_winner IN (0, 1)),
                FOREIGN KEY(tender_id) REFERENCES tenders_boq_meta(tender_id) ON DELETE CASCADE
            )
        """)
        
        # Competitor bid history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitor_bid_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                competitor_name TEXT,
                tender_id TEXT,
                bid_amount REAL,
                official_estimate REAL,
                bid_ratio REAL,
                was_winner BOOLEAN DEFAULT 0,
                bid_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # Competitor profiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitor_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                competitor_name TEXT,
                competitor_type TEXT,
                first_seen DATE,
                last_seen DATE,
                total_appearances INTEGER DEFAULT 0,
                wins_count INTEGER DEFAULT 0,
                avg_bid_ratio REAL,
                bid_std_dev REAL,
                strategy TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # BOQ generation history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS boq_generation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                company_id INTEGER,
                tender_id TEXT,
                tender_title TEXT,
                procuring_entity TEXT,
                file_name TEXT,
                item_count INTEGER,
                total_estimated_cost REAL,
                selected_zone TEXT,
                rate_source TEXT,
                edition_year INTEGER,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'completed',
                notes TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                is_locked BOOLEAN DEFAULT 0,
                locked_at TIMESTAMP,
                locked_by INTEGER,
                FOREIGN KEY (tender_id) REFERENCES tenders_boq_meta(tender_id) ON DELETE SET NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # BOQ items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS boq_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boq_id INTEGER NOT NULL,
                item_code TEXT NOT NULL,
                description TEXT,
                unit TEXT,
                quantity REAL DEFAULT 0,
                unit_rate REAL DEFAULT 0,
                total REAL DEFAULT 0,
                is_custom BOOLEAN DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (boq_id) REFERENCES boq_generation_history(id) ON DELETE CASCADE
            )
        """)
        
        # BOQ approval history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS boq_approval_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boq_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                comment TEXT,
                user_id INTEGER,
                username TEXT,
                user_role TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (boq_id) REFERENCES boq_generation_history(id) ON DELETE CASCADE
            )
        """)
        
        # BOQ activity log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS boq_activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boq_id INTEGER,
                action TEXT,
                details TEXT,
                user_id INTEGER,
                username TEXT,
                user_role TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (boq_id) REFERENCES boq_generation_history(id) ON DELETE CASCADE
            )
        """)
        
        # Bid submissions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bid_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boq_history_id INTEGER,
                tender_id TEXT,
                company_id INTEGER,
                submitted_bid_amount REAL,
                bid_document_path TEXT,
                submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                submitted_by TEXT,
                status TEXT DEFAULT 'draft',
                notes TEXT,
                FOREIGN KEY (boq_history_id) REFERENCES boq_generation_history(id) ON DELETE CASCADE,
                FOREIGN KEY (tender_id) REFERENCES tenders_boq_meta(tender_id) ON DELETE SET NULL,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # =========================================================
        # v007_scenarion_tables.py - SCENARIO GENERATOR
        # =========================================================
        
        # Saved scenarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_uuid TEXT UNIQUE NOT NULL,
                company_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                tender_id INTEGER,
                scenario_name TEXT NOT NULL,
                description TEXT,
                official_estimate REAL NOT NULL,
                procurement_type TEXT NOT NULL,
                min_price_pct REAL DEFAULT 0.88,
                max_price_pct REAL DEFAULT 1.08,
                competitor_counts TEXT NOT NULL,
                bidding_pattern TEXT DEFAULT 'realistic',
                ai_strategy TEXT DEFAULT 'weighted_ensemble',
                random_seed INTEGER DEFAULT 42,
                recommended_bid REAL NOT NULL,
                bid_ratio REAL NOT NULL,
                confidence_score REAL NOT NULL,
                expected_win_probability REAL,
                scenarios_data TEXT NOT NULL,
                competitor_stats TEXT,
                is_favorite BOOLEAN DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                share_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tender_id) REFERENCES company_tenders(id)
            )
        """)
        
        # Scenario comments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scenario_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                comment TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (scenario_id) REFERENCES saved_scenarios(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Scenario shares
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scenario_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id INTEGER NOT NULL,
                shared_by_user_id INTEGER NOT NULL,
                shared_with_company_id INTEGER,
                shared_with_email TEXT,
                permission TEXT DEFAULT 'view',
                share_token TEXT UNIQUE,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (scenario_id) REFERENCES saved_scenarios(id) ON DELETE CASCADE,
                FOREIGN KEY (shared_by_user_id) REFERENCES users(id),
                FOREIGN KEY (shared_with_company_id) REFERENCES companies(id)
            )
        """)
        
        # =========================================================
        # v008_extension_tables.py - EXTENSION TRACKING
        # =========================================================
        
        # Extension auto fill log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extension_auto_fill_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                field_label TEXT,
                confidence_score REAL,
                page_url TEXT,
                filled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # =========================================================
        # v009_knowledge_repository.py - KNOWLEDGE REPOSITORY
        # =========================================================
        
        # Company profile (enhanced)
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
        
        # Personnel (enhanced)
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
        
        # Equipment (enhanced)
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
        
        # Experience record (enhanced)
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
        
        # Financial capacity (enhanced)
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
        
        # Document registry (versioning)
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
                content_hash TEXT,
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
        
        # Document tags
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_tag (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_name TEXT UNIQUE NOT NULL,
                tag_category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Document tag map
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_tag_map (
                document_id INTEGER REFERENCES document_registry(id) ON DELETE CASCADE,
                tag_id INTEGER REFERENCES document_tag(id) ON DELETE CASCADE,
                PRIMARY KEY (document_id, tag_id)
            )
        """)
        
        # Vector embeddings (for semantic search)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vector_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                field_name TEXT,
                embedding_model TEXT NOT NULL,
                embedding_dimension INTEGER,
                embedding_vector BLOB NOT NULL,
                original_text TEXT,
                content_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, entity_type, entity_id, field_name, embedding_model),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        
        # FTS documents (full-text search)
        cursor.execute("""
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
        """)
        
        # Semantic search log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_search_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                query_text TEXT NOT NULL,
                query_embedding BLOB,
                result_count INTEGER,
                search_type TEXT,
                response_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Tender response templates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tender_response_template (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                template_name TEXT NOT NULL,
                template_type TEXT,
                description TEXT,
                sections TEXT,
                field_mappings TEXT,
                version INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                UNIQUE(company_id, template_name),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        
        # Past tender responses
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS past_tender_response (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                tender_id TEXT,
                response_type TEXT,
                response_data TEXT,
                response_file_path TEXT,
                was_successful BOOLEAN DEFAULT 0,
                award_amount REAL,
                feedback TEXT,
                lessons_learned TEXT,
                improvement_points TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                submitted_by INTEGER,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                FOREIGN KEY (submitted_by) REFERENCES users(id)
            )
        """)
        
        # Certificates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS certificate (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                certificate_name TEXT NOT NULL,
                certificate_number TEXT,
                issuing_body TEXT NOT NULL,
                issue_date DATE,
                expiry_date DATE,
                certificate_type TEXT,
                grade TEXT,
                scope TEXT,
                document_path TEXT,
                verification_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, certificate_number),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        
        # Work programs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS work_program (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                program_name TEXT NOT NULL,
                program_type TEXT,
                description TEXT,
                methodology TEXT,
                quality_control_plan TEXT,
                safety_plan TEXT,
                environmental_plan TEXT,
                resource_requirements TEXT,
                timeline TEXT,
                milestones TEXT,
                document_path TEXT,
                is_standard BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, program_name),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        
        # Methodologies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS methodology (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                methodology_name TEXT NOT NULL,
                methodology_type TEXT,
                description TEXT,
                steps TEXT,
                equipment_needed TEXT,
                personnel_needed TEXT,
                safety_measures TEXT,
                quality_checks TEXT,
                document_path TEXT,
                is_standard BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(company_id, methodology_name),
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        
        # Company licenses (v011)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                license_type TEXT NOT NULL,
                license_number TEXT NOT NULL,
                issuing_authority TEXT,
                issue_date DATE,
                expiry_date DATE,
                license_file_path TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        
        # Company financials (v011)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_financials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                fiscal_year TEXT NOT NULL,
                annual_turnover REAL,
                construction_turnover REAL,
                net_worth REAL,
                working_capital REAL,
                liquid_assets REAL,
                credit_limit REAL,
                bank_guarantee_limit REAL,
                is_audited BOOLEAN DEFAULT 0,
                audit_firm TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        
        # Company personnel (v011)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_personnel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                designation TEXT NOT NULL,
                nid_number TEXT,
                phone TEXT,
                email TEXT,
                educational_qualification TEXT,
                experience_years INTEGER,
                is_key_personnel BOOLEAN DEFAULT 0,
                cv_file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        
        # Company documents (v011)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                document_name TEXT NOT NULL,
                document_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_name TEXT,
                description TEXT,
                document_date DATE,
                expiry_date DATE,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uploaded_by INTEGER,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            )
        """)
        
        # Extension downloads
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extension_downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                company_id INTEGER,
                username TEXT,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        """)
        
        # System config
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER,
                FOREIGN KEY (updated_by) REFERENCES users(id)
            )
        """)
        
        # Schema migrations tracker
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT 1
            )
        """)
        
        # Password reset tokens
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                token TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Version change log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS version_change_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id INTEGER,
                source TEXT,
                action TEXT,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                FOREIGN KEY (version_id) REFERENCES rate_versions(id)
            )
        """)
        
        # =========================================================
        # CREATE INDEXES FOR PERFORMANCE
        # =========================================================
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_company ON users(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_company ON subscriptions(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_tender_analyses_company ON tender_analyses(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_extension_log_company ON extension_auto_fill_log(company_id, filled_at)",
            "CREATE INDEX IF NOT EXISTS idx_personnel_company ON personnel(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_equipment_company ON equipment(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_experience_company ON experience_record(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_company_tenders_company ON company_tenders(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_boq_history_company ON boq_generation_history(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_scenarios_company ON saved_scenarios(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_pwd_parents_chapter ON pwd_parents(chapter_number)",
            "CREATE INDEX IF NOT EXISTS idx_pwd_children_parent ON pwd_children(parent_code)",
            "CREATE INDEX IF NOT EXISTS idx_lged_parents_chapter ON lged_parents(chapter_number)",
            "CREATE INDEX IF NOT EXISTS idx_lged_children_parent ON lged_children(parent_code)",
            "CREATE INDEX IF NOT EXISTS idx_historical_company ON historical_tenders(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_competitor_master_company ON competitor_master(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_activity_company ON activity_logs(company_id)",
            "CREATE INDEX IF NOT EXISTS idx_document_company ON document_registry(company_id)",
        ]
        
        for index in indexes:
            try:
                cursor.execute(index)
            except Exception as e:
                pass  # Index might already exist
        
        conn.commit()
        conn.close()
        print("✅ All tables created successfully")
    
    def _insert_default_data(self):
        """Insert default data if tables are empty"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Insert default subscription plans
        cursor.execute("SELECT COUNT(*) FROM subscription_plans")
        if cursor.fetchone()[0] == 0:
            default_plans = [
                ('free', 0, 0, 5, 5, 5, 1, 5, 0, 0, 0, 0, 0, 'Free plan with basic features'),
                ('basic', 4999, 49990, 30, 30, 30, 3, 30, 1, 0, 0, 0, 0, 'Basic plan for small businesses'),
                ('professional', 14999, 149990, 100, 100, -1, 10, 100, 1, 1, 0, 1, 1, 'Professional plan for growing businesses'),
                ('enterprise', 49999, 499990, -1, -1, -1, -1, -1, 1, 1, 1, 1, 1, 'Enterprise plan with unlimited features')
            ]
            for plan in default_plans:
                cursor.execute("""
                    INSERT INTO subscription_plans 
                    (plan_name, monthly_price, yearly_price, max_boq_generations, max_bid_optimizations,
                     max_tender_analyses, max_users, extension_auto_fills, can_export_data, can_edit_rates,
                     can_delete_rates, can_create_versions, can_manage_team, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, plan)
        
        # Create default admin company
        cursor.execute("SELECT COUNT(*) FROM companies")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO companies (company_name, email, is_active)
                VALUES ('System Admin', 'admin@tenderai.com', 1)
            """)
            
            cursor.execute("SELECT id FROM companies WHERE company_name = 'System Admin'")
            admin_company_id = cursor.fetchone()[0]
            
            # Create admin user (password: admin123)
            hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
            cursor.execute("""
                INSERT INTO users (company_id, username, password, email, full_name, role, is_active, is_approved)
                VALUES (?, 'admin', ?, 'admin@tenderai.com', 'System Administrator', 'system_admin', 1, 1)
            """, (admin_company_id, hashed))
        
        # Insert default LGED zones
        cursor.execute("SELECT COUNT(*) FROM lged_zone_mapping")
        if cursor.fetchone()[0] == 0:
            zones = [
                ('A', 'Dhaka & Mymensingh Division', '["Dhaka","Mymensingh"]', 0.05, 'Capital region'),
                ('B', 'Chattogram & Sylhet Division', '["Chattogram","Sylhet"]', 0.05, 'Port city region'),
                ('C', 'Rajshahi & Rangpur Division', '["Rajshahi","Rangpur"]', 0.05, 'Northern region'),
                ('D', 'Khulna & Barishal Division', '["Khulna","Barishal"]', 0.05, 'Southern region')
            ]
            for zone in zones:
                cursor.execute("""
                    INSERT INTO lged_zone_mapping (zone_code, zone_name, divisions, accessibility_bonus, description)
                    VALUES (?, ?, ?, ?, ?)
                """, zone)
        
        # Insert default role permissions
        cursor.execute("SELECT COUNT(*) FROM role_permissions")
        if cursor.fetchone()[0] == 0:
            default_permissions = {
                'system_admin': {'manage_users': True, 'manage_tenders': True, 'view_reports': True, 'export_data': True, 'manage_team': True, 'manage_system': True},
                'admin': {'manage_users': True, 'manage_tenders': True, 'view_reports': True, 'export_data': True, 'manage_team': True, 'manage_system': False},
                'company_admin': {'manage_users': True, 'manage_tenders': True, 'view_reports': True, 'export_data': True, 'manage_team': True, 'manage_system': False},
                'manager': {'manage_users': False, 'manage_tenders': True, 'view_reports': True, 'export_data': True, 'manage_team': True, 'manage_system': False},
                'analyst': {'manage_users': False, 'manage_tenders': True, 'view_reports': True, 'export_data': True, 'manage_team': False, 'manage_system': False},
                'viewer': {'manage_users': False, 'manage_tenders': False, 'view_reports': True, 'export_data': False, 'manage_team': False, 'manage_system': False}
            }
            for role, perms in default_permissions.items():
                cursor.execute("INSERT INTO role_permissions (role, permissions) VALUES (?, ?)", (role, json.dumps(perms)))
        
        conn.commit()
        conn.close()
        print("✅ Default data inserted")
    
    
        
        conn.commit()
        conn.close()
        print("✅ Default data inserted")