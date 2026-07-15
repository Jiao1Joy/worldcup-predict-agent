# 世界杯预测 Agent 完整产品交接设计

日期：2026-07-16

状态：已确认；用户授权 Codex 代为完成规格审阅

目标读者：ZCode、GLM-5.2 Coding Agent、后续维护者与面试评审

## 1. 目标

本规格把“世界杯预测业务内核”和“Agent 工作台”合并为一个可实现、可验证、可演示的完整产品。最终交付必须同时具备：

- 可复现的数据快照与赛前特征；
- 真实的单场比分、赛果概率与锦标赛模拟；
- 正确的 2026 世界杯赛制和 495 种最佳第三名映射；
- 一个 LLM Orchestrator，使用确定性工具完成计算；
- 可追溯的 Decision Record、Evidence、Checkpoint、Replay 与人工审批；
- 面向普通用户的预测结果页，以及面向求职展示的 Agent Workbench；
- 离线演示模式和真实运行模式；
- 自动化测试、容器化启动、数据与模型版本清单。

“完整”不等于提交训练数据、API 密钥或大型训练产物。代码仓库必须提供取得数据、训练模型、生成产物、启动服务和验证结果的完整路径。

## 2. 文档优先级

Coding Agent 遇到冲突时必须按以下顺序裁决：

1. 本规格；
2. `docs/superpowers/plans/2026-07-16-*.md` 新增实施计划；
3. `docs/superpowers/specs/2026-07-15-agent-workbench-design.md`；
4. `docs/superpowers/plans/2026-07-15-agent-runtime-foundation.md`；
5. `docs/superpowers/plans/2026-07-15-agent-workbench-ui.md`；
6. 原始 `TECHNICAL_REPORT.md`，仅作为预测算法与产品需求来源；
7. 参考项目和临时代码。

以下冲突已经裁决，不允许 Coding Agent 自行改回：

| 原方案 | 最终方案 |
|---|---|
| 五个平级 LLM Agent | 一个 Orchestrator，通过 Tool Registry 调用领域工具 |
| 展示 `<think>` 原始思考链 | 只展示结构化 Decision Record 与 Evidence |
| LLM 参与概率计算 | LLM 只解析、路由和解释；所有数值由确定性代码生成 |
| Demo 随机概率作为最终结果 | Demo Tool 仅用于 Agent 基础设施测试；产品默认使用真实 Prediction Engine |
| Agent Run Graph 代替赛事树 | 两者都实现：Run Graph 展示执行过程，Tournament Bracket 展示赛事结果 |

## 3. 产品运行模式

### 3.1 Portfolio Frozen 模式

默认演示模式。使用提交到仓库的小型、不可变 fixture 和预计算模型产物，不依赖外网或 LLM API，也能完整浏览预测、赛程树、Evidence 和 Replay。

固定要求：

- `forecast_cutoff=2026-06-10T23:59:59Z`；
- 2026-06-11 之后的真实赛果不得进入特征；
- 使用固定 `random_seed=20260611`；
- 所有页面显示 `data_version`、`model_version` 和 `forecast_cutoff`；
- fixture 标明是“冻结赛前预测”，不能伪装成实时结果。

### 3.2 Rebuild 模式

从公开历史赛果重新构建数据快照、训练模型、完成 2022 回测并生成 2026 预测。该模式用于证明项目不是硬编码。

### 3.3 As-of Forecast 模式

允许传入任意 `as_of` 时间。时间之前已经完成的比赛作为 locked result，未完成比赛继续预测。任何特征、排名和模型输入都不得读取 `as_of` 之后的数据。

### 3.4 Agent Live 模式

在 Prediction Engine 可用时启用真实 LLM Orchestrator、SSE、故障注入和人工审批。LLM 不可用时自动执行确定性默认图，并使用模板解释。

## 4. 总体架构

```text
Public Data / Versioned Fixtures / Official Rules
                    ↓
       Data Pipeline + Snapshot Manifest
                    ↓
 Elo + Goal Models + ML Calibration + Backtest
                    ↓
        Versioned Prediction Artifacts
                    ↓
 Match Predictor → Tournament Simulator → Forecast Bundle
                    ↓                         ↓
          Evidence Store              Result Read Models
                    ↓                         ↓
       Agent Orchestrator              Result Product UI
                    ↓                         ↓
      Run Events / Checkpoints ─────── Agent Workbench
```

边界原则：

