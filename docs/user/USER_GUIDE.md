# Phase 2 User Guide

## Setup

Install the local runtime dependencies from the repository root:

```bash
python -m pip install -e .[dev]
```

## Local Runtime Boundary

The Phase 2 runtime is local-only and does not persist raw text by default.

Text-only v1: paste extracted text manually. Images/OCR and audio are not accepted in Phase 2.

Do not paste screenshots, audio placeholders, or attachment-only markers. Extract the message text first, then paste that text into the runtime.

## Doctor Command

Use the doctor command before analysis when you want to confirm the local environment is ready:

```bash
vnphish doctor
python -m src.runtime.cli doctor
```

If the runtime is misconfigured, the doctor output includes exact next-step commands such as:

```bash
python -m pip install -e .[dev]
python -m pytest tests/runtime -q
python -m src.runtime.cli doctor
```

## Analyze One Message

The normal usage is stdin-first: one message per run.

```bash
vnphish analyze
python -m src.runtime.cli analyze
```

Paste one suspicious SMS, Zalo, Messenger, Telegram, or Facebook message into stdin, then finish input. The runtime returns a short provisional result and up to three quoted suspicious cues.

## Local Demo UI

If you want a non-terminal flow, launch the local demo UI:

```bash
vnphish demo
python -m src.runtime.cli demo
```

Optional local server controls:

```bash
python -m src.runtime.cli demo --host 127.0.0.1 --port 8765 --no-browser
```

The demo opens a local browser page where you can paste suspicious text, choose an optional channel hint, and review risk tier, threat labels, grounded cues, and safe next steps without using CLI syntax.

You can also provide an optional channel hint:

```bash
python -m src.runtime.cli analyze --channel sms
```

## Automation Escape Hatch

Use `--text` only for automation and tests, not as the default user flow.

```bash
vnphish analyze --text "VPBank cảnh báo account Internet Banking của bạn sẽ bị khóa trong 24h. Không chia sẻ mã OTP." --channel sms
python -m src.runtime.cli analyze --text "VPBank cảnh báo account Internet Banking của bạn sẽ bị khóa trong 24h. Không chia sẻ mã OTP." --channel sms
```

Supported options in Phase 2:

- `--text`
- `--channel`

Supported demo options in Phase 6:

- `--host`
- `--port`
- `--no-browser`

There is no batch mode, file mode, OCR mode, voice mode, or cloud fallback mode in this release.

## Failure Behavior

If the runtime is not ready, `analyze` fails closed and prints local remediation guidance instead of attempting any remote path.

If you see a text-only rejection, paste extracted text manually and retry. The Phase 2 runtime is intentionally limited to direct text input.