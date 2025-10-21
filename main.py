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

# Page configuration
st.set_page_config(
    page_title="Assignment Maker By Ethicallogix",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Enhanced custom CSS for polished UI
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

# Initialize session state
def initialize_session_state():
    defaults = {
        "assignment_generated": False,
        "assignment_content": None,
        "generation_time": None,
        "total_generated": 0,
        "generation_history": [],
        "is_generating": False,
        "student_info": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

# Header
st.title("📚 Ethicallogix Assignment Maker")
st.markdown(
    "<p style='text-align:center; color:#6b7280'>Generate professional academic assignments with AI-powered content</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# Sidebar configuration
with st.sidebar:
    st.header("Powered By Ethicallogix")
    api_key = os.getenv("GOOGLE_API_KEY", "")
    
    
    gemini_model ="gemini-2.0-flash-exp"
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
        """
    )

    st.markdown("---")
    if st.button("🔄 Reset App", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# Main form
st.subheader("📝 Assignment Details")

col1, col2 = st.columns(2)
with col1:
    university_name = st.text_input(
        "University Name *", 
        placeholder="University of Lahore",
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
    st.text_input("", placeholder="", disabled=True, label_visibility="hidden")  # Spacer
    subject_name = st.text_input(
        "Subject Name *", 
        placeholder="Machine Learning",
        help=f"Minimum {MIN_SUBJECT_NAME_LENGTH} characters"
    )
    instructor_name = st.text_input(
        "Instructor Name", 
        placeholder="Dr. Sarah Johnson"
    )
    semester = st.text_input(
        "Semester/Term", 
        placeholder="Fall 2024"
    )

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

    # Optional blocks
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

# PDF generation with cover page, page numbers, and styling
@st.cache_data(ttl=CACHE_TTL)
def create_pdf_cached(student_info_json: str, assignment_content: str, include_refs: bool) -> bytes:
    student_info = json.loads(student_info_json)
    buffer = create_pdf(student_info, assignment_content, include_refs)
    return buffer.getvalue()

def create_pdf(student_info: Dict[str, str], assignment_content: str, include_refs: bool) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.8 * inch,
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
    info_style = ParagraphStyle(
        "Info",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#000000"),
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
    
    # Add decorative line
    story.append(Paragraph("_" * 80, small_style))
    story.append(Spacer(1, 0.2 * inch))
    story.append(PageBreak())

    # Main content parsing and formatting
    content_lines = assignment_content.splitlines()
    in_references = False
    
    for raw_line in content_lines:
        line = raw_line.strip()
        if not line:
            continue
        
        # Remove all ** markdown bold markers from the line for processing
        clean_line = line.replace("**", "")
        
        # Check if we're in references section
        if re.match(r"^##\s*REFERENCES", clean_line.upper()):
            in_references = True
        
        # Handle Markdown headings (## for main sections, ### for subsections)
        if line.startswith("## "):
            clean_line = line.replace("## ", "").replace("**", "")
            story.append(Paragraph(clean_line.upper(), main_heading_style))
            continue
        if line.startswith("### "):
            clean_line = line.replace("### ", "").replace("**", "")
            story.append(Paragraph(clean_line, heading_style))
            continue
        
        # Handle "Subheading:" pattern
        if re.match(r"^Subheading:\s*", clean_line, re.IGNORECASE):
            subheading_text = re.sub(r"^Subheading:\s*", "", clean_line, flags=re.IGNORECASE).strip()
            story.append(Paragraph(subheading_text, heading_style))
            continue
        
        # Handle **Question:** pattern
        if re.match(r"^\*\*Question:\*\*", line, re.IGNORECASE):
            clean_line = re.sub(r"^\*\*Question:\*\*", "Question:", line, flags=re.IGNORECASE)
            story.append(Paragraph(clean_line, question_style))
            continue
        
        # Handle **Answer:** pattern
        if re.match(r"^\*\*Answer:\*\*", line, re.IGNORECASE):
            clean_line = re.sub(r"^\*\*Answer:\*\*", "Answer:", line, flags=re.IGNORECASE)
            story.append(Paragraph(clean_line, question_style))
            continue
        
        # Handle bold section headers
        if re.match(r"^\*\*(INTRODUCTION|LEARNING OBJECTIVES|EVALUATION RUBRIC|REFERENCES|ASSIGNMENT BODY|CONCLUSION)[\*:]", clean_line.upper(), re.IGNORECASE):
            clean_text = clean_line.replace("**", "").replace(":", "").strip().upper()
            story.append(Paragraph(clean_text, main_heading_style))
            continue
            
        # Headings without markdown
        if re.match(r"^(INTRODUCTION:|LEARNING OBJECTIVES:|EVALUATION RUBRIC:|REFERENCES:|ASSIGNMENT BODY:|CONCLUSION:)", clean_line, re.IGNORECASE):
            story.append(Paragraph(clean_line.upper(), main_heading_style))
            continue
        
        # Question lines
        if re.match(r"^Q\d+[\.\)]", clean_line):
            story.append(Paragraph(clean_line, question_style))
            continue
        
        # Answer headings
        if re.match(r"^Answer\s*\d+:", clean_line, re.IGNORECASE):
            story.append(Paragraph(clean_line, question_style))
            continue
        
        # References - use small font
        if in_references and re.match(r"^\d+\.\s", clean_line):
            story.append(Paragraph(clean_line, small_style))
            continue
        
        # Default: body/answer paragraph
        story.append(Paragraph(clean_line, answer_style))

    # Page numbering callback
    def add_page_number(canvas, doc):
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawRightString(7.5 * inch, 0.55 * inch, text)
        
        # Add footer line
        canvas.setStrokeColor(colors.HexColor("#d1d5db"))
        canvas.setLineWidth(0.5)
        canvas.line(0.9 * inch, 0.65 * inch, 7.6 * inch, 0.65 * inch)

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    buffer.seek(0)
    return buffer

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
        # Validate API key first
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
                        
                        # Save to session state
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
                        
                        # Add to history
                        st.session_state.generation_history.append({
                            "timestamp": datetime.now(),
                            "subject": subject_name,
                            "student": student_name,
                            "gen_time": gen_time
                        })

                        progress.progress(100, text="Complete! ✨")
                        st.success(f"✅ **Assignment generated successfully!** (Generation time: {gen_time:.1f}s)")
                        
                        # Word count
                        word_count = len(assignment_content.split())
                        st.info(f"📊 **Content Statistics:** {word_count:,} words | {len(assignment_content):,} characters")

                        # Preview with enhanced display
                        with st.expander("📄 Preview Assignment Content", expanded=True):
                            st.markdown(assignment_content)

                        # Create PDF and download options
                        st.markdown("### 💾 Download Options")
                        col1, col2, col3 = st.columns(3)
                        
                        student_info_json = json.dumps(st.session_state.student_info)
                        pdf_bytes = create_pdf_cached(student_info_json, assignment_content, include_references)
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
        pdf_bytes = create_pdf_cached(student_info_json, st.session_state.assignment_content, include_references)
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
        """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align:center; color:#6b7280; padding:15px; background-color:#f9fafb; border-radius:10px'>
        <strong>📚 Ethicallogix Assignment Maker</strong><br>
         Developed by Muhammad Haseeb<br>
        <small>Version 2.0 | Enhanced Edition</small>
    </div>
    """,
    unsafe_allow_html=True,
)

# Add helpful information in sidebar footer
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🆘 Developer Details")
    st.markdown("""
    **Common Issues:**
    - **This Application Develope by Muhammad Haseeb Raza**
    
    **Best Practices:**
    - Save assignments immediately after generation
    - Keep topics focused and specific
    - Review and edit generated content
    - Cite sources appropriately
    """)
    
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align:center; font-size:0.8em; color:#9ca3af'>
        © 2025 Ethicallogix<br>
        All Rights Reserved
        </div>
        """,
        unsafe_allow_html=True,
    )