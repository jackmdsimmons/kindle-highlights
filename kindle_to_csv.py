"""
Kindle Highlights -> CSV
Scrapes read.amazon.com/notebook and saves all your Kindle highlights to a CSV file.

Setup:
  1. Install dependencies:
       pip install -r requirements.txt
       playwright install chromium

  2. Run:
       python kindle_to_csv.py

  3. Log in to your Amazon account in the browser window that opens.
     The script continues automatically once you are logged in.

Config (optional):
  - OUTPUT_FILE  : change the output filename
  - BOOK_FILTER  : limit export to specific books (see below)
  - HEADLESS     : set to True to run without a visible browser window
"""

import asyncio
import csv
import re
from playwright.async_api import async_playwright

# ── Config ────────────────────────────────────────────────────────────────────

OUTPUT_FILE = "kindle_highlights.csv"

# Set to True to run without a visible browser window
HEADLESS = False

# Optional: export only specific books.
# Add case-insensitive substrings of book titles to filter.
# Example: BOOK_FILTER = ["2666", "Dune"]
# Leave empty to export all books.
BOOK_FILTER: list[str] = []

# ─────────────────────────────────────────────────────────────────────────────


async def scrape_kindle_highlights() -> list[dict]:
    highlights = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context()
        page = await context.new_page()

        print("Opening Amazon Kindle notebook...")
        await page.goto("https://read.amazon.com/notebook")

        if "signin" in page.url or "ap/signin" in page.url:
            print("\n>>> Amazon login required.")
            print(">>> Please log in to your Amazon account in the browser window.")
            print(">>> The script will continue automatically once you are logged in.\n")
            await page.wait_for_url("**/notebook**", timeout=120_000)

        print("Logged in. Loading notebook...")
        await page.wait_for_load_state("networkidle")

        book_elements = await page.query_selector_all("div.kp-notebook-library-each-book")
        if not book_elements:
            book_elements = await page.query_selector_all("[id^='kp-notebook-library']")

        print(f"Found {len(book_elements)} books.\n")

        for i, book_el in enumerate(book_elements):
            title_el = await book_el.query_selector("h2")
            author_el = await book_el.query_selector("p")

            book_title = (await title_el.inner_text()).strip() if title_el else "Unknown Title"
            author = (await author_el.inner_text()).strip() if author_el else "Unknown Author"
            author = re.sub(r"^[Bb]y:?\s*", "", author).strip()

            if BOOK_FILTER and not any(f.lower() in book_title.lower() for f in BOOK_FILTER):
                continue

            print(f"[{i+1}/{len(book_elements)}] {book_title} - {author}")

            if i == 0:
                # The first book is pre-selected when the page loads, so clicking it
                # produces no network activity and content may not refresh. Instead,
                # wait for its highlights to appear from the initial page load.
                try:
                    await page.wait_for_selector("#highlight, .kp-notebook-highlight", timeout=10000)
                except Exception:
                    # Nothing appeared — force a click as fallback
                    await book_el.click()
                    await page.wait_for_load_state("networkidle")
                    try:
                        await page.wait_for_selector("#highlight, .kp-notebook-highlight", timeout=5000)
                    except Exception:
                        pass
            else:
                await book_el.click()
                await page.wait_for_load_state("networkidle")
                try:
                    await page.wait_for_selector("#highlight, .kp-notebook-highlight", timeout=5000)
                except Exception:
                    pass

            await page.wait_for_timeout(500)

            highlight_elements = await page.query_selector_all("#highlight")
            location_elements = await page.query_selector_all("#kp-annotation-location")

            if not highlight_elements:
                highlight_elements = await page.query_selector_all(
                    "span[id='highlight'], .kp-notebook-highlight"
                )
            if not location_elements:
                location_elements = await page.query_selector_all(
                    "span[id='kp-annotation-location'], .kp-notebook-metadata"
                )

            count = 0
            for j, h_el in enumerate(highlight_elements):
                text = (await h_el.inner_text()).strip()
                if not text:
                    continue

                location = ""
                if j < len(location_elements):
                    location = (await location_elements[j].inner_text()).strip()

                highlights.append({
                    "Book Title": book_title,
                    "Author": author,
                    "Highlight": text,
                    "Location": location,
                })
                count += 1

            print(f"  -> {count} highlights")

        await browser.close()

    print(f"\nTotal highlights scraped: {len(highlights)}")

    if len(highlights) == 0:
        print("\nWARNING: No highlights were found.")
        print("This usually means Amazon has updated their page structure.")
        print("Please open an issue at https://github.com/jackmdsimmons/kindle-highlights")

    return highlights


def save_csv(highlights: list[dict], path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Book Title", "Author", "Highlight", "Location"])
        writer.writeheader()
        writer.writerows(highlights)
    print(f"Saved to {path}")


async def main():
    highlights = await scrape_kindle_highlights()

    if not highlights:
        print("No highlights found.")
        return

    save_csv(highlights, OUTPUT_FILE)


if __name__ == "__main__":
    asyncio.run(main())
