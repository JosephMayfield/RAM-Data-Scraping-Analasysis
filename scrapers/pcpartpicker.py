"""PCPartPicker desktop memory (RAM) scraper.

Unlike Newegg/Amazon, PCPartPicker doesn't sell RAM itself - it lists the
lowest current price across retailers for each part, plus a user rating.
Its memory category also isn't split into separate DDR4/DDR5 search URLs
the way Newegg's and Amazon's are (or at least not in a way reliably
reachable by a plain query-string filter), so instead of filtering by
generation at the URL level, this scrapes the combined listing and
determines DDR4 vs DDR5 per row from the product name itself, skipping
anything that names neither (older DDR3 kits still listed for budget
builds, mislabeled rows, etc).

NOTE: like scrapers/amazon.py, this was written from PCPartPicker's
commonly-documented table markup (tr.tr__product rows) since this sandbox
can't reach pcpartpicker.com to verify selectors live, and PCPartPicker
also runs anti-bot protection (Cloudflare) that can serve a challenge
page instead of real results. First real run will confirm whether the
selectors still match and whether requests get through at all - treat
this the same as the Amazon scraper's live-markup caveat.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.common import ListingItem, is_noise, parse_price, save_items, scrape_search_pages

DB_PATH = Path(__file__).parent.parent / "data" / "ram_data.db"
BASE_URL = "https://pcpartpicker.com"

# The combined desktop memory category (laptop SO-DIMMs are a separate
# PCPartPicker category, so that noise source shouldn't show up here).
# sort=price gives the page a real query string so pagination
# (&page=N, added by scrapers.common.scrape_search_pages) is well-formed.
SEARCH_URL = "https://pcpartpicker.com/products/memory/?sort=price"

MAX_PAGES_PER_RUN = 5

# On top of the shared noise list, PCPartPicker's memory category mixes in
# ECC/registered server and workstation modules alongside consumer kits.
EXTRA_NOISE_KEYWORDS = [
    "ecc",
    "registered",
    "rdimm",
    "lrdimm",
]


def detect_memory_type(name: str) -> str | None:
    upper = name.upper()
    if "DDR5" in upper:
        return "DDR5"
    if "DDR4" in upper:
        return "DDR4"
    return None


def extract_product_id(url: str) -> str | None:
    match = re.search(r"/product/([A-Za-z0-9]+)/", url)
    return match.group(1) if match else None


def parse_listing_page(html: str, _memory_type: str) -> list[ListingItem]:
    soup = BeautifulSoup(html, "lxml")
    items: list[ListingItem] = []

    for row in soup.select("tr.tr__product"):
        link_el = row.select_one("td.td__name a")
        if not link_el or not link_el.get("href"):
            continue

        name = link_el.get_text(" ", strip=True)
        memory_type = detect_memory_type(name)
        if not memory_type or is_noise(name, EXTRA_NOISE_KEYWORDS):
            continue

        url = urljoin(BASE_URL, link_el["href"])
        source_product_id = extract_product_id(url)
        if not source_product_id:
            continue

        price_el = row.select_one("td.td__price")
        price = parse_price(price_el.get_text(strip=True)) if price_el else None

        rating = None
        review_count = None
        rating_el = row.select_one("td.td__rating")
        if rating_el:
            rating_text = rating_el.get_text(" ", strip=True)
            rating_match = re.search(r"([\d.]+)\s*/\s*5", rating_text) or re.search(
                r"([\d.]+)\s*out of\s*5", rating_text
            )
            if rating_match:
                rating = float(rating_match.group(1))
            count_match = re.search(r"\(?([\d,]+)\)?\s*rating", rating_text, re.IGNORECASE)
            if count_match:
                review_count = int(count_match.group(1).replace(",", ""))

        items.append(
            ListingItem(
                source="pcpartpicker",
                source_product_id=source_product_id,
                name=name,
                url=url,
                price=price,
                list_price=None,
                rating=rating,
                review_count=review_count,
                memory_type=memory_type,
            )
        )

    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape PCPartPicker DDR4/DDR5 RAM listings.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES_PER_RUN)
    args = parser.parse_args()

    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)

    items = scrape_search_pages("DDR4/DDR5", SEARCH_URL, args.max_pages, parse_listing_page)
    save_items(conn, items)
    conn.close()

    ddr5_count = sum(1 for item in items if item.memory_type == "DDR5")
    ddr4_count = sum(1 for item in items if item.memory_type == "DDR4")
    print(f"DDR5: saved {ddr5_count} listings")
    print(f"DDR4: saved {ddr4_count} listings")
    print(f"Done. {len(items)} listings recorded.")


if __name__ == "__main__":
    main()
