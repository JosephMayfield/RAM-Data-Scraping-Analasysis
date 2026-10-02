# RAM Data Scraping & Analysis

Tracking RAM (DDR4 & DDR5) prices, price drops, and customer sentiment across major retailers to figure out the best and worst RAM for gaming PCs over time.

See [`wiki/Home.md`](wiki/Home.md) for the full project introduction (also meant to be pasted into the GitHub Wiki — see that file's header for why it lives here too).

## Project layout

```
scrapers/      common.py (shared data shape, DB writes, resilient pagination) plus
               one module per retailer: newegg.py, amazon.py, pcpartpicker.py
db/            SQLite schema + init script
data/          ram_data.db lives here (committed, so price history accumulates in git)
scripts/       export_latest.py / export_history.py / export_archive.py turn the db into
               human-readable files
reports/       generated snapshot (CSV+MD), full-history (CSV), and daily archive (CSV) files
.github/workflows/   scheduled scrapes via GitHub Actions
```

## Latest prices tables

Each retailer gets two generated files, regenerated from the database on every scheduled scrape:

- `reports/<source>_latest.csv` — the raw data (one row per product, cheapest first). GitHub renders `.csv` as a sortable table, but CSV cells are plain text, so a product's URL or its `review_search_url` (a YouTube search link for that exact product, e.g. "Corsair Vengeance 32GB DDR5 6000 review") shows up as inert text, not a clickable link — that's a CSV format limitation, not something GitHub's viewer chooses to skip.
- `reports/<source>_latest.md` — the same data as a Markdown table, with the product name and a "Search reviews" link rendered as real clickable links (GitHub renders Markdown tables with working `[text](url)` links). This is the one to open for browsing; use the `.csv` for loading into a spreadsheet or pandas.

So: [`newegg_latest.md`](reports/newegg_latest.md) / [`.csv`](reports/newegg_latest.csv), [`amazon_latest.md`](reports/amazon_latest.md) / [`.csv`](reports/amazon_latest.csv), [`pcpartpicker_latest.md`](reports/pcpartpicker_latest.md) / [`.csv`](reports/pcpartpicker_latest.csv).

### Cross-retailer price columns

Each table also carries the other two retailers' prices for the closest-matching configuration, e.g. `newegg_latest.csv` has `amazon_price`/`amazon_url` and `pcpartpicker_price`/`pcpartpicker_url` columns alongside Newegg's own price. There's no shared product ID between these sites, so `scripts/match.py` matches listings by parsing (brand, total capacity, speed) out of each product's name — e.g. "Corsair Vengeance 32GB (2 x 16GB) DDR5 6000" matches "CORSAIR Vengeance RGB 32GB (2x16GB) DDR5 6000MHz" even though the wording differs. **This is a best-effort "comparable configuration" match, not a guarantee of the exact same SKU** — it can't tell apart two kits with the same brand/capacity/speed but a different CAS latency or heatspreader color. A blank cross-site column means either that retailer has no matching configuration right now, or the match just couldn't be parsed from the name — not necessarily that it's unavailable there.

## Full price history

`data/ram_data.db` (the SQLite database everything is built from) is a binary file — GitHub can't render its contents, and there's no way to make that browsable in-page. `reports/<source>_history.csv` is the readable version: every price/rating snapshot ever recorded for that retailer, not just today's, ordered oldest-first. [`newegg_history.csv`](reports/newegg_history.csv), [`amazon_history.csv`](reports/amazon_history.csv), [`pcpartpicker_history.csv`](reports/pcpartpicker_history.csv).

This is CSV-only (no Markdown companion) and intentionally append-only (new rows added at the end, old ones never reordered) — over a two-year daily scrape this will grow to a lot of rows, and a growing Markdown table isn't something GitHub renders well at that scale. Eventually (not yet, but expect it before the two years are up) this file will likely exceed GitHub's in-browser file-preview size limit; at that point viewing it means downloading it rather than opening it in the browser tab. That's expected, not a bug.

Editing this file (or the database) doesn't feed back into anything — these are one-way generated exports. If you want to actually edit the underlying data directly, open `data/ram_data.db` with a local SQLite GUI tool (e.g. [DB Browser for SQLite](https://sqlitebrowser.org/), free) rather than editing the generated reports.

## Daily archives

`reports/archive/<source>_<YYYY-MM-DD>.csv` is a permanent copy of that day's snapshot table — the same rows `reports/<source>_latest.csv` had on that specific date, including the cross-retailer price columns, never overwritten once the day has passed. This is the "what did the leaderboard look like on March 3rd" file; `_history.csv` is the "every scrape as one long log" file — same underlying data, organized differently depending on whether you want one day's full table or the whole timeline.

Re-running the workflow more than once on the same day just overwrites that day's archive file rather than creating a duplicate. Expect roughly 365 × 2 × 3 ≈ 2,200 small archive files by the end of the two-year run — browsing that folder's file list on GitHub won't be pleasant after a year or so, but any single day's file is still instantly reachable by its exact filename/date.

## Running the scrapers locally

```bash
pip install -r requirements.txt
python -m db.init_db            # creates data/ram_data.db if it doesn't exist
python -m scrapers.newegg       # scrapes DDR4 + DDR5 listings from Newegg
python -m scrapers.amazon       # scrapes DDR4 + DDR5 listings from Amazon
python -m scrapers.pcpartpicker # scrapes DDR4 + DDR5 listings from PCPartPicker
python -m scripts.export_latest # regenerates reports/*_latest.csv and .md from the db
python -m scripts.export_history # regenerates reports/*_history.csv (full history) from the db
python -m scripts.export_archive # writes today's reports/archive/*_<date>.csv snapshot files
```

Newegg and Amazon each search for DDR4/DDR5 desktop memory directly. PCPartPicker lists all memory in one combined category instead of splitting by generation at the URL level, so its scraper detects DDR4 vs DDR5 from each product's own name and skips anything that names neither (older DDR3 kits, mislabeled rows). All three filter out non-RAM-kit noise: prebuilt PCs and laptop SODIMMs everywhere, unrelated flash drive/SD card results on Amazon, and ECC/registered server memory on PCPartPicker. A separate pass to pull individual customer reviews (rather than just aggregate rating/count) comes next.

**Heads up:** retailer page markup changes periodically and any of these sites can serve an anti-bot challenge page instead of real results — Amazon's and PCPartPicker's bot detection (Cloudflare, in PCPartPicker's case) is considerably more aggressive than Newegg's, and this has already happened to Amazon in practice (see the note at the top of `scrapers/amazon.py`). Each scraper's `scrape_search_pages` call treats a blocked/failed request as "no more results" rather than crashing, so one retailer having a bad day never loses another's data for that run. If a run saves 0 listings for a stretch of days, open that scraper's `SEARCH_URL(S)` in a real browser and check whether the CSS selectors in its `parse_listing_page` still match.

A GitHub Actions workflow (`.github/workflows/scrape-ram-prices.yml`) runs all three scrapers daily and commits the updated database and reports back to the repo, so the dataset builds itself over the two-year tracking window without anyone needing to run it by hand. Each scraper step uses `continue-on-error`, so the commit still happens with whatever data was gathered even if one or two retailers fail outright.
