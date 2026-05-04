import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Optional

from src.data_pipeline.schemas import SeedRecord
from src.data_pipeline.scraper.rate_limiter import polite_delay
from src.data_pipeline.scraper.extractors import extract_advisory_links, extract_phishing_payloads
from src.data_pipeline.processing.normalizer import normalize_text
from src.config.settings import get_settings

class NCSCScraper:
    def __init__(self, base_urls: list[str] | None = None, use_playwright: bool = False):
        settings = get_settings()
        self.base_urls = base_urls or [
            settings.ncsc_base_url,
            "https://chongluadao.vn/posts",
            "https://tinnhiemmang.vn/canh-bao-lua-dao",
            "https://scam.vn/bai-viet",
        ]
        self.use_playwright = use_playwright
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (research-project; vn-phishing-detection)"
        })
        self.settings = settings

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        polite_delay(self.settings.scrape_delay_min, self.settings.scrape_delay_max)
        if not self.use_playwright:
            try:
                resp = self.session.get(url, timeout=30)
                resp.encoding = "utf-8"
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    if self._has_content(soup):
                        return soup
            except Exception:
                pass # fallback to playwright if error or no content
        return self._fetch_with_playwright(url)

    def _has_content(self, soup: BeautifulSoup) -> bool:
        content_selectors = ["article", ".post-content", ".entry-content", ".article-body", ".content-detail", "body"]
        for selector in content_selectors:
            if soup.select(selector):
                return True
        return False

    def _fetch_with_playwright(self, url: str) -> Optional[BeautifulSoup]:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                html = page.content()
                browser.close()
            return BeautifulSoup(html, "html.parser")
        except Exception:
            return None

    def scrape_advisory_list(
        self,
        max_pages: int = 1,
        max_links_per_page: int = 5,
        max_seeds: int | None = None,
    ) -> list[SeedRecord]:
        seeds: list[SeedRecord] = []
        seen_payloads: set[str] = set()
        timestamp = datetime.now(timezone.utc).isoformat()

        for base_url in self.base_urls:
            for page_num in range(1, max_pages + 1):
                # Basic pagination pattern
                page_url = f"{base_url}?page={page_num}" if page_num > 1 else base_url
                soup = self.fetch_page(page_url)
                if soup is None:
                    break

                links = extract_advisory_links(str(soup), page_url)
                if not links:
                    break

                for link in links[:max_links_per_page]:
                    detail_soup = self.fetch_page(link)
                    if detail_soup is None:
                        continue
                    payloads = extract_phishing_payloads(str(detail_soup))
                    for payload in payloads:
                        normalized = normalize_text(payload)
                        if len(normalized) >= 10 and normalized not in seen_payloads:
                            seen_payloads.add(normalized)
                            seed = SeedRecord(
                                text=normalized,
                                source_url=link,
                                scrape_timestamp=timestamp,
                                raw_label_hint=None
                            )
                            seeds.append(seed)
                            if max_seeds is not None and len(seeds) >= max_seeds:
                                return seeds
        return seeds

    def save_seeds(self, seeds: list[SeedRecord], output_path: Path | None = None) -> Path:
        path = output_path or (self.settings.data_dir / "raw" / "seeds.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for seed in seeds:
                f.write(seed.model_dump_json() + "\n")
        return path
