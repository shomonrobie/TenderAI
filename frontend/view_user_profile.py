# _pages/view_user_profile.py

import streamlit as st
from database.unified_db_manager import UnifiedDatabaseManager
from modules.ui_components import render_combined_header

db = UnifiedDatabaseManager()

def show():
    """View a user's complete profile (admin view)"""
    
    # Render header
    render_combined_header()
    
    user_id = st.session_state.get('view_user_id')
    
    if not user_id:
        st.error("No user selected")
        if st.button("← Back to User Management"):
            st.session_state.page = "user_management"
            st.rerun()
        return
    
    # Get user profile
    user = db.get_user_profile(user_id)
    
    if not user:
        st.error("User not found")
        return
    
    st.markdown(f"""
    <div class="main-header">
        <h1>👤 User Profile - {user.get('full_name', 'Unknown')}</h1>
        <p>Complete profile information for {user.get('full_name')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Back button
    if st.button("← Back to User Management"):
        st.session_state.page = "user_management"
        st.rerun()
    
    # Display user information
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Avatar
        avatar_url = user.get('avatar_url')
        if avatar_url:
            st.image(avatar_url, width=200)
        else:
            name = user.get('full_name', 'User')
            st.image(f"https://ui-avatars.com/api/?name={name}&size=200&background=6366f1&color=ffffff", 
                    width=200)
        
        # Quick stats
        st.markdown("### 📊 Stats")
        activities = db.get_user_activity_stats(user_id)
        st.metric("Total Activities", activities.get('total', 0))
    
    with col2:
        st.markdown("### 📋 Personal Information")
        
        # Display user fields
        fields = [
            ('Full Name', 'full_name'),
            ('Username', 'username'),
            ('Email', 'email'),
            ('Phone', 'phone'),
            ('Mobile Number', 'mobile_number'),
            ('Location', 'location'),
            ('Website', 'website'),
            ('Bio', 'bio'),
        ]
        
        for label, key in fields:
            value = user.get(key, 'N/A')
            if value:
                st.markdown(f"**{label}:** {value}")
        
        st.divider()
        
        # Role and status
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Role:** {user.get('role', 'N/A').replace('_', ' ').title()}")
            st.markdown(f"**Status:** {'✅ Active' if user.get('is_active') else '❌ Inactive'}")
        with col2:
            st.markdown(f"**Joined:** {user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'}")
            st.markdown(f"**Last Login:** {user.get('last_login', 'Never')[:10] if user.get('last_login') else 'Never'}")
    
    # Social Links
    st.divider()
    st.markdown("### 🔗 Social Media Links")
    
    social_links = user.get('social_links', [])
    if social_links:
        platform_icons = {
            "facebook": "📘", "twitter": "🐦", "instagram": "📸", 
            "linkedin": "💼", "github": "🐙", "youtube": "📺",
            "tiktok": "🎵", "pinterest": "📌", "reddit": "🤖",
            "whatsapp": "📱", "telegram": "✈️", "discord": "🎮",
            "slack": "💬", "medium": "✍️", "dev.to": "💻"
        }
        
        cols = st.columns(4)
        for idx, link in enumerate(social_links):
            with cols[idx % 4]:
                platform = link.get('platform')
                url = link.get('url')
                icon = platform_icons.get(platform, "🔗")
                st.markdown(f"{icon} [{platform.title()}]({url})")
    else:
        st.info("No social media links connected")
    
    # Activity Log
    st.divider()
    with st.expander("📋 Recent Activity"):
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
                    'login': '🔓'
                }
                
                icon = action_icons.get(action, '📌')
                st.markdown(f"{icon} **{action.replace('_', ' ').title()}**: {details}")
                st.caption(f"📅 {created_at[:19] if created_at else 'N/A'}")
                st.divider()
        else:
            st.info("No activity to display")