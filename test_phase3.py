import json
import logging

logging.basicConfig(level=logging.ERROR)

from app.services.llm_service import detect_intent, extract_time_slots, generate_clarification
from app.services.time_parser import parse_time_string, normalize_to_utc

def run_tests():
    print("--- Testing Phase 3: AI / NLP Layer ---\\n")

    test_emails = [
        "Hi, let's schedule a meeting for tomorrow at 2 PM IST. Does that work?"
    ]

    for i, email in enumerate(test_emails):
        print(f"\\n[Test {i+1}] Email: '{email}'")
        
        # 1. Intent Detection
        intent = detect_intent(email)
        print(f" -> Intent Detected: {intent}")
        
        # 2. Clarification Generation (if ambiguous)
        if intent == "scheduling":
            if "tomorrow" in email and "4 PM" not in email:
                 # Simulating ambiguity check
                 clarification = generate_clarification(email)
                 print(f" -> Clarification: {clarification}")
            
            # 3. Time Extraction
            slots = extract_time_slots(email)
            print(f" -> Extracted Slots (JSON): {json.dumps(slots)}")
            
            # 4. Time Parsing (convert to UTC)
            if slots:
                for slot in slots:
                    time_str = f"{slot.get('date')} at {slot.get('start')} {slot.get('timezone', '')}".strip()
                    dt = parse_time_string(time_str)
                    if dt:
                        utc_dt = normalize_to_utc(dt)
                        print(f" -> Parsed Time: {dt}  |  Converted to UTC: {utc_dt.isoformat()}")
                    else:
                        print(f" -> Failed to parse: {time_str}")

if __name__ == "__main__":
    run_tests()
