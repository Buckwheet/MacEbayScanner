import base64
import time
import logging
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger(__name__)


class EbayClientError(Exception):
    pass


class EbayClient:
    OAUTH_ENDPOINT = "https://api.ebay.com/identity/v1/oauth2/token"
    BROWSE_SEARCH_ENDPOINT = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    BROWSE_ITEM_ENDPOINT = "https://api.ebay.com/buy/browse/v1/item"

    def __init__(self, client_id: str, client_secret: str, marketplace: str = "EBAY_US"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.marketplace = marketplace
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def get_access_token(self) -> str:
        """Fetch or refresh OAuth 2.0 application access token."""
        now = time.time()
        if self._access_token and now < (self._token_expires_at - 120):
            return self._access_token

        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_header = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_header}",
        }
        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        }

        try:
            resp = requests.post(self.OAUTH_ENDPOINT, headers=headers, data=data, timeout=15)
            if resp.status_code != 200:
                raise EbayClientError(f"OAuth token error [{resp.status_code}]: {resp.text}")

            res_json = resp.json()
            self._access_token = res_json["access_token"]
            expires_in = int(res_json.get("expires_in", 7200))
            self._token_expires_at = now + expires_in
            logger.debug(f"eBay OAuth token refreshed successfully (expires in {expires_in}s).")
            return self._access_token
        except requests.RequestException as e:
            raise EbayClientError(f"Network error during eBay OAuth authentication: {e}") from e

    def _get_api_headers(self) -> Dict[str, str]:
        token = self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self.marketplace,
            "Accept": "application/json",
            "Accept-Language": "en-US",
        }

    def search_items(self, query: str, limit: int = 50, sort: str = "newlyListed") -> List[Dict[str, Any]]:
        """Search items using eBay Browse API."""
        headers = self._get_api_headers()
        params = {
            "q": query,
            "limit": min(limit, 100),
            "sort": sort,
        }

        try:
            resp = requests.get(self.BROWSE_SEARCH_ENDPOINT, headers=headers, params=params, timeout=20)
            if resp.status_code == 429:
                logger.warning("eBay API rate limit hit (HTTP 429).")
                return []
            if resp.status_code != 200:
                logger.error(f"eBay Browse Search error [{resp.status_code}]: {resp.text}")
                return []

            data = resp.json()
            return data.get("itemSummaries", [])
        except requests.RequestException as e:
            logger.error(f"Network error during eBay search: {e}")
            return []

    def get_item_details(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full details for an item (including localizedAspects)."""
        headers = self._get_api_headers()
        # Item ID might be legacy or URL encoded, handle Browse API format
        encoded_id = requests.utils.quote(item_id, safe="")
        url = f"{self.BROWSE_ITEM_ENDPOINT}/{encoded_id}"

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"Could not fetch item details for {item_id}: [{resp.status_code}] {resp.text}")
                return None
            return resp.json()
        except requests.RequestException as e:
            logger.warning(f"Network error fetching item details for {item_id}: {e}")
            return None
