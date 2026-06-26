# profile_module.py

import streamlit as st
import re
import hashlib
import os
from datetime import datetime
from PIL import Image
import io
from database.unified_db_manager import UnifiedDatabaseManager
db = UnifiedDatabaseManager()

def render_user_profile():
    """Render the user profile page with all features"""
    
    # Check if user is logged in
    if 'user_id' not in st.session_state:
        st.error("Please log in to view your profile")
        return
    
    user_id = st.session_state.user_id
    
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
                # Update user data
                updates = {
                    'full_name': full_name.strip(),
                    'email': email.strip(),
                    'username': username.strip(),
                    'phone': phone.strip() if phone else None,
                    'mobile_number': mobile_number.strip(),
                    'location': location.strip() if location else None,
                    'bio': bio.strip() if bio else None
                }
                
                success = db.update_user(user.get('id'), **updates)
                
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
            # Verify current password and update
            success, message = db.change_user_password(user_id, current_password, new_password)
            
            if success:
                st.success("✅ Password changed successfully!")
                db.log_user_activity(user_id, 'password_change', 'Changed password')
                st.balloons()
            else:
                st.error(f"❌ {message}")

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
                st.image(avatar_url, width=200, caption="Current Profile Picture")
            except:
                # If URL is invalid, show placeholder
                st.image("https://ui-avatars.com/api/?name=" + user.get('full_name', 'User') + "&size=200", width=200)
        else:
            # Generate avatar from name
            name = user.get('full_name', 'User')
            st.image(f"https://ui-avatars.com/api/?name={name}&size=200&background=6366f1&color=ffffff", 
                    width=200, caption="No Profile Picture")
    
    with col2:
        st.markdown("#### Upload New Picture")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=['jpg', 'jpeg', 'png', 'gif'],
            help="Supported formats: JPG, JPEG, PNG, GIF (Max 5MB)"
        )
        
        if uploaded_file is not None:
            # Check file size
            if uploaded_file.size > 5 * 1024 * 1024:
                st.error("File size exceeds 5MB limit")
            else:
                # Display preview
                image = Image.open(uploaded_file)
                st.image(image, width=150, caption="Preview")
                
                # Upload button
                if st.button("📤 Upload Profile Picture", type="primary"):
                    # Here you would upload to cloud storage or save locally
                    # For this example, we'll save to a directory
                    success, avatar_path = save_avatar_image(uploaded_file, user_id)
                    
                    if success:
                        # Update user profile
                        db.update_user(user_id, avatar_url=avatar_path)
                        db.log_user_activity(user_id, 'avatar_update', 'Updated profile picture')
                        st.success("✅ Profile picture updated successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to upload image")
        
        # Remove avatar option
        if avatar_url:
            if st.button("🗑️ Remove Profile Picture", type="secondary"):
                success = db.update_user(user_id, avatar_url=None)
                if success:
                    # Delete file if local
                    if os.path.exists(avatar_url):
                        os.remove(avatar_url)
                    db.log_user_activity(user_id, 'avatar_removed', 'Removed profile picture')
                    st.success("✅ Profile picture removed")
                    st.rerun()
                else:
                    st.error("Failed to remove profile picture")

def render_social_media_links(user_id, social_links):
    """Render social media links management"""
    st.markdown("### 🔗 Social Media Links")
    st.markdown("Connect your social media accounts to your profile")
    
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
                        if new_url and new_url != url:
                            # Update URL
                            success = db.update_social_link(link_id, url=new_url)
                            if success:
                                db.log_user_activity(user_id, 'social_link_updated', f'Updated {platform} URL')
                                st.success("✅ Link updated!")
                                st.rerun()
                            else:
                                st.error("Failed to update link")
                        elif new_status != bool(is_active):
                            # Update status
                            success = db.update_social_link(link_id, is_active=1 if new_status else 0)
                            if success:
                                db.log_user_activity(user_id, 'social_link_status_changed', 
                                                   f'Updated {platform} status to {"active" if new_status else "inactive"}')
                                st.success("✅ Status updated!")
                                st.rerun()
                            else:
                                st.error("Failed to update status")
                    
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

def save_avatar_image(uploaded_file, user_id):
    """Save uploaded avatar image to disk"""
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = "static/uploads/avatars"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate filename
        file_extension = uploaded_file.name.split('.')[-1]
        filename = f"user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}"
        filepath = os.path.join(upload_dir, filename)
        
        # Save file
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return True, filepath
    
    except Exception as e:
        print(f"Error saving avatar: {e}")
        return False, None

# ========== DATABASE FUNCTIONS ==========

def db_get_user_by_id(user_id):
    """Get user by ID with all profile data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM users WHERE id = ?
    """, (user_id,))
    
    user = cursor.fetchone()
    conn.close()
    
    return user if user else None

def db_get_user_social_links(user_id):
    """Get all social links for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM social_links WHERE user_id = ? ORDER BY platform
    """, (user_id,))
    
    links = cursor.fetchall()
    conn.close()
    
    return links

def db_add_social_link(user_id, platform, url, is_public=True):
    """Add a new social link"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO social_links (user_id, platform, url, is_public)
            VALUES (?, ?, ?, ?)
        """, (user_id, platform, url, is_public))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding social link: {e}")
        return False
    finally:
        conn.close()

def db_update_social_link(link_id, **kwargs):
    """Update a social link"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        updates = []
        values = []
        
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            values.append(value)
        
        if updates:
            values.append(link_id)
            query = f"""
                UPDATE social_links 
                SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """
            cursor.execute(query, values)
            conn.commit()
        
        return True
    except Exception as e:
        print(f"Error updating social link: {e}")
        return False
    finally:
        conn.close()

def db_delete_social_link(link_id):
    """Delete a social link"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM social_links WHERE id = ?", (link_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting social link: {e}")
        return False
    finally:
        conn.close()

def db_change_user_password(user_id, current_password, new_password):
    """Change user password with verification"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get current password hash
        cursor.execute("SELECT password FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            return False, "User not found"
        
        stored_hash = result[0]
        
        # Verify current password
        # Note: Assuming password is stored as hash. You'll need to implement proper password hashing
        # Here we're using a simple check for demonstration
        if stored_hash != hash_password(current_password):
            return False, "Current password is incorrect"
        
        # Update password
        new_hash = hash_password(new_password)
        cursor.execute("""
            UPDATE users SET password = ? WHERE id = ?
        """, (new_hash, user_id))
        
        conn.commit()
        return True, "Password changed successfully"
    
    except Exception as e:
        print(f"Error changing password: {e}")
        return False, "Failed to change password"
    finally:
        conn.close()

def hash_password(password):
    """Simple password hashing (replace with proper hashing)"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def db_log_user_activity(user_id, action, details):
    """Log user activity"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO user_activity_log (user_id, action, details)
            VALUES (?, ?, ?)
        """, (user_id, action, details))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error logging activity: {e}")
        return False
    finally:
        conn.close()

def db_get_user_activities(user_id, limit=20):
    """Get user activity log"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM user_activity_log 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (user_id, limit))
    
    activities = cursor.fetchall()
    conn.close()
    
    return activities

def db_update_user(user_id, **kwargs):
    """Update user information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        updates = []
        values = []
        
        for key, value in kwargs.items():
            updates.append(f"{key} = ?")
            values.append(value)
        
        if updates:
            values.append(user_id)
            query = f"""
                UPDATE users 
                SET {', '.join(updates)} 
                WHERE id = ?
            """
            cursor.execute(query, values)
            conn.commit()
        
        return True
    except Exception as e:
        print(f"Error updating user: {e}")
        return False
    finally:
        conn.close()