"""Enhanced PDF generation module with markdown and code block support"""

import re
from io import BytesIO
from datetime import datetime
from typing import Dict, List
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
    Preformatted,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib import colors


def get_pdf_styles() -> Dict:
    """Get custom PDF styles for different elements"""
    styles = getSampleStyleSheet()

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
    
    heading1_style = ParagraphStyle(
        "Heading1",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#1a1a1a"),
        fontName="Helvetica-Bold",
        spaceBefore=18,
        spaceAfter=10,
    )
    
    heading2_style = ParagraphStyle(
        "Heading2",
        parent=styles["Heading2"],
        fontSize=13,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#2c2c2c"),
        fontName="Helvetica-Bold",
        spaceBefore=14,
        spaceAfter=7,
    )
    
    heading3_style = ParagraphStyle(
        "Heading3",
        parent=styles["Heading3"],
        fontSize=11,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#444444"),
        fontName="Helvetica-Bold",
        spaceBefore=10,
        spaceAfter=5,
    )
    
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        alignment=TA_JUSTIFY,
        leading=16,
        spaceAfter=8,
        textColor=colors.HexColor("#2c3e50"),
    )
    
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=styles["Normal"],
        fontSize=11,
        alignment=TA_LEFT,
        leading=15,
        leftIndent=25,
        spaceAfter=5,
        textColor=colors.HexColor("#2c3e50"),
        bulletIndent=10,
    )
    
    numbered_style = ParagraphStyle(
        "Numbered",
        parent=styles["Normal"],
        fontSize=11,
        alignment=TA_LEFT,
        leading=15,
        leftIndent=25,
        spaceAfter=5,
        textColor=colors.HexColor("#2c3e50"),
    )
    
    code_style = ParagraphStyle(
        "Code",
        parent=styles["Code"],
        fontSize=9,
        fontName="Courier",
        textColor=colors.HexColor("#e83e8c"),
        leftIndent=5,
        rightIndent=5,
        spaceBefore=1,
        spaceAfter=1,
        leading=13,
    )
    
    reference_style = ParagraphStyle(
        "Reference",
        parent=styles["Normal"],
        fontSize=10,
        alignment=TA_LEFT,
        leading=14,
        spaceAfter=6,
        textColor=colors.HexColor("#4a4a4a"),
        leftIndent=15,
        firstLineIndent=-15,
    )

    return {
        'title': title_style,
        'subtitle': subtitle_style,
        'heading1': heading1_style,
        'heading2': heading2_style,
        'heading3': heading3_style,
        'body': body_style,
        'bullet': bullet_style,
        'numbered': numbered_style,
        'code': code_style,
        'reference': reference_style,
    }


def create_cover_page(student_info: Dict[str, str], styles: Dict) -> List:
    """Create PDF cover page"""
    story = []
    
    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph(student_info.get("university", "UNIVERSITY").upper(), styles['title']))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("ACADEMIC ASSIGNMENT", styles['subtitle']))
    story.append(Paragraph(student_info.get("subject", ""), styles['subtitle']))
    story.append(Spacer(1, 0.15 * inch))

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
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f0fe")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#2c3e50")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b8d4f1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    
    story.append(tbl)
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("_" * 80, styles['reference']))
    story.append(Spacer(1, 0.2 * inch))
    story.append(PageBreak())
    
    return story


def process_inline_markdown(text: str) -> str:
    """Process inline markdown - bold, italic, inline code"""
    # Store code snippets to protect them
    code_snippets = []
    def save_code(match):
        code_snippets.append(match.group(1))
        return f"___CODE_{len(code_snippets)-1}___"
    
    text = re.sub(r'`([^`]+)`', save_code, text)
    
    # Bold: **text**
    text = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', text)
    
    # Italic: *text*
    text = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'<i>\1</i>', text)
    
    # Restore code with formatting
    for i, code in enumerate(code_snippets):
        code_escaped = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        text = text.replace(f"___CODE_{i}___", 
                          f'<font name="Courier" color="#e83e8c" backColor="#f8f9fa"> {code_escaped} </font>')
    
    return text


