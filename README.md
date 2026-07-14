# 2026 FIFA 世界杯冠军预测 Agent

> 天池世界杯 Agent 大赛参赛项目 —— 基于可验证数据 + 概率校准模型 + 正确赛制模拟 + LLM Agent 可追溯解释。

## 📁 项目状态

当前仓库包含**架构设计与实施计划**（`docs/`），代码实现按计划推进中。

```
.
├── docs/
│   ├── EXECUTION_PLAN.md     # 执行计划（约束性极强，coding agent 按此实现）
│   └── TECHNICAL_REPORT.md   # 技术报告（方法论定稿）
└── README.md
```

## 🎯 项目简介

构建一个 LLM Agent（LangGraph + DeepSeek）驱动的 2026 世界杯冠军预测系统：

- **数据采集**：martj42 历史国家队赛果（2010 至今，纯国家队，含世界杯/欧洲杯/美洲杯/世预/友谊）
- **单场预测**：加权 Elo + 进球模型三并行（纯泊松 / 双变量泊松 / Dixon-Coles）+ ML 四模型校正（Logistic/LightGBM/XGBoost/CatBoost）+ 融合校准
- **锦标赛模拟**：蒙特卡洛完整赛制（48 队 / 12 组 / 最佳第三 / Annex C 算法分配 / R32→决赛，104 场）
- **Agent 架构**：五 Agent 全 LLM 驱动（DataCollector/DataAnalyzer/Predictor/TournamentSimulator/Explainer）+ Orchestrator
- **可视化**：React + ECharts（赛程树 / 单场预测卡 / 冠军概率榜 / 球队雷达 / 推理过程面板 / 2022 卡塔尔回测）

## 🔑 核心设计原则

1. **数据优先于模型复杂度** —— 真实国家队赛果 > 主观合成样本
2. **概率优先于命中率** —— 用 RPS / Log Loss / Brier / 校准曲线评估
3. **赛制必须准确** —— 104 场、R32 无轮空、Annex C 同组回避
4. **解释必须可追溯** —— 自然语言只能基于结构化数值证据
5. **预测必须可复现** —— 数据版本 + 模型版本 + 随机种子

## 📖 文档导航

| 文档 | 内容 |
|---|---|
| [`docs/TECHNICAL_REPORT.md`](docs/TECHNICAL_REPORT.md) | 完整技术方案：数据/模型/Agent/赛制/评估 |
| [`docs/EXECUTION_PLAN.md`](docs/EXECUTION_PLAN.md) | 分阶段实施计划，含铁律约束 + 每任务 TDD 步骤 + 完整代码 |

## 🚀 技术栈

| 层 | 技术 |
|---|---|
| 计算引擎 | Python 3.11 / pandas / numpy / scipy |
| 机器学习 | scikit-learn / xgboost / lightgbm / catboost |
| Agent | LangGraph / LangChain-DeepSeek |
| LLM | DeepSeek（决策）+ DeepSeek-R1（推理） |
| 后端 | FastAPI |
| 前端 | React 18 + Vite + ECharts |
| 算力 | Tesla V100 |

## ⚙️ 运行（待代码实现后补全）

```bash
# 后端
cd backend && pip install -r requirements.txt
# 配置 DeepSeek API key 到环境变量 DEEPSEEK_API_KEY

# 前端
cd frontend && npm install && npm run dev
```

## 📝 许可

本项目为比赛参赛作品，默认私有。
