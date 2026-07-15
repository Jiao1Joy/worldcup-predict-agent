# ZCode Coding Agent 交接指南

## 1. 任务

把本仓库的规格和计划实现为一个完整、可运行、可复现、可视化的世界杯冠军预测 Agent 项目。

你不是在生成原型截图，也不是在把固定概率包装成 Agent。最终系统必须包含真实预测领域代码、正确赛制模拟、Agent Runtime、普通用户预测页面、Agent Workbench、离线演示和自动化验收。

## 2. 开始前必读顺序

1. `docs/superpowers/specs/2026-07-16-complete-product-handoff-design.md`
2. `docs/TECHNICAL_REPORT_MAPPING.md`
3. `docs/superpowers/specs/2026-07-15-agent-workbench-design.md`
4. 本文件下方的实施计划顺序

聊天记录、参考项目和旧技术报告不能覆盖上述文件。

## 3. 实施计划顺序

严格顺序如下：

| 阶段 | 计划 | 进入下一阶段的条件 |
|---|---|---|
| 1 | `2026-07-15-agent-runtime-foundation.md` | Backend Plan Completion Gate |
| 2 | `2026-07-15-agent-workbench-ui.md` | Frontend Plan Completion Gate |
| 3 | `2026-07-16-prediction-engine.md` | Prediction Engine Completion Gate |
| 4 | `2026-07-16-tournament-simulator.md` | Tournament Completion Gate |
| 5 | `2026-07-16-llm-agent-integration.md` | Real Agent Completion Gate |
| 6 | `2026-07-16-prediction-product-ui.md` | Product UI Completion Gate |
| 7 | `2026-07-16-system-integration-acceptance.md` | System Completion Gate 与 Acceptance Report |

所有文件位于 `docs/superpowers/plans/`。

阶段 1 和阶段 2 使用 demo tools/fixtures 建立 Agent 基础设施是允许的；阶段 5 必须把产品依赖切换到真实 Prediction/Tournament services；最终产品不能通过 `build_demo_registry()` 生成冠军预测。

## 4. 每个 Task 的执行协议

对每个 Task 单独执行：

1. 阅读 Task 的全部 Files 与 Steps；
2. 检查工作树，保留用户已有修改；
3. 写失败测试；
4. 运行指定命令并确认测试按预期失败；
5. 写最小实现；
6. 运行指定测试、相关回归测试和静态检查；
7. 只有测试真实通过后才勾选 Step；
8. 使用计划给出的提交信息提交；
9. 报告实际输出，不把 Expected 当作实际结果；
10. 一个 Task 完成并审查后才进入下一个 Task。

如果计划代码与已安装库的真实 API 不一致，保留测试表达的行为合同，查阅官方文档后修正实现，并在提交信息或工程记录中说明差异。不得为了复制代码块而绕开编译器或测试。

## 5. 文档冲突裁决

### 5.1 Agent 架构

最终架构是：一个 Orchestrator + Tool Registry + Shared Run State + Critic + Evidence Store。

禁止实现：

- 五个平级 LLM 人格互相聊天；
- `<think>` 或隐藏 Chain of Thought 展示；
- LLM 直接计算 Elo、比分、概率、排名；
- 仅靠前端动画伪造动态分支或失败恢复。

### 5.2 预测算法

原技术报告的数据、Elo、三种进球模型、校准、融合、2022 回测、2026 模拟和结果页面需求必须实现。精确模块边界和验收以新总设计与新计划为准。

### 5.3 LLM 供应商

实现 OpenAI-compatible provider adapter。DeepSeek、GLM 或其他兼容服务通过环境变量配置；领域包不能依赖供应商 SDK。没有 API key 时必须使用 deterministic planner 和 template explainer。

### 5.4 赛制与时间

