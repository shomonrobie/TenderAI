# database/unified_db_manager.py
"""
TenderAI Unified Database Manager
Complete - Includes ALL tables from migrations v001 to v011
No migrations needed - All tables auto-create on startup
"""

import sqlite3
import json
import bcrypt
import pandas as pd
import os
import logging
import hashlib
import secrets
import string
import re
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List, Tuple, Union
import streamlit as st
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class UnifiedDatabaseManager:
    """Single unified database manager - all tables auto-create on init"""
    
    def __init__(self, db_path="data/tender_system.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._create_all_tables()
        self._insert_default_data()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
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
        
        # =========================================================
        # v010_fix_companies_table.py & v011_add_company_columns.py
        # =========================================================
        # (Columns already added to companies table above)
        
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
    
    
    # ==================== USER MANAGEMENT METHODS ====================
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user data if valid"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Hash the provided password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute("""
                SELECT id, username, email, full_name, role, company_id, is_active,
                       created_at, last_login, subscription_tier
                FROM users 
                WHERE username = ? AND password_hash = ? AND is_active = 1
            """, (username, password_hash))
            
            user = cursor.fetchone()
            
            if user:
                # Update last login time
                cursor.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                    (user['id'],)
                )
                return dict(user)
            
            return None
    
    def create_user(self, username: str, email: str, password: str, full_name: str = None,
                   role: str = 'viewer', company_id: int = None) -> Optional[int]:
        """Create a new user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if username or email already exists
            cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", 
                          (username, email))
            if cursor.fetchone():
                logger.warning(f"User {username} or email {email} already exists")
                return None
            
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, full_name, role, company_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, email, password_hash, full_name, role, company_id))
            
            return cursor.lastrowid
    
    def get_all_users(self, include_inactive: bool = False) -> List[Dict]:
        """Get all users with optional filtering"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT u.id, u.username, u.email, u.full_name, u.role, u.company_id,
                       u.is_active, u.created_at, u.last_login, u.subscription_tier,
                       c.name as company_name
                FROM users u
                LEFT JOIN companies c ON u.company_id = c.id
            """
            
            if not include_inactive:
                query += " WHERE u.is_active = 1"
            
            query += " ORDER BY u.created_at DESC"
            
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """Update user information"""
        allowed_fields = ['email', 'full_name', 'role', 'company_id', 'is_active', 
                         'subscription_tier']
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(user_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE users 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            return cursor.rowcount > 0
    
    def delete_user(self, user_id: int, hard_delete: bool = False) -> bool:
        """Delete or deactivate user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if hard_delete:
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            else:
                cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
            
            return cursor.rowcount > 0
    
    def reset_password(self, user_id: int, new_password: str) -> bool:
        """Reset user password"""
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", 
                          (password_hash, user_id))
            return cursor.rowcount > 0
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, email, full_name, role, company_id, is_active,
                       created_at, last_login, subscription_tier
                FROM users WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ==================== SUBSCRIPTION METHODS ====================
    
    def get_user_subscription(self, user_id: int) -> Dict:
        """Get user's subscription details"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT subscription_tier, subscription_expiry, 
                       api_calls_used, api_calls_limit
                FROM users WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {'subscription_tier': 'free', 'api_calls_used': 0, 'api_calls_limit': 100}
    
    def get_company_subscription(self, company_id: int) -> Dict:
        """Get company's subscription details"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT subscription_tier, subscription_expiry, 
                       max_users, max_projects
                FROM companies WHERE id = ?
            """, (company_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {'subscription_tier': 'free', 'max_users': 5, 'max_projects': 10}
    
    def update_subscription(self, user_id: int = None, company_id: int = None,
                           tier: str = None, expiry_days: int = None) -> bool:
        """Update subscription for user or company"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if user_id:
                updates = ["subscription_tier = ?"]
                values = [tier]
                
                if expiry_days:
                    updates.append("subscription_expiry = DATE('now', ?)")
                    values.append(f"+{expiry_days} days")
                
                values.append(user_id)
                cursor.execute(f"""
                    UPDATE users 
                    SET {', '.join(updates)}
                    WHERE id = ?
                """, values)
                
            elif company_id:
                updates = ["subscription_tier = ?"]
                values = [tier]
                
                if expiry_days:
                    updates.append("subscription_expiry = DATE('now', ?)")
                    values.append(f"+{expiry_days} days")
                
                values.append(company_id)
                cursor.execute(f"""
                    UPDATE companies 
                    SET {', '.join(updates)}
                    WHERE id = ?
                """, values)
            else:
                return False
            
            return cursor.rowcount > 0
    
    def increment_api_usage(self, user_id: int) -> bool:
        """Increment API call count for user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET api_calls_used = api_calls_used + 1
                WHERE id = ? AND api_calls_used < api_calls_limit
            """, (user_id,))
            
            return cursor.rowcount > 0
    
    # ==================== TENDER ANALYSIS METHODS ====================
    
    def save_analysis(self, user_id: int, tender_id: str, analysis_data: Dict,
                     confidence_score: float = None) -> int:
        """Save tender analysis results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO tender_analyses 
                (user_id, tender_id, analysis_data, confidence_score, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, tender_id, json.dumps(analysis_data), confidence_score))
            
            return cursor.lastrowid
    
    def get_user_analyses(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user's analysis history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, tender_id, analysis_data, confidence_score, 
                       created_at, is_favorite
                FROM tender_analyses
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            
            analyses = []
            for row in cursor.fetchall():
                analysis = dict(row)
                analysis['analysis_data'] = json.loads(analysis['analysis_data'])
                analyses.append(analysis)
            
            return analyses
    
    def get_company_stats(self, company_id: int) -> Dict:
        """Get analysis statistics for a company"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get user IDs for this company
            cursor.execute("SELECT id FROM users WHERE company_id = ?", (company_id,))
            user_ids = [row['id'] for row in cursor.fetchall()]
            
            if not user_ids:
                return {'total_analyses': 0, 'avg_confidence': 0}
            
            placeholders = ','.join('?' * len(user_ids))
            cursor.execute(f"""
                SELECT COUNT(*) as total, AVG(confidence_score) as avg_conf
                FROM tender_analyses
                WHERE user_id IN ({placeholders})
            """, user_ids)
            
            row = cursor.fetchone()
            return {
                'total_analyses': row['total'] or 0,
                'avg_confidence': row['avg_conf'] or 0
            }
    
    def toggle_favorite_analysis(self, analysis_id: int, user_id: int) -> bool:
        """Toggle favorite status of an analysis"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tender_analyses
                SET is_favorite = NOT is_favorite
                WHERE id = ? AND user_id = ?
            """, (analysis_id, user_id))
            
            return cursor.rowcount > 0
    
    # ==================== HISTORICAL TENDER METHODS ====================
    
    def save_historical_tender(self, tender_data: Dict) -> int:
        """Save historical tender data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO historical_tenders
                (tender_id, title, procuring_entity, estimated_amount, awarded_amount,
                 award_date, contractor, contract_period, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tender_data.get('tender_id'),
                tender_data.get('title'),
                tender_data.get('procuring_entity'),
                tender_data.get('estimated_amount'),
                tender_data.get('awarded_amount'),
                tender_data.get('award_date'),
                tender_data.get('contractor'),
                tender_data.get('contract_period'),
                tender_data.get('category')
            ))
            
            return cursor.lastrowid
    
    def get_historical_tenders(self, filters: Dict = None, limit: int = 100) -> List[Dict]:
        """Get historical tenders with optional filters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM historical_tenders WHERE 1=1"
            values = []
            
            if filters:
                if 'procuring_entity' in filters:
                    query += " AND procuring_entity LIKE ?"
                    values.append(f"%{filters['procuring_entity']}%")
                
                if 'category' in filters:
                    query += " AND category = ?"
                    values.append(filters['category'])
                
                if 'min_amount' in filters:
                    query += " AND awarded_amount >= ?"
                    values.append(filters['min_amount'])
                
                if 'max_amount' in filters:
                    query += " AND awarded_amount <= ?"
                    values.append(filters['max_amount'])
                
                if 'from_date' in filters:
                    query += " AND award_date >= ?"
                    values.append(filters['from_date'])
                
                if 'to_date' in filters:
                    query += " AND award_date <= ?"
                    values.append(filters['to_date'])
            
            query += " ORDER BY award_date DESC LIMIT ?"
            values.append(limit)
            
            cursor.execute(query, values)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_winning_statistics(self, contractor_name: str = None) -> Dict:
        """Get winning statistics for contractors"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if contractor_name:
                cursor.execute("""
                    SELECT contractor, COUNT(*) as wins, 
                           AVG(awarded_amount) as avg_amount,
                           SUM(awarded_amount) as total_amount,
                           MIN(award_date) as first_win,
                           MAX(award_date) as last_win
                    FROM historical_tenders
                    WHERE contractor = ?
                    GROUP BY contractor
                """, (contractor_name,))
            else:
                cursor.execute("""
                    SELECT contractor, COUNT(*) as wins, 
                           AVG(awarded_amount) as avg_amount,
                           SUM(awarded_amount) as total_amount,
                           MIN(award_date) as first_win,
                           MAX(award_date) as last_win
                    FROM historical_tenders
                    WHERE contractor IS NOT NULL
                    GROUP BY contractor
                    ORDER BY wins DESC
                    LIMIT 50
                """)
            
            row = cursor.fetchone()
            return dict(row) if row else {}
    
    # ==================== COMPETITOR METHODS ====================
    
    def get_competitor_master_list(self, company_id: int) -> List[Dict]:
        """Get competitor master list for a company"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.*, 
                       COUNT(DISTINCT ct.tender_id) as tracked_tenders,
                       MAX(ct.last_updated) as last_activity
                FROM competitors c
                LEFT JOIN competitor_tracking ct ON c.id = ct.competitor_id
                WHERE c.company_id = ?
                GROUP BY c.id
                ORDER BY c.name
            """, (company_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def add_competitor_to_master(self, company_id: int, name: str, 
                                 registration_no: str = None, 
                                 website: str = None) -> int:
        """Add competitor to master list"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO competitors (company_id, name, registration_no, website)
                VALUES (?, ?, ?, ?)
            """, (company_id, name, registration_no, website))
            
            return cursor.lastrowid
    
    def update_competitor_info(self, competitor_id: int, **kwargs) -> bool:
        """Update competitor information"""
        allowed_fields = ['name', 'registration_no', 'website', 'notes']
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(competitor_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE competitors 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            return cursor.rowcount > 0
    
    def track_competitor_tender(self, competitor_id: int, tender_id: str, 
                               amount: float = None, status: str = 'tracking') -> int:
        """Track a competitor's tender activity"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO competitor_tracking (competitor_id, tender_id, amount, status)
                VALUES (?, ?, ?, ?)
            """, (competitor_id, tender_id, amount, status))
            
            return cursor.lastrowid
    
    # ==================== KNOWLEDGE REPOSITORY METHODS ====================
    
    # Personnel Management
    def add_personnel(self, company_id: int, name: str, designation: str,
                     expertise_areas: str, years_experience: int,
                     certifications: str = None, cv_path: str = None) -> int:
        """Add personnel to knowledge repository"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO personnel (company_id, name, designation, expertise_areas,
                                     years_experience, certifications, cv_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (company_id, name, designation, expertise_areas,
                  years_experience, certifications, cv_path))
            
            return cursor.lastrowid
    
    def get_personnel(self, company_id: int, expertise: str = None) -> List[Dict]:
        """Get personnel list with optional expertise filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM personnel WHERE company_id = ?"
            values = [company_id]
            
            if expertise:
                query += " AND expertise_areas LIKE ?"
                values.append(f"%{expertise}%")
            
            query += " ORDER BY years_experience DESC"
            
            cursor.execute(query, values)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_personnel(self, personnel_id: int, **kwargs) -> bool:
        """Update personnel information"""
        allowed_fields = ['name', 'designation', 'expertise_areas', 
                         'years_experience', 'certifications', 'cv_path']
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(personnel_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE personnel 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            return cursor.rowcount > 0
    
    # Equipment Management
    def add_equipment(self, company_id: int, name: str, type: str,
                     specifications: str, quantity: int, condition: str,
                     ownership: str, value: float = None) -> int:
        """Add equipment to knowledge repository"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO equipment (company_id, name, type, specifications,
                                     quantity, condition, ownership, value)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (company_id, name, type, specifications,
                  quantity, condition, ownership, value))
            
            return cursor.lastrowid
    
    def get_equipment(self, company_id: int, equipment_type: str = None) -> List[Dict]:
        """Get equipment list with optional type filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM equipment WHERE company_id = ?"
            values = [company_id]
            
            if equipment_type:
                query += " AND type = ?"
                values.append(equipment_type)
            
            query += " ORDER BY name"
            
            cursor.execute(query, values)
            return [dict(row) for row in cursor.fetchall()]
    
    # Experience Management
    def add_experience(self, company_id: int, project_name: str,
                      client_name: str, contract_value: float,
                      completion_date: str, project_type: str,
                      description: str = None) -> int:
        """Add project experience to knowledge repository"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO experiences (company_id, project_name, client_name,
                                       contract_value, completion_date,
                                       project_type, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (company_id, project_name, client_name,
                  contract_value, completion_date, project_type, description))
            
            return cursor.lastrowid
    
    def get_experiences(self, company_id: int, project_type: str = None,
                       min_value: float = None) -> List[Dict]:
        """Get project experiences with filters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM experiences WHERE company_id = ?"
            values = [company_id]
            
            if project_type:
                query += " AND project_type = ?"
                values.append(project_type)
            
            if min_value:
                query += " AND contract_value >= ?"
                values.append(min_value)
            
            query += " ORDER BY completion_date DESC"
            
            cursor.execute(query, values)
            return [dict(row) for row in cursor.fetchall()]
    
    # Financial Management
    def add_financial_capacity(self, company_id: int, fiscal_year: str,
                              annual_turnover: float, net_profit: float,
                              liquid_assets: float, credit_limit: float) -> int:
        """Add financial capacity record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO financial_records (company_id, fiscal_year, annual_turnover,
                                             net_profit, liquid_assets, credit_limit)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (company_id, fiscal_year, annual_turnover,
                  net_profit, liquid_assets, credit_limit))
            
            return cursor.lastrowid
    
    def get_financial_records(self, company_id: int, 
                             fiscal_year: str = None) -> List[Dict]:
        """Get financial records for a company"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM financial_records WHERE company_id = ?"
            values = [company_id]
            
            if fiscal_year:
                query += " AND fiscal_year = ?"
                values.append(fiscal_year)
            
            query += " ORDER BY fiscal_year DESC"
            
            cursor.execute(query, values)
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== DOCUMENT MANAGEMENT METHODS ====================
    
    def add_document(self, user_id: int, company_id: int, filename: str,
                    file_path: str, document_type: str, metadata: Dict = None) -> int:
        """Add document to repository"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documents (user_id, company_id, filename, file_path,
                                     document_type, metadata, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, company_id, filename, file_path,
                  document_type, json.dumps(metadata) if metadata else None))
            
            return cursor.lastrowid
    
    def update_document(self, document_id: int, **kwargs) -> bool:
        """Update document metadata"""
        allowed_fields = ['filename', 'document_type', 'metadata']
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                if key == 'metadata' and value:
                    value = json.dumps(value)
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(document_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE documents 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            return cursor.rowcount > 0
    
    def get_documents(self, company_id: int, document_type: str = None,
                     limit: int = 100) -> List[Dict]:
        """Get documents for a company"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT d.*, u.username as uploaded_by
                FROM documents d
                LEFT JOIN users u ON d.user_id = u.id
                WHERE d.company_id = ?
            """
            values = [company_id]
            
            if document_type:
                query += " AND d.document_type = ?"
                values.append(document_type)
            
            query += " ORDER BY d.uploaded_at DESC LIMIT ?"
            values.append(limit)
            
            cursor.execute(query, values)
            documents = []
            for row in cursor.fetchall():
                doc = dict(row)
                if doc.get('metadata'):
                    doc['metadata'] = json.loads(doc['metadata'])
                documents.append(doc)
            
            return documents
    
    def delete_document(self, document_id: int, user_id: int) -> bool:
        """Delete a document"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM documents 
                WHERE id = ? AND user_id = ?
            """, (document_id, user_id))
            
            return cursor.rowcount > 0
    
    # ==================== SEMANTIC SEARCH METHODS ====================
    
    def store_embedding(self, content_type: str, content_id: int,
                       content_text: str, embedding_blob: bytes) -> bool:
        """Store embedding vector for semantic search"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO embeddings
                (content_type, content_id, content_text, embedding, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (content_type, content_id, content_text, embedding_blob))
            
            return cursor.rowcount > 0
    
    def semantic_search(self, query_embedding: bytes, content_type: str = None,
                       limit: int = 10) -> List[Dict]:
        """
        Perform semantic search using cosine similarity
        Note: This is a simplified version. In production, use vector similarity
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # For SQLite without vector extension, we'll retrieve candidates
            # and compute similarity in Python (not efficient for large datasets)
            query = "SELECT content_type, content_id, content_text FROM embeddings"
            values = []
            
            if content_type:
                query += " WHERE content_type = ?"
                values.append(content_type)
            
            cursor.execute(query, values)
            
            # Here you would implement cosine similarity calculation
            # This is a placeholder - implement actual similarity search
            results = []
            for row in cursor.fetchall():
                results.append({
                    'content_type': row['content_type'],
                    'content_id': row['content_id'],
                    'content_text': row['content_text'],
                    'similarity_score': 0.0  # Placeholder
                })
            
            # Sort by similarity and limit
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            return results[:limit]
    
    def hybrid_search(self, query_text: str, query_embedding: bytes = None,
                     content_type: str = None, limit: int = 10) -> List[Dict]:
        """Combine keyword and semantic search"""
        # Keyword search results
        keyword_results = self.keyword_search(query_text, content_type, limit*2)
        
        # Semantic search results if embedding provided
        semantic_results = []
        if query_embedding:
            semantic_results = self.semantic_search(query_embedding, content_type, limit*2)
        
        # Merge and deduplicate results (simplified)
        all_results = keyword_results + semantic_results
        seen = set()
        unique_results = []
        
        for result in all_results:
            key = f"{result.get('content_type')}_{result.get('content_id')}"
            if key not in seen:
                seen.add(key)
                unique_results.append(result)
        
        return unique_results[:limit]
    
    def keyword_search(self, query: str, content_type: str = None,
                      limit: int = 10) -> List[Dict]:
        """Perform keyword-based search across knowledge repository"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            results = []
            
            # Search in personnel
            if not content_type or content_type == 'personnel':
                cursor.execute("""
                    SELECT 'personnel' as content_type, id as content_id,
                           name as title, expertise_areas as content,
                           designation as extra_info
                    FROM personnel
                    WHERE name LIKE ? OR expertise_areas LIKE ? OR designation LIKE ?
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
                results.extend([dict(row) for row in cursor.fetchall()])
            
            # Search in equipment
            if not content_type or content_type == 'equipment':
                cursor.execute("""
                    SELECT 'equipment' as content_type, id as content_id,
                           name as title, specifications as content,
                           type as extra_info
                    FROM equipment
                    WHERE name LIKE ? OR specifications LIKE ? OR type LIKE ?
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
                results.extend([dict(row) for row in cursor.fetchall()])
            
            # Search in experiences
            if not content_type or content_type == 'experience':
                cursor.execute("""
                    SELECT 'experience' as content_type, id as content_id,
                           project_name as title, description as content,
                           client_name as extra_info
                    FROM experiences
                    WHERE project_name LIKE ? OR description LIKE ? OR client_name LIKE ?
                    LIMIT ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
                results.extend([dict(row) for row in cursor.fetchall()])
            
            return results[:limit]
    
    # ==================== AUTO-FILL METHODS ====================
    
    def get_auto_fill_data(self, company_id: int, field_type: str) -> List[Dict]:
        """Get auto-fill suggestions based on field type"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if field_type == 'personnel':
                cursor.execute("""
                    SELECT id, name, designation, expertise_areas
                    FROM personnel
                    WHERE company_id = ?
                    ORDER BY years_experience DESC
                """, (company_id,))
                
            elif field_type == 'equipment':
                cursor.execute("""
                    SELECT id, name, type, specifications
                    FROM equipment
                    WHERE company_id = ?
                    ORDER BY name
                """, (company_id,))
                
            elif field_type == 'experience':
                cursor.execute("""
                    SELECT id, project_name, client_name, contract_value, project_type
                    FROM experiences
                    WHERE company_id = ?
                    ORDER BY completion_date DESC
                    LIMIT 20
                """, (company_id,))
                
            elif field_type == 'financial':
                cursor.execute("""
                    SELECT fiscal_year, annual_turnover, net_profit, liquid_assets
                    FROM financial_records
                    WHERE company_id = ?
                    ORDER BY fiscal_year DESC
                    LIMIT 5
                """, (company_id,))
            else:
                return []
            
            return [dict(row) for row in cursor.fetchall()]
    
    def search_knowledge_base(self, company_id: int, search_term: str,
                             category: str = None) -> List[Dict]:
        """Search across knowledge repository for auto-fill"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            results = []
            
            if not category or category == 'personnel':
                cursor.execute("""
                    SELECT 'personnel' as source, id, name, designation as info
                    FROM personnel
                    WHERE company_id = ? AND (name LIKE ? OR expertise_areas LIKE ?)
                    LIMIT 10
                """, (company_id, f"%{search_term}%", f"%{search_term}%"))
                results.extend([dict(row) for row in cursor.fetchall()])
            
            if not category or category == 'equipment':
                cursor.execute("""
                    SELECT 'equipment' as source, id, name, type as info
                    FROM equipment
                    WHERE company_id = ? AND (name LIKE ? OR type LIKE ?)
                    LIMIT 10
                """, (company_id, f"%{search_term}%", f"%{search_term}%"))
                results.extend([dict(row) for row in cursor.fetchall()])
            
            if not category or category == 'experience':
                cursor.execute("""
                    SELECT 'experience' as source, id, project_name as name,
                           client_name as info
                    FROM experiences
                    WHERE company_id = ? AND (project_name LIKE ? OR client_name LIKE ?)
                    LIMIT 10
                """, (company_id, f"%{search_term}%", f"%{search_term}%"))
                results.extend([dict(row) for row in cursor.fetchall()])
            
            return results
    
    # ==================== EXTENSION TRACKING METHODS ====================
    
    def get_extension_fill_usage(self, user_id: int, days: int = 30) -> Dict:
        """Get extension auto-fill usage statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT field_type, COUNT(*) as usage_count,
                       MAX(used_at) as last_used
                FROM extension_fill_log
                WHERE user_id = ? AND used_at >= DATE('now', ?)
                GROUP BY field_type
            """, (user_id, f"-{days} days"))
            
            usage = {row['field_type']: row['usage_count'] for row in cursor.fetchall()}
            return usage
    
    def log_extension_fill(self, user_id: int, field_type: str,
                          source_type: str, source_id: int) -> bool:
        """Log extension auto-fill usage"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO extension_fill_log (user_id, field_type, source_type, source_id)
                VALUES (?, ?, ?, ?)
            """, (user_id, field_type, source_type, source_id))
            
            return cursor.rowcount > 0
    
    # ==================== SCENARIO METHODS ====================
    
    def save_scenario(self, user_id: int, name: str, scenario_data: Dict,
                     is_shared: bool = False) -> int:
        """Save a tender scenario for future use"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            share_token = secrets.token_urlsafe(16) if is_shared else None
            
            cursor.execute("""
                INSERT INTO scenarios (user_id, name, scenario_data, is_shared, share_token)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, name, json.dumps(scenario_data), is_shared, share_token))
            
            return cursor.lastrowid
    
    def get_user_scenarios(self, user_id: int, include_shared: bool = False) -> List[Dict]:
        """Get scenarios for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if include_shared:
                cursor.execute("""
                    SELECT id, user_id, name, scenario_data, is_favorite,
                           is_shared, share_token, created_at, updated_at
                    FROM scenarios
                    WHERE user_id = ? OR is_shared = 1
                    ORDER BY is_favorite DESC, updated_at DESC
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT id, user_id, name, scenario_data, is_favorite,
                           is_shared, share_token, created_at, updated_at
                    FROM scenarios
                    WHERE user_id = ?
                    ORDER BY is_favorite DESC, updated_at DESC
                """, (user_id,))
            
            scenarios = []
            for row in cursor.fetchall():
                scenario = dict(row)
                scenario['scenario_data'] = json.loads(scenario['scenario_data'])
                scenarios.append(scenario)
            
            return scenarios
    
    def get_scenario_by_id(self, scenario_id: int, user_id: int = None) -> Optional[Dict]:
        """Get scenario by ID with optional user ownership check"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute("""
                    SELECT id, user_id, name, scenario_data, is_favorite,
                           is_shared, share_token, created_at, updated_at
                    FROM scenarios
                    WHERE id = ? AND (user_id = ? OR is_shared = 1)
                """, (scenario_id, user_id))
            else:
                cursor.execute("""
                    SELECT id, user_id, name, scenario_data, is_favorite,
                           is_shared, share_token, created_at, updated_at
                    FROM scenarios
                    WHERE id = ?
                """, (scenario_id,))
            
            row = cursor.fetchone()
            if row:
                scenario = dict(row)
                scenario['scenario_data'] = json.loads(scenario['scenario_data'])
                return scenario
            return None
    
    def delete_scenario(self, scenario_id: int, user_id: int) -> bool:
        """Delete a scenario"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM scenarios
                WHERE id = ? AND user_id = ?
            """, (scenario_id, user_id))
            
            return cursor.rowcount > 0
    
    def toggle_favorite_scenario(self, scenario_id: int, user_id: int) -> bool:
        """Toggle favorite status of a scenario"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE scenarios
                SET is_favorite = NOT is_favorite
                WHERE id = ? AND user_id = ?
            """, (scenario_id, user_id))
            
            return cursor.rowcount > 0
    
    def update_scenario_name(self, scenario_id: int, user_id: int, new_name: str) -> bool:
        """Update scenario name"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE scenarios
                SET name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
            """, (new_name, scenario_id, user_id))
            
            return cursor.rowcount > 0
    
    def share_scenario(self, scenario_id: int, user_id: int) -> Optional[str]:
        """Share a scenario and return share token"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            share_token = secrets.token_urlsafe(16)
            
            cursor.execute("""
                UPDATE scenarios
                SET is_shared = 1, share_token = ?
                WHERE id = ? AND user_id = ?
            """, (share_token, scenario_id, user_id))
            
            if cursor.rowcount > 0:
                return share_token
            return None
    
    def get_shared_scenario_by_token(self, share_token: str) -> Optional[Dict]:
        """Get shared scenario by token"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, name, scenario_data, created_at
                FROM scenarios
                WHERE share_token = ? AND is_shared = 1
            """, (share_token,))
            
            row = cursor.fetchone()
            if row:
                scenario = dict(row)
                scenario['scenario_data'] = json.loads(scenario['scenario_data'])
                return scenario
            return None
    
    # ==================== COMPANY MANAGEMENT METHODS ====================
    
    def get_all_companies_filtered(self, filters: Dict = None) -> List[Dict]:
        """Get all companies with optional filtering"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM companies WHERE 1=1"
            values = []
            
            if filters:
                if 'subscription_tier' in filters:
                    query += " AND subscription_tier = ?"
                    values.append(filters['subscription_tier'])
                
                if 'is_active' in filters:
                    query += " AND is_active = ?"
                    values.append(filters['is_active'])
                
                if 'name' in filters:
                    query += " AND name LIKE ?"
                    values.append(f"%{filters['name']}%")
            
            query += " ORDER BY name"
            
            cursor.execute(query, values)
            return [dict(row) for row in cursor.fetchall()]
    
    def create_company(self, name: str, registration_no: str = None,
                      address: str = None, phone: str = None,
                      email: str = None, subscription_tier: str = 'free') -> int:
        """Create a new company"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO companies (name, registration_no, address, phone, email,
                                     subscription_tier)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, registration_no, address, phone, email, subscription_tier))
            
            return cursor.lastrowid
    
    def update_company(self, company_id: int, **kwargs) -> bool:
        """Update company information"""
        allowed_fields = ['name', 'registration_no', 'address', 'phone', 'email',
                         'subscription_tier', 'is_active', 'max_users', 'max_projects']
        
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(company_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE companies 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
            
            return cursor.rowcount > 0
    
    def delete_company(self, company_id: int, hard_delete: bool = False) -> bool:
        """Delete or deactivate company"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if hard_delete:
                cursor.execute("DELETE FROM companies WHERE id = ?", (company_id,))
            else:
                cursor.execute("UPDATE companies SET is_active = 0 WHERE id = ?", (company_id,))
            
            return cursor.rowcount > 0
    
    # ==================== ROLE/PERMISSION METHODS ====================
    
    def get_role_permissions(self, role: str) -> List[str]:
        """Get permissions for a role"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT permission
                FROM role_permissions
                WHERE role = ?
            """, (role,))
            
            return [row['permission'] for row in cursor.fetchall()]
    
    def get_all_roles(self) -> List[Dict]:
        """Get all roles with their permissions"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, GROUP_CONCAT(permission) as permissions
                FROM role_permissions
                GROUP BY role
                ORDER BY role
            """)
            
            roles = []
            for row in cursor.fetchall():
                roles.append({
                    'role': row['role'],
                    'permissions': row['permissions'].split(',') if row['permissions'] else []
                })
            
            return roles
    
    def update_role_permissions(self, role: str, permissions: List[str]) -> bool:
        """Update permissions for a role"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete existing permissions
            cursor.execute("DELETE FROM role_permissions WHERE role = ?", (role,))
            
            # Insert new permissions
            for permission in permissions:
                cursor.execute("""
                    INSERT INTO role_permissions (role, permission)
                    VALUES (?, ?)
                """, (role, permission))
            
            return True
    
    # ==================== PWD/LGED RATE METHODS ====================
    
    def get_pwd_chapters(self) -> List[Dict]:
        """Get all PWD schedule chapters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT chapter_code, chapter_name, version, effective_date
                FROM pwd_schedule
                WHERE parent_code IS NULL
                ORDER BY chapter_code
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_lged_chapters(self) -> List[Dict]:
        """Get all LGED schedule chapters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT chapter_code, chapter_name, version, effective_date
                FROM lged_schedule
                WHERE parent_code IS NULL
                ORDER BY chapter_code
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_pwd_children(self, parent_code: str) -> List[Dict]:
        """Get child items for a PWD schedule parent"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT item_code, description, unit, rate_bdt, parent_code
                FROM pwd_schedule
                WHERE parent_code = ?
                ORDER BY item_code
            """, (parent_code,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_pwd_stats(self, chapter_code: str = None) -> Dict:
        """Get statistics for PWD schedule"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT COUNT(*) as total_items,
                       AVG(rate_bdt) as avg_rate,
                       MIN(rate_bdt) as min_rate,
                       MAX(rate_bdt) as max_rate
                FROM pwd_schedule
                WHERE rate_bdt IS NOT NULL
            """
            values = []
            
            if chapter_code:
                query += " AND chapter_code = ?"
                values.append(chapter_code)
            
            cursor.execute(query, values)
            row = cursor.fetchone()
            
            return dict(row) if row else {}
    
    def search_pwd_schedule(self, search_term: str, limit: int = 50) -> List[Dict]:
        """Search PWD schedule items"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT item_code, description, unit, rate_bdt, chapter_code, chapter_name
                FROM pwd_schedule
                WHERE description LIKE ? OR item_code LIKE ?
                ORDER BY item_code
                LIMIT ?
            """, (f"%{search_term}%", f"%{search_term}%", limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def search_lged_schedule(self, search_term: str, limit: int = 50) -> List[Dict]:
        """Search LGED schedule items"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT item_code, description, unit, rate_bdt, chapter_code, chapter_name
                FROM lged_schedule
                WHERE description LIKE ? OR item_code LIKE ?
                ORDER BY item_code
                LIMIT ?
            """, (f"%{search_term}%", f"%{search_term}%", limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_rate_by_item_code(self, schedule_type: str, item_code: str) -> Optional[Dict]:
        """Get rate by item code from specified schedule"""
        table = 'pwd_schedule' if schedule_type == 'pwd' else 'lged_schedule'
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT item_code, description, unit, rate_bdt, chapter_code, chapter_name
                FROM {table}
                WHERE item_code = ?
            """, (item_code,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def calculate_win_probability(tender_id, user_total_cost):
        """
        Evaluates historical competitor price ranges for the same tender 
        to calculate a statistical win probability percentage.
        """
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT total_bid_amount FROM competitor_bids WHERE tender_id = ?"
        df_comp = pd.read_sql_query(query, conn, params=(tender_id,))
        conn.close()
        
        if df_comp.empty:
            return None, "No data available"
            
        all_bids = df_comp['total_bid_amount'].tolist()
        all_bids.append(user_total_cost)
        all_bids.sort()
        
        # Find rank index positioning (Lower price is preferred in e-GP L1 procurement formats)
        rank = all_bids.index(user_total_cost) + 1
        total_bidders = len(all_bids)
        
        # Calculate probability: higher ranking position results in a stronger win margin
        probability = ((total_bidders - rank) / total_bidders) * 100
        return round(probability, 1), f"Rank {rank} of {total_bidders}"

    
    @st.cache_data(ttl=300)
    def get_company_tenders_cached(company_id: int) -> pd.DataFrame:
        """Cached helper to fetch company tenders as DataFrame"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT 
                t.id, t.company_id, t.tender_id, t.tender_title, t.procuring_entity,
                t.division, t.district, t.thana, t.country, t.procurement_type,
                t.official_estimate, t.submission_deadline, t.tender_security,
                t.document_fee, t.evaluation_type,
                t.is_locked, t.is_copy, t.original_tender_id, t.is_active,
                t.created_at, t.updated_at
            FROM company_tenders t
            WHERE t.company_id = ? 
            ORDER BY t.created_at DESC
            ''', (company_id,))
            
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            conn.close()
            
            return pd.DataFrame(data, columns=columns) if data else pd.DataFrame()
            
        except Exception as e:
            print(f"Failed to fetch cached tenders: {e}")
            return pd.DataFrame()
# Create singleton instance
db = UnifiedDatabaseManager()