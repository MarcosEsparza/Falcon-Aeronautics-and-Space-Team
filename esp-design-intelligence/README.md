# ESP Design Intelligence

A Python and Streamlit screening and historical-analysis demonstration. Included pump and historical records are fictional demonstration data, not validated field designs.

## Local setup

From the esp-design-intelligence directory:

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements-dev.txt
    python -m playwright install chromium

On Windows PowerShell, activate with .venv\Scripts\Activate.ps1.

## Run

Run from the repository root so the root Streamlit theme is applied:

    python -m streamlit run esp-design-intelligence/app.py

## Compile and test

From the esp-design-intelligence directory:

    python -m compileall -q app.py engineering.py history.py tests
    python -m pytest -q

Tests validate software behavior, not field performance.

## Startup check and screenshots

Start Streamlit on port 8501, then run python tests/capture_screenshots.py. The check waits for the application heading and Design Snapshot, rejects horizontal overflow, and writes full-page 390 × 844 mobile and 1440 × 900 desktop screenshots to artifacts/screenshots/. Override defaults with ESP_APP_URL or SCREENSHOT_DIR.

The **ESP quality checks** workflow runs for every pull request and manual dispatch. Open a run summary and download the esp-browser-screenshots artifact, retained for 14 days. Review the images; artifact creation alone is not visual approval.

For a framework-neutral new-repository checklist, see ../DEVELOPMENT_TEMPLATE.md.
