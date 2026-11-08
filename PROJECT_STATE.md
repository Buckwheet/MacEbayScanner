# PROJECT_STATE.md

## Goal
Implement a dedicated, comprehensive Model Combination Trend Analysis section on the public dashboard featuring comparative price brackets, deal targets, liquidity metrics, condition distributions, and interactive filtering.

## What Changed
- Consolidated category normalization in `storage.py` into 7 canonical high-memory tiers (unifying all M3 Ultra 256GB Mac Studios into a single category).
- Added `get_detailed_trend_analysis()` in `storage.py` computing real-time min, median, avg, max, 15% deal threshold, price spread percentage, SSD storage distribution, and condition counts for each hardware combination.
- Updated `site_generator.py` and `docs/index.html` with:
  - Model Combination Trend Analysis grid (`#trendsGrid`) with sub-tabs (`All Specs`, `MacBook Pro`, `Mac Studio`).
  - Visual Price Spectrum bars showing Low, Average, High, and Median benchmarks.
  - Deal target indicators (`🔥 Deal Target: < $X,XXX`).
  - Storage spread chips (`1TB`, `2TB`, `4TB`, `16TB`).
  - Interactive `View X listings ➔` button that instantly activates the combination filter and smoothly scrolls to the listings.
  - Active filter badge with one-click clear button.
- Deployed to `encoder1`; verified autonomous daemon scan pass at 09:24 AM CST cleanly auto-published and verified live on GitHub Pages.

## Commands Run + Results
- `pytest tests -v` -> 17/17 tests passed.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && python3 main.py market"` -> Verified 7 unified model combination categories.
- `python -c "import urllib.request... print('Found trendsGrid in live HTML:', True)"` -> Verified `trendsGrid` and `setTrendTab` live on GitHub Pages.

## Files Touched
- `mac_ebay_scanner/storage.py`
- `mac_ebay_scanner/site_generator.py`
- `docs/index.html`
- `docs/data.json`
- `PROJECT_STATE.md`

## Next 3 Actions
- [ ] Monitor incoming eBay matches during daytime window (8:00 AM - 8:00 PM CST) on Pushbullet.
- [ ] Verify 15-minute heartbeat auto-publish triggers on GitHub Pages without manual intervention.
- [ ] Verify overnight queue transition and 5:00 AM CST summary digest generation.
