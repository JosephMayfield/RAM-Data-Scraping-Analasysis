"""Amazon desktop memory (RAM) scraper.

Scrapes Amazon search-result pages for DDR4/DDR5 desktop memory kits and
records a price/rating snapshot for each listing into the SQLite database.

NOTE: Amazon's anti-bot defenses are considerably more aggressive than
Newegg's. A request from a datacenter IP (including GitHub Actions
runners) is much more likely to get served a CAPTCHA/"Robot Check" page
instead of real results than a blank response - if that happens here, the
page text won't match any of the CSS selectors below and this scraper will
just report 0 listings rather than erroring loudly. If runs stay stuck at
0 for several days in a row, that's the likely cause, and the fix is
either slower/less frequent requests or switching to Amazon's official
Product Advertising API (requires an Amazon Associates account) instead
of scraping search pages directly.

Like scrapers/newegg.py, this was written from Amazon's well-known search
result markup (data-asin result cards) since this sandbox can't reach
amazon.com to verify selectors live. First real run will confirm whether
they still match.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scrapers.common import ListingItem, is_noise, make_session, parse_price, polite_get, save_items

DB_PATH = Path(__file__).parent.parent / "data" / "ram_data.db"
BASE_URL = "https://www.amazon.com"

SEARCH_URLS = {
    "DDR5": "https://www.amazon.com/s?k=ddr5+desktop+memory+ram",
    "DDR4": "https://www.amazon.com/s?k=ddr4+desktop+memory+ram",
}

MAX_PAGES_PER_RUN = 3

# On top of the shared noise list (prebuilt PCs, laptop SODIMMs, ...),
# Amazon's "memory" search also surfaces unrelated storage products.
EXTRA_NOISE_KEYWORDS = [
    "flash drive",
    "usb drive",
    "sd card",
    "memory card",
    "card reader",
    "micro sd",
]


def parse_listing_page(html: str, memory_type: str) -> list[ListingItem]:
    soup = BeautifulSoup(html, "lxml")
    items: list[ListingItem] = []

    for cell in soup.select('div[data-component-type="s-search-result"]'):
        source_product_id = cell.get("data-asin")
        if not source_product_id:
            continue

        link_el = cell.select_one("h2 a")
        if not link_el or not link_el.get("href"):
            continue

        title_el = link_el.select_one("span") or link_el
        name = title_el.get_text(strip=True)
        if not name or is_noise(name, EXTRA_NOISE_KEYWORDS):
            continue

        url = urljoin(BASE_URL, link_el["href"])

        price_el = cell.select_one("span.a-price:not(.a-text-price) span.a-offscreen")
        price = parse_price(price_el.get_text(strip=True)) if price_el else None

        list_price_el = cell.select_one("span.a-text-price span.a-offscreen")
        list_price = parse_price(list_price_el.get_text(strip=True)) if list_price_el else None

        rating = None
        rating_el = cell.select_one("span.a-icon-alt")
        if rating_el:
            match = re.search(r"([\d.]+) out of 5", rating_el.get_text(strip=True))
            if match:
                rating = float(match.group(1))

        review_count = None
        count_el = cell.select_one("span.a-size-base.s-underline-text")
        if count_el:
            match = re.search(r"[\d,]+", count_el.get_text(strip=True))
            if match:
                review_count = int(match.group().replace(",", ""))

        items.append(
            ListingItem(
                source="amazon",
                source_product_id=source_product_id,
                name=name,
                url=url,
                price=price,
                list_price=list_price,
                rating=rating,
                review_count=review_count,
                memory_type=memory_type,
            )
        )

    return items


def scrape(memory_type: str, base_url: str, max_pages: int) -> list[ListingItem]:
    session = make_session()
    all_items: list[ListingItem] = []

    for page in range(1, max_pages + 1):
        page_url = base_url if page == 1 else f"{base_url}&page={page}"
        response = polite_get(session, page_url, min_delay=3.0, max_delay=7.0)
        items = parse_listing_page(response.text, memory_type)
        if not items:
            break
        all_items.extend(items)

    return all_items


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Amazon DDR4/DDR5 RAM listings.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES_PER_RUN)
    args = parser.parse_args()

    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)

    total = 0
    for memory_type, url in SEARCH_URLS.items():
        items = scrape(memory_type, url, args.max_pages)
        save_items(conn, items)
        total += len(items)
        print(f"{memory_type}: saved {len(items)} listings")

    conn.close()
    print(f"Done. {total} listings recorded.")


if __name__ == "__main__":
    main()
