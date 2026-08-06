"""Offline tests for provenance-safe public-source acquisition."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest
from pydantic import ValidationError

from src.data_pipeline.schemas import ProvenancedSeedRecord, SeedRecord
from src.data_pipeline.scraper.real_sources import (
    BoundedHttpClient,
    FetchError,
    SourcePolicy,
    canonicalize_url,
    collect_paginated_links,
    collect_source,
    deduplicate_records,
    redact_victim_pii,
    verify_evidence,
    write_jsonl_atomic,
)


def _content_hash(text: str) -> str:
    normalized = " ".join(text.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _record(
    text: str = "Canh bao tai khoan: truy cap https://fake-bank.example de xac minh ngay.",
    *,
    canonical_url: str = "https://data.example/full.csv?row=MSG-1",
    native_id: str = "MSG-1",
    contributing_urls: list[str] | None = None,
) -> ProvenancedSeedRecord:
    return ProvenancedSeedRecord(
        text=text,
        source_url="https://data.example/full.csv",
        scrape_timestamp="2026-08-06T12:00:00Z",
        raw_label_hint=None,
        data_origin="real_public",
        record_unit="dataset_row",
        canonical_url=canonical_url,
        publisher="Example Research Group",
        native_id=native_id,
        access_method="download",
        collection_status="allowed",
        redistribution_status="allowed",
        rights_url="https://data.example/license",
        retrieved_at="2026-08-06T12:00:00Z",
        content_sha256=_content_hash(text),
        redaction_state="verified_source_anonymized",
        contributing_urls=contributing_urls or [canonical_url],
        duplicate_count=0,
        provenance_confidence="medium",
    )


def _policy(**updates: object) -> SourcePolicy:
    values: dict[str, object] = {
        "source_id": "hf-vietnamese-sms-phishing",
        "publisher": "Example Research Group",
        "canonical_url": "https://huggingface.co/datasets/example/vietnamese-sms",
        "download_url": "https://huggingface.co/datasets/example/vietnamese-sms/resolve/abc/full.csv",
        "rights_url": "https://creativecommons.org/licenses/by/4.0/",
        "allowed_hosts": ("huggingface.co",),
        "record_unit": "dataset_row",
        "access_method": "download",
        "collection_status": "allowed",
        "redistribution_status": "allowed",
        "adapter": "huggingface_csv",
        "text_field": "message",
        "native_id_field": "message_id",
        "include_field": "label",
        "include_values": ("1",),
        "provenance_confidence": "medium",
    }
    values.update(updates)
    return SourcePolicy(**values)


def test_legacy_seed_record_remains_four_field_compatible() -> None:
    payload = {
        "text": "Tin nhan hop le co du do dai de kiem thu.",
        "source_url": "https://example.test/advisory",
        "scrape_timestamp": "2026-04-24T02:19:25Z",
        "raw_label_hint": None,
    }

    record = SeedRecord.model_validate(payload)

    assert record.model_dump() == payload


def test_provenanced_record_requires_real_origin_null_hint_and_matching_hash() -> None:
    record = _record()

    assert record.data_origin == "real_public"
    assert record.record_unit == "dataset_row"
    assert record.raw_label_hint is None
    assert len(record.content_sha256) == 64

    bad_hint = record.model_dump()
    bad_hint["raw_label_hint"] = "bank_impersonation"
    with pytest.raises(ValidationError, match="raw_label_hint"):
        ProvenancedSeedRecord.model_validate(bad_hint)

    payload = record.model_dump()
    payload["content_sha256"] = "0" * 64
    with pytest.raises(ValidationError, match="content_sha256"):
        ProvenancedSeedRecord.model_validate(payload)


def test_canonicalize_url_removes_tracking_and_fragment_but_keeps_native_row() -> None:
    assert canonicalize_url(
        "HTTPS://Data.Example:443/full.csv?utm_source=x&row=MSG-2&fbclid=y#fragment"
    ) == "https://data.example/full.csv?row=MSG-2"


def test_redaction_removes_victim_pii_but_preserves_inert_malicious_url() -> None:
    text = (
        "Ho ten: Nguyen Van A; so dien thoai 0912 345 678; email victim@example.com; "
        "tai khoan 1234567890123; link https://fake-bank.example/login"
    )

    redacted, state = redact_victim_pii(text)

    assert state == "redacted"
    assert "Nguyen Van A" not in redacted
    assert "0912 345 678" not in redacted
    assert "victim@example.com" not in redacted
    assert "1234567890123" not in redacted
    assert "https://fake-bank.example/login" in redacted


def test_deduplication_collapses_exact_near_and_canonical_url_provenance() -> None:
    first = _record()
    exact = _record(
        text="  CANH BAO TAI KHOAN: truy cap https://fake-bank.example de xac minh ngay. ",
        canonical_url="https://data.example/full.csv?row=MSG-2",
        native_id="MSG-2",
    )
    near = _record(
        text="Canh bao tai khoan: truy cap https://fake-bank.example de xac minh ngay!",
        canonical_url="https://data.example/full.csv?row=MSG-3",
        native_id="MSG-3",
    )
    same_url = _record(
        text="Noi dung khac nhung cung mot dong nguon cong khai.",
        canonical_url=first.canonical_url,
        native_id="MSG-1-copy",
    )

    result = deduplicate_records([first, exact, near, same_url], [], threshold=95.0)

    assert len(result.records) == 1
    assert result.duplicates_within == 3
    assert result.duplicates_existing == 0
    kept = result.records[0]
    assert kept.duplicate_count == 3
    assert set(kept.contributing_urls) == {
        first.canonical_url,
        exact.canonical_url,
        near.canonical_url,
    }


def test_deduplication_removes_existing_normalized_text_and_url() -> None:
    record = _record()
    existing = [
        SeedRecord(
            text=record.text.upper(),
            source_url="https://data.example/full.csv?utm_source=old&row=MSG-9",
            scrape_timestamp="2026-04-24T02:19:25Z",
        )
    ]

    result = deduplicate_records([record], existing, threshold=95.0)

    assert result.records == []
    assert result.duplicates_existing == 1


class _Response:
    def __init__(
        self,
        url: str,
        body: bytes,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.content = body
        self.headers = headers or {"content-type": "text/html"}


class _Session:
    def __init__(self, responses: dict[str, _Response]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, float, bool]] = []

    def get(self, url: str, *, timeout: float, allow_redirects: bool) -> _Response:
        self.calls.append((url, timeout, allow_redirects))
        response = self.responses[url]
        response.url = response.url or url
        return response


def test_bounded_http_client_enforces_host_status_and_response_size() -> None:
    ok_url = "https://allowed.example/page"
    client = BoundedHttpClient(
        allowed_hosts=("allowed.example",),
        session=_Session({ok_url: _Response(ok_url, b"ok")}),
        timeout_seconds=7,
        max_response_bytes=4,
        delay_min=0,
        delay_max=0,
    )

    assert client.fetch(ok_url) == b"ok"
    with pytest.raises(FetchError, match="allowlisted"):
        client.fetch("https://evil.example/ssrf")

    large = BoundedHttpClient(
        allowed_hosts=("allowed.example",),
        session=_Session({ok_url: _Response(ok_url, b"12345")}),
        max_response_bytes=4,
        delay_min=0,
        delay_max=0,
    )
    with pytest.raises(FetchError, match="response-size"):
        large.fetch(ok_url)


def test_bounded_http_client_rejects_cross_host_redirect() -> None:
    requested = "https://allowed.example/page"
    session = _Session(
        {requested: _Response("https://evil.example/landing", b"redirected")}
    )
    client = BoundedHttpClient(
        allowed_hosts=("allowed.example",),
        session=session,
        delay_min=0,
        delay_max=0,
    )

    with pytest.raises(FetchError, match="redirect"):
        client.fetch(requested)


def test_paginated_collection_stops_on_repeated_page_and_keeps_same_host() -> None:
    pages = {
        1: ["https://allowed.example/item/1", "https://evil.example/item/2"],
        2: ["https://allowed.example/item/3"],
        3: ["https://allowed.example/item/3"],
        4: ["https://allowed.example/item/4"],
    }

    result = collect_paginated_links(
        page_loader=lambda page: pages[page],
        allowed_hosts=("allowed.example",),
        max_pages=10,
        max_records=10,
    )

    assert result.links == [
        "https://allowed.example/item/1",
        "https://allowed.example/item/3",
    ]
    assert result.pages_inspected == 3
    assert result.stop_reason == "repeated_page"


def test_paginated_collection_stops_on_empty_page_and_record_cap() -> None:
    empty = collect_paginated_links(
        page_loader=lambda page: [] if page == 2 else ["https://allowed.example/1"],
        allowed_hosts=("allowed.example",),
        max_pages=5,
        max_records=5,
    )
    assert empty.stop_reason == "empty_page"
    assert empty.pages_inspected == 2

    capped = collect_paginated_links(
        page_loader=lambda page: [f"https://allowed.example/{page}/a", f"https://allowed.example/{page}/b"],
        allowed_hosts=("allowed.example",),
        max_pages=5,
        max_records=3,
    )
    assert len(capped.links) == 3
    assert capped.stop_reason == "record_cap"


def test_huggingface_csv_adapter_filters_rows_caps_and_redacts() -> None:
    csv_body = (
        "message_id,message,label\n"
        'HAM-1,"Lich hop noi bo luc 9 gio sang mai",0\n'
        'SPAM-1,"Ho ten: Nguyen Van A, goi 0912345678 va vao https://fake.example",1\n'
        'SPAM-2,"Chuyen 1234567890123 dong de nhan thuong ngay hom nay",1\n'
    ).encode()
    policy = _policy()
    client = BoundedHttpClient(
        allowed_hosts=policy.allowed_hosts,
        session=_Session({policy.download_url: _Response(policy.download_url, csv_body)}),
        delay_min=0,
        delay_max=0,
    )

    records, stats = collect_source(
        policy,
        client=client,
        max_records=1,
        retrieved_at="2026-08-06T12:00:00Z",
    )

    assert len(records) == 1
    assert records[0].native_id == "SPAM-1"
    assert records[0].raw_label_hint is None
    assert records[0].redaction_state == "redacted"
    assert "0912345678" not in records[0].text
    assert records[0].canonical_url.endswith("?row=SPAM-1")
    assert stats.raw_items == 3
    assert stats.extracted_candidate_rows == 2
    assert stats.stop_reason == "record_cap"


def test_mendeley_zip_adapter_reads_only_pinned_member_and_indicator_rows() -> None:
    csv_body = (
        "id,url,label,tier\n"
        "VN-1,https://phish.example/login,phishing,gold\n"
        "VN-2,https://safe.example/,benign,gold\n"
    ).encode()
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("data/dataset_url.csv", csv_body)
        archive.writestr("data/splits/url_train.csv", csv_body)
    archive_bytes = archive_buffer.getvalue()
    policy = _policy(
        source_id="phishvn-v2-open",
        canonical_url="https://data.mendeley.com/datasets/b97hxbxtpd/2",
        download_url="https://data.mendeley.com/public-files/datasets/b97hxbxtpd/file_downloaded",
        allowed_hosts=("data.mendeley.com",),
        adapter="mendeley_zip_csv",
        archive_member="data/dataset_url.csv",
        text_field="url",
        native_id_field="id",
        include_field="label",
        include_values=("phishing",),
        record_unit="threat_indicator",
        expected_download_bytes=len(archive_bytes),
        expected_download_sha256=hashlib.sha256(archive_bytes).hexdigest(),
    )
    client = BoundedHttpClient(
        allowed_hosts=policy.allowed_hosts,
        session=_Session({policy.download_url: _Response(policy.download_url, archive_bytes)}),
        delay_min=0,
        delay_max=0,
    )

    records, stats = collect_source(policy, client=client, max_records=50)

    assert len(records) == 1
    assert records[0].record_unit == "threat_indicator"
    assert records[0].text == "https://phish.example/login"
    assert records[0].native_id == "VN-1"
    assert stats.raw_items == 2
    assert stats.extracted_candidate_rows == 1


@pytest.mark.parametrize("field,value", [
    ("collection_status", "forbidden"),
    ("collection_status", "unknown"),
    ("redistribution_status", "forbidden"),
    ("redistribution_status", "unknown"),
])
def test_rights_gate_prevents_durable_collection(field: str, value: str) -> None:
    policy = _policy(**{field: value})
    client = BoundedHttpClient(
        allowed_hosts=policy.allowed_hosts,
        session=_Session({}),
        delay_min=0,
        delay_max=0,
    )

    with pytest.raises(PermissionError, match=field):
        collect_source(policy, client=client, max_records=10)


def test_atomic_writer_refuses_overwrite_without_replace(tmp_path: Path) -> None:
    output = tmp_path / "sample.jsonl"
    write_jsonl_atomic(output, [_record()], replace=False)

    with pytest.raises(FileExistsError):
        write_jsonl_atomic(output, [_record(native_id="MSG-2")], replace=False)

    write_jsonl_atomic(output, [_record(native_id="MSG-2")], replace=True)
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["native_id"] == "MSG-2"


def test_offline_verifier_checks_hash_counts_protected_lineage_and_duplicates(
    tmp_path: Path,
) -> None:
    existing_path = tmp_path / "existing.jsonl"
    existing_path.write_text(
        SeedRecord(
            text="Noi dung cu hoan toan khac de kiem thu doi chieu.",
            source_url="https://old.example/1",
            scrape_timestamp="2026-04-24T02:19:25Z",
        ).model_dump_json()
        + "\n",
        encoding="utf-8",
    )
    sample_path = tmp_path / "sample.jsonl"
    write_jsonl_atomic(sample_path, [_record()], replace=False)
    protected = tmp_path / "protected.jsonl"
    protected.write_text('{"locked":true}\n', encoding="utf-8")
    protected_hash = hashlib.sha256(protected.read_bytes()).hexdigest()
    manifest_path = tmp_path / "manifest.jsonl"
    manifest = {
        "schema_version": "1.0",
        "source_id": "multi-source-audit",
        "record_unit": "mixed_separately_reported",
        "access": "bounded_live_and_download",
        "count_method": "per_source",
        "raw_items": 1,
        "unique_items": 1,
        "duplicates_existing": 0,
        "eligible_new_records": 1,
        "collection_status": "mixed",
        "redistribution_status": "mixed",
        "sources": [],
        "sample": {
            "status": "retained",
            "path": str(sample_path),
            "rows": 1,
            "bytes": sample_path.stat().st_size,
            "sha256": hashlib.sha256(sample_path.read_bytes()).hexdigest(),
        },
        "protected_artifacts": [
            {
                "path": str(protected),
                "before_sha256": protected_hash,
                "after_sha256": protected_hash,
            }
        ],
    }
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")

    result = verify_evidence(manifest_path, sample_path, existing_path)

    assert result["valid"] is True
    assert result["sample_rows"] == 1

    protected.write_text('{"locked":false}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="protected artifact"):
        verify_evidence(manifest_path, sample_path, existing_path)
