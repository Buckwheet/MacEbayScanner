# PROJECT_STATE.md

## Goal
Implement LLM Performance-per-Dollar (Tok/s per $) metrics, memory bandwidth inference, and interactive sorting/filtering controls for upcoming Qwen 4 local inference on 128GB+ Macs.

## What Changed
- Added `calculate_llm_hardware_metrics()` in `mac_ebay_scanner/site_generator.py`:
  - Maps unified memory bandwidth across Apple Silicon configurations (M3 Max 400 GB/s, M4 Max 546 GB/s, M3 Ultra 800 GB/s, M4 Ultra 1,092 GB/s, M5 Ultra 1,280 GB/s).
  - Estimates token generation speeds for Qwen 4 (27B at ~18GB Q4 footprint and 70B at ~42GB footprint assuming 75% memory bus efficiency).
  - Computes `llm_value_score` = `(tok_s_27b / price) * 1000` (tokens per second per $1,000 spent).
- Enhanced GitHub Pages frontend (`docs/index.html` & `docs/data.json`):
  - Added sort options: "⚡ Best LLM Value (Tok/s per $)" and "🚀 Fastest LLM Speed (Raw Tok/s)".
  - Added speed/bandwidth filter buttons: "🚀 Ultra Speed (800+ GB/s)" and "⚡ High Speed (500+ GB/s)".
  - Embedded real-time LLM inference strip on all verified match cards displaying tok/s, unified bandwidth, and value score.
  - Added tok/s and bandwidth badges to model combination trend cards.
- Added unit test `test_llm_hardware_metrics_calculation` in `tests/test_market_and_pricing.py` (23/23 tests pass).
- Deployed to remote host `encoder1`, rebuilt site docs, pushed to GitHub Pages, and restarted `mac-ebay-scanner.service`.

## Commands Run + Results
- `pytest tests -v` -> 23 passed in 0.42s.
- `python main.py build-site` -> Generated updated `index.html` and `data.json` with hardware tok/s and value scores.
- Deployed to `encoder1`, site rebuilt and live at `https://buckwheet.github.io/MacEbayScanner/`.
- `systemctl --user status mac-ebay-scanner.service` -> Running active.

## Files Touched
- `mac_ebay_scanner/site_generator.py`
- `tests/test_market_and_pricing.py`
- `docs/data.json`
- `docs/index.html`
- `PROJECT_STATE.md`

## Next 3 Actions
- [x] Implement hardware bandwidth and Qwen4 tok/s calculator helper.
- [x] Integrate metrics into `site_generator.py` (JSON and HTML dashboard with sort/filter controls).
- [x] Deploy to `encoder1`, rebuild site, and verify live dashboard.
