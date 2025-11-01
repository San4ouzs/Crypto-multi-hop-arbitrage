import os
import math
import argparse
from typing import Set, List, Tuple
from dotenv import load_dotenv
from .exchanges import load_exchanges
from .arbitrage_graph import build_edges_for_exchange, to_log_graph
from .find_cycles import bellman_ford_negative_cycle, product_from_cycle
from .toplist import fetch_top_symbols_coingecko
from .telegram_notify import notify
import pandas as pd

def parse_args():
    p = argparse.ArgumentParser(description="Multi-hop crypto arbitrage finder (intra-exchange).")
    p.add_argument('--exchanges', type=str, default=None, help='Comma-separated CCXT exchange ids (e.g. binance,kucoin)')
    p.add_argument('--bases', type=str, default=None, help='Start/end base assets (e.g. BTC,ETH,USDT)')
    p.add_argument('--max-hops', type=int, default=None, help='Max cycle length (default from .env)')
    p.add_argument('--min-profit-bps', type=int, default=None, help='Min profit to report in bps')
    p.add_argument('--use-orderbook', action='store_true', help='Use order book bid/ask (else ticker last)')
    p.add_argument('--no-use-orderbook', action='store_true', help='Force not using orderbook')
    p.add_argument('--export-csv', type=str, default=None, help='Path to export cycles CSV')
    p.add_argument('--no-top100', action='store_true', help='Disable top-100 filter')
    p.add_argument('--topn', type=int, default=None, help='How many top coins to include (default 100)')
    return p.parse_args()

def env_bool(key:str, default:bool) -> bool:
    v = os.getenv(key)
    if v is None: return default
    return str(v).lower() in ('1','true','yes','y','on')

def main():
    load_dotenv(dotenv_path=os.path.join('config','.env'), override=False)
    args = parse_args()

    ex_ids = (args.exchanges or os.getenv('EXCHANGES','binance')).split(',')
    base_assets = (args.bases or os.getenv('BASE_ASSETS','BTC,ETH,USDT')).split(',')
    base_assets = [s.strip().upper() for s in base_assets if s.strip()]
    max_hops = args.max_hops or int(os.getenv('MAX_HOPS','5'))
    min_profit_bps = args.min_profit_bps or int(os.getenv('MIN_PROFIT_BPS','10'))
    use_orderbook = args.use_orderbook or env_bool('USE_ORDERBOOK', True)
    if args.no_use_orderbook:
        use_orderbook = False
    include_fees = env_bool('INCLUDE_FEES', True)
    use_top100 = (not args.no_top100) and env_bool('USE_TOP100', True)
    topn = args.topn or int(os.getenv('TOPN','100'))

    tg_token = os.getenv('TELEGRAM_TOKEN','').strip()
    tg_chat = os.getenv('TELEGRAM_CHAT_ID','').strip()

    allowed_assets: Set[str] = set()
    if use_top100:
        try:
            syms = fetch_top_symbols_coingecko(topn=topn)
            allowed_assets = set(syms) | set(['BTC','ETH','USDT','USDC'])  # ensure majors
            print(f"[i] Toplist filter active: {len(allowed_assets)} symbols.")
        except Exception as e:
            print(f"[!] Failed to fetch top list: {e}. Proceeding without filter.")
            allowed_assets = set()

    print(f"[i] Loading exchanges: {ex_ids}")
    exs = load_exchanges(ex_ids)

    rows = []
    for ex_id, ex in exs.items():
        print(f"[i] Building graph for {ex_id} (orderbook={use_orderbook}, fees={include_fees})")
        edges = build_edges_for_exchange(ex, use_orderbook=use_orderbook, include_fees=include_fees, allowed_assets=allowed_assets)
        log_edges = [(u,v,w,sym) for (u,v,w,sym) in to_log_graph(edges)]
        nodes = sorted(set([u for u,_,_,_ in log_edges] + [v for _,v,_,_ in log_edges]))

        if not nodes:
            print(f"[!] No nodes for {ex_id}. Skipping.")
            continue

        cycles = bellman_ford_negative_cycle(nodes, log_edges, max_hops=max_hops)
        # Evaluate cycles and filter by bases and profit threshold
        unique = set()
        for cyc in cycles:
            # cyc: [(A, sym1), (B, sym2), ..., (A, sym_last)]
            start = cyc[0][0]
            if base_assets and start not in base_assets:
                continue
            profit = product_from_cycle(cyc, edges) - 1.0
            bps = profit * 10000.0
            if math.isinf(bps) or math.isnan(bps):
                continue
            if bps < min_profit_bps:
                continue
            # Canonicalize cycle to avoid duplicates
            norm = "->".join(n for (n,_) in cyc)
            key = (ex_id, norm)
            if key in unique:
                continue
            unique.add(key)

            # Build readable path with markets
            path_assets = [n for (n,_) in cyc]
            path_markets = []
            for i in range(len(cyc)-1):
                a = cyc[i][0]
                b = cyc[i+1][0]
                m = next((sym for (u,v,_,sym) in log_edges if u==a and v==b), "?")
                path_markets.append(m)

            rows.append({
                "exchange": ex_id,
                "start_asset": start,
                "hops": len(path_assets)-1,
                "profit_bps": round(bps, 2),
                "profit_pct": round(bps/100.0, 4),
                "path_assets": " → ".join(path_assets),
                "path_markets": " | ".join(path_markets),
            })

    if not rows:
        print("[i] No profitable cycles above threshold right now.")
        return

    df = pd.DataFrame(rows).sort_values(["profit_bps","hops"], ascending=[False, True])
    print(df.to_string(index=False))

    if args.export_csv:
        df.to_csv(args.export_csv, index=False)
        print(f"[i] Exported CSV to {args.export_csv}")

    # Telegram notify top 3
    top_text = "\n".join([f"{r['exchange']}: +{r['profit_bps']} bps | {r['path_assets']} | {r['path_markets']}" for _,r in df.head(3).iterrows()])
    if top_text:
        notify(tg_token, tg_chat, f"Arb cycles:\n{top_text}")

if __name__ == '__main__':
    main()
