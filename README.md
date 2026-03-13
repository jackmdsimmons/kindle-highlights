# kindle-highlights

Scrapes all your Kindle highlights from [read.amazon.com/notebook](https://read.amazon.com/notebook) and saves them to a CSV file.

## Setup

**1. Install Python**
Download from [python.org](https://www.python.org/downloads/) if you don't have it.

**2. Install dependencies**
```
pip install -r requirements.txt
playwright install chromium
```

## Usage

```
python kindle_to_csv.py
```

A browser window will open. Log in to your Amazon account — the script continues automatically once you're logged in.

Your highlights are saved to `kindle_highlights.csv` with four columns: Book Title, Author, Highlight, Location.

## Config

Open `kindle_to_csv.py` and edit the config section at the top:

| Option | Default | Description |
|---|---|---|
| `OUTPUT_FILE` | `kindle_highlights.csv` | Output filename |
| `HEADLESS` | `False` | Set to `True` to run without a visible browser |
| `BOOK_FILTER` | `[]` | Limit export to specific books, e.g. `["Dune", "2666"]` |
