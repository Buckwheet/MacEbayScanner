import logging
from typing import Dict, Any, Optional, List
import requests

logger = logging.getLogger(__name__)


class PushbulletNotifier:
    PUSH_ENDPOINT = "https://api.pushbullet.com/v2/pushes"
    USER_ENDPOINT = "https://api.pushbullet.com/v2/users/me"

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = (api_token or "").strip()

    def is_configured(self) -> bool:
        return bool(self.api_token)

    def verify_token(self) -> Dict[str, Any]:
        """Verify the Pushbullet token and return user profile details."""
        if not self.is_configured():
            return {"valid": False, "error": "PUSHBULLET_API_TOKEN is not set."}

        headers = {
            "Access-Token": self.api_token,
            "Content-Type": "application/json",
        }
        try:
            resp = requests.get(self.USER_ENDPOINT, headers=headers, timeout=10)
            if resp.status_code == 200:
                user_info = resp.json()
                return {
                    "valid": True,
                    "name": user_info.get("name", "Unknown"),
                    "email": user_info.get("email", "Unknown"),
                }
            return {
                "valid": False,
                "error": f"Pushbullet authentication failed: HTTP {resp.status_code} - {resp.text}",
            }
        except requests.RequestException as e:
            return {"valid": False, "error": f"Network error connecting to Pushbullet: {e}"}

    def send_notification(
        self,
        title: str,
        body: str,
        url: Optional[str] = None,
    ) -> bool:
        """Send a push notification to Pushbullet."""
        if not self.is_configured():
            logger.warning("Pushbullet token not configured; skipping push notification.")
            return False

        headers = {
            "Access-Token": self.api_token,
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "type": "link" if url else "note",
            "title": title,
            "body": body,
        }
        if url:
            payload["url"] = url

        try:
            resp = requests.post(self.PUSH_ENDPOINT, headers=headers, json=payload, timeout=10)
            if resp.status_code in (200, 201):
                logger.info(f"Pushbullet notification sent: {title}")
                return True
            logger.error(f"Pushbullet push failed: HTTP {resp.status_code} - {resp.text}")
            return False
        except requests.RequestException as e:
            logger.error(f"Network error sending Pushbullet notification: {e}")
            return False

    def notify_match(
        self,
        item: Dict[str, Any],
        detected_model: str,
        detected_chip: str,
        detected_ram: str,
        market_avg: Optional[float] = None,
        discount_pct: Optional[float] = None,
        llm_analysis: Optional[str] = None,
    ) -> bool:
        """Format and send a structured match notification, highlighting below-market deals."""
        title_raw = item.get("title", "eBay Listing Match")
        price_obj = item.get("price", {})
        price_val = price_obj.get("value", "N/A")
        currency = price_obj.get("currency", "USD")
        item_url = item.get("itemWebUrl") or item.get("itemHref")
        condition = item.get("condition", "Not Specified")
        seller = (item.get("seller") or {}).get("username", "Unknown")

        is_deal = discount_pct is not None and discount_pct >= 15.0

        if is_deal:
            notif_title = f"🔥 DEAL ALERT: {detected_model} ({detected_chip}, {detected_ram}) - ${price_val} (-{discount_pct:.1f}% vs Market)"
        else:
            notif_title = f"eBay Alert: {detected_model} ({detected_chip}, {detected_ram}) - ${price_val}"

        body_lines = [
            f"Title: {title_raw}",
            f"Price: ${price_val} {currency}",
        ]
        if market_avg is not None:
            try:
                p_val = float(price_val)
                diff = market_avg - p_val
                pct = discount_pct if discount_pct is not None else ((diff / market_avg) * 100.0 if market_avg > 0 else 0.0)
                pct_str = f"(-{pct:.1f}%)" if diff > 0 else f"(+{abs(pct):.1f}%)"
                body_lines.append(f"Market Average: ${market_avg:.2f} {currency} {pct_str}")
            except Exception:
                body_lines.append(f"Market Average: ${market_avg:.2f} {currency}")

        body_lines.extend([
            f"Condition: {condition}",
            f"Seller: {seller}",
            f"Model: {detected_model}",
            f"Processor: {detected_chip}",
            f"Memory: {detected_ram}",
        ])

        if llm_analysis:
            body_lines.append(f"🤖 LOQ AI Assessment: {llm_analysis}")

        body = "\n".join(body_lines)
        return self.send_notification(title=notif_title, body=body, url=item_url)

    def notify_price_drop(
        self,
        item: Dict[str, Any],
        old_price: float,
        new_price: float,
        detected_model: str,
        detected_chip: str,
        detected_ram: str,
        market_avg: Optional[float] = None,
        llm_analysis: Optional[str] = None,
    ) -> bool:
        """Send notification when an existing watched listing drops in price."""
        title_raw = item.get("title", "Watched Listing")
        drop_amt = old_price - new_price
        drop_pct = (drop_amt / old_price) * 100.0
        currency = (item.get("price") or {}).get("currency", "USD")
        item_url = item.get("itemWebUrl") or item.get("itemHref")
        condition = item.get("condition", "Not Specified")

        notif_title = f"📉 PRICE DROP: {detected_model} ({detected_chip}) - Now ${new_price:.2f} (Down ${drop_amt:.2f} / -{drop_pct:.1f}%)"

        body_lines = [
            f"Title: {title_raw}",
            f"Old Price: ${old_price:.2f} {currency}",
            f"New Price: ${new_price:.2f} {currency}",
            f"Price Drop: -${drop_amt:.2f} (-{drop_pct:.1f}%)",
        ]
        if market_avg is not None:
            vs_market_pct = ((market_avg - new_price) / market_avg) * 100.0
            body_lines.append(f"Market Average: ${market_avg:.2f} ({vs_market_pct:.1f}% under market)")

        body_lines.extend([
            f"Condition: {condition}",
            f"Processor: {detected_chip}",
            f"Memory: {detected_ram}",
        ])
        if llm_analysis:
            body_lines.append(f"🤖 LOQ AI Assessment: {llm_analysis}")

        body = "\n".join(body_lines)
        return self.send_notification(title=notif_title, body=body, url=item_url)

    def notify_overnight_digest(
        self,
        items: List[Dict[str, Any]],
        market_stats: Dict[str, Dict[str, Any]],
        dashboard_url: str = "https://buckwheet.github.io/MacEbayScanner/",
    ) -> bool:
        """Format and dispatch a clean, concise 5:00 AM CST overnight summary linking to GitHub Pages."""
        count = len(items)
        if count == 0:
            title = "🌅 Overnight Mac Deals Digest"
            body = f"Overnight scan complete. All queries monitored—no new M3+ 128GB/256GB listings overnight.\n\nView live dashboard: {dashboard_url}"
            return self.send_notification(title=title, body=body, url=dashboard_url)

        # Sort items by best deal (lowest price or highest discount)
        sorted_deals = sorted(
            items,
            key=lambda x: (x.get("price") or 999999)
        )

        title = f"🌅 Overnight Mac Deals Digest ({count} Active)"
        body_lines = [
            f"Overnight scan complete. Tracking {count} matching M3+ 128GB/256GB Macs.\n",
            "🔥 Top Current Picks:",
        ]

        for idx, it in enumerate(sorted_deals[:3], 1):
            price_val = it.get("price", 0)
            m_chip = it.get("chip") or "M3+"
            m_mod = it.get("model") or "Mac"
            m_ram = "256GB" if "256" in (it.get("ram") or "") else "128GB"
            body_lines.append(f"{idx}. {m_mod} ({m_chip}, {m_ram}) - ${price_val:,.2f}")

        body_lines.append(f"\n📊 Full live dashboard & price trends:")
        body_lines.append(dashboard_url)

        body = "\n".join(body_lines)
        return self.send_notification(title=title, body=body, url=dashboard_url)
