import pytest
from mac_ebay_scanner.filter_engine import MacFilterEngine


@pytest.fixture
def engine():
    return MacFilterEngine()


def test_positive_m4_max_macbook_pro(engine):
    summary = {
        "title": "Apple MacBook Pro M4 Max 128GB 1024GB | Refurbished - Good",
        "price": {"value": "4067.10", "currency": "USD"},
        "condition": "Very Good - Refurbished",
    }
    details = {
        "localizedAspects": [
            {"name": "Brand", "value": "Apple"},
            {"name": "Model", "value": "MacBook Pro M4 Max"},
            {"name": "Processor", "value": "Apple M4 Max"},
            {"name": "RAM", "value": "128GB"},
            {"name": "Storage Capacity", "value": "1024GB"},
        ]
    }
    res = engine.evaluate_item(summary, details)
    assert res.matched is True
    assert res.detected_model == "MacBook Pro"
    assert "M4" in res.detected_chip
    assert "128" in res.detected_ram


def test_positive_m3_max_macbook_pro_title_only(engine):
    summary = {
        "title": "Apple MacBook Pro 16-inch M3 Max 128GB Unified Memory 2TB SSD Space Black",
        "price": {"value": "3899.00", "currency": "USD"},
        "condition": "Used",
    }
    res = engine.evaluate_item(summary)
    assert res.matched is True
    assert res.detected_model == "MacBook Pro"
    assert "M3" in res.detected_chip


def test_positive_mac_studio_m4_max(engine):
    summary = {
        "title": "Apple Mac Studio M4 Max 128GB Unified Memory 1TB SSD",
        "price": {"value": "2999.00", "currency": "USD"},
    }
    res = engine.evaluate_item(summary)
    assert res.matched is True
    assert res.detected_model == "Mac Studio"


def test_reject_intel_with_16gb_ram(engine):
    summary = {
        "title": "Apple MacBook Pro Retina 15\" i7 Laptop • TouchBar • OS 2024 Sequoia • 16 GB RAM",
        "price": {"value": "598.50", "currency": "USD"},
    }
    res = engine.evaluate_item(summary)
    assert res.matched is False


def test_reject_older_macbook_with_128gb_ssd_trap(engine):
    # Older Intel Mac with 128GB SSD
    summary = {
        "title": "Apple MacBook Pro 13\" Core i5 2.3GHz 8GB RAM 128GB SSD Space Gray",
        "price": {"value": "299.00", "currency": "USD"},
    }
    res = engine.evaluate_item(summary)
    assert res.matched is False


def test_reject_m1_max_128gb_ssd_or_ram(engine):
    summary = {
        "title": "Apple MacBook Pro 16\" M1 Max 64GB RAM 1TB SSD",
        "price": {"value": "1800.00", "currency": "USD"},
    }
    res = engine.evaluate_item(summary)
    assert res.matched is False


def test_reject_m2_max_96gb(engine):
    summary = {
        "title": "Apple MacBook Pro 16\" M2 Max 96GB Unified Memory 1TB SSD",
        "price": {"value": "2400.00", "currency": "USD"},
    }
    res = engine.evaluate_item(summary)
    assert res.matched is False


def test_reject_m3_pro_with_36gb_ram(engine):
    summary = {
        "title": "Apple MacBook Pro 16\" M3 Pro 36GB RAM 512GB SSD Space Black",
        "price": {"value": "2199.00", "currency": "USD"},
    }
    res = engine.evaluate_item(summary)
    assert res.matched is False


def test_reject_case_accessory(engine):
    summary = {
        "title": "Hard Case Cover for Apple MacBook Pro 16\" M3 Max 128GB A2991",
        "price": {"value": "24.99", "currency": "USD"},
    }
    res = engine.evaluate_item(summary)
    assert res.matched is False
    assert "accessory" in res.reason.lower()


def test_reject_parts_only_by_default(engine):
    summary = {
        "title": "Apple MacBook Pro 16\" M3 Max 128GB FOR PARTS ONLY Water Damage",
        "price": {"value": "750.00", "currency": "USD"},
        "condition": "For parts or not working",
    }
    res = engine.evaluate_item(summary)
    assert res.matched is False


def test_positive_mac_studio_256gb_ram(engine):
    summary = {
        "title": "Apple Mac Studio M4 Ultra 256GB Unified Memory 2TB SSD Desktop",
        "price": {"value": "8999.00", "currency": "USD"},
    }
    details = {
        "localizedAspects": [
            {"name": "Brand", "value": "Apple"},
            {"name": "Model", "value": "Mac Studio"},
            {"name": "Processor", "value": "Apple M4 Ultra"},
            {"name": "RAM Size", "value": "256 GB"},
        ]
    }
    res = engine.evaluate_item(summary, details)
    assert res.matched is True
    assert res.detected_model == "Mac Studio"
    assert "256" in res.detected_ram


def test_reject_256gb_ssd_with_8gb_ram_trap(engine):
    summary = {
        "title": "Apple MacBook Pro 14\" M3 8GB RAM 256GB SSD Space Gray A2992",
        "price": {"value": "1199.00", "currency": "USD"},
    }
    res = engine.evaluate_item(summary)
    assert res.matched is False


def test_reject_256gb_ssd_in_aspect_with_low_ram(engine):
    summary = {
        "title": "Apple MacBook Pro 16\" M3 Max Space Black",
        "price": {"value": "2600.00", "currency": "USD"},
    }
    details = {
        "localizedAspects": [
            {"name": "Model", "value": "MacBook Pro"},
            {"name": "Processor", "value": "Apple M3 Max"},
            {"name": "RAM Size", "value": "36 GB"},
            {"name": "SSD Capacity", "value": "256 GB"},
        ]
    }
    res = engine.evaluate_item(summary, details)
    assert res.matched is False
    assert "36" in res.reason or "not 128GB" in res.reason
