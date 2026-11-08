# PROJECT_STATE.md

## Goal
Fix price-drop notification bug on unmatched/filtered items (which sent an erroneous price-drop Pushbullet notification for a "MacBook Neo") and verify multi-variation listing 188817784292 is strictly excluded and cannot trigger alerts.

## What Changed
- Diagnosed root cause of the "MacBook Neo" Pushbullet notification:
  - An eBay listing for `New 2026 Apple MacBook Neo 13" A18 Pro 5C GPU 4.0GHz 8GB RAM 256GB SSD` was correctly rejected as `matched=0` ("Not a MacBook Pro or Mac Studio").
  - However, when the seller dropped the price from $664.99 to $630.99, `scanner.py` checked `is_seen(item_id)` and called `check_and_update_price()`. Because `scanner.py` and `storage.py` did not gate price-drop alerts on `matched == 1`, it detected a price drop on this unmatched item, defaulted its model to "MacBook Pro", and sent a Pushbullet alert.
- Diagnosed listing `188817784292`:
  - `2023 Apple MacBook Pro M3 Max 16.2-inch 36GB-128GB RAM, 1TB-8TB SSD, All Colors` ($2,199).
  - Already classified with `matched=0` and `filter_reason: Multi-variation listing (SELLER_DEFINED_VARIATIONS)`.
  - Cleared legacy model/chip/ram metadata on demoted items so they cannot be misattributed.
- Hardened `storage.py`, `scanner.py`, and `filter_engine.py`:
  - `storage.py`: In `check_and_update_price()`, if `not existing.get("matched")`, update the price in `seen_items` but NEVER record in `price_history` and return `is_price_drop=False`.
  - `scanner.py`: In `scan_once()`, explicitly check `is_matched = bool(existing_rec.get("matched"))` before processing any price drop or sending a notification.
  - `filter_engine.py`: Explicitly rejects non-target models (`macbook neo`, `neo`, `macbook air`, etc.) and non-M series mobile chips (`A18 Pro`, `A17`, etc.).
  - Added unit tests: `test_reject_macbook_neo_and_a_series_chip` and `test_unmatched_item_never_triggers_price_drop`. (22/22 unit tests passing).

## Commands Run + Results
- `pytest tests -v` -> 22 passed in 0.67s.
- Local tests verified unmatched items cannot trigger price-drop notifications or record price history.

## Files Touched
- `mac_ebay_scanner/scanner.py`
- `mac_ebay_scanner/storage.py`
- `mac_ebay_scanner/filter_engine.py`
- `tests/test_filter_engine.py`
- `tests/test_market_and_pricing.py`
- `PROJECT_STATE.md`

## Next 3 Actions
- [ ] Commit and push code changes to GitHub repository.
- [ ] Pull changes onto `encoder1`, clean any errant price history for non-target items, and restart `mac-ebay-scanner.service`.
- [ ] Verify `encoder1` journalctl and confirm system is operating cleanly without spurious alerts.
