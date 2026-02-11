<!--
Sync Impact Report

- Version change: none (template) → 1.0.0
- Modified principles:
	- (new) 监控优先：禁止自动交易与仓位管理
	- (new) 完整可审计：记录每次监控循环与所有策略信号
	- (new) 最小权限：只允许只读交易所接口，禁止交易密钥保存
	- (new) 可解释性：策略必须可解释并在触发时包含计算指标与阈值
	- (new) 模块化设计：采集/调度/策略/日志/通知相互独立
	- (new) 配置驱动：禁止在代码中硬编码币种/阈值/Webhook 等
	- (new) 鲁棒性：外部调用需超时与重试，单币种失败不可影响整轮
	- (new) 可复现性：相同数据与配置必须产生相同结果
	- (new) 插件化策略：新增策略以插件方式接入，不修改现有策略逻辑
	- (new) 告警格式：每条告警包含币种、时间戳、策略名、关键指标、原始数值与阈值
- Added sections: `Security & Access Controls`, `Development Workflow & Specs`, `Non-Functional Requirements`
- Removed sections: none
- Templates requiring updates:
	- ⚠ .specify/templates/plan-template.md (needs Constitution Check gates updated)
	- ⚠ .specify/templates/spec-template.md (must require mandatory FRs and reproducibility checks)
	- ⚠ .specify/templates/tasks-template.md (must include tasks for observability, config-driven gating, plugin scaffolding)
	- ⚠ .specify/templates/commands/*.md (commands folder not present; create or update command docs)
- Follow-up TODOs:
	- TODO(COMMANDS): Add or update `.specify/templates/commands/*` to reference constitution gates and workflow commands.
	- TODO(RUNBOOK): Create a runtime runbook that enforces read-only key checks before deployment.

-->

# 币安合约市场监控与告警系统 Constitution

## Core Principles

### 监控优先 — 禁止自动交易（NON-NEGOTIABLE）
本系统的唯一职责是行情监控与告警。系统 MUST NOT 执行任何自动下单、资金管理或仓位控制逻辑。

### 完整可审计 — 记录与不可静默失败
系统 MUST 记录每一次监控循环（含时间戳、输入数据快照、调度上下文）和每一次触发的策略信号。任何错误或异常 MUST 被记录并显式上报，不能被悄悄忽略。

### 最小权限访问 — 只读交易所接口
系统与交易所交互时 ONLY 使用只读权限的 API。项目中不得保存或使用具有交易/下单权限的密钥或凭证。

### 可解释性与可验证触发
所有策略 MUST 可解释（explainable）。每一次触发的告警必须包含用于决策的计算指标、原始数值和触发阈值，足以让审计者重算并验证触发原因。

### 模块化设计
系统架构 MUST 将数据采集、调度、策略评估、日志记录与通知实现为独立模块，模块间通过明确定义的接口通信，保证可替换性与可测试性。

### 配置驱动（禁止硬编码）
所有行为由配置文件控制（YAML/JSON/TOML 等）。代码中 MUST NOT 硬编码币种、阈值、Webhook 地址或运行时策略开关。默认配置与示例配置应作为独立文件提交。

### 外部调用鲁棒性
所有外部接口调用（含交易所、第三方通知服务） MUST 配置超时与重试策略。单个币种或单个外部请求失败 MUST NOT 中断当前监控轮次或导致全局失败。

### 可复现性
在相同的数据输入和相同配置下，系统运行结果 MUST 可复现。记录的输入快照与配置版本应能还原当次运行以便重现结果。

### 插件化策略接入
新增策略应以插件形式接入（例如策略包、策略接口实现），不得通过修改现有策略逻辑实现新策略。插件接入点与生命周期由文档规范化。

### 告警最小信息集
每一条告警消息 MUST 包含：币种（symbol）、时间戳（ISO 8601）、策略名称、关键计算指标、原始数值与阈值、可选的调试上下文（如采样数据引用）。

## Security & Access Controls
 - 禁止保存具有交易权限的密钥（包括在 CI/Secrets 管理中）。
 - 部署前须执行只读密钥校验（deployment check）。
 - 所有外部凭据访问通过受控机密管理系统；审计日志必须记录凭据访问尝试。

## Development Workflow & Specs
 - 所有新功能 MUST 先编写规格说明（`spec.md`）并通过宪章检查（Constitution Check）后方可进入实现阶段。
 - 代码变化需通过代码审查、单元测试与集成测试；关键路径（数据采集、策略评估、通知）需有端到端回归测试或契约测试。

## Non-Functional Requirements
 - 可观测性：模块需产出结构化日志与必要的度量（latency、error-rate、retry-count、processed-per-cycle）。
 - 配置管理：应支持配置版本号与回滚机制。
 - 性能：单轮监控应在可接受的 SLA 内完成（由实现时在 plan.md 中明确）。

## Governance

修订与合规：本宪章优先于其他项目惯例。任何对宪章的修改 MUST 提交修订说明、影响评估与回滚计划，并经项目核心维护者批准。

版本控制规则：采用语义化版本号 `MAJOR.MINOR.PATCH`。
 - MAJOR 增加：当原则被移除或不兼容地重定义时（重大治理变更）。
 - MINOR 增加：当添加新原则或显著扩展现有原则时（新增约束）。
 - PATCH 增加：文字表述修正、澄清或非语义性改动。

合规审查：每次主要功能合并前，PR 必须包含宪章合规检查清单，审查者需在合并记录中确认通过。

**Version**: 1.0.0 | **Ratified**: 2026-02-08 | **Last Amended**: 2026-02-08
