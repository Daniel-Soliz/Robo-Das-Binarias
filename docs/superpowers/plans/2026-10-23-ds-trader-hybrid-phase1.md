# DS Trader Hybrid — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the first testable hybrid slice: safe active-asset tracking in IQ Option's selected window, a provider-backed small Forex/crypto radar, and an uncluttered desktop monitor without placing trades.

**Architecture:** Keep WGC screenshot capture and Tkinter UI in their existing modules; add a pure identity/temporal guard and feed-agnostic scanner with immutable events and bounded queues. Twelve Data is the first read-only provider; display data source, freshness, unsupported symbols and errors. Never combine outside-provider OHLC with IQ Option visual candles.

**Tech Stack:** Python 3.11, Tkinter, PIL, windows-capture on Windows, optional local OCR, Twelve Data REST, pytest, PyInstaller/Inno Setup.

**Spec:** `docs/superpowers/specs/2026-10-23-ds-trader-hybrid-design.md` (approved in user message: "Pode fazer o que vc achar necessário está desse modelo mesmo que vc mandou").

## Global Constraints

- No live trades, credential extraction, fake market data, fake probabilities or unsourced market claims.
- Treat chart screenshots as unverified pixels: fail closed to `AGUARDAR` for M1 and any missing identity or timing.
- Keep existing configs, local SQLite, CSV importer, report export, and UI public methods functional.
- No API key saved or printed; users supply it locally in the application when they want the radar.
- OTC instruments are never silently mapped onto regular Forex quotes.
- Existing source files have user worktree changes; do not overwrite/revert them.
- Windows install and real IQ Option screenshot behavior remain unverified until run on Windows.

## Review Focus

1. Switching from one symbol to another before an old worker finishes: drop stale-generation frames/results — Test in Task 1.
2. OCR missing or ambiguous (or crypto/OTC not recognized): clear prior directional state — Test in Task 1.
3. Network disconnect or 429 while other symbols are updating: no stale/current mix and no token in error — Test in Task 3.
4. Crypto trades on weekends vs Forex closed: category-specific market-hours handling — Test in Task 2.
5. UI stop/start and page navigation with queued results: no Tkinter main-loop network work or callback after shutdown — Test in Task 4.

---

### Task 1: Active symbol and identity guard

**Files:** Create `ds_trader/asset_identity.py`; Test `tests_ds/test_asset_identity.py`; Modify `ds_trader/live_screen.py`, `ds_trader/live_presentation.py`, `ds_trader/live_modern_ui.py` minimally.

**Interfaces:**
- `parse_asset_header(text: str) -> AssetIdentity | None` recognizes Forex (`AAA/BBB`), crypto (`BTC/USD` etc), `M1/M5/M15`, and OTC, rejects multiple symbols.
- `AssetIdentity(symbol: str, timeframe: str, otc: bool)` immutable.
- `IdentityGuard.observe(candidate: AssetIdentity | None, *, frame_id: int) -> IdentityStatus` with `generation`, `confirmed`, `changed`, `reason`, `current`; three consecutive matching candidates required, unknown invalidates immediately, old `frame_id` ignored.
- `ScreenMonitor` publishes identity and capture generation alongside visual assessment; if OCR is missing, identity is `UNVERIFIED` and presentation is `AGUARDAR`. No positive M1 event from screen.

- [ ] Step 1: Write identity parsing tests for EUR/USD M1, BTC/USD M5, mixed candidates, malformed symbols, and OTC.
- [ ] Step 2: Run `pytest -q tests_ds/test_asset_identity.py` (red: module missing).
- [ ] Step 3: Implement pure `parse_asset_header` and `IdentityGuard` with early invalidation and three-frame confirmation.
- [ ] Step 4: Add test for switching immediately after confirmed asset A, and late frame from A arriving after B.
- [ ] Step 5: Wire optional header-recognizer injection into `ScreenMonitor` without OCR requirement for startup; otherwise return `UNVERIFIED`.
- [ ] Step 6: Run `pytest -q tests_ds/test_asset_identity.py tests_ds/test_live_screen.py tests_ds/test_live_presentation.py` and commit only Task 1 files.

### Task 2: Real symbol-aware Forex and crypto candle parsing

**Files:** Modify `ds_trader/forex_live.py` with backwards-compatible public APIs; Test `tests_ds/test_forex_live.py` and new `tests_ds/test_market_assets.py`.

