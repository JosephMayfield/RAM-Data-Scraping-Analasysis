"""Archive today's snapshot table permanently, one file per day.

reports/<source>_latest.csv gets overwritten every run - it only ever
shows the current snapshot. reports/<source>_history.csv has every row
ever scraped, but as one long append-only log, not as "what the table
looked like on this particular day." This script writes that second
thing: reports/archive/<source>_<YYYY-MM-DD>.csv, the exact same rows
export_latest.py would write today (same noise filtering, same
cross-site price columns), saved under today's date and never
overwritten again after today. Re-running this same day replaces that
day's archive file (last run of the day wins), which is fine - it's
still "today's snapshot."

CSV only, consistent with export_history.py: this adds one file per
source per day, so after two years there will be roughly 365*2*3 ≈ 2200
small archive files. That's an intentional tradeoff for "one file per
day" - browsing the reports/archive/ folder's file list on GitHub won't
be pleasant after a year or so, but any single day's file stays
instantly, individually openable by its date. Run as `python -m
scripts.export_archive` so the package imports below resolve.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from scripts.export_latest import (
    DB_PATH,
    OUTPUT_DIR,
    SOURCE_NOISE_KEYWORDS,
    build_cross_site_index,
    build_report_rows,
    fetch_filtered_rows,
)

ARCHIVE_DIR = OUTPUT_DIR / "archive"


def archive_today(
    rows_by_source: dict[str, list[tuple]],
    cross_site_index: dict[tuple, dict[str, tuple[float, str]]],
    archive_dir: Path = ARCHIVE_DIR,
    today: str | None = None,
) -> list[Path]:
    archive_dir.mkdir(parents=True, exist_ok=True)
    today = today or datetime.now(timezone.utc).date().isoformat()

    paths = []
    for source in SOURCE_NOISE_KEYWORDS:
        header, report_rows = build_report_rows(source, rows_by_source[source], cross_site_index)

        out_path = archive_dir / f"{source}_{today}.csv"
        with out_path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(report_rows)
        paths.append(out_path)

    return paths


def main() -> None:
    rows_by_source = {s: fetch_filtered_rows(s, DB_PATH) for s in SOURCE_NOISE_KEYWORDS}
    cross_site_index = build_cross_site_index(rows_by_source)

    for path in archive_today(rows_by_source, cross_site_index):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
