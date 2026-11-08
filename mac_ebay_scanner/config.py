import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")


@dataclass
class AppConfig:
    ebay_client_id: str = os.getenv("EBAY_CLIENT_ID", "")
    ebay_dev_id: str = os.getenv("EBAY_DEV_ID", "")
    ebay_client_secret: str = os.getenv("EBAY_CLIENT_SECRET", "")
    ebay_marketplace: str = os.getenv("EBAY_MARKETPLACE", "EBAY_US")
    pushbullet_api_token: str = os.getenv("PUSHBULLET_API_TOKEN", "")

    scan_interval_seconds: int = int(os.getenv("SCAN_INTERVAL_SECONDS", "180"))
    min_price: Optional[float] = float(os.getenv("MIN_PRICE")) if os.getenv("MIN_PRICE") else None
    max_price: Optional[float] = float(os.getenv("MAX_PRICE")) if os.getenv("MAX_PRICE") else None
    include_parts_or_repair: bool = os.getenv("INCLUDE_PARTS_OR_REPAIR", "false").lower() in ("true", "1", "yes")

    # Deal detection and price drop sensitivity
    deal_discount_percent: float = float(os.getenv("DEAL_DISCOUNT_PERCENT", "15.0"))
    price_drop_min_percent: float = float(os.getenv("PRICE_DROP_MIN_PERCENT", "3.0"))

    # Local LLM Decision Engine (Lenovo LOQ / Ollama)
    use_local_llm: bool = os.getenv("USE_LOCAL_LLM", "false").lower() in ("true", "1", "yes")
    local_llm_url: str = os.getenv("LOCAL_LLM_URL", "http://192.168.68.142:11434")
    local_llm_model: str = os.getenv("LOCAL_LLM_MODEL", "qwen2.5:7b")

    # Schedule: 8am - 8pm CST immediate, 5am CST digest
    timezone_name: str = os.getenv("TIMEZONE", "America/Chicago")
    alert_window_start_hour: int = int(os.getenv("ALERT_WINDOW_START_HOUR", "8"))
    alert_window_end_hour: int = int(os.getenv("ALERT_WINDOW_END_HOUR", "20"))
    digest_hour: int = int(os.getenv("DIGEST_HOUR", "5"))

    db_path: Path = BASE_DIR / "data" / "seen_items.db"

    search_queries: List[str] = field(default_factory=lambda: [
        'MacBook Pro 128GB',
        'Mac Studio 128GB',
        'MacBook Pro M3 Max 128GB',
        'MacBook Pro M4 Max 128GB',
        'Mac Studio M3 128GB',
        'Mac Studio M4 128GB',
        'Mac Studio 256GB',
        'MacBook Pro 256GB',
        'Mac Studio M4 256GB',
        'Mac Studio M4 Ultra 256GB',
        'Mac Studio 256GB Unified Memory',
    ])

    def validate(self, require_pushbullet: bool = False) -> List[str]:
        errors = []
        if not self.ebay_client_id:
            errors.append("EBAY_CLIENT_ID is missing.")
        if not self.ebay_client_secret:
            errors.append("EBAY_CLIENT_SECRET is missing.")
        if require_pushbullet and not self.pushbullet_api_token:
            errors.append("PUSHBULLET_API_TOKEN is missing.")
        return errors


def get_config() -> AppConfig:
    return AppConfig()
