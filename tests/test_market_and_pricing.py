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
