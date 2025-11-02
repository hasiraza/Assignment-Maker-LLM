# config.py
"""Configuration settings for the Assignment Maker application"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash-exp"

# Input Validation Constants
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

# File Paths
USERS_CSV = "users.csv"
ACTIVITY_CSV = "user_activity.csv"
UPLOAD_FOLDER = "uploads"

# Supported File Types
SUPPORTED_IMAGE_FORMATS = ['png', 'jpg', 'jpeg']
SUPPORTED_DOCUMENT_FORMATS = ['pdf', 'txt', 'md', 'docx']
SUPPORTED_LOGO_FORMATS = ['png']

# File Size Limits (in MB)
MAX_LOGO_SIZE_MB = 2
MAX_DOCUMENT_SIZE_MB = 10

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Logging Configuration
import logging
import warnings

warnings.filterwarnings("ignore")
os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
os.environ.setdefault("GLOG_minloglevel", "2")
logging.getLogger("google").setLevel(logging.ERROR)