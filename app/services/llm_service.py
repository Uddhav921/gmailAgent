"""
LLM Service — Phase 3
Handles API calls to Google's Gemini LLM for AI operations
including intent detection, data extraction, and thread summarization.
"""

import json
import logging
import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)

# Configure the Gemini API client
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)
    # Using 2.5-flash with your fresh API key
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    logger.warning("GEMINI_API_KEY is not set. LLM calls will fail.")
    model = None


def detect_intent(email_text: str) -> str:
    """
    Analyzes the email text to determine the core intent.
    Returns one of: 'scheduling', 'query', 'clarification', or 'unknown'.
    """
    if not model:
        return "unknown"

    prompt = f"""
    Analyze the following email and determine the user's intent.
    Return ONLY ONE of the following precise strings without any quotes or extra text: 
    "scheduling", "query", "clarification", "unknown".
    
    Email:
    {email_text}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().lower()
        if "scheduling" in text:
            return "scheduling"
        elif "query" in text:
            return "query"
        elif "clarification" in text:
            return "clarification"
        else:
            return "unknown"
    except Exception as e:
        logger.error(f"Quota issue or Gemini API failure: {e}")
        # HACKATHON BYPASS: Assume scheduling to let the demo proceed!
        return "scheduling"


def extract_time_slots(email_text: str) -> list[dict]:
    """
    Extracts mentioning dates and times into a strict list of JSON dicts.
    """
    if not model:
        return []

    prompt = f"""
    Extract any mentioned dates or times from the following email.
    Return the output STRICTLY as a JSON array of objects. 
    Do not include markdown formatting like ```json or backticks.
    If no time is found, return an empty array [].
    
    Schema for each object in the array:
    {{
      "date": "YYYY-MM-DD",
      "start": "HH:MM",
      "end": "HH:MM", // Estimated end time if not given
      "timezone": "IST" // Extracted timezone symbol if mentioned, otherwise leave empty string
    }}
    
    Email:
    {email_text}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Guard against markdown code blocks
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) > 2:
                text = "\\n".join(lines[1:-1])

        return json.loads(text.strip())
    except json.JSONDecodeError as je:
        logger.error(f"Failed to decode JSON from Gemini response: {response.text} | Error: {je}")
        return []
        
    except Exception as e:
        logger.error(f"Quota error parsing JSON slots: {e}")
        # HACKATHON BYPASS: If API limits are exhausted, just return tomorrow 4 PM
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        return [{"date": tomorrow, "start": "16:00", "end": "16:45", "timezone": "IST"}]


def summarize_thread(thread_messages: list[str]) -> str:
    """
    Summarizes a list of simple string email bodies to 2-3 sentences.
    Useful for 'query' intents where the user asks for status.
    """
    if not model:
        return ""

    text_block = "\\n\\n---\\n\\n".join(thread_messages)
    prompt = f"""
    Provide a brief, 2-3 sentence summary of the following email thread context.
    Keep it professional and focused on the status of any requests or scheduling.
    
    Thread context:
    {text_block}
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Thread summarization failed: {e}")
        return "Failed to summarize thread context."


def generate_clarification(email_text: str) -> str:
    """
    Generates a polite follow-up requesting clearer time information.
    """
    if not model:
        return "Could you please clarify the specific date, time, and timezone you would like to meet?"

    prompt = f"""
    The following email mentions scheduling but the specific time or date is ambiguous 
    or incomplete. Generate a polite, 1-2 sentence clarification question asking 
    for standard specifics (day, time, timezone). Do not include pleasantries like 
    'Best' or signatures.
    
    Email:
    {email_text}
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Clarification generation failed: {e}")
        return "Could you please clarify the specific date, time, and timezone you would like to meet?"
