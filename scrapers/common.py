"""Shared helpers for all retailer scrapers: a browser-like session and
rate-limited requests so we don't hammer any one site.
"""
from __future__ import annotations

import random
import time

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
