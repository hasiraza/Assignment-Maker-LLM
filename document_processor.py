import os
from io import BytesIO
from typing import Tuple, Optional
from PIL import Image
import PyPDF2
import docx
import google.generativeai as genai
from config import UPLOAD_FOLDER, MAX_DOCUMENT_SIZE_MB, GOOGLE_API_KEY


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_file = BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")


def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file"""
    try:
        docx_file = BytesIO(file_content)
        doc = docx.Document(docx_file)
        text = ""
        
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    except Exception as e:
        raise Exception(f"Error reading DOCX: {str(e)}")


def extract_text_from_txt(file_content: bytes) -> str:
    """Extract text from TXT file"""
    try:
        return file_content.decode('utf-8').strip()
    except Exception as e:
        raise Exception(f"Error reading TXT: {str(e)}")


def extract_text_from_image(file_content: bytes, api_key: str) -> str:
    """Extract text from image using Google Gemini Vision"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Open image
        image = Image.open(BytesIO(file_content))
        
        # Use Gemini to extract text
        prompt = """Extract all text content from this image. 
        Include all visible text, maintaining the original structure and formatting as much as possible.
        If this is a document or assignment, extract the complete text.
        If there are equations, formulas, or special symbols, describe them clearly."""
        
        response = model.generate_content([prompt, image])
        return response.text.strip()
    except Exception as e:
        raise Exception(f"Error extracting text from image: {str(e)}")


def process_uploaded_document(uploaded_file, api_key: str) -> Tuple[bool, str, str]:
    """
    Process uploaded document and extract text
    Returns: (success, extracted_text, message)
    """
    try:
        # Check file size
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if file_size_mb > MAX_DOCUMENT_SIZE_MB:
            return False, "", f"File size exceeds {MAX_DOCUMENT_SIZE_MB}MB limit"
        
        file_content = uploaded_file.read()
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        # Process based on file type
        if file_extension == 'pdf':
            text = extract_text_from_pdf(file_content)
        elif file_extension == 'docx':
            text = extract_text_from_docx(file_content)
        elif file_extension == 'txt':
            text = extract_text_from_txt(file_content)
        elif file_extension == 'md':
            text = extract_text_from_txt(file_content)
        elif file_extension in ['png', 'jpg', 'jpeg']:
            if not api_key or len(api_key.strip()) < 10:
                return False, "", "API key required for image text extraction"
            text = extract_text_from_image(file_content, api_key)
        else:
            return False, "", f"Unsupported file format: {file_extension}"
        
        if not text or len(text.strip()) < 10:
            return False, "", "Could not extract meaningful text from the document"
        
        word_count = len(text.split())
        char_count = len(text)
        
        return True, text, f"Successfully extracted {word_count} words ({char_count} characters)"
        
    except Exception as e:
        return False, "", f"Error processing document: {str(e)}"


def summarize_document_for_assignment(document_text: str, api_key: str) -> Tuple[bool, str]:
    """
    Use AI to summarize document content and extract key topics for assignment generation
    Returns: (success, summary)
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""Analyze the following document and provide a comprehensive summary suitable for generating an academic assignment.

Document Content:
{document_text}

Please provide:
1. Main topics and themes
2. Key concepts and ideas
3. Important points that should be covered
4. Suggested assignment focus areas

Format your response as a clear, structured summary that can be used as the basis for an assignment prompt."""

        response = model.generate_content(prompt)
        return True, response.text
        
    except Exception as e:
        return False, f"Error summarizing document: {str(e)}"