def create_code_block(code_lines: List[str], language: str = "") -> List:
    """Create Notion-style code block"""
    elements = []
    styles = get_pdf_styles()
    
    # Header bar
    header_text = f" {language.upper() if language else 'CODE'}"
    header_para = Paragraph(
        f'<font color="#ffffff" name="Helvetica-Bold" size="9">{header_text}</font>',
        styles['code']
    )
    
    header_table = Table([[header_para]], colWidths=[6.8 * inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#343a40")),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(header_table)
    
    # Code content
    code_rows = []
    for line in code_lines:
        if not line.strip():
            line = " "
        line_escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        code_para = Paragraph(
            f'<font name="Courier" size="9" color="#212529">{line_escaped}</font>',
            styles['code']
        )
        code_rows.append([code_para])
    
    code_table = Table(code_rows, colWidths=[6.6 * inch])
    code_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(code_table)
    
    # Bottom border
    border_table = Table([['']], colWidths=[6.8 * inch])
    border_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 1.5, colors.HexColor("#dee2e6")),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(border_table)
    elements.append(Spacer(1, 0.12 * inch))
    
    return elements


def parse_content_to_pdf(assignment_content: str, styles: Dict) -> List:
    """Parse markdown content to PDF elements"""
    story = []
    lines = assignment_content.splitlines()
    
    in_code_block = False
    code_lines = []
    code_language = ""
    in_references = False
    
    for line in lines:
        stripped = line.strip()
        
        # Code block start/end
        if stripped.startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_language = stripped[3:].strip()
                code_lines = []
            else:
                in_code_block = False
                story.extend(create_code_block(code_lines, code_language))
                code_lines = []
            continue
        
        if in_code_block:
            code_lines.append(line)
            continue
        
        # Empty line
        if not stripped:
            story.append(Spacer(1, 0.08 * inch))
            continue
        
        # Check for references section
        if re.match(r'^#+\s*(references?|bibliography)$', stripped, re.IGNORECASE):
            in_references = True
            story.append(Paragraph("References", styles['heading1']))
            continue
        
        # Heading levels: ##, ###, ####
        heading_match = re.match(r'^(#{1,4})\s+(.+)$', stripped)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).replace('**', '').replace('*', '')
            
            if level == 1:
                story.append(Paragraph(heading_text, styles['heading1']))
            elif level == 2:
                story.append(Paragraph(heading_text, styles['heading1']))
            elif level == 3:
                story.append(Paragraph(heading_text, styles['heading2']))
            else:
                story.append(Paragraph(heading_text, styles['heading3']))
            continue
        
        # Bullet points
        if re.match(r'^[\-\*\+]\s+', stripped):
            text = re.sub(r'^[\-\*\+]\s+', '• ', stripped)
            text = process_inline_markdown(text)
            story.append(Paragraph(text, styles['bullet']))
            continue
        
        # Numbered lists
        if re.match(r'^\d+\.\s+', stripped):
            text = process_inline_markdown(stripped)
            if in_references:
                story.append(Paragraph(text, styles['reference']))
            else:
                story.append(Paragraph(text, styles['numbered']))
            continue
        
        # Regular paragraph
        text = process_inline_markdown(stripped)
        story.append(Paragraph(text, styles['body']))
    
    return story


def create_pdf(
    student_info: Dict[str, str], 
    assignment_content: str, 
    include_refs: bool, 
    logo_data: bytes = None
) -> BytesIO:
    """Create PDF document"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1.2 * inch,
        bottomMargin=0.8 * inch,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
    )

    styles = get_pdf_styles()
    story = []

    # Cover page
    story.extend(create_cover_page(student_info, styles))
    
    # Main content
    story.extend(parse_content_to_pdf(assignment_content, styles))

    def add_page_elements(canvas, doc):
        """Add page numbers and logo"""
        page_num = canvas.getPageNumber()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawRightString(7.5 * inch, 0.55 * inch, f"Page {page_num}")
        
        canvas.setStrokeColor(colors.HexColor("#d1d5db"))
        canvas.setLineWidth(0.5)
        canvas.line(0.9 * inch, 0.65 * inch, 7.6 * inch, 0.65 * inch)
        
        if logo_data:
            try:
                logo_buffer = BytesIO(logo_data)
                logo_img = RLImage(logo_buffer, width=0.8*inch, height=0.8*inch)
                logo_img.drawOn(canvas, 0.5*inch, letter[1] - 1.0*inch)
            except:
                pass

    doc.build(story, onFirstPage=add_page_elements, onLaterPages=add_page_elements)
    buffer.seek(0)
    return buffer


def create_pdf_from_dict(pdf_config: Dict) -> BytesIO:
    """Create PDF from configuration dictionary"""
    return create_pdf(
        student_info=pdf_config.get('student_info', {}),
        assignment_content=pdf_config.get('assignment_content', ''),
        include_refs=pdf_config.get('include_refs', False),
        logo_data=pdf_config.get('logo_data', None)
    )


if __name__ == "__main__":
    print("Enhanced PDF Generator - Clean Version")
    print("-" * 50)
    
    test_student_info = {
        "university": "University of Technology",
        "name": "John Doe",
        "id": "ST12345",
        "program": "BS Computer Science",
        "subject": "Data Structures & Algorithms",
        "instructor": "Dr. Jane Smith",
        "semester": "Fall 2024"
    }
    
    test_content = """
## Understanding Data Structures

Data structures are **fundamental components** of computer science that provide *efficient* ways to organize data.

### Core Concepts

Key aspects include:
- Time complexity analysis
- Memory optimization
- Algorithm design patterns

### Binary Search Implementation

Here's a clean implementation:

```python
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
```

The function uses `O(log n)` time complexity.

### Applications

Common uses:
1. Database indexing
2. File system management
3. Network routing protocols

## References

1. Cormen, T. H. (2009). Introduction to Algorithms. MIT Press.
2. Sedgewick, R. (2011). Algorithms. Addison-Wesley.
"""
    
    print("Creating clean PDF...")
    pdf_buffer = create_pdf(test_student_info, test_content, True, None)
    
    with open("test_clean.pdf", "wb") as f:
        f.write(pdf_buffer.getvalue())
    
    print("✅ Clean PDF created: test_clean.pdf")
    print(f"Size: {len(pdf_buffer.getvalue())} bytes")