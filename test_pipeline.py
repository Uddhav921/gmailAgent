import logging
logging.basicConfig(level=logging.INFO)

from app.services.thread_analyzer import process_unread_emails_pipeline

if __name__ == "__main__":
    result = process_unread_emails_pipeline()
    print("FINAL RESULT:", result)
