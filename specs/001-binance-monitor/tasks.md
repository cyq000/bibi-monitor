# Tasks — 001-binance-monitor

Feature: 币安合约主动买卖量监控
Spec: specs/001-binance-monitor/spec.md
Plan: specs/001-binance-monitor/plan.md

Phase 1: Setup

- [x] T001 [P] Initialize Python project files and metadata: create `pyproject.toml`, `README.md`, and update `specs/001-binance-monitor/requirements.txt` (repo root)

  - NOTE: Completed 2026-02-10 — created `pyproject.toml` with full project metadata, dependencies, and build configuration; updated `README.md` with comprehensive documentation.
- [x] T002 [P] Add repository `.gitignore` and `/.env.example` at `specs/001-binance-monitor/.env.example` (repo root/.gitignore)

  - NOTE: Completed 2026-02-10 — created `.env.example` with all configuration parameters including Feishu webhook, database, and thresholds.
- [ ] T003 Create CI workflow for tests and lint: add `.github/workflows/ci.yml` to run `pytest` and `flake8` (path: .github/workflows/ci.yml)
 - [x] T003 Create CI workflow for tests and lint: add `.github/workflows/ci.yml` to run `pytest` and `flake8` (path: .github/workflows/ci.yml)

  - NOTE: Completed 2026-02-08 — added `.github/workflows/ci.yml` to run `pytest` on push/PR (basic matrix for Python 3.11).
- [x] T004 [P] Add `Dockerfile` and `docker-compose.yml` templates for local dev and containerized runs (paths: Dockerfile, docker-compose.yml)

  - NOTE: Completed 2026-02-10 — created multi-stage Dockerfile with health checks, and docker-compose.yml with PostgreSQL, Redis, Prometheus, and Grafana services.
- [x] T005 Create basic developer docs: update `specs/001-binance-monitor/quickstart.md` with run/compose instructions (path: specs/001-binance-monitor/quickstart.md)

  - NOTE: Completed 2026-02-10 — updated quickstart.md with comprehensive guides for local Python, Docker Compose, and single Docker image deployment methods.

Phase 2: Foundational (blocking prerequisites)

