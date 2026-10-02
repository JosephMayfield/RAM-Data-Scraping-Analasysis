-- One row per distinct product we've seen, per source.
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,              -- 'newegg', 'amazon', 'pcpartpicker'
    source_product_id TEXT NOT NULL,   -- retailer's own item/ASIN id
    name TEXT NOT NULL,
    brand TEXT,
    memory_type TEXT,                  -- 'DDR4' or 'DDR5'
    capacity_gb INTEGER,
    kit_config TEXT,                   -- e.g. '2x8GB'
    speed_mhz INTEGER,
    cas_latency TEXT,
    url TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    UNIQUE (source, source_product_id)
);

-- One row per scrape, per product: this is what builds the 2-year price history.
CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products (id),
    price REAL,
    list_price REAL,
    in_stock INTEGER,
    rating REAL,
    review_count INTEGER,
    scraped_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products (id),
    source TEXT NOT NULL,
    reviewer_name TEXT,
    rating REAL,
    title TEXT,
    body TEXT,
    review_date TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE (product_id, source, reviewer_name, review_date, title)
);

CREATE INDEX IF NOT EXISTS idx_price_history_product_time
    ON price_history (product_id, scraped_at);
