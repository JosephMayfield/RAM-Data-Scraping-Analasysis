"""Export the latest price/rating snapshot per product to CSV and Markdown.

GitHub renders a .csv file as a sortable table right in the browser, so
the CSV gives a human-readable view of the dataset without anyone needing
to open the SQLite file - but CSV cells are plain text, so a URL in one
is never clickable there, just a string that happens to look like a link.
The companion .md file exists for that: GitHub renders Markdown tables
with real `[text](url)` links, so the product name and review-search link
are clickable there. The CSV stays the raw/plain-text version (easiest to
load into a spreadsheet or pandas); the Markdown version is for browsing.
Both are regenerated after each scrape so they always reflect the latest
data.

Non-RAM-kit noise (prebuilt PCs, laptop SODIMMs, unrelated storage
products) that was scraped before a scraper started filtering it out of
new results gets dropped here too, so old rows already in the database
don't linger in the generated tables. Run as `python -m
scripts.export_latest` so the `scrapers` package import below resolves.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from urllib.parse import quote_plus

from scrapers.amazon import EXTRA_NOISE_KEYWORDS as AMAZON_EXTRA_NOISE_KEYWORDS
from scrapers.common import is_noise
from scrapers.pcpartpicker import EXTRA_NOISE_KEYWORDS as PCPARTPICKER_EXTRA_NOISE_KEYWORDS

DB_PATH = Path(__file__).parent.parent / "data" / "ram_data.db"
OUTPUT_DIR = Path(__file__).parent.parent / "reports"

# Each source's extra noise keywords, on top of common.BASE_NOISE_KEYWORDS.
SOURCE_NOISE_KEYWORDS = {
    "newegg": (),
    "amazon": AMAZON_EXTRA_NOISE_KEYWORDS,
    "pcpartpicker": PCPARTPICKER_EXTRA_NOISE_KEYWORDS,
}

LATEST_QUERY = """
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
JOIN price_history ph ON ph.id = (
    SELECT id FROM price_history
    WHERE product_id = p.id
    ORDER BY scraped_at DESC
    LIMIT 1
)
WHERE p.source = ?
ORDER BY ph.price ASC
"""

DB_HEADER = [
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
]

# review_search_url isn't a DB column - it's a YouTube search link built from
# the product name at export time, so clicking it in the table shows real
# people's review videos for that kit without needing an API key or any
# per-product lookup/matching step.
REPORT_HEADER = DB_HEADER + ["review_search_url"]


def review_search_url(name: str) -> str:
    return "https://www.youtube.com/results?search_query=" + quote_plus(f"{name} review")


def _escape_markdown_cell(text: str) -> str:
    # Pipes would otherwise be read as column separators; newlines would
    # break the row onto multiple lines.
    return text.replace("|", "\\|").replace("\n", " ")


def write_markdown_table(source: str, rows: list[tuple], out_path: Path) -> None:
    idx = {name: i for i, name in enumerate(REPORT_HEADER)}
    columns = ["memory_type", "name", "price", "list_price", "rating", "review_count", "in_stock", "scraped_at"]
    lines = [
        "| " + " | ".join(col.replace("_", " ").title() for col in columns) + " | Reviews |",
        "|" + "---|" * (len(columns) + 1),
    ]

    for row in rows:
        cells = []
        for col in columns:
            if col == "name":
                name = _escape_markdown_cell(str(row[idx["name"]]))
                cells.append(f"[{name}]({row[idx['url']]})")
            else:
                cells.append(_escape_markdown_cell(str(row[idx[col]] if row[idx[col]] is not None else "")))
        cells.append(f"[Search reviews]({row[idx['review_search_url']]})")
        lines.append("| " + " | ".join(cells) + " |")

    out_path.write_text("\n".join(lines) + "\n")


def export_latest(source: str, db_path: Path = DB_PATH, output_dir: Path = OUTPUT_DIR) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(LATEST_QUERY, (source,)).fetchall()
    conn.close()

    name_index = DB_HEADER.index("name")
    extra_keywords = SOURCE_NOISE_KEYWORDS.get(source, ())
    rows = [row for row in rows if not is_noise(row[name_index], extra_keywords)]
    rows = [(*row, review_search_url(row[name_index])) for row in rows]

    csv_path = output_dir / f"{source}_latest.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(REPORT_HEADER)
        writer.writerows(rows)

    md_path = output_dir / f"{source}_latest.md"
    write_markdown_table(source, rows, md_path)

    return csv_path, md_path


def main() -> None:
    for source in SOURCE_NOISE_KEYWORDS:
        csv_path, md_path = export_latest(source)
        print(f"Wrote {csv_path}")
        print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
