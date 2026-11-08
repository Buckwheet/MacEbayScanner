# PROJECT_STATE.md

## Goal
Deploy live heartbeat dashboard updates, display dual status timestamps ("Last Scan" vs "Last New Match"), add 256GB filter controls, and reconcile git synchronization between `encoder1` and GitHub Pages.

## What Changed
- Resolved divergence on `encoder1` by resetting to latest `origin/main` commit (`dec00a6`), generating fresh static docs with 57 verified listings, and pushing commit `0addcb4`.
- Re-started `mac-ebay-scanner.service` on `encoder1`; verified clean scan pass execution in systemd journal.
- GitHub Pages dashboard is verified live at https://buckwheet.github.io/MacEbayScanner/ featuring:
  - Header: `🟢 ONLINE 24/7 • Polling every 3 mins on encoder1`
  - Dual Timestamps: `Last Scan: [Time] CST` • `Last New Match: [Time]`
  - Four Status Cards: Scanner Status, Evaluated Today, Matching Machines, AI Evaluator (LOQ RTX 3050 qwen2.5)
  - Interactive Filter Tabs: All, MacBook Pro, Mac Studio, 256GB RAM Only, 🔥 Deals Only
- Heartbeat daemon trigger in `scanner.py` set to 15-minute auto-publish cadence even when no new listings appear.

## Commands Run + Results
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && git reset --hard origin/main && python3 main.py build-site"` -> Successfully reset working directory to `dec00a6` and built static dashboard files.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && git commit -am 'Refresh live dashboard...' && git push origin main && systemctl --user restart mac-ebay-scanner.service"` -> Pushed commit `0addcb4` and restarted service.
- `python -c "import urllib.request; ..."` -> Confirmed `ONLINE 24/7` and `256GB` elements present on live GitHub Pages site.
- `ssh encoder1 "journalctl --user -u mac-ebay-scanner.service -n 15 --no-pager"` -> Verified daemon actively scanning 11 queries every 180s.

## Files Touched
- `mac_ebay_scanner/scanner.py`
- `mac_ebay_scanner/site_generator.py`
- `docs/index.html`
- `docs/data.json`
- `PROJECT_STATE.md`

## Next 3 Actions
- [ ] Monitor incoming eBay matches during daytime window (8:00 AM - 8:00 PM CST) on Pushbullet.
- [ ] Verify 15-minute heartbeat auto-publish triggers on GitHub Pages without manual intervention.
- [ ] Verify overnight queue transition and 5:00 AM CST summary digest generation.
