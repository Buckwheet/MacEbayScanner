# PROJECT_STATE.md

## Goal
Diagnose and resolve the GitHub Pages live site update freeze where "Last Scan" was stuck at 10:30 AM CST.

## What Changed
- Diagnosed root cause: At 10:30 AM CST, commits were pushed from the local development repo to `origin/main`. The background systemd service on `encoder1` generated doc commits on an older base commit without syncing first; GitHub subsequently rejected `git push origin main` due to divergent branches.
- Identified silent error handling in `mac_ebay_scanner/scanner.py`: `update_public_site()` did not evaluate `subprocess.run(["git", "push", ...]).returncode`, erroneously reporting "pushed successfully" in logs when the push was rejected.
- Hardened `mac_ebay_scanner/scanner.py`:
  - Added pre-push `fetch` and `rebase` against `origin/main`.
  - Added returncode checking with an automated `git pull --rebase` fallback attempt.
  - Added explicit stderr warning logs if a push fails.
- Rebased and published all pending scans on `encoder1` to GitHub Pages.
- Confirmed GitHub Pages deployment succeeded and live site reflects real-time status.

## Commands Run + Results
- `ssh encoder1 "systemctl --user status mac-ebay-scanner.service --no-pager"` -> Scanner confirmed active.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && git push origin main"` -> Failed with `[rejected] main -> main (fetch first)`.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && git pull --rebase origin main && git push origin main"` -> Successfully rebased and pushed 9 commits (`d7b29b2..3a8c7b3`).
- `pytest "D:\Code Projects\MacEbayScanner\tests" -v` -> 23 passed in 0.36s.
- `gh api repos/Buckwheet/MacEbayScanner/pages/builds/latest` -> Build completed with status `built`.
- `curl.exe -s "https://buckwheet.github.io/MacEbayScanner/"` -> Live site confirmed displaying: `Last Scan: 01:15 PM CST • Last Match: Nov 08, 08:28 AM CST`.

## Files Touched
- `mac_ebay_scanner/scanner.py`
- `PROJECT_STATE.md`

## Next 3 Actions
- [x] Diagnose root cause of 10:30 AM CST live site freeze.
- [x] Harden `update_public_site()` against upstream divergent commits and failed push masking.
- [x] Deploy to `encoder1`, verify service restart, and confirm live dashboard auto-updates.
