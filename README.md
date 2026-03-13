# kindle-highlights

Scrapes all your Kindle highlights from [read.amazon.com/notebook](https://read.amazon.com/notebook) and saves them to a CSV file.

> **Note:** This tool scrapes Amazon's web interface, so it may break if Amazon updates their page structure. If you see 0 highlights, please [open an issue](https://github.com/jackmdsimmons/kindle-highlights/issues).

## Setup

**Windows — one click**

Download the repo and double-click `setup.bat`. It will install everything and offer to run the script immediately.

**Mac/Linux — one click**

```
chmod +x setup.sh && ./setup.sh
```

**Manual (any OS)**

1. Install Python from [python.org](https://www.python.org/downloads/) if you don't have it.
2. Install dependencies:
```
pip install -r requirements.txt
python -m playwright install chromium
```

## Usage

```
python kindle_to_csv.py
```

A browser window will open. Log in to your Amazon account — the script continues automatically once you are logged in.

Your highlights are saved to `kindle_highlights.csv` with four columns: Book Title, Author, Highlight, Location.

**Runtime:** Expect roughly 3-5 minutes for a large library (100+ books).

**Highlight cap:** Kindle's notebook page loads a limited number of highlights per book. Books with very large numbers of highlights may be truncated.

## Config

Open `kindle_to_csv.py` and edit the config section at the top:

| Option | Default | Description |
|---|---|---|
| `OUTPUT_FILE` | `kindle_highlights.csv` | Output filename |
| `HEADLESS` | `False` | Set to `True` to run without a visible browser |
| `BOOK_FILTER` | `[]` | Limit export to specific books, e.g. `["Dune", "2666"]` |
