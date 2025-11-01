import ccxt
from typing import Dict, Any, List

def load_exchanges(ids: List[str]) -> Dict[str, ccxt.Exchange]:
    exs = {}
    for ex_id in ids:
        ex = getattr(ccxt, ex_id)()
        ex.options = ex.options or {}
        ex.rateLimit = max(50, getattr(ex, 'rateLimit', 50))
        ex.load_markets()
        exs[ex_id] = ex
    return exs

def taker_fee_for_market(ex: ccxt.Exchange, symbol: str) -> float:
    m = ex.market(symbol)
    fee = None
    # try market-specific taker fee, then exchange default
    if isinstance(m, dict):
        fee = m.get('taker')
    if fee is None:
        fee = getattr(ex, 'fees', {}).get('trading', {}).get('taker', 0.001)
    # fallback
    if fee is None:
        fee = 0.001
    return float(fee)
