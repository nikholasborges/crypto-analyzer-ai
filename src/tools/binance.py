import json
import requests
from crewai.tools import BaseTool
from core.audit import audit_tool_call


def get_coin_gecko_data(symbol: str) -> dict:
    """
    Fetch market cap and supply data from CoinGecko (free API, no auth needed).

    Args:
        symbol: Cryptocurrency symbol (e.g., "bitcoin", "ethereum")

    Returns:
        Dictionary with market cap, supply, and other data
    """
    try:
        coin_id = _symbol_to_coin_id(symbol)
        if not coin_id:
            return {}

        url = "https://api.coingecko.com/api/v3/simple/data"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
            "include_circulating_supply": "true",
        }

        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get(coin_id, {})
    except Exception:
        pass  # Fail gracefully if CoinGecko is unavailable

    return {}


def _symbol_to_coin_id(symbol: str) -> str:
    """Convert trading symbol to CoinGecko coin ID."""
    symbol_clean = (
        symbol.replace("USDT", "").replace("USDC", "").replace("BUSD", "").lower()
    )

    # Map common symbols to CoinGecko IDs
    mapping = {
        "btc": "bitcoin",
        "eth": "ethereum",
        "bnb": "binancecoin",
        "xrp": "ripple",
        "ada": "cardano",
        "sol": "solana",
        "dot": "polkadot",
        "link": "chainlink",
        "matic": "polygon",
        "avax": "avalanche-2",
    }

    return mapping.get(symbol_clean)


class BinanceMarketTool(BaseTool):
    name: str = "BinanceMarketTool"
    description: str = "Fetches real-time cryptocurrency market data from Binance API, including price, volume, market cap, and supply information."

    @audit_tool_call(tool_name="BinanceMarketTool")
    def _run(self, symbol: str = "BTCUSDT") -> str:
        """
        Fetch current market data for a cryptocurrency pair from Binance and CoinGecko.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT", "ETHUSDT"). Defaults to "BTCUSDT"

        Returns:
            JSON formatted string with market data including price, volume, and market cap
        """
        url = "https://api.binance.com/api/v3/ticker/24hr"
        params = {"symbol": symbol.upper()}

        binance_data = {}
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code != 200:
                if response.status_code == 404:
                    return json.dumps(
                        {"error": f"Trading pair '{symbol}' not found on Binance"}
                    )
                return json.dumps(
                    {"error": f"Failed to fetch market data: {response.status_code}"}
                )

            binance_data = response.json()
            if "code" in binance_data and binance_data.get("code") != 200:
                return json.dumps(
                    {
                        "error": f"Binance API Error: {binance_data.get('msg', 'Unknown error')}"
                    }
                )
        except requests.Timeout:
            return json.dumps({"error": f"Binance API timeout for {symbol}"})
        except Exception as e:
            return json.dumps({"error": f"Binance API error: {str(e)}"})

        # Get additional data from CoinGecko
        gecko_data = get_coin_gecko_data(symbol)

        # Extract data safely with fallbacks
        symbol_display = binance_data.get("symbol", symbol)
        current_price = float(binance_data.get("lastPrice", 0))
        high_24h = float(binance_data.get("highPrice", 0))
        low_24h = float(binance_data.get("lowPrice", 0))
        volume = float(binance_data.get("volume", 0))
        quote_asset_volume = float(binance_data.get("quoteAssetVolume", 0))
        price_change = float(binance_data.get("priceChange", 0))
        price_change_percent = float(binance_data.get("priceChangePercent", 0))

        # Market cap from CoinGecko
        market_cap = None
        if gecko_data and "usd" in gecko_data:
            market_cap = gecko_data.get("usd", {}).get("market_cap")

        # Build JSON response
        result = {
            "symbol": symbol_display,
            "current_price": current_price,
            "24h_high": high_24h,
            "24h_low": low_24h,
            "price_change": price_change,
            "price_change_percent": price_change_percent,
            "24h_volume_crypto": volume,
            "24h_volume_usd": quote_asset_volume if quote_asset_volume > 0 else None,
            "market_cap": market_cap,
            "data_source": "Binance API (real-time)",
        }

        return json.dumps(result, indent=2)


class BinanceOrderBookTool(BaseTool):
    name: str = "BinanceOrderBookTool"
    description: str = "Fetches the order book (bid/ask levels) for a cryptocurrency pair from Binance to show liquidity and spread."

    @audit_tool_call(tool_name="BinanceOrderBookTool")
    def _run(self, symbol: str = "BTCUSDT", depth: int = 5) -> str:
        """
        Fetch order book data for a cryptocurrency pair from Binance.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT", "ETHUSDT"). Defaults to "BTCUSDT"
            depth: Number of price levels to show (5, 10, 20, etc.). Defaults to 5

        Returns:
            JSON formatted string with order book data including bid/ask orders and spread
        """
        # Validate and adjust depth parameter
        valid_depths = [5, 10, 20, 50, 100, 500, 1000, 5000]
        if depth not in valid_depths:
            depth = 5

        url = "https://api.binance.com/api/v3/depth"
        params = {"symbol": symbol.upper(), "limit": depth}

        try:
            response = requests.get(url, params=params, timeout=5)
        except requests.Timeout:
            return json.dumps({"error": f"Order book request timed out for {symbol}"})
        except Exception as e:
            return json.dumps({"error": f"Order book API error: {str(e)}"})

        # Handle HTTP errors gracefully
        if response.status_code == 404:
            return json.dumps(
                {"error": f"Trading pair '{symbol}' not found on Binance"}
            )
        elif response.status_code != 200:
            return json.dumps(
                {"error": f"Binance API returned status {response.status_code}"}
            )

        try:
            data = response.json()
        except Exception:
            return json.dumps({"error": "Failed to parse order book response"})

        # Check for API errors
        if "code" in data and data.get("code") != 200:
            return json.dumps(
                {"error": f"API Error: {data.get('msg', 'Unknown error')}"}
            )

        bids = data.get("bids", [])
        asks = data.get("asks", [])

        if not bids and not asks:
            return json.dumps({"error": f"No order book data available for {symbol}"})

        # Convert asks and bids to structured format
        asks_list = []
        for ask in asks:
            try:
                asks_list.append({"price": float(ask[0]), "quantity": float(ask[1])})
            except (ValueError, IndexError):
                continue

        bids_list = []
        for bid in bids:
            try:
                bids_list.append({"price": float(bid[0]), "quantity": float(bid[1])})
            except (ValueError, IndexError):
                continue

        # Calculate spread if available
        spread_info = None
        if asks_list and bids_list:
            best_ask = asks_list[0]["price"]
            best_bid = bids_list[0]["price"]
            spread = best_ask - best_bid
            spread_pct = (spread / best_bid) * 100 if best_bid != 0 else 0
            spread_info = {
                "price_difference": round(spread, 8),
                "percentage": round(spread_pct, 2),
            }

        # Build JSON response
        result = {
            "symbol": symbol.upper(),
            "asks": asks_list,
            "bids": bids_list,
            "spread": spread_info,
            "data_source": "Binance API (real-time)",
            "depth_limit": depth,
        }

        return json.dumps(result, indent=2)
