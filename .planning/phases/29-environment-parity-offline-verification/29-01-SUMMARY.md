---
phase: 29-environment-parity-offline-verification
plan: 01
subsystem: ui
tags: [offline, fonts, wsgi, demo, security]

requires:
  - phase: 28-baseline-readiness-zero-code-diagnostics
    provides: "Locked golden prompts and Phase 29 offline-verification prerequisites"
provides:
  - "Be Vietnam Pro self-hosted WOFF2 assets for the local demo"
  - "Allowlisted WSGI font route for /static/fonts/<filename>"
  - "CDN-free demo HTML and local @font-face declarations"
  - "Regression coverage for font serving and allowlist rejection"
affects: [phase-29-offline-verification, phase-32-fallback-recording]

tech-stack:
  added: []
  patterns:
    - "Exact-filename allowlist before filesystem access for request-derived static font names"
    - "Self-hosted @font-face assets served through the existing WSGI demo app"

key-files:
  created:
    - src/runtime/demo_assets/fonts/be-vietnam-pro-400-vietnamese.woff2
    - src/runtime/demo_assets/fonts/be-vietnam-pro-400-latin-ext.woff2
    - src/runtime/demo_assets/fonts/be-vietnam-pro-400-latin.woff2
    - src/runtime/demo_assets/fonts/be-vietnam-pro-500-vietnamese.woff2
    - src/runtime/demo_assets/fonts/be-vietnam-pro-500-latin-ext.woff2
    - src/runtime/demo_assets/fonts/be-vietnam-pro-500-latin.woff2
    - src/runtime/demo_assets/fonts/be-vietnam-pro-600-vietnamese.woff2
    - src/runtime/demo_assets/fonts/be-vietnam-pro-600-latin-ext.woff2
    - src/runtime/demo_assets/fonts/be-vietnam-pro-600-latin.woff2
    - src/runtime/demo_assets/fonts/be-vietnam-pro-700-vietnamese.woff2
    - src/runtime/demo_assets/fonts/be-vietnam-pro-700-latin-ext.woff2
    - src/runtime/demo_assets/fonts/be-vietnam-pro-700-latin.woff2
  modified:
    - src/runtime/demo.py
    - src/runtime/demo_assets/index.html
    - src/runtime/demo_assets/demo.css
    - tests/runtime/test_demo.py

key-decisions:
  - "Kept the font-serving route deliberately narrow: only exact KNOWN_FONT_FILES members reach FONT_DIR reads."
  - "Left the demo.js .example URL untouched because it is phishing bait text, not a live network dependency."

patterns-established:
  - "For local demo static assets with request-derived names, allowlist before any Path construction."
  - "Offline-readiness sweeps should distinguish real network dependencies from inert sample-message URLs."

requirements-completed: [ENV-03]

coverage:
  - id: D1
    description: "Self-hosted Be Vietnam Pro WOFF2 files are served through an allowlisted /static/fonts route."
    requirement: ENV-03
    verification:
      - kind: unit
        ref: "tests/runtime/test_demo.py::test_demo_font_assets_are_served"
        status: pass
      - kind: unit
        ref: "tests/runtime/test_demo.py::test_demo_font_route_rejects_unlisted_and_path_traversal_names"
        status: pass
    human_judgment: false
  - id: D2
    description: "The demo page no longer references fonts.googleapis.com or fonts.gstatic.com."
    requirement: ENV-03
    verification:
      - kind: unit
        ref: "tests/runtime/test_demo.py::test_demo_index_serves_text_only_form"
        status: pass
      - kind: other
        ref: "rg -n \"https?://\" src/runtime/demo_assets"
        status: pass
    human_judgment: false

duration: 25 min
completed: 2026-07-05
status: complete
---

# Phase 29 Plan 01: Font Self-Hosting Summary

**The local demo now serves Be Vietnam Pro from vendored WOFF2 files with no Google Fonts CDN dependency**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-05T20:33:00+07:00
- **Completed:** 2026-07-05T20:58:37+07:00
- **Tasks:** 2
- **Files modified:** 16

## Accomplishments

- Downloaded the official Be Vietnam Pro WOFF2 assets for weights 400/500/600/700 across vietnamese, latin-ext, and latin subsets.
- Added `FONT_DIR`, `FONT_CONTENT_TYPE`, `KNOWN_FONT_FILES`, and an allowlisted `GET /static/fonts/<filename>` route in `src/runtime/demo.py`.
- Removed Google Fonts CDN preconnect/stylesheet tags from `index.html`.
- Added 12 local `@font-face` declarations to `demo.css`.
- Replaced the stale HTML font assertion with explicit absence checks for `fonts.googleapis.com` and `fonts.gstatic.com`.
- Added route tests that cover all 12 allowed font files plus unlisted and literal `../` traversal-shaped requests.

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing font route coverage** - `e38d2d5` (test)
2. **Task 1 GREEN: Serve self-hosted demo fonts** - `45beca3` (feat)
3. **Task 2: Remove demo font CDN dependency** - `141544d` (fix)

**Plan metadata:** captured in the close-out commit.

## Files Created/Modified

- `src/runtime/demo_assets/fonts/*.woff2` - 12 vendored Be Vietnam Pro font binaries.
- `src/runtime/demo.py` - allowlisted font route and static font constants.
- `src/runtime/demo_assets/index.html` - removed Google Fonts host references.
- `src/runtime/demo_assets/demo.css` - local `@font-face` declarations.
- `tests/runtime/test_demo.py` - font route and CDN-removal regression tests.

## Decisions Made

- Used an exact `frozenset` allowlist rather than a generic static-file route, so path traversal strings never reach a filesystem read.
- Preserved the existing demo sample text containing `https://vpbank-secure.example`; it is an inert `.example` phishing bait URL, not a network dependency.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Verification

- `python -m pytest tests\runtime\test_demo.py -x` -> 7 passed.
- `rg -n "https?://" src/runtime/demo_assets` -> exactly one hit: `src/runtime/demo_assets\demo.js:17` with the documented `.example` bait URL.
- `Select-String demo.css '@font-face'` -> 12 declarations.
- Font asset count under `src/runtime/demo_assets/fonts` -> 12 WOFF2 files.

## Next Phase Readiness

Plan 29-04 can now run its offline browser check without expected failed requests to Google Fonts. Phase 29 Wave 1 can continue with ENV-01/ENV-05 and ENV-04 evidence tasks.

---
*Phase: 29-environment-parity-offline-verification*
*Completed: 2026-07-05*
