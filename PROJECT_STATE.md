# PROJECT_STATE.md

## Goal
Fix multi-variation / range listing false positives (such as item 266752480393) where sellers list multiple configurations (e.g. "M1 M2 M3 Max 16GB-128GB RAM") with entry-level pricing ($1,349) reflecting base 16GB models instead of 128GB/256GB target machines.

## What Changed
- Diagnosed listing `266752480393`:
  - Title: `Apple MacBook Pro 16” (2021-2023) M1 M2 M3 Max 40-C 16GB- 128GB RAM 512GB- 8TB`
  - Price: `$1,349.00`
  - eBay API metadata: `itemGroupType: SELLER_DEFINED_VARIATIONS`
  - Root cause: Multi-variation dropdown listing where eBay's search API returns the entry-level baseline price ($1,349 for 16GB M1), but the seller stuffed all upper configurations (M3 Max, 128GB RAM, 8TB) into the single title.
- Hardened filter engine in `mac_ebay_scanner/filter_engine.py`:
  - Rejects `itemGroupType == "SELLER_DEFINED_VARIATIONS"`.
  - Rejects title RAM ranges (`\b\d+\s*(?:gb|g)?\s*[-–/]\s*\d+\s*(?:gb|g)?\s*(?:ram|memory)?\b`).
  - Rejects mixed processor generations (`\bm[12]\b.*\bm[345]\b`).
  - Rejects configuration pickers (`choose specs`, `select specs`).
- Upgraded `SeenStorage.reconcile_all_items()` in `mac_ebay_scanner/storage.py` and added `reconcile` CLI command in `mac_ebay_scanner/cli.py`.
- Unit tests added to `tests/test_filter_engine.py` (20 of 20 tests pass).
- Deployed to remote host `encoder1`, reconciled `seen_items.db` (demoting 6 deceptive variation listings), rebuilt dashboard docs, pushed changes to GitHub Pages, and restarted `mac-ebay-scanner.service`.

## Commands Run + Results
- `pytest tests -v` -> 20 passed in 0.40s.
- `ssh encoder1 "python3 main.py reconcile --build-site"` -> Successfully demoted variation listings and rebuilt site.
- `systemctl --user restart mac-ebay-scanner.service` -> Scanner service running cleanly on encoder1.
- `python -c "..."` -> Verified item `266752480393` is moved to `Filtered Out` with reason: `Multi-variation listing (SELLER_DEFINED_VARIATIONS): price reflects entry tier, not 128GB/256GB`. Minimum price for MacBook Pro M3 MAX 128GB corrected to true hardware baseline of $3,690.

## Files Touched
- `mac_ebay_scanner/filter_engine.py`
- `mac_ebay_scanner/storage.py`
- `mac_ebay_scanner/cli.py`
- `tests/test_filter_engine.py`
- `docs/data.json`
- `docs/index.html`
- `PROJECT_STATE.md`

## Next 3 Actions
- [x] Reject multi-variation (`SELLER_DEFINED_VARIATIONS`) and title range listings.
- [x] Add unit tests and reconcile database on `encoder1`.
- [x] Verify GitHub Pages dashboard and trend metrics reflect only true 128GB/256GB hardware.
