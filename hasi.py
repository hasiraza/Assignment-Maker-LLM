# app.py
import streamlit as st
import google.generativeai as genai
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    Image as RLImage,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime
import os
from dotenv import load_dotenv
import re
import warnings
import logging
import json
from typing import Tuple, Dict, Any, List
from PIL import Image
import csv
import hashlib
import pandas as pd
from pathlib import Path

# Suppress warnings and gRPC logs
warnings.filterwarnings("ignore")
os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
os.environ.setdefault("GLOG_minloglevel", "2")
logging.getLogger("google").setLevel(logging.ERROR)

# Load environment variables
load_dotenv()

# Constants
MIN_UNIVERSITY_NAME_LENGTH = 3
MIN_STUDENT_NAME_LENGTH = 2
MIN_STUDENT_ID_LENGTH = 3
MIN_PROGRAM_NAME_LENGTH = 5
MIN_SUBJECT_NAME_LENGTH = 3
MIN_TOPIC_LENGTH = 20
MAX_QUESTIONS = 10
CACHE_TTL = 3600

# Admin Credentials
ADMIN_USERNAME = "hasi"
ADMIN_PASSWORD = "system786@"

# CSV file paths
USERS_CSV = "users.csv"
ACTIVITY_CSV = "user_activity.csv"

# ==================== AUTHENTICATION FUNCTIONS ====================

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def initialize_csv_files():
    """Initialize CSV files if they don't exist"""
    # Users CSV
    if not Path(USERS_CSV).exists():
        with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['username', 'email', 'password_hash', 'full_name', 'registration_date', 'status'])
    
    # Activity CSV
    if not Path(ACTIVITY_CSV).exists():
        with open(ACTIVITY_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['username', 'activity_type', 'timestamp', 'details'])

def log_activity(username: str, activity_type: str, details: str = ""):
    """Log user activity to CSV"""
    try:
        with open(ACTIVITY_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([username, activity_type, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), details])
    except Exception as e:
        st.error(f"Error logging activity: {str(e)}")

