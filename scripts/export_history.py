"""Export the full price-history log (every snapshot ever recorded) to CSV.

Unlike export_latest.py (today's single row per product, rewritten and
re-sorted by price on every run), this is a growing append-only log
ordered by scraped_at - a plain historical record of every scrape, not a
leaderboard. CSV only, no Markdown companion: this keeps growing for the
full two-year run, and a multi-hundred-thousand-row Markdown table isn't
something GitHub (or a browser) renders well. Ordering by scraped_at
(not re-sorting by price) also keeps this git-diff-friendly, since each
run only appends new rows at the end instead of reshuffling old ones.

Once this file grows past GitHub's file-preview size limit (a few MB),
the in-browser table view will stop rendering and it'll need downloading
to open instead - expected eventually for a two-year daily scrape, not a
bug. Run as `python -m scripts.export_history` so the package imports
below resolve.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from scrapers.common import is_noise
from scripts.export_latest import SOURCE_NOISE_KEYWORDS, review_search_url

DB_PATH = Path(__file__).parent.parent / "data" / "ram_data.db"
OUTPUT_DIR = Path(__file__).parent.parent / "reports"

HISTORY_QUERY = """
SELECT
    p.source,
    p.memory_type,
    p.name,
    ph.price,
    ph.list_price,
    ph.rating,
    ph.review_count,
    ph.in_stock,
    ph.scraped_at,
    p.url
FROM products p
JOIN price_history ph ON ph.product_id = p.id
WHERE p.source = ?
ORDER BY ph.scraped_at ASC, ph.id ASC
"""

HEADER = [
    "source",
    "memory_type",
    "name",
    "price",
    "list_price",
    "rating",
    "review_count",
    "in_stock",
    "scraped_at",
    "url",
    "review_search_url",
]
_NAME_INDEX = HEADER.index("name")


def export_history(source: str, db_path: Path = DB_PATH, output_dir: Path = OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(HISTORY_QUERY, (source,)).fetchall()
    conn.close()

    extra_keywords = SOURCE_NOISE_KEYWORDS.get(source, ())
    rows = [row for row in rows if not is_noise(row[_NAME_INDEX], extra_keywords)]
    rows = [(*row, review_search_url(row[_NAME_INDEX])) for row in rows]

    out_path = output_dir / f"{source}_history.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(rows)

    return out_path


def main() -> None:
    for source in SOURCE_NOISE_KEYWORDS:
        path = export_history(source)
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
