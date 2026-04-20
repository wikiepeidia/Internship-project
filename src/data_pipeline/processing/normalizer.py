import re
import ftfy
import unicodedata

def normalize_text(text: str) -> str:
    """
    Normalizes Vietnamese text preserving code-switch tokens.
    
    1. Fixes mojibake using ftfy.
    2. Applies NFC normalization for canonical Vietnamese diacritics.
    3. Strips leading/trailing whitespace.
    4. Collapses multiple whitespace to a single space.
    """
    # 1. Fix mojibake
    text = ftfy.fix_text(text)
    
    # 2. NFC normalization
    text = unicodedata.normalize("NFC", text)
    
    # 3. & 4. Strip and collapse whitespace
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    
    return text
