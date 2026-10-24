# DS Trader Public Markets Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show official TradingView markets with B3 delay attribution and ingest Binance public WebSocket closed crypto candles independently of the IQ Option screen, without credentials or real orders.

**Architecture:** Binance REST bootstrap and combined public WebSocket feed live in a bounded daemon-thread worker, emitting the existing `RadarEvent` contract for UI consumption. The Radar tab combines these events with Kraken/Twelve Data favorites. A packaged HTML market board runs the official TradingView widget in the user's default browser on demand (native embedded WebView2 pending Windows validation), never as a signal datafeed.

**Tech Stack:** Python 3.11+, Tkinter, urllib, websockets 16.x synchronous client, official Binance market-only endpoints and TradingView widgets.

**Spec:** `docs/superpowers/specs/2026-10-24-mercados-sem-cadastros-proposta.md` (approved by user's “Vamos fazer o que você disse”).

## Global Constraints

- No authenticated Binance endpoints, credentials, IQ Option account access or financial orders.
- Never substitute BTC/USDT for BTC/USD; strict source, symbol, timeframe and closed timestamps.
- The TradingView B3 widget is visually labeled as approximately 15 minutes delayed; it never feeds M1 analytics.
- No price, candle or connection may be presented as current without verified provider input.
- Preserve local SQLite, existing user configuration, Kraken/Twelve Data mode and branch, and pass the full suite before handoff.
- Capture and network workers may not block Tk mainloop. Cancel quickly; bounded history, message size, favorites and reconnect delays.

## Review Focus

- A Binance `x=false` candle (open) must never enter a directional analysis — test in Task 1.
- Lost WebSocket after a fresh event must invalidate display and later reconnect without signal replay — test in Task 2.
- Incorrect symbol, interval or unsorted/duplicated events must be rejected — test in Task 1.
- B3 display must remain labelled delayed and separate from the analyzable feed — test in Task 3.
- Launching a market board after packaging must resolve its bundled asset and never open arbitrary user-provided URLs — test in Task 3.

---

### Task 1: Binance public candle adapters and strict closed-bar validation

**Files:** Create `ds_trader/binance_public.py`; tests `tests_ds/test_binance_public.py`.

**Interfaces:** `BinanceCandleBook(spec: AssetSpec, interval: str)` with `bootstrap(payload, now)` and `accept(event, now) -> MarketView|None`, and `fetch_binance_history(spec, interval, *, opener, now) -> MarketView` for an unauthenticated `GET /api/v3/klines` to `data-api.binance.vision`.

- [x] Step 1: Tests for true Binance USDT symbols, malformed REST bars, UTC timestamps, duplicate bars, interval mismatches, out-of-order messages, and `x=false` ignored.
- [x] Step 2: Run `.venv/bin/python -m pytest -q tests_ds/test_binance_public.py` and observe expected failure.
- [x] Step 3: Implement minimal parser/book with bounded 120 closed bars and `analyze()` reused from Forex module.
- [x] Step 4: Rerun the task tests; report the output.
- [x] Step 5: Commit task 1.

### Task 2: WebSocket worker and Radar UI integration

**Files:** Create `ds_trader/binance_stream.py`, tests `tests_ds/test_binance_stream.py`; modify `ds_trader/market_radar_ui.py`, `requirements-runtime.txt`, `tests_ds/test_hybrid_navigation.py`, `scripts/gui_smoke.py`.

**Interfaces:** `BinanceStreamRadar(specs, *, interval, fetcher, connector)` exposes `.events: Queue[RadarEvent]`, `.running`, `.start()`, `.stop(wait=False)`, `.coverage()`; UI partitions `/USDT` symbols to stream and all others to existing `MarketRadar`.

- [x] Step 1: Write tests for combined URL, bounded queue, reconnect after provider failure, no late event after stop, and stale view model behavior; start test in RED.
- [x] Step 2: Implement background stream worker with exponential backoff and bounded `recv(timeout=1)`; no Tk network.
- [x] Step 3: Integrate source partition and unified events into Radar with default `BTC/USDT`, `ETH/USDT` favorites and accurate coverage.
- [x] Step 4: Run targeted and full suites; commit task 2.

### Task 3: TradingView official market board and launcher

**Files:** Create `ds_trader/assets/mercados_globais.html`, `ds_trader/market_board.py`, tests `tests_ds/test_market_board.py`; modify `ds_trader/market_radar_ui.py`, `scripts/build.ps1`, `README.md`, `docs/TESTES.md`.

**Interfaces:** `market_board_path() -> Path`, `open_market_board(*, opener=webbrowser.open) -> bool` only opens checked packaged board `file://` path; HTML embeds official TradingView widgets for B3/Forex/crypto with branded attribution and B3 delay warning.

- [x] Step 1: Tests verify bundled file exists, official widget script and attribution, delay label, and launcher opens only the validated local file.
- [x] Step 2: Run targeted tests expecting RED; write HTML and launcher.
- [x] Step 3: Add `Ver mercados globais` button to Radar, include asset in PyInstaller build (`--add-data`), GUI smoke check; no new account/login.
- [ ] Step 4: Verify tests, compileall, package asset presence; document limitations and run Windows when available. (Python validado; Windows pendente.)
- [x] Step 5: Commit task 3. No remote push or installer release without separate authorization.

## Handoff

The HTML board opens in a browser for this safe phase. Embedding the widget as a native WebView2 child control, and automatic analysis of B3 intraday prices, remain explicitly unverified and out of scope until Windows UI and market-data rights are validated.
