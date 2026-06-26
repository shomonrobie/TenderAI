
from database.unified_db_manager import db

# 1. Check Babui's company
print("=" * 60)
print("🔍 CHECKING BABUI COMPANY")
print("=" * 60)

# Get Babui company by name
babui = db.get_company_by_name('Babui')

if babui:
    babui_id = babui['id']
    print(f"✅ Babui Company ID: {babui_id}")
    print(f"   Company Name: {babui.get('company_name')}")
    print(f"   Email: {babui.get('email')}")
else:
    print("❌ Babui company not found!")

# 2. Get shomonrobie's current data
print("\n" + "=" * 60)
print("👤 SHOMONROBIE CURRENT DATA")
print("=" * 60)

user = db.get_user_by_id(7738)
if user:
    print(f"   Username: {user.get('username')}")
    print(f"   Role: {user.get('role')}")
    print(f"   Current Company ID: {user.get('company_id')}")
    print(f"   Email: {user.get('email')}")
    
    # Get current company name
    if user.get('company_id'):
        current_company = db.get_company_by_id(user['company_id'])
        if current_company:
            print(f"   Current Company Name: {current_company.get('company_name')}")
        else:
            print(f"   ⚠️ Company {user['company_id']} not found!")

# 3. Update shomonrobie's company to Babui
if babui and user:
    print("\n" + "=" * 60)
    print("🔄 UPDATING SHOMONROBIE'S COMPANY")
    print("=" * 60)
    
    # Update the user's company_id to Babui
    success = db.update_user(7738, {'company_id': babui_id})
    
    if success:
        print(f"✅ Updated shomonrobie's company_id to {babui_id} (Babui)")
        
        # Verify the update
        updated_user = db.get_user_by_id(7738)
        if updated_user:
            print(f"   ✅ Verification: Company ID is now {updated_user.get('company_id')}")
            
            # Get new company name
            new_company = db.get_company_by_id(updated_user['company_id'])
            if new_company:
                print(f"   ✅ Company Name: {new_company.get('company_name')}")
    else:
        print("❌ Failed to update user!")

# 4. Check if there are any other users in company 1 that should be moved
print("\n" + "=" * 60)
print("📊 COMPANY 1 USERS")
print("=" * 60)

users = db.get_all_users_filtered(company_id=1, limit=100, offset=0)
if users:
    print(f"Found {users[1]} users in company 1:")
    for u in users[0][:10]:  # Show first 10
        print(f"   - {u.get('username')} ({u.get('role')})")
else:
    print("No users found in company 1")