- Portfolio Frozen cutoff 固定为 `2026-06-10T23:59:59Z`；
- 赛后真实结果不能进入冻结赛前预测；
- 赛制与 fixtures 来自版本化官方文件；
- Annexe C 必须有 495 个已校验组合，不能用算法猜配对；
- 当前实际赛况只能进入显式 `as_of` 模式。

## 6. 允许的自主决策

你可以自主决定：

- 小文件的内部函数拆分；
- 不改变公共合同的重构；
- 测试 fixture 的虚构球队名称；
- CSS 细节和非品牌字体 fallback；
- 在满足既定行为时升级 patch/minor 依赖；
- CI 运行在 Windows 或 Ubuntu，只要本地 PowerShell 入口保留。

## 7. 必须停止并报告的情况

出现以下情况不得猜测：

- 无法从 FIFA 官方材料取得或校验 495 行 Annexe C；
- 数据源许可不允许仓库内再分发所需 fixture；
- 官方赛制文件与规格中的不变量冲突；
- 需要付费 API、密钥或外部部署权限才能通过必选 Portfolio 验收；
- 训练数据缺少必需列且无确定映射；
- 用户已有修改与计划要覆盖的文件产生实质冲突；
- 两个更高优先级规格互相矛盾；
- 固定 seed 仍无法复现且原因来自并行或第三方模型非确定性。

报告时给出：阻塞步骤、已验证证据、可选方案及各自影响。不要仅说“无法完成”。

## 8. 外部输入与不能伪造的内容

以下输入不一定提交在仓库中：

- 完整 martj42 历史赛果下载；
- 完整训练后的大型 GBDT artifacts；
- LLM API key；
- 可选线上部署凭证。

仓库仍必须包含：

- 数据 schema、下载/读取命令、许可与 hash；
- 小型合规 fixture；
- baseline 模型重建命令；
- versioned rules 与 Annexe C；
- 离线 forecast/backtest/run/evidence bundle；
- 不使用密钥的完整 Portfolio 演示。

禁止硬编码或编造：

- 2022 回测指标；
- 冠军概率；
- 训练集行数或 hash；
- FIFA 规则表；
- “测试通过”状态；
- LLM token/cost；
- 实际联网数据的获取时间。

## 9. 完成定义

只有 `docs/ACCEPTANCE_REPORT.md` 对所有必选 Portfolio 条目标记 PASS，项目才完成。

至少包含：

- 后端全部 pytest 与 Ruff 通过；
- 前端 Vitest、build、Playwright 通过；
- 495/495 Annexe C；
- 每次赛事 104 场；
- 比分矩阵与胜平负一致；
- artifact/data/rules hash 一致；
- 固定 seed 结果 hash 一致；
- 无 LLM key 完成真实领域预测；
- published claims Evidence coverage 100%；
- Replay 零外部调用；
- Docker Compose health 与 smoke test 通过；
- README、数据来源、安全说明、演示脚本齐全。

Full Training 与 Live LLM 是可选运行项，可以在验收报告标记 `NOT RUN`，但对应代码、配置、测试替身和文档必须存在。不能标记为 PASS。

## 10. 推荐给 ZCode 的启动指令

```text
你正在实现 worldcup-predict-agent。先完整阅读 docs/ZCODE_HANDOFF.md 和其中列出的最高优先级设计。严格按七份实施计划顺序逐 Task 执行，遵守 TDD、Completion Gate 和频繁提交。不要一次生成全部项目，不要把 Expected 输出当作实际结果，不要展示 Chain of Thought，不要用 demo registry 生成最终产品预测。遇到交接指南第 7 节的停止条件时，携带证据报告；否则自主推进，直到 System Completion Gate 与 ACCEPTANCE_REPORT 完成。
```

## 11. 当前交接状态

交接时只有规格和实施计划已完成。源码、数据规则表、模型 artifacts、测试结果、容器与 Acceptance Report 需要 Coding Agent 按计划创建。README 中的“当前状态”是事实，不得在首个任务前改成“项目已完成”。
