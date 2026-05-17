"""
Utilities — Shared helper functions, including failure recording.
"""

import os
from datetime import datetime

def log_failure(error_type: str, message: str, details: str = ""):
    """
    Log failures/issues to test_failed.txt for debugging purposes.
    Saves a timestamp, error type, message, and optional details.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{error_type.upper()}] {message}\n"
    
    if details:
        log_line += f"Details: {details}\n"
    log_line += "-" * 60 + "\n"
    
    try:
        with open("test_failed.txt", "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"Error writing to test_failed.txt: {e}")
