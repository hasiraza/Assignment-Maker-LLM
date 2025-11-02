# main.py
"""Main application file for Ethicallogix Assignment Maker"""

import streamlit as st
import json
from datetime import datetime
from PIL import Image

# Import modules
from config import *
from auth import (
    initialize_csv_files, authenticate_user, 
    get_user_stats, log_activity
)
from document_processor import (
    process_uploaded_document, 
    summarize_document_for_assignment
)
from ai_generator import generate_assignment
from pdf_generator import create_pdf
from ui_components import (
    show_login_page, show_admin_portal, 
    show_tips_section, show_footer
)


# Page configuration
st.set_page_config(
    page_title="Assignment Maker By Ethicallogix",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
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
    .upload-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px dashed #dee2e6;
        margin: 1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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
        "logo_data": None,
        "document_text": None,
        "document_summary": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Initialize
initialize_csv_files()
initialize_session_state()


# ==================== AUTHENTICATION ====================
if not st.session_state.authenticated:
    login_submit, login_username, login_password = show_login_page()
    
    show_footer()
    
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
    st.stop()


# ==================== ADMIN PORTAL ====================
if st.session_state.is_admin:
    logout = show_admin_portal()
    if logout:
        st.session_state.authenticated = False
        st.session_state.is_admin = False
        st.session_state.user_info = None
        st.rerun()
    st.stop()


# ==================== MAIN APPLICATION ====================

# Sidebar
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
    api_key = GOOGLE_API_KEY
    
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
        - 📄 Document upload support (NEW!)
        - 🖼️ Image text extraction
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
        for k in ['assignment_generated', 'assignment_content', 'generation_time', 'student_info', 'logo_data', 'document_text', 'document_summary']:
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
        placeholder="Dr.Farhan Aslam"
    )
    semester = st.text_input(
        "Semester/Term", 
        placeholder="Fall 2024"
    )
    
    # Logo upload section
    st.markdown("###### University Logo")
    uploaded_logo = st.file_uploader(
    "Upload",
    type=SUPPORTED_LOGO_FORMATS,
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


# Document Upload Section (NEW!)
st.markdown("---")
st.markdown("###  Upload Document")
# st.markdown(
#     """
#     <div class='upload-section'>
#         <p><strong>📄 Supported Formats:</strong> PDF, DOCX, TXT, MD, PNG, JPG, JPEG</p>
#         <p>Upload a document to extract content and use it as context for assignment generation.</p>
#     </div>
#     """,
#     unsafe_allow_html=True
# )

uploaded_document = st.file_uploader(
    "Choose a document file",
    type=SUPPORTED_IMAGE_FORMATS + SUPPORTED_DOCUMENT_FORMATS,
    help=f"Maximum file size: {MAX_DOCUMENT_SIZE_MB}MB"
)

if uploaded_document is not None:
    with st.spinner("Processing document..."):
        success, extracted_text, message = process_uploaded_document(uploaded_document, api_key)
        
        if success:
            st.success(f"✅ {message}")
            st.session_state.document_text = extracted_text
            
            # Show preview
            with st.expander("📖 View Extracted Text", expanded=False):
                st.text_area("Extracted Content", extracted_text, height=200, disabled=True)
            
            # Option to summarize
            if st.button("🤖 Generate AI Summary of Document"):
                with st.spinner("Creating summary..."):
                    sum_success, summary = summarize_document_for_assignment(extracted_text, api_key)
                    if sum_success:
                        st.session_state.document_summary = summary
                        st.success("✅ Summary generated!")
                        with st.expander("📝 View Summary", expanded=True):
                            st.markdown(summary)
                    else:
                        st.error(f"❌ {summary}")
        else:
            st.error(f"❌ {message}")
            st.session_state.document_text = None


st.markdown("### 📋 Assignment Topic / Prompt")
assignment_topic = st.text_area(
    "Describe the topic or assignment brief *",
    height=140,
    placeholder="Example: Explain time complexity of sorting algorithms and implement merge sort in Python with detailed analysis and complexity comparison.",
    help=f"Minimum {MIN_TOPIC_LENGTH} characters"
)

if st.session_state.document_summary:
    st.info("💡 **Tip:** You can use the AI summary of your uploaded document as the topic, or combine it with your own topic description.")

if assignment_topic:
    chars = len(assignment_topic)
    words = len(assignment_topic.split())
    st.caption(f"📊 {chars} characters | {words} words")


# Input validation
def validate_inputs():
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


# Generate button
st.markdown("---")
generate_col1, generate_col2, generate_col3 = st.columns([1, 2, 1])
with generate_col2:
    generate_button = st.button(
        "Generate Assignment", 
        type="primary", 
        use_container_width=True,
        disabled=st.session_state.is_generating
    )
    
    if generate_button:
        if not api_key or len(api_key.strip()) < 10:
            st.error("❌ **API Key Required**: Please configure API key in config.py")
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
                    progress.progress(15, text="⚙️ Preparing your assignment...")
                    progress.progress(30, text="🤖 AI is analyzing your requirements...")
                    progress.progress(50, text="✍️ Making your assignment...")
                    
                    # Use document context if available
                    document_context = st.session_state.document_text if st.session_state.document_text else None
                    
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
                        model_name=GEMINI_MODEL,
                        word_pref=word_count_preference,
                        document_context=document_context,
                    )
                    
                    progress.progress(75, text="📝 Finalizing your assignment...")
                    
                    if assignment_content.startswith("❌"):
                        st.error(assignment_content)
                        progress.empty()
                    else:
                        progress.progress(95, text="🎉 Almost done...")
                        
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
                        doc_info = " (with document context)" if document_context else ""
                        log_activity(
                            st.session_state.user_info['username'],
                            "ASSIGNMENT_GENERATED",
                            f"Subject: {subject_name}, Student: {student_name}{doc_info}"
                        )

                        progress.progress(100, text="✅ Complete!")
                        st.success(f"🎉 **Assignment generated successfully!** (Generated in {gen_time:.1f}s)")
                        
                        word_count = len(assignment_content.split())
                        st.info(f"📊 **Content Statistics:** {word_count:,} words | {len(assignment_content):,} characters")

                        # Download options
                        st.markdown("### 💾 Download Options")
                        col1, col2, col3 = st.columns(3)
                        
                        student_info_json = json.dumps(st.session_state.student_info)
                        pdf_buffer = create_pdf(
                            st.session_state.student_info,
                            assignment_content,
                            include_references,
                            st.session_state.logo_data
                        )
                        pdf_bytes = pdf_buffer.getvalue()
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
# if st.session_state.assignment_generated and st.session_state.assignment_content and not st.session_state.is_generating:
#     st.markdown("---")
    
