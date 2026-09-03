import re
from typing import Tuple

CRISIS_KEYWORDS = [
    r"\bkill myself\b", r"\bsuicide\b", r"\bwant to die\b",
    r"\bend my life\b", r"\bself-harm\b", r"\bcut myself\b",
    r"\bhurt myself\b", r"\bno reason to live\b"
]

CRISIS_PAYLOAD = {
    "is_crisis": True,
    "response": "I hear how much pain you are experiencing, but you don't have to navigate this alone. Please reach out immediately to trained listeners who care and can support you safely.",
    "resources": [
        {"name": "Tele-MANAS (Free & 24/7)", "contact": "14416"},
        {"name": "KIRAN Helpline", "contact": "1800-599-0019"},
        {"name": "National Emergency Services", "contact": "112"}
    ]
}

def scan_for_crisis(text: str) -> Tuple[bool, dict | None]:
    for pattern in CRISIS_KEYWORDS:
        if re.search(pattern, text, re.IGNORECASE):
            return True, CRISIS_PAYLOAD
    return False, None
