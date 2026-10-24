# DS Trader Automatic Active Asset M5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically track the confirmed IQ Option chart symbol, study verified public M5 closed candles up to 24 hours earlier, and explain a conservatively blocked CALL/PUT/AGUARDAR *scenario* without emitting trading entries.

**Architecture:** Source-specific bounded historical snapshots feed a pure deterministic `ActiveHistoryReport`; an isolated worker tracks confirmed on-screen asset identity by generation and never updates Tk from its thread. The live monitor renders the external scenario separately from its existing visual and M1 cycle states.

**Tech Stack:** Python/Tkinter, HTTPS public Binance and Kraken, optional Twelve Data Forex key, pytest, optional Python `pytesseract` bridge plus separately installed Windows Tesseract OCR engine.

**Spec:** `docs/superpowers/specs/2026-10-24-modo-automatico-ativo-m5-design.md`

## Global Constraints

- Never equate external sources with IQ Option/OTC; no real orders, no probabilities.
- M5 default; only confirmed, consecutive closed OHLC, up to 288 for 24 hours.
- Fail closed on pair/timeframe/OTC/age/source/gaps/missing data; never reuse a prior pair's opinion.
- Threads only for HTTP, Tk mainloop for widgets; bounded queues, short timeouts, no credential persistence.
- Do not overwrite or reset user SQLite, settings, previous worktree changes.

## Review Focus

- A rapid USD/JPY → USD/BRL switch during slow HTTP must never show USD/JPY's delayed result.
- A lost header/OTC switch invalidates a previous scenario immediately, even when the last source was current.
- Open/corrupt/noncontiguous candles must not produce a confident next-bar scenario.
- Forex with no key or unsupported symbol is explicitly unavailable.
- A different source or stale closed candle never becomes a verified IQ Option CALL/PUT.

---

### Task 1: Pure closed-candle historical scenario

**Files:** Create `ds_trader/active_history.py`, `tests_ds/test_active_history.py`.

**Interfaces:** `assess_history(view: MarketView, *, now: datetime) -> ActiveHistoryReport`; fields `symbol, interval, source, horizon_hours, closed_count, scenario, reason, operational_side`; operational side always `AGUARDAR` while data are external.

- [x] Step 1: Write tests for 288 M5 consecutive candles, 24h horizon, stale/absent bars, gaps, insufficient history, directional evidence, and no actionable CALL/PUT.
- [x] Step 2: Run target tests, watch RED from missing module.
- [x] Step 3: Implement minimal explanatory pure engine reusing `evaluate_next()` with verified candle flag while distinguishing scenario and operational side.
- [x] Step 4: Run targeted + full tests; commit.

### Task 2: Source-specific extended M5 history

**Files:** Modify `ds_trader/binance_public.py`, `ds_trader/public_crypto.py`, `ds_trader/forex_live.py`; create `ds_trader/active_source.py`; tests `tests_ds/test_active_source.py` and extend adapter tests.

**Interfaces:** `fetch_active_history(spec: AssetSpec, *, api_key: str, ...) -> MarketView`; fixed M5, use exact symbol and source, 288 closed bars max; never call Twelve Data without provided key.

- [x] Step 1: Write failing tests for 289 Binance REST requested bars, M5 exact pairs and timestamps, Kraken 721-last-open parsing, optional Forex `outputsize=...`, provider denial with no key.
- [x] Step 2: Verify RED.
- [x] Step 3: Add bounded optional history length to source adapters without expanding normal radar memory and add source selector.
- [x] Step 4: Run adapter tests/full suite; commit.

### Task 3: Active chart following, suppression and UI

**Files:** Create `ds_trader/active_tracking.py` with pure switching and bounded asynchronous worker; modify `ds_trader/live_modern_ui.py`, `ds_trader/ui.py`, `scripts/gui_smoke.py`; tests `tests_ds/test_active_tracking.py`.

**Interfaces:** `ActiveAssetTracking.observe(identity: AssetIdentity | None)`, `.drain()`, `.stop()`, `focus_identity(result)`; `LiveScreenTab.set_market_key_supplier()` reuses the Radar's in-memory key (app wires them). Focus panel always labels the source and operational `AGUARDAR`.

- [x] Step 1: Write tests for same-pair dedup, immediate invalidation on switch/OTC/unknown, delayed reply suppression, source errors, M5 default, stale data; verify RED.
- [x] Step 2: Implement background tracking and queue with per-generation responses, never perform network in Tk.
- [x] Step 3: Wire callback and a dedicated active-target context section; extend GUI smoke expectations without connecting online in CI.
- [x] Step 4: Run targeted/full suite, compileall, diff checks and report Windows limitations; commit after review.

Ruling: The M5 target panel and tracker live with `LiveScreenTab` instead of
inside `RadarTab`: it depends on the screen's confirmed identity, and a
key supplier connects it read-only to the existing Radar settings. Cost:
it appears under the Monitor, not as a separate highlighted Radar row.

### Task 4: Documentation and handoff

**Files:** `README.md`, `docs/TESTES.md`.

- [x] Step 1: Document new M5 mode, sources, no-key limitations, OTC/sync guardrails and setup.
- [x] Step 2: Verify all automated tests and packaging settings; independent review flagged and led to corrections for Kraken asset-key integrity, period switching, and Windows CI test execution.
- [x] Step 3: Commit and prepare source ZIP; no remote push or unverified Windows binary.
