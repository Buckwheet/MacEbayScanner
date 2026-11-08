# PROJECT_STATE.md

## Goal
Expand eBay monitor, filter engine, local model prompts, and GitHub Pages dashboard to support 128GB and 256GB Unified Memory models (M3+ MacBook Pro and Mac Studio) for Splash LLM workloads, with strict 256GB SSD storage trap rejection.

## What Changed
- Expanded search queries in `mac_ebay_scanner/config.py` from 6 to 11 queries covering 256GB unified memory configurations (`Mac Studio 256GB`, `Mac Studio M4 256GB`, `Mac Studio M4 Ultra 256GB`, etc.).
- Enhanced `mac_ebay_scanner/filter_engine.py`:
  - Added support for 256GB Unified Memory / RAM.
  - Implemented strict 256GB SSD trap prevention: rejects base laptops (e.g. 8GB RAM + 256GB SSD) by verifying RAM size in eBay structured aspects and title specs.
- Updated `mac_ebay_scanner/storage.py` to track 128GB and 256GB models in dynamic category baselines.
- Refined `mac_ebay_scanner/local_llm.py` so LOQ's `qwen2.5:7b` recognizes 256GB RAM as valid and focuses strictly on qualitative value evaluation without false-negative vetoes.
- Added 3 unit tests in `tests/test_filter_engine.py` (total 17 passed).
- Live verification on `encoder1`: Found 12 new listings including 256GB Mac Studio M3 Ultra ($8,850.00) and M5 Ultra configs, sent alerts to Pushbullet, and published 57 active listings to GitHub Pages.

## Commands Run + Results
- `python -m pytest tests -v` -> 17 passed in 0.34s.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && /home/encoder1/.local/bin/pytest tests -v"` -> 17 passed in 0.41s.
- `systemctl --user restart mac-ebay-scanner.service` -> Running across 11 queries in `[Mode: Immediate Daytime]`.
- Live Scan: Found 256GB Mac Studios (`Apple Mac Studio M3 Ultra 256GB RAM 1TB SSD - $9,997.00`, `Mac Studio M5 Ultra 256GB - $15,000.00`).
- Dashboard updated at [https://buckwheet.github.io/MacEbayScanner/](https://buckwheet.github.io/MacEbayScanner/).

## Files Touched
- `D:\Code Projects\MacEbayScanner\mac_ebay_scanner\config.py`
- `D:\Code Projects\MacEbayScanner\mac_ebay_scanner\filter_engine.py`
- `D:\Code Projects\MacEbayScanner\mac_ebay_scanner\storage.py`
- `D:\Code Projects\MacEbayScanner\mac_ebay_scanner\local_llm.py`
- `D:\Code Projects\MacEbayScanner\mac_ebay_scanner\notifier.py`
- `D:\Code Projects\MacEbayScanner\mac_ebay_scanner\scanner.py`
- `D:\Code Projects\MacEbayScanner\tests\test_filter_engine.py`
- `D:\Code Projects\MacEbayScanner\PROJECT_STATE.md`
- `encoder1:/home/encoder1/MacEbayScanner/*`

## Next 3 Actions
- [x] Expanded target to 128GB and 256GB unified memory models.
- [x] Verified SSD trap rejection and unit tests (17 passed).
- [ ] Monitor incoming live Pushbullet notifications for 128GB & 256GB Mac deals.
