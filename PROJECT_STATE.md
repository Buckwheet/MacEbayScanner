# PROJECT_STATE.md

## Goal
Implement automatic 3-minute client-side auto-refresh on the public website with a live countdown timer, in-place data updates (preserving search/filters), and manual refresh capability.

## What Changed
- Added client-side 3-minute auto-refresh in [`site_generator.py`](file:///D:/Code%20Projects/MacEbayScanner/mac_ebay_scanner/site_generator.py) that asynchronously polls `data.json?t=[timestamp]`.
- Implemented visual countdown timer (`Refresh: 3:00` ticking down to `0:00`) in the header next to scanner status.
- Added smooth, in-place DOM updates for listings, stats cards, and dual scan/match timestamps without disruptive full-page reloading or loss of search/filter state.
- Added quick manual refresh button (`triggerImmediateRefresh()`) with spinning animation on click.
- Rebuilt static dashboard on `encoder1` and pushed commit `c109675` to GitHub.
- Verified live on GitHub Pages: `https://buckwheet.github.io/MacEbayScanner/` (confirmed `autoRefreshTimer` and `triggerImmediateRefresh` active in production HTML).

## Commands Run + Results
- `pytest tests -v` -> 17/17 tests passed.
- `python main.py build-site` -> Generated static site locally.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && git pull && python3 main.py build-site && git commit -am 'Deploy client-side 3-min auto refresh [skip ci]' && git push origin main && systemctl --user restart mac-ebay-scanner.service"` -> Built and pushed live docs to `main`, restarted systemd service.
- `python -c "import urllib.request... print('Auto-refresh timer in live site:', ...)"` -> Confirmed both `autoRefreshTimer` and `Refresh button in live site: True` live on GitHub Pages.

## Files Touched
- `mac_ebay_scanner/site_generator.py`
- `docs/index.html`
- `docs/data.json`
- `PROJECT_STATE.md`

## Next 3 Actions
- [ ] Monitor incoming eBay matches during daytime window (8:00 AM - 8:00 PM CST) on Pushbullet.
- [ ] Verify 15-minute heartbeat auto-publish triggers on GitHub Pages without manual intervention.
- [ ] Verify overnight queue transition and 5:00 AM CST summary digest generation.