- `prediction` 包不依赖 FastAPI、LangGraph 或 React；
- `tournament` 只消费 `MatchPredictor` 协议，不了解具体模型；
- `agent` 只通过 Tool Contract 调用 prediction/tournament 服务；
- `api` 负责传输与错误映射，不承载领域计算；
- `frontend` 只消费版本化 API，不复制排名或概率算法；
- 所有发布数值必须存在 Evidence ID。

## 5. 仓库目标结构

```text
backend/
├── pyproject.toml
├── src/worldcup_agent/
│   ├── data/                 # 下载、标准化、赛前切分、快照
│   ├── prediction/           # Elo、进球模型、ML、融合、校准
│   ├── backtest/             # 2022 样本外评估与报告
│   ├── tournament/           # 排名、Annex C、淘汰赛与蒙特卡洛
│   ├── artifacts/            # manifest 与运行时加载器
│   ├── tools/                # 领域服务的 Agent adapters
│   ├── runtime/              # LangGraph、Reducer、Policy、Replay
│   ├── evidence/             # Evidence 与发布校验
│   ├── storage/              # SQLite run/event/evidence
│   └── api/                  # Forecast 与 Agent Run API
├── rules/fifa_2026/          # 赛制版本、槽位、Annex C 表
├── tests/
└── scripts/
frontend/
├── src/
│   ├── api/
│   ├── domain/
│   ├── pages/
│   │   ├── ForecastOverviewPage.tsx
│   │   ├── MatchDetailPage.tsx
│   │   ├── TournamentPage.tsx
│   │   ├── BacktestPage.tsx
│   │   └── AgentWorkbenchPage.tsx
│   ├── features/forecast/
│   ├── features/bracket/
│   ├── features/backtest/
│   └── features/agent-run/
└── e2e/
artifacts/
├── manifests/
├── demo/
└── README.md
docs/
└── ZCODE_HANDOFF.md
```

## 6. 数据与产物合同

### 6.1 DataSnapshotManifest

```json
{
  "data_version": "matches-20260610-sha256",
  "source_name": "martj42-international-results",
  "source_uri": "configured-at-build-time",
  "source_sha256": "64-hex-characters",
  "snapshot_cutoff": "2026-06-10T23:59:59Z",
  "row_count": 0,
  "schema_version": "match-v1",
  "created_at": "ISO-8601"
}
```

标准比赛表至少包含：`match_id`、`date`、`home_team`、`away_team`、`home_score`、`away_score`、`tournament`、`city`、`country`、`neutral`。任何衍生特征必须带 `feature_as_of`。

### 6.2 ModelArtifactManifest

```json
{
  "model_version": "forecast-ensemble-v1",
  "data_version": "matches-20260610-sha256",
  "trained_until": "2022-11-19T23:59:59Z",
  "validation_window": ["2022-11-20", "2022-12-18"],
  "selected_goal_model": "dixon_coles",
  "fusion_weights": {"elo": 0.2, "goal": 0.5, "ml": 0.3},
  "calibrator": "isotonic-v1",
  "files": [{"path": "relative/path", "sha256": "64-hex-characters"}],
  "metrics": {"rps": 0.0, "log_loss": 0.0, "brier": 0.0}
}
```

权重和指标示例只定义 schema，不是预设结果；训练命令必须写入真实值。

### 6.3 MatchPrediction

```json
{
  "match_id": "M001",
  "home_team": "Team A",
  "away_team": "Team B",
  "expected_goals": {"home": 1.4, "away": 0.9},
  "outcome_probabilities": {"home": 0.48, "draw": 0.29, "away": 0.23},
  "score_matrix": [[0.0]],
  "top_scores": [{"home": 1, "away": 0, "probability": 0.12}],
  "advance_probabilities": null,
  "model_version": "forecast-ensemble-v1",
  "data_version": "matches-20260610-sha256",
  "evidence_ids": ["MATCH-M001-PRED"]
}
```

不变量：比分矩阵概率和为 1；由比分矩阵汇总出的胜平负与 `outcome_probabilities` 误差小于 `1e-9`。

### 6.4 TournamentForecast

必须包含：

- 104 个 match slots；
- 12 个小组积分榜；
- 48 支球队每阶段晋级概率；
- 冠军概率分布与置信区间；
- 最可能路径；
- 每场 MatchPrediction；
- 模拟次数、随机种子、收敛轨迹；
- data/model/rules/fixture 版本；
- Evidence IDs。

### 6.5 EvidenceBundle

每项 Evidence 包含 `evidence_id`、`kind`、`value`、`unit`、`source`、`version`、`created_at` 和 `content_hash`。解释器只能引用 Bundle 中存在的数字。

