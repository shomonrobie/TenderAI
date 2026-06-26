# scripts/create_test_users.py

"""
Test User Creation Script for TenderAI
Run this script to create test users with different roles and subscription plans
Usage: python scripts/create_test_users.py
"""

import sys
import os
import bcrypt
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from modules.subscription_manager import PLANS

class TestUserCreator:
    def __init__(self):
        self.db = DatabaseManager()
        # Ensure subscription_plans table exists
        self._init_subscription_plans()
    
    def _init_subscription_plans(self):
        """Initialize subscription_plans table"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
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
            ('basic', 'company', 4999, 49990, 30, 30, 30, 3, 1, 0, 0, 0, 0, 'Basic plan for small businesses'),
            ('professional', 'company', 14999, 149990, 100, 100, -1, 10, 1, 1, 0, 1, 1, 'Professional plan for growing businesses'),
            ('enterprise', 'company', 49999, 499990, -1, -1, -1, -1, 1, 1, 1, 1, 1, 'Enterprise plan with unlimited features')
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
        
        conn.commit()
        conn.close()
        print("✅ Subscription plans table initialized")
    
    def create_company(self, name, email, phone, division="Dhaka"):
        """Create a test company"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO companies (company_name, email, phone, division, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (name, email, phone, division))
        
        conn.commit()
        cursor.execute("SELECT id FROM companies WHERE company_name = ?", (name,))
        result = cursor.fetchone()
        company_id = result[0] if result else None
        conn.close()
        
        if company_id:
            print(f"✅ Created company: {name} (ID: {company_id})")
        return company_id
    
    def create_user(self, company_id, username, email, full_name, role, password="Test@123", is_approved=1):
        """Create a test user"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        cursor.execute("""
            INSERT OR IGNORE INTO users (
                company_id, username, password, email, full_name, role, 
                is_active, is_approved, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (company_id, username, hashed_password, email, full_name, role, is_approved, datetime.now()))
        
        conn.commit()
        
        if cursor.lastrowid:
            user_id = cursor.lastrowid
            print(f"✅ Created user: {username} ({role}) - ID: {user_id}")
            conn.close()
            return user_id
        else:
            # User might exist, try to get existing
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
    
    # Update the create_subscription method in create_test_users.py

    def create_subscription(self, company_id, plan, duration='monthly'):
        """Create subscription for a company"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        start_date = datetime.now().date()
        plan_config = PLANS.get(plan, PLANS['free'])
        
        if duration == 'monthly':
            end_date = start_date + timedelta(days=30)
        else:
            end_date = start_date + timedelta(days=365)
        
        # Check if subscription exists
        cursor.execute("SELECT id FROM subscriptions WHERE company_id = ?", (company_id,))
        existing = cursor.fetchone()
        
        # Set values based on plan
        max_boq = plan_config.get('max_boq_generations', 5)
        max_bid = plan_config.get('max_bid_optimizations', 5)
        max_analyses = plan_config.get('analyses_limit', 5)
        can_export = 1 if plan_config.get('can_export_data', False) else 0
        can_edit = 1 if plan_config.get('can_edit_rates', False) else 0
        can_delete = 1 if plan_config.get('can_delete_rates', False) else 0
        can_create = 1 if plan_config.get('can_create_versions', False) else 0
        can_manage = 1 if plan_config.get('can_manage_team', False) else 0
        
        if existing:
            cursor.execute("""
                UPDATE subscriptions 
                SET plan = ?, status = 'active', start_date = ?, end_date = ?,
                    analyses_limit = ?, analyses_used = 0,
                    max_boq_generations = ?, max_bid_optimizations = ?,
                    can_edit_rates = ?, can_delete_rates = ?, can_create_versions = ?,
                    can_export_data = ?, can_manage_team = ?,
                    updated_at = ?
                WHERE company_id = ?
            """, (
                plan, start_date, end_date,
                max_analyses,
                max_boq, max_bid,
                can_edit, can_delete, can_create,
                can_export, can_manage,
                datetime.now(), company_id
            ))
        else:
            cursor.execute("""
                INSERT INTO subscriptions (
                    company_id, plan, status, start_date, end_date,
                    analyses_limit, max_boq_generations, max_bid_optimizations,
                    can_edit_rates, can_delete_rates, can_create_versions,
                    can_export_data, can_manage_team
                ) VALUES (?, ?, 'active', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id, plan, start_date, end_date,
                max_analyses, max_boq, max_bid,
                can_edit, can_delete, can_create,
                can_export, can_manage
            ))
        
        conn.commit()
        conn.close()
        print(f"✅ Created {plan} subscription for company (Duration: {duration})")

    def create_test_data(self):
        """Create all test data"""
        
        print("\n" + "=" * 60)
        print("🔧 CREATING TEST USERS WITH DIFFERENT ROLES")
        print("=" * 60 + "\n")
        
        # ========== 1. SYSTEM ADMIN ==========
        print("\n📌 Creating SYSTEM ADMIN...")
        admin_company = self.create_company("System Admin Company", "admin@tenderai.com", "0000000000")
        if admin_company:
            admin_user = self.create_user(
                company_id=admin_company,
                username="system_admin",
                email="admin@tenderai.com",
                full_name="System Administrator",
                role="system_admin",
                password="Admin@123"
            )
            self.create_subscription(admin_company, "enterprise", "yearly")
        
        # ========== 2. FREE PLAN COMPANY ==========
        print("\n📌 Creating FREE PLAN COMPANY...")
        free_company = self.create_company("ABC Free Construction", "free@abcconstruction.com", "01710000001", "Dhaka")
        
        if free_company:
            # Company Admin
            self.create_user(
                company_id=free_company,
                username="free_admin",
                email="free_admin@abcconstruction.com",
                full_name="Free Company Admin",
                role="company_admin",
                password="Free@123"
            )
            
            # Manager
            self.create_user(
                company_id=free_company,
                username="free_manager",
                email="free_manager@abcconstruction.com",
                full_name="Free Manager",
                role="manager",
                password="Free@123"
            )
            
            # Analyst
            self.create_user(
                company_id=free_company,
                username="free_analyst",
                email="free_analyst@abcconstruction.com",
                full_name="Free Analyst",
                role="analyst",
                password="Free@123"
            )
            
            # Viewer
            self.create_user(
                company_id=free_company,
                username="free_viewer",
                email="free_viewer@abcconstruction.com",
                full_name="Free Viewer",
                role="viewer",
                password="Free@123"
            )
            
            self.create_subscription(free_company, "free", "monthly")
        
        # ========== 3. BASIC PLAN COMPANY ==========
        print("\n📌 Creating BASIC PLAN COMPANY...")
        basic_company = self.create_company("XYZ Basic Construction", "basic@xyzconstruction.com", "01710000002", "Chattogram")
        
        if basic_company:
            self.create_user(
                company_id=basic_company,
                username="basic_admin",
                email="basic_admin@xyzconstruction.com",
                full_name="Basic Company Admin",
                role="company_admin",
                password="Basic@123"
            )
            
            self.create_user(
                company_id=basic_company,
                username="basic_manager",
                email="basic_manager@xyzconstruction.com",
                full_name="Basic Manager",
                role="manager",
                password="Basic@123"
            )
            
            self.create_user(
                company_id=basic_company,
                username="basic_analyst",
                email="basic_analyst@xyzconstruction.com",
                full_name="Basic Analyst",
                role="analyst",
                password="Basic@123"
            )
            
            self.create_subscription(basic_company, "basic", "monthly")
        
        # ========== 4. PROFESSIONAL PLAN COMPANY ==========
        print("\n📌 Creating PROFESSIONAL PLAN COMPANY...")
        pro_company = self.create_company("Professional Construction Ltd", "pro@proconstruction.com", "01710000003", "Khulna")
        
        if pro_company:
            self.create_user(
                company_id=pro_company,
                username="pro_admin",
                email="pro_admin@proconstruction.com",
                full_name="Professional Admin",
                role="company_admin",
                password="Pro@123"
            )
            
            self.create_user(
                company_id=pro_company,
                username="pro_manager",
                email="pro_manager@proconstruction.com",
                full_name="Professional Manager",
                role="manager",
                password="Pro@123"
            )
            
            self.create_user(
                company_id=pro_company,
                username="pro_analyst",
                email="pro_analyst@proconstruction.com",
                full_name="Professional Analyst",
                role="analyst",
                password="Pro@123"
            )
            
            self.create_user(
                company_id=pro_company,
                username="pro_data_entry",
                email="pro_data@proconstruction.com",
                full_name="Professional Data Entry",
                role="data_entry",
                password="Pro@123"
            )
            
            self.create_subscription(pro_company, "professional", "yearly")
        
        # ========== 5. ENTERPRISE PLAN COMPANY ==========
        print("\n📌 Creating ENTERPRISE PLAN COMPANY...")
        enterprise_company = self.create_company("Enterprise Mega Construction", "enterprise@megaconstruction.com", "01710000004", "Rajshahi")
        
        if enterprise_company:
            self.create_user(
                company_id=enterprise_company,
                username="enterprise_admin",
                email="enterprise_admin@megaconstruction.com",
                full_name="Enterprise Admin",
                role="company_admin",
                password="Enterprise@123"
            )
            
            self.create_user(
                company_id=enterprise_company,
                username="enterprise_manager",
                email="enterprise_manager@megaconstruction.com",
                full_name="Enterprise Manager",
                role="manager",
                password="Enterprise@123"
            )
            
            self.create_user(
                company_id=enterprise_company,
                username="enterprise_analyst",
                email="enterprise_analyst@megaconstruction.com",
                full_name="Enterprise Analyst",
                role="analyst",
                password="Enterprise@123"
            )
            
            self.create_subscription(enterprise_company, "enterprise", "yearly")
        
        # ========== 6. INDIVIDUAL USER ==========
        print("\n📌 Creating INDIVIDUAL USER...")
        individual_company = self.create_company("Rahim Khan - Individual", "rahim.khan@email.com", "01710000005", "Dhaka")
        
        if individual_company:
            self.create_user(
                company_id=individual_company,
                username="rahim_khan",
                email="rahim.khan@email.com",
                full_name="Rahim Khan",
                role="analyst",
                password="Individual@123"
            )
            
            self.create_subscription(individual_company, "professional", "monthly")
        
        print("\n" + "=" * 60)
        print("✅ TEST USERS CREATED SUCCESSFULLY!")
        print("=" * 60)
        
        return {
            'admin': {'username': 'system_admin', 'password': 'Admin@123', 'role': 'system_admin'},
            'free': {
                'company_admin': {'username': 'free_admin', 'password': 'Free@123', 'role': 'company_admin'},
                'manager': {'username': 'free_manager', 'password': 'Free@123', 'role': 'manager'},
                'analyst': {'username': 'free_analyst', 'password': 'Free@123', 'role': 'analyst'},
                'viewer': {'username': 'free_viewer', 'password': 'Free@123', 'role': 'viewer'}
            },
            'basic': {
                'company_admin': {'username': 'basic_admin', 'password': 'Basic@123', 'role': 'company_admin'},
                'manager': {'username': 'basic_manager', 'password': 'Basic@123', 'role': 'manager'},
                'analyst': {'username': 'basic_analyst', 'password': 'Basic@123', 'role': 'analyst'}
            },
            'professional': {
                'company_admin': {'username': 'pro_admin', 'password': 'Pro@123', 'role': 'company_admin'},
                'manager': {'username': 'pro_manager', 'password': 'Pro@123', 'role': 'manager'},
                'analyst': {'username': 'pro_analyst', 'password': 'Pro@123', 'role': 'analyst'},
                'data_entry': {'username': 'pro_data_entry', 'password': 'Pro@123', 'role': 'data_entry'}
            },
            'enterprise': {
                'company_admin': {'username': 'enterprise_admin', 'password': 'Enterprise@123', 'role': 'company_admin'},
                'manager': {'username': 'enterprise_manager', 'password': 'Enterprise@123', 'role': 'manager'},
                'analyst': {'username': 'enterprise_analyst', 'password': 'Enterprise@123', 'role': 'analyst'}
            },
            'individual': {'username': 'rahim_khan', 'password': 'Individual@123', 'role': 'analyst'}
        }


