"""
Kindle Highlights → Notion
Scrapes read.amazon.com/notebook and uploads highlights to a Notion database.
Each row = one highlight with Book Title, Author, Highlight, Location columns.

Setup:
  1. Create a Notion integration: https://www.notion.so/my-integrations
  2. Copy the token into NOTION_TOKEN below
  3. Create a Notion database (or use an existing one) and share it with your integration
  4. Copy the database ID into NOTION_DATABASE_ID below
     (The ID is the 32-char string in the database URL before the '?')
  5. Run: python kindle_to_notion.py
"""

import asyncio
import json
import re
import os
from playwright.async_api import async_playwright
from notion_client import Client

# ── Config ────────────────────────────────────────────────────────────────────
NOTION_TOKEN = "your_notion_token_here"
NOTION_DATABASE_ID = "your_database_id_here"

# Set to True to see the browser window while scraping (useful for debugging)
HEADLESS = False

# Optional: filter to specific book titles (case-insensitive substrings).
# Leave empty to export all books.
BOOK_FILTER: list[str] = []
# ─────────────────────────────────────────────────────────────────────────────


async def scrape_kindle_highlights() -> list[dict]:
    """
    Opens read.amazon.com/notebook in a browser, waits for the user to log in,
    then scrapes all books and their highlights.
    Returns a list of dicts: {book_title, author, highlight, location}
    """
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
            print(">>> Please log in to your Amazon account in the browser window.")
            print(">>> The script will continue automatically once you're logged in.\n")
            await page.wait_for_url("**/notebook**", timeout=120_000)

        print("Logged in. Loading notebook...")
        await page.wait_for_load_state("networkidle")

        # Get all book entries in the sidebar
        book_elements = await page.query_selector_all("div.kp-notebook-library-each-book")

        if not book_elements:
            # Try alternate selector
            book_elements = await page.query_selector_all("[id^='kp-notebook-library']")

        print(f"Found {len(book_elements)} books.")

        for i, book_el in enumerate(book_elements):
            # Get book title and author
            title_el = await book_el.query_selector("h2")
            author_el = await book_el.query_selector("p")

            book_title = (await title_el.inner_text()).strip() if title_el else "Unknown Title"
            author = (await author_el.inner_text()).strip() if author_el else "Unknown Author"
            # Clean up "By: " prefix Amazon sometimes adds
            author = re.sub(r"^[Bb]y:?\s*", "", author).strip()

            # Apply book filter
            if BOOK_FILTER:
                if not any(f.lower() in book_title.lower() for f in BOOK_FILTER):
                    continue

            print(f"  [{i+1}/{len(book_elements)}] {book_title} — {author}")

            # Click the book to load its highlights
            await book_el.click()
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(1000)

            # Scrape highlights
            highlight_elements = await page.query_selector_all("#highlight")
            location_elements = await page.query_selector_all("#kp-annotation-location")

            # Fallback selectors
            if not highlight_elements:
                highlight_elements = await page.query_selector_all(
                    "span[id='highlight'], .kp-notebook-highlight"
                )
            if not location_elements:
                location_elements = await page.query_selector_all(
                    "span[id='kp-annotation-location'], .kp-notebook-metadata"
                )

            book_highlight_count = 0
            for j, h_el in enumerate(highlight_elements):
                text = (await h_el.inner_text()).strip()
                if not text:
                    continue

                location = ""
                if j < len(location_elements):
                    location = (await location_elements[j].inner_text()).strip()

                highlights.append({
                    "book_title": book_title,
                    "author": author,
                    "highlight": text,
                    "location": location,
                })
                book_highlight_count += 1

            print(f"    → {book_highlight_count} highlights")

        await browser.close()

    print(f"\nTotal highlights scraped: {len(highlights)}")
    return highlights


def create_notion_database_if_missing(notion: Client, parent_page_id: str | None = None) -> str:
    """
    Creates the Notion database with the right schema if it doesn't exist.
    Only used when you don't have a database ID yet.
    Requires a parent_page_id.
    """
    if not parent_page_id:
        raise ValueError("parent_page_id is required to create a new database.")

    response = notion.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "Kindle Highlights"}}],
        properties={
            "Highlight": {"title": {}},
            "Book Title": {"rich_text": {}},
            "Author": {"rich_text": {}},
            "Location": {"rich_text": {}},
        },
    )
    return response["id"]


def upload_to_notion(highlights: list[dict], notion_token: str, database_id: str):
    """
    Uploads highlights to Notion. Skips duplicates by checking if the
    exact highlight text already exists in the database.
    """
    notion = Client(auth=notion_token)

    print(f"\nUploading {len(highlights)} highlights to Notion...")

    # Fetch existing highlights to avoid duplicates
    print("Checking for existing highlights...")
    existing = set()
    has_more = True
    cursor = None

    while has_more:
        kwargs = {"database_id": database_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        response = notion.databases.query(**kwargs)

        for page in response["results"]:
            props = page["properties"]
            if props.get("Highlight", {}).get("title"):
                texts = props["Highlight"]["title"]
                if texts:
                    existing.add(texts[0]["plain_text"][:200])

        has_more = response.get("has_more", False)
        cursor = response.get("next_cursor")

    print(f"Found {len(existing)} existing highlights — skipping duplicates.")

    added = 0
    skipped = 0

    for h in highlights:
        key = h["highlight"][:200]
        if key in existing:
            skipped += 1
            continue

        notion.pages.create(
            parent={"database_id": database_id},
            properties={
                "Highlight": {
                    "title": [{"text": {"content": h["highlight"][:2000]}}]
                },
                "Book Title": {
                    "rich_text": [{"text": {"content": h["book_title"]}}]
                },
                "Author": {
                    "rich_text": [{"text": {"content": h["author"]}}]
                },
                "Location": {
                    "rich_text": [{"text": {"content": h["location"]}}]
                },
            },
        )
        added += 1

        if added % 10 == 0:
            print(f"  Uploaded {added}/{len(highlights) - skipped} highlights...")

    print(f"\nDone! Added {added} new highlights, skipped {skipped} duplicates.")


async def main():
    if NOTION_TOKEN == "your_notion_token_here":
        print("ERROR: Set your NOTION_TOKEN in the script before running.")
        return
    if NOTION_DATABASE_ID == "your_database_id_here":
        print("ERROR: Set your NOTION_DATABASE_ID in the script before running.")
        return

    # 1. Scrape
    highlights = await scrape_kindle_highlights()

    if not highlights:
        print("No highlights found. Exiting.")
        return

    # 2. Save a local backup JSON
    backup_file = "kindle_highlights_backup.json"
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(highlights, f, ensure_ascii=False, indent=2)
    print(f"Backup saved to {backup_file}")

    # 3. Upload to Notion
    upload_to_notion(highlights, NOTION_TOKEN, NOTION_DATABASE_ID)


if __name__ == "__main__":
    asyncio.run(main())
