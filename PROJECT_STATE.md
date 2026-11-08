# PROJECT_STATE.md

## Goal
Diagnose and fix GitHub Pages live site update freeze where "Last Scan" remained stuck at 10:30 AM CST.

## What Changed
- Diagnosed root cause: At 10:30 AM CST, commits were pushed from local to `origin/main`. On `encoder1`, the scanning service committed site doc updates on an older commit without rebasing first. GitHub rejected `git push origin main` because remote contained newer commits.
- Found silent failure in `mac_ebay_scanner/scanner.py`: `update_public_site()` did not inspect `subprocess.run(["git", "push", ...]).returncode`, erroneously logging "GitHub Pages updated and pushed successfully" even when git rejected the push.
- Hardened `mac_ebay_scanner/scanner.py`:
  - Added pre-push fetch/rebase against `origin/main`.
  - Added push return code check and automated `pull --rebase` retry on rejected push.
  - Added warning logging with stderr output if push fails.
- Rebased `encoder1` git repo onto `origin/main`, successfully pushing the accumulated 9 commits (up to 1:00 PM CST scan).
- Verified GitHub Pages build succeeded and live site now displays "Last Scan: 01:00 PM CST • Last Match: Nov 08, 08:28 AM CST".

## Commands Run + Results
- `ssh encoder1 "systemctl --user status mac-ebay-scanner.service --no-pager"` -> Verified scanner was actively running.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && git push origin main"` -> Failed with `[rejected] main -> main (fetch first)`.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && git pull --rebase origin main && git push origin main"` -> Rebased 9 commits and pushed `d7b29b2..3a8c7b3`.
- `gh api repos/Buckwheet/MacEbayScanner/pages/builds/latest` -> Status `built`.
- `curl.exe -s "https://buckwheet.github.io/MacEbayScanner/"` -> Verified live site now displays `01:00 PM CST`.
- `pytest "D:\Code Projects\MacEbayScanner\tests" -v` -> 23 passed in 0.36s.

## Files Touched
- `mac_ebay_scanner/scanner.py`
- `PROJECT_STATE.md`

## Next 3 Actions
- [x] Diagnose why live site showed 10:30 AM CST.
- [x] Rebase and push queued updates on `encoder1` and verify live GitHub Pages build.
- [x] Harden `scanner.py` with rebase sync and push verification, and deploy to `encoder1`.
