import pytest
from pathlib import Path
from mac_ebay_scanner.storage import SeenStorage


@pytest.fixture
def temp_storage(tmp_path):
    db_file = tmp_path / "test_seen.db"
    return SeenStorage(db_path=db_file)


def test_price_history_and_drop_detection(temp_storage):
    item = {
        "itemId": "v1|123456789|0",
        "title": "Apple MacBook Pro 16\" M3 Max 128GB RAM 1TB SSD",
        "price": {"value": "4500.00", "currency": "USD"},
    }

    # Record initial item
    temp_storage.record_item(
        item=item,
        matched=True,
        notified=True,
        detected_model="MacBook Pro",
        detected_chip="Apple M3 Max",
        detected_ram="128GB",
    )

    # Price unchanged
    is_drop, old_p, drop_amt, drop_pct = temp_storage.check_and_update_price("v1|123456789|0", 4500.00)
    assert is_drop is False

    # Tiny price drop below 3% threshold
    is_drop, old_p, drop_amt, drop_pct = temp_storage.check_and_update_price("v1|123456789|0", 4450.00, min_pct_drop=3.0)
    assert is_drop is False

    # Major price drop from $4450 to $3800 (>14% drop)
    is_drop, old_p, drop_amt, drop_pct = temp_storage.check_and_update_price("v1|123456789|0", 3800.00, min_pct_drop=3.0)
    assert is_drop is True
    assert old_p == 4450.00
    assert drop_amt == 650.00
    assert round(drop_pct, 1) == 14.6


def test_market_statistics_and_deal_evaluation(temp_storage):
    # Seed multiple items to establish market average
    prices = [5000.00, 5200.00, 4800.00, 5400.00]  # Average = 5100.00
    for idx, p in enumerate(prices):
        temp_storage.record_item(
            item={
                "itemId": f"v1|seed_{idx}|0",
                "title": f"MacBook Pro M3 Max 128GB #{idx}",
                "price": {"value": str(p), "currency": "USD"},
            },
            matched=True,
            detected_model="MacBook Pro",
            detected_chip="Apple M3 Max",
            detected_ram="128GB",
        )

    stats = temp_storage.get_market_statistics()
    cat_key = "MacBook Pro M3 MAX 128GB"
    assert cat_key in stats
    assert stats[cat_key]["count"] == 4
    assert stats[cat_key]["avg"] == 5100.00

    # Normal price (no deal)
    is_deal, avg_p, disc_pct, count = temp_storage.evaluate_deal("MacBook Pro", "Apple M3 Max", 4800.00, discount_threshold_pct=15.0)
    assert is_deal is False

    # Steal deal price ($3900 is ~23.5% below $5100 average)
    is_deal, avg_p, disc_pct, count = temp_storage.evaluate_deal("MacBook Pro", "Apple M3 Max", 3900.00, discount_threshold_pct=15.0)
    assert is_deal is True
    assert avg_p == 5100.00
    assert disc_pct > 20.0


def test_unmatched_item_never_triggers_price_drop(temp_storage):
    item = {
        "itemId": "v1|neo_999|0",
        "title": "New 2026 Apple MacBook Neo 13\" A18 Pro 8GB RAM 256GB SSD",
        "price": {"value": "664.99", "currency": "USD"},
    }

    # Record unmatched item
    temp_storage.record_item(
        item=item,
        matched=False,
        filter_reason="Not a MacBook Pro or Mac Studio",
    )

    # Price drops from $664.99 to $630.99 (>5% drop)
    is_drop, old_p, drop_amt, drop_pct = temp_storage.check_and_update_price("v1|neo_999|0", 630.99, min_pct_drop=3.0)
    assert is_drop is False
    assert old_p == 664.99

    # Verify no price history was recorded for unmatched items
    with temp_storage._get_connection() as conn:
        ph = conn.execute("SELECT count(*) as c FROM price_history WHERE item_id = 'v1|neo_999|0'").fetchone()["c"]
        assert ph == 0


def test_llm_hardware_metrics_calculation():
    from mac_ebay_scanner.site_generator import calculate_llm_hardware_metrics

    # Test M3 Max (400 GB/s on 128GB tier)
    m3 = calculate_llm_hardware_metrics("MacBook Pro", "M3 Max", "16-core 40-core GPU 128GB", 3690.0)
    assert m3["bandwidth_gb_s"] == 400
    assert m3["tok_s_27b"] == 16.7
    assert m3["tok_s_70b"] == 7.1
    assert m3["llm_value_score"] == 4.53

    # Test M4 Max (546 GB/s)
    m4 = calculate_llm_hardware_metrics("MacBook Pro", "M4 Max", "Apple M4 Max 128GB RAM", 4067.10)
    assert m4["bandwidth_gb_s"] == 546
    assert m4["tok_s_27b"] == 22.8
    assert m4["llm_value_score"] == 5.61

    # Test M3 Ultra (800 GB/s)
    ultra = calculate_llm_hardware_metrics("Mac Studio", "M3 Ultra", "Mac Studio M3 Ultra 256GB", 8850.0)
    assert ultra["bandwidth_gb_s"] == 800
    assert ultra["tok_s_27b"] == 33.3
    assert ultra["tok_s_70b"] == 14.3
    assert ultra["llm_value_score"] == 3.76
