"""Bounded, provenance-first collection of audited public real-source seeds.

This module is deliberately separate from generation, labeling, and split
building.  It only audits an evidence manifest, downloads sources whose access
*and* redistribution status are explicitly allowed, and verifies frozen
evidence offline.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import random
import re
import tempfile
import time
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from rapidfuzz import fuzz

from src.data_pipeline.processing.normalizer import normalize_text
from src.data_pipeline.schemas import ProvenancedSeedRecord, SeedRecord


TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
}
REQUIRED_SOURCE_FIELDS = {
    "source_id",
    "source_family",
    "record_unit",
    "access",
    "count_method",
    "raw_items",
    "unique_items",
    "duplicates_existing",
    "eligible_new_records",
    "collection_status",
    "redistribution_status",
}


class FetchError(RuntimeError):
    """A visible, source-specific network or safety failure."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalized_key(text: str) -> str:
    return normalize_text(text).casefold()


def _content_hash(text: str) -> str:
    return hashlib.sha256(_normalized_key(text).encode("utf-8")).hexdigest()


def _allowed_host(host: str | None, allowed_hosts: Sequence[str]) -> bool:
    if not host:
        return False
    normalized = host.casefold().rstrip(".")
    return normalized in {item.casefold().rstrip(".") for item in allowed_hosts}


def canonicalize_url(url: str) -> str:
    """Return a stable HTTP(S) URL without fragments or tracking parameters."""
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"}:
        raise ValueError(f"unsupported URL scheme: {parsed.scheme or '<missing>'}")
    if not parsed.hostname:
        raise ValueError("URL has no hostname")

    host = parsed.hostname.casefold().rstrip(".")
    port = parsed.port
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        host = f"{host}:{port}"
    path = parsed.path or "/"
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in TRACKING_QUERY_KEYS
    ]
    query.sort()
    return urlunsplit((scheme, host, path, urlencode(query), ""))


_PHONE_RE = re.compile(r"(?<!\d)(?:\+?84|0)\d(?:[\s.\-]?\d){8,10}(?!\d)")
_EMAIL_RE = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
_ACCOUNT_RE = re.compile(r"(?<!\d)\d(?:[\s.\-]?\d){11,18}(?!\d)")
_NAME_RE = re.compile(
    r"(?i)\b(?:h[ọo]\s*t[eê]n|t[eê]n\s*(?:n[aạ]n\s*nh[aâ]n)?)\s*:\s*"
    r"[^;,\n]{2,80}"
)


def redact_victim_pii(text: str) -> tuple[str, str]:
    """Redact common victim identifiers while leaving malicious URLs inert."""
    redacted = _NAME_RE.sub("Ho ten: [NAME]", text)
    redacted = _EMAIL_RE.sub("[EMAIL]", redacted)
    redacted = _PHONE_RE.sub("[PHONE]", redacted)
    redacted = _ACCOUNT_RE.sub("[BANK_ACCOUNT]", redacted)
    redacted = normalize_text(redacted)
    return redacted, "redacted" if redacted != normalize_text(text) else "not_needed"


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    source_id: str
    publisher: str
    canonical_url: str
    download_url: str
    rights_url: str
    allowed_hosts: tuple[str, ...]
    record_unit: str
    access_method: str
    collection_status: str
    redistribution_status: str
    adapter: str
    text_field: str
    native_id_field: str | None
    include_field: str | None = None
    include_values: tuple[str, ...] = ()
    provenance_confidence: str = "low"
    archive_member: str | None = None
    expected_download_sha256: str | None = None
    expected_download_bytes: int | None = None

    @classmethod
    def from_mapping(cls, source: Mapping[str, Any]) -> "SourcePolicy":
        return cls(
            source_id=str(source["source_id"]),
            publisher=str(source["publisher"]),
            canonical_url=str(source["canonical_url"]),
            download_url=str(source["download_url"]),
            rights_url=str(source["rights_url"]),
            allowed_hosts=tuple(source.get("allowed_hosts") or (urlsplit(str(source["download_url"])).hostname,)),
            record_unit=str(source["record_unit"]),
            access_method=str(source.get("access_method", "download")),
            collection_status=str(source["collection_status"]),
            redistribution_status=str(source["redistribution_status"]),
            adapter=str(source["adapter"]),
            text_field=str(source["text_field"]),
            native_id_field=(str(source["native_id_field"]) if source.get("native_id_field") else None),
            include_field=(str(source["include_field"]) if source.get("include_field") else None),
            include_values=tuple(str(value) for value in source.get("include_values", ())),
            provenance_confidence=str(source.get("provenance_confidence", "low")),
            archive_member=(str(source["archive_member"]) if source.get("archive_member") else None),
            expected_download_sha256=(
                str(source["expected_download_sha256"])
                if source.get("expected_download_sha256")
                else None
            ),
            expected_download_bytes=(
                int(source["expected_download_bytes"])
                if source.get("expected_download_bytes") is not None
                else None
            ),
        )


