import sqlite3
import json
import statistics
import re
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class SeenStorage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_items (
                    item_id TEXT PRIMARY KEY,
                    legacy_item_id TEXT,
                    title TEXT NOT NULL,
                    price REAL,
                    currency TEXT,
                    url TEXT,
                    condition TEXT,
                    seller TEXT,
                    model TEXT,
                    chip TEXT,
                    ram TEXT,
                    matched INTEGER DEFAULT 0,
                    notified INTEGER DEFAULT 0,
                    digest_sent INTEGER DEFAULT 0,
                    llm_analysis TEXT,
                    filter_reason TEXT,
                    first_seen_at TEXT NOT NULL,
                    last_updated_at TEXT,
                    raw_json TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    currency TEXT,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY (item_id) REFERENCES seen_items(item_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            # Check for missing columns in existing database
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(seen_items)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "digest_sent" not in columns:
                conn.execute("ALTER TABLE seen_items ADD COLUMN digest_sent INTEGER DEFAULT 0")
            if "llm_analysis" not in columns:
                conn.execute("ALTER TABLE seen_items ADD COLUMN llm_analysis TEXT")
            if "last_updated_at" not in columns:
                conn.execute("ALTER TABLE seen_items ADD COLUMN last_updated_at TEXT")
            if "filter_reason" not in columns:
                conn.execute("ALTER TABLE seen_items ADD COLUMN filter_reason TEXT")

            # Automatically normalize any legacy or verbose RAM strings
            conn.execute("UPDATE seen_items SET ram = '256GB' WHERE ram LIKE '%256%' AND ram != '256GB'")
            conn.execute("UPDATE seen_items SET ram = '128GB' WHERE ram LIKE '%128%' AND ram != '128GB'")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_seen_matched ON seen_items(matched);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_seen_legacy ON seen_items(legacy_item_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ph_item ON price_history(item_id);")
            conn.commit()

        # Re-evaluate any legacy items against latest filter criteria
        try:
            self.reconcile_all_items()
        except Exception as e:
            logger.warning(f"Could not reconcile items during init: {e}")

    def is_seen(self, item_id: str, legacy_item_id: Optional[str] = None) -> bool:
        """Check if an item has already been processed."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM seen_items WHERE item_id = ?", (item_id,))
            if cursor.fetchone():
                return True
            if legacy_item_id:
                cursor.execute("SELECT 1 FROM seen_items WHERE legacy_item_id = ?", (legacy_item_id,))
                if cursor.fetchone():
                    return True
        return False

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM seen_items WHERE item_id = ?", (item_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def record_item(
        self,
        item: Dict[str, Any],
        matched: bool = False,
        notified: bool = False,
        detected_model: Optional[str] = None,
        detected_chip: Optional[str] = None,
        detected_ram: Optional[str] = None,
        llm_analysis: Optional[str] = None,
        filter_reason: Optional[str] = None,
    ):
        """Record an item into the database and capture initial price in price_history."""
        item_id = item.get("itemId", "")
        legacy_id = item.get("legacyItemId")
        title = item.get("title", "")
        price_obj = item.get("price") or {}
        try:
            price = float(price_obj.get("value", 0))
        except (ValueError, TypeError):
            price = None
        currency = price_obj.get("currency", "USD")
        url = item.get("itemWebUrl") or item.get("itemHref", "")
        condition = item.get("condition")
        seller = (item.get("seller") or {}).get("username")
        now = datetime.now(timezone.utc).isoformat()
        raw_json = json.dumps(item)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO seen_items (
                    item_id, legacy_item_id, title, price, currency, url, condition, seller,
                    model, chip, ram, matched, notified, digest_sent, llm_analysis, filter_reason,
                    first_seen_at, last_updated_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    legacy_id,
                    title,
                    price,
                    currency,
                    url,
                    condition,
                    seller,
                    detected_model,
                    detected_chip,
                    detected_ram,
                    1 if matched else 0,
                    1 if notified else 0,
                    llm_analysis,
                    filter_reason,
                    now,
                    now,
                    raw_json,
                ),
            )
            if price is not None and matched:
                conn.execute(
                    "INSERT INTO price_history (item_id, price, currency, recorded_at) VALUES (?, ?, ?, ?)",
                    (item_id, price, currency, now),
                )
            conn.commit()

    def check_and_update_price(
        self,
        item_id: str,
        current_price: float,
        currency: str = "USD",
        min_pct_drop: float = 3.0,
    ) -> Tuple[bool, Optional[float], Optional[float], Optional[float]]:
        """
        Check if an existing matched item has experienced a price drop.
        Returns: (is_price_drop, old_price, drop_amount, drop_percentage)
        """
        existing = self.get_item(item_id)
        if not existing or existing.get("price") is None:
            return False, None, None, None

        old_price = float(existing["price"])
        now = datetime.now(timezone.utc).isoformat()

        # If the item is not a matched target machine, update its price in seen_items
        # but NEVER trigger price-drop alerts or append to price_history
        if not existing.get("matched"):
            if current_price != old_price:
                with self._get_connection() as conn:
                    conn.execute(
                        "UPDATE seen_items SET price = ?, currency = ?, last_updated_at = ? WHERE item_id = ?",
                        (current_price, currency, now, item_id),
                    )
                    conn.commit()
            return False, old_price, None, None

        if current_price < old_price:
            drop_amount = old_price - current_price
            drop_pct = (drop_amount / old_price) * 100.0

            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE seen_items SET price = ?, currency = ?, last_updated_at = ? WHERE item_id = ?",
                    (current_price, currency, now, item_id),
                )
                conn.execute(
                    "INSERT INTO price_history (item_id, price, currency, recorded_at) VALUES (?, ?, ?, ?)",
                    (item_id, current_price, currency, now),
                )
                conn.commit()

            if drop_pct >= min_pct_drop:
                return True, old_price, drop_amount, drop_pct

        elif current_price != old_price:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE seen_items SET price = ?, currency = ?, last_updated_at = ? WHERE item_id = ?",
                    (current_price, currency, now, item_id),
                )
                conn.execute(
                    "INSERT INTO price_history (item_id, price, currency, recorded_at) VALUES (?, ?, ?, ?)",
                    (item_id, current_price, currency, now),
                )
                conn.commit()

        return False, old_price, None, None

    def get_category_key(self, model: Optional[str], chip: Optional[str], ram: Optional[str] = None) -> str:
        """Normalize model, chip, and ram into standard market category key."""
        m_str = (model or "MacBook Pro").strip()
        c_str = (chip or "M3 Max").strip()
        r_str = "256GB" if ram and "256" in ram else "128GB"

        clean_model = "Mac Studio" if "studio" in m_str.lower() else "MacBook Pro"
        c_upper = c_str.upper()

        m_gen = re.search(r"\bM([3-9]|\d{2})\b", c_upper)
        gen = f"M{m_gen.group(1)}" if m_gen else "M3"

        if "ULTRA" in c_upper or (clean_model == "Mac Studio" and r_str == "256GB"):
            tier = "ULTRA"
        elif "MAX" in c_upper:
            tier = "MAX"
        elif "PRO" in c_upper:
            tier = "PRO"
        else:
            tier = "MAX"

        chip_norm = f"{gen} {tier}"
        return f"{clean_model} {chip_norm} {r_str}"

    def get_market_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Compute market pricing statistics by model and chip category from matched items."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT model, chip, ram, price
                FROM seen_items
                WHERE matched = 1 AND price IS NOT NULL AND price > 500
            """)
            rows = cursor.fetchall()

        grouped: Dict[str, List[float]] = {}
        for r in rows:
            cat = self.get_category_key(r["model"], r["chip"], r["ram"])
            grouped.setdefault(cat, []).append(float(r["price"]))

        stats: Dict[str, Dict[str, Any]] = {}
        for cat, prices in grouped.items():
            if not prices:
                continue
            stats[cat] = {
                "count": len(prices),
                "min": min(prices),
                "avg": round(statistics.mean(prices), 2),
                "median": round(statistics.median(prices), 2),
                "max": max(prices),
            }
        return stats

    def get_detailed_trend_analysis(self) -> List[Dict[str, Any]]:
        """Compute rich trend analysis metrics grouped by model combination."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT item_id, title, model, chip, ram, price, currency, condition, seller, url, first_seen_at
                FROM seen_items
                WHERE matched = 1 AND price IS NOT NULL AND price > 500
                ORDER BY price ASC
            """)
            rows = cursor.fetchall()

        by_cat: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            cat = self.get_category_key(r["model"], r["chip"], r["ram"])
            by_cat.setdefault(cat, []).append(dict(r))

        trends = []
        for cat, items in by_cat.items():
            if not items:
                continue
            prices = [float(it["price"]) for it in items]
            avg_price = round(statistics.mean(prices), 2)
            med_price = round(statistics.median(prices), 2)
            min_price = min(prices)
            max_price = max(prices)
            deal_threshold = round(avg_price * 0.85, 2)  # 15% discount threshold

            conditions: Dict[str, int] = {}
            for it in items:
                c = it.get("condition") or "Pre-owned"
                conditions[c] = conditions.get(c, 0) + 1

            storage_spread: Dict[str, int] = {}
            for it in items:
                t = (it.get("title") or "").upper()
                if "16TB" in t:
                    s = "16TB"
                elif "8TB" in t:
                    s = "8TB"
                elif "4TB" in t:
                    s = "4TB"
                elif "2TB" in t:
                    s = "2TB"
                elif "1TB" in t:
                    s = "1TB"
                elif "512GB" in t:
                    s = "512GB"
                else:
                    s = "Standard"
                storage_spread[s] = storage_spread.get(s, 0) + 1

            cheapest = items[0]
            parts = cat.split(" ")
            ram_val = parts[-1]
            chip_val = " ".join(parts[-3:-1])
            model_val = " ".join(parts[:-3])

            trends.append({
                "category": cat,
                "model": model_val,
                "chip": chip_val,
                "ram": ram_val,
                "count": len(items),
                "min": min_price,
                "avg": avg_price,
                "median": med_price,
                "max": max_price,
                "deal_threshold": deal_threshold,
                "conditions": conditions,
                "storage_spread": storage_spread,
                "best_deal": {
                    "title": cheapest["title"],
                    "price": cheapest["price"],
                    "url": cheapest["url"],
                    "seller": cheapest.get("seller", "eBay"),
                    "condition": cheapest.get("condition", "Used"),
                },
                "price_spread_pct": round(((max_price - min_price) / min_price) * 100.0, 1) if min_price > 0 else 0,
            })

        def sort_key(t):
            mod_prio = 0 if "MacBook" in t["model"] else 1
            ram_prio = 0 if "128" in t["ram"] else 1
            return (mod_prio, ram_prio, t["chip"], t["avg"])

        trends.sort(key=sort_key)
        return trends

    def evaluate_deal(
        self,
        model: str,
        chip: str,
        price: float,
        ram: Optional[str] = None,
        discount_threshold_pct: float = 15.0,
    ) -> Tuple[bool, Optional[float], Optional[float], int]:
        """Evaluate if a listing price is significantly below market average."""
        market_stats = self.get_market_statistics()
        cat_key = self.get_category_key(model, chip, ram)

        stat = market_stats.get(cat_key)
        if not stat or stat["count"] < 2:
            all_prices = []
            for s in market_stats.values():
                all_prices.extend([s["avg"]] * s["count"])
            if len(all_prices) >= 3:
                avg_val = statistics.mean(all_prices)
                sample_count = len(all_prices)
            else:
                return False, None, None, 0
        else:
            avg_val = stat["avg"]
            sample_count = stat["count"]

        if avg_val > 0 and price < avg_val:
            discount_pct = ((avg_val - price) / avg_val) * 100.0
            if discount_pct >= discount_threshold_pct:
                return True, avg_val, discount_pct, sample_count

        return False, avg_val, 0.0, sample_count

    def get_queued_digest_items(self) -> List[Dict[str, Any]]:
        """Retrieve matched items that were queued overnight and not yet notified or included in a digest."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT item_id, title, price, currency, url, model, chip, ram, condition, seller,
                       llm_analysis, first_seen_at
                FROM seen_items
                WHERE matched = 1 AND notified = 0 AND digest_sent = 0
                ORDER BY price ASC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def mark_digest_sent(self, item_ids: List[str]):
        """Mark items as included in a sent digest."""
        if not item_ids:
            return
        with self._get_connection() as conn:
            placeholders = ",".join("?" for _ in item_ids)
            conn.execute(
                f"UPDATE seen_items SET digest_sent = 1 WHERE item_id IN ({placeholders})",
                tuple(item_ids),
            )
            conn.commit()

    def get_state(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an app metadata state value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_state WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_state(self, key: str, value: str):
        """Set an app metadata state value."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_state (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, now),
            )
            conn.commit()

    def get_stats(self) -> Dict[str, int]:
        """Return total seen, matched, and notified item counts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(matched), SUM(notified) FROM seen_items")
            row = cursor.fetchone()
            total = row[0] or 0
            matched = row[1] or 0
            notified = row[2] or 0

            cursor.execute("SELECT COUNT(*) FROM price_history")
            ph_count = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(*) FROM seen_items WHERE matched = 1 AND notified = 0 AND digest_sent = 0")
            queued_count = cursor.fetchone()[0] or 0

            return {
                "total_seen": total,
                "total_matched": matched,
                "total_notified": notified,
                "price_history_records": ph_count,
                "overnight_queued_items": queued_count,
            }

    def get_matched_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent matched items."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT item_id, title, price, currency, url, model, chip, ram, condition, seller,
                       llm_analysis, first_seen_at
                FROM seen_items
                WHERE matched = 1
                ORDER BY first_seen_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(r) for r in cursor.fetchall()]

    def get_all_seen_items(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve all evaluated items (both matched and non-matched)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT item_id, title, price, currency, url, model, chip, ram, matched, condition, seller,
                       llm_analysis, filter_reason, first_seen_at, raw_json
                FROM seen_items
                ORDER BY matched DESC, first_seen_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(r) for r in cursor.fetchall()]

    def reconcile_all_items(self) -> Dict[str, int]:
        """Re-evaluate all items against current filter criteria to promote or demote as criteria evolve."""
        from .filter_engine import MacFilterEngine
        engine = MacFilterEngine()

        stats = {"promoted": 0, "demoted": 0, "updated_reason": 0}

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT item_id, title, price, currency, matched, filter_reason, raw_json FROM seen_items")
            rows = cursor.fetchall()

            for r in rows:
                raw_json = r["raw_json"]
                if not raw_json:
                    continue
                try:
                    item_data = json.loads(raw_json)
                except Exception:
                    continue

                res = engine.evaluate_item(item_data)
                curr_matched = r["matched"]

                if res.matched and curr_matched == 0:
                    conn.execute(
                        """
                        UPDATE seen_items
                        SET matched = 1,
                            model = ?,
                            chip = ?,
                            ram = ?,
                            filter_reason = NULL
                        WHERE item_id = ?
                        """,
                        (res.detected_model, res.detected_chip, res.detected_ram, r["item_id"]),
                    )
                    price = r["price"]
                    if price:
                        now = datetime.now(timezone.utc).isoformat()
                        conn.execute(
                            "INSERT OR IGNORE INTO price_history (item_id, price, currency, recorded_at) VALUES (?, ?, ?, ?)",
                            (r["item_id"], price, r["currency"] or "USD", now),
                        )
                    stats["promoted"] += 1

                elif not res.matched and curr_matched == 1:
                    conn.execute(
                        """
                        UPDATE seen_items
                        SET matched = 0,
                            model = NULL,
                            chip = NULL,
                            ram = NULL,
                            filter_reason = ?
                        WHERE item_id = ?
                        """,
                        (res.reason, r["item_id"]),
                    )
                    stats["demoted"] += 1

                elif not res.matched and curr_matched == 0:
                    if r["filter_reason"] != res.reason:
                        conn.execute(
                            "UPDATE seen_items SET filter_reason = ? WHERE item_id = ?",
                            (res.reason, r["item_id"]),
                        )
                        stats["updated_reason"] += 1

            conn.commit()
            if stats["promoted"] > 0 or stats["demoted"] > 0:
                logger.info(
                    f"Reconciliation complete: {stats['promoted']} promoted, {stats['demoted']} demoted."
                )
        return stats

    def reconcile_unmatched_items(self) -> int:
        """Re-evaluate all items previously recorded as matched=0 against current filter criteria."""
        return self.reconcile_all_items()["promoted"]
