# auth.py
"""Authentication and user management module"""

import csv
import hashlib
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, Any


# Import config values (you'll need to adjust based on your config.py location)
try:
    from config import USERS_CSV, ACTIVITY_CSV, ADMIN_USERNAME, ADMIN_PASSWORD
except ImportError:
    # Fallback defaults if config not found
    USERS_CSV = "users.csv"
    ACTIVITY_CSV = "user_activity.csv"
    ADMIN_USERNAME = "hasi"
    ADMIN_PASSWORD = "system786@"


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
        print(f"Error logging activity: {str(e)}")


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
        print(f"Authentication error: {str(e)}")
        return False, {}, False


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
            return df[['username', 'email', 'full_name', 'registration_date', 'status']]
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading users: {str(e)}")
        return pd.DataFrame()


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
            
            if not users_df.empty:
                users_df_sorted = users_df.sort_values('registration_date', ascending=False)
                recent = users_df_sorted.head(5)[['username', 'full_name', 'registration_date']]
                stats['recent_registrations'] = recent.to_dict('records')
        
        if Path(ACTIVITY_CSV).exists():
            activity_df = pd.read_csv(ACTIVITY_CSV)
            stats['total_activities'] = len(activity_df)
            stats['total_assignments'] = len(activity_df[activity_df['activity_type'] == 'ASSIGNMENT_GENERATED'])
        
        return stats
    except Exception as e:
        print(f"Error getting statistics: {str(e)}")
        return {'total_users': 0, 'active_users': 0, 'total_assignments': 0, 'total_activities': 0, 'recent_registrations': []}