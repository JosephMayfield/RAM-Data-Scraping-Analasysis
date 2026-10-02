# RAM Data Scraping & Analysis

Tracking RAM (DDR4 & DDR5) prices, price drops, and customer sentiment across major retailers to figure out the best and worst RAM for gaming PCs over time.

See [`wiki/Home.md`](wiki/Home.md) for the full project introduction (also meant to be pasted into the GitHub Wiki — see that file's header for why it lives here too).

## Project layout

```
scrapers/      one module per retailer (newegg.py, amazon.py, pcpartpicker.py — newegg first)
db/            SQLite schema + init script
data/          ram_data.db lives here (committed, so price history accumulates in git)
scripts/       export_latest.py turns the db into human-readable CSV tables
reports/       generated CSV snapshots — open these on GitHub to see a live table
.github/workflows/   scheduled scrapes via GitHub Actions
```

## Latest prices table

[`reports/newegg_latest.csv`](reports/newegg_latest.csv) holds the most recent price/rating snapshot per product, one row each, sorted cheapest first. GitHub renders `.csv` files as a sortable table right in the browser — click the file above to view it that way instead of as raw text. It's regenerated from the database on every scheduled scrape.

## Running the Newegg scraper locally

```bash
pip install -r requirements.txt
python -m db.init_db          # creates data/ram_data.db if it doesn't exist
python -m scrapers.newegg     # scrapes DDR4 + DDR5 listings, appends a price_history snapshot
python scripts/export_latest.py   # regenerates reports/newegg_latest.csv from the db
```

`scrapers/newegg.py` currently scrapes product listing pages (price, rating, review count) for DDR4 and DDR5 desktop memory. A separate pass to pull individual customer reviews, plus Amazon and PCPartPicker scrapers, comes next.

**Heads up:** Newegg's page markup changes periodically and can occasionally serve an anti-bot challenge page instead of real results. If a run saves 0 listings, open one of the `SEARCH_URLS` in `scrapers/newegg.py` in a real browser and check whether the CSS selectors in `parse_listing_page` still match.

A GitHub Actions workflow (`.github/workflows/scrape-newegg.yml`) runs this daily and commits the updated database back to the repo, so the dataset builds itself over the two-year tracking window without anyone needing to run it by hand.
