# World Cup Prediction Agent

这是一个面向 AI Agent 应用开发求职展示的世界杯冠军预测项目。

## 当前状态

**完整设计与实施计划已就绪，产品代码尚未实施。**

仓库中的 Markdown 代码块是给 Coding Agent 的实施规格，不代表已经通过运行验证。任何 Agent 都必须逐 Task 执行测试、实现、复验和提交，不能把计划中的预期输出写成验收结果。

## 交给 ZCode 时从这里开始

1. 阅读 [`docs/ZCODE_HANDOFF.md`](docs/ZCODE_HANDOFF.md)；
2. 阅读 [`完整产品交接设计`](docs/superpowers/specs/2026-07-16-complete-product-handoff-design.md)；
3. 严格按交接文档中的计划顺序执行；
4. 每个计划的 Completion Gate 通过后再进入下一个计划；
5. 最终以 `system-integration-acceptance` 计划生成的验收报告为完成依据。

## 文档导航

### 总规范

- [`docs/ZCODE_HANDOFF.md`](docs/ZCODE_HANDOFF.md)：Coding Agent 执行入口、顺序、权限与停止条件
- [`docs/superpowers/specs/2026-07-16-complete-product-handoff-design.md`](docs/superpowers/specs/2026-07-16-complete-product-handoff-design.md)：完整产品单一事实源
- [`docs/TECHNICAL_REPORT_MAPPING.md`](docs/TECHNICAL_REPORT_MAPPING.md)：原技术报告保留、修订与替代关系

### Agent 设计与基础计划

- [`Agent Workbench 设计`](docs/superpowers/specs/2026-07-15-agent-workbench-design.md)
- [`Agent Runtime Foundation`](docs/superpowers/plans/2026-07-15-agent-runtime-foundation.md)
- [`Agent Workbench UI`](docs/superpowers/plans/2026-07-15-agent-workbench-ui.md)

### 完整产品补充计划

- [`Prediction Engine`](docs/superpowers/plans/2026-07-16-prediction-engine.md)
- [`FIFA 2026 Tournament Simulator`](docs/superpowers/plans/2026-07-16-tournament-simulator.md)
- [`Real LLM Agent Integration`](docs/superpowers/plans/2026-07-16-llm-agent-integration.md)
- [`Prediction Product UI`](docs/superpowers/plans/2026-07-16-prediction-product-ui.md)
- [`System Integration and Acceptance`](docs/superpowers/plans/2026-07-16-system-integration-acceptance.md)

## 最终产品范围

- 历史国家队数据快照与防信息泄漏；
- 加权 Elo、Poisson、Bivariate Poisson、Dixon-Coles；
- ML 概率校正、融合、artifact 与 2022 回测；
- 48 队、12 组、最佳第三、Annexe C、104 场模拟；
- 真实 LLM Orchestrator、Tool Registry、Evidence、Checkpoint、Replay；
- 冠军页、赛事树、比分热力图、球队概率、回测页；
- Agent Workbench、故障恢复、人工审批和六分钟求职演示；
- 离线 Portfolio 模式、Docker、CI 和可审计验收报告。

## 重要边界

- LLM 不计算概率、比分或排名；
- 不展示原始 Chain of Thought；
- Demo fixture 不能冒充真实模型评估；
- 预测结果必须显示数据、模型、规则和预测截止时间；
- 当前日期之后或预测截止时间之后的数据不能回流到冻结赛前预测。
