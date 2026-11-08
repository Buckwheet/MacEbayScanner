from datetime import datetime
from zoneinfo import ZoneInfo
from mac_ebay_scanner.config import AppConfig
from mac_ebay_scanner.scanner import MacEbayScanner
from mac_ebay_scanner.storage import SeenStorage


def test_immediate_alert_window_logic(tmp_path):
    config = AppConfig(
        alert_window_start_hour=8,
        alert_window_end_hour=20,
        digest_hour=5,
        timezone_name="America/Chicago",
        db_path=tmp_path / "test_sched.db",
    )
    scanner = MacEbayScanner(config)
    tz = ZoneInfo("America/Chicago")

    # 07:59 AM CST -> Night/Queue window (False)
    dt_759 = datetime(2026, 11, 8, 7, 59, tzinfo=tz)
    assert scanner.is_immediate_alert_window(dt_759) is False

    # 08:00 AM CST -> Daytime Immediate Alert window (True)
    dt_800 = datetime(2026, 11, 8, 8, 0, tzinfo=tz)
    assert scanner.is_immediate_alert_window(dt_800) is True

    # 12:30 PM CST -> Daytime Immediate Alert window (True)
    dt_noon = datetime(2026, 11, 8, 12, 30, tzinfo=tz)
    assert scanner.is_immediate_alert_window(dt_noon) is True

    # 07:59 PM CST (19:59) -> Daytime Immediate Alert window (True)
    dt_1959 = datetime(2026, 11, 8, 19, 59, tzinfo=tz)
    assert scanner.is_immediate_alert_window(dt_1959) is True

    # 08:00 PM CST (20:00) -> Night/Queue window (False)
    dt_2000 = datetime(2026, 11, 8, 20, 0, tzinfo=tz)
    assert scanner.is_immediate_alert_window(dt_2000) is False

    # 05:00 AM CST -> Night/Digest hour (False for immediate, True for digest)
    dt_0500 = datetime(2026, 11, 8, 5, 0, tzinfo=tz)
    assert scanner.is_immediate_alert_window(dt_0500) is False
    assert dt_0500.hour == config.digest_hour


def test_overnight_queue_and_digest_tracking(tmp_path):
    db_file = tmp_path / "test_digest.db"
    storage = SeenStorage(db_path=db_file)

    # Record item overnight (notified=0, digest_sent=0)
    item = {
        "itemId": "v1|overnight_item_1|0",
        "title": "MacBook Pro M3 Max 128GB Overnight Deal",
        "price": {"value": "3999.00", "currency": "USD"},
    }
    storage.record_item(
        item=item,
        matched=True,
        notified=False,
        detected_model="MacBook Pro",
        detected_chip="Apple M3 Max",
        detected_ram="128GB",
        llm_analysis="Excellent 128GB RAM configuration under market average.",
    )

    queued = storage.get_queued_digest_items()
    assert len(queued) == 1
    assert queued[0]["item_id"] == "v1|overnight_item_1|0"
    assert queued[0]["llm_analysis"] == "Excellent 128GB RAM configuration under market average."

    # Mark digest sent
    storage.mark_digest_sent(["v1|overnight_item_1|0"])
    queued_after = storage.get_queued_digest_items()
    assert len(queued_after) == 0

    # Test state key-value store
    assert storage.get_state("last_5am_digest_date") is None
    storage.set_state("last_5am_digest_date", "2026-11-08")
    assert storage.get_state("last_5am_digest_date") == "2026-11-08"
