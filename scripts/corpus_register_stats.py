# corpus_register_stats.py
#
# Counts the three register features the thesis reports for its corpus:
#   1. messages that use Vietnamese chat abbreviations
#   2. messages typed with no diacritics at all
#   3. messages that contain at least one emoji
#
# The figures quoted in Section 1.1 and Chapter II are the train.jsonl row of
# this script's output. A message counts once for a feature no matter how many
# times the feature occurs inside it.
#
# Usage, from the repository root:  python -I scripts/corpus_register_stats.py

import json
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SPLIT_DIR = Path(__file__).resolve().parent.parent / "data" / "splits"

# ---------------------------------------------------------------------------
# The abbreviation list. Each entry is Vietnamese chat or SMS shorthand that
# was found in this corpus by inspection, with a gloss of what it stands for.
#
# Official acronyms that also appear in formal bank messages -- OTP, CCCD,
# CMND, CSKH, VCB, ACB, ATM, KYC -- are deliberately NOT in this list. They
# are not evidence of a chat register, and including them would nearly double
# the reported rate: OTP alone appears in 511 of the training messages.
# ---------------------------------------------------------------------------
ABBREVIATIONS = {
    "ko":  "khong",            # không
    "k":   "khong",            # không
    "tk":  "tai khoan",        # tài khoản
    "dc":  "duoc",             # được
    "đc":  "duoc",             # được
    "ak":  "a particle",       # chat respelling of "ạ" / "à"
    "lh":  "lien he",          # liên hệ
    "tb":  "thong bao",        # thông báo
    "gd":  "giao dich",        # giao dịch
    "nh":  "ngan hang",        # ngân hàng
    "kh":  "khach hang",       # khách hàng
    "nv":  "nhan vien",        # nhân viên
    "mk":  "minh / mat khau",  # mình or mật khẩu
    "ib":  "inbox",            # inbox
    "sdt": "so dien thoai",    # số điện thoại
    "sđt": "so dien thoai",    # số điện thoại
    "stk": "so tai khoan",     # số tài khoản
    "dt":  "dien thoai",       # điện thoại
    "đt":  "dien thoai",       # điện thoại
    "acc": "account",
    "bn":  "ban",              # bạn
    "ok":  "ok",
    "tks": "thanks",
}

# URLs are removed before tokenizing. Without this step, domain and path
# fragments get miscounted as shorthand: "bit.ly/..." reads as "bit",
# "/huy-gd?id=" reads as "gd", "techcom-kh.info" reads as "kh".
URL = re.compile(
    r"(?:https?://|www\.)\S+|\b[\w.-]+\.(?:com|net|vn|info|org|cc|ly|app|xyz)\b\S*",
    re.IGNORECASE)

WORD = re.compile(r"[0-9A-Za-zÀ-ỹđĐ]+")

# A diacritic-free message is one whose letters carry no Vietnamese tone or
# vowel mark. Found by NFD decomposition: "ầ" becomes "a" plus combining
# marks, "a" does not. "đ" carries no combining mark, so it is tested on its
# own.
COMBINING = re.compile(r"[̀-ͯ]")


def strip_urls(text):
    return URL.sub(" ", text)


def has_diacritics(text):
    if "đ" in text.lower():
        return True
    return bool(COMBINING.search(unicodedata.normalize("NFD", text)))


def is_emoji(ch):
    # Pictographic ranges only. Ordinary punctuation and the "đ" / "₫"
    # currency signs are not emoji.
    cp = ord(ch)
    return (0x1F300 <= cp <= 0x1FAFF      # symbols, pictographs, emoticons
            or 0x1F000 <= cp <= 0x1F2FF   # tiles, enclosed characters
            or 0x2600 <= cp <= 0x27BF     # miscellaneous symbols, dingbats
            or cp in (0x2764, 0x2B50, 0x2757, 0x203C))  # heart, star, ! and !!


def find_abbreviations(text):
    """The abbreviations present in one message, URLs removed."""
    tokens = set(WORD.findall(strip_urls(text).lower()))
    return sorted(tokens & set(ABBREVIATIONS))


def count(path):
    texts = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                texts.append(json.loads(line)["text"])

    n_abbrev = n_plain = n_emoji = 0
    per_token = {}
    for text in texts:
        found = find_abbreviations(text)
        if found:
            n_abbrev += 1
            for token in found:
                per_token[token] = per_token.get(token, 0) + 1
        if not has_diacritics(strip_urls(text)):
            n_plain += 1
        if any(is_emoji(c) for c in text):
            n_emoji += 1

    return len(texts), n_abbrev, n_plain, n_emoji, per_token


def main():
    for name in ("train.jsonl", "val.jsonl", "test.jsonl"):
        path = SPLIT_DIR / name
        if not path.exists():
            print(f"{name}: not found at {path}")
            continue
        total, abbrev, plain, emoji, per_token = count(path)
        print(f"\n=== {name}: {total} records ===")
        print(f"  chat abbreviations : {abbrev:5d}  {100 * abbrev / total:5.2f}%")
        print(f"  no diacritics      : {plain:5d}  {100 * plain / total:5.2f}%")
        print(f"  contains emoji     : {emoji:5d}  {100 * emoji / total:5.2f}%")
        if name == "train.jsonl":
            print("  messages containing each abbreviation:")
            for token, hits in sorted(per_token.items(), key=lambda kv: -kv[1]):
                print(f"    {token:5s} {hits:5d}  ({ABBREVIATIONS[token]})")


if __name__ == "__main__":
    main()
