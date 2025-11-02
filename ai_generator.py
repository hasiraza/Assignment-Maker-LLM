# ai_generator.py
"""AI-powered assignment generation using Google Gemini"""

import google.generativeai as genai
from datetime import datetime
from typing import Tuple, Dict, Any


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
    document_context: str = None,
) -> Tuple[str, Dict[str, Any]]:
    """Build the prompt for assignment generation"""
    
    word_count = "400-600"
    if "Concise" in word_pref:
        word_count = "200-300"
    elif "Detailed" in word_pref:
        word_count = "800-1000"

    examples_instruction = "Include practical examples and real-world applications." if include_ex else ""

    lo_block = ""
    if include_lo:
        lo_block = """
Include a section with 3-5 clear, measurable learning objectives that students should achieve.
"""

    rubric_block = ""
    if include_rub:
        rubric_block = """
Include an evaluation rubric with 4-5 criteria showing descriptors for different performance levels.
"""


    # Add document context if provided
    document_section = ""
    if document_context:
        document_section = f"""
DOCUMENT CONTEXT PROVIDED:
{document_context[:3000]}

Use this context to enhance the assignment content. Integrate the information naturally with additional insights.
"""

    prompt = f"""You are an expert university professor and academic writer.
Create a professional {assign_type} assignment for {diff_level}-level students.

Topic: {topic}
Subject: {subject}

{document_section}

FORMATTING REQUIREMENTS:
- Use ## for main topic headings (be specific to the topic, not generic)
- Use ### for subsections
- Write in formal academic English
- Target approximately {word_count} words total
- {examples_instruction}
- 

CONTENT STRUCTURE:
Write a well-organized academic paper that flows naturally:

1. Start with background and context (1-2 paragraphs introducing the topic)

2. Develop the main content through several specific topic-related sections using ## headings like:
   ## [Specific Topic Aspect 1]
   ## [Specific Topic Aspect 2]
   ## [Specific Topic Aspect 3]
   
   Under each main section, use ### for subsections to organize details.

3. End with synthesis and implications (1-2 paragraphs concluding insights)

{lo_block}
{rubric_block}

4. Add programming code if user say in attachment or in topic 

IMPORTANT: 
- Do NOT use generic headings like "Introduction", "Main Discussion", or "Conclusion"
- Use descriptive, topic-specific headings throughout
- Make the content flow like a professional research paper
- Provide academic reasoning, evidence-based arguments, and critical analysis
"""

    meta = {
        "word_count_range": word_count,
        "examples_instruction": examples_instruction,
        "num_questions": num_qs,
        "has_document_context": document_context is not None,
    }
    return prompt, meta


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
    document_context: str = None,
) -> Tuple[str, float]:
    """
    Generate assignment content using Google Gemini AI
    
    Args:
        api_key: Google Gemini API key
        topic: Assignment topic/prompt
        subject: Subject name
        num_qs: Number of questions (legacy parameter)
        assign_type: Type of assignment
        diff_level: Difficulty level
        include_refs: Include references
        include_ex: Include examples
        include_lo: Include learning objectives
        include_rub: Include rubric
        model_name: Gemini model name
        word_pref: Word count preference
        document_context: Optional document context for enhancement
        
    Returns:
        Tuple of (generated_content, generation_time_seconds)
    """
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
            document_context,
        )

        start = datetime.now()
        response = model.generate_content(prompt)
        end = datetime.now()
        gen_time = (end - start).total_seconds()

        return response.text, gen_time
        
    except Exception as e:
        msg = str(e)
        
        # Handle specific error types
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


def test_api_connection(api_key: str) -> Tuple[bool, str]:
    """
    Test the API connection with a simple request
    
    Args:
        api_key: Google Gemini API key
        
    Returns:
        Tuple of (success, message)
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        response = model.generate_content("Say 'API connection successful'")
        
        if response.text:
            return True, "✅ API connection successful!"
        else:
            return False, "❌ API returned empty response"
            
    except Exception as e:
        return False, f"❌ API connection failed: {str(e)}"


if __name__ == "__main__":
    # Test the module
    print("AI Generator Module - Test Mode")
    print("-" * 50)
    
    # Example usage
    test_topic = "Explain the concept of machine learning and its applications"
    test_subject = "Computer Science"
    
    print(f"Topic: {test_topic}")
    print(f"Subject: {test_subject}")
    print("\nBuilding prompt...")
    
    prompt, meta = build_prompt(
        topic=test_topic,
        subject=test_subject,
        num_qs=3,
        assign_type="Essay",
        diff_level="Intermediate",
        include_refs=True,
        include_ex=True,
        include_lo=True,
        include_rub=False,
        word_pref="Standard (400-600 words)",
        document_context=None
    )
    
    print("✅ Prompt built successfully!")
    print(f"Metadata: {meta}")
    print("\nNote: To test generation, add your API key and call generate_assignment()")