"""
Database Manager for TenderAI System
Handles all database operations including users, subscriptions, tenders, and competitor tracking
"""
import streamlit as st
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from unittest import result
import pandas as pd
import numpy as np
import logging
import bcrypt
import os
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Union  # ← Add this line
import secrets
import string
import re

logger = logging.getLogger(__name__)
logging.getLogger("pdfminer").setLevel(logging.WARNING)
logging.getLogger("pdfminer.psparser").setLevel(logging.WARNING)
logging.getLogger("pdfminer.pdfdocument").setLevel(logging.WARNING)
logging.getLogger("pdfminer.pdfpage").setLevel(logging.WARNING)
logging.getLogger("pdfplumber").setLevel(logging.WARNING)

class DatabaseManager:
    def __init__(self, db_path="data/tender_system.db"):
        
        
        self.db_path = db_path
        # Force a database directory build check if it's missing on fresh clones
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize base tables if absent
        if not self._tables_exist():
            self.init_database()
            
        # FORCE ALIGNMENT: Explicitly initialize advanced BOQ subsystems 
        # so they build even if the legacy 'users' table already exists.
        #self.init_boq_tables_direct()
        #self.init_pwd_hierarchical_tables()
        #self.init_chapters_tables()
        #self.init_lged_tables()
        #self.init_boq_management_tables()  # ← ADD THIS LINE
        #self.migrate_lged_tables_for_sections()
        #self.migrate_rate_versions_add_version_number()
        self.migrate_subscription()    
        #self.migrate_lged_tables_for_parent_types()
        self._verify_tables()

    def _verify_tables(self):
        """Verify that all expected tables exist"""
        expected_tables = ['users', 'companies', 'subscriptions', 'rate_versions', 
                        'lged_parents', 'lged_children', 'pwd_parents', 'pwd_children']
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        missing = [t for t in expected_tables if t not in existing]
        if missing:
            print(f"⚠️ Warning: Missing tables: {missing}. Run migrations to fix.")

    def migrate_subscription(self):
        """Initialize subscription tables and add missing columns"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        print("🔧 Migrating subscription tables...")
        
        # ========== 1. CREATE SUBSCRIPTION PLANS TABLE ==========
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
        
        # Insert default plans
        default_plans = [
            ('free', 'company', 0, 0, 5, 5, 5, 1, 0, 0, 0, 0, 0, 'Free plan with basic features'),
            ('basic', 'company', 4999, 49990, 30, 30, 30, 5, 1, 0, 0, 0, 0, 'Basic plan for small businesses'),
            ('professional', 'company', 14999, 149990, 100, 100, -1, 15, 1, 0, 0, 1, 1, 'Professional plan for growing businesses'),
            ('enterprise', 'company', 49999, 499990, -1, -1, -1, -1, 1, 0, 0, 1, 1, 'Enterprise plan with unlimited features')
        ]
        
        for plan in default_plans:
            cursor.execute("""
                INSERT OR IGNORE INTO subscription_plans (
                    plan_name, plan_type, monthly_price, yearly_price,
                    max_boq_generations, max_bid_optimizations, max_tender_analyses,
                    max_users, can_export_data, can_edit_rates, can_delete_rates,
                    can_create_versions, can_manage_team, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, plan)
        
        # ========== 2. ADD MISSING COLUMNS TO SUBSCRIPTIONS TABLE ==========
        # Check existing columns
        cursor.execute("PRAGMA table_info(subscriptions)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Define columns to add
        columns_to_add = {
            'max_boq_generations': 'INTEGER DEFAULT 5',
            'max_bid_optimizations': 'INTEGER DEFAULT 5',
            'boq_used': 'INTEGER DEFAULT 0',
            'bid_optimizations_used': 'INTEGER DEFAULT 0',
            'can_edit_rates': 'BOOLEAN DEFAULT 0',
            'can_delete_rates': 'BOOLEAN DEFAULT 0',
            'can_create_versions': 'BOOLEAN DEFAULT 0',
            'can_export_data': 'BOOLEAN DEFAULT 0',
            'can_manage_team': 'BOOLEAN DEFAULT 0',
            'last_reset_date': 'DATE'
        }
        
        for col_name, col_type in columns_to_add.items():
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE subscriptions ADD COLUMN {col_name} {col_type}")
                    print(f"  ✅ Added column: {col_name}")
                except Exception as e:
                    print(f"  ⚠️ Could not add {col_name}: {e}")
        
        # ========== 3. UPDATE EXISTING SUBSCRIPTIONS WITH PLAN VALUES ==========
        # Set default values based on plan
        cursor.execute("""
            UPDATE subscriptions 
            SET 
                analyses_limit = CASE plan
                    WHEN 'free' THEN 5
                    WHEN 'basic' THEN 30
                    WHEN 'professional' THEN -1
                    WHEN 'enterprise' THEN -1
                    ELSE 5
                END,
                max_boq_generations = CASE plan
                    WHEN 'free' THEN 5
                    WHEN 'basic' THEN 30
                    WHEN 'professional' THEN 100
                    WHEN 'enterprise' THEN -1
                    ELSE 5
                END,
                max_bid_optimizations = CASE plan
                    WHEN 'free' THEN 5
                    WHEN 'basic' THEN 30
                    WHEN 'professional' THEN 100
                    WHEN 'enterprise' THEN -1
                    ELSE 5
                END,
                can_edit_rates = CASE plan
                    WHEN 'professional' THEN 1
                    WHEN 'enterprise' THEN 1
                    ELSE 0
                END,
                can_delete_rates = CASE plan
                    WHEN 'enterprise' THEN 1
                    ELSE 0
                END,
                can_create_versions = CASE plan
                    WHEN 'professional' THEN 1
                    WHEN 'enterprise' THEN 1
                    ELSE 0
                END,
                can_export_data = CASE plan
                    WHEN 'basic' THEN 1
                    WHEN 'professional' THEN 1
                    WHEN 'enterprise' THEN 1
                    ELSE 0
                END,
                can_manage_team = CASE plan
                    WHEN 'professional' THEN 1
                    WHEN 'enterprise' THEN 1
                    ELSE 0
                END,
                last_reset_date = date('now')
            WHERE plan IN ('free', 'basic', 'professional', 'enterprise')
        """)
        
        conn.commit()
        conn.close()
        print("✅ Subscription migration complete!")
    def init_database(self):
        """Initialize all database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # ==================== EXISTING TABLES ====================
        
        # Companies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT UNIQUE NOT NULL,
                registration_number TEXT,
                vat_number TEXT,
                address TEXT,
                district TEXT,
                division TEXT,
                phone TEXT,
                email TEXT,
                website TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
            ''')
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                phone TEXT,
                role TEXT DEFAULT 'user',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (company_id) REFERENCES companies (id)
            )
            ''')
        
        # Subscriptions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan TEXT DEFAULT 'free',
                status TEXT DEFAULT 'active',
                start_date DATE,
                end_date DATE,
                analyses_used INTEGER DEFAULT 0,
                analyses_limit INTEGER DEFAULT 5,
                payment_method TEXT,
                transaction_id TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            ''')
        
                
        # 3. Create consultant-client mapping table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultant_clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consultant_user_id INTEGER REFERENCES users(id),
                client_company_id INTEGER REFERENCES companies(id),
                role TEXT DEFAULT 'manager',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(consultant_user_id, client_company_id)
            )''')

        # 4. Indexes for fast lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sub_user ON subscriptions(user_id);
            ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sub_company ON subscriptions(company_id);
            ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_consultant_client ON consultant_clients(consultant_user_id);
            ''')
        # Tender analyses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tender_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                company_id INTEGER,
                tender_id TEXT,
                tender_title TEXT,
                procuring_entity TEXT,
                division TEXT,
                construction_type TEXT,
                official_estimate REAL,
                recommended_bid REAL,
                actual_bid REAL,
                success_probability REAL,
                risk_level TEXT,
                competitor_count INTEGER,
                bid_status TEXT,
                analysis_type TEXT,
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (company_id) REFERENCES companies (id)
            )
            ''')
        
        # Contact messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                subject TEXT,
                message TEXT,
                status TEXT DEFAULT 'unread',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
        
        # ==================== HISTORICAL DATA TABLES ====================
        
        # Historical tenders table
        cursor.execute('''
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
                num_competitors INTEGER,
                total_bidders INTEGER,
                our_rank INTEGER,
                award_date DATE,
                competitors_data TEXT,
                winning_competitor TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (company_id) REFERENCES companies (id)
            )
            ''')
        # 1. Extends state management for ingested e-GP Tenders
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenders_boq_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id TEXT PRIMARY KEY,
                ministry_or_agency TEXT,
                selected_zone TEXT,
                workflow_status TEXT CHECK(workflow_status IN ('Draft', 'Pending Approval', 'Approved')) DEFAULT 'Draft',
                official_budget_cap REAL DEFAULT 0.0,
                created_by TEXT,
                approved_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Stores individual financial line items tied contextually to the Tender
        cursor.execute('''
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
        ''')

        # 3. Dedicated Audit Trail Log System
        cursor.execute('''
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
        ''')
        # 4. Competitor Pricing Registry Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competitor_bids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id TEXT,
                competitor_name TEXT NOT NULL,
                total_bid_amount REAL NOT NULL,
                submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_winner INTEGER DEFAULT 0 CHECK(is_winner IN (0, 1)),
                FOREIGN KEY(tender_id) REFERENCES tenders_boq_meta(tender_id) ON DELETE CASCADE
            )
        ''')
        # Company NPPI table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_nppi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            procurement_type TEXT,
            nppi_factor REAL,
            data_points INTEGER,
            calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies (id)
        )
        ''')
        cursor.execute('''
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
            -- Index for fast lookups
            CREATE INDEX IF NOT EXISTS idx_activity_company ON activity_logs(company_id);
            CREATE INDEX IF NOT EXISTS idx_activity_actor ON activity_logs(actor_user_id);
            CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_logs(created_at);
        )
        ''')

       
        # ==================== COMPETITOR MASTER TABLE ====================
        
        cursor.execute('''
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
            FOREIGN KEY (company_id) REFERENCES companies (id),
            UNIQUE(company_id, competitor_name)
        )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS role_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT UNIQUE NOT NULL,
                permissions TEXT,  -- JSON string of permissions
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_historical_company ON historical_tenders(company_id, procurement_type, award_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nppi_company ON company_nppi(company_id, procurement_type, calculation_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_competitor_master ON competitor_master(company_id, competitor_name)')
        
      
        # ==================== DEFAULT DATA ====================
        
        # Create default admin company if not exists
        cursor.execute('INSERT OR IGNORE INTO companies (company_name) VALUES ("System Admin")')
        cursor.execute('SELECT id FROM companies WHERE company_name = "System Admin"')
        admin_company_id = cursor.fetchone()[0]
        
        # Create admin user
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute('''
            INSERT OR IGNORE INTO users (company_id, username, password, email, full_name, role)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (admin_company_id, "admin", admin_pass, "admin@tenderai.com", "System Administrator", "admin"))
        
        # Create demo company
        cursor.execute('''
            INSERT OR IGNORE INTO companies (company_name, email, phone, division)
            VALUES (?, ?, ?, ?)
            ''', ("ABC Construction Ltd", "info@abcconstruction.com", "017XXXXXXXX", "Dhaka"))
        
        cursor.execute('SELECT id FROM companies WHERE company_name = "ABC Construction Ltd"')
        demo_company = cursor.fetchone()
        
        if demo_company:
            demo_company_id = demo_company[0]
            
            # Create demo users
            demo_users = [
                ("john.doe", "John@123", "john@abcconstruction.com", "John Doe", "company_admin"),
                ("jane.smith", "Jane@123", "jane@abcconstruction.com", "Jane Smith", "manager"),
                ("rahim.khan", "Rahim@123", "rahim@abcconstruction.com", "Rahim Khan", "analyst"),
            ]
            
            for user in demo_users:
                hashed_pass = hashlib.sha256(user[1].encode()).hexdigest()
                cursor.execute('''
                INSERT OR IGNORE INTO users (company_id, username, password, email, full_name, role)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (demo_company_id, user[0], hashed_pass, user[2], user[3], user[4]))
        
        # Insert default role permissions if not present
        default_permissions = {
            'admin': {
                'manage_users': True, 'manage_tenders': True, 'run_analysis': True,
                'view_reports': True, 'export_data': True, 'change_plans': True,
                'manage_team': True, 'delete_any': True
            },
            'company_admin': {
                'manage_users': True, 'manage_tenders': True, 'run_analysis': True,
                'view_reports': True, 'export_data': True, 'change_plans': True,
                'manage_team': True, 'delete_any': False
            },
            'manager': {
                'manage_users': False, 'manage_tenders': True, 'run_analysis': True,
                'view_reports': True, 'export_data': True, 'change_plans': False,
                'manage_team': False, 'delete_any': False
            },
            'analyst': {
                'manage_users': False, 'manage_tenders': False, 'run_analysis': True,
                'view_reports': True, 'export_data': False, 'change_plans': False,
                'manage_team': False, 'delete_any': False
            },
            'viewer': {
                'manage_users': False, 'manage_tenders': False, 'run_analysis': False,
                'view_reports': True, 'export_data': False, 'change_plans': False,
                'manage_team': False, 'delete_any': False
            }
        }
        for role, perms in default_permissions.items():
            import json
            cursor.execute('''
            INSERT OR IGNORE INTO role_permissions (role, permissions) VALUES (?, ?)
            ''', (role, json.dumps(perms)))

        conn.commit()
        conn.close()
        print("Database initialized successfully")
    
    def init_boq_tables_direct(self):
        """Guarantees advanced e-GP and PWD schemas are injected without constructor bypass conflicts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Ingested Tenders Metadata Tracking Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenders_boq_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id TEXT PRIMARY KEY,
                ministry_or_agency TEXT,
                selected_zone TEXT,
                workflow_status TEXT CHECK(workflow_status IN ('Draft', 'Pending Approval', 'Approved')) DEFAULT 'Draft',
                official_budget_cap REAL DEFAULT 0.0,
                created_by TEXT,
                approved_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Transactional Financial Line Items
        cursor.execute('''
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
        ''')
        
        # 3. Modification Accountability Logs Audit Trail
        cursor.execute('''
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
        ''')
        
        # 4. Competitor Bids Matrix Registry
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS competitor_bids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tender_id TEXT,
                competitor_name TEXT NOT NULL,
                total_bid_amount REAL NOT NULL,
                submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_winner INTEGER DEFAULT 0 CHECK(is_winner IN (0, 1)),
                FOREIGN KEY(tender_id) REFERENCES tenders_boq_meta(tender_id) ON DELETE CASCADE
            )
        ''')
        

        conn.commit()
        conn.close()


    def init_lged_tables(self):
        """Initialize LGED-specific tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # LGED Versions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT DEFAULT 'LGED',
                version_name TEXT NOT NULL,
                edition_year INTEGER NOT NULL,
                effective_from DATE,
                is_active BOOLEAN DEFAULT 0,
                released_by TEXT,
                release_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                total_parents INTEGER DEFAULT 0,
                total_children INTEGER DEFAULT 0,
                total_rates INTEGER DEFAULT 0,
                created_by TEXT
            )
        """)
        
        # LGED Parents table (updated to support both section headers and leaf items)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lged_parents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                description TEXT,
                chapter_number TEXT,
                section_number TEXT,
                parent_type TEXT DEFAULT 'section_header',  -- 'section_header' or 'leaf_item'
                has_children BOOLEAN DEFAULT 0,
                unit TEXT,
                version_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (version_id) REFERENCES rate_versions(id)
            )
        """)
        
        # LGED Children table (for items that belong to section headers)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lged_children (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                parent_code TEXT NOT NULL,
                description TEXT,
                unit TEXT,
                chapter_number TEXT,
                section_number TEXT,
                zone_a REAL,
                zone_b REAL,
                zone_c REAL,
                zone_d REAL,
                edition_year INTEGER,
                version_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (version_id) REFERENCES rate_versions(id)
            )
        """)
        
        # LGED Zone Rates table (for leaf items)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lged_zone_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER,
                zone_name TEXT NOT NULL,
                unit_rate REAL NOT NULL,
                version_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES lged_parents(id),
                FOREIGN KEY (version_id) REFERENCES rate_versions(id)
            )
        """)
        
        # LGED Sections table
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
        
        # Zone mapping table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lged_zone_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone_code TEXT PRIMARY KEY,
                zone_name TEXT,
                divisions TEXT,
                accessibility_bonus REAL DEFAULT 0.05,
                description TEXT
            )
        """)
        
        # Insert default zone mapping
        cursor.execute("""
            INSERT OR IGNORE INTO lged_zone_mapping (zone_code, zone_name, divisions, accessibility_bonus)
            VALUES 
            ('A', 'Dhaka & Mymensingh Division', '["Dhaka","Mymensingh"]', 0.05),
            ('B', 'Chattogram & Sylhet Division', '["Chattogram","Sylhet"]', 0.05),
            ('C', 'Rajshahi & Rangpur Division', '["Rajshahi","Rangpur"]', 0.05),
            ('D', 'Khulna & Barishal Division', '["Khulna","Barishal"]', 0.05)
        """)
        
        # Insert default sections for Chapter 1 (your data uses Chapter 1)
        default_sections = [
            ("1", "1.01", "Site Office Setup", 1),
            ("1", "1.1", "Videography Services", 2),
        ]
        
        for chapter_num, section_num, section_name, display_order in default_sections:
            cursor.execute("""
                INSERT OR IGNORE INTO lged_sections (chapter_number, section_number, section_name, display_order)
                VALUES (?, ?, ?, ?)
            """, (chapter_num, section_num, section_name, display_order))
        
        conn.commit()
        conn.close()
        print("✅ LGED tables initialized")
    def migrate_lged_tables_for_parent_types(self):
        """Migrate existing LGED tables to support parent types (section_header vs leaf_item)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check and add parent_type column to lged_parents
        cursor.execute("PRAGMA table_info(lged_parents)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'parent_type' not in columns:
            cursor.execute("ALTER TABLE lged_parents ADD COLUMN parent_type TEXT DEFAULT 'section_header'")
            print("✅ Added parent_type to lged_parents")
        
        if 'has_children' not in columns:
            cursor.execute("ALTER TABLE lged_parents ADD COLUMN has_children BOOLEAN DEFAULT 0")
            print("✅ Added has_children to lged_parents")
        
        if 'unit' not in columns:
            cursor.execute("ALTER TABLE lged_parents ADD COLUMN unit TEXT")
            print("✅ Added unit to lged_parents")
        
        # Check lged_children for rate columns
        cursor.execute("PRAGMA table_info(lged_children)")
        child_columns = [col[1] for col in cursor.fetchall()]
        
        if 'zone_a' not in child_columns:
            cursor.execute("ALTER TABLE lged_children ADD COLUMN zone_a REAL")
            cursor.execute("ALTER TABLE lged_children ADD COLUMN zone_b REAL")
            cursor.execute("ALTER TABLE lged_children ADD COLUMN zone_c REAL")
            cursor.execute("ALTER TABLE lged_children ADD COLUMN zone_d REAL")
            print("✅ Added zone rate columns to lged_children")
        
        conn.commit()
        conn.close()
    def migrate_lged_tables_for_sections(self):
        """Add section support columns to LGED tables if missing"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Migrate lged_parents table
        cursor.execute("PRAGMA table_info(lged_parents)")
        parent_columns = [col[1] for col in cursor.fetchall()]
        
        if 'section_number' not in parent_columns:
            cursor.execute("ALTER TABLE lged_parents ADD COLUMN section_number TEXT")
            print("✅ Added section_number to lged_parents")
        
        # Migrate lged_children table
        cursor.execute("PRAGMA table_info(lged_children)")
        child_columns = [col[1] for col in cursor.fetchall()]
        
        if 'chapter_number' not in child_columns:
            cursor.execute("ALTER TABLE lged_children ADD COLUMN chapter_number TEXT")
            print("✅ Added chapter_number to lged_children")
        
        if 'section_number' not in child_columns:
            cursor.execute("ALTER TABLE lged_children ADD COLUMN section_number TEXT")
            print("✅ Added section_number to lged_children")
        
        conn.commit()
        conn.close()
        print("✅ LGED tables migration complete")

    def migrate_rate_versions_add_version_number(self):
        """Add version_number column to rate_versions table if missing"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if version_number column exists
            cursor.execute("PRAGMA table_info(rate_versions)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'version_number' not in columns:
                cursor.execute("ALTER TABLE rate_versions ADD COLUMN version_number INTEGER DEFAULT 1")
                print("✅ Added version_number column to rate_versions")
            
            if 'updated_at' not in columns:
                cursor.execute("ALTER TABLE rate_versions ADD COLUMN updated_at TIMESTAMP")
                print("✅ Added updated_at column to rate_versions")
            
            if 'notes' not in columns:
                cursor.execute("ALTER TABLE rate_versions ADD COLUMN notes TEXT")
                print("✅ Added notes column to rate_versions")
            
            # Update existing records to have version_number = 1
            cursor.execute("""
                UPDATE rate_versions 
                SET version_number = 1 
                WHERE version_number IS NULL
            """)
            
            conn.commit()
            
        except Exception as e:
            print(f"⚠️ Migration error: {e}")
            conn.rollback()
        finally:
            conn.close()    
    def init_pwd_hierarchical_tables(self):
        """Initialize hierarchical PWD tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Ensure rate_versions table exists with all columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT DEFAULT 'PWD',
                version_name TEXT NOT NULL,
                edition_year INTEGER NOT NULL,
                effective_from DATE,
                is_active BOOLEAN DEFAULT 0,
                released_by TEXT,
                release_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                total_parents INTEGER DEFAULT 0,
                total_children INTEGER DEFAULT 0,
                total_rates INTEGER DEFAULT 0,
                created_by TEXT
            )
        """)
        
        # Parent items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pwd_parents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pwd_code TEXT PRIMARY KEY,
                description TEXT,
                chapter_number TEXT,
                version_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Child items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pwd_children (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pwd_code TEXT PRIMARY KEY,
                parent_code TEXT NOT NULL,
                description TEXT,
                unit TEXT,
                edition_year INTEGER,
                version_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_code) REFERENCES pwd_parents(pwd_code) ON DELETE CASCADE
            )
        ''')
        
        # Rates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pwd_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pwd_code TEXT NOT NULL,
                zone_name TEXT NOT NULL,
                unit_rate REAL NOT NULL,
                edition_year INTEGER NOT NULL,
                version_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(pwd_code, zone_name, edition_year),
                FOREIGN KEY (pwd_code) REFERENCES pwd_children(pwd_code) ON DELETE CASCADE
            )
        ''')
        
        # Indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pwd_parent_chapter ON pwd_parents(chapter_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pwd_child_parent ON pwd_children(parent_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pwd_rates_code ON pwd_rates(pwd_code)')
        
        conn.commit()
        conn.close()
        print("✅ PWD hierarchical tables initialized")


    def init_chapters_tables(self):
        """Initialize chapters tables for both PWD and LGED"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # PWD Chapters table (without description column initially)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pwd_chapters (
                chapter_number TEXT PRIMARY KEY,
                chapter_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add description column if it doesn't exist (for future use)
        try:
            cursor.execute("ALTER TABLE pwd_chapters ADD COLUMN description TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # LGED Chapters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lged_chapters (
                chapter_number TEXT PRIMARY KEY,
                chapter_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add description column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE lged_chapters ADD COLUMN description TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Insert default PWD chapters
        default_pwd_chapters = [
            ("01", "General, Site Facilities and Safety"),
            ("02", "Excavation, Filling & Site Development"),
            ("03", "Brick Works, Patent Stone and Fancy Screen"),
            ("04", "Reinforced Cement Concrete (RCC) Works"),
            ("05", "Mosaic Works"),
            ("06", "Tiles, Marble and Granite Stone Works"),
            ("07", "Wood Works"),
            ("08", "Window Grill, Verandah Grill & Netting"),
            ("09", "Pile Works and Pile Test"),
            ("10", "Structural Steel Works"),
            ("11", "Wood Works in Door and Window Frame"),
            ("12", "Collapsible Gate, M.S. Gate, Rolling Shutter"),
            ("13", "Aluminium Door, Window and Partition"),
            ("14", "Cement Plaster, Fair-Face Plaster"),
            ("15", "Painting and Polishing"),
            ("16", "Water Proofing and Heat Proofing"),
            ("17", "False Ceiling and Wall Panelling"),
            ("18", "Sanitary and Plumbing Works"),
            ("19", "Gas Pipe Line Installation"),
            ("20", "Sub-Soil Investigation"),
            ("21", "Repair Works")
        ]
        
        for chapter_num, chapter_name in default_pwd_chapters:
            cursor.execute("""
                INSERT OR IGNORE INTO pwd_chapters (chapter_number, chapter_name)
                VALUES (?, ?)
            """, (chapter_num, chapter_name))
        
        # Insert default LGED chapters
        default_lged_chapters = [
            ("1", "General, Site Facilities and Safety"),
            ("2", "Earth Works in Road Embankment"),
            ("3", "Sub-Base and Base Course"),
            ("4", "Bituminous Pavement"),
            ("5", "Bridge and Culvert Works"),
            ("6", "Building Works"),
            ("7", "Sanitary and Water Supply"),
            ("8", "Electrical Works"),
            ("9", "Landscaping and Development")
        ]
        
        for chapter_num, chapter_name in default_lged_chapters:
            cursor.execute("""
                INSERT OR IGNORE INTO lged_chapters (chapter_number, chapter_name)
                VALUES (?, ?)
            """, (chapter_num, chapter_name))
        
        conn.commit()
        conn.close()
        print("✅ Chapters tables initialized")
    

    def init_boq_management_tables(self):
        """Initialize BOQ management tables with tender linking"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # BOQ generation history with tender link
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
                FOREIGN KEY (tender_id) REFERENCES tenders_boq_meta(tender_id) ON DELETE SET NULL
            )
        """)
        
        # Bid submissions tracking
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
                FOREIGN KEY (tender_id) REFERENCES tenders_boq_meta(tender_id) ON DELETE SET NULL
            )
        """)
        
        # Add indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_boq_history_tender ON boq_generation_history(tender_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_boq_history_user ON boq_generation_history(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_boq_history_company ON boq_generation_history(company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bid_submissions_tender ON bid_submissions(tender_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bid_submissions_company ON bid_submissions(company_id)")
        
        conn.commit()
        conn.close()
        print("✅ BOQ management tables initialized")

    
    def save_lged_hierarchy_enhanced(self, hierarchy, version_name, edition_year, 
                                  effective_date=None, selected_chapters=None, 
                                  selected_sections=None):
        """
        Save LGED hierarchy with support for:
        - Section headers (parents without rates, have children)
        - Leaf items (parents with rates, no children)
        - Child items (belong to section headers)
        """
        from datetime import date
        import json
        
        # Ensure schema is updated
        self.migrate_lged_tables_for_parent_types()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        effective_date = effective_date or date.today()
        has_sections = selected_sections is not None and len(selected_sections) > 0
        
        try:
            # Create version record
            cursor.execute("""
                INSERT INTO rate_versions (source, version_name, edition_year, effective_from, 
                                        is_active, release_date, created_by, has_sections)
                VALUES ('LGED', ?, ?, ?, 1, ?, ?, ?)
            """, (version_name, edition_year, effective_date, datetime.now(), 
                'system', has_sections))
            
            version_id = cursor.lastrowid
            
            # Save section headers (parents without rates)
            section_headers = [p for p in hierarchy.get('section_headers', [])]
            leaf_items = [p for p in hierarchy.get('leaf_items', [])]
            children = hierarchy.get('children', [])
            
            parent_ids = {}
            
            # Save section headers (parents without rates, may have children)
            for header in section_headers:
                cursor.execute("""
                    INSERT INTO lged_parents (code, description, chapter_number, section_number, 
                                            parent_type, has_children, version_id)
                    VALUES (?, ?, ?, ?, 'section_header', ?, ?)
                """, (header['code'], header.get('description', ''), 
                    header.get('chapter_number', ''), header.get('section_number', ''),
                    1 if header.get('has_children') else 0, version_id))
                parent_ids[header['code']] = cursor.lastrowid
            
            # Save leaf items (parents with rates, no children)
            for leaf in leaf_items:
                cursor.execute("""
                    INSERT INTO lged_parents (code, description, chapter_number, section_number, 
                                            parent_type, has_children, unit, version_id)
                    VALUES (?, ?, ?, ?, 'leaf_item', 0, ?, ?)
                """, (leaf['code'], leaf.get('description', ''), 
                    leaf.get('chapter_number', ''), leaf.get('section_number', ''),
                    leaf.get('unit', ''), version_id))
                parent_id = cursor.lastrowid
                parent_ids[leaf['code']] = parent_id
                
                # Save rates for leaf items
                for zone, rate in leaf.get('rates', {}).items():
                    cursor.execute("""
                        INSERT INTO lged_zone_rates (parent_id, zone_name, unit_rate, version_id)
                        VALUES (?, ?, ?, ?)
                    """, (parent_id, zone, rate, version_id))
            
            # Save child items (belong to section headers)
            for child in children:
                parent_code = child.get('parent_code', '')
                cursor.execute("""
                    INSERT INTO lged_children (code, parent_code, description, unit, 
                                            chapter_number, section_number,
                                            zone_a, zone_b, zone_c, zone_d,
                                            edition_year, version_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (child['code'], parent_code, child.get('description', ''), 
                    child.get('unit', ''),
                    child.get('chapter_number', ''), child.get('section_number', ''),
                    child.get('zone_a'), child.get('zone_b'), 
                    child.get('zone_c'), child.get('zone_d'),
                    edition_year, version_id))
            
            # Update version record with statistics
            cursor.execute("""
                UPDATE rate_versions 
                SET total_parents = ?, total_children = ?, total_rates = ?
                WHERE id = ?
            """, (len(section_headers) + len(leaf_items), len(children), 
                len(leaf_items) + len(children), version_id))
            
            conn.commit()
            
            print(f"✅ Saved LGED hierarchy:")
            print(f"  - Section Headers: {len(section_headers)}")
            print(f"  - Leaf Items: {len(leaf_items)}")
            print(f"  - Child Items: {len(children)}")
            
            return version_id
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error saving LGED hierarchy: {e}")
            import traceback
            traceback.print_exc()
            raise e
        finally:
            conn.close()



    # ==================== LGED IMPORT MODES METHODS ====================

    def get_active_version_id(self, source: str, edition_year: int) -> Optional[int]:
        """Get the active version ID for a specific source and edition year"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id FROM rate_versions 
            WHERE source = ? AND edition_year = ? AND is_active = 1
            LIMIT 1
        """, (source, edition_year))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None

    def version_exists(self, source: str, edition_year: int) -> bool:
        """Check if ANY version exists for given source and edition year"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Count all versions (including inactive)
        cursor.execute("""
            SELECT COUNT(*) FROM rate_versions 
            WHERE source = ? AND edition_year = ?
        """, (source, edition_year))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0

    def get_version_history(self, source: str, edition_year: int) -> pd.DataFrame:
        """Get version history for a specific source and edition year"""
        conn = self.get_connection()
        
        try:
            # Use a simpler query that works regardless of columns
            query = """
                SELECT 
                    id, 
                    version_name, 
                    version_number, 
                    is_active,
                    COALESCE(created_at, release_date, datetime('now')) as created_at,
                    COALESCE(updated_at, release_date, datetime('now')) as updated_at,
                    COALESCE(total_parents, 0) as total_parents,
                    COALESCE(total_children, 0) as total_children,
                    COALESCE(total_rates, 0) as total_rates,
                    COALESCE(notes, '') as notes
                FROM rate_versions
                WHERE source = ? AND edition_year = ?
                ORDER BY version_number DESC
            """
            
            df = pd.read_sql_query(query, conn, params=(source, edition_year))
            
            # Calculate total_items
            if not df.empty:
                df['total_items'] = df['total_parents'] + df['total_children']
            
            conn.close()
            return df
            
        except Exception as e:
            print(f"Error getting version history: {e}")
            conn.close()
            return pd.DataFrame()
    def update_existing_lged_version(self, hierarchy, version_id, edition_year, notes=None):
        """Update an existing version with new data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Clear existing data for this version
            cursor.execute("DELETE FROM lged_children WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM lged_parents WHERE version_id = ?", (version_id,))
            
            # Get data from hierarchy
            section_headers = hierarchy.get('section_headers', [])
            rate_items = hierarchy.get('rate_items', [])
            
            # Save section headers
            for header in section_headers:
                cursor.execute("""
                    INSERT INTO lged_parents (code, description, chapter_number, section_number, 
                                            parent_type, has_children, version_id)
                    VALUES (?, ?, ?, ?, 'section_header', ?, ?)
                """, (header['code'], header.get('description', '')[:500], 
                    header.get('chapter_number', ''), header.get('section_number', ''),
                    1 if header.get('has_children') else 0, version_id))
            
            # Save ALL rate items
            for item in rate_items:
                cursor.execute("""
                    INSERT INTO lged_children (
                        code, parent_code, description, unit, 
                        chapter_number, section_number,
                        zone_a, zone_b, zone_c, zone_d,
                        edition_year, version_id, is_parent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item['code'], 
                    item.get('parent_code'), 
                    item.get('description', '')[:500], 
                    item.get('unit', ''),
                    item.get('chapter_number', ''), 
                    item.get('section_number', ''),
                    item.get('zone_a'), item.get('zone_b'), 
                    item.get('zone_c'), item.get('zone_d'),
                    edition_year, version_id, 
                    1 if item.get('is_parent') else 0
                ))
            
            # Update version record
            total_parents = len(section_headers) + len([i for i in rate_items if i.get('is_parent')])
            total_children = len([i for i in rate_items if not i.get('is_parent')])
            total_rates = len(rate_items) * 4
            
            cursor.execute("""
                UPDATE rate_versions 
                SET total_parents = ?, total_children = ?, total_rates = ?,
                    updated_at = ?, notes = ?, is_active = 1
                WHERE id = ?
            """, (total_parents, total_children, total_rates,
                datetime.now(), notes, version_id))
            
            conn.commit()
            
            # Get version number for display
            cursor.execute("SELECT version_number FROM rate_versions WHERE id = ?", (version_id,))
            version_number = cursor.fetchone()[0]
            
            return {
                'success': True,
                'version_id': version_id,
                'version_number': version_number,
                'mode': 'update',
                'message': f"✅ Updated Version {version_number} for LGED {edition_year}"
            }
            
        except Exception as e:
            conn.rollback()
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'mode': 'update',
                'message': f"❌ Failed to update version: {e}"
            }
        finally:
            conn.close()

    def save_lged_hierarchy_enhanced(self, hierarchy, version_name, edition_year, 
                                  effective_date=None, selected_chapters=None, 
                                  selected_sections=None, notes=None):
        """
        Create NEW version for LGED hierarchy
        """
        from datetime import date
        
        self.migrate_lged_tables_for_parent_types()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        effective_date = effective_date or date.today()
        has_sections = selected_sections is not None and len(selected_sections) > 0
        
        try:
            # Get the next version number
            cursor.execute("""
                SELECT MAX(version_number) FROM rate_versions 
                WHERE source = 'LGED' AND edition_year = ?
            """, (edition_year,))
            
            result = cursor.fetchone()
            next_version = (result[0] or 0) + 1
            
            # Deactivate current active version
            cursor.execute("""
                UPDATE rate_versions 
                SET is_active = 0, updated_at = ?
                WHERE source = 'LGED' AND edition_year = ? AND is_active = 1
            """, (datetime.now(), edition_year))
            
            # Create new version
            cursor.execute("""
                INSERT INTO rate_versions (
                    source, version_name, edition_year, version_number,
                    effective_from, is_active, release_date, 
                    created_by, has_sections, notes
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """, ('LGED', version_name, edition_year, next_version, 
                effective_date, datetime.now(), 'system', has_sections, notes))
            
            version_id = cursor.lastrowid
            print(f"✅ Created version {next_version} for LGED {edition_year}")
            
            # Get data from hierarchy
            section_headers = hierarchy.get('section_headers', [])
            rate_items = hierarchy.get('rate_items', [])
            
            # Clear existing data for this version
            cursor.execute("DELETE FROM lged_children WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM lged_parents WHERE version_id = ?", (version_id,))
            
            # Save section headers (parents without rates) - stored in lged_parents
            for header in section_headers:
                cursor.execute("""
                    INSERT INTO lged_parents (code, description, chapter_number, section_number, 
                                            parent_type, has_children, version_id)
                    VALUES (?, ?, ?, ?, 'section_header', ?, ?)
                """, (header['code'], header.get('description', '')[:500], 
                    header.get('chapter_number', ''), header.get('section_number', ''),
                    1 if header.get('has_children') else 0, version_id))
            
            # Save ALL rate items (both 2-part and 3-part codes) - stored in lged_children
            for item in rate_items:
                cursor.execute("""
                    INSERT INTO lged_children (
                        code, parent_code, description, unit, 
                        chapter_number, section_number,
                        zone_a, zone_b, zone_c, zone_d,
                        edition_year, version_id, is_parent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item['code'], 
                    item.get('parent_code'), 
                    item.get('description', '')[:500], 
                    item.get('unit', ''),
                    item.get('chapter_number', ''), 
                    item.get('section_number', ''),
                    item.get('zone_a'), item.get('zone_b'), 
                    item.get('zone_c'), item.get('zone_d'),
                    edition_year, version_id, 
                    1 if item.get('is_parent') else 0
                ))
            
            # Count items
            total_parents = len(section_headers) + len([i for i in rate_items if i.get('is_parent')])
            total_children = len([i for i in rate_items if not i.get('is_parent')])
            total_rates = len(rate_items) * 4  # Each item has 4 zones
            
            # Update version record with statistics
            cursor.execute("""
                UPDATE rate_versions 
                SET total_parents = ?, total_children = ?, total_rates = ?
                WHERE id = ?
            """, (total_parents, total_children, total_rates, version_id))
            
            conn.commit()
            
            return {
                'success': True,
                'version_id': version_id,
                'version_number': next_version,
                'mode': 'create_new',
                'total_parents': total_parents,
                'total_children': total_children,
                'total_rates': total_rates,
                'message': f"✅ Created new version {next_version} for LGED {edition_year}"
            }

            
        except Exception as e:
            conn.rollback()
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'mode': 'create_new',
                'message': f"❌ Failed to create new version: {e}"
            }
        finally:
            conn.close()

    def update_lged_hierarchy(self, hierarchy, edition_year, notes=None):
        """
        UPDATE existing active version (replaces data, no version increment)
        """
        from datetime import date
        
        self.migrate_lged_tables_for_parent_types()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get the active version
            cursor.execute("""
                SELECT id, version_number FROM rate_versions 
                WHERE source = 'LGED' AND edition_year = ? AND is_active = 1
            """, (edition_year,))
            
            result = cursor.fetchone()
            if not result:
                return {
                    'success': False,
                    'error': f"No active version found for LGED {edition_year}",
                    'mode': 'update_existing',
                    'message': f"❌ No active version found. Please do a first-time import first."
                }
            
            version_id = result[0]
            current_version = result[1]
            
            # Clear existing data for this version
            cursor.execute("DELETE FROM lged_zone_rates WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM lged_children WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM lged_parents WHERE version_id = ?", (version_id,))
            
            # Insert the new/updated data
            section_headers = hierarchy.get('section_headers', [])
            leaf_items = hierarchy.get('leaf_items', [])
            children = hierarchy.get('children', [])
            
            parent_ids = {}
            
            # Save section headers
            for header in section_headers:
                cursor.execute("""
                    INSERT INTO lged_parents (code, description, chapter_number, section_number, 
                                            parent_type, has_children, version_id)
                    VALUES (?, ?, ?, ?, 'section_header', ?, ?)
                """, (header['code'], header.get('description', ''), 
                    header.get('chapter_number', ''), header.get('section_number', ''),
                    1 if header.get('has_children') else 0, version_id))
                parent_ids[header['code']] = cursor.lastrowid
            
            # Save leaf items
            for leaf in leaf_items:
                cursor.execute("""
                    INSERT INTO lged_parents (code, description, chapter_number, section_number, 
                                            parent_type, has_children, unit, version_id)
                    VALUES (?, ?, ?, ?, 'leaf_item', 0, ?, ?)
                """, (leaf['code'], leaf.get('description', ''), 
                    leaf.get('chapter_number', ''), leaf.get('section_number', ''),
                    leaf.get('unit', ''), version_id))
                parent_id = cursor.lastrowid
                parent_ids[leaf['code']] = parent_id
                
                for zone, rate in leaf.get('rates', {}).items():
                    cursor.execute("""
                        INSERT INTO lged_zone_rates (parent_id, zone_name, unit_rate, version_id)
                        VALUES (?, ?, ?, ?)
                    """, (parent_id, zone, rate, version_id))
            
            # Save child items
            for child in children:
                cursor.execute("""
                    INSERT INTO lged_children (code, parent_code, description, unit, 
                                            chapter_number, section_number,
                                            zone_a, zone_b, zone_c, zone_d,
                                            edition_year, version_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (child['code'], child.get('parent_code', ''), child.get('description', ''), 
                    child.get('unit', ''),
                    child.get('chapter_number', ''), child.get('section_number', ''),
                    child.get('zone_a'), child.get('zone_b'), 
                    child.get('zone_c'), child.get('zone_d'),
                    edition_year, version_id))
            
            # Update version record
            cursor.execute("""
                UPDATE rate_versions 
                SET total_parents = ?, total_children = ?, total_rates = ?,
                    updated_at = ?, notes = ?
                WHERE id = ?
            """, (len(section_headers) + len(leaf_items), len(children), 
                len(leaf_items) + len(children),
                datetime.now(), notes or "Updated via import", version_id))
            
            conn.commit()
            
            return {
                'success': True,
                'version_id': version_id,
                'version_number': current_version,
                'mode': 'update_existing',
                'message': f"✅ Updated existing version {current_version} for LGED {edition_year}"
            }
            
        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'error': str(e),
                'mode': 'update_existing',
                'message': f"❌ Failed to update: {e}"
            }
        finally:
            conn.close()

    def add_items_to_lged_version(self, items, edition_year, conflict_handling='skip'):
        """
        Add new items only to existing version (selective update)
        
        Args:
            items: List of new items to add
            edition_year: Edition year
            conflict_handling: 'skip', 'replace', or 'error'
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get active version
            cursor.execute("""
                SELECT id FROM rate_versions 
                WHERE source = 'LGED' AND edition_year = ? AND is_active = 1
            """, (edition_year,))
            
            result = cursor.fetchone()
            if not result:
                return {
                    'success': False,
                    'error': f"No active version found for LGED {edition_year}",
                    'mode': 'add_items',
                    'message': "❌ No active version found"
                }
            
            version_id = result[0]
            
            added = 0
            skipped = 0
            
            for item in items:
                item_code = item.get('code')
                dot_count = item_code.count('.')
                
                # Check if item already exists
                if dot_count == 1:  # Parent item
                    cursor.execute("""
                        SELECT COUNT(*) FROM lged_parents 
                        WHERE code = ? AND version_id = ?
                    """, (item_code, version_id))
                    exists = cursor.fetchone()[0] > 0
                    
                    if exists:
                        if conflict_handling == 'skip':
                            skipped += 1
                            continue
                        elif conflict_handling == 'replace':
                            # Delete existing
                            cursor.execute("""
                                DELETE FROM lged_parents 
                                WHERE code = ? AND version_id = ?
                            """, (item_code, version_id))
                        else:
                            return {'success': False, 'error': f"Item {item_code} already exists"}
                    
                    # Insert new parent
                    cursor.execute("""
                        INSERT INTO lged_parents (code, description, chapter_number, section_number,
                                                parent_type, has_children, unit, version_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (item_code, item.get('description', ''), item.get('chapter_number', ''),
                        item.get('section_number', ''), item.get('parent_type', 'leaf_item'),
                        0, item.get('unit', ''), version_id))
                    added += 1
                    
                elif dot_count == 2:  # Child item
                    cursor.execute("""
                        SELECT COUNT(*) FROM lged_children 
                        WHERE code = ? AND version_id = ?
                    """, (item_code, version_id))
                    exists = cursor.fetchone()[0] > 0
                    
                    if exists:
                        if conflict_handling == 'skip':
                            skipped += 1
                            continue
                        elif conflict_handling == 'replace':
                            cursor.execute("""
                                DELETE FROM lged_children 
                                WHERE code = ? AND version_id = ?
                            """, (item_code, version_id))
                        else:
                            return {'success': False, 'error': f"Item {item_code} already exists"}
                    
                    # Insert new child
                    cursor.execute("""
                        INSERT INTO lged_children (code, parent_code, description, unit,
                                                chapter_number, section_number,
                                                zone_a, zone_b, zone_c, zone_d,
                                                edition_year, version_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (item_code, item.get('parent_code', ''), item.get('description', ''),
                        item.get('unit', ''), item.get('chapter_number', ''),
                        item.get('section_number', ''), item.get('zone_a'), item.get('zone_b'),
                        item.get('zone_c'), item.get('zone_d'), edition_year, version_id))
                    added += 1
            
            # Update version statistics
            cursor.execute("""
                SELECT COUNT(*) FROM lged_parents WHERE version_id = ?
            """, (version_id,))
            total_parents = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM lged_children WHERE version_id = ?
            """, (version_id,))
            total_children = cursor.fetchone()[0]
            
            cursor.execute("""
                UPDATE rate_versions 
                SET total_parents = ?, total_children = ?, updated_at = ?
                WHERE id = ?
            """, (total_parents, total_children, datetime.now(), version_id))
            
            conn.commit()
            
            return {
                'success': True,
                'version_id': version_id,
                'added': added,
                'skipped': skipped,
                'mode': 'add_items',
                'message': f"✅ Added {added} new items ({skipped} skipped)"
            }
            
        except Exception as e:
            conn.rollback()
            return {
                'success': False,
                'error': str(e),
                'mode': 'add_items',
                'message': f"❌ Failed to add items: {e}"
            }
        finally:
            conn.close()
    def get_version_with_structure(self, version_id: int) -> Dict:
        """
        Get complete version data including chapters, sections, and items.
        
        Args:
            version_id: The version ID to retrieve
            
        Returns:
            Dict with version, chapters, sections, and items
        """
        conn = self.get_connection()
        
        try:
            # Get version info
            version_df = pd.read_sql_query(
                "SELECT * FROM rate_versions WHERE id = ?",
                conn, params=[version_id]
            )
            
            if version_df.empty:
                return None
            
            version = version_df.to_dict('records')[0]
            source = version['source']
            
            # Get chapters
            chapters = pd.read_sql_query("""
                SELECT * FROM rate_chapters 
                WHERE version_id = ? AND source = ?
                ORDER BY display_order, chapter_number
            """, conn, params=[version_id, source]).to_dict('records')
            
            # Get sections (if LGED and has sections)
            sections = []
            if source == 'LGED' and version.get('has_sections'):
                sections = pd.read_sql_query("""
                    SELECT s.*, c.chapter_number 
                    FROM rate_sections s
                    JOIN rate_chapters c ON s.chapter_id = c.id
                    WHERE s.version_id = ? AND s.source = ?
                    ORDER BY s.display_order, s.section_number
                """, conn, params=[version_id, source]).to_dict('records')
            
            # Get items based on source
            if source == 'LGED':
                items = pd.read_sql_query("""
                    SELECT c.*, ch.chapter_number, s.section_number,
                        z.zone_name, z.unit_rate
                    FROM lged_children c
                    LEFT JOIN rate_chapters ch ON c.chapter_id = ch.id
                    LEFT JOIN rate_sections s ON c.section_id = s.id
                    LEFT JOIN lged_zone_rates z ON c.id = z.child_id
                    WHERE c.version_id = ?
                    ORDER BY c.code
                """, conn, params=[version_id]).to_dict('records')
            else:  # PWD
                items = pd.read_sql_query("""
                    SELECT c.*, ch.chapter_number,
                        r.zone_name, r.unit_rate
                    FROM pwd_children c
                    LEFT JOIN rate_chapters ch ON c.chapter_id = ch.id
                    LEFT JOIN pwd_rates r ON c.pwd_code = r.pwd_code AND r.version_id = c.version_id
                    WHERE c.version_id = ?
                    ORDER BY c.pwd_code
                """, conn, params=[version_id]).to_dict('records')
            
            return {
                'version': version,
                'chapters': chapters,
                'sections': sections,
                'items': items
            }
            
        except Exception as e:
            print(f"Error getting version structure: {e}")
            return None
        finally:
            conn.close()

    def get_chapters_by_source(self, source: str, version_id: int = None) -> pd.DataFrame:
        """
        Get chapters for a specific source, optionally filtered by version.
        
        Args:
            source: 'PWD' or 'LGED'
            version_id: Optional version ID to filter by
        
        Returns:
            DataFrame with chapters
        """
        conn = self.get_connection()
        
        if version_id:
            query = """
                SELECT * FROM rate_chapters 
                WHERE source = ? AND version_id = ?
                ORDER BY display_order, chapter_number
            """
            df = pd.read_sql_query(query, conn, params=[source, version_id])
        else:
            query = """
                SELECT DISTINCT chapter_number, chapter_name, description
                FROM rate_chapters 
                WHERE source = ?
                ORDER BY CAST(chapter_number AS INTEGER)
            """
            df = pd.read_sql_query(query, conn, params=[source])
        
        conn.close()
        return df

    def get_sections_by_chapter(self, source: str, version_id: int, chapter_id: int) -> pd.DataFrame:
        """
        Get sections for a specific chapter (LGED only).
        
        Args:
            source: Must be 'LGED'
            version_id: Version ID
            chapter_id: Chapter ID
        
        Returns:
            DataFrame with sections
        """
        if source != 'LGED':
            return pd.DataFrame()
        
        conn = self.get_connection()
        df = pd.read_sql_query("""
            SELECT * FROM rate_sections 
            WHERE source = ? AND version_id = ? AND chapter_id = ?
            ORDER BY display_order, section_number
        """, conn, params=[source, version_id, chapter_id])
        conn.close()
        return df

    def _is_float(self, value):
        """Helper method to check if string can be converted to float"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    
    def get_pwd_chapters(self):
        """Get all PWD chapters"""
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT chapter_number, chapter_name, description FROM pwd_chapters ORDER BY CAST(chapter_number AS INTEGER)", conn)
        conn.close()
        return df


    def get_lged_chapters(self):
        """Get all LGED chapters"""
        try:
            conn = self.get_connection()
            df = pd.read_sql_query("""
                SELECT chapter_number, chapter_name 
                FROM lged_chapters 
                ORDER BY CAST(chapter_number AS INTEGER)
            """, conn)
            conn.close()
            return df
        except Exception as e:
            # Return default chapters if table doesn't exist
            return pd.DataFrame([
                {"chapter_number": "1", "chapter_name": "General, Site Facilities and Safety"},
                {"chapter_number": "2", "chapter_name": "Earth Works in Road Embankment"},
                {"chapter_number": "3", "chapter_name": "Sub-Base and Base Course"},
                {"chapter_number": "4", "chapter_name": "Bituminous Pavement"},
                {"chapter_number": "5", "chapter_name": "Bridge and Culvert Works"},
                {"chapter_number": "6", "chapter_name": "Building Works"},
                {"chapter_number": "7", "chapter_name": "Sanitary and Water Supply"},
                {"chapter_number": "8", "chapter_name": "Electrical Works"},
                {"chapter_number": "9", "chapter_name": "Landscaping and Development"}
            ])



    def add_pwd_chapter(self, chapter_number, chapter_name, description=""):
        """Add a new PWD chapter"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO pwd_chapters (chapter_number, chapter_name, description)
            VALUES (?, ?, ?)
        """, (chapter_number, chapter_name, description))
        conn.commit()
        conn.close()

    def save_pwd_hierarchy_enhanced(self, hierarchy, version_name, edition_year, 
                                effective_date=None, selected_chapters=None):
        """
        Save PWD hierarchy with chapter support (PWD doesn't have sections).
        Auto-increments version number for each new version.
        """
        from datetime import date
        import json
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        effective_date = effective_date or date.today()
        
        try:
            # Get the next version number
            cursor.execute("""
                SELECT MAX(version_number) FROM rate_versions 
                WHERE source = 'PWD' AND edition_year = ?
            """, (edition_year,))
            
            result = cursor.fetchone()
            next_version = (result[0] or 0) + 1
            
            # Deactivate current active version
            cursor.execute("""
                UPDATE rate_versions 
                SET is_active = 0, updated_at = ?
                WHERE source = 'PWD' AND edition_year = ? AND is_active = 1
            """, (datetime.now(), edition_year))
            
            # Create version record
            cursor.execute("""
                INSERT INTO rate_versions (
                    source, version_name, edition_year, version_number,
                    effective_from, is_active, release_date, created_by, 
                    has_sections, created_at
                ) VALUES ('PWD', ?, ?, ?, ?, 1, ?, ?, 0, ?)
            """, (version_name, edition_year, next_version, effective_date, 
                datetime.now(), 'system', datetime.now()))
            
            version_id = cursor.lastrowid
            print(f"✅ Created version {next_version} for PWD {edition_year}")
            
            chapter_ids = {}
            
            # Save chapters to rate_chapters
            chapters_saved = 0
            if selected_chapters:
                for chapter_num, chapter_info in selected_chapters.items():
                    cursor.execute("""
                        INSERT INTO rate_chapters (
                            source, version_id, chapter_number, 
                            chapter_name, description, display_order
                        ) VALUES ('PWD', ?, ?, ?, ?, ?)
                    """, (version_id, chapter_num, chapter_info.get('name', f'Chapter {chapter_num}'),
                        chapter_info.get('description', ''), int(chapter_num) if chapter_num.isdigit() else 999))
                    chapter_ids[chapter_num] = cursor.lastrowid
                    chapters_saved += 1
            
            # Save parents to pwd_parents
            parents_saved = 0
            for parent in hierarchy.get('parents', []):
                chapter_num = parent.get('chapter_number', parent.get('chapter', parent['code']))
                
                cursor.execute("""
                    INSERT INTO pwd_parents (pwd_code, description, chapter_number, version_id)
                    VALUES (?, ?, ?, ?)
                """, (parent['code'], parent.get('description', ''), chapter_num, version_id))
                parents_saved += 1
            
            # Save children to pwd_children - handle NOT NULL constraint
            children_saved = 0
            rates_saved = 0
            
            for child in hierarchy.get('children', []):
                code = child.get('pwd_code') or child.get('code')
                if not code:
                    continue
                
                # Handle parent_code NOT NULL constraint
                parent_code = child.get('parent_code')
                if parent_code is None or parent_code == '':
                    # For leaf items, use empty string (if allowed) or a default value
                    parent_code = ''  # Try empty string first
                    # If empty string fails, use: parent_code = code (self-reference)
                
                cursor.execute("""
                    INSERT INTO pwd_children (
                        pwd_code, parent_code, description, unit, 
                        edition_year, version_id
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (code, parent_code, child.get('description', ''), 
                    child.get('unit', ''), edition_year, version_id))
                children_saved += 1
                
                # Save rates
                for zone, rate in child.get('rates', {}).items():
                    cursor.execute("""
                        INSERT INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year, version_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (code, zone, rate, edition_year, version_id))
                    rates_saved += 1
            
            # Update version record with statistics
            cursor.execute("""
                UPDATE rate_versions 
                SET total_parents = ?, total_children = ?, total_rates = ?,
                    chapter_numbers = ?
                WHERE id = ?
            """, (parents_saved, children_saved, rates_saved,
                json.dumps(list(chapter_ids.keys())), version_id))
            
            conn.commit()
            
            print(f"✅ Saved PWD hierarchy: {chapters_saved} chapters, "
                f"{parents_saved} parents, {children_saved} children, {rates_saved} rates")
            
            return version_id
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error saving PWD hierarchy: {e}")
            import traceback
            traceback.print_exc()
            raise e
        finally:
            conn.close()


    def save_pwd_hierarchy(self, hierarchy, edition_year, version_name=None):
        """
        Save PWD hierarchy to database with version number support.
        """
        from datetime import date
        
        self.init_pwd_hierarchical_tables()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create version if new
        if version_name is None:
            version_name = f"PWD Schedule {edition_year}"
        
        # Check if rate_versions table has all columns
        cursor.execute("PRAGMA table_info(rate_versions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'source' not in columns:
            cursor.execute("ALTER TABLE rate_versions ADD COLUMN source TEXT DEFAULT 'PWD'")
        if 'total_parents' not in columns:
            cursor.execute("ALTER TABLE rate_versions ADD COLUMN total_parents INTEGER DEFAULT 0")
        if 'total_children' not in columns:
            cursor.execute("ALTER TABLE rate_versions ADD COLUMN total_children INTEGER DEFAULT 0")
        if 'total_rates' not in columns:
            cursor.execute("ALTER TABLE rate_versions ADD COLUMN total_rates INTEGER DEFAULT 0")
        if 'created_by' not in columns:
            cursor.execute("ALTER TABLE rate_versions ADD COLUMN created_by TEXT")
        if 'version_number' not in columns:
            cursor.execute("ALTER TABLE rate_versions ADD COLUMN version_number INTEGER DEFAULT 1")
        if 'created_at' not in columns:
            cursor.execute("ALTER TABLE rate_versions ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        if 'updated_at' not in columns:
            cursor.execute("ALTER TABLE rate_versions ADD COLUMN updated_at TIMESTAMP")
        
        # Get the next version number
        cursor.execute("""
            SELECT MAX(version_number) FROM rate_versions 
            WHERE source = 'PWD' AND edition_year = ?
        """, (edition_year,))
        
        result = cursor.fetchone()
        next_version = (result[0] or 0) + 1
        
        # Deactivate current active version
        cursor.execute("""
            UPDATE rate_versions 
            SET is_active = 0, updated_at = ?
            WHERE source = 'PWD' AND edition_year = ? AND is_active = 1
        """, (datetime.now(), edition_year))
        
        # Create version record
        cursor.execute("""
            INSERT INTO rate_versions (
                source, version_name, edition_year, version_number, 
                effective_from, is_active, release_date, created_by, created_at
            ) VALUES ('PWD', ?, ?, ?, ?, 1, ?, ?, ?)
        """, (version_name, edition_year, next_version, date.today(), 
            datetime.now(), 'system', datetime.now()))
        
        version_id = cursor.lastrowid
        
        # Clear existing data for this version
        cursor.execute("DELETE FROM pwd_rates WHERE version_id = ?", (version_id,))
        cursor.execute("DELETE FROM pwd_children WHERE version_id = ?", (version_id,))
        cursor.execute("DELETE FROM pwd_parents WHERE version_id = ?", (version_id,))
        
        # Save parents
        parents_saved = 0
        for parent in hierarchy.get('parents', []):
            cursor.execute("""
                INSERT INTO pwd_parents (pwd_code, description, chapter_number, version_id)
                VALUES (?, ?, ?, ?)
            """, (parent['code'], parent.get('description', ''), parent.get('chapter', parent['code']), version_id))
            parents_saved += 1
        
        # Save children and rates
        children_saved = 0
        rates_saved = 0
        
        for child in hierarchy.get('children', []):
            # Determine chapter from code
            code = child['pwd_code']
            chapter_num = code.split('.')[0] if '.' in code else code
            
            # Get chapter_id from rate_chapters if exists
            chapter_id = None
            cursor.execute("""
                SELECT id FROM rate_chapters 
                WHERE source = 'PWD' AND chapter_number = ? AND version_id = ?
            """, (chapter_num, version_id))
            chapter_row = cursor.fetchone()
            if chapter_row:
                chapter_id = chapter_row[0]
            
            cursor.execute("""
                INSERT INTO pwd_children (
                    pwd_code, parent_code, description, unit, 
                    edition_year, version_id, chapter_id, is_parent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, child.get('parent_code', ''), child.get('description', ''), 
                child.get('unit', ''), edition_year, version_id, chapter_id, 0))
            children_saved += 1
            
            for zone, rate in child.get('rates', {}).items():
                cursor.execute("""
                    INSERT INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year, version_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (code, zone, rate, edition_year, version_id))
                rates_saved += 1
        
        # Update version record with statistics
        cursor.execute("""
            UPDATE rate_versions 
            SET total_parents = ?, total_children = ?, total_rates = ?
            WHERE id = ?
        """, (parents_saved, children_saved, rates_saved, version_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Saved PWD hierarchy: {parents_saved} parents, {children_saved} children, {rates_saved} rates")
        
        return {
            'parents': parents_saved, 
            'children': children_saved, 
            'rates': rates_saved,
            'version_id': version_id,
            'version_number': next_version
        }
    def add_lged_chapter(self, chapter_number, chapter_name, description=""):
        """Add a new LGED chapter"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO lged_chapters (chapter_number, chapter_name, description)
            VALUES (?, ?, ?)
        """, (chapter_number, chapter_name, description))
        conn.commit()
        conn.close()    

    def save_lged_hierarchy(self, hierarchy, version_name, edition_year, effective_date=None):
        """Save LGED hierarchy to database"""
        from datetime import date
        
        self.init_lged_tables()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        effective_date = effective_date or date.today()
        
        # Create version record with all required columns
        cursor.execute("""
            INSERT INTO rate_versions (source, version_name, edition_year, effective_from, is_active, release_date, created_by)
            VALUES ('LGED', ?, ?, ?, 1, ?, ?)
        """, (version_name, edition_year, effective_date, datetime.now(), 'system'))
        
        version_id = cursor.lastrowid
        
        # Insert parents
        parents_saved = 0
        for parent in hierarchy.get('parents', []):
            cursor.execute("""
                INSERT INTO lged_parents (code, description, chapter_number, version_id)
                VALUES (?, ?, ?, ?)
            """, (parent['code'], parent['description'], parent['chapter'], version_id))
            parents_saved += 1
        
        # Insert children
        children_saved = 0
        rates_saved = 0
        
        for child in hierarchy.get('children', []):
            cursor.execute("""
                INSERT INTO lged_children (code, parent_code, description, unit, edition_year, version_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (child['code'], child['parent_code'], child['description'], 
                child.get('unit', ''), edition_year, version_id))
            child_id = cursor.lastrowid
            children_saved += 1
            
            # Insert zone rates
            for zone, rate in child.get('rates', {}).items():
                cursor.execute("""
                    INSERT INTO lged_zone_rates (child_id, zone_name, unit_rate, version_id)
                    VALUES (?, ?, ?, ?)
                """, (child_id, zone, rate, version_id))
                rates_saved += 1
        
        # Update version record with statistics
        cursor.execute("""
            UPDATE rate_versions 
            SET total_parents = ?, total_children = ?, total_rates = ?
            WHERE id = ?
        """, (parents_saved, children_saved, rates_saved, version_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Saved LGED hierarchy: {parents_saved} parents, {children_saved} children, {rates_saved} rates")
        
        return version_id

    def get_lged_active_version(self):
        """Get active LGED version"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, version_name, edition_year, effective_from
            FROM rate_versions 
            WHERE is_active = 1 
            ORDER BY edition_year DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'version_name': result[1],
                'edition_year': result[2],
                'effective_from': result[3]
            }
        return None


    def get_lged_rate(self, code, zone="Zone-A"):
        """Get LGED rate for specific item code and zone"""
        active = self.get_lged_active_version()
        if not active:
            return None
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.unit_rate 
            FROM lged_zone_rates r
            JOIN lged_children c ON r.child_id = c.id
            WHERE c.code = ? AND r.zone_name = ? AND c.version_id = ?
            LIMIT 1
        """, (code, zone, active['id']))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    

    def get_pwd_stats(self):
        """Get PWD statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM pwd_parents")
        total_parents = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pwd_children")
        total_children = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pwd_rates")
        total_rates = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_parents': total_parents,
            'total_children': total_children,
            'total_rates': total_rates,
            'total_items': total_parents + total_children
        }


    def get_pwd_children(self, parent_code=None, limit=100):
        """Get PWD child items, optionally filtered by parent"""
        conn = self.get_connection()
        
        if parent_code:
            df = pd.read_sql_query("""
                SELECT c.pwd_code, c.description, c.unit, c.edition_year,
                    r.zone_name, r.unit_rate
                FROM pwd_children c
                LEFT JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                WHERE c.parent_code = ?
                ORDER BY c.pwd_code, r.zone_name
                LIMIT ?
            """, conn, params=(parent_code, limit))
        else:
            df = pd.read_sql_query("""
                SELECT c.pwd_code, c.description, c.unit, c.edition_year,
                    r.zone_name, r.unit_rate
                FROM pwd_children c
                LEFT JOIN pwd_rates r ON c.pwd_code = r.pwd_code
                ORDER BY c.pwd_code, r.zone_name
                LIMIT ?
            """, conn, params=(limit,))
        
        conn.close()
        return df


    def search_pwd_items(self, search_term, limit=50):
        """Search PWD items by code or description"""
        conn = self.get_connection()
        df = pd.read_sql_query("""
            SELECT pwd_code, description, unit 
            FROM pwd_children 
            WHERE pwd_code LIKE ? OR description LIKE ?
            LIMIT ?
        """, conn, params=(f"%{search_term}%", f"%{search_term}%", limit))
        conn.close()

    def clear_pwd_version_data(self, version_id):
        """Clear all PWD data for a specific version"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Delete in correct order (child tables first due to foreign keys)
            cursor.execute("DELETE FROM pwd_rates WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM pwd_children WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM pwd_parents WHERE version_id = ?", (version_id,))
            
            conn.commit()
            conn.close()
            print(f"✅ Cleared PWD data for version ID: {version_id}")
            return True
            
        except Exception as e:
            print(f"Error clearing PWD version data: {e}")
            return False


    def clear_lged_version_data(self, version_id):
        """Clear all LGED data for a specific version"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Delete in correct order (child tables first due to foreign keys)
            cursor.execute("DELETE FROM lged_zone_rates WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM lged_children WHERE version_id = ?", (version_id,))
            cursor.execute("DELETE FROM lged_parents WHERE version_id = ?", (version_id,))
            
            conn.commit()
            conn.close()
            print(f"✅ Cleared LGED data for version ID: {version_id}")
            return True
            
        except Exception as e:
            print(f"Error clearing LGED version data: {e}")
            return False

    def _tables_exist(self):
        """Check if database tables already exist"""
        conn = self.get_connection()        
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def get_connection(self):
        """Get a fresh SQLite connection with FK enforcement"""
        import os
        conn = sqlite3.connect(self.db_path)
        #print(f"🗄️ APP DB PATH: {os.path.abspath(self.db_path)}")  # Adjust variable name to match yours
        conn.row_factory = sqlite3.Row  # Optional: enables dict-like access
        #conn.execute("PRAGMA foreign_keys = ON;")        
        
        return conn
        
    
    
    # ==================== AUTHENTICATION METHODS ====================
    def store_password_reset_token(self, email: str, token: str, expires_in_minutes: int = 60):
        """Store password reset token"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            expires_at = (datetime.now() + timedelta(minutes=expires_in_minutes)).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT OR REPLACE INTO password_reset_tokens 
                (email, token, expires_at) 
                VALUES (?, ?, ?)
            ''', (email, token, expires_at))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to store reset token: {e}")
            return False
        finally:
            conn.close()

    def verify_reset_token(self, token: str):
        """Verify reset token and return email if valid"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT email FROM password_reset_tokens 
                WHERE token = ? AND expires_at > ?
            ''', (token, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

    def update_password(self, email: str, new_password: str):
        """Update user password with bcrypt"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute("UPDATE users SET password = ? WHERE email = ?", (hashed, email))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def authenticate_user(self, username, password):
        """Improved authentication with clear error messages"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT u.id, u.username, u.email, u.full_name, u.role, u.is_active, 
                u.company_id, u.password, u.last_login, u.is_approved, u.account_type
            FROM users u
            WHERE (u.username = ? OR u.email = ?)
            ''', (username, username))
            
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                return None, "invalid_credentials", "❌ Username or email not found."

            is_active = user[5]
            if not is_active:
                conn.close()
                return None, "inactive", "⚠️ Your account is inactive. Please contact support."

            stored_pass = user[7]  # password column
            
            password_match = False
            error_message = "❌ Invalid password."
            
            if stored_pass and password:
                try:
                    if str(stored_pass).startswith('$2b$') or str(stored_pass).startswith('$2y$'):
                        # bcrypt hash
                        import bcrypt
                        password_match = bcrypt.checkpw(
                            password.encode('utf-8'), 
                            str(stored_pass).encode('utf-8')
                        )
                    else:
                        # Legacy SHA256
                        import hashlib
                        hashed_input = hashlib.sha256(password.encode()).hexdigest()
                        password_match = (hashed_input == stored_pass)
                except Exception as e:
                    print(f"Hash verification error: {e}")
                    password_match = False

            if not password_match:
                conn.close()
                return None, "invalid_password", error_message

            # Success - update last login
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (now_str, user[0]))
            conn.commit()
            conn.close()
            
            status = "approved" if user[9] else "pending_approval"
            return user, status, "success"

        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            return None, "auth_error", "❌ System error during login. Please try again."


    
    def create_user(self, company_id, user_data, created_by):
        """Create a new user with pending approval"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        hashed_pass = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            cursor.execute('''
                INSERT INTO users (
                    company_id, username, password, email, full_name, phone, role,
                    is_active, created_by, is_approved, account_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    company_id, user_data['username'], hashed_pass, user_data['email'],
                    user_data['full_name'], user_data.get('phone', ''), user_data.get('role', 'user'),
                    1, created_by, 0,  # is_approved = 0 (pending)
                    user_data.get('account_type', 'company')
                ))
            user_id = cursor.lastrowid
            
            # Create subscription record (pending approval)
            cursor.execute('''
            INSERT INTO subscriptions (user_id, plan, status, analyses_limit)
            VALUES (?, 'free', 'pending_approval', 0)
            ''', (user_id,))
            
            conn.commit()
            
            # Log the registration
            self.log_team_activity(company_id, user_id, "registration", "user", str(user_id), 
                                f"New user registration pending approval: {user_data['username']}")
            
            return True, user_id
        except sqlite3.IntegrityError as e:
            return False, str(e)
        finally:
            conn.close()

    
    # ==================== USER MANAGEMENT METHODS ====================
    
    def get_all_users(self, company_id=None, role=None):
        """Get all users as dictionaries"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
            u.created_at, u.last_login, c.company_name, u.is_approved
        FROM users u
        JOIN companies c ON u.company_id = c.id
        WHERE 1=1
        '''
        params = []
        
        if company_id:
            query += " AND u.company_id = ?"
            params.append(company_id)
        if role:
            query += " AND u.role = ?"
            params.append(role)
        
        query += " ORDER BY u.created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        users = []
        for row in rows:
            users.append({
                'id': row[0], 'username': row[1], 'email': row[2], 'full_name': row[3],
                'phone': row[4], 'role': row[5], 'is_active': row[6],
                'created_at': row[7], 'last_login': row[8], 'company_name': row[9],
                'is_approved': row[10] if len(row) > 10 else 1
            })
        return users

    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT u.*, c.company_name, c.id as company_id
        FROM users u
        JOIN companies c ON u.company_id = c.id
        WHERE u.id = ?
        ''', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def update_user_role(self, user_id, new_role, updated_by):
        """Update user role"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
        conn.commit()
        conn.close()
        return True
    
    def update_user_status(self, user_id, is_active):
        """Activate/deactivate user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (is_active, user_id))
        conn.commit()
        conn.close()
    
    def delete_user_bak(self, user_id):
        """Delete user (non-admin only)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ? AND role != "admin"', (user_id,))
        cursor.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    # ==================== SUBSCRIPTION METHODS ====================
    
    def get_user_subscription(self, user_id):
        """Get user's subscription details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT plan, status, start_date, end_date, analyses_used, analyses_limit
        FROM subscriptions WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'plan': result[0],
                'status': result[1],
                'start_date': result[2],
                'end_date': result[3],
                'analyses_used': result[4] or 0,
                'analyses_limit': result[5] or 5
            }
        return {'plan': 'free', 'status': 'active', 'analyses_used': 0, 'analyses_limit': 5}
    
    def get_effective_subscription(self, user_id: int, company_id: Optional[int] = None) -> Dict[str, Any]:
        """Resolve subscription with NULL-safe queries"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Priority 1: Company subscription (only if company_id provided)
            if company_id:
                cursor.execute('''
                SELECT plan, status, analyses_used, analyses_limit 
                FROM subscriptions 
                WHERE company_id = ? AND status = 'active' AND company_id IS NOT NULL
                LIMIT 1
                ''', (company_id,))
                row = cursor.fetchone()
                if row and row[1] == 'active':
                    conn.close()
                    return {
                        'owner_type': 'company', 'owner_id': company_id,
                        'plan': row[0] or 'free', 'status': 'active',
                        'analyses_used': row[2] or 0, 'analyses_limit': row[3] or 5
                    }
            
            # Priority 2: Personal/consultant subscription
            cursor.execute('''
            SELECT plan, status, analyses_used, analyses_limit 
            FROM subscriptions 
            WHERE user_id = ? AND status = 'active' AND user_id IS NOT NULL
            LIMIT 1
            ''', (user_id,))
            row = cursor.fetchone()
            if row and row[1] == 'active':
                conn.close()
                return {
                    'owner_type': 'user', 'owner_id': user_id,
                    'plan': row[0] or 'free', 'status': 'active',
                    'analyses_used': row[2] or 0, 'analyses_limit': row[3] or 5
                }
                
            conn.close()
            return {'owner_type': 'free', 'plan': 'free', 'status': 'active', 
                    'analyses_used': 0, 'analyses_limit': 5}
                    
        except Exception as e:
            logger.error(f"Subscription lookup error: {e}")
            return {'owner_type': 'free', 'plan': 'free', 'analyses_used': 0, 'analyses_limit': 5}
    
    def update_subscription(self, user_id, plan, duration='monthly', payment_method=None, transaction_id=None):
        """Update user's subscription"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        start_date = datetime.now().date()
        
        plan_limits = {
            'free': {'limit': 5},
            'basic': {'limit': 30},
            'professional': {'limit': -1},
            'enterprise': {'limit': -1}
        }
        
        if duration == 'monthly':
            end_date = start_date + timedelta(days=30)
        else:
            end_date = start_date + timedelta(days=365)
        
        # Check if subscription exists
        cursor.execute('SELECT id FROM subscriptions WHERE user_id = ?', (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute('''
            UPDATE subscriptions 
            SET plan = ?, status = 'active', start_date = ?, end_date = ?, 
                analyses_limit = ?, payment_method = ?, transaction_id = ?, updated_at = ?
            WHERE user_id = ?
            ''', (plan, start_date, end_date, plan_limits[plan]['limit'], 
                  payment_method, transaction_id, datetime.now(), user_id))
        else:
            cursor.execute('''
            INSERT INTO subscriptions (user_id, plan, status, start_date, end_date, 
                                       analyses_limit, payment_method, transaction_id)
            VALUES (?, ?, 'active', ?, ?, ?, ?, ?)
            ''', (user_id, plan, start_date, end_date, plan_limits[plan]['limit'], 
                  payment_method, transaction_id))
        
        conn.commit()
        conn.close()
        return True
    
    def increment_analysis_usage(self, user_id):
        """Increment analysis counter"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE subscriptions SET analyses_used = analyses_used + 1 
        WHERE user_id = ? AND analyses_limit != -1
        ''', (user_id,))
        conn.commit()
        conn.close()
    
    def can_perform_analysis(self, user_id):
        """Check if user can perform an analysis"""
        sub = self.get_user_subscription(user_id)
        if sub['analyses_limit'] == -1:
            return True, "Unlimited"
        remaining = sub['analyses_limit'] - sub['analyses_used']
        return remaining > 0, remaining
    
    def get_all_subscriptions(self):
        """Get all subscriptions for admin"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT s.*, u.username, u.email, u.full_name, c.company_name
        FROM subscriptions s
        JOIN users u ON s.user_id = u.id
        JOIN companies c ON u.company_id = c.id
        ORDER BY s.updated_at DESC
        ''')
        subs = cursor.fetchall()
        conn.close()
        return subs
    
    def log_team_activity(self, company_id: int, actor_user_id: int, 
                     action_type: str, target_type: str, target_id: str,
                     details: str = None) -> bool:
        """Log team management activity for audit trail."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO activity_logs (
                company_id, actor_user_id, action_type, target_type, 
                target_id, details, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_id,
                actor_user_id,
                action_type,
                target_type,
                target_id,
                details,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            return False

    # ==================== TENDER ANALYSIS METHODS ====================
    
    def save_analysis(self, user_id, company_id, analysis_data):
        """Save tender analysis to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get existing columns in the table
            cursor.execute("PRAGMA table_info(tender_analyses)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            
            # Prepare competitor bids as JSON if present
            competitor_bids_json = None
            if 'competitor_bids' in analysis_data and analysis_data['competitor_bids']:
                import json
                competitor_bids_json = json.dumps(analysis_data['competitor_bids'])
            
            # Base fields that should always exist
            base_fields = [
                'user_id', 'company_id', 'tender_id', 'tender_title', 'procuring_entity',
                'division', 'district', 'thana', 'construction_type', 'official_estimate',
                'recommended_bid', 'success_probability', 'risk_level', 'competitor_count',
                'bid_status', 'analysis_date'
            ]
            
            base_values = [
                user_id, company_id,
                analysis_data.get('tender_id', ''),
                analysis_data.get('tender_title', ''),
                analysis_data.get('procuring_entity', ''),
                analysis_data.get('division', ''),
                analysis_data.get('district', ''),
                analysis_data.get('thana', ''),
                analysis_data.get('construction_type', ''),
                analysis_data.get('official_estimate', 0),
                analysis_data.get('recommended_bid', 0),
                analysis_data.get('success_probability', 0),
                analysis_data.get('risk_level', 'MEDIUM'),
                analysis_data.get('competitor_count', 0),
                analysis_data.get('bid_status', 'Pending'),
                datetime.now()
            ]
            
            # Optional fields (only include if they exist in table and data)
            optional_fields = []
            optional_values = []
            
            # Check and add analysis_type
            if 'analysis_type' in existing_columns and 'analysis_type' in analysis_data:
                optional_fields.append('analysis_type')
                optional_values.append(analysis_data.get('analysis_type', 'Basic'))
            
            # Check and add competitor_bids
            if 'competitor_bids' in existing_columns:
                optional_fields.append('competitor_bids')
                optional_values.append(competitor_bids_json)
            
            # Check and add risk_strategy
            if 'risk_strategy' in existing_columns and 'risk_strategy' in analysis_data:
                optional_fields.append('risk_strategy')
                optional_values.append(analysis_data.get('risk_strategy', 'moderate'))
            
            # Check and add confidence_score
            if 'confidence_score' in existing_columns and 'confidence_score' in analysis_data:
                optional_fields.append('confidence_score')
                optional_values.append(analysis_data.get('confidence_score', 0.70))
            
            # Check and add expected_profit
            if 'expected_profit' in existing_columns and 'expected_profit' in analysis_data:
                optional_fields.append('expected_profit')
                optional_values.append(analysis_data.get('expected_profit', 0))
            
            # Check and add expected_value
            if 'expected_value' in existing_columns and 'expected_value' in analysis_data:
                optional_fields.append('expected_value')
                optional_values.append(analysis_data.get('expected_value', 0))
            
            # Check and add slt_threshold
            if 'slt_threshold' in existing_columns and 'slt_threshold' in analysis_data:
                optional_fields.append('slt_threshold')
                optional_values.append(analysis_data.get('slt_threshold', 0))
            
            # Check and add nppi_factor
            if 'nppi_factor' in existing_columns and 'nppi_factor' in analysis_data:
                optional_fields.append('nppi_factor')
                optional_values.append(analysis_data.get('nppi_factor', 0.92))
            
            # Check and add weighted_average
            if 'weighted_average' in existing_columns and 'weighted_average' in analysis_data:
                optional_fields.append('weighted_average')
                optional_values.append(analysis_data.get('weighted_average', 0))
            
            # Build the final query
            all_fields = base_fields + optional_fields
            all_values = base_values + optional_values
            placeholders = ','.join(['?' for _ in range(len(all_fields))])
            
            query = f"INSERT INTO tender_analyses ({','.join(all_fields)}) VALUES ({placeholders})"
            
            cursor.execute(query, all_values)
            
            analysis_id = cursor.lastrowid
            conn.commit()
            
            print(f"[DEBUG] Analysis saved successfully with ID: {analysis_id}")
            
            conn.close()
            return analysis_id
            
        except Exception as e:
            print(f"[DEBUG ERROR] save_analysis failed: {str(e)}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            conn.close()
            return None


    def get_pending_users(self, company_id):
        """Get all pending approval users for a company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT id, username, email, full_name, phone, role, created_at, created_by
        FROM users 
        WHERE company_id = ? AND is_approved = 0 AND registration_complete = 0 AND is_active = 1
        ORDER BY created_at ASC
        ''', (company_id,))
        users = cursor.fetchall()
        conn.close()
        return users


    def approve_user(self, user_id, approved_by):
        """Approve a pending user registration"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            UPDATE users 
            SET is_approved = 1, approved_by = ?, approved_at = ?
            WHERE id = ?
            ''', (approved_by, datetime.now(), user_id))
            
            # Update subscription to active
            cursor.execute('''
            UPDATE subscriptions 
            SET status = 'active', analyses_limit = 5
            WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error approving user: {e}")
            return False
        finally:
            conn.close()



    def reject_user(self, user_id, rejected_by):
        """Reject a pending user registration"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE users 
        SET is_active = 0, registration_complete = 0
        WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
        return True


    def is_user_approved(self, user_id):
        """Check if user is approved"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT is_approved, is_active FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0] == 1 and result[1] == 1
        return False
    
    def get_user_analyses(self, user_id, company_id, role, limit=50):
        """Get user's tender analyses with role-based filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Debug print
        print(f"🔍 get_user_analyses called with: user_id={user_id}, company_id={company_id}, role={role}")
        
        # System admin can see all analyses across all companies
        if role in ['admin', 'system_admin']:
            cursor.execute('''
                SELECT * FROM tender_analyses 
                ORDER BY analysis_date DESC LIMIT ?
            ''', (limit,))
        # Company admin and manager can see all analyses for their company
        elif role in ['company_admin', 'manager']:
            cursor.execute('''
                SELECT * FROM tender_analyses 
                WHERE company_id = ? 
                ORDER BY analysis_date DESC LIMIT ?
            ''', (company_id, limit))
        # Regular users can only see their own analyses
        else:
            cursor.execute('''
                SELECT * FROM tender_analyses 
                WHERE user_id = ? AND company_id = ?
                ORDER BY analysis_date DESC LIMIT ?
            ''', (user_id, company_id, limit))
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        print(f"🔍 Found {len(data)} analyses for role={role}, company_id={company_id}")
        
        if data:
            df = pd.DataFrame(data, columns=columns)
            
            # Parse competitor_bids JSON if present
            if 'competitor_bids' in df.columns:
                import json
                def parse_competitor_bids(value):
                    if value is None:
                        return []
                    if isinstance(value, str):
                        try:
                            if value and value != 'null':
                                return json.loads(value)
                        except:
                            pass
                    return []
                df['competitor_bids'] = df['competitor_bids'].apply(parse_competitor_bids)
            
            return df
        return pd.DataFrame()

    def get_all_companies(self) -> List[tuple]:
        """Fetch all companies from database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT id, company_name, email, phone, division, district, 
                created_at, status 
            FROM companies 
            ORDER BY company_name ASC
            ''')
            companies = cursor.fetchall()
            conn.close()
            return companies
        except Exception as e:
            logger.error(f"Failed to fetch companies: {e}")
            return []
        

    
    # ==================== CONTACT METHODS ====================
    
    def save_contact_message(self, name, email, subject, message):
        """Save contact message"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO contact_messages (name, email, subject, message)
        VALUES (?, ?, ?, ?)
        ''', (name, email, subject, message))
        conn.commit()
        conn.close()
        return True
    
    # ==================== HISTORICAL DATA METHODS ====================
    
    def save_historical_tender(self, user_id, company_id, data):
        """Save historical tender data with competitor details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO historical_tenders (
            user_id, company_id, tender_id, tender_title, procuring_entity,
            procurement_type, official_estimate, awarded_price, num_competitors,
            total_bidders, our_rank, award_date, competitors_data, 
            winning_competitor, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, company_id, data['tender_id'], data['tender_title'],
            data['procuring_entity'], data['procurement_type'], data['official_estimate'],
            data['awarded_price'], data.get('num_competitors', 0),
            data.get('total_bidders', 0), data.get('our_rank', 0),
            data['award_date'], data.get('competitors_data'), 
            data.get('winning_competitor'), data.get('notes', '')
        ))
        
        tender_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return tender_id
    
    def get_historical_tenders(self, company_id, procurement_type=None, winner_type=None, limit=100):
        """Get historical tenders with winner filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT id, tender_id, tender_title, procuring_entity, procurement_type,
            official_estimate, awarded_price, our_awarded_price, num_competitors,
            total_bidders, our_rank, award_date, competitors_data, winning_competitor,
            winning_company_type, notes, created_at
        FROM historical_tenders 
        WHERE company_id = ?
        '''
        params = [company_id]
        
        if procurement_type:
            query += " AND procurement_type = ?"
            params.append(procurement_type)
        
        if winner_type and winner_type != "All":
            query += " AND winning_company_type = ?"
            params.append(winner_type)
        
        query += " ORDER BY award_date DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        if data:
            return pd.DataFrame(data, columns=columns)
        return pd.DataFrame()
    
    def update_historical_tender_winner(self, tender_id, winner_name, winner_type, winning_price):
        """Update winner information for an existing historical tender"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE historical_tenders 
        SET winning_competitor = ?, winning_company_type = ?, awarded_price = ?
        WHERE id = ?
        ''', (winner_name, winner_type, winning_price, tender_id))
        
        conn.commit()
        conn.close()
        return True

    def get_competitor_performance_against_us(self, company_id, competitor_name=None):
        """Get competitor performance statistics against our company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            winning_competitor,
            COUNT(*) as times_won,
            AVG(awarded_price / official_estimate) as avg_winning_ratio
        FROM historical_tenders 
        WHERE company_id = ? 
        AND winning_company_type = 'Competitor'
        '''
        params = [company_id]
        
        if competitor_name:
            query += " AND winning_competitor = ?"
            params.append(competitor_name)
        
        query += " GROUP BY winning_competitor ORDER BY times_won DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        if results:
            return [{'competitor': r[0], 'wins': r[1], 'avg_ratio': r[2]} for r in results]
        return []


    def get_winning_statistics(self, company_id, procurement_type=None):
        """Get winning statistics for analysis"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            COUNT(*) as total_tenders,
            SUM(CASE WHEN winning_company_type = 'Our Company' THEN 1 ELSE 0 END) as our_wins,
            SUM(CASE WHEN winning_company_type = 'Competitor' THEN 1 ELSE 0 END) as competitor_wins,
            SUM(CASE WHEN winning_company_type = 'Unknown' THEN 1 ELSE 0 END) as unknown_wins,
            AVG(CASE WHEN winning_company_type = 'Our Company' THEN awarded_price ELSE NULL END) as avg_our_winning_price,
            AVG(CASE WHEN winning_company_type = 'Competitor' THEN awarded_price ELSE NULL END) as avg_competitor_winning_price,
            AVG(official_estimate) as avg_estimate,
            MIN(CASE WHEN winning_company_type = 'Our Company' THEN awarded_price ELSE NULL END) as min_our_winning_price,
            MAX(CASE WHEN winning_company_type = 'Our Company' THEN awarded_price ELSE NULL END) as max_our_winning_price,
            MIN(CASE WHEN winning_company_type = 'Competitor' THEN awarded_price ELSE NULL END) as min_competitor_winning_price,
            MAX(CASE WHEN winning_company_type = 'Competitor' THEN awarded_price ELSE NULL END) as max_competitor_winning_price
        FROM historical_tenders 
        WHERE company_id = ?
        '''
        params = [company_id]
        
        if procurement_type:
            query += " AND procurement_type = ?"
            params.append(procurement_type)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'total_tenders': result[0] or 0,
                'our_wins': result[1] or 0,
                'competitor_wins': result[2] or 0,
                'unknown_wins': result[3] or 0,
                'our_win_rate': (result[1] / result[0] * 100) if result[0] > 0 else 0,
                'avg_our_winning_price': result[4] or 0,
                'avg_competitor_winning_price': result[5] or 0,
                'avg_estimate': result[6] or 0,
                'min_our_winning_price': result[7] or 0,
                'max_our_winning_price': result[8] or 0,
                'min_competitor_winning_price': result[9] or 0,
                'max_competitor_winning_price': result[10] or 0
            }
        return None


    def get_winner_trends(self, company_id, procurement_type=None, months=12):
        """Get winner trends over time"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            strftime('%Y-%m', award_date) as month,
            COUNT(*) as total,
            SUM(CASE WHEN winning_company_type = 'Our Company' THEN 1 ELSE 0 END) as our_wins,
            SUM(CASE WHEN winning_company_type = 'Competitor' THEN 1 ELSE 0 END) as competitor_wins
        FROM historical_tenders 
        WHERE company_id = ?
        AND award_date >= date('now', ?)
        '''
        params = [company_id, f'-{months} months']
        
        if procurement_type:
            query += " AND procurement_type = ?"
            params.append(procurement_type)
        
        query += " GROUP BY strftime('%Y-%m', award_date) ORDER BY month DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        if results:
            return pd.DataFrame(results, columns=['month', 'total', 'our_wins', 'competitor_wins'])
        return pd.DataFrame()

    def get_nppi_for_company(self, company_id, procurement_type='goods'):
        """Get the latest NPPI for a company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT nppi_factor, calculation_date, data_points
        FROM company_nppi
        WHERE company_id = ? AND procurement_type = ?
        ORDER BY calculation_date DESC LIMIT 1
        ''', (company_id, procurement_type))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'nppi_factor': result[0],
                'calculation_date': result[1],
                'data_points': result[2]
            }
        return None
    
    def save_company_nppi(self, company_id, procurement_type, nppi_factor, data_points):
        """Save calculated NPPI for a company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO company_nppi (company_id, procurement_type, nppi_factor, data_points)
        VALUES (?, ?, ?, ?)
        ''', (company_id, procurement_type, nppi_factor, data_points))
        
        conn.commit()
        conn.close()
    
    # ==================== COMPETITOR MASTER METHODS ====================
    
    def get_competitor_master_list(self, company_id, active_only=True):
        """Get all competitors for a company from master list"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT id, competitor_name, business_type, total_bids, total_wins,
               avg_bid_ratio, preferred_strategy, last_seen, is_active
        FROM competitor_master 
        WHERE company_id = ?
        '''
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY total_bids DESC"
        
        cursor.execute(query, (company_id,))
        competitors = cursor.fetchall()
        conn.close()
        
        return competitors
    
    def add_competitor_to_master(self, company_id, competitor_data):
        """Add or update competitor in master list"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if competitor exists
        cursor.execute('''
        SELECT id, total_bids, total_wins, avg_bid_ratio 
        FROM competitor_master 
        WHERE company_id = ? AND competitor_name = ?
        ''', (company_id, competitor_data['competitor_name']))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing competitor
            comp_id, total_bids, total_wins, avg_ratio = existing
            new_total_bids = total_bids + 1
            new_total_wins = total_wins + (1 if competitor_data.get('was_winner', False) else 0)
            
            # Update rolling average
            new_avg_ratio = (avg_ratio * total_bids + competitor_data['bid_ratio']) / new_total_bids if new_total_bids > 0 else competitor_data['bid_ratio']
            
            cursor.execute('''
            UPDATE competitor_master 
            SET total_bids = ?, total_wins = ?, avg_bid_ratio = ?,
                last_seen = ?, updated_at = ?
            WHERE id = ?
            ''', (new_total_bids, new_total_wins, new_avg_ratio, 
                  datetime.now().date(), datetime.now(), comp_id))
        else:
            # Add new competitor
            cursor.execute('''
            INSERT INTO competitor_master (
                company_id, competitor_name, business_type, contact_person,
                phone, email, address, notes, first_seen, last_seen,
                total_bids, total_wins, avg_bid_ratio, preferred_strategy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_id, competitor_data['competitor_name'],
                competitor_data.get('business_type', ''),
                competitor_data.get('contact_person', ''),
                competitor_data.get('phone', ''),
                competitor_data.get('email', ''),
                competitor_data.get('address', ''),
                competitor_data.get('notes', ''),
                datetime.now().date(), datetime.now().date(),
                1, 1 if competitor_data.get('was_winner', False) else 0,
                competitor_data['bid_ratio'],
                competitor_data.get('preferred_strategy', 'Unknown')
            ))
            comp_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return comp_id
    
    def get_competitor_by_id(self, competitor_id):
        """Get competitor details by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM competitor_master WHERE id = ?', (competitor_id,))
        competitor = cursor.fetchone()
        conn.close()
        return competitor
    
    def update_competitor_master(self, competitor_id, update_data):
        """Update competitor information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        fields = []
        values = []
        for key, value in update_data.items():
            fields.append(f"{key} = ?")
            values.append(value)
        
        values.append(competitor_id)
        query = f"UPDATE competitor_master SET {', '.join(fields)}, updated_at = ? WHERE id = ?"
        values.insert(0, datetime.now())
        
        cursor.execute(query, values)
        conn.commit()
        conn.close()
    
    def delete_competitor(self, competitor_id):
        """Soft delete competitor (mark inactive)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE competitor_master SET is_active = 0 WHERE id = ?', (competitor_id,))
        conn.commit()
        conn.close()
    
    def update_competitor_stats_from_bid(self, company_id, competitor_name, bid_ratio, was_winner):
        """Update competitor statistics from a bid"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if competitor exists
        cursor.execute('''
        SELECT id, total_bids, total_wins, avg_bid_ratio 
        FROM competitor_master 
        WHERE company_id = ? AND competitor_name = ?
        ''', (company_id, competitor_name))
        
        existing = cursor.fetchone()
        
        if existing:
            comp_id, total_bids, total_wins, avg_ratio = existing
            new_total_bids = total_bids + 1
            new_total_wins = total_wins + (1 if was_winner else 0)
            new_avg_ratio = (avg_ratio * total_bids + bid_ratio) / new_total_bids
            
            cursor.execute('''
            UPDATE competitor_master 
            SET total_bids = ?, total_wins = ?, avg_bid_ratio = ?,
                last_seen = ?, updated_at = ?
            WHERE id = ?
            ''', (new_total_bids, new_total_wins, new_avg_ratio, 
                  datetime.now().date(), datetime.now(), comp_id))
        else:
            # Add new competitor
            cursor.execute('''
            INSERT INTO competitor_master (
                company_id, competitor_name, first_seen, last_seen,
                total_bids, total_wins, avg_bid_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (company_id, competitor_name, datetime.now().date(), datetime.now().date(),
                  1, 1 if was_winner else 0, bid_ratio))
        
        conn.commit()
        conn.close()
    def update_historical_tender_schema(self):
        """Add new columns for winner tracking if not exists"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Add winning_company_type column
        try:
            cursor.execute("ALTER TABLE historical_tenders ADD COLUMN winning_company_type TEXT")
            print("✓ Added winning_company_type column")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Add our_awarded_price column
        try:
            cursor.execute("ALTER TABLE historical_tenders ADD COLUMN our_awarded_price REAL")
            print("✓ Added our_awarded_price column")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        conn.commit()
        conn.close()

    def get_historical_tenders_with_winner(self, company_id, procurement_type=None, winner_type=None, limit=100):
        """Get historical tenders with winner filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT * FROM historical_tenders 
        WHERE company_id = ?
        '''
        params = [company_id]
        
        if procurement_type:
            query += " AND procurement_type = ?"
            params.append(procurement_type)
        
        if winner_type and winner_type != "All":
            query += " AND winning_company_type = ?"
            params.append(winner_type)
        
        query += " ORDER BY award_date DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        data = cursor.fetchall()
        conn.close()
        
        if data:
            return pd.DataFrame(data, columns=columns)
        return pd.DataFrame()

    def get_winning_statistics(self, company_id, procurement_type=None):
        """Get winning statistics for analysis"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
        SELECT 
            COUNT(*) as total_tenders,
            SUM(CASE WHEN winning_company_type = 'Our Company' THEN 1 ELSE 0 END) as our_wins,
            SUM(CASE WHEN winning_company_type = 'Competitor' THEN 1 ELSE 0 END) as competitor_wins,
            AVG(CASE WHEN winning_company_type = 'Our Company' THEN awarded_price ELSE NULL END) as avg_our_winning_price,
            AVG(CASE WHEN winning_company_type = 'Competitor' THEN awarded_price ELSE NULL END) as avg_competitor_winning_price,
            AVG(official_estimate) as avg_estimate
        FROM historical_tenders 
        WHERE company_id = ?
        '''
        params = [company_id]
        
        if procurement_type:
            query += " AND procurement_type = ?"
            params.append(procurement_type)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'total_tenders': result[0] or 0,
                'our_wins': result[1] or 0,
                'competitor_wins': result[2] or 0,
                'our_win_rate': (result[1] / result[0] * 100) if result[0] > 0 else 0,
                'avg_our_winning_price': result[3] or 0,
                'avg_competitor_winning_price': result[4] or 0,
                'avg_estimate': result[5] or 0
            }
        return None
    def save_historical_tender(self, user_id, company_id, data):
        """Save historical tender data with competitor details and winner info"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO historical_tenders (
            user_id, company_id, tender_id, tender_title, procuring_entity,
            procurement_type, official_estimate, awarded_price, our_awarded_price,
            num_competitors, total_bidders, our_rank, award_date, competitors_data,
            winning_competitor, winning_company_type, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, company_id, data['tender_id'], data['tender_title'],
            data['procuring_entity'], data['procurement_type'], data['official_estimate'],
            data['awarded_price'], data.get('our_awarded_price'),
            data.get('num_competitors', 0), data.get('total_bidders', 0),
            data.get('our_rank'), data['award_date'], data.get('competitors_data'),
            data.get('winning_competitor'), data.get('winning_company_type'),
            data.get('notes', '')
        ))
        
        tender_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return tender_id

    def add_tender_lot(self, tender_id, lot_data):
        """Add lot information for a tender"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO tender_lots (tender_id, lot_no, lot_description, location, 
                                security_amount, estimated_value, start_date, completion_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tender_id, lot_data.get('lot_no'), lot_data.get('description'),
            lot_data.get('location'), lot_data.get('security_amount', 0),
            lot_data.get('estimated_value', 0), lot_data.get('start_date'),
            lot_data.get('completion_date')))
        
        conn.commit()
        conn.close()
    def update_tender_lock_status(self, tender_id: int, locked: bool) -> bool:
        """Update the lock status of a tender"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE company_tenders 
            SET is_locked = ?, locked_at = ?, locked_by = ?
            WHERE id = ?
            ''', (
                1 if locked else 0,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S') if locked else None,
                st.session_state.user_id if locked else None,
                tender_id
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to update tender lock status: {e}")
            return False


    def create_tender_copy(self, original_tender_id: int, created_by: int) -> Optional[int]:
        """Create a backup copy of a locked tender"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Fetch original tender
            cursor.execute('SELECT * FROM company_tenders WHERE id = ?', (original_tender_id,))
            original = cursor.fetchone()
            if not original:
                return None
            
            # Create copy with new ID and copy flags
            cursor.execute('''
            INSERT INTO company_tenders (
                company_id, tender_id, tender_title, procuring_entity, official_estimate,
                submission_deadline, procurement_type, division, district, thana,
                tender_security, document_fee, evaluation_type, created_at,
                is_locked, is_copy, original_tender_id, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                original[1],  # company_id
                f"{original[2]}_COPY",  # tender_id with COPY suffix
                f"{original[3]} (Backup Copy)",  # title with indicator
                original[4], original[5], original[6], original[7],
                original[8], original[9], original[10], original[11],
                original[12], original[13], datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                0,  # is_locked = False for copy
                1,  # is_copy = True
                original_tender_id,  # reference to original
                created_by
            ))
            
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return new_id
            
        except Exception as e:
            logger.error(f"Failed to create tender copy: {e}")
            return None


    def delete_tender(self, tender_id: int) -> bool:
        """Soft delete a tender (mark as inactive)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE company_tenders 
            SET is_active = 0, deleted_at = ?, deleted_by = ?
            WHERE id = ?
            ''', (
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                st.session_state.user_id,
                tender_id
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Failed to delete tender: {e}")
            return False
        


    def increment_analysis_usage(self, user_id: int, company_id: Optional[int] = None) -> bool:
        """Increment usage on the active subscription (company first, then personal)"""
        try:
            sub = self.get_effective_subscription(user_id, company_id)
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if sub['owner_type'] == 'company':
                cursor.execute('''
                UPDATE subscriptions SET analyses_used = analyses_used + 1, updated_at = CURRENT_TIMESTAMP
                WHERE company_id = ?
                ''', (company_id,))
            elif sub['owner_type'] == 'user':
                cursor.execute('''
                UPDATE subscriptions SET analyses_used = analyses_used + 1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                ''', (user_id,))
                
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Usage increment error: {e}")
            return False


    def add_consultant_client(self, consultant_id: int, client_company_id: int, role: str = 'manager') -> bool:
        """Link a consultant to a client company"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            INSERT OR IGNORE INTO consultant_clients (consultant_user_id, client_company_id, role)
            VALUES (?, ?, ?)
            ''', (consultant_id, client_company_id, role))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Client relationship error: {e}")
            return False

    def create_individual_user(self, user_data: Dict) -> tuple:
        """Create an individual user (no company)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create a personal company for the individual
            personal_company_name = f"{user_data['full_name']} (Individual)"
            
            cursor.execute('''
                INSERT INTO companies (company_name, email, phone, division, is_active)
                VALUES (?, ?, ?, ?, ?)
            ''', (personal_company_name, user_data['email'], user_data.get('phone', ''), 'Dhaka', 1))
            
            company_id = cursor.lastrowid
            
            # Hash password
            import bcrypt
            hashed = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute('''
                INSERT INTO users (company_id, username, password, email, full_name, phone, 
                                role, account_type, status, is_approved, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_id,
                user_data['username'],
                hashed,
                user_data['email'],
                user_data['full_name'],
                user_data.get('phone', ''),
                user_data['role'],
                'individual',
                'active',
                1,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return True, user_id
        except Exception as e:
            logger.error(f"Individual user creation failed: {e}")
            return False, str(e)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, username, password, email, full_name, role, company_id, 
                    is_approved, account_type, auth_provider, created_at
                FROM users 
                WHERE email = ?
            """, (email,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'username': row[1],
                    'password': row[2],
                    'email': row[3],
                    'full_name': row[4],
                    'role': row[5],
                    'company_id': row[6],
                    'is_approved': row[7],
                    'account_type': row[8],
                    'auth_provider': row[9],
                    'created_at': row[10]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    def get_company_by_id(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get company by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, company_name, email, phone, division, district, is_individual, created_at
                FROM companies 
                WHERE id = ?
            """, (company_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'company_name': row[1],
                    'email': row[2],
                    'phone': row[3],
                    'division': row[4],
                    'district': row[5],
                    'is_individual': row[6],
                    'created_at': row[7]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting company by ID: {e}")
            return None

    def migrate_schema(self):
        """Auto-migrate database schema for new features"""
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Define new columns to add
        new_columns = {
            'users': [
                ("auth_provider", "TEXT DEFAULT 'email'"),
                ("email_verified", "BOOLEAN DEFAULT 0"),
                ("email_verified_at", "TIMESTAMP"),
                ("verification_token", "TEXT"),
                ("reset_token", "TEXT"),
                ("reset_token_expires", "TIMESTAMP"),
                ("specialization", "TEXT"),
                ("years_experience", "INTEGER")
            ],
            'companies': [
                ("is_individual", "BOOLEAN DEFAULT 0")
            ]
        }
        
        # Add missing columns
        for table, columns in new_columns.items():
            for col_name, col_type in columns:
                if col_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                        print(f"✅ Added column: {table}.{col_name}")
                    except Exception as e:
                        print(f"⚠️ Could not add {table}.{col_name}: {e}")
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token)",
            "CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(reset_token)"
        ]
        
        for index in indexes:
            try:
                cursor.execute(index)
            except Exception as e:
                print(f"⚠️ Could not create index: {e}")
        
        conn.commit()
        conn.close()


    def get_consultant_clients(self, consultant_id: int) -> List[Dict]:
        """Fetch all client companies linked to a consultant"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT c.id, c.company_name, c.email, cc.role, cc.created_at
            FROM consultant_clients cc
            JOIN companies c ON cc.client_company_id = c.id
            WHERE cc.consultant_user_id = ?
            ''', (consultant_id,))
            clients = [{'id': r[0], 'company_name': r[1], 'email': r[2], 'role': r[3]} for r in cursor.fetchall()]
            conn.close()
            return clients
        except Exception as e:
            logger.error(f"Fetch consultant clients error: {e}")
            return []
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, username, email FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {'id': row[0], 'username': row[1], 'email': row[2]}
            return None
        except Exception as e:
            logger.error(f"Error getting user by username: {e}")
            return None

    def update_user(self, user_id, updates):
        """Update user fields including company_id"""
        allowed_fields = ['full_name', 'email', 'phone', 'role', 'is_active', 'company_id']
        set_clause = []
        params = []
        for field, value in updates.items():
            if field in allowed_fields:
                set_clause.append(f"{field} = ?")
                params.append(value)
        if not set_clause:
            return False
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(set_clause)} WHERE id = ?"
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Update user failed: {e}")
            return False
        finally:
            conn.close()

    def generate_random_password(self, length=12):
        """Generate a secure random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password

    def reset_user_password(self, user_id, new_password=None):
        """Reset user password. If new_password not provided, generate random."""
        if not new_password:
            new_password = self.generate_random_password()
        import bcrypt
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
            conn.commit()
            return True, new_password
        except Exception as e:
            logger.error(f"Password reset failed: {e}")
            return False, None
        finally:
            conn.close()

    def delete_user(self, user_id):
        """Hard delete user (only allowed for non-admin users)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # First check if user is admin - prevent deletion of admin
            cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
            role = cursor.fetchone()
            if role and role[0] == 'admin':
                conn.close()
                return False
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            cursor.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Delete user failed: {e}")
            return False
        finally:
            conn.close()

    def get_role_permissions(self, role):
        """Get permissions for a given role as dict"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT permissions FROM role_permissions WHERE role = ?", (role,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
        return {}

    def get_all_roles(self):
        """Get all defined roles with their permissions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Check if table exists first
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='role_permissions'")
            if not cursor.fetchone():
                # Table doesn't exist - create it
                self._create_role_permissions_table()
            
            cursor.execute("SELECT role, permissions FROM role_permissions ORDER BY role")
            rows = cursor.fetchall()
            conn.close()
            roles = []
            for row in rows:
                try:
                    perms = json.loads(row[1]) if row[1] else {}
                except:
                    perms = {}
                roles.append({
                    'role': row[0],
                    'permissions': perms
                })
            return roles
        except Exception as e:
            logger.error(f"Error getting roles: {e}")
            conn.close()
            return []

    def _create_role_permissions_table(self):
        """Create role_permissions table if it doesn't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS role_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT UNIQUE NOT NULL,
                permissions TEXT,  -- JSON string of permissions
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def update_role_permissions(self, role, permissions):
        """Update permissions for a role (permissions is dict)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE role_permissions SET permissions = ?, updated_at = ?
                WHERE role = ?
            ''', (json.dumps(permissions), datetime.now(), role))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Update role permissions failed: {e}")
            return False
        finally:
            conn.close()
      # ==================== COMPANY CRUD OPERATIONS ====================
    
    def get_all_companies_filtered(self, search="", status=None, limit=20, offset=0):
        """Get all companies with pagination and filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, company_name, email, phone, division, district, 
                   address, registration_number, vat_number, created_at, is_active
            FROM companies
            WHERE 1=1
        """
        params = []
        
        if search:
            query += " AND (company_name LIKE ? OR email LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if status is not None:
            query += " AND is_active = ?"
            params.append(status)
        
        # Count total
        count_query = query.replace("SELECT id, company_name, ...", "SELECT COUNT(*)")
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Paginated results
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        companies = []
        for row in rows:
            companies.append({
                'id': row[0], 'company_name': row[1], 'email': row[2],
                'phone': row[3], 'division': row[4], 'district': row[5],
                'address': row[6], 'registration_number': row[7],
                'vat_number': row[8], 'created_at': row[9], 'is_active': row[10]
            })
        return companies, total

    def create_company(self, company_data):
        """Create a new company with full details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO companies (
                    company_name, email, phone, division, district, 
                    address, registration_number, vat_number, website, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_data['company_name'],
                company_data.get('email', ''),
                company_data.get('phone', ''),
                company_data.get('division', ''),
                company_data.get('district', ''),
                company_data.get('address', ''),
                company_data.get('registration_number', ''),
                company_data.get('vat_number', ''),
                company_data.get('website', ''),
                1
            ))
            company_id = cursor.lastrowid
            conn.commit()
            return True, company_id
        except sqlite3.IntegrityError as e:
            return False, f"Company name already exists: {e}"
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()

    def update_company(self, company_id, updates):
        """Update company information"""
        allowed_fields = ['company_name', 'email', 'phone', 'division', 'district', 
                         'address', 'registration_number', 'vat_number', 'website', 'is_active']
        set_clause = []
        params = []
        for field, value in updates.items():
            if field in allowed_fields:
                set_clause.append(f"{field} = ?")
                params.append(value)
        if not set_clause:
            return False
        params.append(company_id)
        query = f"UPDATE companies SET {', '.join(set_clause)} WHERE id = ?"
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Update company failed: {e}")
            return False
        finally:
            conn.close()

    def delete_company(self, company_id):
        """Soft delete a company (mark inactive)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # First, deactivate all users in this company
            cursor.execute("UPDATE users SET is_active = 0 WHERE company_id = ?", (company_id,))
            # Then deactivate the company
            cursor.execute("UPDATE companies SET is_active = 0 WHERE id = ?", (company_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Delete company failed: {e}")
            return False
        finally:
            conn.close()

    def get_company_by_id_bak(self, company_id):
        """Get company by ID as dictionary"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None

    # ==================== SYSTEM USER MANAGEMENT ====================
    
    def get_system_users(self):
        """Get all system-level users (company_id IS NULL)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, full_name, phone, role, is_active, 
                   created_at, last_login
            FROM users
            WHERE company_id IS NULL
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'id': row[0], 'username': row[1], 'email': row[2], 'full_name': row[3],
                'phone': row[4], 'role': row[5], 'is_active': row[6],
                'created_at': row[7], 'last_login': row[8]
            })
        return users

    def create_system_user(self, user_data, created_by):
        """Create a system-level user (no company)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        hashed_pass = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            cursor.execute('''
                INSERT INTO users (
                    company_id, username, password, email, full_name, phone, role,
                    is_active, created_by, is_approved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                None, user_data['username'], hashed_pass, user_data['email'],
                user_data['full_name'], user_data.get('phone', ''), user_data.get('role', 'viewer'),
                1, created_by, 1
            ))
            user_id = cursor.lastrowid
            
            # Create subscription record
            cursor.execute('''
            INSERT INTO subscriptions (user_id, plan, status, analyses_limit)
            VALUES (?, ?, ?, ?)
            ''', (user_id, 'professional', 'active', -1))
            
            conn.commit()
            return True, user_id
        except sqlite3.IntegrityError as e:
            return False, str(e)
        finally:
            conn.close()

    def get_company_users(self, company_id):
        """Get all users belonging to a specific company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, full_name, phone, role, is_active, 
                   created_at, last_login
            FROM users
            WHERE company_id = ?
            ORDER BY created_at DESC
        """, (company_id,))
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'id': row[0], 'username': row[1], 'email': row[2], 'full_name': row[3],
                'phone': row[4], 'role': row[5], 'is_active': row[6],
                'created_at': row[7], 'last_login': row[8]
            })
        return users

    # ==================== ENHANCED GET_ALL_USERS_FILTERED ====================
    
    def get_all_users_filtered(self, company_id=None, search="", role="", status=None, limit=20, offset=0):
        """Get users filtered by company, search, role, status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build base query
        if company_id == -1:
            # Special case: get system users only (company_id IS NULL)
            query = """
                SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
                    u.created_at, u.last_login, NULL as company_name, u.is_approved
                FROM users u
                WHERE u.company_id IS NULL
            """
            params = []
        elif company_id and company_id > 0:
            # Get users for a specific company
            query = """
                SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
                    u.created_at, u.last_login, c.company_name, u.is_approved
                FROM users u
                LEFT JOIN companies c ON u.company_id = c.id
                WHERE u.company_id = ?
            """
            params = [company_id]
        else:
            # Get all users (including system users) - for system admin
            query = """
                SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, 
                    u.created_at, u.last_login, c.company_name, u.is_approved
                FROM users u
                LEFT JOIN companies c ON u.company_id = c.id
                WHERE 1=1
            """
            params = []
        
        # Add search filter
        if search:
            query += " AND (u.username LIKE ? OR u.email LIKE ? OR u.full_name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        
        # Add role filter
        if role:
            query += " AND u.role = ?"
            params.append(role)
        
        # Add status filter
        if status is not None:
            query += " AND u.is_active = ?"
            params.append(status)
        
        # Create count query (remove SELECT part and ORDER BY, LIMIT, OFFSET)
        count_query = query
        # Remove the SELECT part for count
        if "SELECT u.id" in count_query:
            count_query = count_query.replace(
                "SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, u.is_active, u.created_at, u.last_login, c.company_name, u.is_approved",
                "SELECT COUNT(*)"
            )
        
        # Execute count query
        try:
            cursor.execute(count_query, params)
            count_result = cursor.fetchone()
            total = count_result[0] if count_result else 0
        except Exception as e:
            print(f"Count query error: {e}")
            total = 0
        
        # Add pagination
        query += " ORDER BY u.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Execute main query
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        except Exception as e:
            print(f"Main query error: {e}")
            rows = []
        
        conn.close()
        
        # Convert to list of dicts
        users = []
        for row in rows:
            users.append({
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'full_name': row[3],
                'phone': row[4] if len(row) > 4 else '',
                'role': row[5] if len(row) > 5 else 'viewer',
                'is_active': row[6] if len(row) > 6 else 1,
                'created_at': row[7] if len(row) > 7 else None,
                'last_login': row[8] if len(row) > 8 else None,
                'company_name': row[9] if len(row) > 9 else None,
                'is_approved': row[10] if len(row) > 10 else 1
            })
        
        return users, total
    def get_company_stats(self, company_id):
        """Get company statistics including users and analyses"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE company_id = ?', (company_id,))
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tender_analyses WHERE company_id = ?', (company_id,))
        total_analyses = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM tender_analyses 
            WHERE company_id = ? AND bid_status = 'Won'
        ''', (company_id,))
        won_tenders = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_users': total_users,
            'total_analyses': total_analyses,
            'won_tenders': won_tenders,
            'win_rate': (won_tenders / total_analyses * 100) if total_analyses > 0 else 0
        }

    def get_company_stats_by_id(self, company_id):
        """Get statistics for a specific company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE company_id = ?', (company_id,))
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM tender_analyses WHERE company_id = ?', (company_id,))
        total_analyses = cursor.fetchone()[0]
        
        cursor.execute('''
        SELECT COUNT(*) FROM tender_analyses 
        WHERE company_id = ? AND bid_status = 'Won'
        ''', (company_id,))
        won_tenders = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_users': total_users,
            'total_analyses': total_analyses,
            'won_tenders': won_tenders,
            'win_rate': (won_tenders / total_analyses * 100) if total_analyses > 0 else 0
        }
    
    
    def get_tender_analyses_by_company(self, company_id, tender_id=None):
        """Get all analyses for a company, optionally for a specific tender"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if tender_id:
            cursor.execute('''
                SELECT id, tender_title, recommended_bid, success_probability, 
                    risk_level, analysis_date, user_id
                FROM tender_analyses
                WHERE company_id = ? AND tender_id = ?
                ORDER BY analysis_date DESC
            ''', (company_id, tender_id))
        else:
            cursor.execute('''
                SELECT id, tender_id, tender_title, recommended_bid, success_probability,
                    risk_level, analysis_date
                FROM tender_analyses
                WHERE company_id = ?
                ORDER BY analysis_date DESC
                LIMIT 20
            ''', (company_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        analyses = []
        for row in rows:
            analyses.append({
                'id': row[0],
                'tender_title': row[1],
                'recommended_bid': row[2],
                'win_probability': f"{row[3]*100:.0f}%" if row[3] else 'N/A',
                'risk_level': row[4],
                'date': row[5][:16] if row[5] else 'N/A'
            })
        return analyses

    def create_company_user(self, company_id, user_data, created_by):
        """Create a user under a specific company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        hashed_pass = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            cursor.execute('''
                INSERT INTO users (
                    company_id, username, password, email, full_name, phone, role,
                    is_active, created_by, is_approved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                company_id, user_data['username'], hashed_pass, user_data['email'],
                user_data['full_name'], user_data.get('phone', ''), user_data.get('role', 'viewer'),
                1, created_by, 1
            ))
            user_id = cursor.lastrowid
            
            # Create subscription record
            cursor.execute('''
                INSERT INTO subscriptions (user_id, plan, status, analyses_limit)
                VALUES (?, ?, ?, ?)
            ''', (user_id, 'free', 'active', 5))
            
            conn.commit()
            return True, user_id
        except sqlite3.IntegrityError as e:
            return False, str(e)
        finally:
            conn.close()

    def init_role_permissions(self):
        """Initialize or update role permissions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Define role hierarchy and permissions
        role_permissions_config = {
            # System-level roles (company_id = NULL)
            'system_admin': {
                'level': 100,
                'can_manage_all_companies': True,
                'can_create_company': True,
                'can_delete_company': True,
                'can_manage_system_users': True,
                'can_view_all_analyses': True,
                'can_manage_subscriptions': True,
                'can_manage_roles': True,
                'can_view_system_logs': True,
                'description': 'Full platform access'
            },
            'system_support': {
                'level': 80,
                'can_manage_all_companies': True,
                'can_create_company': False,
                'can_delete_company': False,
                'can_manage_system_users': False,
                'can_view_all_analyses': True,
                'can_manage_subscriptions': False,
                'can_manage_roles': False,
                'can_view_system_logs': True,
                'description': 'Can view all companies, support access'
            },
            'system_auditor': {
                'level': 70,
                'can_manage_all_companies': False,
                'can_create_company': False,
                'can_delete_company': False,
                'can_manage_system_users': False,
                'can_view_all_analyses': True,
                'can_manage_subscriptions': False,
                'can_manage_roles': False,
                'can_view_system_logs': True,
                'description': 'Read-only across platform'
            },
            # Company-level roles (has company_id)
            'company_admin': {
                'level': 50,
                'can_manage_company_users': True,
                'can_create_user': True,
                'can_delete_user': True,
                'can_manage_tenders': True,
                'can_view_company_analyses': True,
                'can_manage_company_subscription': True,
                'can_edit_company_settings': True,
                'description': 'Full company management'
            },
            'company_manager': {
                'level': 40,
                'can_manage_company_users': False,
                'can_create_user': True,
                'can_delete_user': False,
                'can_manage_tenders': True,
                'can_view_company_analyses': True,
                'can_manage_company_subscription': False,
                'can_edit_company_settings': False,
                'description': 'Can manage tenders and create users'
            },
            'analyst': {
                'level': 30,
                'can_manage_company_users': False,
                'can_create_user': False,
                'can_delete_user': False,
                'can_manage_tenders': True,
                'can_view_company_analyses': True,
                'can_manage_company_subscription': False,
                'can_edit_company_settings': False,
                'description': 'Can run analyses and view reports'
            },
            'viewer': {
                'level': 10,
                'can_manage_company_users': False,
                'can_create_user': False,
                'can_delete_user': False,
                'can_manage_tenders': False,
                'can_view_company_analyses': True,
                'can_manage_company_subscription': False,
                'can_edit_company_settings': False,
                'description': 'Read-only access'
            }
        }
        
        for role, perms in role_permissions_config.items():
            cursor.execute('''
                INSERT OR REPLACE INTO role_permissions (role, permissions, updated_at)
                VALUES (?, ?, ?)
            ''', (role, json.dumps(perms), datetime.now()))
        
        conn.commit()
        conn.close()
        print("✅ Role permissions initialized")
    def migrate_user_columns(self):
        """Add missing columns to users table for system users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Columns to add if missing
        columns_to_add = {
            'account_type': "TEXT DEFAULT 'company'",
            'is_approved': "BOOLEAN DEFAULT 1",
            'registration_complete': "BOOLEAN DEFAULT 1",
            'approved_by': "INTEGER",
            'approved_at': "TIMESTAMP",
            'auth_provider': "TEXT DEFAULT 'email'",
            'email_verified': "BOOLEAN DEFAULT 1",
            'verification_token': "TEXT",
            'reset_token': "TEXT",
            'reset_token_expires': "TIMESTAMP"
        }
        
        for col_name, col_type in columns_to_add.items():
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                    print(f"✅ Added column: {col_name}")
                except Exception as e:
                    print(f"⚠️ Could not add {col_name}: {e}")
        
        conn.commit()
        conn.close() 
    def get_all_pending_users(self):
        """Get all pending user registrations across all companies (for system admin)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Fix: Include users where is_approved = 0, regardless of registration_complete
        cursor.execute('''
            SELECT u.id, u.username, u.email, u.full_name, u.phone, u.role, 
                u.created_at, u.created_by, c.company_name, u.is_approved, u.is_active
            FROM users u
            LEFT JOIN companies c ON u.company_id = c.id
            WHERE u.is_approved = 0
            ORDER BY u.created_at ASC
        ''')
        
        users = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        result = []
        for user in users:
            result.append({
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'full_name': user[3],
                'phone': user[4] if len(user) > 4 else '',
                'role': user[5] if len(user) > 5 else 'user',
                'created_at': user[6] if len(user) > 6 else '',
                'created_by': user[7] if len(user) > 7 else None,
                'company_name': user[8] if len(user) > 8 else 'N/A',
                'is_approved': user[9] if len(user) > 9 else 0,
                'is_active': user[10] if len(user) > 10 else 1
            })
        
        print(f"🔍 Found {len(result)} pending users")  # Debug
        return result


    
    def migrate_company_isolation(self):
        """Ensure proper company isolation and add missing columns"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get existing columns in tender_analyses
        cursor.execute("PRAGMA table_info(tender_analyses)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Add company_id to tender_analyses if missing
        if 'company_id' not in existing_columns:
            try:
                cursor.execute("ALTER TABLE tender_analyses ADD COLUMN company_id INTEGER REFERENCES companies(id)")
                print("✅ Added company_id to tender_analyses")
            except Exception as e:
                print(f"⚠️ Could not add company_id to tender_analyses: {e}")
        
        # Get existing columns in users
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        
        # Add is_company_admin flag to users if missing
        if 'is_company_admin' not in user_columns:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN is_company_admin BOOLEAN DEFAULT 0")
                print("✅ Added is_company_admin to users")
            except Exception as e:
                print(f"⚠️ Could not add is_company_admin: {e}")
        
        # Add company_admin_approved_by if missing
        if 'company_admin_approved_by' not in user_columns:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN company_admin_approved_by INTEGER")
                print("✅ Added company_admin_approved_by to users")
            except Exception as e:
                print(f"⚠️ Could not add company_admin_approved_by: {e}")
        
        # Add company_admin_approved_at if missing
        if 'company_admin_approved_at' not in user_columns:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN company_admin_approved_at TIMESTAMP")
                print("✅ Added company_admin_approved_at to users")
            except Exception as e:
                print(f"⚠️ Could not add company_admin_approved_at: {e}")
        
        # Create indexes for faster company-based queries
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_company ON tender_analyses(company_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_company ON users(company_id)")
            print("✅ Created company isolation indexes")
        except Exception as e:
            print(f"⚠️ Could not create indexes: {e}")
        
        conn.commit()
        conn.close()
        print("✅ Company isolation migration completed")

    def get_company_subscription(self, company_id):
        """Get subscription details for a company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if company has a direct subscription
        cursor.execute('''
            SELECT id, plan, status, start_date, end_date, analyses_used, analyses_limit,
                payment_method, transaction_id, updated_at
            FROM subscriptions 
            WHERE company_id = ? AND company_id IS NOT NULL
            ORDER BY created_at DESC LIMIT 1
        ''', (company_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'plan': result[1],
                'status': result[2],
                'start_date': result[3],
                'end_date': result[4],
                'analyses_used': result[5] or 0,
                'analyses_limit': result[6] or 5,
                'payment_method': result[7],
                'transaction_id': result[8],
                'updated_at': result[9]
            }
        
        # Return default if no subscription exists
        return {
            'plan': 'free',
            'status': 'active',
            'analyses_used': 0,
            'analyses_limit': 5,
            'start_date': datetime.now().date(),
            'end_date': datetime.now().date() + timedelta(days=30)
        }

    def update_company_subscription(self, company_id, plan, duration='monthly', payment_method='admin', transaction_id=None):
        """Update or create subscription for a company"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        start_date = datetime.now().date()
        
        # Plan limits and pricing
        plan_limits = {
            'free': {'limit': 5, 'price': 0},
            'basic': {'limit': 30, 'price': 4999},
            'professional': {'limit': -1, 'price': 14999},
            'enterprise': {'limit': -1, 'price': 49999}
        }
        
        if duration == 'monthly':
            end_date = start_date + timedelta(days=30)
        else:
            end_date = start_date + timedelta(days=365)
        
        # Check if subscription exists
        cursor.execute('SELECT id FROM subscriptions WHERE company_id = ? AND company_id IS NOT NULL', (company_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE subscriptions 
                SET plan = ?, status = 'active', start_date = ?, end_date = ?, 
                    analyses_limit = ?, payment_method = ?, transaction_id = ?, updated_at = ?
                WHERE company_id = ?
            ''', (plan, start_date, end_date, plan_limits[plan]['limit'], 
                payment_method, transaction_id or f"ADMIN_{datetime.now().strftime('%Y%m%d%H%M%S')}", 
                datetime.now(), company_id))
        else:
            cursor.execute('''
                INSERT INTO subscriptions (company_id, plan, status, start_date, end_date, 
                                        analyses_limit, payment_method, transaction_id)
                VALUES (?, ?, 'active', ?, ?, ?, ?, ?)
            ''', (company_id, plan, start_date, end_date, plan_limits[plan]['limit'], 
                payment_method, transaction_id or f"ADMIN_{datetime.now().strftime('%Y%m%d%H%M%S')}"))
        
        conn.commit()
        conn.close()
        return True
    def migrate_subscriptions_table(self):
        """Add missing columns to subscriptions table"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(subscriptions)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Add created_at if missing (without default first)
        if 'created_at' not in existing_columns:
            try:
                cursor.execute("ALTER TABLE subscriptions ADD COLUMN created_at TIMESTAMP")
                # Set default value for existing rows
                cursor.execute("UPDATE subscriptions SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
                print("✅ Added created_at to subscriptions")
            except Exception as e:
                print(f"⚠️ Could not add created_at: {e}")
        
        # Add company_id if missing
        if 'company_id' not in existing_columns:
            try:
                cursor.execute("ALTER TABLE subscriptions ADD COLUMN company_id INTEGER REFERENCES companies(id)")
                print("✅ Added company_id to subscriptions")
            except Exception as e:
                print(f"⚠️ Could not add company_id: {e}")
        
        # Add updated_at if missing (without default first)
        if 'updated_at' not in existing_columns:
            try:
                cursor.execute("ALTER TABLE subscriptions ADD COLUMN updated_at TIMESTAMP")
                # Set default value for existing rows
                cursor.execute("UPDATE subscriptions SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
                print("✅ Added updated_at to subscriptions")
            except Exception as e:
                print(f"⚠️ Could not add updated_at: {e}")
        
        conn.commit()
        conn.close()
        print("✅ Subscriptions table migration completed")
    
    def migrate_tender_analyses_table(self):
        """Add missing columns to tender_analyses table"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(tender_analyses)")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        # Define missing columns to add
        columns_to_add = {
            'district': "TEXT",
            'thana': "TEXT",
            'risk_strategy': "TEXT",
            'confidence_score': "REAL DEFAULT 0.70",
            'expected_profit': "REAL DEFAULT 0",
            'expected_value': "REAL DEFAULT 0",
            'competitor_bids': "TEXT",  # JSON string
            'slt_threshold': "REAL DEFAULT 0",
            'nppi_factor': "REAL DEFAULT 0.92",
            'weighted_average': "REAL DEFAULT 0"
        }
        
        for col_name, col_type in columns_to_add.items():
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE tender_analyses ADD COLUMN {col_name} {col_type}")
                    print(f"✅ Added column: {col_name}")
                except Exception as e:
                    print(f"⚠️ Could not add {col_name}: {e}")
        
        conn.commit()
        conn.close()
        print("✅ Tender analyses table migration completed")    
        # Singleton instance
    
    def _save_hierarchical_pwd_data(self, hierarchy, edition_year, version_id=None):
        """Save hierarchical data to database - NO DESCRIPTION TRUNCATION"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Ensure tables exist
        self.init_pwd_hierarchical_tables()
        
        # Get or create version
        if version_id is None:
            from datetime import date
            cursor.execute("""
                INSERT INTO rate_versions (source, version_name, edition_year, effective_from, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, ('PWD', f"PWD Schedule {edition_year}", edition_year, date.today(), True))
            version_id = cursor.lastrowid
        
        # Save parents - NO truncation
        for parent in hierarchy['parents']:
            cursor.execute("""
                INSERT OR REPLACE INTO pwd_parents (pwd_code, description, chapter_number, version_id)
                VALUES (?, ?, ?, ?)
            """, (parent['code'], parent['description'], parent['chapter'], version_id))
        
        # Save children and rates - NO truncation
        for child in hierarchy['children']:
            cursor.execute("""
                INSERT OR REPLACE INTO pwd_children (pwd_code, parent_code, description, unit, edition_year, version_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (child['pwd_code'], child['parent_code'], child['description'], child['unit'], edition_year, version_id))
            
            for zone, rate in child['rates'].items():
                cursor.execute("""
                    INSERT OR REPLACE INTO pwd_rates (pwd_code, zone_name, unit_rate, edition_year, version_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (child['pwd_code'], zone, rate, edition_year, version_id))
        
        conn.commit()
        conn.close()
        
        return version_id

     # APPEND THIS TO THE BOTTOM OF YOUR EXISTING database/db_manager.py FILE
    def get_pwd_stats(self):
        """Get statistics about imported PWD data."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM pwd_items")
            total_items = cursor.fetchone()[0] if cursor.fetchone() else 0
            
            cursor.execute("SELECT COUNT(*) FROM pwd_rates")
            total_rates = cursor.fetchone()[0] if cursor.fetchone() else 0
            
            cursor.execute("SELECT COUNT(DISTINCT chapter_number) FROM pwd_items")
            total_chapters = cursor.fetchone()[0] if cursor.fetchone() else 0
            
            conn.close()
            
            return {
                "total_items": total_items,
                "total_rates": total_rates,
                "total_chapters": total_chapters
            }
        except Exception as e:
            logger.error(f"Error getting PWD stats: {e}")
            return {"total_items": 0, "total_rates": 0, "total_chapters": 0}

    def get_pwd_rates(self, pwd_code=None, chapter=None, zone=None, limit=None):
        """
        Retrieve PWD rates from database.
        
        Args:
            pwd_code: Specific item code (e.g., '01.1.1')
            chapter: Chapter number (e.g., '01')
            zone: Zone name (e.g., 'Dhaka', 'Chattogram')
            limit: Maximum number of rows to return
        
        Returns:
            DataFrame with matching rates
        """
        import pandas as pd
        
        try:
            conn = self.get_connection()
            
            query = """
                SELECT i.pwd_code, i.specification_text, i.measurement_unit,
                    r.zone_name, r.unit_rate, r.edition_year, 
                    c.chapter_name as chapter_name
                FROM pwd_items i
                JOIN pwd_rates r ON i.pwd_code = r.pwd_code
                JOIN chapters c ON i.chapter_number = c.chapter_number
                WHERE 1=1
            """
            params = []
            
            if pwd_code:
                query += " AND i.pwd_code = ?"
                params.append(pwd_code)
            
            if chapter:
                query += " AND i.chapter_number = ?"
                params.append(chapter)
            
            if zone:
                query += " AND r.zone_name = ?"
                params.append(zone)
            
            query += " ORDER BY i.pwd_code, r.zone_name"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            return df
        except Exception as e:
            logger.error(f"Error getting PWD rates: {e}")
            return pd.DataFrame()

    def search_pwd_items(self, search_term, limit=50):
        """Search PWD items by code or description."""
        import pandas as pd
        
        try:
            conn = self.get_connection()
            
            query = """
                SELECT DISTINCT i.pwd_code, i.specification_text, i.measurement_unit,
                    i.chapter_number, c.chapter_name
                FROM pwd_items i
                LEFT JOIN chapters c ON i.chapter_number = c.chapter_number
                WHERE i.pwd_code LIKE ? OR i.specification_text LIKE ?
                ORDER BY i.pwd_code
                LIMIT ?
            """
            params = [f"%{search_term}%", f"%{search_term}%", limit]
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            return df
        except Exception as e:
            logger.error(f"Error searching PWD items: {e}")
            return pd.DataFrame()
    def update_role_permissions_for_rates(self):
        """Add rate management permissions to role_permissions table"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Define rate management permissions for each role
        rate_permissions = {
            'admin': {
                'manage_zones': True,
                'manage_chapters': True,
                'manage_parents': True,
                'manage_children': True,
                'manage_versions': True,
                'view_rates': True,
                'edit_rates': True,
                'delete_rates': True
            },
            'system_admin': {
                'manage_zones': True,
                'manage_chapters': True,
                'manage_parents': True,
                'manage_children': True,
                'manage_versions': True,
                'view_rates': True,
                'edit_rates': True,
                'delete_rates': True
            },
            'company_admin': {
                'manage_zones': False,  # Zones are system-wide
                'manage_chapters': True,
                'manage_parents': True,
                'manage_children': True,
                'manage_versions': True,
                'view_rates': True,
                'edit_rates': True,
                'delete_rates': False
            },
            'manager': {
                'manage_zones': False,
                'manage_chapters': True,
                'manage_parents': True,
                'manage_children': True,
                'manage_versions': False,
                'view_rates': True,
                'edit_rates': True,
                'delete_rates': False
            },
            'analyst': {
                'manage_zones': False,
                'manage_chapters': False,
                'manage_parents': False,
                'manage_children': True,
                'manage_versions': False,
                'view_rates': True,
                'edit_rates': True,
                'delete_rates': False
            },
            'data_entry': {
                'manage_zones': False,
                'manage_chapters': False,
                'manage_parents': True,
                'manage_children': True,
                'manage_versions': False,
                'view_rates': True,
                'edit_rates': True,
                'delete_rates': False
            },
            'viewer': {
                'manage_zones': False,
                'manage_chapters': False,
                'manage_parents': False,
                'manage_children': False,
                'manage_versions': False,
                'view_rates': True,
                'edit_rates': False,
                'delete_rates': False
            }
        }
        
        # Update each role's permissions
        for role, perms in rate_permissions.items():
            # Get existing permissions
            existing = self.get_role_permissions(role)
            # Merge with new permissions
            existing.update(perms)
            # Save back
            self.update_role_permissions(role, existing)
        
        print("✅ Rate management permissions added to roles")  
    def get_lged_sections_by_chapter(self, chapter_number: str) -> pd.DataFrame:
        """
        Get LGED sections for a specific chapter from rate_sections table.
        
        Args:
            chapter_number: The chapter number (e.g., "1", "2")
        
        Returns:
            DataFrame with sections
        """
        try:
            conn = self.get_connection()
            
            # First get the chapter ID
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM rate_chapters 
                WHERE source = 'LGED' AND chapter_number = ?
                ORDER BY id DESC LIMIT 1
            """, (chapter_number,))
            
            chapter_row = cursor.fetchone()
            
            if chapter_row:
                chapter_id = chapter_row[0]
                df = pd.read_sql_query("""
                    SELECT section_number, section_name, description
                    FROM rate_sections 
                    WHERE source = 'LGED' AND chapter_id = ?
                    ORDER BY section_number
                """, conn, params=[chapter_id])
            else:
                df = pd.DataFrame()
            
            conn.close()
            return df
            
        except Exception as e:
            logger.error(f"Error getting sections for chapter {chapter_number}: {e}")
            return pd.DataFrame()
    
    def update_lged_chapter_section(self, hierarchy, version_id, edition_year, 
                                  chapter_num, section_num=None, notes=None):
        """
        Update data for a specific chapter/section within an existing version.
        Only affects items belonging to the specified chapter/section.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Verify version exists
            cursor.execute("""
                SELECT id, version_number FROM rate_versions 
                WHERE id = ? AND source = 'LGED'
            """, (version_id,))
            
            version = cursor.fetchone()
            if not version:
                return {
                    'success': False,
                    'error': f"Version {version_id} not found",
                    'message': "Version not found"
                }
            
            version_number = version[1]
            
            # Get data from hierarchy
            section_headers = hierarchy.get('section_headers', [])
            rate_items = hierarchy.get('rate_items', [])
            
            # Delete existing data for this specific chapter/section
            if section_num:
                # Delete specific section within chapter
                cursor.execute("""
                    DELETE FROM lged_children 
                    WHERE version_id = ? AND chapter_number = ? AND section_number = ?
                """, (version_id, chapter_num, section_num))
                
                cursor.execute("""
                    DELETE FROM lged_parents 
                    WHERE version_id = ? AND chapter_number = ? AND section_number = ?
                """, (version_id, chapter_num, section_num))
            else:
                # Delete entire chapter
                cursor.execute("""
                    DELETE FROM lged_children 
                    WHERE version_id = ? AND chapter_number = ?
                """, (version_id, chapter_num))
                
                cursor.execute("""
                    DELETE FROM lged_parents 
                    WHERE version_id = ? AND chapter_number = ?
                """, (version_id, chapter_num))
            
            # Save section headers for this chapter/section
            for header in section_headers:
                cursor.execute("""
                    INSERT INTO lged_parents (code, description, chapter_number, section_number, 
                                            parent_type, has_children, version_id)
                    VALUES (?, ?, ?, ?, 'section_header', ?, ?)
                """, (header['code'], header.get('description', '')[:500], 
                    header.get('chapter_number', chapter_num), 
                    header.get('section_number', section_num or ''),
                    1 if header.get('has_children') else 0, version_id))
            
            # Save rate items for this chapter/section
            for item in rate_items:
                parent_code_val = item.get('parent_code') if item.get('parent_code') else None
                
                cursor.execute("""
                    INSERT INTO lged_children (
                        code, parent_code, description, unit, 
                        chapter_number, section_number,
                        zone_a, zone_b, zone_c, zone_d,
                        edition_year, version_id, is_parent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item['code'], 
                    parent_code_val,
                    item.get('description', '')[:500], 
                    item.get('unit', ''),
                    item.get('chapter_number', chapter_num), 
                    item.get('section_number', section_num or ''),
                    item.get('zone_a'), item.get('zone_b'), 
                    item.get('zone_c'), item.get('zone_d'),
                    edition_year, version_id, 
                    1 if item.get('is_parent') else 0
                ))
            
            # Update version statistics (recalculate totals)
            cursor.execute("""
                SELECT COUNT(*) FROM lged_parents WHERE version_id = ?
            """, (version_id,))
            total_parents = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM lged_children WHERE version_id = ?
            """, (version_id,))
            total_children = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM lged_children WHERE version_id = ?
            """, (version_id,))
            total_rate_items = cursor.fetchone()[0]
            total_rates = total_rate_items * 4
            
            cursor.execute("""
                UPDATE rate_versions 
                SET total_parents = ?, total_children = ?, total_rates = ?,
                    updated_at = ?, notes = ?
                WHERE id = ?
            """, (total_parents, total_children, total_rates, datetime.now(), notes, version_id))
            
            conn.commit()
            
            return {
                'success': True,
                'version_id': version_id,
                'version_number': version_number,
                'chapter': chapter_num,
                'section': section_num,
                'mode': 'update_chapter_section',
                'total_parents': total_parents,
                'total_children': total_children,
                'total_rates': total_rates,
                'message': f"✅ Updated Chapter {chapter_num}" + (f" Section {section_num}" if section_num else "") + f" in Version {version_number}"
            }
            
        except Exception as e:
            conn.rollback()
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'mode': 'update_chapter_section',
                'message': f"❌ Failed to update: {e}"
            }
        finally:
            conn.close()
    def save_scenario(self, company_id: int, user_id: int, scenario_data: dict) -> Optional[int]:
        """
        Save a generated scenario to database.
        
        Args:
            company_id: Company ID
            user_id: User ID
            scenario_data: Dictionary with scenario data
            
        Returns:
            scenario_id if successful, None otherwise
        """
        import uuid
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            scenario_uuid = str(uuid.uuid4())
            
            cursor.execute("""
                INSERT INTO saved_scenarios (
                    scenario_uuid, company_id, user_id, tender_id, scenario_name, description,
                    official_estimate, procurement_type, min_price_pct, max_price_pct,
                    competitor_counts, bidding_pattern, ai_strategy, random_seed,
                    recommended_bid, bid_ratio, confidence_score, expected_win_probability,
                    scenarios_data, competitor_stats
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scenario_uuid,
                company_id,
                user_id,
                scenario_data.get('tender_id'),
                scenario_data.get('scenario_name', f"Scenario {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
                scenario_data.get('description', ''),
                scenario_data['official_estimate'],
                scenario_data['procurement_type'],
                scenario_data.get('min_price_pct', 0.88),
                scenario_data.get('max_price_pct', 1.08),
                json.dumps(scenario_data['competitor_counts']),
                scenario_data.get('bidding_pattern', 'realistic'),
                scenario_data.get('ai_strategy', 'weighted_ensemble'),
                scenario_data.get('random_seed', 42),
                scenario_data['recommended_bid'],
                scenario_data['bid_ratio'],
                scenario_data['confidence_score'],
                scenario_data.get('expected_win_probability'),
                json.dumps(scenario_data['scenarios']),
                json.dumps(scenario_data.get('competitor_stats', {}))
            ))
            
            scenario_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return scenario_id
            
        except Exception as e:
            logger.error(f"Error saving scenario: {e}")
            return None

    def get_user_scenarios(self, company_id: int, user_id: int = None, 
                        limit: int = 50, offset: int = 0,
                        search: str = "", is_favorite: bool = None) -> tuple:
        """
        Get scenarios for a company/user with pagination.
        
        Args:
            company_id: Company ID
            user_id: Optional user ID to filter by user
            limit: Max records to return
            offset: Pagination offset
            search: Search term for scenario name
            is_favorite: Filter by favorite status
            
        Returns:
            (scenarios_list, total_count)
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT s.*, u.full_name as created_by_name
                FROM saved_scenarios s
                LEFT JOIN users u ON s.user_id = u.id
                WHERE s.company_id = ?
            """
            params = [company_id]
            
            if user_id:
                query += " AND s.user_id = ?"
                params.append(user_id)
            
            if search:
                query += " AND (s.scenario_name LIKE ? OR s.description LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])
            
            if is_favorite is not None:
                query += " AND s.is_favorite = ?"
                params.append(1 if is_favorite else 0)
            
            # Count total
            count_query = query.replace("SELECT s.*, u.full_name as created_by_name", "SELECT COUNT(*)")
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Get paginated results
            query += " ORDER BY s.created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            scenarios = []
            for row in rows:
                scenarios.append({
                    'id': row[0],
                    'scenario_uuid': row[1],
                    'company_id': row[2],
                    'user_id': row[3],
                    'tender_id': row[4],
                    'scenario_name': row[5],
                    'description': row[6],
                    'official_estimate': row[7],
                    'procurement_type': row[8],
                    'recommended_bid': row[15],
                    'bid_ratio': row[16],
                    'confidence_score': row[17],
                    'expected_win_probability': row[18],
                    'is_favorite': row[21],
                    'view_count': row[22],
                    'created_at': row[24],
                    'created_by_name': row[26] if len(row) > 26 else None
                })
            
            return scenarios, total
            
        except Exception as e:
            logger.error(f"Error getting scenarios: {e}")
            return [], 0

    def get_scenario_by_id(self, scenario_id: int, company_id: int) -> Optional[dict]:
        """Get a specific scenario by ID with company verification"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.*, u.full_name as created_by_name
                FROM saved_scenarios s
                LEFT JOIN users u ON s.user_id = u.id
                WHERE s.id = ? AND s.company_id = ?
            """, (scenario_id, company_id))
            
            row = cursor.fetchone()
            
            if row:
                # Increment view count
                cursor.execute("""
                    UPDATE saved_scenarios 
                    SET view_count = view_count + 1
                    WHERE id = ?
                """, (scenario_id,))
                conn.commit()
                
                scenario = {
                    'id': row[0],
                    'scenario_uuid': row[1],
                    'company_id': row[2],
                    'user_id': row[3],
                    'tender_id': row[4],
                    'scenario_name': row[5],
                    'description': row[6],
                    'official_estimate': row[7],
                    'procurement_type': row[8],
                    'min_price_pct': row[9],
                    'max_price_pct': row[10],
                    'competitor_counts': json.loads(row[11]) if row[11] else [],
                    'bidding_pattern': row[12],
                    'ai_strategy': row[13],
                    'random_seed': row[14],
                    'recommended_bid': row[15],
                    'bid_ratio': row[16],
                    'confidence_score': row[17],
                    'expected_win_probability': row[18],
                    'scenarios_data': json.loads(row[19]) if row[19] else [],
                    'competitor_stats': json.loads(row[20]) if row[20] else {},
                    'is_favorite': row[21],
                    'view_count': row[22],
                    'share_token': row[23],
                    'created_at': row[24],
                    'updated_at': row[25],
                    'created_by_name': row[26] if len(row) > 26 else None
                }
                conn.close()
                return scenario
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"Error getting scenario by ID: {e}")
            return None

    def delete_scenario(self, scenario_id: int, company_id: int) -> bool:
        """Delete a scenario (company-scoped)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM saved_scenarios 
                WHERE id = ? AND company_id = ?
            """, (scenario_id, company_id))
            
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            return affected > 0
            
        except Exception as e:
            logger.error(f"Error deleting scenario: {e}")
            return False

    def toggle_favorite_scenario(self, scenario_id: int, company_id: int, is_favorite: bool) -> bool:
        """Mark/unmark scenario as favorite"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE saved_scenarios 
                SET is_favorite = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND company_id = ?
            """, (1 if is_favorite else 0, scenario_id, company_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error toggling favorite: {e}")
            return False

    def update_scenario_name(self, scenario_id: int, company_id: int, new_name: str) -> bool:
        """Update scenario name"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE saved_scenarios 
                SET scenario_name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND company_id = ?
            """, (new_name, scenario_id, company_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating scenario name: {e}")
            return False

    def share_scenario(self, scenario_id: int, user_id: int, share_with_email: str, 
                    permission: str = 'view', expires_days: int = 7) -> Optional[str]:
        """Generate share token for a scenario"""
        import uuid
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            share_token = str(uuid.uuid4()).replace('-', '')[:16]
            expires_at = datetime.now() + timedelta(days=expires_days)
            
            cursor.execute("""
                INSERT INTO scenario_shares (
                    scenario_id, shared_by_user_id, shared_with_email, 
                    permission, share_token, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (scenario_id, user_id, share_with_email, permission, share_token, expires_at))
            
            # Also update the share_token in saved_scenarios
            cursor.execute("""
                UPDATE saved_scenarios 
                SET share_token = ?
                WHERE id = ?
            """, (share_token, scenario_id))
            
            conn.commit()
            conn.close()
            
            return share_token
            
        except Exception as e:
            logger.error(f"Error sharing scenario: {e}")
            return None

    def get_shared_scenario_by_token(self, share_token: str) -> Optional[dict]:
        """Get a shared scenario by token"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.*, u.full_name as created_by_name
                FROM saved_scenarios s
                LEFT JOIN users u ON s.user_id = u.id
                WHERE s.share_token = ? AND s.is_favorite IS NOT NULL
            """, (share_token,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'scenario_uuid': row[1],
                    'scenario_name': row[5],
                    'description': row[6],
                    'official_estimate': row[7],
                    'recommended_bid': row[15],
                    'scenarios_data': json.loads(row[19]) if row[19] else [],
                    'created_at': row[24],
                    'created_by_name': row[26] if len(row) > 26 else None
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting shared scenario: {e}")
            return None
        
    
db = UnifiedDatabaseManager()
