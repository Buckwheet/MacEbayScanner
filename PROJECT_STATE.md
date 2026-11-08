# PROJECT_STATE.md

## Goal
Fix multi-variation / range listing false positives (such as item 266752480393) where sellers list multiple configurations (e.g. "M1 M2 M3 Max 16GB-128GB RAM") with entry-level pricing ($1,349) reflecting base 16GB models instead of 128GB/256GB target machines.

## What Changed
- Diagnosed listing `266752480393`:
  - Title: `Apple MacBook Pro 16” (2021-2023) M1 M2 M3 Max 40-C 16GB- 128GB RAM 512GB- 8TB`
  - Price: `$1,349.00`
  - eBay API metadata: `itemGroupType: SELLER_DEFINED_VARIATIONS`
  - Root cause: The listing is a multi-variation dropdown listing where the $1,349 price is for the base 16GB M1 model, not the 128GB M3 Max option mentioned in the title range.
- Updated `mac_ebay_scanner/filter_engine.py`:
  - Reject listings with `itemGroupType == "SELLER_DEFINED_VARIATIONS"`.
  - Reject titles containing RAM ranges (e.g. `16GB-128GB RAM`, `36GB-128GB RAM`).
  - Reject titles listing mixed processor generations (e.g. `M1 M2 M3 Max`).
  - Reject multi-spec configuration picker keywords (`Choose Specs`, `Select Specs`).
- Added 3 new unit tests in `tests/test_filter_engine.py` (total 20 tests pass).
- Deploying to `encoder1` and reconciling SQLite database to demote multi-variation items and rebuild GitHub Pages dashboard.

## Commands Run + Results
- `pytest tests -v` -> 20 passed in 0.48s.
- `git commit -am "Reject multi-variation and RAM range listings (SELLER_DEFINED_VARIATIONS)"` -> Committed locally.

## Files Touched
- `mac_ebay_scanner/filter_engine.py`
- `tests/test_filter_engine.py`
- `PROJECT_STATE.md`

## Next 3 Actions
- [ ] Push local commit to GitHub `origin/main`.
- [ ] SSH to `encoder1`, pull latest code, reconcile database to demote variation listings, rebuild site, and commit/push.
- [ ] Verify `266752480393` is moved to `Filtered Out` and no longer skews statistics or shows as a verified match.