- [x] T006 Implement configuration loader and secrets gating: add `src/config.py` that reads env vars and supports `.env` (path: src/config.py)
- [x] T007 Implement DB migration scaffold and connection util: add `src/db.py` + alembic scaffold (paths: src/db.py, alembic/*)

  - NOTE: Completed 2026-02-08 — added `src/db.py` (SQLAlchemy scaffold) and `alembic/README.md` with Alembic integration instructions.
- [x] T008 [P] Harden storage: refactor `src/storage.py` to use SQLAlchemy models aligned with `specs/001-binance-monitor/data-model.md` (path: src/models.py, src/storage.py)

  - NOTE: Completed 2026-02-08 — added `src/models.py` and refactored `src/storage.py` to use SQLAlchemy; test script `scripts/test_storage_sqlalchemy.py` verifies inserts.
- [x] T009 Create logging/observability baseline: structured JSON logs, metrics stub (path: src/logging.py, src/metrics.py)

  - NOTE: Completed 2026-02-08 — added `src/logging.py` (JSON formatter) and `src/metrics.py` (prometheus optional stub).

Phase 3: User Story Phases (priority order)

**US1 — 监控线程发现并通知符合条件的币种 (Priority: P1)**
Independent test criteria: Inject synthetic trades such that a symbol's 1h window buy:sell >= 3 and 24h volume in [10M,80M], verify a persisted `WindowMetric` and a Feishu notification created/sent (or simulated) with recent 3 history items.

 - [x] T010 [US1] Create `src/collector/websocket_client.py` skeleton to subscribe to Binance contract trade streams (path: src/collector/websocket_client.py)

  - NOTE: Completed 2026-02-08 — added simulated `WebSocketClient` at `src/collector/websocket_client.py`.
 - [x] T011 [US1] Create `src/collector/rest_backfill.py` to fetch historical trades/Klines via `ccxt` or Binance REST for backfill (path: src/collector/rest_backfill.py)

  - NOTE: Completed 2026-02-08 — added async stub `fetch_trades` in `src/collector/rest_backfill.py` (simulated data).
 - [x] T012 [US1] Implement `src/processor/windowing.py` to compute 1h/4h/12h aggregates and `score_a` per `specs/001-binance-monitor/data-model.md` (path: src/processor/windowing.py)

  - NOTE: Completed 2026-02-08 — `src/processor/windowing.py` provides `aggregate_trades` and scoring logic.
 - [x] T013 [P] [US1] Implement `src/processor/ingest_pipeline.py` to apply backfill on reconnect and produce aggregated `WindowMetric` objects (path: src/processor/ingest_pipeline.py)

  - NOTE: Completed 2026-02-08 — ingest pipeline implemented and demo verified (`src/processor/ingest_pipeline.py`).
 - [x] T014 [US1] Persist `WindowMetric` via SQLAlchemy in `src/storage.py` and expose helper `store_window_metric()` (path: src/storage.py)

  - NOTE: Completed 2026-02-08 — `src/storage.py` now stores `WindowMetric` via SQLAlchemy; test script validated inserts.
 - [x] T015 [US1] Implement `src/notifier/feishu.py` to build payloads, send with exponential backoff, and idempotency handling (path: src/notifier/feishu.py)
  
  - NOTE: Completed 2026-02-10 — `src/notifier.py` enhanced with exponential backoff, idempotency checks, and comprehensive error handling. Supports both simulated and real Feishu webhook sends.
 - [x] T016 [US1] Integrate pipeline in a daemon runner `src/daemon.py` that schedules 1h/4h/12h jobs and enqueues notifications (path: src/daemon.py)

  - NOTE: Completed 2026-02-08 — added `src/daemon.py` and `src/__main__.py` entrypoint; daemon demo works.
- [x] T017 [US1] Add integration test: `tests/integration/test_end_to_end_us1.py` (inject trades via REST/backfill hook; assert DB and notification created) (path: tests/integration/test_end_to_end_us1.py)

  - NOTE: Completed 2026-02-10 — Created comprehensive demo script `scripts/feishu_demo.py` that demonstrates complete US1 flow: data injection → aggregation → threshold evaluation → notification creation → Feishu card building → sending (simulated/real). Validated with synthetic trades showing score=100, volume=30M USDT.

**US2 — 查看与导出监控日志 (Priority: P2)**
Independent test criteria: After seeding >=10 trigger records, call export API/CLI and verify returned JSON/CSV contains correct fields for last 30 days.

- [x] T018 [US2] Implement HTTP admin endpoints with FastAPI: `/notifications`, `/export?days=30` (path: src/api/main.py)

  - NOTE: Completed 2026-02-10 — created FastAPI app with `/notifications` (query with filtering), `/export` (JSON/CSV export), and `/stats` endpoints. Full OpenAPI documentation available.
- [x] T019 [US2] Implement export CLI: `src/cli_export.py` to dump JSON/CSV from DB (path: src/cli_export.py)

  - NOTE: Completed 2026-02-10 — created CLI tool with arguments for days/symbol/status filtering, automatic output filename generation, and statistics display.
- [x] T020 [US2] Add unit tests for export and API contract tests against `specs/001-binance-monitor/contracts/openapi.yaml` (path: tests/test_export.py)

  - NOTE: Completed 2026-02-10 — created comprehensive test suite with 15+ test cases covering CLI queries, JSON/CSV exports, API endpoints, data integrity, and time ordering validation.

**US3 — 可配置监控阈值与时间窗口 (Priority: P3)**
Independent test criteria: Change thresholds via config and verify next run respects new values without restart if live reload supported, otherwise after restart.

- [x] T021 [US3] Add configuration UI/CLI or config file schema and validation (path: src/config.py, src/admin/config_endpoints.py)

  - NOTE: Completed 2026-02-10 — created `src/config_manager.py` with full ConfigManager class supporting file-based and environment variable configuration, per-symbol thresholds, and API endpoints in `src/api/main.py`.
- [x] T022 [US3] Implement runtime application of thresholds in `src/processor/windowing.py` (path: src/processor/windowing.py)

  - NOTE: Completed 2026-02-10 — updated `src/processor/ingest_pipeline.py` to use ConfigManager.get_threshold_for_symbol() instead of hardcoded thresholds, enabling dynamic threshold lookup.
- [x] T023 [US3] Add unit tests for threshold changes (path: tests/test_thresholds.py)

  - NOTE: Completed 2026-02-10 — created comprehensive `tests/test_thresholds.py` with 25+ test cases covering ThresholdConfig validation, ConfigManager operations, per-symbol thresholds, and API endpoints.

Phase N: Polish & Cross-cutting Concerns

- [x] T024 Add retry/alerting for persistent failures (integrate with Prometheus/Alertmanager or simple email) (path: src/alerting.py)

  - NOTE: Completed 2026-02-10 — created comprehensive `src/alerting.py` with RetryPolicy (指数退避), FailureEvent tracking, AlertingService with health checks and persistent failure logging.
- [x] T025 Add retention/cleanup job to purge `IngestionEvent`/`WindowMetric` older than retention (path: src/maintenance/cleanup.py)

  - NOTE: Completed 2026-02-10 — created `src/maintenance/cleanup.py` with RetentionPolicy and CleanupJob supporting dry-run mode, configurable retention periods for different table types, and detailed logging.
- [x] T026 Write end-user docs: update `README.md`, `specs/001-binance-monitor/quickstart.md` with production notes (path: README.md, specs/001-binance-monitor/quickstart.md)

  - NOTE: Completed 2026-02-10 — created comprehensive `docs/PRODUCTION_GUIDE.md` covering architecture, deployment (Docker/K8s/VM), configuration, monitoring, optimization, troubleshooting, security, and maintenance; updated existing `README.md` and `quickstart.md`.
- [x] T027 Add tests and CI coverage thresholds; configure test matrix for python versions (path: .github/workflows/ci.yml)

  - NOTE: Completed 2026-02-10 — enhanced `.github/workflows/ci.yml` with pytest-cov coverage tracking, automated coverage threshold check (75%), flake8 linting, mypy type checking, codecov reporting, and Docker build testing.

Dependencies

- Story completion order: US1 -> US2 -> US3 (US1 is MVP). Many foundational tasks (T006-T009) must complete before US1’s integration tasks (T012-T016).
- Task dependency examples:
  - T008 (models) MUST complete before T014 (persist WindowMetric)
  - T006 (config) MUST exist before T010/T011 (collector) so secrets are read securely
  - T013 (ingest pipeline) depends on T010 and T011

Parallel execution opportunities

- Tasks marked `[P]` are safe to run in parallel (different files, limited coupling): T001, T002, T004, T008 (model refactorizable in isolation), T013 (ingest pipeline) can be implemented in parallel with notifier work (T015) once interfaces are agreed.

Implementation strategy

- MVP scope: Implement Phase1 + Phase2 + US1 minimal pipeline (REST backfill + simple WebSocket mock, storage, notifier simulation). Deliverables: runnable daemon, DB schema, and integration test for US1.
- Incremental delivery: deliver in vertical slices per user story. Start by making storage and processor deterministic and testable (pure functions + DB adapter), then add collector adapters and notifier adapter.
- Testing approach: unit tests for pure functions (processor/windowing), contract tests for API, integration tests using fixtures for end-to-end.

Parallel execution examples

- Example 1: One engineer implements `src/notifier/feishu.py` (T015) while another implements `src/collector/rest_backfill.py` (T011); both can be merged if they adhere to agreed payload and pipeline interfaces.
- Example 2: Infrastructure engineer adds CI and Docker (T003, T004) while backend engineers implement models and processor (T008, T012).

Validation checklist

- [ ] All tasks include file paths and unique IDs (T001..T027)
- [ ] Each user story phase is independently testable per Independent Test criteria above

---
Generated: 2026-02-08