**Interfaces:**
- `AssetSpec(symbol: str, category: Literal['FOREX','CRYPTO'])` validates a controlled watchlist; `classify_market_symbol(symbol: str) -> str | None`.
- `parse_asset_payload(payload, spec: AssetSpec, interval: str, *, now: datetime | None = None) -> MarketView` returns actual source metadata; existing `parse_payload` remains Forex-compatible.
- `fetch_asset_candles(api_key, spec, interval, *, timeout=12, opener=None, now=None) -> MarketView` makes real Twelve Data REST read-only request.
- Crypto is not gated by `reference_forex_open()`, but stale timestamps, missing series, invalid quotes remain blocked.

- [ ] Step 1: Add red tests: BTC/USD crypto metadata, Saturday crypto, Saturday Forex closed, mismatched source symbol, duplicate timestamp, 429 and stale crypto.
- [ ] Step 2: Run targeted tests (red for new API).
- [ ] Step 3: Implement symbol-aware parser/fetcher with existing Forex path calling shared validation; preserve exact old test behavior.
- [ ] Step 4: Run `pytest -q tests_ds/test_forex_live.py tests_ds/test_market_assets.py` and commit Task 2 files.

### Task 3: Read-only multiasset radar worker

**Files:** Create `ds_trader/market_radar.py`, `tests_ds/test_market_radar.py`.

**Interfaces:**
- `RadarEvent(symbol, category, status, snapshot, observed_at, source, reason)` immutable; no invented values when `snapshot=None`.
- `MarketRadar(api_key: str, specs: Sequence[AssetSpec], interval='1min', refresh_seconds=120, fetcher=fetch_asset_candles, monotonic=time.monotonic)`; `start()`, `stop()`, `events: Queue`, `coverage()`; honors bounded favorites and per-symbol interval, backoff, clean teardown and no token in errors.
- `coverage` counts requested, current, failed, stale, unsupported; outcomes do not masquerade as completed scans.

- [ ] Step 1: Create failing tests for 2 assets scanned, coverage counts, out-of-order delivery, worker stop, 429, slow fetch, no key, avoiding leaks.
- [ ] Step 2: Run targeted tests (red).
- [ ] Step 3: Implement worker scheduling/queues, injection points and provenance.
- [ ] Step 4: Run `pytest -q tests_ds/test_market_radar.py` and commit Task 3 files.

### Task 4: Minimal hybrid desktop UI

**Files:** Create `ds_trader/market_radar_ui.py`; Modify `ds_trader/ui.py`, `ds_trader/dashboard_shell.py`, `ds_trader/live_modern_ui.py`; Test `tests_ds/test_compact_navigation.py`, `tests_ds/test_hybrid_navigation.py`, `scripts/gui_smoke.py`.

**Interfaces:**
- `RadarTab(parent, root)` displays a provider-key field (masked), start/stop controls, configurable initial favorites, coverage, and an informative compact table; polling uses `root.after`, never main-thread network.
- Existing `App.forex_view` remains functional through a legacy tools page; `App.radar_view` adds new `Radar` page. `LiveScreenTab` header shows confirmed/unknown active asset and generation.
- UI text always distinguishes `CAPTURA VISUAL`, `TWELVE DATA` and `SEM FONTE`, plus illustrated view when offline.

- [ ] Step 1: Add smoke test for correct new page wiring, no automatic capture/network calls, shutdown before scheduled poll.
- [ ] Step 2: Run targeted tests (red).
- [ ] Step 3: Implement simple table and navigation inspired by approved screenshot; do not reproduce fake live values.
- [ ] Step 4: Run focused UI contract tests and `python -m pytest -q`; commit Task 4 files.

### Task 5: Instrumentation and release validation

**Files:** Modify `scripts/benchmark_visual.py`, `scripts/gui_smoke.py`, `README.md`, `docs/TESTES.md` and Windows workflow only if required by tests.

- [ ] Step 1: Add or run benchmark covering captured-to-rendered age and worker queue usage, log P50/P95 with actual environment.
- [ ] Step 2: Run `python -m pytest -q` and collect exact results; run GUI smoke if available, otherwise mark Windows as pending.
- [ ] Step 3: Run build/installer tests on Windows CI if accessible, report artifact hashes/results only when actually observed.
- [ ] Step 4: Update docs with config, provider limitations, OTC and per-source provenance; commit documentation changes.

## Execution policy

Implementation proceeds in small verified slices. Stop and request permission before installing a paid source, entering credentials, publishing a GitHub release, or changing/deleting user's historical data. If external live validation isn't available, never claim it passed; report the functional code and what's blocked.
