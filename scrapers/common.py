"""Shared helpers for all retailer scrapers: a browser-like session,
rate-limited requests, the product/price-history data shape, and the DB
write logic every scraper needs regardless of which site it parses.
"""
from __future__ import annotations

import random
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Optional, Sequence

import requests

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return session


def polite_get(
    session: requests.Session,
    url: str,
    min_delay: float = 2.0,
    max_delay: float = 5.0,
    **kwargs,
) -> requests.Response:
    """GET with a randomized delay beforehand, so scheduled runs don't
    fire requests back-to-back.
    """
    time.sleep(random.uniform(min_delay, max_delay))
    response = session.get(url, timeout=15, **kwargs)
    response.raise_for_status()
    return response


@dataclass
class ListingItem:
    source: str
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


# Prebuilt PCs and laptop SODIMMs show up in full-text RAM searches on every
# retailer because their descriptions mention "DDR4"/"DDR5 RAM". Each
# scraper can extend this with site-specific noise (e.g. Amazon's memory
# card/flash drive results).
BASE_NOISE_KEYWORDS = [
    "sodimm",
    "laptop",
    "notebook",
    "ssd",
    "processor",
    "geforce",
    "radeon",
    "prebuilt",
    "motherboard",
    "graphics card",
    "all-in-one",
]


def is_noise(name: str, extra_keywords: Sequence[str] = ()) -> bool:
    lower = name.lower()
    return any(keyword in lower for keyword in (*BASE_NOISE_KEYWORDS, *extra_keywords))


def save_items(conn: sqlite3.Connection, items: Iterable[ListingItem]) -> None:
    now = datetime.now(timezone.utc).isoformat()

    for item in items:
        conn.execute(
            """
            INSERT INTO products (source, source_product_id, name, memory_type, url, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_product_id) DO UPDATE SET
                name = excluded.name,
                url = excluded.url,
                last_seen = excluded.last_seen
            """,
            (item.source, item.source_product_id, item.name, item.memory_type, item.url, now, now),
        )

        row = conn.execute(
            "SELECT id FROM products WHERE source = ? AND source_product_id = ?",
            (item.source, item.source_product_id),
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
