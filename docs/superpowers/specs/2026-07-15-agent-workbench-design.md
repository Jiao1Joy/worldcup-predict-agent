# 世界杯预测 Agent 工作台设计

日期：2026-07-15

状态：已确认；完整产品范围与优先级见 `2026-07-16-complete-product-handoff-design.md`

目标岗位：AI Agent 应用开发

## 1. 背景与目标

世界杯冠军预测系统已经有明确的确定性计算内核设计：数据快照、概率模型、官方赛制模拟、蒙特卡洛、可追溯解释和可视化。本设计聚焦其中的 Agent 层，目标不是增加更多 LLM 角色，而是让求职面试官能够在 30 秒内看懂系统具备以下能力：

- 根据任务与运行状态规划和选择工具；
- 使用结构化状态而非聊天记录传递上下文；
- 根据观察动态追加步骤、停止或降级；
- 在工具失败后重试并从 checkpoint 恢复；
- 将最终结论绑定到可验证证据；
- 支持人工审批、运行回放和完整审计。

产品主张：**一个 Orchestrator + 确定性工具 + 显式状态 + Critic + Evidence Store，比多个平级 LLM Agent 群聊更可信、更容易测试。**

## 2. 设计决策

### 2.1 选择 Agent 工作台

采用“Agent 工作台型”作为核心展示方式，并在下方嵌入执行时间线。

未选择的方案：

- 纯流程日志：容易理解，但难以证明动态决策和状态管理；
- 多 Agent 群聊：视觉热闹，但容易退化为角色扮演，证据、共享状态和失败恢复不清晰。

### 2.2 单 Orchestrator 架构

不实现五个平级 LLM Agent。数据计算、模型预测、赛事模拟和规则校验由确定性工具负责；LLM 只负责解析目标、路由工具和组织解释。Critic 优先使用确定性规则，必要时再调用 LLM 评议。

### 2.3 不展示原始思考链

界面展示结构化 Decision Record：观察、规则、动作、理由、证据引用和状态差异。原始隐藏思考文本不属于产品输出，也不能作为可验证解释。

## 3. 总体架构

```text
User Request
    ↓
Task Parser → TaskSpec
    ↓
Orchestrator / Planner / Router
    ├── Tool Registry
    ├── Shared Run State
    ├── Checkpoint Manager
    ├── Policy & Guardrails
    ├── Critic
    └── Evidence Store
             ↓
        Evidence Bundle
             ↓
          Explainer
             ↓
      Result API + Agent Trace
```

推荐技术边界：

- 编排：LangGraph 状态图；
- API：FastAPI；
- 实时事件：Server-Sent Events；
- 前端：React + `@xyflow/react` 展示 Run Graph，ECharts 展示预测数据；
- 本地作品存储：SQLite 保存 Run、Event、Checkpoint 和 Evidence；
- 模型接入：Provider Adapter，固定模型版本和参数，不使用“latest”；
- 追踪语义：字段兼容 OpenTelemetry，但首版不强制引入完整平台。

## 4. 核心组件

### 4.1 Task Parser

将自然语言转换为结构化任务：

```json
{
  "intent": "predict_tournament",
  "scope": "full_tournament",
  "snapshot_policy": "refresh_if_stale",
  "explain_level": "evidence",
  "allow_human_review": true
}
```

解析失败时返回明确的 validation error，不将不完整对象交给 Orchestrator。

### 4.2 Orchestrator

职责：

- 基于 `TaskSpec` 创建初始 Run Graph；
- 从可执行节点中选择下一项工具；
- 处理 Observation 与 State Diff；
- 根据 Guard 条件增加节点、重试、降级或结束；
- 不直接计算比分、概率或赛程。

至少支持四类真实条件边：

| 观察 | 条件 | 动作 |
|---|---|---|
| 数据过期 | snapshot_age > 24h | 调用数据刷新 |
| 模型分歧 | disagreement > 0.06 | 插入 Critic |
| 模拟未收敛 | probability_delta > 0.5pp | 追加模拟 |
| 工具失败 | retryable = true | 重试或 checkpoint 恢复 |

