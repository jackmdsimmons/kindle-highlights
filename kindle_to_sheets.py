"""
Kindle Highlights → CSV 
Scrapes read.amazon.com/notebook and saves highlights to a CSV file.

Usage:
  python kindle_to_sheets.py

"""

import asyncio
import csv
import re
from playwright.async_api import async_playwright

# Set to True to see the browser window while scraping
HEADLESS = False

# Optional: filter to specific book titles (case-insensitive substrings).
# Leave empty to export all books.
BOOK_FILTER: list[str] = []

OUTPUT_FILE = "kindle_highlights.csv"


async def scrape_kindle_highlights() -> list[dict]:
    highlights = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context()
        page = await context.new_page()

        print("Opening Amazon Kindle notebook...")
        await page.goto("https://read.amazon.com/notebook")

        # Wait for login if needed
        if "signin" in page.url or "ap/signin" in page.url:
            print("\n>>> Amazon login required.")
            print(">>> Please log in in the browser window.")
            print(">>> The script will continue automatically once you're logged in.\n")
            await page.wait_for_url("**/notebook**", timeout=120_000)

        print("Logged in. Loading notebook...")
        await page.wait_for_load_state("networkidle")

        # Get all books from the sidebar
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

            print(f"[{i+1}/{len(book_elements)}] {book_title} — {author}")

            if i == 0:
                # First book is pre-selected on load — don't click, just wait for its
                # highlights to appear naturally.
                try:
                    await page.wait_for_selector("#highlight, .kp-notebook-highlight", timeout=10000)
                except Exception:
                    # Still nothing — force a click
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
    print(f"\nDone! Open Google Sheets > File > Import > upload '{OUTPUT_FILE}'")


if __name__ == "__main__":
    asyncio.run(main())
