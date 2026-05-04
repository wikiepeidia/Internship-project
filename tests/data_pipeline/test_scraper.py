import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.data_pipeline.scraper.ncsc_scraper import NCSCScraper
from src.data_pipeline.scraper.extractors import extract_advisory_links, extract_phishing_payloads
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


def test_extract_phishing_payloads_from_plain_paragraphs():
    html = """
    <html><body>
        <article class="post-content">
            <p>Moi chao viec nhe luong cao, yeu cau dat coc 500.000 dong de kich hoat tai khoan cong tac vien.</p>
            <p>Xem san pham gia uu dai tai cua hang doi tac.</p>
        </article>
    </body></html>
    """

    payloads = extract_phishing_payloads(html)

    assert payloads == [
        "Moi chao viec nhe luong cao, yeu cau dat coc 500.000 dong de kich hoat tai khoan cong tac vien."
    ]


def test_extract_phishing_payloads_excludes_official_warning_cta_copy():
    html = """
    <html><body>
        <div id="post" class="mt-4">
            <div class="container">
                <div class="row g-5">
                    <div class="col-md-9">
                        <p>Doi tuong lua dao chu dong lien he, yeu cau cai dat phan mem gia mao qua duong link de chiem doat tien.</p>
                        <p>Theo doi va cap nhat cac thong tin, dau hieu ve lua dao truc tuyen tai Cong khong gian mang quoc gia.</p>
                        <p>Khi phat hien cac truong hop co dau hieu lua dao nhu tren, nguoi dan can bao ngay cho co quan Cong an noi gan nhat.</p>
                        <p>Bao cao cho biet co den hon 601.000 bao cao ve cac vu lua dao trong nam 2023.</p>
                        <p>Hinh anh cac giao dich chuyen khoan cho ke lua dao.</p>
                    </div>
                </div>
            </div>
        </div>
    </body></html>
    """

    payloads = extract_phishing_payloads(html)

    assert payloads == [
        "Doi tuong lua dao chu dong lien he, yeu cau cai dat phan mem gia mao qua duong link de chiem doat tien."
    ]


def test_extract_advisory_links_from_live_style_listing_paths():
    html = """
    <html><body>
        <section id="category-publish">
            <div class="post-vertical">
                <a href="/canh-bao-mao-danh-ngan-hang-huong-dan-nguoi-dung-xac-thuc-sinh-trac-hoc">
                    CANH BAO MAO DANH NGAN HANG, HUONG DAN NGUOI DUNG XAC THUC SINH TRAC HOC
                </a>
            </div>
            <div class="post-vertical"><a href="/canh-bao-lua-dao?page=2">2</a></div>
            <div class="post-vertical"><a href="/danh-cho-to-chuc">Tin nhiem mang danh cho to chuc</a></div>
            <div class="post-vertical"><a href="/posts/info">Thong tin huu ich</a></div>
        </section>
    </body></html>
    """

    links = extract_advisory_links(html, "https://tinnhiemmang.vn/canh-bao-lua-dao")

    assert links == [
        "https://tinnhiemmang.vn/canh-bao-mao-danh-ngan-hang-huong-dan-nguoi-dung-xac-thuc-sinh-trac-hoc"
    ]
