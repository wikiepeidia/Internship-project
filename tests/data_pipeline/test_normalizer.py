import pytest
from src.data_pipeline.processing.normalizer import normalize_text

def test_normalize_fixes_mojibake():
    # Example mojibake
    text = "NgÃ¢n hÃ ng" # "Ngân hàng" with mojibake
    normalized = normalize_text(text)
    assert "Ngân" in normalized

def test_normalize_nfc():
    # NFD representation of "Tiếng Việt"
    nfd_text = "T" + "i" + "e\u0302\u0301" + "n" + "g" + " " + "V" + "i" + "e\u0302\u0323" + "t"
    normalized = normalize_text(nfd_text)
    # NFC representation
    assert normalized == "Tiếng Việt"

def test_normalize_preserves_code_switch():
    text = "Vui lòng nhập mã OTP để login vào app Internet Banking."
    normalized = normalize_text(text)
    assert "OTP" in normalized
    assert "login" in normalized
    assert "app" in normalized
    assert "Internet Banking" in normalized

def test_normalize_preserves_teencode():
    text = "a ko bit dau nha, nt dc ko"
    normalized = normalize_text(text)
    assert "ko" in normalized
    assert "nha" in normalized
    assert "dc" in normalized

def test_normalize_whitespace():
    text = "   This   is  a test\tmessage \nwith lots of    spaces.  "
    normalized = normalize_text(text)
    assert normalized == "This is a test message with lots of spaces."
