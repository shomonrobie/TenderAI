# migrate_to_supabase.py
# Run this script to migrate data from SQLite to Supabase

import sqlite3
import streamlit as st
from database.supabase_manager import SupabaseManager
from datetime import datetime
import bcrypt
import json

def get_sqlite_connection():
    """Get SQLite connection"""
    return sqlite3.connect('data/tender_system.db')

def migrate_users():
    """Migrate users from SQLite to Supabase"""
    print("\n" + "="*60)
    print("🔄 MIGRATING USERS")
    print("="*60)
    
    conn = get_sqlite_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all users
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    print(f"📊 Found {len(users)} users in SQLite")
    
    db = SupabaseManager()
    
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    for user in users:
        user_dict = dict(user)
        user_id = user_dict.pop('id', None)
        email = user_dict.get('email')
        
        # Check if user already exists in Supabase
        existing = db.get_user_by_email(email)
        if existing:
            print(f"  ⏭️ Skipping existing user: {email}")
            skipped_count += 1
            continue
        
        # Handle password - keep as is (already hashed)
        if 'password' in user_dict and not user_dict['password']:
            user_dict['password'] = None
        
        # Create user in Supabase
        success, result = db.create_user(
            company_id=user_dict.get('company_id'),
            user_data=user_dict,
            created_by=user_dict.get('created_by')
        )
        
        if success:
            print(f"  ✅ Migrated user: {email} -> ID: {result}")
            success_count += 1
        else:
            print(f"  ❌ Failed to migrate user: {email} - {result}")
            fail_count += 1
    
    print(f"\n📊 Users Migration Summary:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed: {fail_count}")
    print(f"   ⏭️ Skipped: {skipped_count}")
    
    conn.close()
    return success_count, fail_count

def migrate_companies():
    """Migrate companies from SQLite to Supabase"""
    print("\n" + "="*60)
    print("🔄 MIGRATING COMPANIES")
    print("="*60)
    
    conn = get_sqlite_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM companies")
    companies = cursor.fetchall()
    print(f"📊 Found {len(companies)} companies in SQLite")
    
    db = SupabaseManager()
    
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    for company in companies:
        company_dict = dict(company)
        company_id = company_dict.pop('id', None)
        company_name = company_dict.get('company_name')
        
        # Skip if company already exists in Supabase
        existing = db.get_company_by_name(company_name)
        if existing:
            print(f"  ⏭️ Skipping existing company: {company_name}")
            skipped_count += 1
            continue
        
        result = db.create_company(company_dict)
        
        if result:
            print(f"  ✅ Migrated company: {company_name} -> ID: {result}")
            success_count += 1
        else:
            print(f"  ❌ Failed to migrate company: {company_name}")
            fail_count += 1
    
    print(f"\n📊 Companies Migration Summary:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed: {fail_count}")
    print(f"   ⏭️ Skipped: {skipped_count}")
    
    conn.close()
    return success_count, fail_count

def migrate_otp_verification():
    """Migrate OTP verification records"""
    print("\n" + "="*60)
    print("🔄 MIGRATING OTP VERIFICATION")
    print("="*60)
    
    conn = get_sqlite_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM otp_verification")
    records = cursor.fetchall()
    print(f"📊 Found {len(records)} OTP records in SQLite")
    
    db = SupabaseManager()
    
    success_count = 0
    fail_count = 0
    
    for record in records:
        record_dict = dict(record)
        record_dict.pop('id', None)  # Remove id, let Supabase generate
        
        try:
            result = db.conn.table('otp_verification').insert(record_dict).execute()
            if result.data:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  ❌ Failed to migrate OTP record: {e}")
            fail_count += 1
    
    print(f"\n📊 OTP Migration Summary:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed: {fail_count}")
    
    conn.close()
    return success_count, fail_count

def migrate_subscription_plans():
    """Migrate subscription plans"""
    print("\n" + "="*60)
    print("🔄 MIGRATING SUBSCRIPTION PLANS")
    print("="*60)
    
    conn = get_sqlite_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM subscription_plans")
    plans = cursor.fetchall()
    print(f"📊 Found {len(plans)} plans in SQLite")
    
    db = SupabaseManager()
    
    success_count = 0
    fail_count = 0
    
    for plan in plans:
        plan_dict = dict(plan)
        plan_name = plan_dict.get('plan_name')
        plan_dict.pop('id', None)
        
        # Check if plan exists
        try:
            existing = db.conn.table('subscription_plans').select('*').eq('plan_name', plan_name).execute()
            if existing.data:
                print(f"  ⏭️ Skipping existing plan: {plan_name}")
                continue
        except:
            pass
        
        try:
            result = db.conn.table('subscription_plans').insert(plan_dict).execute()
            if result.data:
                print(f"  ✅ Migrated plan: {plan_name}")
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  ❌ Failed to migrate plan {plan_name}: {e}")
            fail_count += 1
    
    print(f"\n📊 Plans Migration Summary:")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed: {fail_count}")
    
    conn.close()
    return success_count, fail_count

def main():
    """Run all migrations"""
    print("\n" + "="*60)
    print("🚀 STARTING MIGRATION TO SUPABASE")
    print("="*60)
    
    # Migrate companies first (users depend on companies)
    comp_success, comp_fail = migrate_companies()
    
    # Then migrate users
    user_success, user_fail = migrate_users()
    
    # Migrate other tables
    otp_success, otp_fail = migrate_otp_verification()
    plan_success, plan_fail = migrate_subscription_plans()
    
    print("\n" + "="*60)
    print("📊 MIGRATION SUMMARY")
    print("="*60)
    print(f"   Companies: ✅ {comp_success} | ❌ {comp_fail}")
    print(f"   Users:     ✅ {user_success} | ❌ {user_fail}")
    print(f"   OTP:       ✅ {otp_success} | ❌ {otp_fail}")
    print(f"   Plans:     ✅ {plan_success} | ❌ {plan_fail}")
    print("="*60)
    print("🎉 Migration complete!")

if __name__ == "__main__":
    main()