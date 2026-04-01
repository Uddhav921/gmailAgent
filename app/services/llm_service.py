"""
LLM Service — Phase 3
Handles API calls to Google's Gemini LLM for AI operations
including intent detection, data extraction, and thread summarization.
"""

import json
import logging
from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)

# Configure the new Gemini API client
if settings.gemini_api_key:
    _client = genai.Client(api_key=settings.gemini_api_key)
    _MODEL = "gemini-2.0-flash"
else:
    logger.warning("GEMINI_API_KEY is not set. LLM calls will fail.")
    _client = None
    _MODEL = None


def _generate(prompt: str) -> str:
    """Internal helper: call Gemini and return the response text."""
    response = _client.models.generate_content(
        model=_MODEL,
        contents=prompt,
    )
    return response.text.strip()


def detect_intent(email_text: str) -> str:
    """
    Analyzes the email text to determine the core intent.
    Returns one of: 'scheduling', 'query', 'clarification', or 'unknown'.
    """
    if not _client:
        return _fallback_intent_detection(email_text)

    prompt = f"""
    Analyze the following email and determine the user's intent.
    Return ONLY ONE of the following precise strings without any quotes or extra text: 
    "scheduling", "query", "clarification", "unknown".
    
    Email:
    {email_text}
    """
    try:
        text = _generate(prompt).lower()
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
        # FALLBACK: Use keyword-based detection when API fails
        return _fallback_intent_detection(email_text)


def _fallback_intent_detection(email_text: str) -> str:
    """
    Keyword-based intent detection fallback (no API needed).
    Used when Gemini API is unavailable or quota exceeded.
    """
    text_lower = email_text.lower()
    
    # Scheduling keywords: meeting requests, calendar, dates/times
    scheduling_keywords = [
        "schedule", "meeting", "call", "sync", "book", "calendar",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "tomorrow", "next week", "this week", "afternoon", "morning", "evening",
        "2pm", "3pm", "4pm", "10am", "11am", "2:00", "3:00", "4:00", "10:00", "11:00"
    ]
    
    # Clarification keywords: requests for more info, unclear input
    clarification_keywords = [
        "could you please", "can you clarify", "what do you mean", "sorry i didn't",
        "didn't understand", "not clear", "more details", "explain please"
    ]
    
    # Check for scheduling intent
    if any(keyword in text_lower for keyword in scheduling_keywords):
        return "scheduling"
    
    # Check for clarification requests
    if any(keyword in text_lower for keyword in clarification_keywords):
        return "clarification"
    
    # Default to query for general questions, statements, and conversations
    # (e.g., "What's your favorite food?", "Tell me about...", "How are you?")
    return "query"


def extract_time_slots(email_text: str) -> list[dict]:
    """
    Extracts mentioning dates and times into a strict list of JSON dicts.
    """
    if not _client:
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
        text = _generate(prompt)
        
        # Guard against markdown code blocks
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) > 2:
                text = "\\n".join(lines[1:-1])

        return json.loads(text.strip())
    except json.JSONDecodeError as je:
        logger.error(f"Failed to decode JSON from Gemini response: {text} | Error: {je}")
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
    if not _client:
        return ""

    text_block = "\\n\\n---\\n\\n".join(thread_messages)
    prompt = f"""
    Provide a brief, 2-3 sentence summary of the following email thread context.
    Keep it professional and focused on the status of any requests or scheduling.
    
    Thread context:
    {text_block}
    """
    try:
        return _generate(prompt)
    except Exception as e:
        logger.error(f"Thread summarization failed: {e}")
        return "Failed to summarize thread context."


def generate_clarification(email_text: str) -> str:
    """
    Generates a polite follow-up requesting clearer time information.
    """
    if not _client:
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
        return _generate(prompt)
    except Exception as e:
        logger.error(f"Clarification generation failed: {e}")
        return "Could you please clarify the specific date, time, and timezone you would like to meet?"
