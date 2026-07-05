# modules/profile_module.py

import streamlit as st
import re
import hashlib
import os
from datetime import datetime
from PIL import Image
import io
from database.unified_db_manager import get_db_manager
import base64
import traceback

# ✅ Get db instance at module level (but it will be cached)
_db = None

def get_db():
    global _db
    if _db is None:
        _db = get_db_manager()
    return _db


def render_user_profile():
    """Render the user profile page with all features"""
    
    # Check if user is logged in
    if 'user_id' not in st.session_state:
        st.error("Please log in to view your profile")
        return
    
    user_id = st.session_state.user_id
    db = get_db()

    # Get user data
    user = db.get_user_by_id(user_id)
    if not user:
        st.error("User not found")
        return
    
    # Get social links
    social_links = db.get_user_social_links(user_id)
    
    # Page header
    st.markdown("""
    <div class="main-header">
        <h1>👤 My Profile</h1>
        <p>Manage your personal information, password, and social media links</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Profile Information", 
        "🔑 Change Password", 
        "🖼️ Profile Picture",
        "🔗 Social Media Links"
    ])
    
    # ========== TAB 1: PROFILE INFORMATION ==========
    with tab1:
        render_profile_information(user)
    
    # ========== TAB 2: CHANGE PASSWORD ==========
    with tab2:
        render_change_password(user_id)
    
    # ========== TAB 3: PROFILE PICTURE ==========
    with tab3:
        render_profile_picture(user_id, user)
    
    # ========== TAB 4: SOCIAL MEDIA LINKS ==========
    with tab4:
        render_social_media_links(user_id, social_links)
    
    # Activity log section (optional)
    with st.expander("📊 Recent Activity"):
        render_activity_log(user_id)

def render_profile_information(user):
    """Render profile information edit form"""
    st.markdown("### 📝 Personal Information")
    st.markdown("Update your personal details below")
    
    with st.form("profile_info_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input(
                "Full Name *", 
                value=user.get('full_name', ''),
                help="Your full name as it appears on the platform"
            )
            
            email = st.text_input(
                "Email *", 
                value=user.get('email', ''),
                help="Your email address (cannot be changed)"
            )
            
            username = st.text_input(
                "Username *", 
                value=user.get('username', ''),
                help="Your unique username"
            )
            
        with col2:
            phone = st.text_input(
                "Phone", 
                value=user.get('phone', '') or '',
                help="Your phone number"
            )
            
            mobile_number = st.text_input(
                "Mobile Number *", 
                value=user.get('mobile_number', ''),
                help="Your primary mobile number"
            )
            
            location = st.text_input(
                "Location", 
                value=user.get('location', '') or '',
                help="Your city, state, or country"
            )
        
        # Bio
        bio = st.text_area(
            "Bio",
            value=user.get('bio', '') or '',
            help="A brief description about yourself (max 500 characters)",
            max_chars=500
        )
        
        # Read-only fields
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Role:** {user.get('role', 'user').replace('_', ' ').title()}")
            st.info(f"**Account Type:** {user.get('account_type', 'company').title()}")
        with col2:
            st.info(f"**Joined:** {user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'}")
            st.info(f"**Last Login:** {user.get('last_login', 'Never')[:10] if user.get('last_login') else 'Never'}")
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Profile Changes", type="primary")
        
        if submitted:
            # Validate inputs
            if not full_name:
                st.error("Full name is required")
            elif not email:
                st.error("Email is required")
            elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                st.error("Invalid email format")
            elif not username:
                st.error("Username is required")
            elif not mobile_number:
                st.error("Mobile number is required")
            else:
                # Update user data using dictionary
                updates = {
                    'full_name': full_name.strip(),
                    'email': email.strip(),
                    'username': username.strip(),
                    'phone': phone.strip() if phone else None,
                    'mobile_number': mobile_number.strip(),
                    'location': location.strip() if location else None,
                    'bio': bio.strip() if bio else None
                }
                db = get_db()

                # ✅ FIX: Pass as dictionary, not kwargs
                success = db.update_user(user.get('id'), updates)
                
                if success:
                    # Log activity
                    db.log_user_activity(user.get('id'), 'profile_update', 'Updated profile information')
                    st.success("✅ Profile information updated successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to update profile. Please try again.")

def render_change_password(user_id):
    """Render password change form"""
    st.markdown("### 🔑 Change Password")
    st.markdown("Choose a strong password that you don't use for other accounts")
    
    # Password strength indicator
    col1, col2 = st.columns([2, 1])
    with col1:
        current_password = st.text_input(
            "Current Password *", 
            type="password",
            help="Enter your current password to verify your identity"
        )
        
        new_password = st.text_input(
            "New Password *", 
            type="password",
            help="Must be at least 8 characters with uppercase, lowercase, number, and special character"
        )
        
        confirm_password = st.text_input(
            "Confirm New Password *", 
            type="password",
            help="Re-enter your new password to confirm"
        )
        
        # Password strength indicator
        if new_password:
            score, msg, color = validate_password_strength(new_password)
            st.progress(score / 100)
            st.markdown(f"<small style='color:{color}'>{msg}</small>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### Password Requirements:")
        st.markdown("""
        - ✅ At least 8 characters  
        - ✅ Uppercase letter  
        - ✅ Lowercase letter  
        - ✅ Number  
        - ✅ Special character
        """)
        
        # Password tips
        st.info("💡 Tip: Use a passphrase like 'Coffee$Morning2024!' for better security")
    
    # Submit button
    if st.button("🔐 Update Password", type="primary", use_container_width=False):
        if not current_password:
            st.error("Please enter your current password")
        elif not new_password:
            st.error("Please enter a new password")
        elif new_password != confirm_password:
            st.error("New passwords do not match")
        elif len(new_password) < 8:
            st.error("Password must be at least 8 characters long")
        else:
            db = get_db()

            # Verify current password and update
            success, message = db.change_user_password(user_id, current_password, new_password)
            
            if success:
                st.success("✅ Password changed successfully!")
                db.log_user_activity(user_id, 'password_change', 'Changed password')
                st.balloons()
            else:
                st.error(f"❌ {message}")

# modules/profile_module.py - Debug version

import streamlit as st
import re
import os
from datetime import datetime
from PIL import Image
import io
import base64
import traceback
from database.unified_db_manager import get_db_manager

_db = None

def get_db():
    global _db
    if _db is None:
        _db = get_db_manager()
    return _db

# modules/profile_module.py - Fixed update with complete base64 data

def render_profile_picture(user_id, user):
    """Render profile picture upload and management"""
    st.markdown("### 🖼️ Profile Picture")
    
    # Current avatar
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### Current Picture")
        avatar_url = user.get('avatar_url')
        
        if avatar_url:
            try:
                if avatar_url.startswith('data:image'):
                    st.image(avatar_url, width=200, caption="Current Profile Picture")
                else:
                    st.image(avatar_url, width=200, caption="Current Profile Picture")
            except Exception as e:
                st.warning(f"Could not load image: {e}")
                name = user.get('full_name', 'User')
                st.image(f"https://ui-avatars.com/api/?name={name}&size=200&background=6366f1&color=ffffff", 
                        width=200, caption="No Profile Picture")
        else:
            name = user.get('full_name', 'User')
            st.image(f"https://ui-avatars.com/api/?name={name}&size=200&background=6366f1&color=ffffff", 
                    width=200, caption="No Profile Picture")
    
    with col2:
        st.markdown("#### Upload New Picture")
        
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=['jpg', 'jpeg', 'png', 'gif'],
            help="Supported formats: JPG, JPEG, PNG, GIF (Max 5MB)"
        )
        
        if uploaded_file is not None:
            if uploaded_file.size > 5 * 1024 * 1024:
                st.error("File size exceeds 5MB limit")
            else:
                try:
                    image = Image.open(uploaded_file)
                    image.thumbnail((150, 150))
                    st.image(image, width=150, caption="Preview")
                    
                    if st.button("📤 Upload Profile Picture", type="primary"):
                        with st.spinner("Uploading..."):
                            try:
                                # ✅ Generate full base64 data
                                success, avatar_data = save_avatar_image_complete(uploaded_file, user_id)
                                
                                if success and avatar_data:
                                    db = get_db()
                                    
                                    # ✅ Use direct Supabase update with the full data
                                    if db._use_supabase and db.supabase:
                                        print(f"🔍 Updating avatar for user {user_id}")
                                        print(f"🔍 Avatar data length: {len(avatar_data)}")
                                        
                                        response = db.supabase.table('users')\
                                            .update({
                                                'avatar_url': avatar_data,
                                                'updated_at': datetime.now().isoformat()
                                            })\
                                            .eq('id', user_id)\
                                            .execute()
                                        
                                        print(f"🔍 Response: {response}")
                                        
                                        if response.data:
                                            # ✅ Verify the update
                                            verified = db.query_one("SELECT avatar_url FROM users WHERE id = ?", (user_id,))
                                            if verified and verified.get('avatar_url'):
                                                db.log_user_activity(user_id, 'avatar_update', 'Updated profile picture')
                                                st.success("✅ Profile picture updated successfully!")
                                                st.balloons()
                                                st.rerun()
                                            else:
                                                st.error("❌ Avatar was not saved properly. Please try again.")
                                        else:
                                            st.error(f"❌ Failed to update avatar: {response}")
                                    else:
                                        # Fallback to update_user
                                        updates = {'avatar_url': avatar_data}
                                        success = db.update_user(user_id, updates)
                                        if success:
                                            st.success("✅ Profile picture updated successfully!")
                                            st.balloons()
                                            st.rerun()
                                        else:
                                            st.error("❌ Failed to update profile picture")
                                else:
                                    st.error("❌ Failed to process image")
                            except Exception as e:
                                print(f"❌ Error: {e}")
                                import traceback
                                traceback.print_exc()
                                st.error(f"❌ Error: {e}")
                                
                except Exception as e:
                    st.error(f"Error processing image: {e}")
        
        if avatar_url:
            if st.button("🗑️ Remove Profile Picture", type="secondary"):
                db = get_db()
                if db._use_supabase and db.supabase:
                    response = db.supabase.table('users')\
                        .update({'avatar_url': None})\
                        .eq('id', user_id)\
                        .execute()
                    success = bool(response.data)
                else:
                    success = db.update_user(user_id, {'avatar_url': None})
                
                if success:
                    db.log_user_activity(user_id, 'avatar_removed', 'Removed profile picture')
                    st.success("✅ Profile picture removed")
                    st.rerun()
                else:
                    st.error("Failed to remove profile picture")


def save_avatar_image_complete(uploaded_file, user_id):
    """Save uploaded avatar as complete base64 - no truncation"""
    try:
        from PIL import Image
        import base64
        from io import BytesIO
        
        print("🔍 save_avatar_image_complete called")
        
        # Open and process image
        image = Image.open(uploaded_file)
        print(f"🔍 Image opened: {image.size}, {image.mode}")
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
            print("🔍 Converted to RGB")
        
        # Resize
        max_size = (300, 300)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        print(f"🔍 Resized to {image.size}")
        
        # Save to bytes
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=85, optimize=True)
        print(f"🔍 Bytes size: {len(buffered.getvalue())}")
        
        # Convert to base64
        img_str = base64.b64encode(buffered.getvalue()).decode()
        print(f"🔍 Base64 length: {len(img_str)}")
        
        # Return complete data URL
        avatar_data = f"data:image/jpeg;base64,{img_str}"
        print(f"🔍 Complete data URL length: {len(avatar_data)}")
        
        return True, avatar_data
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, None
    

def render_social_media_links(user_id, social_links):
    """Render social media links management"""
    st.markdown("### 🔗 Social Media Links")
    st.markdown("Connect your social media accounts to your profile")
    db = get_db()

    # Add new social link
    with st.expander("➕ Add New Social Link", expanded=not social_links):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            platform = st.selectbox(
                "Platform *",
                options=[
                    "facebook", "twitter", "instagram", "linkedin", "github",
                    "youtube", "tiktok", "pinterest", "reddit", "whatsapp",
                    "telegram", "discord", "slack", "medium", "dev.to"
                ],
                key="platform_select"
            )
            
            # Platform icons
            platform_icons = {
                "facebook": "📘", "twitter": "🐦", "instagram": "📸", 
                "linkedin": "💼", "github": "🐙", "youtube": "📺",
                "tiktok": "🎵", "pinterest": "📌", "reddit": "🤖",
                "whatsapp": "📱", "telegram": "✈️", "discord": "🎮",
                "slack": "💬", "medium": "✍️", "dev.to": "💻"
            }
            st.info(f"Selected: {platform_icons.get(platform, '')} {platform.title()}")
        
        with col2:
            url = st.text_input(
                "URL *",
                placeholder=f"https://{platform}.com/username",
                help=f"Enter your complete {platform.title()} profile URL",
                key="url_input"
            )
            
            is_public = st.checkbox(
                "Make this link public", 
                value=True,
                help="If unchecked, only you can see this link"
            )
        
        # Add button
        if st.button("➕ Add Social Link", type="primary"):
            if not url:
                st.error("Please enter a valid URL")
            elif not url.startswith(('http://', 'https://')):
                st.error("Please enter a complete URL starting with http:// or https://")
            else:
                # Check if platform already exists
                existing = [l for l in social_links if l.get('platform') == platform]
                if existing:
                    st.error(f"{platform.title()} link already exists. Please edit the existing one instead.")
                else:
                    # Add new link
                    success = db.add_social_link(user_id, platform, url, is_public)
                    if success:
                        db.log_user_activity(user_id, 'social_link_added', f'Added {platform} link')
                        st.success(f"✅ {platform.title()} link added successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to add social link")
    
    # Display existing social links
    if social_links:
        st.markdown("#### Your Connected Accounts")
        
        for link in social_links:
            link_id = link.get('id')
            platform = link.get('platform')
            url = link.get('url')
            is_active = link.get('is_active', 1)
            is_public = link.get('is_public', 1)
            
            platform_icons = {
                "facebook": "📘", "twitter": "🐦", "instagram": "📸", 
                "linkedin": "💼", "github": "🐙", "youtube": "📺",
                "tiktok": "🎵", "pinterest": "📌", "reddit": "🤖",
                "whatsapp": "📱", "telegram": "✈️", "discord": "🎮",
                "slack": "💬", "medium": "✍️", "dev.to": "💻"
            }
            
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{platform_icons.get(platform, '🔗')} {platform.title()}**")
                    
                    # Editable URL
                    new_url = st.text_input(
                        "URL",
                        value=url,
                        key=f"url_{link_id}",
                        label_visibility="collapsed"
                    )
                
                with col2:
                    # Toggle active status
                    new_status = st.checkbox(
                        "Active",
                        value=bool(is_active),
                        key=f"status_{link_id}",
                        help="Disable to hide this link temporarily"
                    )
                
                with col3:
                    # Update and delete buttons
                    if st.button("💾 Update", key=f"update_{link_id}"):
                        updates = {}
                        if new_url and new_url != url:
                            updates['url'] = new_url
                        if new_status != bool(is_active):
                            updates['is_active'] = 1 if new_status else 0
                        
                        if updates:
                            success = db.update_social_link(link_id, updates)
                            if success:
                                db.log_user_activity(user_id, 'social_link_updated', f'Updated {platform} link')
                                st.success("✅ Link updated!")
                                st.rerun()
                            else:
                                st.error("Failed to update link")
                        else:
                            st.info("No changes to update")
                    
                    if st.button("🗑️ Remove", key=f"remove_{link_id}", type="secondary"):
                        success = db.delete_social_link(link_id)
                        if success:
                            db.log_user_activity(user_id, 'social_link_removed', f'Removed {platform} link')
                            st.success(f"✅ {platform.title()} link removed!")
                            st.rerun()
                        else:
                            st.error("Failed to remove link")
                
                st.divider()
    else:
        st.info("No social media links connected yet. Add your first link above!")

def render_activity_log(user_id):
    """Render user activity log"""
    db = get_db()

    activities = db.get_user_activities(user_id, limit=20)
    
    if activities:
        for activity in activities:
            action = activity.get('action')
            details = activity.get('details')
            created_at = activity.get('created_at')
            
            action_icons = {
                'profile_update': '📝',
                'password_change': '🔑',
                'avatar_update': '🖼️',
                'avatar_removed': '🗑️',
                'social_link_added': '➕',
                'social_link_updated': '✏️',
                'social_link_removed': '❌',
                'social_link_status_changed': '🔄',
                'login': '🔓'
            }
            
            icon = action_icons.get(action, '📌')
            
            # ✅ Show more details for avatar updates
            if action == 'avatar_update':
                st.markdown(f"{icon} **Avatar Updated**: {details}")
            else:
                st.markdown(f"{icon} **{action.replace('_', ' ').title()}**: {details}")
            
            st.caption(f"📅 {created_at[:19] if created_at else 'N/A'}")
            st.divider()
    else:
        st.info("No recent activity to display")




# ========== HELPER FUNCTIONS ==========

def validate_password_strength(password):
    """Validate password strength and return score, message, and color"""
    score = 0
    messages = []
    
    if len(password) >= 8:
        score += 20
        messages.append("✅ Good length (8+ characters)")
    else:
        messages.append("❌ Too short (minimum 8 characters)")
    
    if re.search(r'[A-Z]', password):
        score += 20
        messages.append("✅ Contains uppercase letter")
    else:
        messages.append("❌ Missing uppercase letter")
    
    if re.search(r'[a-z]', password):
        score += 20
        messages.append("✅ Contains lowercase letter")
    else:
        messages.append("❌ Missing lowercase letter")
    
    if re.search(r'\d', password):
        score += 20
        messages.append("✅ Contains number")
    else:
        messages.append("❌ Missing number")
    
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 20
        messages.append("✅ Contains special character")
    else:
        messages.append("❌ Missing special character")
    
    if score >= 80:
        return score, "💪 Strong password!", "#28a745"
    elif score >= 60:
        return score, "⚠️ Medium strength password", "#ffc107"
    else:
        return score, "🔴 Weak password - please make it stronger", "#dc3545"



# ========== USER FUNCTIONS ==========

def db_get_user_by_id(user_id: int):
    """Get user by ID with all profile data"""
    db = get_db()
    return db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))


def db_update_user(user_id: int, **kwargs):
    """Update user information"""
    db = get_db()
    
    try:
        # Build update query
        updates = []
        values = []
        
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            values.append(value)
        
        if not updates:
            return True
        
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        
        db.execute(query, tuple(values))
        return True
        
    except Exception as e:
        print(f"Error updating user: {e}")
        return False


def db_change_user_password(user_id: int, current_password: str, new_password: str):
    """Change user password with verification"""
    db = get_db()
    
    try:
        # Get current password hash
        result = db.query_one("SELECT password FROM users WHERE id = ?", (user_id,))
        
        if not result:
            return False, "User not found"
        
        stored_hash = result.get('password')
        
        # Verify current password
        if stored_hash != hash_password(current_password):
            return False, "Current password is incorrect"
        
        # Update password
        new_hash = hash_password(new_password)
        db.execute("UPDATE users SET password = ? WHERE id = ?", (new_hash, user_id))
        
        return True, "Password changed successfully"
    
    except Exception as e:
        print(f"Error changing password: {e}")
        return False, "Failed to change password"


def hash_password(password: str) -> str:
    """Simple password hashing (replace with proper hashing)"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


# ========== SOCIAL LINKS FUNCTIONS ==========

def db_get_user_social_links(user_id: int):
    """Get all social links for a user"""
    db = get_db()
    return db.query(
        "SELECT * FROM social_links WHERE user_id = ? ORDER BY platform",
        (user_id,)
    )


def db_add_social_link(user_id: int, platform: str, url: str, is_public: bool = True):
    """Add a new social link"""
    db = get_db()
    
    try:
        db.execute("""
            INSERT INTO social_links (user_id, platform, url, is_public, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, platform, url, is_public, datetime.now().isoformat()))
        return True
        
    except Exception as e:
        print(f"Error adding social link: {e}")
        return False


def db_update_social_link(link_id: int, **kwargs):
    """Update a social link"""
    db = get_db()
    
    try:
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['platform', 'url', 'is_public']:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return True
        
        values.append(link_id)
        query = f"""
            UPDATE social_links 
            SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """
        
        db.execute(query, tuple(values))
        return True
        
    except Exception as e:
        print(f"Error updating social link: {e}")
        return False


def db_delete_social_link(link_id: int):
    """Delete a social link"""
    db = get_db()
    
    try:
        db.execute("DELETE FROM social_links WHERE id = ?", (link_id,))
        return True
        
    except Exception as e:
        print(f"Error deleting social link: {e}")
        return False


# ========== ACTIVITY LOG FUNCTIONS ==========

def db_log_user_activity(user_id: int, action: str, details: str):
    """Log user activity"""
    db = get_db()
    
    try:
        db.execute("""
            INSERT INTO user_activity_log (user_id, action, details, created_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, action, details, datetime.now().isoformat()))
        return True
        
    except Exception as e:
        print(f"Error logging activity: {e}")
        return False


def db_get_user_activities(user_id: int, limit: int = 20):
    """Get user activity log"""
    db = get_db()
    return db.query("""
        SELECT * FROM user_activity_log 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (user_id, limit))


# ========== CONVENIENCE FUNCTION ==========

def get_user_profile_data(user_id: int):
    """Get complete user profile data including social links"""
    db = get_db()
    
    user = db.get_user_by_id(user_id)
    if not user:
        return None
    
    social_links = db_get_user_social_links(user_id)
    
    return {
        'user': user,
        'social_links': social_links
    }


# ========== STREAMLIT RENDER FUNCTIONS ==========

def render_user_avatar(user, size: int = 100):
    """Render user avatar with fallback"""
    if user and user.get('avatar_url'):
        st.image(user['avatar_url'], width=size)
    else:
        # Show initials as fallback
        name = user.get('full_name', '') or user.get('username', 'U')
        initials = ''.join([word[0] for word in name.split()[:2]])
        st.markdown(f"""
        <div style="
            width: {size}px; 
            height: {size}px; 
            border-radius: 50%; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex; 
            align-items: center; 
            justify-content: center; 
            color: white; 
            font-size: {size//2}px; 
            font-weight: bold;
        ">
            {initials}
        </div>
        """, unsafe_allow_html=True)

def save_avatar_image_base64(uploaded_file, user_id):
    """Save avatar as base64 in database - for Streamlit Cloud compatibility"""
    try:
        import base64
        from io import BytesIO
        
        # Open and process image
        image = Image.open(uploaded_file)
        
        # Resize
        max_size = (300, 300)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to base64
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Return data URL
        avatar_data = f"data:image/png;base64,{img_str}"
        return True, avatar_data
        
    except Exception as e:
        print(f"Error saving avatar as base64: {e}")
        return False, None        