import re
import urllib.parse

from bs4 import BeautifulSoup


LISTING_LINK_SELECTORS = (
    ".post-title a",
    "h2 a",
    "h3 a",
    ".entry-title a",
    ".advisory-list a",
    ".post-vertical a",
    "#category-publish a",
    'a[href*="/canh-bao/"]',
    'a[href*="/bai-viet/"]',
    'a[href*="/posts/"]',
)

LISTING_PATH_MARKERS = (
    "/advisory/",
    "/canh-bao/",
    "/bai-viet/",
    "/posts/",
)

LISTING_PATH_DENY_MARKERS = (
    "/cdn-cgi/",
    "/danh-cho-",
    "/download",
    "/gioi-thieu",
    "/he-thong-tin-nhiem",
    "/lien-he",
    "/partners",
    "/posts/donate",
    "/posts/info",
    "/report",
    "/resources",
    "/to-chuc-tin-nhiem",
    "/ung-dung-tin-nhiem",
    "/vinh-danh",
    "/website-lua-dao",
    "/website-tin-nhiem",
)


NOISE_MARKERS = (
    "xem sản phẩm",
    "xem chi tiết",
    "đăng bình luận",
    "các bình luận",
    "privacy",
    "terms",
    "disclaimer",
    "donate",
    "google dịch",
    "đăng nhập",
    "trang chủ",
    "tìm kiếm",
    "chia sẻ",
    "bản quyền",
    "tín nhiệm mạng",
    "chứng nhận",
    "hãy chia sẻ câu chuyện của bạn",
    "theo dõi và cập nhật các thông tin",
    "hãy gửi phản ánh",
    "cục an toàn thông tin",
    "bộ tt&tt",
    "báo ngay cho cơ quan công an",
    "khi phát hiện các trường hợp có dấu hiệu lừa đảo",
    "báo cáo cho biết",
    "hình ảnh các giao dịch",
)

SUSPICIOUS_MARKERS = (
    "lừa đảo",
    "mạo danh",
    "giả danh",
    "tài khoản",
    "tai khoan",
    "xác minh",
    "xac minh",
    "chuyển tiền",
    "chuyen tien",
    "đặt cọc",
    "dat coc",
    "việc nhẹ lương cao",
    "viec nhe luong cao",
    "nhiệm vụ",
    "nhiem vu",
    "tuyển dụng",
    "tuyen dung",
    "otp",
    "link",
    "telegram",
    "zalo",
)


CONTENT_AREA_SELECTORS = (
    "article",
    ".post-content",
    ".entry-content",
    ".article-body",
    ".content-detail",
    "#post .col-md-9",
)

def extract_advisory_links(html: str, base_url: str) -> list[str]:
    """Extracts advisory listing links from HTML and resolves them to absolute URLs."""
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for selector in LISTING_LINK_SELECTORS:
        for a_tag in soup.select(selector):
            href = a_tag.get("href")
            if not href:
                continue
            absolute_url = urllib.parse.urljoin(base_url, href)
            anchor_text = a_tag.get_text(" ", strip=True)
            if _looks_like_advisory_link(absolute_url, anchor_text, base_url) and absolute_url not in links:
                links.append(absolute_url)
                    
    return links


def _normalize_candidate(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^[\-\*\u2022\d\.\)\s]+", "", text)
    return text.strip()


def _looks_like_advisory_link(url: str, anchor_text: str, base_url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False

    base_host = urllib.parse.urlparse(base_url).netloc
    if parsed.netloc and base_host and parsed.netloc != base_host:
        return False

    path = parsed.path.casefold()
    if not path or path == "/":
        return False
    if any(marker in path for marker in LISTING_PATH_DENY_MARKERS):
        return False
    if parsed.query.startswith("page="):
        return False
    if any(marker in path for marker in LISTING_PATH_MARKERS):
        return True

    normalized_text = _normalize_candidate(anchor_text)
    return len(normalized_text) >= 30 and len(path.strip("/")) >= 20


def _is_bare_url(text: str) -> bool:
    return bool(re.fullmatch(r"(?:https?://|www\.)\S+", text))


def _looks_like_payload(text: str) -> bool:
    normalized = text.casefold()
    if len(text) < 20 or len(text) > 600:
        return False
    if _is_bare_url(normalized):
        return False
    if any(marker in normalized for marker in NOISE_MARKERS):
        return False
    word_count = len(text.split())
    if word_count < 4:
        return False
    if re.search(r"https?://|www\.|\.vn\b|\.com\b", normalized):
        return word_count >= 4
    return any(marker in normalized for marker in SUSPICIOUS_MARKERS)

def extract_phishing_payloads(html: str) -> list[str]:
    """Extracts quoted phishing payloads from advisory detail page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    payloads = []

    content_areas = soup.select(", ".join(CONTENT_AREA_SELECTORS))
    if not content_areas:
        content_areas = [soup] # fallback
        
    for area in content_areas:
        text_nodes = area.find_all(string=True)
        full_text = " ".join(text_nodes)

        quotes = re.findall(r'[“"”](.*?)[“"”]', full_text)
        for quoted_text in quotes:
            candidate = _normalize_candidate(quoted_text)
            if _looks_like_payload(candidate) and candidate not in payloads:
                payloads.append(candidate)

        for tag in area.find_all(["blockquote", "code", "pre", "p", "li"]):
            candidate = _normalize_candidate(tag.get_text(" ", strip=True))
            if _looks_like_payload(candidate) and candidate not in payloads:
                payloads.append(candidate)
                
    return payloads