def register_user_admin(username: str, email: str, password: str, full_name: str) -> Tuple[bool, str]:
    """Register a new user (Admin only)"""
    try:
        # Check if user already exists
        if Path(USERS_CSV).exists():
            df = pd.read_csv(USERS_CSV)
            if username in df['username'].values:
                return False, "Username already exists"
            if email in df['email'].values:
                return False, "Email already registered"
        
        # Add new user
        password_hash = hash_password(password)
        with open(USERS_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([username, email, password_hash, full_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'active'])
        
        log_activity('admin', "USER_REGISTERED", f"New user registered by admin: {username} ({full_name})")
        return True, "User registered successfully!"
    
    except Exception as e:
        return False, f"Registration error: {str(e)}"

def delete_user(username: str) -> Tuple[bool, str]:
    """Delete a user (Admin only)"""
    try:
        if not Path(USERS_CSV).exists():
            return False, "No users found"
        
        df = pd.read_csv(USERS_CSV)
        if username not in df['username'].values:
            return False, "User not found"
        
        # Remove user
        df = df[df['username'] != username]
        df.to_csv(USERS_CSV, index=False)
        
        log_activity('admin', "USER_DELETED", f"User deleted by admin: {username}")
        return True, f"User '{username}' deleted successfully!"
    
    except Exception as e:
        return False, f"Delete error: {str(e)}"

def get_all_users() -> pd.DataFrame:
    """Get all users (Admin only)"""
    try:
        if Path(USERS_CSV).exists():
            df = pd.read_csv(USERS_CSV)
            # Don't show password hash
            return df[['username', 'email', 'full_name', 'registration_date', 'status']]
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading users: {str(e)}")
        return pd.DataFrame()

def authenticate_user(username: str, password: str) -> Tuple[bool, Dict[str, str], bool]:
    """Authenticate user credentials. Returns (success, user_info, is_admin)"""
    # Check if admin
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        admin_info = {
            'username': 'admin',
            'email': 'admin@ethicallogix.com',
            'full_name': 'System Administrator',
            'registration_date': 'N/A'
        }
        log_activity('admin', "ADMIN_LOGIN", "Administrator logged in")
        return True, admin_info, True
    
    # Check regular users
    try:
        if not Path(USERS_CSV).exists():
            return False, {}, False
        
        df = pd.read_csv(USERS_CSV)
        user_row = df[df['username'] == username]
        
        if user_row.empty:
            return False, {}, False
        
        # Check if user is active
        if user_row.iloc[0]['status'] != 'active':
            return False, {}, False
        
        stored_hash = user_row.iloc[0]['password_hash']
        if hash_password(password) == stored_hash:
            user_info = {
                'username': user_row.iloc[0]['username'],
                'email': user_row.iloc[0]['email'],
                'full_name': user_row.iloc[0]['full_name'],
                'registration_date': user_row.iloc[0]['registration_date']
            }
            log_activity(username, "LOGIN", "User logged in successfully")
            return True, user_info, False
        
        return False, {}, False
    
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return False, {}, False

def get_user_stats(username: str) -> Dict[str, Any]:
    """Get user activity statistics"""
    try:
        if not Path(ACTIVITY_CSV).exists():
            return {'total_activities': 0, 'assignments_generated': 0, 'last_activity': 'N/A'}
        
        df = pd.read_csv(ACTIVITY_CSV)
        user_activities = df[df['username'] == username]
        
        total_activities = len(user_activities)
        assignments_generated = len(user_activities[user_activities['activity_type'] == 'ASSIGNMENT_GENERATED'])
        last_activity = user_activities.iloc[-1]['timestamp'] if not user_activities.empty else 'N/A'
        
        return {
            'total_activities': total_activities,
            'assignments_generated': assignments_generated,
            'last_activity': last_activity
        }
    except Exception as e:
        return {'total_activities': 0, 'assignments_generated': 0, 'last_activity': 'N/A'}

def get_admin_statistics() -> Dict[str, Any]:
    """Get overall system statistics for admin"""
    try:
        stats = {
            'total_users': 0,
            'active_users': 0,
            'total_assignments': 0,
            'total_activities': 0,
            'recent_registrations': []
        }
        
        if Path(USERS_CSV).exists():
            users_df = pd.read_csv(USERS_CSV)
            stats['total_users'] = len(users_df)
            stats['active_users'] = len(users_df[users_df['status'] == 'active'])
            
            # Get recent registrations (sort by string date in descending order)
            if not users_df.empty:
                # Sort by registration_date as string (works for YYYY-MM-DD format)
                users_df_sorted = users_df.sort_values('registration_date', ascending=False)
                recent = users_df_sorted.head(5)[['username', 'full_name', 'registration_date']]
                stats['recent_registrations'] = recent.to_dict('records')
        
        if Path(ACTIVITY_CSV).exists():
            activity_df = pd.read_csv(ACTIVITY_CSV)
            stats['total_activities'] = len(activity_df)
            stats['total_assignments'] = len(activity_df[activity_df['activity_type'] == 'ASSIGNMENT_GENERATED'])
        
        return stats
    except Exception as e:
        st.error(f"Error getting statistics: {str(e)}")
        return {'total_users': 0, 'active_users': 0, 'total_assignments': 0, 'total_activities': 0, 'recent_registrations': []}

# ==================== ADMIN PORTAL ====================

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
            st.session_state.authenticated = False
            st.session_state.is_admin = False
            st.session_state.user_info = None
            st.rerun()

# ==================== LOGIN PAGE ====================

def show_login_page():
    """Display login page"""
    st.markdown(
        """
        <div style='text-align:center; padding:2rem'>
            <h1 style='color:#1a2384'>📚 Ethicallogix Assignment Maker</h1>
            <p style='color:#6b7280; font-size:1.2rem'>Generate professional academic assignments with AI</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("### 🔐 User Login")
    
    with st.form("login_form"):
        login_username = st.text_input("Username", key="login_username", placeholder="Enter your username")
        login_password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            login_submit = st.form_submit_button("🔓 Login", use_container_width=True, type="primary")
        
        if login_submit:
            if not login_username or not login_password:
                st.error("❌ Please fill in all fields")
            else:
                success, user_info, is_admin = authenticate_user(login_username, login_password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.user_info = user_info
                    st.session_state.is_admin = is_admin
                    
                    if is_admin:
                        st.success(f"✅ Welcome Administrator!")
                    else:
                        st.success(f"✅ Welcome back, {user_info['full_name']}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
    
    st.markdown("---")
    st.info("""💡 **Note:** User registration is managed by the administrator.
                    Please contact admin on email for account creation.
                    Your account will be create in 1 hour.""")
    st.info("💡 **Administrator Email:** hasiraza511@gmail.com")
    
    
    
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align:center; color:#6b7280; padding:15px'>
            <small>© 2025 Ethicallogix | Developed by Muhammad Haseeb</small>
        </div>
        """,
        unsafe_allow_html=True
    )

# ==================== MAIN APPLICATION ====================

# Page configuration
st.set_page_config(
    page_title="Assignment Maker By Ethicallogix",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Enhanced custom CSS
st.markdown(
    """
    <style>
    .stButton>button { 
        border-radius: 10px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .reportview-container .main .block-container{ 
        padding-top:1rem; 
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize CSV files
initialize_csv_files()

# Initialize session state
def initialize_session_state():
    defaults = {
        "authenticated": False,
        "user_info": None,
        "is_admin": False,
        "assignment_generated": False,
        "assignment_content": None,
        "generation_time": None,
        "total_generated": 0,
        "generation_history": [],
        "is_generating": False,
        "student_info": None,
        "logo_data": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

# Check authentication
if not st.session_state.authenticated:
    show_login_page()
    st.stop()

# Show admin portal if admin
if st.session_state.is_admin:
    show_admin_portal()
    st.stop()

# ==================== USER INTERFACE (Rest of the original code) ====================

# Load environment variables
load_dotenv()

# Sidebar with user info
with st.sidebar:
    st.markdown(f"### 👤 Welcome, {st.session_state.user_info['full_name']}!")
    st.markdown(f"**Username:** {st.session_state.user_info['username']}")
    
    # User stats
    user_stats = get_user_stats(st.session_state.user_info['username'])
    st.markdown("---")
    st.markdown("### 📊 Your Statistics")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Activities", user_stats['total_activities'])
    with col2:
        st.metric("Assignments", user_stats['assignments_generated'])
    
    st.caption(f"Last Activity: {user_stats['last_activity']}")
    
    st.markdown("---")
    st.header("Powered By Ethicallogix")
    api_key = os.getenv("GOOGLE_API_KEY", "")
    
    gemini_model = "gemini-2.0-flash-exp"
    st.subheader("⚙️ Advanced Options")
    
    num_questions = st.slider("Number of Questions", 1, MAX_QUESTIONS, 3)
    assignment_type = st.selectbox(
        "Assignment Type",
        [
            "Assignment",
            "Research Paper",
            "Problem Solving",
            "Essay",
            "Case Study",
            "Technical Report",
            "Literature Review",
            "Project Proposal",
        ],
    )
    word_count_preference = st.selectbox(
        "Answer Length",
        ["Concise (200-300 words)", "Standard (400-600 words)", "Detailed (800-1000 words)"],
        index=1,
    )

    difficulty = st.selectbox(
        "Difficulty Level", 
        ["Beginner", "Intermediate", "Advanced", "Expert"], 
        index=1
    )
    include_references = st.checkbox("Include Academic References (APA)", value=True)
    include_examples = st.checkbox("Include Practical Examples", value=True)
    include_learning_objectives = st.checkbox("Include Learning Objectives", value=False)
    include_rubric = st.checkbox("Include Grading Rubric", value=False)

    st.markdown("---")
    st.subheader("ℹ️ About")
    st.markdown(
        """
        **Features:**
        - 📝 Q→A academic assignments
        - 🎯 Optional learning objectives & rubric
        - 📄 Professional PDF output
        - 🎨 Formatted cover page
        - 📊 Page numbering
        - 💾 Multiple export formats
        - 🖼️ Custom university logo
        """
    )

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        log_activity(st.session_state.user_info['username'], "LOGOUT", "User logged out")
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.rerun()
    
    if st.button("🔄 Reset App", use_container_width=True):
        for k in ['assignment_generated', 'assignment_content', 'generation_time', 'student_info', 'logo_data']:
            if k in st.session_state:
                st.session_state[k] = None if k != 'assignment_generated' else False
        st.rerun()

# Header
st.title("📚 Ethicallogix Assignment Maker")
st.markdown(
    "<p style='text-align:center; color:#6b7280'>Generate professional academic assignments with AI-powered content</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# Main form
st.subheader("📝 Assignment Details")

col1, col2 = st.columns(2)
with col1:
    university_name = st.text_input(
        "University Name *", 
        placeholder="University of Management and Technology",
        help=f"Minimum {MIN_UNIVERSITY_NAME_LENGTH} characters"
    )
    student_name = st.text_input(
        "Student Name *", 
        placeholder="Muhammad Haseeb",
        help=f"Minimum {MIN_STUDENT_NAME_LENGTH} characters"
    )
    student_id = st.text_input(
        "Student ID *", 
        placeholder="F2024332157",
        help=f"Minimum {MIN_STUDENT_ID_LENGTH} characters"
    )
    program_name = st.text_input(
        "Program Name *", 
        placeholder="BS Data Science",
        help=f"Minimum {MIN_PROGRAM_NAME_LENGTH} characters"
    )
with col2:
    subject_name = st.text_input(
        "Subject Name *", 
        placeholder="Machine Learning",
        help=f"Minimum {MIN_SUBJECT_NAME_LENGTH} characters"
    )
    instructor_name = st.text_input(
        "Instructor Name", 
        placeholder="Dr. Farhan Aslam"
    )
    semester = st.text_input(
        "Semester/Term", 
        placeholder="Fall 2024"
    )
    
    # Logo upload section
    st.markdown("### 🎨 University Logo (Optional)")
    uploaded_logo = st.file_uploader(
        "Upload Logo (PNG)",
        type=['png'],
        help="Upload a PNG logo (max 2MB). Logo will appear on all pages at top-left corner."
    )
    
    if uploaded_logo is not None:
        try:
            logo_image = Image.open(uploaded_logo)
            st.image(logo_image, caption="Logo Preview", width=120)
            uploaded_logo.seek(0)
            st.session_state.logo_data = uploaded_logo.read()
            st.success("✅ Logo uploaded successfully!")
        except Exception as e:
            st.error(f"❌ Error loading logo: {str(e)}")
            st.session_state.logo_data = None

st.markdown("### 📋 Assignment Topic / Prompt")
assignment_topic = st.text_area(
    "Describe the topic or assignment brief *",
    height=140,
    placeholder="Example: Explain time complexity of sorting algorithms and implement merge sort in Python with detailed analysis and complexity comparison.",
    help=f"Minimum {MIN_TOPIC_LENGTH} characters"
)
if assignment_topic:
    chars = len(assignment_topic)
    words = len(assignment_topic.split())
    st.caption(f"📊 {chars} characters | {words} words")

# Input validation
def validate_inputs() -> List[str]:
    errors = []
    if not university_name or len(university_name.strip()) < MIN_UNIVERSITY_NAME_LENGTH:
        errors.append(f"❌ University name must be at least {MIN_UNIVERSITY_NAME_LENGTH} characters.")
    if not student_name or len(student_name.strip()) < MIN_STUDENT_NAME_LENGTH:
        errors.append(f"❌ Student name must be at least {MIN_STUDENT_NAME_LENGTH} characters.")
    if not student_id or len(student_id.strip()) < MIN_STUDENT_ID_LENGTH:
        errors.append(f"❌ Student ID must be at least {MIN_STUDENT_ID_LENGTH} characters.")
    if not program_name or len(program_name.strip()) < MIN_PROGRAM_NAME_LENGTH:
        errors.append(f"❌ Program name must be at least {MIN_PROGRAM_NAME_LENGTH} characters.")
    if not subject_name or len(subject_name.strip()) < MIN_SUBJECT_NAME_LENGTH:
        errors.append(f"❌ Subject name must be at least {MIN_SUBJECT_NAME_LENGTH} characters.")
    if not assignment_topic or len(assignment_topic.strip()) < MIN_TOPIC_LENGTH:
        errors.append(f"❌ Assignment topic must be at least {MIN_TOPIC_LENGTH} characters.")
    return errors

# Build prompt generator
def build_prompt(
    topic: str,
    subject: str,
    num_qs: int,
    assign_type: str,
    diff_level: str,
    include_refs: bool,
    include_ex: bool,
    include_lo: bool,
    include_rub: bool,
    word_pref: str,
) -> Tuple[str, Dict[str, Any]]:
    word_count = "100-150"
    if "Concise" in word_pref:
        word_count = "100-150"
    elif "Detailed" in word_pref:
        word_count = "800-1000"

    examples_instruction = "\n- Include practical examples and real-world applications." if include_ex else ""

    lo_block = ""
    if include_lo:
        lo_block = """
## LEARNING OBJECTIVES
[List 3–5 clear, measurable learning objectives that students should achieve after completing this assignment.]
"""

    rubric_block = ""
    if include_rub:
        rubric_block = """
## EVALUATION RUBRIC
[Provide 4–5 criteria with brief descriptors for Excellent, Good, Satisfactory, and Poor performance (concise table style).]
"""

    references_instruction = ""
    if include_refs:
        references_instruction = """
## REFERENCES

"""

    prompt = f"""
You are an expert university professor and academic writer.
Create a professional {assign_type} assignment suitable for {diff_level}-level students.

CRITICAL FORMATTING RULES:
- Use ## for main section headings (e.g., ## INTRODUCTION)
- Use ### for subsection headings (e.g., ### Importance of Biofertilizers)
- Do NOT use any "Question" or "Answer" format.
- Maintain consistent academic formatting and spacing.
- Write in formal academic English throughout.

Topic: {topic}
Subject: {subject}

INSTRUCTIONS:
- Structure the assignment with clear sections and subsections.
- Each subsection should explain key aspects of the topic in a coherent, analytical manner.
- Maintain academic flow — introduction, main discussion (divided into logical subtopics), and conclusion.
- Use discipline-appropriate terminology and theoretical insights{examples_instruction}.
- Provide depth, evidence-based reasoning, and critical reflection.
- Each major section should contain approximately {word_count} words.

## INTRODUCTION
[Write short paragraph of introduction on 2-3 lines:
- Provide background and significance of the topic
- Explain its relevance to the academic discipline
- Outline the key concepts or challenges explored
- State the overall purpose and learning outcomes of the assignment]

{lo_block}
{rubric_block}

## MAIN DISCUSSION
[Organize this section into several subheadings and this section is short paragraph on 2-3 lines, e.g.:
### Definition and Concept
### Mechanism or Process
### Applications
### Challenges and Future Prospects
Each subsection should elaborate comprehensively with academic reasoning and examples.]

## CONCLUSION
[Write 1 paragraphs synthesizing the key insights from all sections and reflecting on the broader academic and practical significance of the topic.]
"""

    meta = {
        "word_count_range": word_count,
        "examples_instruction": examples_instruction,
        "num_questions": num_qs,
    }
    return prompt, meta

# Generate assignment using Gemini
def generate_assignment(
    api_key: str,
    topic: str,
    subject: str,
    num_qs: int,
    assign_type: str,
    diff_level: str,
    include_refs: bool,
    include_ex: bool,
    include_lo: bool,
    include_rub: bool,
    model_name: str,
    word_pref: str,
) -> Tuple[str, float]:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)

        prompt, meta = build_prompt(
            topic,
            subject,
            num_qs,
            assign_type,
            diff_level,
            include_refs,
            include_ex,
            include_lo,
            include_rub,
            word_pref,
        )

        start = datetime.now()
        response = model.generate_content(prompt)
        end = datetime.now()
        gen_time = (end - start).total_seconds()

        return response.text, gen_time
    except Exception as e:
        msg = str(e)
        if "API_KEY_INVALID" in msg or "invalid" in msg.lower():
            return (
                "❌ **API Key Error**: Your API key is invalid.\n\n"
                "**Solution:** Get your key at: https://makersuite.google.com/app/apikey"
            ), 0.0
        if "quota" in msg.lower() or "resource_exhausted" in msg.lower():
            return (
                "❌ **Quota Exceeded**: You've reached your API usage limits.\n\n"
                "**Solution:** Check your quota at: https://console.cloud.google.com/"
            ), 0.0
        if "timeout" in msg.lower():
            return (
                "❌ **Timeout Error**: Request took too long.\n\n"
                "**Solution:** Try reducing word count or number of questions."
            ), 0.0
        if "PERMISSION_DENIED" in msg:
            return (
                "❌ **Permission Error**: API key doesn't have permission to use this model.\n\n"
                "**Solution:** Enable the Generative AI API in Google Cloud Console."
            ), 0.0
        return f"❌ **Unexpected Error**: {msg}", 0.0

# PDF generation with logo on all pages
def create_pdf(student_info: Dict[str, str], assignment_content: str, include_refs: bool, logo_data: bytes = None) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1.2 * inch,
        bottomMargin=0.8 * inch,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
    )

    styles = getSampleStyleSheet()

    # Enhanced styles
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=26,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1a2384"),
        fontName="Helvetica-Bold",
        spaceAfter=10,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#000000"),
        spaceAfter=14,
        fontName="Helvetica-Bold",
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=12,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#0a0a0a"),
        fontName="Helvetica-Bold",
        spaceBefore=12,
        spaceAfter=6,
    )
    main_heading_style = ParagraphStyle(
        "MainHeading",
        parent=styles["Heading1"],
        fontSize=14,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#000000"),
        fontName="Helvetica-Bold",
        spaceBefore=16,
        spaceAfter=10,
    )
    question_style = ParagraphStyle(
        "Question",
        parent=styles["Normal"],
        fontSize=11,
        alignment=TA_LEFT,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1565c0"),
        spaceBefore=10,
        spaceAfter=6,
    )
    answer_style = ParagraphStyle(
        "Answer",
        parent=styles["Normal"],
        fontSize=11,
        alignment=TA_JUSTIFY,
        leading=16,
        spaceAfter=8,
        textColor=colors.HexColor("#2c3e50"),
    )
    small_style = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=9,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#020202"),
        leading=12,
    )

    story = []

    # Enhanced cover page
    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph(student_info.get("university", "UNIVERSITY").upper(), title_style))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("ACADEMIC ASSIGNMENT", subtitle_style))
    story.append(Paragraph(student_info.get("subject", ""), subtitle_style))
    story.append(Spacer(1, 0.15 * inch))

    # Student information table
    student_table = [
        ["Student Name:", student_info.get("name", "")],
        ["Student ID:", student_info.get("id", "")],
        ["Program:", student_info.get("program", "")],
        ["Instructor:", student_info.get("instructor", "N/A")],
        ["Semester / Term:", student_info.get("semester", "N/A")],
        ["Submission Date:", datetime.now().strftime("%B %d, %Y")],
    ]
    tbl = Table(student_table, colWidths=[2.0 * inch, 4.8 * inch], hAlign="CENTER")
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f0fe")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2c3e50")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b8d4f1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 0.3 * inch))
    
    story.append(Paragraph("_" * 80, small_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(PageBreak())

    # Main content parsing
    content_lines = assignment_content.splitlines()
    in_references = False
    
    for raw_line in content_lines:
        line = raw_line.strip()
        if not line:
            continue
        
        clean_line = line.replace("**", "")
        
        if re.match(r"^##\s*REFERENCES", clean_line.upper()):
            in_references = True
        
        if line.startswith("## "):
            clean_line = line.replace("## ", "").replace("**", "")
            story.append(Paragraph(clean_line.upper(), main_heading_style))
            continue
        if line.startswith("### "):
            clean_line = line.replace("### ", "").replace("**", "")
            story.append(Paragraph(clean_line, heading_style))
            continue
        
        if re.match(r"^Subheading:\s*", clean_line, re.IGNORECASE):
            subheading_text = re.sub(r"^Subheading:\s*", "", clean_line, flags=re.IGNORECASE).strip()
            story.append(Paragraph(subheading_text, heading_style))
            continue
        
        if re.match(r"^\*\*Question:\*\*", line, re.IGNORECASE):
            clean_line = re.sub(r"^\*\*Question:\*\*", "Question:", line, flags=re.IGNORECASE)
            story.append(Paragraph(clean_line, question_style))
            continue
        
        if re.match(r"^\*\*Answer:\*\*", line, re.IGNORECASE):
            clean_line = re.sub(r"^\*\*Answer:\*\*", "Answer:", line, flags=re.IGNORECASE)
            story.append(Paragraph(clean_line, question_style))
            continue
        
        if re.match(r"^\*\*(INTRODUCTION|LEARNING OBJECTIVES|EVALUATION RUBRIC|REFERENCES|ASSIGNMENT BODY|CONCLUSION)[\*:]", clean_line.upper(), re.IGNORECASE):
            clean_text = clean_line.replace("**", "").replace(":", "").strip().upper()
            story.append(Paragraph(clean_text, main_heading_style))
            continue
            
        if re.match(r"^(INTRODUCTION:|LEARNING OBJECTIVES:|EVALUATION RUBRIC:|REFERENCES:|ASSIGNMENT BODY:|CONCLUSION:)", clean_line, re.IGNORECASE):
            story.append(Paragraph(clean_line.upper(), main_heading_style))
            continue
        
        if re.match(r"^Q\d+[\.\)]", clean_line):
            story.append(Paragraph(clean_line, question_style))
            continue
        
        if re.match(r"^Answer\s*\d+:", clean_line, re.IGNORECASE):
            story.append(Paragraph(clean_line, question_style))
            continue
        
        if in_references and re.match(r"^\d+\.\s", clean_line):
            story.append(Paragraph(clean_line, small_style))
            continue
        
        story.append(Paragraph(clean_line, answer_style))

    # Page numbering and logo callback
    def add_page_elements(canvas, doc):
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawRightString(7.5 * inch, 0.55 * inch, text)
        
        canvas.setStrokeColor(colors.HexColor("#d1d5db"))
        canvas.setLineWidth(0.5)
        canvas.line(0.9 * inch, 0.65 * inch, 7.6 * inch, 0.65 * inch)
        
        if logo_data:
            try:
                logo_buffer = BytesIO(logo_data)
                logo_img = RLImage(logo_buffer, width=0.8*inch, height=0.8*inch)
                logo_img.drawOn(canvas, 0.5*inch, letter[1] - 1.0*inch)
            except Exception as e:
                pass

    doc.build(story, onFirstPage=add_page_elements, onLaterPages=add_page_elements)
    buffer.seek(0)
    return buffer

@st.cache_data(ttl=CACHE_TTL)
def create_pdf_cached(student_info_json: str, assignment_content: str, include_refs: bool, logo_data: bytes = None) -> bytes:
    student_info = json.loads(student_info_json)
    buffer = create_pdf(student_info, assignment_content, include_refs, logo_data)
    return buffer.getvalue()

# Generate button area
st.markdown("---")
generate_col1, generate_col2, generate_col3 = st.columns([1, 2, 1])
with generate_col2:
    generate_button = st.button(
        "🚀 Generate Assignment", 
        type="primary", 
        use_container_width=True,
        disabled=st.session_state.is_generating
    )
    
    if generate_button:
        if not api_key or len(api_key.strip()) < 10:
            st.error("❌ **API Key Required**: Please enter a valid Google Gemini API key in the sidebar.")
            st.info("💡 Get your free API key at: https://makersuite.google.com/app/apikey")
        else:
            errors = validate_inputs()
            if errors:
                st.error("**Please fix the following errors:**")
                for err in errors:
                    st.markdown(err)
            else:
                st.session_state.is_generating = True
                progress = st.progress(0, text="Initializing...")
                try:
                    progress.progress(10, text="Building prompt...")
                    progress.progress(20, text=f"Connecting to {gemini_model}...")
                    
                    assignment_content, gen_time = generate_assignment(
                        api_key=api_key,
                        topic=assignment_topic,
                        subject=subject_name,
                        num_qs=num_questions,
                        assign_type=assignment_type,
                        diff_level=difficulty,
                        include_refs=include_references,
                        include_ex=include_examples,
                        include_lo=include_learning_objectives,
                        include_rub=include_rubric,
                        model_name=gemini_model,
                        word_pref=word_count_preference,
                    )
                    
                    progress.progress(70, text="Processing response...")
                    
                    if assignment_content.startswith("❌"):
                        st.error(assignment_content)
                        progress.empty()
                    else:
                        progress.progress(90, text="Finalizing...")
                        
                        st.session_state.assignment_content = assignment_content
                        st.session_state.assignment_generated = True
                        st.session_state.student_info = {
                            "university": university_name,
                            "name": student_name,
                            "id": student_id,
                            "program": program_name,
                            "subject": subject_name,
                            "instructor": instructor_name or "N/A",
                            "semester": semester or "N/A",
                        }
                        st.session_state.total_generated += 1
                        st.session_state.generation_time = gen_time
                        
                        st.session_state.generation_history.append({
                            "timestamp": datetime.now(),
                            "subject": subject_name,
                            "student": student_name,
                            "gen_time": gen_time
                        })
                        
                        # Log activity
                        log_activity(
                            st.session_state.user_info['username'],
                            "ASSIGNMENT_GENERATED",
                            f"Subject: {subject_name}, Student: {student_name}"
                        )

                        progress.progress(100, text="Complete! ✨")
                        st.success(f"✅ **Assignment generated successfully!** (Generation time: {gen_time:.1f}s)")
                        
                        word_count = len(assignment_content.split())
                        st.info(f"📊 **Content Statistics:** {word_count:,} words | {len(assignment_content):,} characters")

                        with st.expander("📄 Preview Assignment Content", expanded=True):
                            st.markdown(assignment_content)

                        st.markdown("### 💾 Download Options")
                        col1, col2, col3 = st.columns(3)
                        
                        student_info_json = json.dumps(st.session_state.student_info)
                        pdf_bytes = create_pdf_cached(student_info_json, assignment_content, include_references, st.session_state.logo_data)
                        base_filename = f"{student_name.replace(' ', '_')}_{subject_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}"
                        
                        with col1:
                            st.download_button(
                                "📥 Download PDF",
                                data=pdf_bytes,
                                file_name=f"{base_filename}.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                            )
                        with col2:
                            st.download_button(
                                "📥 Download Markdown",
                                data=assignment_content,
                                file_name=f"{base_filename}.md",
                                mime="text/markdown",
                                use_container_width=True,
                            )
                        with col3:
                            st.download_button(
                                "📥 Download Text",
                                data=assignment_content,
                                file_name=f"{base_filename}.txt",
                                mime="text/plain",
                                use_container_width=True,
                            )
                        
                        progress.empty()
                        
                except Exception as e:
                    st.error(f"❌ **Unexpected Error**: {str(e)}")
                    st.info("💡 Try refreshing the page or checking your API key.")
                    progress.empty()
                finally:
                    st.session_state.is_generating = False

# Show previous assignment if exists
if st.session_state.assignment_generated and st.session_state.assignment_content and not st.session_state.is_generating:
    st.markdown("---")
    st.info("💡 **Previous assignment available below**")
    
    with st.expander("📖 View Previous Assignment", expanded=False):
        word_count = len(st.session_state.assignment_content.split())
        st.caption(f"📊 {word_count:,} words | Generated: {st.session_state.generation_history[-1]['timestamp'].strftime('%Y-%m-%d %H:%M')}")
        st.markdown(st.session_state.assignment_content)
    
    if st.session_state.student_info:
        st.markdown("### 💾 Download Previous Assignment")
        col1, col2, col3 = st.columns(3)
        
        student_info_json = json.dumps(st.session_state.student_info)
        pdf_bytes = create_pdf_cached(student_info_json, st.session_state.assignment_content, include_references, st.session_state.logo_data)
        prev_base_filename = f"{st.session_state.student_info['name'].replace(' ', '_')}_{st.session_state.student_info['subject'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}"
        
        with col1:
            st.download_button(
                "📥 PDF",
                data=pdf_bytes,
                file_name=f"{prev_base_filename}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                "📥 Markdown",
                data=st.session_state.assignment_content,
                file_name=f"{prev_base_filename}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col3:
            st.download_button(
                "📥 Text",
                data=st.session_state.assignment_content,
                file_name=f"{prev_base_filename}.txt",
                mime="text/plain",
                use_container_width=True,
            )

# Tips section
if not st.session_state.assignment_generated:
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

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align:center; color:#6b7280; padding:15px; background-color:#f9fafb; border-radius:10px'>
        <strong>📚 Ethicallogix Assignment Maker</strong><br>
         Developed by Muhammad Haseeb<br>
        <small>Version 3.0 | Admin Portal with User Management</small>
    </div>
    """,
    unsafe_allow_html=True,
)
