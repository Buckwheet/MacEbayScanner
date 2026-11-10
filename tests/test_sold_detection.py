import pytest
import sqlite3
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from pathlib import Path

from mac_ebay_scanner.ebay_client import EbayClient
from mac_ebay_scanner.storage import SeenStorage
from mac_ebay_scanner.site_generator import generate_static_site
from mac_ebay_scanner.scanner import MacEbayScanner
from mac_ebay_scanner.config import AppConfig


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_sold.db"
    return SeenStorage(db_file)


def test_ebay_client_check_item_availability_in_stock():
    client = EbayClient(client_id="dummy", client_secret="dummy")
    with patch.object(client, "get_item_details") as mock_details:
        mock_details.return_value = {
            "itemId": "v1|123456|0",
            "title": "MacBook Pro 16 M4 Max 128GB",
            "estimatedAvailabilities": [
                {
                    "estimatedAvailabilityStatus": "IN_STOCK",
                    "estimatedAvailableQuantity": 1,
                    "estimatedRemainingQuantity": 1,
                    "estimatedSoldQuantity": 0,
                }
            ],
            "itemEndDate": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat().replace("+00:00", "Z"),
        }
        res = client.check_item_availability("v1|123456|0")
        assert res["is_sold"] is False
        assert res["reason"] == "ACTIVE"
        assert res["remaining_quantity"] == 1


def test_ebay_client_check_item_availability_out_of_stock():
    client = EbayClient(client_id="dummy", client_secret="dummy")
    with patch.object(client, "get_item_details") as mock_details:
        mock_details.return_value = {
            "itemId": "v1|123456|0",
            "title": "MacBook Pro 16 M4 Max 128GB",
            "estimatedAvailabilities": [
                {
                    "estimatedAvailabilityStatus": "OUT_OF_STOCK",
                    "estimatedAvailableQuantity": 0,
                    "estimatedRemainingQuantity": 0,
                    "estimatedSoldQuantity": 2,
                }
            ],
        }
        res = client.check_item_availability("v1|123456|0")
        assert res["is_sold"] is True
        assert res["reason"] == "OUT_OF_STOCK"
        assert res["sold_quantity"] == 2


def test_ebay_client_check_item_availability_not_found_404():
    client = EbayClient(client_id="dummy", client_secret="dummy")
    with patch.object(client, "get_item_details") as mock_details:
        mock_details.return_value = None
        res = client.check_item_availability("v1|notfound|0")
        assert res["is_sold"] is True
        assert res["reason"] == "NOT_FOUND_OR_ENDED"


def test_ebay_client_check_item_availability_expired_end_date():
    client = EbayClient(client_id="dummy", client_secret="dummy")
    with patch.object(client, "get_item_details") as mock_details:
        mock_details.return_value = {
            "itemId": "v1|ended|0",
            "title": "Mac Studio M4 Max 128GB",
            "estimatedAvailabilities": [
                {
                    "estimatedAvailabilityStatus": "IN_STOCK",
                    "estimatedAvailableQuantity": 1,
                    "estimatedRemainingQuantity": 1,
                }
            ],
            "itemEndDate": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
        }
        res = client.check_item_availability("v1|ended|0")
        assert res["is_sold"] is True
        assert res["reason"] == "LISTING_ENDED"


