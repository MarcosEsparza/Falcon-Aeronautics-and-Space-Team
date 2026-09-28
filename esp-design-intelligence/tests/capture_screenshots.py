"""Browser smoke check and screenshots after actual Streamlit chart rendering."""

from __future__ import annotations

import os
from pathlib import Path
import re

from playwright.sync_api import expect, sync_playwright

BASE_URL = os.environ.get("ESP_APP_URL", "http://127.0.0.1:8501")
OUTPUT_DIR = Path(os.environ.get("SCREENSHOT_DIR", "artifacts/screenshots"))
VIEWPORTS = {"mobile": {"width": 390, "height": 844}, "desktop": {"width": 1440, "height": 900}}

# Vega containers can appear before Altair finishes rendering. Require visible chart artwork.
RENDERED_CHARTS = """minimum => {
    const charts = [...document.querySelectorAll('[data-testid="stVegaLiteChart"]')];
    const rendered = charts.filter(chart => {
        if (chart.getBoundingClientRect().width === 0) return false;
        return [...chart.querySelectorAll('.vega-embed canvas, .vega-embed svg')]
            .some(visual => {
                const size = visual.getBoundingClientRect();
                return size.width > 100 && size.height > 80;
            });
    });
    return rendered.length >= minimum;
}"""


def check_no_horizontal_overflow(page, label: str) -> None:
    dimensions = page.evaluate("""() => ({
        viewport: document.documentElement.clientWidth,
        content: document.documentElement.scrollWidth,
    })""")
    assert dimensions["content"] <= dimensions["viewport"], (
        f"{label} layout overflows horizontally: {dimensions}"
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for name, viewport in VIEWPORTS.items():
                page = browser.new_page(viewport=viewport)
                try:
                    page.goto(BASE_URL, wait_until="domcontentloaded")
                    expect(page.get_by_role("heading", name="ESP Design Intelligence")).to_be_visible(timeout=30_000)
                    expect(page.get_by_role("heading", name="Design snapshot")).to_be_visible()
                    expect(page.locator('[data-testid="stMetricValue"]').first).to_have_text(
                        re.compile(r"^\d[\d,]*(?:\.\d+)? m$"), timeout=30_000
                    )
                    for heading in ("Pump and system head", "Pump shaft horsepower", "Modeled pump efficiency", "Eligible family comparison"):
                        expect(page.get_by_role("heading", name=heading)).to_be_visible()
                    page.wait_for_function(RENDERED_CHARTS, arg=4, timeout=30_000)
                    expect(page.get_by_text("01 / SCREENING RESULT")).to_be_visible()
                    background = page.locator('[data-testid="stAppViewContainer"]').evaluate(
                        "element => getComputedStyle(element).backgroundColor"
                    )
                    assert background == "rgb(8, 18, 20)", (
                        f"{name} expected dark dashboard background, got {background}"
                    )
                    check_no_horizontal_overflow(page, f"{name} sizing")
                    # Ensure numeric cards are readable rather than CSS-ellipsized.
                    clipped = page.locator('[data-testid="stMetricValue"]').evaluate_all(
                        "nodes => nodes.filter(node => node.scrollWidth > node.clientWidth + 2)"
                        ".map(node => node.textContent.trim())"
                    )
                    assert not clipped, f"{name} clipped metric values: {clipped}"
                    page.screenshot(path=OUTPUT_DIR / f"{name}.png", full_page=True)

                    # Streamlit scrolls inside its main pane, so full_page=True alone
                    # does not reveal charts beneath the initial viewport.
                    page.get_by_role("heading", name="Pump and system head").evaluate(
                        "element => element.scrollIntoView({block: 'start'})"
                    )
                    page.wait_for_function(RENDERED_CHARTS, arg=4, timeout=30_000)
                    check_no_horizontal_overflow(page, f"{name} chart grid")
                    page.screenshot(path=OUTPUT_DIR / f"{name}-charts.png")

                    page.get_by_role("tab", name="History").click()
                    expect(page.get_by_role("heading", name="Synthetic historical comparison")).to_be_visible()
                    expect(page.get_by_text("Nearest-neighbor suggestion at historical 60 Hz:", exact=False)).to_be_visible()
                    page.wait_for_function(RENDERED_CHARTS, arg=1, timeout=30_000)
                    check_no_horizontal_overflow(page, f"{name} history")
                    page.screenshot(path=OUTPUT_DIR / f"{name}-history.png", full_page=True)
                finally:
                    page.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
