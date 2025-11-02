# ui_components.py
"""User interface components for Streamlit application"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from auth import (
    get_all_users, delete_user, register_user_admin,
    log_activity, get_admin_statistics
)
from config import ACTIVITY_CSV


def show_login_page():
    """Display enhanced professional login page"""
    
    # # Main header with gradient background
    # st.markdown(
    #     """
    #     <div style='text-align:center; padding:3rem 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius:20px; margin-bottom:3rem; box-shadow: 0 10px 40px rgba(0,0,0,0.1)'>
    #         <h1 style='color:white; margin:0; font-size:2.8rem; font-weight:700'>📚 Ethicallogix</h1>
    #         <h2 style='color:#f0f0f0; margin:0.5rem 0; font-size:1.8rem; font-weight:400'>Assignment Maker</h2>
    #         <p style='color:#e0e0e0; font-size:1.1rem; margin:1rem 0 0 0'>AI-Powered Academic Assignment Generator</p>
    #     </div>
    #     """,
    #     unsafe_allow_html=True
    # )
    
    # Login form in a centered card
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(
            """
            <div style='background:white; padding:1rem; border-radius:15px; box-shadow: 0 4px 5px rgba(0,0,0,0.08)'>
                <h3 style='text-align:center; color:#1a2384; margin-bottom:1.5rem'>🔐 User Login</h3>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        with st.form("login_form", clear_on_submit=False):
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Username field with icon
            login_username = st.text_input(
                "👤 Username",
                key="login_username",
                placeholder="Enter your username",
                help="Use your registered username"
            )
            
            # Password field with icon
            login_password = st.text_input(
                "🔒 Password",
                type="password",
                key="login_password",
                placeholder="Enter your password",
                help="Enter your account password"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Login button
            login_submit = st.form_submit_button(
                "Login ",
                use_container_width=True,
                type="primary"
            )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Information boxes
        st.info("📧 **New User?** Contact administrator for account creation\n\n✉️ **Email:** hasiraza511@gmail.com")
        
        return login_submit, login_username, login_password
    

def show_admin_portal():
    """Display admin dashboard"""
    st.markdown(
        """
        <div style='text-align:center; padding:2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius:15px; margin-bottom:2rem'>
            <h1 style='color:white; margin:0'>🔐 Admin Portal</h1>
            <p style='color:#f0f0f0; font-size:1.1rem; margin:0.5rem 0 0 0'>System Management Dashboard</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Get statistics
    stats = get_admin_statistics()
    
    # Display statistics cards
    st.markdown("### 📊 System Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f"""
            <div style='background:#e8f5e9; padding:1.5rem; border-radius:10px; text-align:center'>
                <h2 style='color:#2e7d32; margin:0'>{stats['total_users']}</h2>
                <p style='color:#66bb6a; margin:0.5rem 0 0 0'>Total Users</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            f"""
            <div style='background:#e3f2fd; padding:1.5rem; border-radius:10px; text-align:center'>
                <h2 style='color:#1565c0; margin:0'>{stats['active_users']}</h2>
                <p style='color:#42a5f5; margin:0.5rem 0 0 0'>Active Users</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            f"""
            <div style='background:#fff3e0; padding:1.5rem; border-radius:10px; text-align:center'>
                <h2 style='color:#ef6c00; margin:0'>{stats['total_assignments']}</h2>
                <p style='color:#ff9800; margin:0.5rem 0 0 0'>Assignments Generated</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col4:
        st.markdown(
            f"""
            <div style='background:#f3e5f5; padding:1.5rem; border-radius:10px; text-align:center'>
                <h2 style='color:#7b1fa2; margin:0'>{stats['total_activities']}</h2>
                <p style='color:#ab47bc; margin:0.5rem 0 0 0'>Total Activities</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # Tabs for different admin functions
    tab1, tab2, tab3 = st.tabs(["👥 User Management", "➕ Register New User", "📈 Activity Logs"])
    
    # Tab 1: User Management
    with tab1:
        st.markdown("### 👥 Registered Users")
        users_df = get_all_users()
        
        if not users_df.empty:
            st.dataframe(users_df, use_container_width=True, hide_index=True)
            
            st.markdown("### 🗑️ Delete User")
            col1, col2 = st.columns([3, 1])
            with col1:
                user_to_delete = st.selectbox(
                    "Select user to delete",
                    options=users_df['username'].tolist(),
                    key="delete_user_select"
                )
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Delete User", type="secondary", use_container_width=True):
                    success, message = delete_user(user_to_delete)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        else:
            st.info("📭 No users registered yet.")
    
    # Tab 2: Register New User
    with tab2:
        st.markdown("### ➕ Register New User")
        
        with st.form("admin_register_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_full_name = st.text_input("Full Name *", key="admin_reg_full_name")
                new_username = st.text_input("Username * (min 4 characters)", key="admin_reg_username")
            with col2:
                new_email = st.text_input("Email Address *", key="admin_reg_email")
                new_password = st.text_input("Password * (min 6 characters)", type="password", key="admin_reg_password")
            
            register_submit = st.form_submit_button("✅ Register User", use_container_width=True, type="primary")
            
            if register_submit:
                errors = []
                if not new_full_name or len(new_full_name.strip()) < 2:
                    errors.append("Full name must be at least 2 characters")
                if not new_username or len(new_username.strip()) < 4:
                    errors.append("Username must be at least 4 characters")
                if not new_email or '@' not in new_email:
                    errors.append("Valid email address required")
                if not new_password or len(new_password) < 6:
                    errors.append("Password must be at least 6 characters")
                
                if errors:
                    for error in errors:
                        st.error(f"❌ {error}")
                else:
                    success, message = register_user_admin(new_username, new_email, new_password, new_full_name)
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                    else:
                        st.error(f"❌ {message}")
    
    # Tab 3: Activity Logs
    with tab3:
        st.markdown("### 📈 Recent Activity Logs")
        
        if Path(ACTIVITY_CSV).exists():
            activity_df = pd.read_csv(ACTIVITY_CSV)
            
            # Show last 50 activities
            recent_activities = activity_df.tail(50).sort_values('timestamp', ascending=False)
            st.dataframe(recent_activities, use_container_width=True, hide_index=True)
            
            # Download activity logs
            csv_data = activity_df.to_csv(index=False)
            st.download_button(
                "📥 Download All Activity Logs",
                data=csv_data,
                file_name=f"activity_logs_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("📭 No activity logs available.")
    
    st.markdown("---")
    
    # Logout button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            log_activity('admin', "ADMIN_LOGOUT", "Administrator logged out")
            return True
    return False


def show_tips_section():
    """Display tips for best results"""
    st.markdown("---")
    st.markdown("### 💡 Tips for Best Results")
    
    tips_col1, tips_col2 = st.columns(2)
    
    with tips_col1:
        st.markdown("""
        **Topic Guidelines:**
        - Be specific and clear about requirements
        - Include context and scope
        - Mention any specific concepts to cover
        - Specify format preferences (if any)
        - Upload documents for context (NEW!)
        """)
        
    with tips_col2:
        st.markdown("""
        **Quality Tips:**
        - Choose appropriate difficulty level
        - Enable examples for better understanding
        - Include references for academic credibility
        - Adjust word count based on depth needed
        - Upload university logo for professional branding
        """)


def show_footer():
    """Display application footer"""
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align:center; color:#6b7280; padding:20px; background-color:#f9fafb; border-radius:10px; margin-top:2rem'>
            <strong style='font-size:1.1rem'>📚 Ethicallogix Assignment Maker</strong><br>
            <p style='margin:0.5rem 0'>Developed by <strong>Muhammad Haseeb</strong></p>
            <small>Version 4.0 | Enhanced with Document Upload Support</small>
        </div>
        """,
        unsafe_allow_html=True,
    )