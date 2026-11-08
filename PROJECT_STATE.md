# PROJECT_STATE.md

## Goal
Investigate and fix Unified Memory claim bug where 256GB listings displayed "128GB Unified Memory" in card footers, normalize RAM detection across storage and site generation, and visually distinguish 128GB vs 256GB models with prominent memory badges.

## What Changed
- Root Cause Identified: The initial HTML dashboard template had hardcoded `<span class="text-xs text-gray-500 font-mono">128GB Unified Memory</span>` from before 256GB models were supported, causing 256GB Mac Studio cards to display contradictory memory values.
- Updated `storage.py` to automatically normalize legacy or unnormalized memory strings in `seen_items.db` to canonical `'128GB'` or `'256GB'`.
- Updated `site_generator.py`:
  - Normalized RAM display (`256GB Unified Memory` vs `128GB Unified Memory`).
  - Added prominent badges in listing card headers: purple `[💾 256GB RAM]` for 256GB models, cyan `[💾 128GB RAM]` for 128GB models.
  - Formatted card footers with distinct memory icons and verified memory text.
- Updated `notifier.py` overnight digest template to display actual listing memory (`256GB` or `128GB`) and refer to `M3+ 128GB/256GB Macs`.
- Rebuilt static dashboard on `encoder1` and published commit `f1aea82` to GitHub Pages. Confirmed live in production HTML.

## Commands Run + Results
- `pytest tests -v` -> 17/17 unit tests passed.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && python3 main.py matches --limit 15"` -> Confirmed backend SQLite database correctly classified M3/M5 Ultra models with 256GB RAM.
- `python -c "import urllib.request... print('Found ramBadgeText in live HTML:', ...)"` -> Confirmed `True` on live GitHub Pages site.

## Files Touched
- `mac_ebay_scanner/storage.py`
- `mac_ebay_scanner/site_generator.py`
- `mac_ebay_scanner/notifier.py`
- `docs/index.html`
- `docs/data.json`
- `PROJECT_STATE.md`

## Next 3 Actions
- [ ] Monitor incoming eBay matches during daytime window (8:00 AM - 8:00 PM CST) on Pushbullet.
- [ ] Verify 15-minute heartbeat auto-publish triggers on GitHub Pages without manual intervention.
- [ ] Verify overnight queue transition and 5:00 AM CST summary digest generation.
