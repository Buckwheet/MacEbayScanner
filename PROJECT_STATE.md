# PROJECT_STATE.md

## Goal
Implement periodic heartbeat updates (every 15 minutes) for the public GitHub Pages website, add live scanner status badge ("🟢 Active (Polling every 3 mins)", "Last Scan Timestamp", and "Last New Match Timestamp"), and explain why the website timestamp hadn't refreshed.

## What Changed
- Diagnosed root cause: `encoder1` was scanning actively every 3 minutes (08:31, 08:34, 08:37, 08:40, 08:43, 08:46, 08:49, 08:52, 08:55, 08:58, 09:01, 09:04), but `update_public_site()` was only conditioned on `matches_found > 0 or price_drops_detected > 0`. Since no new 128GB/256GB Macs were listed in those 35 minutes, the site timestamp remained at 08:28 AM.
- Updating `scanner.py` to trigger periodic site updates (every 15 minutes or when matches occur) with a heartbeat mechanism.
- Updating `site_generator.py` and `docs/index.html` to clearly display:
  - `🟢 Scanner Online (Polling eBay every 3 mins)`
  - `Last eBay Scan Check: [time]`
  - `Last New Listing Found: [time]`
  - `Total Listings Evaluated: [count]`

## Commands Run + Results
- `journalctl --user -u mac-ebay-scanner.service -n 25` -> Verified scanner ran 12 scans between 08:31 and 09:04 CST, accurately filtering out non-target laptops.

## Files Touched
- `D:\Code Projects\MacEbayScanner\PROJECT_STATE.md`

## Next 3 Actions
- [ ] Update `site_generator.py` with heartbeat metadata (last scanned, last match time, total processed).
- [ ] Update `scanner.py` with 15-minute periodic site publish interval.
- [ ] Push to GitHub and sync with `encoder1`.