def test_storage_sold_tracking(temp_db):
    item1 = {
        "itemId": "v1|item1|0",
        "title": "Apple MacBook Pro 16 M4 Max 128GB",
        "price": {"value": "3999.00", "currency": "USD"},
        "itemWebUrl": "https://ebay.com/itm/item1",
    }
    item2 = {
        "itemId": "v1|item2|0",
        "title": "Apple Mac Studio M4 Max 128GB",
        "price": {"value": "2499.00", "currency": "USD"},
        "itemWebUrl": "https://ebay.com/itm/item2",
    }

    temp_db.record_item(item1, matched=True, detected_model="MacBook Pro", detected_chip="M4 Max", detected_ram="128GB")
    temp_db.record_item(item2, matched=True, detected_model="Mac Studio", detected_chip="M4 Max", detected_ram="128GB")

    # Both should be active matches initially
    active_matches = temp_db.get_matched_items(include_sold=False)
    assert len(active_matches) == 2

    # Mark item1 as sold
    marked = temp_db.mark_item_sold("v1|item1|0")
    assert marked is True

    # Active matches should now only have item2
    active_matches = temp_db.get_matched_items(include_sold=False)
    assert len(active_matches) == 1
    assert active_matches[0]["item_id"] == "v1|item2|0"

    # All matches should still show both
    all_matches = temp_db.get_matched_items(include_sold=True)
    assert len(all_matches) == 2

    # Sold items should contain item1
    sold_items = temp_db.get_sold_items()
    assert len(sold_items) == 1
    assert sold_items[0]["item_id"] == "v1|item1|0"
    assert sold_items[0]["is_sold"] == 1

    # Reactivate item1
    temp_db.mark_item_active("v1|item1|0")
    assert len(temp_db.get_matched_items(include_sold=False)) == 2
    assert len(temp_db.get_sold_items()) == 0

    # Test permanent deletion of sold item
    temp_db.mark_item_sold("v1|item1|0")
    deleted_count = temp_db.delete_sold_items()
    assert deleted_count == 1
    assert temp_db.get_item("v1|item1|0") is None
    assert len(temp_db.get_matched_items(include_sold=True)) == 1


def test_site_generator_with_sold_items(temp_db, tmp_path):
    item_active = {
        "itemId": "v1|active1|0",
        "title": "Apple MacBook Pro 16 M4 Max 128GB",
        "price": {"value": "3999.00", "currency": "USD"},
        "itemWebUrl": "https://ebay.com/itm/active1",
    }
    item_sold = {
        "itemId": "v1|sold1|0",
        "title": "Apple MacBook Pro 16 M3 Max 128GB",
        "price": {"value": "2999.00", "currency": "USD"},
        "itemWebUrl": "https://ebay.com/itm/sold1",
    }
    temp_db.record_item(item_active, matched=True, detected_model="MacBook Pro", detected_chip="M4 Max", detected_ram="128GB")
    temp_db.record_item(item_sold, matched=True, detected_model="MacBook Pro", detected_chip="M3 Max", detected_ram="128GB")
    temp_db.mark_item_sold("v1|sold1|0")

    docs_dir = tmp_path / "docs"
    generate_static_site(temp_db, docs_dir)

    import json
    data_file = docs_dir / "data.json"
    assert data_file.exists()
    data = json.loads(data_file.read_text(encoding="utf-8"))

    assert data["total_matches"] == 1
    assert data["total_sold"] == 1
    sold_entries = [it for it in data["items"] if it.get("is_sold")]
    assert len(sold_entries) == 1
    assert sold_entries[0]["item_id"] == "v1|sold1|0"

    html = (docs_dir / "index.html").read_text(encoding="utf-8")
    assert "Active Matches (" in html
    assert "Sold / Ended (" in html


def test_scanner_check_sold_items(temp_db, monkeypatch):
    config = AppConfig()
    config.db_path = temp_db.db_path
    scanner = MacEbayScanner(config)

    item1 = {
        "itemId": "v1|check1|0",
        "title": "MacBook Pro 16 M4 Max 128GB",
        "price": {"value": "3999.00", "currency": "USD"},
    }
    temp_db.record_item(item1, matched=True, detected_model="MacBook Pro", detected_chip="M4 Max", detected_ram="128GB")

    # Mock check_item_availability returning out of stock
    scanner.ebay_client.check_item_availability = MagicMock(return_value={
        "is_sold": True,
        "reason": "OUT_OF_STOCK",
        "remaining_quantity": 0,
        "sold_quantity": 1,
    })

    res = scanner.check_sold_items(max_items=5)
    assert res["checked"] == 1
    assert res["sold_detected"] == 1

    # Verify item is marked as sold in DB
    item_in_db = temp_db.get_item("v1|check1|0")
    assert item_in_db["is_sold"] == 1
    assert item_in_db["sold_at"] is not None
