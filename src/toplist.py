import requests
from typing import Set

def fetch_top_symbols_coingecko(topn:int=100) -> Set[str]:
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency":"usd", "order":"market_cap_desc", "per_page": topn, "page":1, "sparkline":"false"}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    # Return uppercase tickers (e.g., 'btc' -> 'BTC'), include stablecoins.
    return set((row.get("symbol","") or "").upper() for row in data if "symbol" in row)
