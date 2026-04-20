import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.data_pipeline.scraper.ncsc_scraper import NCSCScraper
from src.data_pipeline.schemas import SeedRecord

@pytest.fixture
def mock_listing_html():
    return """
    <html><body>
        <h2 class="post-title"><a href="/advisory/1">Advisory 1</a></h2>
        <h2 class="post-title"><a href="/advisory/2">Advisory 2</a></h2>
    </body></html>
    """

@pytest.fixture
def mock_detail_html():
    return """
    <html><body>
        <article class="post-content">
            <p>Example phishing: "Tai khoan cua ban bi khoa, truy cap link de mo khoa: http://vpbank-fake.vn"</p>
        </article>
    </body></html>
    """

@patch("src.data_pipeline.scraper.ncsc_scraper.requests.Session.get")
@patch("src.data_pipeline.scraper.ncsc_scraper.polite_delay")
def test_fetch_page(mock_delay, mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body><article>Test</article></body></html>"
    mock_get.return_value = mock_resp
    
    scraper = NCSCScraper(base_urls=["https://test.com"])
    soup = scraper.fetch_page("https://test.com")
    
    assert soup is not None
    assert "Test" in soup.text
    mock_delay.assert_called_once()
    mock_get.assert_called_once_with("https://test.com", timeout=30)
    assert scraper.session.headers["User-Agent"] == "Mozilla/5.0 (research-project; vn-phishing-detection)"

@patch("src.data_pipeline.scraper.ncsc_scraper.requests.Session.get")
@patch("src.data_pipeline.scraper.ncsc_scraper.polite_delay")
def test_scrape_advisory_list(mock_delay, mock_get, mock_listing_html, mock_detail_html):
    def side_effect(url, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        if "advisory/" in url:
            mock_resp.text = mock_detail_html
        else:
            mock_resp.text = mock_listing_html
        return mock_resp
        
    mock_get.side_effect = side_effect
    
    scraper = NCSCScraper(base_urls=["https://test.com"])
    seeds = scraper.scrape_advisory_list(max_pages=1)
    
    assert len(seeds) > 0
    for seed in seeds:
        assert isinstance(seed, SeedRecord)
        assert "Tai khoan cua ban bi khoa" in seed.text
        assert seed.source_url.startswith("https://test.com/advisory/")

def test_save_seeds(tmp_path):
    scraper = NCSCScraper()
    seeds = [
        SeedRecord(
            text="Tai khoan cua ban bi khoa, truy cap link de mo khoa: http://vpbank-fake.vn",
            source_url="https://test.com/1",
            scrape_timestamp="2026-04-10T12:00:00Z"
        )
    ]
    output_path = tmp_path / "seeds.jsonl"
    saved_path = scraper.save_seeds(seeds, output_path=output_path)
    
    assert saved_path.exists()
    content = saved_path.read_text()
    assert "Tai khoan cua ban" in content
    assert "http://vpbank-fake.vn" in content
