"""Archive today's full cross-retailer snapshot permanently, one file per day.

reports/<source>_latest.csv gets overwritten every run - it only ever
shows the current snapshot. reports/<source>_history.csv has every row
ever scraped, but as one long append-only log, not as "what did the
table look like on this particular day." This script writes that second
thing: reports/archive/<YYYY-MM>/<YYYY-MM-DD>.csv, saved under today's
date and never touched again after today. Re-running this same day
replaces that day's file (last run of the day wins), which is fine -
it's still "today's snapshot."

Unlike export_latest.py (one file per source, so each file only shows
the *other* two retailers' prices), this combines all three sources into
one file per day with every row's own `source` column intact - so
instead of ~3 files/day (~2,200 over two years, all dumped in one flat
folder), it's 1 file/day (~730 over two years) nested under a
year-month subfolder (~30 files per folder, not ~2,200 in one). Combining
sources also lets the price columns be fully symmetric: every row shows
newegg_price, amazon_price, AND pcpartpicker_price side by side (a row's
own retailer's column just repeats its main `price`), rather than only
the *other* two - a genuine cross-site leaderboard in one sorted file,
sorted by price ascending across all three retailers together.

CSV only, same reasoning as export_history.py: a Markdown table isn't
practical at this scale. Run as `python -m scripts.export_archive` so
the package imports below resolve.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from scripts.export_latest import (
    DB_HEADER,
    DB_PATH,
    OUTPUT_DIR,
    SOURCE_NOISE_KEYWORDS,
    _MEMORY_TYPE_INDEX,
    _NAME_INDEX,
    _PRICE_INDEX,
    _URL_INDEX,
    build_cross_site_index,
    fetch_filtered_rows,
    review_search_url,
)
from scripts.match import spec_key

ARCHIVE_DIR = OUTPUT_DIR / "archive"
ALL_SOURCES = list(SOURCE_NOISE_KEYWORDS)


def build_combined_rows(
    rows_by_source: dict[str, list[tuple]], cross_site_index: dict[tuple, dict[str, tuple[float, str]]]
) -> tuple[list[str], list[tuple]]:
    header = list(DB_HEADER)
    for source in ALL_SOURCES:
        header += [f"{source}_price", f"{source}_url"]
    header.append("review_search_url")

    combined: list[tuple] = []
    for source in ALL_SOURCES:
        for row in rows_by_source[source]:
            key = spec_key(row[_MEMORY_TYPE_INDEX], row[_NAME_INDEX])
            bucket = cross_site_index.get(key, {}) if key else {}

            extra: list = []
            for other in ALL_SOURCES:
                if other == source:
                    extra.extend([row[_PRICE_INDEX], row[_URL_INDEX]])
                else:
                    price, url = bucket.get(other, (None, None))
                    extra.extend([price, url])

            combined.append((*row, *extra, review_search_url(row[_NAME_INDEX])))

    # Sort across all three retailers together - a real cross-site leaderboard.
    # Rows with no price (shouldn't normally happen, but defensively) sort last.
    combined.sort(key=lambda row: (row[_PRICE_INDEX] is None, row[_PRICE_INDEX]))

    return header, combined


def archive_today(
    rows_by_source: dict[str, list[tuple]],
    cross_site_index: dict[tuple, dict[str, tuple[float, str]]],
    archive_dir: Path = ARCHIVE_DIR,
    today: str | None = None,
) -> Path:
    today = today or datetime.now(timezone.utc).date().isoformat()
    month_dir = archive_dir / today[:7]  # YYYY-MM
    month_dir.mkdir(parents=True, exist_ok=True)

    header, combined_rows = build_combined_rows(rows_by_source, cross_site_index)

    out_path = month_dir / f"{today}.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(combined_rows)

    return out_path


def main() -> None:
    rows_by_source = {s: fetch_filtered_rows(s, DB_PATH) for s in SOURCE_NOISE_KEYWORDS}
    cross_site_index = build_cross_site_index(rows_by_source)

    path = archive_today(rows_by_source, cross_site_index)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