def print_summary(users):
    """Print summary of all test users"""
    print("\n" + "=" * 60)
    print("📋 TEST USERS SUMMARY")
    print("=" * 60)
    
    print("\n👑 SYSTEM ADMIN:")
    print(f"   Username: {users['admin']['username']}")
    print(f"   Password: {users['admin']['password']}")
    print(f"   Role: {users['admin']['role']}")
    
    print("\n💰 FREE PLAN COMPANY (ABC Free Construction):")
    for role, creds in users['free'].items():
        print(f"   {role.title()}: {creds['username']} / {creds['password']}")
    
    print("\n📊 BASIC PLAN COMPANY (XYZ Basic Construction):")
    for role, creds in users['basic'].items():
        print(f"   {role.title()}: {creds['username']} / {creds['password']}")
    
    print("\n🚀 PROFESSIONAL PLAN COMPANY (Professional Construction Ltd):")
    for role, creds in users['professional'].items():
        print(f"   {role.title()}: {creds['username']} / {creds['password']}")
    
    print("\n🏢 ENTERPRISE PLAN COMPANY (Enterprise Mega Construction):")
    for role, creds in users['enterprise'].items():
        print(f"   {role.title()}: {creds['username']} / {creds['password']}")
    
    print("\n👤 INDIVIDUAL USER:")
    print(f"   {users['individual']['username']} / {users['individual']['password']}")
    
    print("\n" + "=" * 60)
    print("✅ All test users created!")
    print("=" * 60)
    
    print("\n💡 Test these users by logging into the application:")
    print("   1. Open the app and logout if already logged in")
    print("   2. Login with any username/password above")
    print("   3. Navigate through pages to verify permissions")
    print("   4. Check BOQ generation limits and rate editing permissions")


if __name__ == "__main__":
    creator = TestUserCreator()
    users = creator.create_test_data()
    print_summary(users)
    print("\n✅ Script completed!")