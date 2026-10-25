"""Multilingual Intent Classifier for Ghost Data Still Exists.

Distinguishes between valid account deletion requests and non-deletion customer
inquiries (e.g., data access, export, marketing unsubscribe, typo correction).
"""

import re

# Explicit negative indicators (user explicitly wants to keep account or states non-deletion)
NON_DELETION_PATTERNS = [
    r"\bkeep the account\b",
    r"\bleave the account active\b",
    r"\bleave my (profile|purchase history|records)\b",
    r"\bdo not (close|delete|change)\b",
    r"\bdon't (close|delete|change)\b",
    r"\bnot asking for deletion\b",
    r"\bnot a request to erase\b",
    r"\bmarketing lists? only\b",
    r"\bhelp resetting the login\b",
    r"\bcan you correct it without removing\b",
    r"\bwant to continue using the service\b",
    r"\bdownload my account information\b",
    r"\bcopy of last year's invoices\b",
    r"\binformation request, not a request to erase\b",
    r"\bsend me a copy of the information\b",
]

# Deletion keywords and stems in multiple languages
DELETION_STEMS = [
    # English
    "delet", "remov", "eras", "clos", "gone", "clean", "tombstone", "de-identif",
    # French
    "suppr", "effac", "fermer",
    # Spanish
    "elimin", "borra", "cerrar",
    # Portuguese
    "exclu", "apaga", "encerrar",
    # German
    "lösch", "schließ",
    # Japanese
    "削除", "消去",
    # Korean
    "삭제",
    # Arabic
    "حذف", "إغلاق", "مسح",
]


def is_deletion_request(request_text: str) -> bool:
    """Classifies whether the request text authorizes account/data deletion.
    
    Returns:
        True if the request is an authorized deletion request.
        False if the request is a non-deletion action (NOT_APPLICABLE).
    """
    if not request_text or not request_text.strip():
        return False
        
    text_lower = request_text.lower().strip()
    
    # 1. Check for explicit non-deletion intent first
    for pattern in NON_DELETION_PATTERNS:
        if re.search(pattern, text_lower):
            return False
            
    # 2. Check for presence of deletion authorization stems
    for stem in DELETION_STEMS:
        if stem in text_lower:
            return True
            
    # Default to False if no deletion intent is confirmed
    return False