### 4.3 Tool Registry

每个工具必须声明：

```json
{
  "name": "simulate_tournament",
  "input_schema": {},
  "output_schema": {},
  "timeout_seconds": 30,
  "retry_policy": {"max_attempts": 3},
  "fallback": "cached_simulation",
  "idempotent": true,
  "side_effect": "none"
}
```

工具调用统一生成 `tool_call_id`，记录参数摘要、耗时、状态、重试次数、输入输出 hash 和错误分类。

### 4.4 Shared Run State

```text
RunState
├── run_id
├── task_spec
├── graph
├── data_snapshot
├── model_snapshot
├── tournament_state
├── tool_results
├── decisions
├── evidence_refs
├── errors
└── checkpoints
```

节点不得任意覆盖整个状态，只提交 schema 校验后的 State Patch。每次 patch 产生可展示的 State Diff。

### 4.5 Checkpoint Manager

在以下时机保存 checkpoint：

- 外部数据快照完成；
- 模型概率缓存完成；
- 每个蒙特卡洛批次完成；
- 进入人工审批前；
- 生成最终 Evidence Bundle 前。

恢复必须保持已完成节点、随机种子和幂等工具结果不变。

### 4.6 Critic

Critic 输出结构化 verdict：

```json
{
  "passed": false,
  "issues": ["simulation_not_converged"],
  "recommended_action": "simulate_more",
  "params": {"additional_runs": 10000}
}
```

检查项：模型分歧、概率和、赛制不变量、模拟收敛、解释数字来源和不确定性披露。

### 4.7 Evidence Store

所有可展示数字和关键结论必须绑定 Evidence ID：

```text
SIM-030        蒙特卡洛批次结果
BT-2022-DC     2022 样本外回测结果
RULE-ANNEX-C   FIFA 第三名组合规则
DATA-20260715  数据快照
```

Explainer 只能消费 Evidence Bundle。数字与原始 evidence 不一致时，拒绝发布并回到 Critic。

## 5. 运行数据流

```text
1. 用户输入自然语言任务
2. Task Parser 生成 TaskSpec
3. Orchestrator 创建初始 Run Graph
4. Router 选择 ready 节点并调用工具
5. 工具返回结构化 Observation
6. Reducer 校验并提交 State Patch
7. Policy / Critic 检查下一条条件边
8. 必要时增加工具、重试、暂停或恢复
9. 收集 Evidence Bundle
10. Explainer 生成带证据引用的结果
11. Publisher 写入最终快照并关闭 Run
```

前端通过 SSE 消费 append-only Event Stream；刷新页面后通过 Run API 获取快照，再从最后一个 event sequence 继续订阅。

## 6. Agent 工作台界面

### 6.1 信息层级

1. 顶部 Run Bar：运行状态、步骤数、工具调用数、重试次数、Replay 和故障注入；
2. 中部 Run Graph：节点状态、条件边和动态插入的节点；
3. 右侧 Step Inspector：Decision、Input/Output、Evidence；
4. 底部 Event Timeline：Plan、Tool、State、Decision、Guardrail 和 Retry。

普通冠军预测页只提供“查看 Agent 如何得出结论”的入口。工作台是求职深度展示页，不挤占普通用户的核心结果页面。

### 6.2 Step Inspector

点击节点展示：

- 节点输入和输出摘要；
- 调用工具及 schema；
- Observation；
- State Diff；
- 条件边判断；
- retry / fallback / checkpoint；
- Evidence ID；
- latency、token 和 cost。

### 6.3 Replay

Replay 按 Event sequence 重放界面状态，不重新调用外部工具。用户可暂停并点击任意节点检查当时的 State Snapshot。

## 7. 四个求职演示场景

### 7.1 正常执行

自然语言任务经 TaskSpec、Run Graph、工具、Critic、Evidence Bundle 到最终结果。证明编排和证据闭环。

### 7.2 动态追加工具

模型分歧超过阈值，Orchestrator 动态插入 Critic；Critic 再建议追加 10,000 次模拟。界面实时增加节点并展示条件边依据。

