"""Deterministic browser smoke check and screenshot capture for CI."""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("ESP_APP_URL", "http://127.0.0.1:8501")
OUTPUT_DIR = Path(os.environ.get("SCREENSHOT_DIR", "artifacts/screenshots"))
VIEWPORTS = {
    "mobile": {"width": 390, "height": 844},
    "desktop": {"width": 1440, "height": 900},
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for name, viewport in VIEWPORTS.items():
                page = browser.new_page(viewport=viewport)
                page.goto(BASE_URL, wait_until="domcontentloaded")
                expect(page.get_by_role("heading", name="ESP Design Intelligence")).to_be_visible(timeout=30_000)
                expect(page.get_by_text("Design Snapshot", exact=True)).to_be_visible()
                dimensions = page.evaluate("""() => ({
                    viewport: document.documentElement.clientWidth,
                    content: document.documentElement.scrollWidth,
                })""")
                assert dimensions["content"] <= dimensions["viewport"], (
                    f"{name} layout overflows horizontally: {dimensions}"
                )
                page.screenshot(path=OUTPUT_DIR / f"{name}.png", full_page=True)
                page.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
