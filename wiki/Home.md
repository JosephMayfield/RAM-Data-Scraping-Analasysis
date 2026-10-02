<!--
This file mirrors the GitHub Wiki "Home" page. GitHub Wikis live in a
separate git repo (RAM-Data-Scraping-Analasysis.wiki.git) that only gets
created once the Wiki is turned on and a first page is saved through the
GitHub web UI — there's no API for it, so it can't be pushed to from here
sight unseen. Enable the wiki under Settings > Features > Wikis, click
"Create the first page," and paste everything below the next line in as
the Home page. Keeping a copy here means the intro stays version-controlled
and travels with the code.
-->

# RAM Data Scraping & Analysis

## What this project is

A long-running data collection and analysis project to track **RAM pricing, price drops, and customer sentiment** for gaming PCs — comparing **DDR4 vs. DDR5** modules over roughly a **two-year window** (late 2026 – late 2028) to answer a simple question: *which RAM is actually worth buying, and which isn't?*

## Goals

- **Price tracking** — Scrape and log prices over time to capture:
  - Historical price trends and seasonal patterns (holiday sales, new-GPU-launch bumps, etc.)
  - Price drops/discounts as they happen
  - Price ranges by capacity (8GB–64GB+ kits), speed (MHz/MT/s), and timing (CL)
  - DDR4 vs. DDR5 price-per-GB trends as DDR5 matures and DDR4 phases out
- **Best vs. worst RAM** — Rank kits using a combination of:
  - Price-to-performance (price per GB, price per MHz)
  - Price stability/value retention over time
  - Reliability signals from aggregated customer reviews
- **Customer sentiment** — Pull and analyze reviews to surface real-world reliability and compatibility issues that spec sheets don't show (DOA rates, XMP/EXPO stability, heat spreader quality, compatibility with specific motherboards/CPUs).

## Data sources

| Source | What we pull |
|---|---|
| **Newegg** | Pricing, price history, customer star ratings & review text |
| **Amazon** | Pricing, "used/new" price spread, customer star ratings & review text |
| **PCPartPicker** | Price comparison across retailers, user build popularity, compatibility notes |

## Scope

- **RAM types covered:** DDR4 and DDR5 (desktop DIMMs, gaming/consumer focus — not ECC/server RAM)
- **Timeframe:** Continuous scraping over ~2 years to build a real historical dataset rather than a single snapshot
- **Output:** Clean, structured datasets + analysis (price trend charts, best/worst rankings, sentiment summaries) that update as more data comes in

## Status

🚧 Project is just getting started — this page will be updated as scraping pipelines, data schemas, and analysis dashboards come online. Check the repo's README and commit history for the latest progress.
