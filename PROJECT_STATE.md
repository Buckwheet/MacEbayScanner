# PROJECT_STATE.md

## Goal
Implement a dedicated, comprehensive Model Combination Trend Analysis section on the public dashboard featuring comparative price brackets, deal thresholds, liquidity metrics, condition distributions, and interactive filtering.

## What Changed
- Initiating model combination trend analysis:
  - Consolidating category normalization in `storage.py` (unifying Studio Ultra 256GB classifications).
  - Calculating comprehensive trend metrics per combination: min, median, avg, max, 15% deal target, sample volume, and condition breakdown.
  - Adding a visual comparative price trend matrix and deep-dive cards to `site_generator.py` and `docs/index.html`.
  - Adding click-to-filter capability connecting trend analysis rows directly to filtered listing results.

## Commands Run + Results
- `read_file tests/test_market_and_pricing.py` -> Confirmed test assertions for `get_category_key`.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && python3 main.py market"` -> Inspected current market stats distribution across 8 model combinations.

## Files Touched
- `mac_ebay_scanner/storage.py`
- `mac_ebay_scanner/site_generator.py`
- `PROJECT_STATE.md`

## Next 3 Actions
- [ ] Update `storage.py` category normalization and add `get_model_trends()` helper.
- [ ] Update `site_generator.py` to embed trend analysis matrix, visual comparative spectrums, and interactive quick-filters.
- [ ] Run test suite (`pytest tests -v`), build site, push to GitHub, and deploy to `encoder1`.
