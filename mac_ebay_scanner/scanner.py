import time
import logging
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from typing import Optional, List, Dict, Any
from .config import AppConfig
from .ebay_client import EbayClient
from .filter_engine import MacFilterEngine
from .notifier import PushbulletNotifier
from .storage import SeenStorage
from .local_llm import LocalLLMVerifier

logger = logging.getLogger(__name__)


class MacEbayScanner:
    def __init__(self, config: AppConfig):
        self.config = config
        self.ebay_client = EbayClient(
            client_id=config.ebay_client_id,
            client_secret=config.ebay_client_secret,
            marketplace=config.ebay_marketplace,
        )
        self.filter_engine = MacFilterEngine(
            min_price=config.min_price,
            max_price=config.max_price,
            include_parts=config.include_parts_or_repair,
        )
        self.notifier = PushbulletNotifier(api_token=config.pushbullet_api_token)
        self.storage = SeenStorage(db_path=config.db_path)
        self.llm_verifier = LocalLLMVerifier(
            endpoint_url=config.local_llm_url,
            model=config.local_llm_model,
            enabled=config.use_local_llm,
        )
        self._stop_requested = False

        try:
            self.tz = ZoneInfo(config.timezone_name)
        except Exception:
            self.tz = ZoneInfo("America/Chicago")

    def get_cst_now(self) -> datetime:
        """Return current datetime in configured timezone (CST)."""
        return datetime.now(self.tz)

    def is_immediate_alert_window(self, dt: Optional[datetime] = None) -> bool:
        """
        Check if datetime falls within the 8:00 AM - 8:00 PM CST daytime window.
        Returns True if immediate individual alerts should be dispatched.
        """
        current_dt = dt or self.get_cst_now()
        hour = current_dt.hour
        return self.config.alert_window_start_hour <= hour < self.config.alert_window_end_hour

    def check_and_send_5am_digest(self) -> bool:
        """
        Check if it's the 5:00 AM CST window and send overnight summary digest if not already sent today.
        """
        now_cst = self.get_cst_now()
        if now_cst.hour != self.config.digest_hour:
            return False

        today_str = now_cst.strftime("%Y-%m-%d")
        last_sent_date = self.storage.get_state("last_5am_digest_date")
        if last_sent_date == today_str:
            return False

        logger.info(f"5:00 AM CST Digest trigger: preparing overnight summary for {today_str}...")
        # Update public site before sending digest
        self.update_public_site()

        queued_items = self.storage.get_queued_digest_items()
        market_stats = self.storage.get_market_statistics()

        sent = False
        if self.notifier.is_configured():
            sent = self.notifier.notify_overnight_digest(queued_items, market_stats)
            if sent:
                logger.info(f"5:00 AM CST overnight digest sent successfully ({len(queued_items)} items).")
                self.storage.mark_digest_sent([it["item_id"] for it in queued_items])
                self.storage.set_state("last_5am_digest_date", today_str)
        return sent

    def update_public_site(self):
        """Regenerate static dashboard and push to GitHub Pages."""
        try:
            from .site_generator import generate_static_site
            docs_dir = self.config.db_path.parent.parent / "docs"
            generate_static_site(self.storage, docs_dir)

            import subprocess
            repo_dir = str(self.config.db_path.parent.parent)
            subprocess.run(["git", "add", "docs/"], cwd=repo_dir, capture_output=True, timeout=10)
            res = subprocess.run(
                ["git", "commit", "-m", "Auto-update live Mac listings [skip ci]"],
                cwd=repo_dir,
                capture_output=True,
                timeout=10,
            )
            if res.returncode == 0:
                subprocess.run(["git", "push", "origin", "main"], cwd=repo_dir, capture_output=True, timeout=20)
                logger.info("GitHub Pages updated and pushed successfully.")
        except Exception as e:
            logger.warning(f"Could not auto-publish to GitHub Pages: {e}")

    def stop(self):
        self._stop_requested = True

    def scan_once(self) -> Dict[str, int]:
        """Execute a single scanning pass across all configured queries."""
        now_cst = self.get_cst_now()
        is_immediate = self.is_immediate_alert_window(now_cst)

        # Check 5am digest window
        self.check_and_send_5am_digest()

        total_found = 0
        new_items = 0
        matches_found = 0
        price_drops_detected = 0
        notifications_sent = 0
        queued_overnight = 0

        logger.info(
            f"Starting scan across {len(self.config.search_queries)} queries "
            f"[{now_cst.strftime('%I:%M %p %Z')} | Mode: {'Immediate Daytime' if is_immediate else 'Overnight Queue'}]..."
        )

        for query in self.config.search_queries:
            if self._stop_requested:
                break

            logger.debug(f"Searching eBay: '{query}'")
            items = self.ebay_client.search_items(query=query, limit=50)
            total_found += len(items)

            for item in items:
                if self._stop_requested:
                    break

                item_id = item.get("itemId")
                legacy_id = item.get("legacyItemId")
                if not item_id:
                    continue

                price_obj = item.get("price") or {}
                try:
                    current_price = float(price_obj.get("value", 0))
                except (ValueError, TypeError):
                    current_price = 0.0
                currency = price_obj.get("currency", "USD")

                # Check if item is already seen
                if self.storage.is_seen(item_id, legacy_id):
                    is_drop, old_price, drop_amt, drop_pct = self.storage.check_and_update_price(
                        item_id=item_id,
                        current_price=current_price,
                        currency=currency,
                        min_pct_drop=self.config.price_drop_min_percent,
                    )
                    if is_drop and old_price is not None:
                        price_drops_detected += 1
                        existing_rec = self.storage.get_item(item_id) or {}
                        det_model = existing_rec.get("model") or "MacBook Pro"
                        det_chip = existing_rec.get("chip") or "M3+"
                        det_ram = existing_rec.get("ram") or "128GB"

                        is_deal, mkt_avg, disc_pct, _ = self.storage.evaluate_deal(
                            model=det_model,
                            chip=det_chip,
                            price=current_price,
                            ram=det_ram,
                            discount_threshold_pct=self.config.deal_discount_percent,
                        )

                        logger.info(
                            f"PRICE DROP DETECTED: {item.get('title')} | "
                            f"${old_price:.2f} -> ${current_price:.2f} (-{drop_pct:.1f}%)"
                        )

                        if is_immediate and self.notifier.is_configured():
                            sent = self.notifier.notify_price_drop(
                                item=item,
                                old_price=old_price,
                                new_price=current_price,
                                detected_model=det_model,
                                detected_chip=det_chip,
                                detected_ram=det_ram,
                                market_avg=mkt_avg,
                            )
                            if sent:
                                notifications_sent += 1
                        else:
                            queued_overnight += 1
                    continue

                new_items += 1
                title = item.get("title", "")

                # Step 1: Preliminary evaluation using summary
                prelim = self.filter_engine.evaluate_item(item)

                item_details = None
                final_res = prelim

                if prelim.matched or (("128" in title.lower() or "256" in title.lower()) and ("mac" in title.lower() or "apple" in title.lower())):
                    item_details = self.ebay_client.get_item_details(item_id)
                    final_res = self.filter_engine.evaluate_item(item, item_details)

                if final_res.matched:
                    model_name = final_res.detected_model or "Mac"
                    chip_name = final_res.detected_chip or "M3+"
                    ram_name = final_res.detected_ram or "128GB"

                    # Evaluate deal against market baseline
                    is_deal, mkt_avg, discount_pct, sample_count = self.storage.evaluate_deal(
                        model=model_name,
                        chip=chip_name,
                        price=current_price,
                        ram=ram_name,
                        discount_threshold_pct=self.config.deal_discount_percent,
                    )

                    # Optional LOQ Local Model Qualitative Assessment
                    llm_analysis_text = None
                    if self.llm_verifier.enabled:
                        llm_eval = self.llm_verifier.evaluate_candidate(
                            item=item,
                            detected_model=model_name,
                            detected_chip=chip_name,
                            detected_ram=ram_name,
                            price=current_price,
                            condition=item.get("condition", "Used"),
                            market_avg=mkt_avg,
                            discount_pct=discount_pct if is_deal else None,
                        )
                        if not llm_eval.get("approved", True):
                            logger.info(
                                f"LOQ LLM REJECTED listing: '{title}' - {llm_eval.get('analysis')}"
                            )
                            self.storage.record_item(item=item, matched=False, notified=False)
                            continue

                        llm_analysis_text = llm_eval.get("value_assessment") or llm_eval.get("analysis")

                    matches_found += 1
                    deal_tag = f" [🔥 DEAL: -{discount_pct:.1f}% vs ${mkt_avg:.2f} avg]" if is_deal else ""
                    logger.info(
                        f"MATCH FOUND: {title} | {model_name} | {chip_name} | {ram_name} | "
                        f"Price: ${current_price:.2f} {currency}{deal_tag}"
                    )

                    notified = False
                    if is_immediate:
                        if self.notifier.is_configured():
                            notified = self.notifier.notify_match(
                                item=item,
                                detected_model=model_name,
                                detected_chip=chip_name,
                                detected_ram=ram_name,
                                market_avg=mkt_avg,
                                discount_pct=discount_pct if is_deal else None,
                                llm_analysis=llm_analysis_text,
                            )
                            if notified:
                                notifications_sent += 1
                    else:
                        queued_overnight += 1
                        logger.info(f"Overnight window active (8pm-8am CST): queued match for 5:00 AM summary.")

                    self.storage.record_item(
                        item=item,
                        matched=True,
                        notified=notified,
                        detected_model=model_name,
                        detected_chip=chip_name,
                        detected_ram=ram_name,
                        llm_analysis=llm_analysis_text,
                    )
                else:
                    logger.debug(f"Filtered out: '{title}' - Reason: {final_res.reason}")
                    self.storage.record_item(item=item, matched=False, notified=False)

        # If new matches or price drops were detected, refresh the live website
        if matches_found > 0 or price_drops_detected > 0:
            self.update_public_site()

        stats = {
            "total_items_examined": total_found,
            "new_items_processed": new_items,
            "matches_found": matches_found,
            "price_drops_detected": price_drops_detected,
            "notifications_sent": notifications_sent,
            "queued_overnight": queued_overnight,
            "is_daytime_window": is_immediate,
        }
        logger.info(
            f"Scan pass complete: {new_items} new items, {matches_found} matches, "
            f"{notifications_sent} immediate alerts sent, {queued_overnight} queued for 5am digest."
        )
        return stats

    def run_daemon(self, interval_seconds: Optional[int] = None):
        """Continuously run scanner at interval until stopped."""
        interval = interval_seconds or self.config.scan_interval_seconds
        logger.info(f"Starting MacEbayScanner daemon loop (interval: {interval}s)...")

        while not self._stop_requested:
            start_time = time.time()
            try:
                self.scan_once()
            except Exception as e:
                logger.error(f"Error occurred during scan cycle: {e}", exc_info=True)

            elapsed = time.time() - start_time
            sleep_time = max(1.0, interval - elapsed)

            step = 1.0
            slept = 0.0
            while slept < sleep_time and not self._stop_requested:
                time.sleep(min(step, sleep_time - slept))
                slept += step

        logger.info("Scanner daemon terminated cleanly.")