#     with st.expander("📖 View Generated Assignment", expanded=False):
#         word_count = len(st.session_state.assignment_content.split())
#         st.caption(f"📊 {word_count:,} words | Generated: {st.session_state.generation_history[-1]['timestamp'].strftime('%Y-%m-%d %H:%M')}")
#         st.markdown(st.session_state.assignment_content)
    
#     if st.session_state.student_info:
#         st.markdown("### 💾 Download Your Assignment")
#         col1, col2, col3 = st.columns(3)
        
#         pdf_buffer = create_pdf(
#             st.session_state.student_info,
#             st.session_state.assignment_content,
#             include_references,
#             st.session_state.logo_data
#         )
#         pdf_bytes = pdf_buffer.getvalue()
#         prev_base_filename = f"{st.session_state.student_info['name'].replace(' ', '_')}_{st.session_state.student_info['subject'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}"
        
#         with col1:
#             st.download_button(
#                 "📥 PDF",
#                 data=pdf_bytes,
#                 file_name=f"{prev_base_filename}.pdf",
#                 mime="application/pdf",
#                 use_container_width=True,
#             )
#         with col2:
#             st.download_button(
#                 "📥 Markdown",
#                 data=st.session_state.assignment_content,
#                 file_name=f"{prev_base_filename}.md",
#                 mime="text/markdown",
#                 use_container_width=True,
#             )
#         with col3:
#             st.download_button(
#                 "📥 Text",
#                 data=st.session_state.assignment_content,
#                 file_name=f"{prev_base_filename}.txt",
#                 mime="text/plain",
#                 use_container_width=True,
#             )


# Tips section
if not st.session_state.assignment_generated:
    show_tips_section()

# Footer
show_footer()