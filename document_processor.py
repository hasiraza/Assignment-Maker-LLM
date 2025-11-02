import os
from io import BytesIO
from typing import Tuple
from PIL import Image
import PyPDF2
import docx
import pytesseract
import google.generativeai as genai
from config import UPLOAD_FOLDER, MAX_DOCUMENT_SIZE_MB, GOOGLE_API_KEY


# ---------- TEXT EXTRACTION HELPERS ---------- #

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file."""
    try:
        pdf_file = BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")


def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file."""
    try:
        docx_file = BytesIO(file_content)
        doc = docx.Document(docx_file)
        text = "\n".join([p.text for p in doc.paragraphs])
        return text.strip()
    except Exception as e:
        raise Exception(f"Error reading DOCX: {str(e)}")


def extract_text_from_txt(file_content: bytes) -> str:
    """Extract text from TXT or MD file."""
    try:
        return file_content.decode('utf-8').strip()
    except Exception as e:
        raise Exception(f"Error reading TXT: {str(e)}")


def extract_text_from_image_local(file_content: bytes) -> str:
    """Extract text from image using local OCR (pytesseract)."""
    try:
        image = Image.open(BytesIO(file_content))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        raise Exception(f"Error extracting text from image (OCR): {str(e)}")


# ---------- DOCUMENT PROCESSING ---------- #

def process_uploaded_document(uploaded_file, api_key: str) -> Tuple[bool, str, str]:
    """
    Reads an uploaded file, extracts its text, and validates size and format.
    Returns: (success, text, message)
    """
    try:
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if file_size_mb > MAX_DOCUMENT_SIZE_MB:
            return False, "", f"File size exceeds {MAX_DOCUMENT_SIZE_MB} MB limit"

        file_content = uploaded_file.read()
        file_extension = uploaded_file.name.split('.')[-1].lower()

        if file_extension == 'pdf':
            text = extract_text_from_pdf(file_content)
        elif file_extension == 'docx':
            text = extract_text_from_docx(file_content)
        elif file_extension in ['txt', 'md']:
            text = extract_text_from_txt(file_content)
        elif file_extension in ['png', 'jpg', 'jpeg']:
            text = extract_text_from_image_local(file_content)
        else:
            return False, "", f"Unsupported file type: {file_extension}"

        if not text or len(text.strip()) < 10:
            return False, "", "No meaningful text extracted from document"

        word_count = len(text.split())
        char_count = len(text)
        return True, text, f"Extracted {word_count} words ({char_count} characters)"
    except Exception as e:
        return False, "", f"Error processing document: {str(e)}"


# ---------- SAFE SUMMARIZATION ---------- #

def summarize_in_chunks(text: str, api_key: str, chunk_size: int = 4000) -> Tuple[bool, str]:
    """
    Summarize long text safely by splitting it into chunks.
    Returns (success, final_summary)
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        # Break text into manageable pieces
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        summaries = []

        for idx, chunk in enumerate(chunks, start=1):
            prompt = f"Summarize the following part ({idx}/{len(chunks)}):\n\n{chunk}"
            response = model.generate_content(prompt)
            summaries.append(response.text.strip())

        # Combine all partial summaries into one final summary
        final_prompt = (
            "Combine the following summaries into one clear, structured academic summary:\n\n"
            + "\n\n".join(summaries)
        )
        final_response = model.generate_content(final_prompt)
        return True, final_response.text.strip()

    except Exception as e:
        return False, f"Error summarizing text: {str(e)}"


def summarize_document_for_assignment(document_text: str, api_key: str) -> Tuple[bool, str]:
    """
    Generates a comprehensive summary suitable for assignment creation.
    Uses chunking to avoid token limits.
    """
    try:
        # Limit overall length for safety
        MAX_CHARS = 16000
        if len(document_text) > MAX_CHARS:
            document_text = document_text[:MAX_CHARS] + "\n\n[Truncated for AI summarization]"

        return summarize_in_chunks(document_text, api_key)

    except Exception as e:
        return False, f"Error summarizing document: {str(e)}"
