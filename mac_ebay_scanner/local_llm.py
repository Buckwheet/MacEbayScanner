import logging
import json
from typing import Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)


class LocalLLMVerifier:
    """Uses Ollama on LOQ (qwen2.5:7b) for intelligent qualitative listing assessment and value analysis."""

    def __init__(
        self,
        endpoint_url: str = "http://192.168.68.142:11434",
        model: str = "qwen2.5:7b",
        enabled: bool = False,
    ):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.model = model
        self.enabled = enabled

    def is_available(self) -> bool:
        """Check if LOQ Ollama server is reachable and model is loaded."""
        if not self.enabled:
            return False
        try:
            resp = requests.get(f"{self.endpoint_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                models = [m.get("name") for m in resp.json().get("models", [])]
                return any(self.model in m for m in models)
            return False
        except Exception:
            return False

    def evaluate_candidate(
        self,
        item: Dict[str, Any],
        detected_model: str,
        detected_chip: str,
        detected_ram: str,
        price: float,
        condition: str,
        market_avg: Optional[float] = None,
        discount_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate listing for qualitative value (storage upgrades, warranty, condition)
        grounded with live mathematical market baseline data.
        """
        if not self.enabled or not self.is_available():
            return {
                "approved": True,
                "analysis": "Heuristic match (Local LLM bypassed)",
                "confidence": 1.0,
            }

        title = item.get("title", "")
        seller = (item.get("seller") or {}).get("username", "Unknown")

        market_context = ""
        if market_avg is not None and discount_pct is not None:
            diff = market_avg - price
            status_str = f"${diff:.2f} ({discount_pct:.1f}%) BELOW average" if diff > 0 else f"${abs(diff):.2f} ({abs(discount_pct):.1f}%) ABOVE average"
            market_context = f"""
Mathematical Market Baseline:
- Category Average Price: ${market_avg:.2f}
- Listing Price: ${price:.2f}
- Price Position: {status_str}
"""

        prompt = f"""You are an Apple Silicon hardware valuation expert.
Target Criteria:
- Model: Apple MacBook Pro OR Mac Studio
- Processor: Apple Silicon M3, M4, or higher (e.g., M3 Max, M4 Max - Note: M4 Max is officially released). NEVER M1, M2, or Intel.
- Memory: 128GB of Unified Memory (Note: 128GB is RAM, NOT SSD storage).
- Condition: Must be a working computer, NOT for parts, NOT iCloud/MDM locked, NOT an accessory/case/box.

Listing Details:
- Title: {title}
- Price: ${price:.2f}
- Condition: {condition}
- Seller: {seller}
- Detected Specs: {detected_model}, {detected_chip}, {detected_ram}
{market_context}
Task:
1. Verify this is a working 128GB RAM Apple Silicon M3+ computer (not parts, lock, or accessory).
2. Assess qualitative value (look for SSD upgrades like 2TB/4TB/8TB, 100% battery, AppleCare+, or condition flaws).

Output strictly a JSON object:
{{
  "approved": true or false,
  "confidence": float between 0.0 and 1.0,
  "value_assessment": "1 sharp sentence evaluating the deal quality factoring in storage/condition relative to price",
  "is_exceptional_deal": true or false
}}"""

        try:
            resp = requests.post(
                f"{self.endpoint_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                raw_response = resp.json().get("response", "{}")
                data = json.loads(raw_response)
                logger.info(f"LOQ Local Model Valuation: {data}")
                return data
            logger.warning(f"LOQ Ollama returned HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"Error calling LOQ local model: {e}")

        return {
            "approved": True,
            "analysis": "Heuristic confirmed (LLM timeout)",
            "confidence": 0.8,
        }
