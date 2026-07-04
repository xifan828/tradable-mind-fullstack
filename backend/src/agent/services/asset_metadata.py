"""Asset metadata service for fetching and caching symbol metadata from TwelveData."""

from twelvedata import TDClient
from typing import Optional
from dataclasses import dataclass
import os
import re
from functools import lru_cache
from dotenv import load_dotenv


@dataclass
class AssetMetadata:
    """Metadata for a trading asset."""
    symbol: str
    decimal_places: int
    exchange: Optional[str]
    asset_type: str  # "forex", "forex_jpy", "crypto", "stock", "commodity", "etf", "index"


class AssetMetadataService:
    """Service to fetch and cache asset metadata from TwelveData."""

    # Default decimal places by asset type (fallback)
    DEFAULT_DECIMALS = {
        "forex": 4,      # Most forex pairs (EUR/USD, GBP/USD)
        "forex_jpy": 2,  # JPY pairs (USD/JPY, EUR/JPY)
        "forex_cnh": 4,  # CNH pairs
        "crypto": 2,     # Crypto (BTC/USD, ETH/USD)
        "stock": 2,      # Stocks (AAPL, MSFT)
        "commodity": 2,  # Gold, Silver, etc.
        "etf": 2,        # ETFs
        "index": 2,      # Indices
    }

    # Symbol patterns for auto-detection
    FOREX_PATTERN = re.compile(r'^[A-Z]{3}/[A-Z]{3}$')  # EUR/USD, GBP/JPY
    CRYPTO_PATTERN = re.compile(r'^(BTC|ETH|XRP|SOL|ADA|DOGE|DOT|AVAX|LINK|LTC)/USD$')
    COMMODITY_PATTERN = re.compile(r'^X[A-Z]{2}/USD$')  # XAU/USD, XAG/USD

    def __init__(self):
        load_dotenv()
        self._client: Optional[TDClient] = None
        self._cache: dict[str, AssetMetadata] = {}

    def _get_client(self) -> TDClient:
        """Lazy initialization of TwelveData client."""
        if self._client is None:
            api_key = os.getenv("TD_API_KEY")
            if not api_key:
                raise ValueError("TD_API_KEY not set in environment variables")
            self._client = TDClient(apikey=api_key)
        return self._client

    def detect_asset_type(self, symbol: str) -> str:
        """Auto-detect asset type from symbol format."""
        # Check for commodity pattern first (XAU/USD, XAG/USD)
        if self.COMMODITY_PATTERN.match(symbol):
            return "commodity"

        # Check for known crypto patterns
        if self.CRYPTO_PATTERN.match(symbol):
            return "crypto"

        # Check for forex pattern (XXX/YYY)
        if self.FOREX_PATTERN.match(symbol):
            # Check for JPY or CNH pairs which have different decimals
            if "JPY" in symbol:
                return "forex_jpy"
            if "CNH" in symbol:
                return "forex_cnh"
            return "forex"

        # Check for crypto without pattern match (any XXX/USD that wasn't caught)
        if "/" in symbol and symbol.endswith("/USD"):
            return "crypto"

        # Default to stock for non-pattern symbols (AAPL, MSFT, SPY, etc.)
        return "stock"

    def _fetch_from_api(self, symbol: str) -> Optional[dict]:
        """Fetch metadata from TwelveData quote endpoint."""
        try:
            client = self._get_client()
            quote = client.quote(symbol=symbol).as_json()
            return quote
        except Exception:
            return None

    def get_metadata(self, symbol: str) -> AssetMetadata:
        """Get metadata for a symbol with caching."""
        # Check cache first
        if symbol in self._cache:
            return self._cache[symbol]

        asset_type = self.detect_asset_type(symbol)
        default_decimals = self.DEFAULT_DECIMALS.get(asset_type, 2)

        # Try to fetch from API
        quote = self._fetch_from_api(symbol)

        if quote and isinstance(quote, dict):
            decimal_places = quote.get("decimal_places", default_decimals)
            exchange = quote.get("exchange")

            # Handle decimal_places that might be None or string
            try:
                decimal_places = int(decimal_places) if decimal_places is not None else default_decimals
            except (ValueError, TypeError):
                decimal_places = default_decimals

            metadata = AssetMetadata(
                symbol=symbol,
                decimal_places=decimal_places,
                exchange=exchange,
                asset_type=asset_type
            )
        else:
            # Fallback to defaults on API error
            metadata = AssetMetadata(
                symbol=symbol,
                decimal_places=default_decimals,
                exchange=None,
                asset_type=asset_type
            )

        # Cache the result
        self._cache[symbol] = metadata
        return metadata

    def get_decimal_places(self, symbol: str) -> int:
        """Get decimal places for a symbol."""
        return self.get_metadata(symbol).decimal_places

    def get_exchange(self, symbol: str) -> Optional[str]:
        """Get exchange for a symbol."""
        return self.get_metadata(symbol).exchange

    def clear_cache(self):
        """Clear the metadata cache."""
        self._cache.clear()


# Global singleton instance
_metadata_service: Optional[AssetMetadataService] = None


def get_metadata_service() -> AssetMetadataService:
    """Get or create the global metadata service instance."""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = AssetMetadataService()
    return _metadata_service
