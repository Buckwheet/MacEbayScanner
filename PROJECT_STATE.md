# PROJECT_STATE.md

## Goal
Fix price-drop notification bug on unmatched/filtered items (which sent an erroneous price-drop Pushbullet notification for a "MacBook Neo") and verify multi-variation listing 188817784292 is strictly excluded and cannot trigger alerts.

## What Changed
- Diagnosed root cause of the "MacBook Neo" Pushbullet notification:
  - An eBay listing for `New 2026 Apple MacBook Neo 13" A18 Pro 5C GPU 4.0GHz 8GB RAM 256GB SSD` was correctly rejected as `matched=0` ("Not a MacBook Pro or Mac Studio").
  - However, at 09:45:17 CST, the seller dropped the price from $664.99 to $630.99. In `scanner.py`, `is_seen(item_id)` was True, and `check_and_update_price()` lacked an `existing_rec.get("matched") == 1` guard. It detected a price drop on an unmatched item, defaulted the model to "MacBook Pro", and sent a Pushbullet alert.
- Diagnosed listing `188817784292`:
  - `2023 Apple MacBook Pro M3 Max 16.2-inch 36GB-128GB RAM, 1TB-8TB SSD, All Colors` ($2,199).
  - Confirmed demoted to `matched: 0` (`filter_reason: Multi-variation listing (SELLER_DEFINED_VARIATIONS)`). Cleared legacy model/chip/ram to `Non-Target`.
- Hardened `storage.py`, `scanner.py`, and `filter_engine.py`:
  - `storage.py`: In `check_and_update_price()`, if `not existing.get("matched")`, update the price in `seen_items` but NEVER record in `price_history` and return `is_price_drop=False`.
  - `scanner.py`: In `scan_once()`, explicitly check `is_matched = bool(existing_rec.get("matched"))` before processing any price drop or sending a notification.
  - `filter_engine.py`: Explicitly rejects non-target models (`macbook neo`, `neo`, `macbook air`, etc.) and non-M series mobile chips (`A18 Pro`, `A17`, etc.).
  - Added unit tests: `test_reject_macbook_neo_and_a_series_chip` and `test_unmatched_item_never_triggers_price_drop`. (22/22 unit tests passing).
  - Cleaned stray `price_history` records on `encoder1`, refreshed dashboard docs, and restarted `mac-ebay-scanner.service`.

## Commands Run + Results
- `pytest tests -v` -> 22 passed in 0.67s.
- `journalctl` grep on `encoder1` -> Identified errant price drop on item `v1|287711261951|0` at 09:45:17 CST.
- Reconciled and cleaned `encoder1` database -> Deleted 3 stray price history records, set `model: Non-Target`.
- Verified `docs/data.json` -> Confirmed both item `188817784292` and all MacBook Neo listings have `is_matched: False` and `model: Non-Target`.

## Files Touched
- `mac_ebay_scanner/scanner.py`
- `mac_ebay_scanner/storage.py`
- `mac_ebay_scanner/filter_engine.py`
- `tests/test_filter_engine.py`
- `tests/test_market_and_pricing.py`
- `docs/data.json`
- `docs/index.html`
- `PROJECT_STATE.md`

## Next 3 Actions
- [x] Restrict price drop alerts and price history strictly to `matched == 1` items.
- [x] Add explicit rejection for MacBook Neo and non-M series chips in filter engine.
- [x] Deploy to `encoder1`, verify database cleanup, rebuild site, and restart service.
