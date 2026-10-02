# RAM Data Scraping & Analysis

Tracking RAM (DDR4 & DDR5) prices, price drops, and customer sentiment across major retailers to figure out the best and worst RAM for gaming PCs over time.

See [`wiki/Home.md`](wiki/Home.md) for the full project introduction (also meant to be pasted into the GitHub Wiki — see that file's header for why it lives here too).

## Project layout

```
scrapers/      common.py (shared data shape, DB writes, resilient pagination) plus
               one module per retailer: newegg.py, amazon.py, pcpartpicker.py
db/            SQLite schema + init script
data/          ram_data.db lives here (committed, so price history accumulates in git)
scripts/       export_latest.py turns the db into human-readable CSV tables
reports/       generated CSV snapshots, one per retailer — open these on GitHub to see a live table
.github/workflows/   scheduled scrapes via GitHub Actions
```

## Latest prices tables

[`reports/newegg_latest.csv`](reports/newegg_latest.csv), [`reports/amazon_latest.csv`](reports/amazon_latest.csv), and [`reports/pcpartpicker_latest.csv`](reports/pcpartpicker_latest.csv) each hold the most recent price/rating snapshot per product, one row each, sorted cheapest first. GitHub renders `.csv` files as a sortable table right in the browser — click a file above to view it that way instead of as raw text. All three are regenerated from the database on every scheduled scrape.

Each row also has a `review_search_url` column: a YouTube search link built from that exact product's name (e.g. "Corsair Vengeance 32GB DDR5 6000 review"), so clicking it from the table pulls up real people's review videos for that kit. GitHub's CSV viewer renders a table but doesn't auto-link URLs in a cell, so you'll need to copy/open the link rather than click it directly in the preview — it's still plain text in the raw file, which keeps this dependency-free (no YouTube API key, no per-product video matching to maintain).

## Running the scrapers locally

```bash
pip install -r requirements.txt
python -m db.init_db            # creates data/ram_data.db if it doesn't exist
python -m scrapers.newegg       # scrapes DDR4 + DDR5 listings from Newegg
python -m scrapers.amazon       # scrapes DDR4 + DDR5 listings from Amazon
python -m scrapers.pcpartpicker # scrapes DDR4 + DDR5 listings from PCPartPicker
python -m scripts.export_latest # regenerates reports/*_latest.csv from the db
```

Newegg and Amazon each search for DDR4/DDR5 desktop memory directly. PCPartPicker lists all memory in one combined category instead of splitting by generation at the URL level, so its scraper detects DDR4 vs DDR5 from each product's own name and skips anything that names neither (older DDR3 kits, mislabeled rows). All three filter out non-RAM-kit noise: prebuilt PCs and laptop SODIMMs everywhere, unrelated flash drive/SD card results on Amazon, and ECC/registered server memory on PCPartPicker. A separate pass to pull individual customer reviews (rather than just aggregate rating/count) comes next.

**Heads up:** retailer page markup changes periodically and any of these sites can serve an anti-bot challenge page instead of real results — Amazon's and PCPartPicker's bot detection (Cloudflare, in PCPartPicker's case) is considerably more aggressive than Newegg's, and this has already happened to Amazon in practice (see the note at the top of `scrapers/amazon.py`). Each scraper's `scrape_search_pages` call treats a blocked/failed request as "no more results" rather than crashing, so one retailer having a bad day never loses another's data for that run. If a run saves 0 listings for a stretch of days, open that scraper's `SEARCH_URL(S)` in a real browser and check whether the CSS selectors in its `parse_listing_page` still match.

A GitHub Actions workflow (`.github/workflows/scrape-ram-prices.yml`) runs all three scrapers daily and commits the updated database and reports back to the repo, so the dataset builds itself over the two-year tracking window without anyone needing to run it by hand. Each scraper step uses `continue-on-error`, so the commit still happens with whatever data was gathered even if one or two retailers fail outright.
