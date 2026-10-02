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

Each source's table also gets a price/url column per *other* source, for
whatever that source is charging for the closest-matching configuration
(see scripts/match.py) - e.g. newegg_latest.csv gets amazon_price,
amazon_url, pcpartpicker_price, pcpartpicker_url columns. This is a
best-effort spec match (brand/capacity/speed), not a guarantee of the
exact same SKU across retailers - blank means either that retailer isn't
carrying a matching configuration right now, or the match just couldn't
be made.

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
from scripts.match import spec_key

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
_NAME_INDEX = DB_HEADER.index("name")
_MEMORY_TYPE_INDEX = DB_HEADER.index("memory_type")
_PRICE_INDEX = DB_HEADER.index("price")
_URL_INDEX = DB_HEADER.index("url")


def review_search_url(name: str) -> str:
    return "https://www.youtube.com/results?search_query=" + quote_plus(f"{name} review")


def _escape_markdown_cell(text: str) -> str:
    # Pipes would otherwise be read as column separators; newlines would
    # break the row onto multiple lines.
    return text.replace("|", "\\|").replace("\n", " ")


def fetch_filtered_rows(source: str, db_path: Path) -> list[tuple]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(LATEST_QUERY, (source,)).fetchall()
    conn.close()

    extra_keywords = SOURCE_NOISE_KEYWORDS.get(source, ())
    return [row for row in rows if not is_noise(row[_NAME_INDEX], extra_keywords)]


def build_cross_site_index(rows_by_source: dict[str, list[tuple]]) -> dict[tuple, dict[str, tuple[float, str]]]:
    """spec_key -> {source: (cheapest_price, url)} across all sources."""
    index: dict[tuple, dict[str, tuple[float, str]]] = {}

    for source, rows in rows_by_source.items():
        for row in rows:
            price = row[_PRICE_INDEX]
            if price is None:
                continue
            key = spec_key(row[_MEMORY_TYPE_INDEX], row[_NAME_INDEX])
            if key is None:
                continue

            bucket = index.setdefault(key, {})
            existing = bucket.get(source)
            if existing is None or price < existing[0]:
                bucket[source] = (price, row[_URL_INDEX])

    return index


def build_report_rows(
    source: str, rows: list[tuple], cross_site_index: dict[tuple, dict[str, tuple[float, str]]]
) -> tuple[list[str], list[tuple]]:
    other_sources = [s for s in SOURCE_NOISE_KEYWORDS if s != source]
    header = list(DB_HEADER)
    for other in other_sources:
        header += [f"{other}_price", f"{other}_url"]
    header.append("review_search_url")

    report_rows = []
    for row in rows:
        key = spec_key(row[_MEMORY_TYPE_INDEX], row[_NAME_INDEX])
        bucket = cross_site_index.get(key, {}) if key else {}

        extra: list = []
        for other in other_sources:
            price, url = bucket.get(other, (None, None))
            extra.extend([price, url])

        report_rows.append((*row, *extra, review_search_url(row[_NAME_INDEX])))

    return header, report_rows


def _column_display_name(column: str) -> str:
    words = column.replace("_", " ").split()
    return " ".join("PCPartPicker" if w == "pcpartpicker" else w.title() for w in words)


def write_markdown_table(header: list[str], rows: list[tuple], out_path: Path) -> None:
    idx = {name: i for i, name in enumerate(header)}
    # name/url become one linked cell; review_search_url becomes a link
    # label; every other column (including the cross-site price/url pairs)
    # is shown as-is, in header order.
    skip = {"url", "review_search_url"}
    columns = [c for c in header if c not in skip]

    lines = [
        "| " + " | ".join(_column_display_name(col) for col in columns) + " | Reviews |",
        "|" + "---|" * (len(columns) + 1),
    ]

    for row in rows:
        cells = []
        for col in columns:
            if col == "name":
                name = _escape_markdown_cell(str(row[idx["name"]]))
                cells.append(f"[{name}]({row[idx['url']]})")
            elif col.endswith("_url"):
                value = row[idx[col]]
                label = _column_display_name(col.removesuffix("_url"))
                cells.append(f"[{label}]({value})" if value else "")
            else:
                value = row[idx[col]]
                cells.append(_escape_markdown_cell(str(value)) if value is not None else "")
        cells.append(f"[Search reviews]({row[idx['review_search_url']]})")
        lines.append("| " + " | ".join(cells) + " |")

    out_path.write_text("\n".join(lines) + "\n")


def write_source_report(
    source: str,
    rows_by_source: dict[str, list[tuple]],
    cross_site_index: dict[tuple, dict[str, tuple[float, str]]],
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    header, report_rows = build_report_rows(source, rows_by_source[source], cross_site_index)

    csv_path = output_dir / f"{source}_latest.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(report_rows)

    md_path = output_dir / f"{source}_latest.md"
    write_markdown_table(header, report_rows, md_path)

    return csv_path, md_path


def export_latest(source: str, db_path: Path = DB_PATH, output_dir: Path = OUTPUT_DIR) -> tuple[Path, Path]:
    """Export a single source's report. Fetches every source fresh to build
    the cross-site index, so prefer main()'s approach (fetch once, write
    every source's report) when exporting all sources in one run.
    """
    rows_by_source = {s: fetch_filtered_rows(s, db_path) for s in SOURCE_NOISE_KEYWORDS}
    cross_site_index = build_cross_site_index(rows_by_source)
    return write_source_report(source, rows_by_source, cross_site_index, output_dir)


def main() -> None:
    rows_by_source = {s: fetch_filtered_rows(s, DB_PATH) for s in SOURCE_NOISE_KEYWORDS}
    cross_site_index = build_cross_site_index(rows_by_source)

    for source in SOURCE_NOISE_KEYWORDS:
        csv_path, md_path = write_source_report(source, rows_by_source, cross_site_index, OUTPUT_DIR)
        print(f"Wrote {csv_path}")
        print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
