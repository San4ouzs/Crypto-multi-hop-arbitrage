# Crypto Multi‑Hop Arbitrage Finder (Top‑100 filter)

This tool scans one or more centralized exchanges (via [CCXT](https://github.com/ccxt/ccxt))
for profitable multi‑hop **conversion cycles** (start/end in the same asset), e.g.:

```
BTC → BNB → XRP → USDT → ETH → BTC
```

If the product of conversion rates (after fees) is > 1, the cycle is profitable.

---

## Highlights

- **Multi‑hop cycles**: up to `MAX_HOPS` (default 5).
- **Fees-aware**: uses taker fee estimates (per exchange) to discount rates.
- **Top‑100 filter** (optional): pulls top‑market‑cap coins from CoinGecko and only uses those symbols.
- **Live data**: builds edges from best **bid/ask** (order books) or mid‑prices (tickers).
- **Multiple exchanges**: scan one or more (e.g., `binance,kucoin,bybit`) independently.
- **CSV export** and console summary of best cycles.
- **Optional Telegram alerts** when profit exceeds threshold.

> ⚠️ This is **intra‑exchange** arbitrage: it finds cycles within a single exchange's markets.
> Cross‑exchange arbitrage requires transfer/latency modeling and is out of scope for this MVP.

---

## Quick Start

1) Create a virtual environment and install deps:

```bash
python -m venv .venv
. .venv/bin/activate   # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
```

2) Copy and edit config:

```bash
cp config/.env.example config/.env
```

3) Run:

```bash
python -m src.main
```

Or with flags:

```bash
python -m src.main --exchanges binance,kucoin --bases BTC,ETH,USDT --max-hops 5 --min-profit-bps 10 --use-orderbook
```

4) (Optional) Export CSV:

```bash
python -m src.main --export-csv cycles.csv
```

---

## Config

Edit `config/.env` or pass CLI flags.

- `EXCHANGES=binance,kucoin,bybit` — list of exchanges (CCXT ids).
- `BASE_ASSETS=BTC,ETH,USDT,USDC` — assets to start/end cycles on.
- `MAX_HOPS=5` — maximum path length (including the return to start).
- `MIN_PROFIT_BPS=5` — minimum profit in basis points (1 bps = 0.01%).
- `USE_ORDERBOOK=true` — if `true`, uses best bids/asks; otherwise uses last price.
- `INCLUDE_FEES=true` — apply taker fee (estimate).
- `USE_TOP100=true` — filter universe to top‑100 market‑cap coins (CoinGecko).
- `TOPN=100` — how many from top list to include.
- `TELEGRAM_TOKEN=...` and `TELEGRAM_CHAT_ID=...` — optional alerts.

---

## How it works

We create a directed graph per exchange:
- Nodes: assets (e.g., BTC, ETH, USDT).
- Edges: tradable pairs, with a conversion rate after fees:
  - For market `BASE/QUOTE`:
    - Edge `BASE → QUOTE` uses **bid** (sell BASE to get QUOTE).
    - Edge `QUOTE → BASE` uses **1/ask** (buy BASE with QUOTE).
- We transform rates with `weight = -log(rate)` and run Bellman‑Ford.
  - A **negative cycle** implies product of rates > 1 ⇒ arbitrage.
- Cycles are reconstructed and ranked by **net profit**.

Notes:
- Fees are estimated with exchange taker fee (CCXT `market['taker']` if available).
- Slippage is **not** modeled beyond top of book; use small `notional` to test live fills.

---

## Safety & Disclaimer

This software is for **research/education**. Markets are fast; quotes may change by the time
you attempt execution. Use at your own risk.
