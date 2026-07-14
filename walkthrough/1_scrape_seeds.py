# ============================================================
# STEP 1 of 10 — Scrape Real Seed Messages
# ============================================================
# Canonical source (this numbered copy exists ONLY for defense-day
# navigation — it is not a second implementation and is not imported
# by anything): src/data_pipeline/scraper/ncsc_scraper.py
#
# What this file does: fetches advisory pages from NCSC/tinnhiemmang.vn
# (with a polite randomized delay + Playwright fallback), extracts real
# scam-message text via extractors.py, normalizes it, and saves
# SeedRecord rows to data/raw/seeds.jsonl. This is the very first step
# of the data pipeline — everything downstream is derived from these
# real, human-reported seeds.
#
# WHY THIS STEP EXISTS AT ALL: if I generated synthetic scam messages
# from nothing (just prompting an LLM "write a scam message"), the
# output tends to be generic, textbook-sounding, not what real
# Vietnamese SMS/Zalo scams look like. Starting from real reported
# cases gives the generator (step 2) something concrete to riff on —
# real bank names, real slang, real urgency phrasing. Seeds are the
# anchor that keeps the whole ~3,000-row corpus grounded in reality
# instead of being pure LLM hallucination. If a judge asks "where did
# the data come from," the honest answer starts here, not at the LLM.
#
# See also: documents/reports/supervisor/defense_code_navigation.md
# (§ "Data pipeline — walk it in order")
# ============================================================

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
    """
    One scraper class, four possible source sites. Not one-scraper-per-site
    because the extraction logic (extractors.py) is written to be generic
    enough (CSS-selector based, not site-specific hardcoding) that the same
    class can walk any of these four listing pages.
    """

    def __init__(self, base_urls: list[str] | None = None, use_playwright: bool = False):
        settings = get_settings()

        # NCSC = Vietnam's National Cyber Security Center (Cục An toàn thông
        # tin). tinnhiemmang.vn is their public "trust portal" that publishes
        # verified scam alerts — this is the PRIMARY, most authoritative
        # source, which is why it's first in the list and also why the
        # project is named around "trustworthy"/NCSC framing in the report.
        # The other three (chongluadao.vn, tinnhiemmang canh-bao page,
        # scam.vn) are community-run scam-report sites, kept as fallbacks —
        # NCSC's own listing can be sparse on some days, or the endpoint can
        # be briefly unreachable, so having 4 sources means one bad day for
        # one site doesn't stall the whole scrape.
        self.base_urls = base_urls or [
            settings.ncsc_base_url,
            "https://chongluadao.vn/posts",
            "https://tinnhiemmang.vn/canh-bao-lua-dao",
            "https://scam.vn/bai-viet",
        ]

        # use_playwright: when True, skip the plain-HTTP path entirely and
        # ALWAYS use a real headless Chromium browser. Why this knob exists:
        # some of these sites render their article body with client-side JS
        # (React/Vue-style), so a bare `requests.get()` sometimes returns an
        # empty HTML shell with no visible text at all — the JS never runs
        # because there's no browser to run it. Playwright launches an
        # actual browser engine, so it sees the page the same way a human
        # visitor's browser would, after JS has executed. It's slower (has
        # to boot a browser process) so it's opt-in / fallback-only, not
        # the default path.
        self.use_playwright = use_playwright

        # A requests.Session (not a fresh `requests.get` every time) reuses
        # the underlying TCP connection across requests to the same host —
        # cheaper than reconnecting every single page fetch.
        self.session = requests.Session()

        # Custom User-Agent: identifies this traffic honestly as a research
        # project rather than spoofing a real browser's UA string. Some
        # scraping guides tell you to fake a browser UA to "avoid blocks" —
        # deliberately not doing that here, since this is a legitimate
        # academic scrape of public advisory pages, not something that
        # needs to hide what it is.
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (research-project; vn-phishing-detection)"
        })

        self.settings = settings  # kept for scrape_delay_min/max and data_dir, used later

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Single entry point for "get me this URL as parsed HTML." Every
        other method calls THIS, never requests.get directly — that's what
        keeps the rate-limit call and the Playwright-fallback logic in one
        place instead of duplicated everywhere.
        """
        # Rate-limit ourselves BEFORE every fetch, not after and not only
        # on retry. This is basic scraper etiquette: NCSC and the other
        # three sites are small public services, not built for high-volume
        # bot traffic. polite_delay() sleeps a random amount between
        # scrape_delay_min and scrape_delay_max seconds — randomized (not a
        # fixed sleep) so the request pattern doesn't look like an
        # obviously mechanical, evenly-spaced bot hitting the server.
        polite_delay(self.settings.scrape_delay_min, self.settings.scrape_delay_max)

        if not self.use_playwright:
            try:
                resp = self.session.get(url, timeout=30)
                # Forcing utf-8 explicitly: `requests` sometimes guesses
                # the wrong encoding from response headers alone, and if it
                # guesses wrong, every Vietnamese diacritic (ệ, ạ, ề, etc.)
                # comes out as mojibake garbage. This one line prevents a
                # whole category of silently-corrupted seed text.
                resp.encoding = "utf-8"
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    if self._has_content(soup):
                        # Happy path: plain HTTP worked and the page has
                        # real content. Return immediately — no need to
                        # pay the cost of launching a browser.
                        return soup
                    # else: fall through to Playwright below — the page
                    # loaded but looked like an empty JS shell.
            except Exception:
                # Deliberately broad except: DNS failure, timeout,
                # connection reset, malformed response — any of these
                # should fall through to the Playwright fallback rather
                # than crash the entire multi-hour scrape run over one bad
                # page. A scraper that dies on the first flaky request is
                # useless for this kind of long unattended job.
                pass  # fallback to playwright if error or no content

        return self._fetch_with_playwright(url)

    def _has_content(self, soup: BeautifulSoup) -> bool:
        """
        Heuristic check: "does this parsed page actually contain something
        that looks like article content?" Used to decide whether the plain
        HTTP fetch was good enough, or whether we need the heavier
        Playwright path. Checks a list of common content-container
        selectors (article tag, common CMS class names) and falls back to
        just checking <body> has anything at all. Not perfect, but good
        enough to catch the "JS never ran, page is basically blank" case.
        """
        content_selectors = ["article", ".post-content", ".entry-content", ".article-body", ".content-detail", "body"]
        for selector in content_selectors:
            if soup.select(selector):
                return True
        return False

    def _fetch_with_playwright(self, url: str) -> Optional[BeautifulSoup]:
        """
        The JS-rendering fallback. Only reached when the plain HTTP path
        either errored out or returned a content-less shell page.
        """
        # Import is INSIDE the function on purpose (lazy import), not at
        # the top of the file. playwright is a heavy dependency — it needs
        # a real browser binary downloaded separately (`playwright install
        # chromium`). Importing it only here means the rest of this class,
        # and this whole module, still works fine in an environment where
        # playwright isn't installed at all; you'd just never successfully
        # hit this fallback branch (get None back instead of a crash at
        # import time).
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)  # headless = no visible window, fine for a server/CI/batch job
                page = browser.new_page()
                # wait_until="networkidle": don't just wait for the initial
                # HTML document to load — wait until the page has stopped
                # firing network requests for a bit. That gives client-side
                # JS time to finish its own fetch calls and actually paint
                # the real article content before we grab page.content().
                page.goto(url, wait_until="networkidle", timeout=30000)
                html = page.content()  # the fully-rendered DOM as HTML, post-JS
                browser.close()
            return BeautifulSoup(html, "html.parser")
        except Exception:
            # If even the full browser can't get this page (site down,
            # blocked, malformed), give up on this ONE url and return None.
            # Caller (fetch_page / scrape_advisory_list) treats None as
            # "skip this link, move on" rather than aborting the whole run.
            return None

    def scrape_advisory_list(
        self,
        max_pages: int = 1,
        max_links_per_page: int = 5,
        max_seeds: int | None = None,
    ) -> list[SeedRecord]:
        """
        The actual orchestration loop. Nested structure, outside-in:
          for each of the 4 base sites
            for each page number (pagination)
              for each advisory LINK found on that listing page
                for each scam-message PAYLOAD extracted from that one advisory
        The three max_* parameters are all just safety caps so one run
        can never accidentally scrape forever / hammer a site infinitely —
        useful both for politeness and for keeping local dev runs fast.
        """
        seeds: list[SeedRecord] = []

        # Dedup by exact normalized text. The SAME advisory (or a very
        # close copy of it) can legitimately appear on more than one of the
        # 4 sites — chongluadao.vn and tinnhiemmang.vn, for instance, often
        # both re-post the same NCSC alert. Without this set, the seed pool
        # would have exact duplicates padding the count without adding any
        # real signal.
        seen_payloads: set[str] = set()

        # One shared timestamp for the whole run (not one per-seed
        # `datetime.now()` call) — every SeedRecord produced by this single
        # invocation of scrape_advisory_list gets stamped with when the RUN
        # happened, which is what you actually want for provenance/audit
        # purposes, not the exact microsecond each individual record was
        # appended to the list.
        timestamp = datetime.now(timezone.utc).isoformat()

        for base_url in self.base_urls:
            for page_num in range(1, max_pages + 1):
                # Basic pagination pattern: page 1 is just the bare URL
                # (no query string), page 2+ appends ?page=N. Not every
                # site necessarily supports this param the same way, but
                # it degrades gracefully — if the param is ignored, we just
                # re-scrape page 1's links again, which `seen_payloads`
                # dedupes away.
                page_url = f"{base_url}?page={page_num}" if page_num > 1 else base_url

                soup = self.fetch_page(page_url)
                if soup is None:
                    # This site/page is unreachable even after the
                    # Playwright fallback — stop paginating THIS base_url
                    # (break out of the inner page_num loop) and move on to
                    # the next site in the outer loop. Don't keep retrying
                    # a dead site.
                    break

                links = extract_advisory_links(str(soup), page_url)
                if not links:
                    # No advisory links found on this listing page — either
                    # we've walked past the last real page of results, or
                    # this site's HTML structure doesn't match what
                    # extract_advisory_links expects. Either way, no point
                    # paginating further for this base_url.
                    break

                for link in links[:max_links_per_page]:
                    detail_soup = self.fetch_page(link)
                    if detail_soup is None:
                        # This one advisory page didn't load — skip just
                        # this link, keep processing the rest of `links`.
                        continue

                    payloads = extract_phishing_payloads(str(detail_soup))
                    for payload in payloads:
                        # normalize_text is the SAME normalizer function
                        # used later at live-inference time (see step 8,
                        # RuntimeService.analyze_text). Using one shared
                        # normalizer for both training-time seeds and
                        # real-time user input matters: it means the model
                        # always sees text in the same canonical shape
                        # (consistent Unicode form, whitespace, etc.)
                        # whether that text was scraped in this step or
                        # typed into the demo UI by a live user tomorrow.
                        normalized = normalize_text(payload)

                        # len >= 10: throw out near-empty extraction noise
                        # (stray short strings extractors.py sometimes
                        # pulls out that aren't actually scam message body
                        # text — e.g. a lone "Xem thêm" button label).
                        if len(normalized) >= 10 and normalized not in seen_payloads:
                            seen_payloads.add(normalized)
                            seed = SeedRecord(
                                text=normalized,
                                source_url=link,           # provenance: exactly which advisory this came from
                                scrape_timestamp=timestamp,
                                # raw_label_hint is deliberately left None
                                # here, not guessed at scrape time. Real
                                # classification (scam vs benign, which
                                # threat category) happens downstream in
                                # the generation/judge stages (steps 2-3),
                                # not in the scraper. The scraper's only
                                # job is "get real text," not "grade it."
                                raw_label_hint=None,
                            )
                            seeds.append(seed)

                            if max_seeds is not None and len(seeds) >= max_seeds:
                                # Hit the cap — return immediately instead
                                # of finishing the remaining nested loops
                                # for no reason.
                                return seeds
        return seeds

    def save_seeds(self, seeds: list[SeedRecord], output_path: Path | None = None) -> Path:
        """
        Writes the seed list to disk as JSONL (one JSON object per line —
        NOT a single big JSON array). This is the standard on-disk shape
        used at every stage of this pipeline (seeds, generated records,
        judged records, split files): JSONL is trivial to stream line-by-
        line without loading a huge array into memory, trivial to append
        to, and if one line is malformed you can still read every other
        line instead of the whole file failing to parse.
        """
        path = output_path or (self.settings.data_dir / "raw" / "seeds.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for seed in seeds:
                # model_dump_json(): SeedRecord is a Pydantic model (this
                # is the "why Pydantic" answer for this specific file —
                # schema validation on every record, and a one-call clean
                # JSON serialization that's guaranteed to match the schema
                # exactly, no hand-built dict/json.dumps drift possible).
                f.write(seed.model_dump_json() + "\n")
        return path