## 7. Prediction Engine

### 7.1 数据管道

- 下载或读取 martj42 国际比赛数据；
- schema 校验、球队别名标准化、重复比赛检测；
- 按比赛时间升序生成赛前特征；
- 时间切分，不使用随机拆分；
- 保存 Parquet 快照与 manifest；
- 拒绝 cutoff 之后的记录进入赛前预测。

### 7.2 模型层

最小可交付模型链：

1. 加权 Elo 赛前滚动；
2. 独立 Poisson；
3. Bivariate Poisson；
4. Dixon-Coles；
5. 三种进球模型在 2022 世界杯窗口按 RPS 选优；
6. Logistic Regression 校正基线；
7. 可选 LightGBM/XGBoost/CatBoost adapters；缺少可选依赖时仍能完成基线训练；
8. 非负、和为 1 的融合权重；
9. Isotonic calibration；
10. 9×9 比分矩阵与尾部质量处理。

高级树模型不能阻塞首个可运行版本。默认 CI 使用 Logistic 基线；完整训练 profile 才启用四模型比较。

### 7.3 回测

训练数据截止 2022-11-19；2022-11-20 至 2022-12-18 的世界杯比赛仅用于样本外评估。生成 RPS、Log Loss、Brier、校准分箱和逐场预测。2022 之后的数据不得参与该回测模型训练。

## 8. Tournament Simulator

官方规则以版本化文件保存，不散落在代码中。截至本规格日期，FIFA 官方说明确认：48 队、12 组，每组前两名与 8 支最佳第三名进入 32 强，共 104 场；同分球队先应用相关球队之间的积分与净胜球等规则，最佳第三名使用积分、净胜球、进球、纪律分和 FIFA 排名排序；Annexe C 包含 495 种第三名组合。

实现要求：

- 小组赛每组 6 场，共 72 场；
- 小组排名使用独立、可递归重算的 tie-break engine；
- 最佳第三名比较独立于组内排名；
- Annex C 数据文件覆盖 `C(12,8)=495` 个组合；
- Round of 32 至决赛，以及三四名赛，共 32 场；
- 淘汰赛平局进入加时，仍平进入点球；
- 点球默认 50/50，可通过版本化策略替换；
- 模拟按批次运行并记录冠军概率变化；
- 固定 seed 与相同 artifacts 必须产生完全相同输出。

官方来源：

- <https://www.fifa.com/en/articles/groups-how-teams-qualify-tie-breakers>
- <https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums>

## 9. Agent 与 LLM

### 9.1 单 Orchestrator

默认图：`parse → inspect_snapshot → ensure_artifacts → predict_matches → simulate → critique → explain → publish`。

真实条件边：数据过期、artifact 不匹配、模型分歧、模拟未收敛、Evidence 缺失、工具超时和人工审批。动态节点必须由后端状态触发，不能只在前端插入。

### 9.2 Provider Adapter

定义统一 `LLMProvider`：

- `complete_structured(request, response_schema)`；
- 固定 provider、model、temperature 和 timeout；
- API key 只读环境变量；
- 保存 prompt template version，不保存密钥和隐藏推理；
- JSON schema 失败最多修复一次；
- provider 不可用时执行 deterministic planner。

首版实现 OpenAI-compatible HTTP adapter，使 DeepSeek、GLM 或其他兼容服务只通过配置切换。不得在领域代码中出现供应商 SDK 类型。

### 9.3 可解释输出

输出包含：结论、Observation、Rule、Action、Reason、Evidence IDs、数据与模型版本、不确定性。禁止存储或展示原始 Chain of Thought。

## 10. API

除既有 Run API 外，至少提供：

```text
GET  /api/health
GET  /api/artifacts/current
POST /api/forecasts
GET  /api/forecasts/{forecast_id}
GET  /api/forecasts/{forecast_id}/matches/{match_id}
GET  /api/forecasts/{forecast_id}/bracket
GET  /api/forecasts/{forecast_id}/teams
GET  /api/backtests/2022
POST /api/runs
POST /api/runs/{run_id}/start
GET  /api/runs/{run_id}
GET  /api/runs/{run_id}/events
POST /api/runs/{run_id}/inject-failure
POST /api/runs/{run_id}/approve
```

耗时预测创建返回 `202 Accepted` 与 `forecast_id/run_id`；Portfolio fixture 可以同步加载。错误使用稳定的 `error_code`，不得把 Python traceback 返回给前端。

## 11. 结果产品 UI

### 11.1 普通用户路径