@dataclass(slots=True)
class CollectionStats:
    source_id: str
    raw_items: int
    extracted_candidate_rows: int
    retained_before_dedup: int
    skipped_short_or_empty: int
    stop_reason: str


@dataclass(slots=True)
class DedupResult:
    records: list[ProvenancedSeedRecord]
    duplicates_within: int
    duplicates_existing: int


@dataclass(slots=True)
class PaginationResult:
    links: list[str]
    pages_inspected: int
    stop_reason: str


class BoundedHttpClient:
    """Small HTTP client with a fixed host allowlist and hard fetch bounds."""

    def __init__(
        self,
        *,
        allowed_hosts: Sequence[str],
        session: Any | None = None,
        timeout_seconds: float = 30.0,
        max_response_bytes: int = 64 * 1024 * 1024,
        delay_min: float = 2.0,
        delay_max: float = 5.0,
    ) -> None:
        if delay_min < 0 or delay_max < delay_min:
            raise ValueError("invalid polite-delay range")
        self.allowed_hosts = tuple(allowed_hosts)
        self.session = session or requests.Session()
        if hasattr(self.session, "headers"):
            self.session.headers.update(
                {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/139.0.0.0 Safari/537.36"
                    ),
                    "Accept": "*/*",
                }
            )
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes
        self.delay_min = delay_min
        self.delay_max = delay_max

    def fetch(self, url: str) -> bytes:
        requested = canonicalize_url(url)
        if not _allowed_host(urlsplit(requested).hostname, self.allowed_hosts):
            raise FetchError(f"URL host is not allowlisted: {requested}")
        if self.delay_max:
            time.sleep(random.uniform(self.delay_min, self.delay_max))
        try:
            response = self.session.get(
                url,
                timeout=self.timeout_seconds,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            raise FetchError(f"request failed for {requested}: {exc}") from exc
        except Exception as exc:
            raise FetchError(f"request failed for {requested}: {exc}") from exc

        final_url = canonicalize_url(response.url)
        if not _allowed_host(urlsplit(final_url).hostname, self.allowed_hosts):
            raise FetchError(f"redirect left the source allowlist: {final_url}")
        if response.status_code != 200:
            raise FetchError(f"HTTP {response.status_code} for {requested}")
        declared = response.headers.get("content-length")
        if declared and int(declared) > self.max_response_bytes:
            raise FetchError(f"response-size limit exceeded for {requested}")
        content = response.content
        if len(content) > self.max_response_bytes:
            raise FetchError(f"response-size limit exceeded for {requested}")
        return content


def collect_paginated_links(
    *,
    page_loader: Callable[[int], Sequence[str]],
    allowed_hosts: Sequence[str],
    max_pages: int,
    max_records: int,
) -> PaginationResult:
    """Collect same-host links until an empty/repeated page or a hard cap."""
    if max_pages < 1 or max_records < 1:
        raise ValueError("page and record caps must be positive")
    links: list[str] = []
    prior_signature: tuple[str, ...] | None = None
    for page_number in range(1, max_pages + 1):
        raw_page = page_loader(page_number)
        page_links: list[str] = []
        for raw_url in raw_page:
            try:
                canonical = canonicalize_url(raw_url)
            except ValueError:
                continue
            if _allowed_host(urlsplit(canonical).hostname, allowed_hosts) and canonical not in page_links:
                page_links.append(canonical)
        if not page_links:
            return PaginationResult(links, page_number, "empty_page")
        signature = tuple(page_links)
        if signature == prior_signature:
            return PaginationResult(links, page_number, "repeated_page")
        prior_signature = signature
        for link in page_links:
            if link not in links:
                links.append(link)
                if len(links) >= max_records:
                    return PaginationResult(links, page_number, "record_cap")
    return PaginationResult(links, max_pages, "page_cap")


def _load_csv_bytes(policy: SourcePolicy, content: bytes) -> list[dict[str, str]]:
    if policy.adapter == "huggingface_csv":
        csv_bytes = content
    elif policy.adapter == "mendeley_zip_csv":
        if not policy.archive_member:
            raise ValueError(f"{policy.source_id}: archive_member is required")
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                member = archive.getinfo(policy.archive_member)
                if member.file_size > 64 * 1024 * 1024:
                    raise FetchError(f"{policy.source_id}: archive member exceeds size cap")
                csv_bytes = archive.read(member)
        except (KeyError, zipfile.BadZipFile) as exc:
            raise FetchError(f"{policy.source_id}: invalid or unexpected ZIP archive") from exc
    else:
        raise ValueError(f"unsupported adapter: {policy.adapter}")

    try:
        text = csv_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FetchError(f"{policy.source_id}: CSV is not UTF-8") from exc
    return [dict(row) for row in csv.DictReader(io.StringIO(text))]


def collect_source(
    policy: SourcePolicy,
    *,
    client: BoundedHttpClient,
    max_records: int,
    retrieved_at: str | None = None,
) -> tuple[list[ProvenancedSeedRecord], CollectionStats]:
    """Collect one rights-qualified CSV/ZIP source without assigning labels."""
    for field in ("collection_status", "redistribution_status"):
        if getattr(policy, field) != "allowed":
            raise PermissionError(f"{field} is {getattr(policy, field)} for {policy.source_id}")
    if max_records < 1:
        raise ValueError("max_records must be positive")

    content = client.fetch(policy.download_url)
    if policy.expected_download_bytes is not None and len(content) != policy.expected_download_bytes:
        raise FetchError(
            f"{policy.source_id}: download size mismatch "
            f"({len(content)} != {policy.expected_download_bytes})"
        )
    if policy.expected_download_sha256 is not None:
        actual = hashlib.sha256(content).hexdigest()
        if actual != policy.expected_download_sha256:
            raise FetchError(f"{policy.source_id}: download SHA-256 mismatch")

    rows = _load_csv_bytes(policy, content)
    if rows and policy.text_field not in rows[0]:
        raise FetchError(f"{policy.source_id}: missing text field {policy.text_field!r}")
    if rows and policy.native_id_field and policy.native_id_field not in rows[0]:
        raise FetchError(f"{policy.source_id}: missing native ID field {policy.native_id_field!r}")

    candidates = [
        row
        for row in rows
        if not policy.include_field
        or str(row.get(policy.include_field, "")) in policy.include_values
    ]
    retrieval_time = retrieved_at or _utc_now()
    records: list[ProvenancedSeedRecord] = []
    skipped = 0
    source_base = canonicalize_url(policy.canonical_url)
    for index, row in enumerate(candidates):
        raw_text = str(row.get(policy.text_field, ""))
        text, state = redact_victim_pii(raw_text)
        if len(text) < 10:
            skipped += 1
            continue
        native_id = (
            str(row.get(policy.native_id_field, "")).strip()
            if policy.native_id_field
            else str(index + 1)
        ) or str(index + 1)
        canonical_row_url = f"{source_base}?{urlencode({'row': native_id})}"
        records.append(
            ProvenancedSeedRecord(
                text=text,
                source_url=policy.download_url,
                scrape_timestamp=retrieval_time,
                raw_label_hint=None,
                data_origin="real_public",
                record_unit=policy.record_unit,
                canonical_url=canonical_row_url,
                publisher=policy.publisher,
                native_id=native_id,
                access_method=policy.access_method,
                collection_status=policy.collection_status,
                redistribution_status=policy.redistribution_status,
                rights_url=policy.rights_url,
                retrieved_at=retrieval_time,
                content_sha256=_content_hash(text),
                redaction_state=(
                    "redacted"
                    if state == "redacted"
                    else "verified_source_anonymized"
                ),
                contributing_urls=[canonical_row_url],
                duplicate_count=0,
                provenance_confidence=policy.provenance_confidence,
            )
        )
        if len(records) >= max_records:
            break

    return records, CollectionStats(
        source_id=policy.source_id,
        raw_items=len(rows),
        extracted_candidate_rows=len(candidates),
        retained_before_dedup=len(records),
        skipped_short_or_empty=skipped,
        stop_reason="record_cap" if len(records) >= max_records and len(candidates) > len(records) else "source_exhausted",
    )


def deduplicate_records(
    records: Sequence[ProvenancedSeedRecord],
    existing_records: Sequence[SeedRecord],
    *,
    threshold: float = 95.0,
) -> DedupResult:
    """Collapse URL/exact/near duplicates and retain contributing provenance."""
    existing_texts = [_normalized_key(record.text) for record in existing_records]
    existing_urls = {canonicalize_url(record.source_url) for record in existing_records}
    kept: list[ProvenancedSeedRecord] = []
    kept_keys: list[str] = []
    duplicates_within = 0
    duplicates_existing = 0

    for record in records:
        key = _normalized_key(record.text)
        canonical = canonicalize_url(record.canonical_url)
        if canonical in existing_urls or any(
            fuzz.ratio(key, existing) >= threshold for existing in existing_texts
        ):
            duplicates_existing += 1
            continue

        match_index: int | None = None
        for index, other in enumerate(kept):
            if canonicalize_url(other.canonical_url) == canonical or fuzz.ratio(key, kept_keys[index]) >= threshold:
                match_index = index
                break
        if match_index is None:
            kept.append(record)
            kept_keys.append(key)
            continue

        duplicates_within += 1
        primary = kept[match_index]
        urls = list(dict.fromkeys([*primary.contributing_urls, *record.contributing_urls]))
        kept[match_index] = primary.model_copy(
            update={
                "contributing_urls": urls,
                "duplicate_count": primary.duplicate_count + 1 + record.duplicate_count,
            }
        )

    return DedupResult(kept, duplicates_within, duplicates_existing)


def _load_seed_records(path: Path) -> list[SeedRecord]:
    return [
        SeedRecord.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl_atomic(
    path: Path,
    records: Iterable[ProvenancedSeedRecord],
    *,
    replace: bool,
) -> Path:
    """Atomically write JSONL, refusing accidental overwrite by default."""
    if path.exists() and not replace:
        raise FileExistsError(f"refusing to overwrite {path}; pass --replace")
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(records)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            for record in rows:
                handle.write(record.model_dump_json() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return path


def _load_manifest(path: Path) -> dict[str, Any]:
    rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 1:
        raise ValueError("manifest must contain exactly one JSON object on one JSONL line")
    manifest = json.loads(rows[0])
    if not isinstance(manifest, dict):
        raise ValueError("manifest root must be an object")
    return manifest


def audit_manifest(path: Path) -> dict[str, Any]:
    manifest = _load_manifest(path)
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        raise ValueError("manifest.sources must be a list")
    for source in sources:
        missing = REQUIRED_SOURCE_FIELDS - set(source)
        if missing:
            raise ValueError(f"source {source.get('source_id', '<unknown>')} missing {sorted(missing)}")
    return {
        "valid": True,
        "sources": len(sources),
        "source_families": len({source["source_family"] for source in sources}),
        "qualified_adapters": [
            source["source_id"]
            for source in sources
            if source.get("adapter")
            and source["collection_status"] == "allowed"
            and source["redistribution_status"] == "allowed"
        ],
        "record_units": dict(
            sorted(
                {
                    unit: sum(1 for source in sources if source["record_unit"] == unit)
                    for unit in {source["record_unit"] for source in sources}
                }.items()
            )
        ),
    }


def verify_evidence(
    manifest_path: Path,
    sample_path: Path,
    existing_seed_path: Path,
) -> dict[str, Any]:
    """Verify manifest, sample, dedup, and protected-lineage claims offline."""
    manifest = _load_manifest(manifest_path)
    audit_manifest(manifest_path)
    sample = manifest.get("sample", {})
    status = sample.get("status")
    sample_rows = 0
    if status == "retained":
        if not sample_path.exists():
            raise ValueError(f"retained sample is missing: {sample_path}")
        payload = sample_path.read_bytes()
        if len(payload) != int(sample["bytes"]):
            raise ValueError("sample byte count mismatch")
        if hashlib.sha256(payload).hexdigest() != sample["sha256"]:
            raise ValueError("sample SHA-256 mismatch")
        raw_rows = [json.loads(line) for line in payload.decode("utf-8").splitlines() if line.strip()]
        sample_rows = len(raw_rows)
        if sample_rows != int(sample["rows"]):
            raise ValueError("sample row count mismatch")
        if any("label" in row or "risk_tier" in row for row in raw_rows):
            raise ValueError("sample must remain unlabeled seed evidence")
        records = [ProvenancedSeedRecord.model_validate(row) for row in raw_rows]
        existing = _load_seed_records(existing_seed_path)
        deduped = deduplicate_records(records, existing)
        if len(deduped.records) != len(records):
            raise ValueError("sample contains duplicate rows or overlaps retained seeds")
        if int(manifest.get("eligible_new_records", sample_rows)) != sample_rows:
            raise ValueError("eligible_new_records does not match retained sample rows")
    elif status == "withheld":
        if sample_path.exists():
            raise ValueError("manifest says sample withheld but sample file exists")
    else:
        raise ValueError("manifest sample.status must be retained or withheld")

    for artifact in manifest.get("protected_artifacts", []):
        artifact_path = Path(artifact["path"])
        if not artifact_path.exists():
            raise ValueError(f"protected artifact is missing: {artifact_path}")
        current = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if artifact["before_sha256"] != artifact["after_sha256"] or current != artifact["after_sha256"]:
            raise ValueError(f"protected artifact hash changed: {artifact_path}")
    return {"valid": True, "sample_status": status, "sample_rows": sample_rows}


def _cmd_audit(args: argparse.Namespace) -> int:
    print(json.dumps(audit_manifest(args.manifest), ensure_ascii=False, sort_keys=True))
    return 0


def _cmd_collect(args: argparse.Namespace) -> int:
    manifest = _load_manifest(args.manifest)
    existing = _load_seed_records(args.existing_seeds)
    collected: list[ProvenancedSeedRecord] = []
    stats: list[dict[str, Any]] = []
    for source in manifest.get("sources", []):
        if not source.get("adapter"):
            continue
        policy = SourcePolicy.from_mapping(source)
        if policy.collection_status != "allowed" or policy.redistribution_status != "allowed":
            continue
        client = BoundedHttpClient(
            allowed_hosts=policy.allowed_hosts,
            timeout_seconds=args.timeout,
            max_response_bytes=args.max_response_bytes,
            delay_min=args.delay_min,
            delay_max=args.delay_max,
        )
        source_records, source_stats = collect_source(
            policy,
            client=client,
            max_records=args.max_records_per_source,
        )
        collected.extend(source_records)
        stats.append(asdict(source_stats))
    deduped = deduplicate_records(collected, existing, threshold=args.near_threshold)
    write_jsonl_atomic(args.output, deduped.records, replace=args.replace)
    payload = args.output.read_bytes()
    summary = {
        "output": str(args.output),
        "rows": len(deduped.records),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "duplicates_within": deduped.duplicates_within,
        "duplicates_existing": deduped.duplicates_existing,
        "sources": stats,
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            verify_evidence(args.manifest, args.sample, args.existing_seeds),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit, collect, or verify bounded public Vietnamese scam-source evidence."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Validate and summarize an acquisition manifest.")
    audit.add_argument("--manifest", type=Path, required=True)
    audit.set_defaults(handler=_cmd_audit)

    collect = subparsers.add_parser("collect", help="Collect only rights-qualified audited adapters.")
    collect.add_argument("--manifest", type=Path, required=True)
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--existing-seeds", type=Path, required=True)
    collect.add_argument("--max-records-per-source", type=int, default=50)
    collect.add_argument("--near-threshold", type=float, default=95.0)
    collect.add_argument("--timeout", type=float, default=30.0)
    collect.add_argument("--max-response-bytes", type=int, default=64 * 1024 * 1024)
    collect.add_argument("--delay-min", type=float, default=2.0)
    collect.add_argument("--delay-max", type=float, default=5.0)
    collect.add_argument("--replace", action="store_true")
    collect.set_defaults(handler=_cmd_collect)

    verify = subparsers.add_parser("verify", help="Verify frozen evidence without network access.")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--sample", type=Path, required=True)
    verify.add_argument("--existing-seeds", type=Path, required=True)
    verify.set_defaults(handler=_cmd_verify)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":  # pragma: no cover - exercised via python -m
    raise SystemExit(main())
