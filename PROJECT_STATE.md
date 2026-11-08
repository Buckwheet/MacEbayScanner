# PROJECT_STATE.md

## Goal
Expand eBay monitor and filter engine to target both 128GB and 256GB Unified Memory models (M3+ MacBook Pro and Mac Studio) for Splash LLM local workloads, with strict SSD-trap protection for 256GB storage.

## What Changed
- Starting task to support 256GB RAM models alongside 128GB RAM models:
  - Add search queries for 256GB RAM (`Mac Studio 256GB`, `MacBook Pro 256GB`, etc.) in `config.py`.
  - Update `filter_engine.py` to recognize 128GB and 256GB unified memory, while strictly rejecting base Macs that have 256GB SSD with low RAM.
  - Update `storage.py` to categorize and compute market trends for 128GB and 256GB models.
  - Update `local_llm.py` and `notifier.py` prompts and formatting.
  - Write test cases for 256GB RAM detection and 256GB SSD trap rejection.
  - Deploy to `encoder1`.

## Commands Run + Results
- Previous deployment verified live on `encoder1` and GitHub Pages at `https://buckwheet.github.io/MacEbayScanner/`.

## Files Touched
- `D:\Code Projects\MacEbayScanner\PROJECT_STATE.md`

## Next 3 Actions
- [ ] Update `filter_engine.py`, `config.py`, `storage.py`, and `local_llm.py` to support 128GB and 256GB unified memory.
- [ ] Write unit tests in `tests/test_filter_engine.py` verifying 256GB RAM support and 256GB SSD trap rejection.
- [ ] Deploy updates to `encoder1`, rebuild site, and verify live monitor.
