import urllib.parse
from bs4 import BeautifulSoup

def extract_advisory_links(html: str, base_url: str) -> list[str]:
    """Extracts advisory listing links from HTML and resolves them to absolute URLs."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    
    # Selectors based on common listing patterns
    selectors = [".post-title a", "h2 a", "h3 a", ".entry-title a", ".advisory-list a"]
    
    for selector in selectors:
        for a_tag in soup.select(selector):
            href = a_tag.get("href")
            if href:
                absolute_url = urllib.parse.urljoin(base_url, href)
                if absolute_url not in links:
                    links.append(absolute_url)
                    
    return links

def extract_phishing_payloads(html: str) -> list[str]:
    """Extracts quoted phishing payloads from advisory detail page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    payloads = []
    
    content_areas = soup.select("article, .post-content, .entry-content, .article-body, .content-detail")
    if not content_areas:
        content_areas = [soup] # fallback
        
    for area in content_areas:
        # Extract from quotes (both Vietnamese and standard) or backticks
        # We can also get text inside blockquote, code, pre tags
        text_nodes = area.find_all(text=True)
        full_text = "".join(text_nodes)
        
        import re
        # Match quoted texts: “...” or "..."
        quotes = re.findall(r'[“"”](.*?)[“"”]', full_text)
        
        for q in quotes:
            q = q.strip()
            if len(q) >= 20 and q not in payloads:
                payloads.append(q)
                
        # Also extract from specific tags
        for tag in area.find_all(['blockquote', 'code', 'pre']):
            tag_text = tag.get_text(strip=True)
            if len(tag_text) >= 20 and tag_text not in payloads:
                # remove surrounding quotes if any
                tag_text = re.sub(r'^[“"”]|[“"”]$', '', tag_text).strip()
                if len(tag_text) >= 20:
                    payloads.append(tag_text)
                
    return payloads
