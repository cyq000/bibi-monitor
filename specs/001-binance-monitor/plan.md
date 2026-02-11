# Implementation Plan: 币安合约主动买卖量监控

**Branch**: `001-binance-monitor` | **Date**: 2026-02-08 | **Spec**: ../spec.md
**Input**: Feature specification from `/specs/001-binance-monitor/spec.md`

## Summary

实现一个周期性监控服务：定时（1h/4h/12h）计算币安 USDT 永续合约的主动 taker 买/卖量，基于买/卖比率计算得分A，筛选 24 小时成交额在 10M80M USDT 的币种并在触发时把记录写入持久化存储与发送飞书通知。数据获取采用 WebSocket 实时流 + REST 回补策略；存储策略以轻量化持久化（SQLite）为首选，兼容 Postgres/Redis 以便未来扩展。

## Technical Context

**Language/Version**: Python 3.11 (首选)
**Primary Dependencies**: ccxt (REST)、websockets / aiohttp（WebSocket 客户端）、asyncio、requests、SQLAlchemy、alembic（可选迁移）、uvicorn + FastAPI（用于本地调试和导出接口）、pytest
**Storage**: 首选 SQLite 文件（轻量、无需运维），队列/短期缓存建议使用 Redis（可选）；生产级建议 Postgres + Redis。历史记录保留 90 天。
**Testing**: pytest（单元/集成）、contract tests 用示例数据回放
**Target Platform**: Linux / Windows 可运行（Python 跨平台）；建议以 Docker 容器化以简化部署
**Project Type**: 单一后端服务（CLI / daemon + minimal HTTP admin endpoints）
**Performance Goals**: 支持同时监控 ~200 个合约，处理延迟目标 110 分钟内完成一轮通知（非高频需求）
**Constraints**: 不保存具有下单权限的密钥；所有敏感信息不得提交仓库；遵循宪章的最小权限与可审计性规则
**Scale/Scope**: 初始设计针对 200 币种，长期可扩展到更多币种与多租户

## Constitution Check

GATE: 必须在 Phase 0 之前通过。检查点：

- Principle: 最小权限  **要求** 仅使用只读 API 密钥；禁止在仓库中保存具有下单权限的密钥。
- Principle: 配置驱动  **要求** 不要在源码中硬编码 Webhook 或密钥；应使用受控机密或本地不提交的配置文件并在 README 明确说明。

Current status: VIOLATION FOUND (requires justification)

- Violation: User-provided configuration includes Binance API key/secret and explicit Webhook URLs intended to be stored in a local config file. Constitution policy requires: (1) keys MUST be read-only; (2) secrets MUST be managed outside VCS (secret manager or local config explicitly excluded from VCS).

Action required from requestor before Phase 0 research proceeds:
- Confirm that the provided Binance API key/secret are read-only (market data only) and do NOT allow trading. If they have trading permissions, remove/rotate them and provide read-only keys.
- Confirm you will NOT commit the local config file containing secrets to the repository. Recommended: use environment variables, a `.env` file excluded by `.gitignore`, or a secrets manager (Vault/K8s Secret).

If you confirm the above, Phase 0 research will continue. If not, we must remediate (remove secrets from repo, generate read-only keys, or switch to mocked/test credentials).

## Constitution Re-evaluation (post-Phase0)

- Status: RESOLVED

- Findings:
	- Requestor confirmed the provided Binance API key/secret are read-only (market-data only) and do NOT have trading permissions.
	- Requestor confirmed they will NOT commit local config files containing secrets to the repository; recommended approach (and to be used in examples): environment variables or a local `.env` file that is excluded by `.gitignore`. For production, use a secret manager (Vault/K8s Secret).
	- All generated artifacts (`research.md`, `data-model.md`, `/contracts/*`) avoid embedding secrets; any examples use placeholders.

- Outcome: With the above confirmations and the implementation guidance in this plan, the constitutional gates for minimal privilege and no-commit of secrets are satisfied. Phase 0 may proceed to Phase 1 design artifacts and implementation scaffolding.

Generated on 2026-02-08 — re-evaluated by automation script and documented by agent.

## Project Structure

```
specs/001-binance-monitor/
 spec.md
 plan.md         # this file
 research.md
 data-model.md
 quickstart.md
 checklists/requirements.md

src/
 collector/      # websocket and rest ingestion
 processor/      # windowing, scoring logic
 storage/        # persistence (sqlite/postgres adapters)
 notifier/       # feishu webhook sender with retry/backoff
 cli/            # run, migrate, export
 tests/

```

**Structure Decision**: 单一后端服务（Python），模块化按功能拆分，便于测试与替换实现。

## Complexity Tracking

No constitution violations remain except the secret/key storage decision which requires confirmation from the requestor. Once confirmed, complexity is lowmedium: moderate async ingestion and windowing logic, stable persistence and notifications.