### 7.3 故障恢复

向 MonteCarloWorker 注入 timeout：RetryPolicy 判断可重试，从最近 checkpoint 恢复，并将大批次拆成小批次。必须证明无重复副作用、无状态丢失。

### 7.4 Human-in-the-loop

当官方快照和缓存冲突时暂停执行，展示来源和影响范围，由用户选择。审批人、时间、理由和选项写入 Run State 后继续。

## 8. 错误处理策略

| 错误 | 分类 | 默认处理 |
|---|---|---|
| 网络超时 | retryable | 指数退避，最多 3 次 |
| LLM 非法 JSON | retryable | schema 错误反馈后重试一次 |
| 工具输入非法 | non-retryable | 节点失败，返回开发可读错误 |
| 数据源冲突 | human-required | 暂停并请求审批 |
| 模拟 Worker 超时 | retryable | checkpoint 恢复并缩小批次 |
| LLM 不可用 | degradable | 使用确定性默认执行图和模板解释 |
| Evidence 缺失 | blocking | 禁止发布，回到 Critic |

错误事件不得只保存字符串，必须包含 `error_type`、`retryable`、`source`、`attempt`、`checkpoint_id` 和安全的错误摘要。

## 9. 可观测性

每次执行记录：

```text
run_id, trace_id, step_id, tool_call_id, parent_step_id,
input_hash, output_hash, state_diff, latency_ms, token_usage,
retry_count, checkpoint_id, evidence_ids, event_sequence
```

Prompt、API key 和敏感输入默认脱敏。Event Stream 为 append-only；Run Snapshot 是对事件的物化视图。

## 10. 测试设计

### 10.1 Tool Contract Test

验证 input/output schema、timeout、idempotency、retry 和 fallback。

### 10.2 Graph Branch Test

覆盖数据过期、模型分歧、模拟不收敛、工具失败和人工审批等关键条件边。

### 10.3 State Replay Test

固定 checkpoint、random seed 和工具结果，确认 Replay 后状态 hash 一致。

### 10.4 Chaos Test

注入 timeout、无效 JSON、网络失败、LLM 不可用和 checkpoint 中断。

### 10.5 Evidence Test

提取最终回答中的数字与 Evidence ID，验证引用存在、值一致、版本匹配。

### 10.6 赛制不变量

- Annex C 组合覆盖 495/495；
- 每次完整赛事共 104 场；
- 冠军概率和接近 1；
- 固定 seed 可复现；
- 比分矩阵与胜平负概率一致。

## 11. 验收标准

- 面试官在 30 秒内能识别任务、当前节点、工具和决策依据；
- 至少四类动态条件边在真实状态上运行，不是前端动画伪造；
- 最终回答中的数值 Evidence coverage 为 100%；
- 工具失败后可从 checkpoint 恢复，已完成状态不丢失；
- 无 LLM 时仍能完成确定性赛事预测；
- Replay 不触发外部工具，重放后的状态 hash 一致；
- 关键 Graph 分支、Tool Contract 和赛制不变量有自动化测试；
- 正常执行、动态追加、故障恢复和人工审批四个场景均可现场演示。

## 12. 六分钟演示脚本

| 时间 | 内容 |
|---|---|
| 0:00 | 冠军结论、概率和项目价值 |
| 0:30 | 输入自然语言任务 |
| 1:00 | 进入 Agent 工作台，检查节点与工具 |
| 2:00 | 模型分歧触发动态追加 Critic |
| 3:00 | 注入 Worker 超时并从 checkpoint 恢复 |
| 4:00 | 打开预测结果、赛事树与 Evidence |
| 5:00 | 展示架构、测试、Trace 和降级路径 |
| 5:40 | 总结：LLM 决策、工具计算、证据约束 |

## 13. 非目标

- 不以多个 LLM 人格群聊作为主界面；
- 不展示原始思考链；
- 不让 LLM 计算比分、概率或排名；
- 不在首版实现通用 Agent 平台；
- 不为了展示而伪造动态节点、失败或 Trace；
- 不将高级模型数量当作 Agent 能力指标。
