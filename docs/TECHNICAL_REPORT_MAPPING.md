# 原技术报告内容映射与裁决

## 1. 目的

原技术报告现已完整归档为 [`docs/archive/TECHNICAL_REPORT_ORIGINAL.md`](archive/TECHNICAL_REPORT_ORIGINAL.md)。它提供了完整的预测业务构想，但其中的 Agent 架构、供应商选择、思考链展示和部分产品表述与最终求职项目设计冲突。本文件说明哪些内容继续实现、由哪份计划负责，以及哪些内容已被替代。

Coding Agent 不再依赖仓库外文件即可了解原始方案，但归档报告只用于背景与设计演进。其有效要求已经进入完整产品设计和实施计划；发生冲突时，以 `docs/ZCODE_HANDOFF.md` 规定的优先级为准。

## 2. 逐章映射

| 原报告章节 | 状态 | 最终落点 |
|---|---|---|
| 摘要、项目目标 | 保留 | 完整产品交接设计 §1、README 产品范围 |
| 48 队、12 组、104 场、最佳第三 | 保留并版本化 | Tournament Simulator Tasks 1-8 |
| Annexe C 495 组合 | 保留，禁止推测 | Tournament Simulator Task 3 |
| 数据源与时间切分 | 保留并强化 hash/cutoff | Prediction Engine Tasks 2、8、9 |
| 数据快照与版本 | 保留并形成 manifest | Prediction Engine Tasks 1、2、6 |
| 加权 Elo | 保留 | Prediction Engine Task 3 |
| Poisson / Bivariate / Dixon-Coles | 保留 | Prediction Engine Tasks 4、5 |
| 四模型 ML + 集成 | 分层实现 | Logistic 为必选 baseline；GBDT 为 full-training profile |
| 融合与 Isotonic 校准 | 保留 | Prediction Engine Tasks 6、7 |
| 淘汰赛加时与点球 | 保留并策略化 | Tournament Simulator Task 5 |
| RPS / Log Loss / Brier / 校准曲线 | 保留 | Prediction Engine Task 8、Product UI Task 6 |
| 2022 卡塔尔回测 | 保留并精确定义窗口 | Prediction Engine Task 8 |
| 五 Agent + Orchestrator | 替代 | 单 Orchestrator + Tool Registry，见 Real LLM Agent Integration |
| DeepSeek-V4 / R1 固定供应商 | 替代 | OpenAI-compatible provider adapter，供应商由配置决定 |
| `<think>` 显式思考链 | 删除 | Decision Record + Evidence；禁止原始 Chain of Thought |
| 单场预测卡 | 保留 | Product UI Task 5 |
| 赛事树 | 保留，且不等同 Run Graph | Product UI Task 4 |
| 冠军概率榜 | 保留 | Product UI Task 3 |
| 球队雷达图 | 修订 | 使用真实阶段概率和比赛路径，不展示无数据支持的阵容完整度 |
| 推理面板 | 强化 | Agent Workbench + Evidence + Replay |
| 2022 回测专区 | 保留 | Product UI Task 6 |
| React + ECharts | 保留 | Product UI Tasks 1、3、5、6 |
| Tesla V100 | 非必需 | full-training 可使用 GPU；baseline 与 Portfolio 必须 CPU 可运行 |

## 3. 保留的核心方法论

### 3.1 LLM 与计算分离

“LLM 负责决策与解释，确定性代码负责所有计算”继续作为最高原则。任何 Elo、比分、概率、排名、模拟汇总和回测指标都来自 Python 工具及版本化 artifacts。

### 3.2 概率而非确定性结论

产品输出是冠军概率、逐阶段概率、比分分布、最可能路径和不确定性，不使用“必然夺冠”等语言。

### 3.3 防信息泄漏

所有特征是赛前特征；Elo 在当前比赛后才更新；2022 回测模型训练截止 2022-11-19；Portfolio Frozen 预测截止 2026-06-10 23:59:59Z。

### 3.4 可复现

预测绑定 data/model/rules/fixture 版本、hash、截止时间、随机种子、模拟次数和 Evidence IDs。

## 4. 已修订的内容

### 4.1 ML 交付范围

原报告要求 Logistic、LightGBM、XGBoost、CatBoost 全部运行。最终设计将 Logistic 设为必选 baseline，使无 GPU、无可选库的 CI 和面试电脑仍可重建。三种 GBDT 保留在 full-training profile，代码和比较流程必须实现，但大型训练不是 Portfolio 必选运行项。

### 4.2 实时数据

原报告面向赛前预测。当前项目必须明确运行模式：Portfolio 使用冻结赛前快照；`as_of` 模式才能锁定某时刻之前的真实赛果。两种模式不得混淆。

### 4.3 球队雷达图

原报告提出“阵容完整度”，同时又明确不采集稳定的阵容/伤停数据。最终产品不展示这一无证据指标。可展示 Elo、近期状态、预期进球、失球和阶段晋级概率，但每项必须绑定 Evidence。

### 4.4 Agent 数量

DataCollector、DataAnalyzer、Predictor、TournamentSimulator、Explainer 不再是五个平级 LLM。它们成为一个 Orchestrator 下的确定性工具或服务边界。这样仍保留职责分离，同时提升测试、状态恢复和证据审计能力。

## 5. 原报告没有充分定义、现已补齐的内容

- 明确仓库模块与依赖方向；
- DataSnapshotManifest 与 ModelArtifactManifest；
- MatchPrediction、TournamentForecast 与 EvidenceBundle 合同；
- 495 行规则表的来源、hash 和加载失败策略；
- deterministic batch seed 与 convergence record；
- Agent Event、Checkpoint、Replay 与 Human Approval；
- LLM provider fallback、JSON repair 和 secret redaction；
- Forecast REST API 与稳定错误码；
- 产品路由、可访问图表、移动端和 E2E；
- 离线 bundle、Docker、CI、安全、数据许可与验收报告；
- ZCode 的执行顺序、停止条件和完成定义。

## 6. 最终结论

原技术报告的预测算法与结果产品内容没有被删除，而是被拆入可测试的 Prediction Engine、Tournament Simulator 和 Product UI 计划。被删除的是不适合可靠 Agent 产品的实现方式：多 LLM 人格群聊、供应商硬绑定和原始思考链展示。