1. Overview：最终冠军、Top 10、最可能决赛、版本与不确定性；
2. Tournament：可缩放的赛事树、各轮比分与晋级概率；
3. Match Detail：胜平负、xG、比分热力图、关键证据；
4. Team Detail：各阶段晋级概率与实力趋势；
5. Backtest：2022 指标、校准图和逐场预测；
6. “查看 Agent 如何得出结论”进入 Workbench。

### 11.2 Agent Workbench

沿用现有设计：Run Bar、Run Graph、Step Inspector、Event Timeline、Replay、故障注入和 Approval。Workbench 使用真实 Forecast Evidence，不再以三支球队随机概率作为产品结果。

### 11.3 可视化技术

- `@xyflow/react`：Agent Run Graph；
- ECharts：冠军榜、比分矩阵、校准图、阶段概率；
- HTML/CSS 或专用 bracket layout：赛事树；
- 所有图表必须提供文本表格或 aria label；
- 390px 移动视口不能产生页面级横向溢出。

## 12. 错误与降级

| 场景 | 行为 |
|---|---|
| 数据下载失败 | 使用已校验缓存；无缓存则阻塞 rebuild |
| 数据 hash 不匹配 | 阻塞训练并记录 manifest error |
| 可选 GBDT 不可用 | 使用 Logistic 基线并在 manifest 标记 degraded |
| 模型 artifact 与数据版本不匹配 | 禁止加载 |
| Annex C 缺少组合 | 启动失败，不允许 fallback 猜测 |
| 模拟 Worker 超时 | checkpoint 恢复、缩小批次、重试 |
| LLM 不可用 | deterministic planner + template explainer |
| Evidence 数字不一致 | 禁止发布并回到 Critic |
| SSE 断线 | 使用 Last-Event-ID 续传 |

## 13. 测试与质量门

### 13.1 单元测试

- Elo 无未来信息、比赛后才更新；
- 三个进球模型矩阵归一；
- 融合权重合法；
- 比分矩阵与赛果概率一致；
- group tie-break 示例；
- 495 个 Annex C 组合全部存在；
- Tool input/output schema；
- Evidence 值和引用一致；
- 前端 reducer、图表 formatter 与可访问性。

### 13.2 集成测试

- 小型 48 队 fixture 完成 104 场；
- 固定 seed 结果 hash 一致；
- 训练 manifest 能被 runtime 加载；
- Forecast API 生成完整 read model；
- Agent run 调用真实领域工具并写入 Evidence；
- LLM 故障时仍完成预测；
- Replay 不调用外部系统。

### 13.3 E2E

- 从 Overview 打开赛事树与单场详情；
- 从预测结果进入 Agent Workbench；
- 注入 timeout，观察恢复；
- 触发数据冲突并审批；
- 打开 Backtest 看到真实 fixture 指标；
- Portfolio 模式断网可运行。

## 14. 实施顺序

严格按以下顺序执行：

1. Prediction Engine；
2. Tournament Simulator；
3. 将真实领域工具接入 Agent Runtime；
4. Forecast Result API 与产品 UI；
5. 真实 LLM Provider 与结构化解释；
6. 系统集成、fixture、容器和验收；
7. 最后才删除或隔离 Demo Tools。

前一个阶段的 completion gate 未通过，不开始下一个阶段。Coding Agent 每完成一个 Task 都必须运行指定测试并提交，不能一次生成全部文件后统一调试。

## 15. 最终验收

交付被视为完整，必须同时满足：

- 一条命令启动 Portfolio 模式；
- 一条命令运行后端与前端完整测试；
- 一条命令从公开数据重建 baseline artifacts；
- 真实预测链不调用 `tools/demo.py`；
- 2022 回测指标来自逐场 fixture，而非硬编码；
- 2026 模拟满足 104 场、495 组合、概率和与固定 seed 不变量；
- 普通用户能看到冠军、比分、赛程树和推理依据；
- 面试官能看到动态路由、失败恢复、Evidence 与 Replay；
- 无 LLM/API key/网络时，Portfolio 模式仍可完整演示；
- README、环境变量示例、数据许可说明、架构图和六分钟演示脚本齐全。

## 16. 非目标

- 不训练通用基础模型；
- 不抓取受限或需要绕过授权的数据；
- 不用实时伤病和俱乐部球员数据阻塞首版；
- 不声称概率预测可以保证赛果；
- 不展示原始隐藏思考链；
- 不实现多个 LLM 人格之间的表演式对话；
- 不把 Demo fixture 当作真实模型评估结果。
