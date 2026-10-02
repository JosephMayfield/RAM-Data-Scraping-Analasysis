"""Newegg desktop memory (RAM) scraper.

Scrapes Newegg search-result pages for DDR4/DDR5 desktop memory kits and
records a price/rating snapshot for each listing into the SQLite database.

NOTE: Newegg's page markup changes periodically and the site may serve an
anti-bot challenge page instead of real results if it doesn't like the
request. If a run comes back with 0 listings saved, open one of the
SEARCH_URLS below in a real browser, view source on a product tile, and
update the CSS selectors in `parse_listing_page`.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from bs4 import BeautifulSoup

from scrapers.common import make_session, polite_get

DB_PATH = Path(__file__).parent.parent / "data" / "ram_data.db"

# Newegg's "Desktop Memory" category, pre-filtered by DDR generation.
SEARCH_URLS = {
    "DDR5": "https://www.newegg.com/p/pl?d=ddr5+desktop+memory",
    "DDR4": "https://www.newegg.com/p/pl?d=ddr4+desktop+memory",
}

MAX_PAGES_PER_RUN = 3


@dataclass
class ListingItem:
    source_product_id: str
    name: str
    url: str
    price: Optional[float]
    list_price: Optional[float]
    rating: Optional[float]
    review_count: Optional[int]
    memory_type: str


def parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text)
    return float(cleaned) if cleaned else None


def extract_item_id(url: str) -> Optional[str]:
    match = re.search(r"/p/([A-Za-z0-9]+)", url)
    return match.group(1) if match else None


def parse_listing_page(html: str, memory_type: str) -> list[ListingItem]:
    soup = BeautifulSoup(html, "lxml")
    items: list[ListingItem] = []

    for cell in soup.select("div.item-cell"):
        title_el = cell.select_one("a.item-title")
        if not title_el:
            continue

        url = title_el.get("href", "")
        name = title_el.get_text(strip=True)
        source_product_id = extract_item_id(url)
        if not source_product_id:
            continue

        current_el = cell.select_one("li.price-current")
        price = parse_price(current_el.get_text(" ", strip=True)) if current_el else None

        was_el = cell.select_one("li.price-was")
        list_price = parse_price(was_el.get_text(" ", strip=True)) if was_el else None

        rating = None
        rating_el = cell.select_one("a.item-rating")
        if rating_el and rating_el.get("title"):
            match = re.search(r"([\d.]+) out of 5", rating_el["title"])
            if match:
                rating = float(match.group(1))

        review_count = None
        count_el = cell.select_one("span.item-rating-num")
        if count_el:
            match = re.search(r"\d+", count_el.get_text(strip=True).replace(",", ""))
            if match:
                review_count = int(match.group())

        items.append(
            ListingItem(
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


def save_items(conn: sqlite3.Connection, items: Iterable[ListingItem]) -> None:
    now = datetime.now(timezone.utc).isoformat()

    for item in items:
        conn.execute(
            """
            INSERT INTO products (source, source_product_id, name, memory_type, url, first_seen, last_seen)
            VALUES ('newegg', ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_product_id) DO UPDATE SET
                name = excluded.name,
                url = excluded.url,
                last_seen = excluded.last_seen
            """,
            (item.source_product_id, item.name, item.memory_type, item.url, now, now),
        )

        row = conn.execute(
            "SELECT id FROM products WHERE source = 'newegg' AND source_product_id = ?",
            (item.source_product_id,),
        ).fetchone()
        product_id = row[0]

        conn.execute(
            """
            INSERT INTO price_history
                (product_id, price, list_price, in_stock, rating, review_count, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                item.price,
                item.list_price,
                int(item.price is not None),
                item.rating,
                item.review_count,
                now,
            ),
        )

    conn.commit()


def scrape(memory_type: str, base_url: str, max_pages: int) -> list[ListingItem]:
    session = make_session()
    all_items: list[ListingItem] = []

    for page in range(1, max_pages + 1):
        page_url = base_url if page == 1 else f"{base_url}&page={page}"
        response = polite_get(session, page_url)
        items = parse_listing_page(response.text, memory_type)
        if not items:
            break
        all_items.extend(items)

    return all_items


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Newegg DDR4/DDR5 RAM listings.")
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
