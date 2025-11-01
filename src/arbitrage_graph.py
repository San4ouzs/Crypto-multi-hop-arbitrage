import math
from typing import Dict, Tuple, Iterable, Set, List
from .exchanges import taker_fee_for_market

Edge = Tuple[str, str, float, str]  # (u, v, rate_after_fees, market_symbol)

def _apply_fee(rate: float, fee: float) -> float:
    # taker fee applied once per edge
    return rate * (1.0 - fee)

def build_edges_for_exchange(ex, use_orderbook: bool, include_fees: bool, allowed_assets: Set[str]) -> List[Edge]:
    edges: List[Edge] = []
    markets = ex.load_markets()
    for sym, m in markets.items():
        if not m.get('active', True):
            continue
        base = m.get('base')
        quote = m.get('quote')
        if not base or not quote:
            continue
        if allowed_assets and (base not in allowed_assets or quote not in allowed_assets):
            continue

        fee = taker_fee_for_market(ex, sym) if include_fees else 0.0

        # Try to get bid/ask or last price
        bid = ask = last = None
        if use_orderbook:
            try:
                ob = ex.fetch_order_book(sym, limit=5)
                if ob.get('bids'):
                    bid = float(ob['bids'][0][0])
                if ob.get('asks'):
                    ask = float(ob['asks'][0][0])
            except Exception:
                pass
        if bid is None or ask is None:
            try:
                t = ex.fetch_ticker(sym)
                last = float(t.get('last') or t.get('close') or 0.0)
            except Exception:
                last = 0.0

        # From BASE -> QUOTE (sell BASE, receive QUOTE) uses bid; fallback to last
        if (bid and bid > 0) or (last and last > 0):
            px_sell = bid if (bid and bid > 0) else last
            rate_bq = _apply_fee(px_sell, fee)
            if rate_bq > 0:
                edges.append((base, quote, rate_bq, sym))

        # From QUOTE -> BASE (buy BASE with QUOTE) uses 1/ask; fallback to 1/last
        if (ask and ask > 0) or (last and last > 0):
            px_buy = ask if (ask and ask > 0) else last
            if px_buy > 0:
                rate_qb = _apply_fee(1.0 / px_buy, fee)
                if rate_qb > 0:
                    edges.append((quote, base, rate_qb, sym))

    return edges

def to_log_graph(edges: Iterable[Edge]):
    # weight = -log(rate); sum < 0 implies profitable product > 1
    log_edges = []
    for u, v, r, sym in edges:
        if r <= 0: 
            continue
        w = -math.log(r)
        log_edges.append((u, v, w, sym))
    return log_edges
