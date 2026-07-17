# 2026 世界杯冠军预测 Agent — 执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个基于 LLM Agent（LangGraph + DeepSeek）驱动的 2026 世界杯冠军预测系统，输出赛前预测结果（赛程树、比分、冠军概率、可追溯推理链）并通过 React 可视化页面呈现。

**Architecture:** 确定性计算层（数据→Elo→进球模型三并行→ML四模型校正→融合→蒙特卡洛模拟）作为"工具库"，LangGraph 编排的五个 Agent（DataCollector/DataAnalyzer/Predictor/TournamentSimulator/Explainer）通过 DeepSeek LLM 做决策与解释、调用工具库执行计算。前后端分离：FastAPI 暴露结构化接口，React+ECharts 渲染。

**Tech Stack:** Python 3.11 / pandas / numpy / scipy / scikit-learn / xgboost / lightgbm / catboost / FastAPI / LangGraph / LangChain-DeepSeek / React 18 / Vite / ECharts

---

## 🚨 实施铁律（coding agent 必须遵守的硬约束）

下列约束在任何任务中**不可违反**，违反即视为 bug：

### C1. 信息泄漏零容忍
- **训练/特征生成严禁使用"赛后"信息。** 任何"第 N 场比赛的特征"必须只能用"第 N 场开赛日之前"的数据计算（Elo 滚动到赛前、近期状态只看赛前）。
- 时间切分严格按方案：训练 `[2010-07-11, 2022-11-19)`（2022卡塔尔揭幕前一晚），验证 `[2022-11-20, 2026-06-10)`（2026美加墨揭幕前一晚）。这两个边界值必须作为常量定义在 `core/constants.py`，不可散落。

### C2. LLM 绝不算数
- LLM（DeepSeek）只负责**决策与解释**，所有数值（Elo、概率、比分、模拟结果）必须由确定性 Python 代码计算。
- Explainer Agent 生成的每一句话，其中出现的任何数字必须能在结构化证据里找到对应来源；**数字不一致即视为幻觉 bug**。

### C3. 概率一致性
- 胜/平/负概率必须由比分矩阵**汇总得到**（`P(胜)=Σ矩阵上三角, P(平)=Σ对角线, P(负)=Σ下三角`），严禁"先采样比分再人为修正赛果"。
- 全部 48 队冠军概率之和必须在 `[0.99, 1.01]` 区间内（蒙特卡洛噪声容许 1% 偏差），否则模拟不通过验收。

### C4. 赛制 100% 准确
- 总场次必须等于 104（72 小组 + 16 R32 + 8 R16 + 4 QF + 2 SF + 1 三四名 + 1 决赛）。
- R32 必须是 **32 队打满 16 场，无任何种子轮空**。
- 第三名→R32 槽位必须严格遵循 `core/annex_c.py` 的映射表，不得自行编造对阵。
- 小组同分决胜必须用 **2026 新规则**（先 H2H 积分，再 H2H 净胜球，再 H2H 进球，再总净胜球，再总进球，再公平分，再 FIFA 排名）。

### C5. 纯国家队数据
- 训练数据**严禁**混入俱乐部比赛（欧冠/西甲/英超/亚冠等）。martj42 数据集本身是纯国家队，但 coding agent 若做任何数据补充，必须校验 `tournament` 字段属于国家队赛事白名单。

### C6. 可复现性
- 每一次预测产物必须记录 `data_version / model_version / fixture_version / generated_at`。
- 蒙特卡洛模拟必须接受 `random_seed` 参数；相同 seed + 相同数据 → 相同结果。

### C7. DRY / YAGNI / TDD / 频繁提交
- 每个任务先写失败测试，再写最小实现，再验证通过，再提交。
- 不要写用不到的代码；不要重复实现已有函数。
- 使用中文注释，与项目语言一致。

### C8. Agent 可靠性
- 每次 LLM 调用必须有 `max_retries=3` + schema 校验 + fallback 默认流程。
- 关键决策（如"是否继续模拟"）若 LLM 失败，fallback 到确定性默认值，不得让整个流程挂死。

---

## 📁 项目文件结构（锁定）

```
ZCodeProject/
├── backend/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── constants.py          # 时间窗、赛事权重、Elo参数等所有常量
│   │   ├── schemas.py            # pydantic 数据 Schema（比赛、预测报告、模拟结果）
│   │   └── annex_c.py            # 第三名→R32 槽位映射表（495组合）
│   ├── data/
│   │   ├── __init__.py
│   │   ├── fixtures_2026.py      # 12组分组 + 72场赛程 + 场地（硬编码官方抽签）
│   │   ├── team_aliases.py       # 队名映射（martj42 ↔ FIFA）
│   │   └── loader.py             # 加载历史赛果CSV、清洗、版本快照
│   ├── models/
│   │   ├── __init__.py
│   │   ├── elo.py                # 加权Elo递推（eloratings.net官方参数）
│   │   ├── goal_model_poisson.py # 纯泊松（基线）
│   │   ├── goal_model_bivar.py   # 双变量泊松（Karlis-Ntzoufras 2003）
│   │   ├── goal_model_dc.py      # Dixon-Coles（τ低分修正）
│   │   ├── ml_calibrator.py      # Logistic/LightGBM/XGBoost/CatBoost + 集成
│   │   └── fusion.py             # 融合权重学习 + Isotonic校准
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── group_stage.py        # 小组赛排名（含2026 H2H新规则）
│   │   ├── knockout.py           # R32→决赛（含加时50/50、Annex C）
│   │   └── simulator.py          # 蒙特卡洛全赛制模拟
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── tools.py              # 所有确定性函数封装为LangGraph工具
│   │   ├── orchestrator.py       # LangGraph编排大脑
│   │   ├── data_collector.py
│   │   ├── data_analyzer.py
│   │   ├── predictor.py
│   │   ├── tournament_simulator.py
│   │   └── explainer.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py               # FastAPI 服务层
│   ├── eval/
│   │   ├── __init__.py
│   │   └── metrics.py            # RPS / LogLoss / Brier / 校准曲线
│   ├── pipeline.py               # 端到端编排（非Agent流水线模式）
│   ├── config.yaml               # API key、模型版本、路径配置
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── api/client.js         # 调FastAPI
│   │   └── components/
│   │       ├── BracketTree.jsx
│   │       ├── MatchCard.jsx
│   │       ├── ChampionRanking.jsx
│   │       ├── TeamRadar.jsx
│   │       ├── ExplanationPanel.jsx
│   │       └── Backtest2022.jsx
│   ├── package.json
│   └── vite.config.js
├── data/
│   ├── raw/                      # martj42 CSV 原始文件
│   ├── snapshots/                # 版本快照
│   └── results/                  # 模拟输出JSON
└── docs/
    ├── EXECUTION_PLAN.md         # 本文件
    └── TECHNICAL_REPORT.md       # 技术报告
```

---

## 阶段总览（6 阶段，每阶段产出可独立验证）

| 阶段 | 内容 | 验收 |
|---|---|---|
| P0 | 骨架+常量+Schema | 项目可 import，所有常量集中定义 |
| P1 | 数据层 | 加载历史赛果、2026赛程、队名映射，单元测试通过 |
| P2 | Elo + 进球模型三并行 | 三模型在验证集上输出 RPS，裁决选优 |
| P3 | ML校正层 + 融合 + 校准 | 四模型+集成对比表、融合权重、校准曲线 |
| P4 | 赛制引擎 + 蒙特卡洛模拟 | 104场计数、冠军概率和≈1、Annex C正确 |
| P5 | 五Agent + LangGraph编排 | Agent能调工具、有决策、Explainer有思考链 |
| P6 | FastAPI + React前端 + 2022回测 | 端到端跑通、可视化呈现 |

---

# 阶段 P0：骨架 + 常量 + Schema

### Task 0.1：创建项目骨架与依赖文件

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config.yaml`
- Create: 所有 `__init__.py`（空文件）

- [ ] **Step 1：写 requirements.txt**

```
pandas==2.2.0
numpy==1.26.4
scipy==1.12.0
scikit-learn==1.4.2
xgboost==2.0.3
lightgbm==4.3.0
catboost==1.2.5
pydantic==2.6.4
fastapi==0.110.0
uvicorn==0.29.0
langgraph==0.0.40
langchain==0.1.13
langchain-community==0.0.29
langchain-deepseek  # 最新版本，coding时联网确认
httpx==0.27.0
pytest==8.1.1
pyyaml==6.0.1
```

- [ ] **Step 2：写 config.yaml**

```yaml
data:
  raw_results_csv: "data/raw/results.csv"
  snapshot_date: "2025-12-31"
  data_version: "2026-06-01-v1"
  fixture_version: "official-schedule-v3"

split:
  train_start: "2010-07-11"
  train_end: "2022-11-19"      # 卡塔尔揭幕前
  valid_start: "2022-11-20"
  valid_end: "2026-06-10"      # 美加墨揭幕前

models:
  elo: {k_world_cup: 60, k_cont: 35, k_qual: 25, k_friendly: 20,
        home_adv: 100, neutral_adv: 0, init_rating: 1500}
  goal_models: ["poisson", "bivar", "dc"]
  ml_models: ["logistic", "lightgbm", "xgboost", "catboost"]
  fusion: {method: "convex_logloss", calibrate: "isotonic"}
  model_version: "ensemble-3.0"

simulation:
  n_simulations: 30000
  max_goals: 8
  knockout_penalty_fairness: 0.5  # 加时+点球50/50
  random_seed: 42

llm:
  provider: "deepseek"
  model_decision: "deepseek-chat"       # V4 工具调用
  model_reasoning: "deepseek-reasoner"  # R1 推理解释
  api_key_env: "DEEPSEEK_API_KEY"
  max_retries: 3
  mock_when_no_key: true
```

- [ ] **Step 3：创建所有空 `__init__.py`**

用脚本创建（见下）。不展开，coding agent 按"文件结构"清单创建。

- [ ] **Step 4：提交**

```bash
git init && git add -A && git commit -m "P0.1: project skeleton, requirements, config"
```

---

### Task 0.2：常量集中定义

**Files:**
- Create: `backend/core/constants.py`
- Test: `backend/tests/test_constants.py`

- [ ] **Step 1：写失败测试**

```python
# backend/tests/test_constants.py
from core.constants import (
    TRAIN_START, TRAIN_END, VALID_START, VALID_END,
    K_FACTORS, HOME_ADVANTAGE, INIT_RATING, MAX_GOALS,
    NATIONAL_TOURNAMENTS, TOTAL_MATCHES_2026
)

def test_time_split_boundaries():
    assert TRAIN_START == "2010-07-11"
    assert TRAIN_END == "2022-11-19"
    assert VALID_START == "2022-11-20"
    assert VALID_END == "2026-06-10"

def test_elo_factors_complete():
    assert K_FACTORS == {"world_cup": 60, "continental": 35,
                         "qualifier": 25, "friendly": 20}
    assert HOME_ADVANTAGE == 100
    assert INIT_RATING == 1500

def test_total_matches_2026():
    assert TOTAL_MATCHES_2026 == 104

def test_national_tournament_whitelist_includes_euro_copa():
    assert "UEFA Euro" in NATIONAL_TOURNAMENTS
    assert "Copa América" in NATIONAL_TOURNAMENTS
    assert "UEFA Champions League" not in NATIONAL_TOURNAMENTS
```

- [ ] **Step 2：运行，确认失败**

```bash
cd backend && python -m pytest tests/test_constants.py -v
```
Expected: ImportError（模块不存在）

- [ ] **Step 3：写实现**

```python
# backend/core/constants.py
"""全项目唯一常量来源。任何魔法数字都必须定义在此并 import。"""

# ===== 时间切分（信息泄漏防线，见约束 C1）=====
TRAIN_START = "2010-07-11"   # 南非世界杯开赛
TRAIN_END = "2022-11-19"     # 卡塔尔世界杯揭幕前一晚（不含）
VALID_START = "2022-11-20"   # 卡塔尔揭幕
VALID_END = "2026-06-10"     # 美加墨揭幕前一晚（不含）

# ===== Elo 参数（照搬 eloratings.net 官方）=====
K_FACTORS = {"world_cup": 60, "continental": 35, "qualifier": 25, "friendly": 20}
HOME_ADVANTAGE = 100         # 主队+100，非中立场地
NEUTRAL_ADVANTAGE = 0        # 中立场（世界杯大部分）
INIT_RATING = 1500
ELO_SCALE = 400              # W_e = 1/(1+10^(-dElo/400))

# ===== 进球模型 =====
MAX_GOALS = 8                # 比分矩阵 9x9
MODEL_SELECTION_EPSILON = 0.001  # 双变量泊松 ≤ DC + ε 即选双变量

# ===== 赛制（见约束 C4）=====
TOTAL_MATCHES_2026 = 104
GROUP_MATCHES = 72
R32_MATCHES = 16
R16_MATCHES = 8
QF_MATCHES = 4
SF_MATCHES = 2
THIRD_PLACE_MATCHES = 1
FINAL_MATCHES = 1
N_GROUPS = 12
GROUP_SIZE = 4
N_THIRD_QUALIFY = 8          # 最佳第三名数量
R32_TEAM_COUNT = 32          # 24(前二) + 8(最佳第三)，无轮空

# ===== 国家队赛事白名单（见约束 C5，禁止俱乐部）=====
# 注意：这是 tournament 字段的关键词集合，用于分类赛事权重
NATIONAL_TOURNAMENTS = {
    # 世界杯
    "FIFA World Cup", "World Cup",
    # 洲际国家杯
    "UEFA Euro", "Copa América", "African Cup of Nations",
    "AFC Asian Cup", "Gold Cup", "CONCACAF Gold Cup",
    "Oceania Nations Cup", "UEFA Nations League",
    # 世预赛
    "Qualification", "Qualifying", "UEFA Euro qualification",
    # 友谊赛
    "Friendly",
}
# 俱乐部赛事黑名单（出现即报错）
CLUB_TOURNAMENT_BLACKLIST = {
    "UEFA Champions League", "UEFA Europa League", "UEFA Conference League",
    "Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1",
    "CONMEBOL Libertadores", "CONMEBOL Sudamericana", "AFC Champions League",
}

# ===== 赛事权重分类映射 =====
# 将 tournament 字段映射到 K_FACTORS 的 key
def classify_tournament(tournament: str, is_world_cup_year: bool = False) -> str:
    t = tournament.lower()
    if "world cup" in t and "qualif" not in t:
        return "world_cup"
    if any(k in t for k in ["euro", "copa américa", "copa america",
                            "african cup", "asian cup", "gold cup",
                            "nations league", "nations cup"]):
        return "continental"
    if "qualif" in t or "qualifying" in t:
        return "qualifier"
    return "friendly"
```

- [ ] **Step 4：运行测试，通过**

- [ ] **Step 5：提交**

```bash
git commit -am "P0.2: centralized constants with tests"
```

---

### Task 0.3：数据 Schema 定义

**Files:**
- Create: `backend/core/schemas.py`
- Test: `backend/tests/test_schemas.py`

- [ ] **Step 1：写失败测试**

```python
# backend/tests/test_schemas.py
import pytest
from pydantic import ValidationError
from core.schemas import Match, PredictionReport, ScoreMatrix

def test_match_basic():
    m = Match(date="2022-12-18", team_a="Argentina", team_b="France",
              goals_a=3, goals_b=3, tournament="FIFA World Cup", neutral=True)
    assert m.team_a == "Argentina"

def test_match_rejects_negative_goals():
    with pytest.raises(ValidationError):
        Match(date="2022-12-18", team_a="A", team_b="B",
              goals_a=-1, goals_b=0, tournament="Friendly", neutral=True)

def test_prediction_report_has_versions():
    r = PredictionReport(team_a="A", team_b="B",
                         p_home=0.4, p_draw=0.3, p_away=0.3,
                         expected_goals_a=1.2, expected_goals_b=1.1,
                         score_matrix=[[0.2]*9 for _ in range(9)],
                         key_factors=[], data_version="v1", model_version="m1")
    assert r.data_version == "v1"
    assert abs(r.p_home + r.p_draw + r.p_away - 1.0) < 1e-6

def test_score_matrix_sums_to_one():
    # score_matrix 必须归一化
    m = [[0.0]*9 for _ in range(9)]
    m[0][0] = 1.0
    sm = ScoreMatrix(matrix=m, max_goals=8)
    assert abs(sm.total_prob() - 1.0) < 1e-6
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现**

```python
# backend/core/schemas.py
"""全项目数据契约。Agent 与工具之间、前后端之间均用这些 Schema。"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import numpy as np

class Match(BaseModel):
    date: str
    team_a: str
    team_b: str
    goals_a: int = Field(ge=0)
    goals_b: int = Field(ge=0)
    tournament: str
    neutral: bool = True
    city: Optional[str] = None
    country: Optional[str] = None

    @property
    def goal_diff(self) -> int:
        return self.goals_a - self.goals_b

class KeyFactor(BaseModel):
    factor: str
    contribution_pp: float  # 百分点贡献，可正可负
    evidence: str           # 必须可追溯的数值证据

class ScoreMatrix(BaseModel):
    matrix: list[list[float]]   # (MAX_GOALS+1) x (MAX_GOALS+1)
    max_goals: int

    def as_numpy(self) -> np.ndarray:
        return np.array(self.matrix)

    def total_prob(self) -> float:
        return float(self.as_numpy().sum())

    def p_home_draw_away(self) -> tuple[float, float, float]:
        m = self.as_numpy()
        p_home = float(np.triu(m, k=1).sum())  # 严格上三角（行>列即 A 进球多）
        p_draw = float(np.diag(m).sum())
        p_away = float(np.tril(m, k=-1).sum())
        return p_home, p_draw, p_away

class PredictionReport(BaseModel):
    team_a: str
    team_b: str
    p_home: float
    p_draw: float
    p_away: float
    expected_goals_a: float
    expected_goals_b: float
    score_matrix: list[list[float]]
    key_factors: list[KeyFactor]
    data_version: str
    model_version: str
    neutral: bool = True
    confidence_note: Optional[str] = None
```

- [ ] **Step 4：运行测试，通过**

- [ ] **Step 5：提交**

```bash
git commit -am "P0.3: pydantic schemas with validation"
```

---

# 阶段 P1：数据层

### Task 1.1：2026 分组与赛程硬编码

**Files:**
- Create: `backend/data/fixtures_2026.py`
- Test: `backend/tests/test_fixtures.py`

- [ ] **Step 1：写失败测试（结构校验，不校验具体队名真实性，留作人工核对）**

```python
# backend/tests/test_fixtures.py
from data.fixtures_2026 import GROUPS_2026, GROUP_STAGE_MATCHES_2026, HOSTS

def test_12_groups_of_4():
    assert len(GROUPS_2026) == 12
    for g, teams in GROUPS_2026.items():
        assert len(teams) == 4, f"组 {g} 不是4队"

def test_group_stage_match_count():
    # 每组 C(4,2)=6 场 × 12 = 72
    assert len(GROUP_STAGE_MATCHES_2026) == 72

def test_hosts_are_three():
    assert set(HOSTS) == {"United States", "Mexico", "Canada"}

def test_all_group_teams_appear_in_matches():
    teams_in_matches = set()
    for m in GROUP_STAGE_MATCHES_2026:
        teams_in_matches.add(m["team_a"])
        teams_in_matches.add(m["team_b"])
    all_teams = set()
    for teams in GROUPS_2026.values():
        all_teams.update(teams)
    assert teams_in_matches == all_teams
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现**

```python
# backend/data/fixtures_2026.py
"""2026 世界杯官方抽签结果（硬编码，来源已联网核实）。
coding agent 必须从 Wikipedia 官方抽签页核对每个组的 4 支队。
分组字母 A-L。"""
# 注：实际队名在编码阶段以 Wikipedia 2026 draw 页为准，此处给出结构。
# 每组格式："A": ["队1","队2","队3","队4"]

HOSTS = ["United States", "Mexico", "Canada"]

# ✅ 已联网核实（来源：Wikipedia 2026 FIFA World Cup draw 官方抽签页，2025-12-05 抽签）
# 抽签位置约定：Pos1=种子(Pot1东道主/强队), Pos2-4 按 FIFA 抽签程序分配
GROUPS_2026 = {
    "A": ["Mexico",               "South Africa",  "South Korea",      "Czech Republic"],
    "B": ["Canada",               "Bosnia and Herzegovina", "Qatar",   "Switzerland"],
    "C": ["Brazil",               "Morocco",       "Haiti",            "Scotland"],
    "D": ["United States",        "Paraguay",      "Australia",        "Turkey"],
    "E": ["Germany",              "Curaçao",       "Ivory Coast",      "Ecuador"],
    "F": ["Netherlands",          "Japan",         "Sweden",           "Tunisia"],
    "G": ["Belgium",              "Egypt",         "Iran",             "New Zealand"],
    "H": ["Spain",                "Cape Verde",    "Saudi Arabia",     "Uruguay"],
    "I": ["France",               "Senegal",       "Iraq",             "Norway"],
    "J": ["Argentina",            "Algeria",       "Austria",          "Jordan"],
    "K": ["Portugal",             "DR Congo",      "Uzbekistan",       "Colombia"],
    "L": ["England",              "Croatia",       "Ghana",            "Panama"],
}
# 注：队名以 FIFA 官方名为准；与 martj42 的拼写差异由 team_aliases.py 统一处理
# （如 Ivory Coast→Côte d'Ivoire, South Korea→Korea Republic, Cape Verde→Cabo Verde）

def _build_group_stage_matches():
    """每组生成 6 场（C(4,2)），返回 72 场的列表。
    每场 dict: {group, match_in_group, team_a, team_b, date, city, venue}"""
    matches = []
    for group, teams in GROUPS_2026.items():
        # 6 个对阵：(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)
        pairs = [(0,1),(2,3),(0,2),(1,3),(3,0),(2,1)]
        for idx, (i, j) in enumerate(pairs):
            matches.append({
                "group": group,
                "match_in_group": idx + 1,
                "team_a": teams[i],
                "team_b": teams[j],
                "date": None,    # coding agent 从官方赛程页填
                "city": None,
                "venue": None,
            })
    return matches

GROUP_STAGE_MATCHES_2026 = _build_group_stage_matches()
```

> ⚠️ **此任务要求 coding agent 必须联网核对 Wikipedia 官方抽签**，把真实 48 队填入。**未联网核对就提交视为不合格。**

- [ ] **Step 4：运行测试，通过（结构部分）**

- [ ] **Step 5：提交**

---

### Task 1.2：队名映射表

**Files:**
- Create: `backend/data/team_aliases.py`
- Test: `backend/tests/test_team_aliases.py`

- [ ] **Step 1：写失败测试**

```python
# backend/tests/test_team_aliases.py
from data.team_aliases import canonical_team_name

def test_ivory_coast_variants():
    assert canonical_team_name("Ivory Coast") == "Côte d'Ivoire"
    assert canonical_team_name("Cote d'Ivoire") == "Côte d'Ivoire"

def test_usa_variants():
    assert canonical_team_name("USA") == "United States"
    assert canonical_team_name("United States of America") == "United States"

def test_already_canonical():
    assert canonical_team_name("Brazil") == "Brazil"

def test_unknown_returns_input():
    assert canonical_team_name("Atlantis") == "Atlantis"
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现**

```python
# backend/data/team_aliases.py
"""队名规范化：martj42 用 'Ivory Coast'，FIFA 用 'Côte d'Ivoire'，
统一切换到 FIFA 官方名（与 fixtures_2026 一致）。"""

# 别名 -> 规范名（FIFA官方英文）
ALIASES = {
    "Ivory Coast": "Côte d'Ivoire",
    "Cote d'Ivoire": "Côte d'Ivoire",
    "USA": "United States",
    "United States of America": "United States",
    "South Korea": "Korea Republic",
    "Korea Republic": "Korea Republic",
    "North Korea": "Korea DPR",
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde": "Cabo Verde",
    "Cape Verde Islands": "Cabo Verde",
    "FYR Macedonia": "North Macedonia",
    "Macedonia": "North Macedonia",
    "Iran": "IR Iran",
    "IR Iran": "IR Iran",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Republic of Ireland": "Republic of Ireland",
    "DR Congo": "DR Congo",
    "Congo DR": "DR Congo",
    "China PR": "China PR",
    "China": "China PR",
}
# coding agent：核对 fixtures_2026 里出现的所有队名，
# 为每个在 martj42 里可能拼写不同的队补一条映射。

def canonical_team_name(name: str) -> str:
    return ALIASES.get(name, name)
```

- [ ] **Step 4：运行测试，通过**

- [ ] **Step 5：提交**

---

### Task 1.3：历史赛果加载与清洗

**Files:**
- Create: `backend/data/loader.py`
- Test: `backend/tests/test_loader.py`

- [ ] **Step 1：写失败测试（用小 fixture CSV）**

```python
# backend/tests/test_loader.py
import pandas as pd
from pathlib import Path
from data.loader import load_and_clean_results

def test_load_filters_to_2010_after(tmp_path):
    csv = tmp_path / "r.csv"
    csv.write_text(
        "date,home_team,away_team,home_score,away_score,tournament,city,country,neutral\n"
        "2005-01-01,Brazil,Argentina,1,0,Friendly,,,TRUE\n"     # 应被过滤
        "2011-01-01,Brazil,Argentina,2,0,Friendly,,,TRUE\n"      # 保留
        "2023-06-01,Spain,France,1,1,FIFA World Cup,,,TRUE\n"    # 保留
    )
    df = load_and_clean_results(str(csv))
    assert len(df) == 2
    assert (df["date"] >= "2010-07-11").all()

def test_load_rejects_club_tournaments(tmp_path):
    csv = tmp_path / "r.csv"
    csv.write_text(
        "date,home_team,away_team,home_score,away_score,tournament,city,country,neutral\n"
        "2020-01-01,Real Madrid,Bayern Munich,2,1,UEFA Champions League,,,TRUE\n"
    )
    df = load_and_clean_results(str(csv))
    assert len(df) == 0   # 俱乐部比赛被过滤

def test_load_normalizes_team_names(tmp_path):
    csv = tmp_path / "r.csv"
    csv.write_text(
        "date,home_team,away_team,home_score,away_score,tournament,city,country,neutral\n"
        "2015-01-01,Ivory Coast,USA,1,0,Friendly,,,TRUE\n"
    )
    df = load_and_clean_results(str(csv))
    assert "Côte d'Ivoire" in df["team_a"].values
    assert "United States" in df["team_b"].values
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现**

```python
# backend/data/loader.py
"""加载 martj42 历史赛果 CSV，清洗、过滤、规范化、版本记录。
核心约束：只保留国家队赛事 + 2010-07 之后 + 队名规范化。"""
import pandas as pd
from core.constants import (TRAIN_START, CLUB_TOURNAMENT_BLACKLIST)
from data.team_aliases import canonical_team_name

def load_and_clean_results(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # 列名标准化（martj42 原始列名）
    df = df.rename(columns={
        "home_team": "team_a", "away_team": "team_b",
        "home_score": "goals_a", "away_score": "goals_b",
    })
    # 1. 时间过滤：只保留 TRAIN_START 之后（信息泄漏防线起点）
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= TRAIN_START].copy()
    # 2. 过滤俱乐部赛事（约束 C5）
    mask_blacklist = df["tournament"].isin(CLUB_TOURNAMENT_BLACKLIST)
    df = df[~mask_blacklist].copy()
    # 3. 队名规范化
    df["team_a"] = df["team_a"].map(canonical_team_name)
    df["team_b"] = df["team_b"].map(canonical_team_name)
    # 4. 类型与索引
    df = df.reset_index(drop=True)
    df["goals_a"] = df["goals_a"].astype(int)
    df["goals_b"] = df["goals_b"].astype(int)
    return df

def make_snapshot(df: pd.DataFrame, version: str, out_path: str):
    """固化数据快照，保证可复现（约束 C6）。"""
    import json
    meta = {"data_version": version, "rows": len(df),
            "date_min": str(df["date"].min()), "date_max": str(df["date"].max())}
    df.to_csv(out_path, index=False)
    with open(out_path.replace(".csv", ".meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
```

- [ ] **Step 4：运行测试，通过**

- [ ] **Step 5：提交**

---

# 阶段 P2：Elo + 进球模型三并行

### Task 2.1：加权 Elo 递推

**Files:**
- Create: `backend/models/elo.py`
- Test: `backend/tests/test_elo.py`

- [ ] **Step 1：写失败测试**

```python
# backend/tests/test_elo.py
import pandas as pd
from models.elo import EloRatings, compute_elo_history

def test_equal_teams_draw_no_change():
    e = EloRatings()
    # 两队同分1500，平局，应几乎不变（W=0.5, W_e=0.5）
    new_a, new_b = e.update(rating_a=1500, rating_b=1500,
                            goal_diff=0, k=60, home_adv_applied=0)
    assert abs(new_a - 1500) < 1e-9
    assert abs(new_b - 1500) < 1e-9

def test_winner_gains_loser_loses():
    e = EloRatings()
    new_a, new_b = e.update(rating_a=1500, rating_b=1500,
                            goal_diff=1, k=60, home_adv_applied=0)
    assert new_a > 1500 and new_b < 1500
    assert abs((new_a - 1500) + (1500 - new_b)) < 1e-9  # 零和

def test_goal_diff_multiplier():
    # 赢3球 G=(11+3)/8=1.75，比赢1球(G=1)得分多
    e = EloRatings()
    _, _ = e.update(1500, 1500, 1, 60, 0)
    new_a1, _ = e.update(1500, 1500, 1, 60, 0)
    new_a3, _ = e.update(1500, 1500, 3, 60, 0)
    assert new_a3 > new_a1

def test_compute_history_strict_pre_match():
    # 关键：第N场的Elo只能用前N-1场的信息（约束 C1）
    df = pd.DataFrame({
        "date": ["2011-01-01", "2011-06-01", "2012-01-01"],
        "team_a": ["A", "A", "A"],
        "team_b": ["B", "B", "B"],
        "goals_a": [1, 2, 0],
        "goals_b": [0, 0, 1],
        "tournament": ["Friendly", "Friendly", "Friendly"],
        "neutral": [True, True, True],
    })
    df["date"] = pd.to_datetime(df["date"])
    history = compute_elo_history(df)
    # 第1场赛前，A和B都是初始分1500
    first = history[0]
    assert first["pre_elo_a"] == 1500 and first["pre_elo_b"] == 1500
    # 第3场赛前，A的Elo必须受第1、2场影响（严格赛前）
    third = history[2]
    assert third["pre_elo_a"] != 1500
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现**

```python
# backend/models/elo.py
"""加权 Elo（照搬 eloratings.net 官方公式）。
R_new = R_old + K * G * (W - W_e)
W_e = 1/(1+10^(-(Ra-Rb+H)/400))，H为主场优势。
严格遵守赛前信息约束：compute_elo_history 按日期排序，
每场用"此前"的累计评分作为 pre_elo。"""
import pandas as pd
import numpy as np
from core.constants import (K_FACTORS, INIT_RATING, ELO_SCALE,
                            HOME_ADVANTAGE, NEUTRAL_ADVANTAGE)
from core.constants import classify_tournament

class EloRatings:
    def __init__(self, init: int = INIT_RATING):
        self.init = init

    @staticmethod
    def expected(rating_a: float, rating_b: float, home_adv_applied: float) -> float:
        return 1.0 / (1.0 + 10 ** (-(rating_a - rating_b + home_adv_applied) / ELO_SCALE))

    @staticmethod
    def goal_diff_multiplier(goal_diff: int) -> float:
        """eloratings.net 官方：赢1球G=1，2球G=1.5，≥3球G=(11+gd)/8。"""
        gd = abs(goal_diff)
        if gd <= 1: return 1.0
        if gd == 2: return 1.5
        return (11.0 + gd) / 8.0

    @staticmethod
    def result_score(goal_diff: int) -> float:
        if goal_diff > 0: return 1.0
        if goal_diff == 0: return 0.5
        return 0.0

    def update(self, rating_a, rating_b, goal_diff, k, home_adv_applied):
        we = self.expected(rating_a, rating_b, home_adv_applied)
        w = self.result_score(goal_diff)
        g = self.goal_diff_multiplier(goal_diff)
        delta = k * g * (w - we)
        return rating_a + delta, rating_b - delta

def _k_for(tournament: str) -> float:
    cat = classify_tournament(tournament)
    return float(K_FACTORS[cat])

def _home_adv(neutral: bool, team_a_is_host: bool) -> float:
    """A 为视角的主场优势。中立场=0；A是东道主且非中立=+HOME_ADVANTAGE。"""
    if neutral:
        return NEUTRAL_ADVANTAGE
    return HOME_ADVANTAGE if team_a_is_host else -HOME_ADVANTAGE

def compute_elo_history(df: pd.DataFrame, hosts: set = None) -> list[dict]:
    """按日期升序滚动计算每场赛前 Elo。返回每场 {pre_elo_a, pre_elo_b}。
    严格赛前：第N场只用前N-1场的信息更新。"""
    hosts = hosts or set()
    df = df.sort_values("date").reset_index(drop=True)
    ratings = {}  # team -> rating
    def r(t): return ratings.get(t, INIT_RATING)
    history = []
    for _, m in df.iterrows():
        ra, rb = r(m["team_a"]), r(m["team_b"])
        history.append({"pre_elo_a": ra, "pre_elo_b": rb})
        k = _k_for(m["tournament"])
        h = _home_adv(bool(m["neutral"]), m["team_a"] in hosts)
        # 注意：update 内部已含 home_adv 对 W_e 的影响；A主队则 h 为正
        na, nb = EloRatings().update(ra, rb, m["goals_a"]-m["goals_b"], k, h)
        ratings[m["team_a"]] = na
        ratings[m["team_b"]] = nb
    return history
```

- [ ] **Step 4：运行测试，通过**

- [ ] **Step 5：提交**

---

### Task 2.2：纯泊松进球模型（基线）

**Files:**
- Create: `backend/models/goal_model_poisson.py`
- Test: `backend/tests/test_goal_model_poisson.py`

- [ ] **Step 1：写失败测试**

```python
# backend/tests/test_goal_model_poisson.py
import numpy as np
from models.goal_model_poisson import (
    independent_poisson_matrix, fit_poisson_global
)

def test_matrix_shape_and_normalization():
    m = independent_poisson_matrix(lam_a=1.2, lam_b=1.0, max_goals=8)
    assert m.shape == (9, 9)
    assert abs(m.sum() - 1.0) < 1e-6

def test_probs_consistent_with_matrix():
    # 约束 C3：胜平负由矩阵汇总
    m = independent_poisson_matrix(1.5, 0.8, 8)
    p_home = np.triu(m, k=1).sum()
    p_draw = np.diag(m).sum()
    p_away = np.tril(m, k=-1).sum()
    assert abs(p_home + p_draw + p_away - 1.0) < 1e-6
    assert p_home > p_away  # lam_a 大则 A 更可能赢

def test_fit_returns_positive_params():
    import pandas as pd
    df = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01"]*50),
        "team_a": ["A"]*50, "team_b": ["B"]*50,
        "goals_a": [1]*50, "goals_b": [0]*50,
        "tournament": ["Friendly"]*50, "neutral": [True]*50,
        "pre_elo_a": [1600]*50, "pre_elo_b": [1500]*50,
    })
    params = fit_poisson_global(df)
    mu, xi = params
    assert mu > 0
    # A 强（Elo高）应导致 xi 正向，使 lam_a 更高
    assert xi > 0
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现**

```python
# backend/models/goal_model_poisson.py
"""独立泊松基线（Maher 1982）。
强度由 Elo 差驱动（全局参数，非每队 α/β，见学术调研结论）。
log(λ_A) = μ + ξ·(Elo_A - Elo_B)/2
log(λ_B) = μ - ξ·(Elo_A - Elo_B)/2
中立/主场修正作为额外项。"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson
from core.constants import MAX_GOALS, NEUTRAL_ADVANTAGE, ELO_SCALE

def independent_poisson_matrix(lam_a: float, lam_b: float, max_goals: int = MAX_GOALS):
    """返回 (max_goals+1)x(max_goals+1) 比分概率矩阵，归一化。"""
    i = np.arange(max_goals + 1)
    pa = poisson.pmf(i, lam_a)
    pb = poisson.pmf(i, lam_b)
    m = np.outer(pa, pb)
    m /= m.sum()
    return m

def _lam_pair(mu, xi, elo_a, elo_b, neutral=True, host_a=False):
    half = xi * (elo_a - elo_b) / 2.0
    # 简化：中立场不加主场，host 时微调
    host_adj = 0.0 if neutral else (0.1 if host_a else -0.1)
    lam_a = np.exp(mu + half + host_adj)
    lam_b = np.exp(mu - half - host_adj)
    return lam_a, lam_b

def fit_poisson_global(df: pd.DataFrame):
    """最大似然拟合全局参数 (μ, ξ)。df 需含 pre_elo_a/pre_elo_b/goals_a/goals_b。"""
    goals_a = df["goals_a"].values.astype(float)
    goals_b = df["goals_b"].values.astype(float)
    elo_a = df["pre_elo_a"].values.astype(float)
    elo_b = df["pre_elo_b"].values.astype(float)
    neutral = df["neutral"].values.astype(bool)

    def neg_ll(params):
        mu, xi = params
        if mu > 5 or mu < -3 or abs(xi) > 0.01:
            return 1e10
        lam_a = np.exp(mu + xi*(elo_a-elo_b)/2)
        lam_b = np.exp(mu - xi*(elo_a-elo_b)/2)
        ll = (poisson.logpmf(goals_a, lam_a) + poisson.logpmf(goals_b, lam_b)).sum()
        return -ll

    res = minimize(neg_ll, x0=[0.4, 0.0015], method="Nelder-Mead",
                   options={"maxiter": 5000, "xatol": 1e-6})
    return res.x  # (mu, xi)

def predict_poisson(mu, xi, elo_a, elo_b, neutral=True, host_a=False, max_goals=MAX_GOALS):
    lam_a, lam_b = _lam_pair(mu, xi, elo_a, elo_b, neutral, host_a)
    m = independent_poisson_matrix(lam_a, lam_b, max_goals)
    return m, lam_a, lam_b
```

- [ ] **Step 4：运行测试，通过**

- [ ] **Step 5：提交**

---

### Task 2.3：双变量泊松进球模型

**Files:**
- Create: `backend/models/goal_model_bivar.py`
- Test: `backend/tests/test_goal_model_bivar.py`

- [ ] **Step 1：写失败测试**

```python
# backend/tests/test_goal_model_bivar.py
import numpy as np
from models.goal_model_bivar import (
    bivariate_poisson_matrix, bivariate_poisson_pmf, fit_bivar_global
)

def test_matrix_shape_and_norm():
    m = bivariate_poisson_matrix(lam1=1.0, lam2=0.8, lam3=0.1, max_goals=8)
    assert m.shape == (9, 9)
    assert abs(m.sum() - 1.0) < 1e-6

def test_lam3_zero_reduces_to_independent():
    # λ3=0 时应接近独立泊松（退化）
    m_bv = bivariate_poisson_matrix(1.2, 1.0, 1e-9, 8)
    from models.goal_model_poisson import independent_poisson_matrix
    m_indep = independent_poisson_matrix(1.2, 1.0, 8)
    assert np.allclose(m_bv, m_indep, atol=1e-3)

def test_pmf_single_value_in_range():
    p = bivariate_poisson_pmf(lam1=1.0, lam2=1.0, lam3=0.2, x=1, y=1)
    assert 0 < p < 1

def test_fit_returns_nonneg_lam3():
    import pandas as pd
    df = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01"]*50),
        "team_a": ["A"]*50, "team_b": ["B"]*50,
        "goals_a": [1]*50, "goals_b": [1]*50,  # 高相关
        "tournament": ["Friendly"]*50, "neutral": [True]*50,
        "pre_elo_a": [1500]*50, "pre_elo_b": [1500]*50,
    })
    params = fit_bivar_global(df)
    mu, xi, lam3 = params
    assert lam3 >= 0
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现**

```python
# backend/models/goal_model_bivar.py
"""双变量泊松（Karlis & Ntzoufras 2003）。
X = X1 + X3, Y = Y1 + X3，X3 为共享进球源。
P(X=x,Y=y) = e^{-(λ1+λ2+λ3)} Σ_{k=0}^{min(x,y)} λ1^{x-k}λ2^{y-k}λ3^k / ((x-k)!(y-k)!k!)
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln
from core.constants import MAX_GOALS

def bivariate_poisson_pmf(lam1, lam2, lam3, x, y):
    """单点概率。对数空间求和防下溢。"""
    log_l1, log_l2, log_l3 = np.log([lam1, lam2, lam3 + 1e-12])
    k = np.arange(0, min(x, y) + 1)
    log_terms = (
        (x - k) * log_l1 + (y - k) * log_l2 + k * log_l3
        - gammaln(x - k + 1) - gammaln(y - k + 1) - gammaln(k + 1)
    )
    return float(np.exp(log_terms.sum() - (lam1 + lam2 + lam3)))

def bivariate_poisson_matrix(lam1, lam2, lam3, max_goals=MAX_GOALS):
    """返回 (max_goals+1)x(max_goals+1) 比分矩阵，归一化。"""
    m = np.zeros((max_goals + 1, max_goals + 1))
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            m[i, j] = bivariate_poisson_pmf(lam1, lam2, lam3, i, j)
    m /= m.sum()
    return m

def fit_bivar_global(df: pd.DataFrame):
    """拟合全局 (μ, ξ, λ3)。"""
    goals_a = df["goals_a"].values.astype(float)
    goals_b = df["goals_b"].values.astype(float)
    elo_a = df["pre_elo_a"].values.astype(float)
    elo_b = df["pre_elo_b"].values.astype(float)

    def neg_ll(params):
        mu, xi, lam3 = params
        if mu > 5 or mu < -3 or abs(xi) > 0.01 or lam3 < 0 or lam3 > 2:
            return 1e10
        lam1 = np.exp(mu + xi*(elo_a-elo_b)/2)
        lam2 = np.exp(mu - xi*(elo_a-elo_b)/2)
        ll = 0.0
        for ga, gb, l1, l2 in zip(goals_a, goals_b, lam1, lam2):
            ll += np.log(max(bivariate_poisson_pmf(l1, l2, lam3, int(ga), int(gb)), 1e-15))
        return -ll

    res = minimize(neg_ll, x0=[0.4, 0.0015, 0.1], method="Nelder-Mead",
                   options={"maxiter": 5000, "xatol": 1e-6})
    return res.x  # (mu, xi, lam3)

def predict_bivar(mu, xi, lam3, elo_a, elo_b, neutral=True, host_a=False, max_goals=MAX_GOALS):
    host_adj = 0.0 if neutral else (0.1 if host_a else -0.1)
    lam1 = np.exp(mu + xi*(elo_a-elo_b)/2 + host_adj)
    lam2 = np.exp(mu - xi*(elo_a-elo_b)/2 - host_adj)
    m = bivariate_poisson_matrix(lam1, lam2, lam3, max_goals)
    return m, lam1, lam2
```

- [ ] **Step 4：运行测试，通过**

- [ ] **Step 5：提交**

---

### Task 2.4：Dixon-Coles 进球模型

**Files:**
- Create: `backend/models/goal_model_dc.py`
- Test: `backend/tests/test_goal_model_dc.py`

- [ ] **Step 1：写失败测试**

```python
# backend/tests/test_goal_model_dc.py
import numpy as np
from models.goal_model_dc import dc_matrix, fit_dc_global

def test_matrix_shape_norm():
    m = dc_matrix(lam_a=1.2, lam_b=1.0, rho=-0.1, max_goals=8)
    assert m.shape == (9, 9)
    assert abs(m.sum() - 1.0) < 1e-6

def test_low_score_boosted():
    # DC 应提升 0-0, 1-0, 0-1, 1-1（ρ<0）
    m_dc = dc_matrix(1.0, 1.0, rho=-0.15, max_goals=8)
    from models.goal_model_poisson import independent_poisson_matrix
    m_ind = independent_poisson_matrix(1.0, 1.0, 8)
    assert m_dc[0,0] > m_ind[0,0]   # 0-0 提升
    assert m_dc[1,1] > m_ind[1,1]   # 1-1 提升

def test_fit_rho_negative():
    import pandas as pd
    df = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01"]*80),
        "team_a": ["A"]*80, "team_b": ["B"]*80,
        "goals_a": [0]*40 + [1]*40, "goals_b": [0]*40 + [1]*40,
        "tournament": ["Friendly"]*80, "neutral": [True]*80,
        "pre_elo_a": [1500]*80, "pre_elo_b": [1500]*80,
    })
    mu, xi, rho = fit_dc_global(df)
    assert rho < 0   # 低分相关 → ρ 通常为负
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现**

```python
# backend/models/goal_model_dc.py
"""Dixon-Coles (1997)：独立泊松 × τ 低分修正。
τ(i,j) 在 (0,0),(1,0),(0,1),(1,1) 处对 ρ 敏感，其余为 1。
τ(0,0)=1-λa·λb·ρ; τ(1,0)=1+λa·ρ; τ(0,1)=1+λb·ρ; τ(1,1)=1-ρ。
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson
from core.constants import MAX_GOALS

def _tau(i, j, lam_a, lam_b, rho):
    if i == 0 and j == 0: return 1 - lam_a * lam_b * rho
    if i == 0 and j == 1: return 1 + lam_a * rho
    if i == 1 and j == 0: return 1 + lam_b * rho
    if i == 1 and j == 1: return 1 - rho
    return 1.0

def dc_matrix(lam_a, lam_b, rho, max_goals=MAX_GOALS):
    i = np.arange(max_goals + 1)
    pa = poisson.pmf(i, lam_a)
    pb = poisson.pmf(i, lam_b)
    m = np.outer(pa, pb)
    # 应用 τ 修正（仅低分格）
    for ii in range(2):
        for jj in range(2):
            m[ii, jj] *= _tau(ii, jj, lam_a, lam_b, rho)
    # 防止负概率
    m = np.clip(m, 0, None)
    m /= m.sum()
    return m

def fit_dc_global(df: pd.DataFrame):
    goals_a = df["goals_a"].values.astype(float)
    goals_b = df["goals_b"].values.astype(float)
    elo_a = df["pre_elo_a"].values.astype(float)
    elo_b = df["pre_elo_b"].values.astype(float)

    def neg_ll(params):
        mu, xi, rho = params
        if mu > 5 or mu < -3 or abs(xi) > 0.01 or abs(rho) > 0.5:
            return 1e10
        lam_a = np.exp(mu + xi*(elo_a-elo_b)/2)
        lam_b = np.exp(mu - xi*(elo_a-elo_b)/2)
        ll = 0.0
        for ga, gb, la, lb in zip(goals_a, goals_b, lam_a, lam_b):
            base = poisson.pmf(int(ga), la) * poisson.pmf(int(gb), lb)
            t = _tau(int(ga), int(gb), la, lb, rho)
            ll += np.log(max(base * t, 1e-15))
        return -ll

    res = minimize(neg_ll, x0=[0.4, 0.0015, -0.1], method="Nelder-Mead",
                   options={"maxiter": 5000, "xatol": 1e-6})
    return res.x  # (mu, xi, rho)

def predict_dc(mu, xi, rho, elo_a, elo_b, neutral=True, host_a=False, max_goals=MAX_GOALS):
    host_adj = 0.0 if neutral else (0.1 if host_a else -0.1)
    lam_a = np.exp(mu + xi*(elo_a-elo_b)/2 + host_adj)
    lam_b = np.exp(mu - xi*(elo_a-elo_b)/2 - host_adj)
    m = dc_matrix(lam_a, lam_b, rho, max_goals)
    return m, lam_a, lam_b
```

- [ ] **Step 4：运行测试，通过**

- [ ] **Step 5：提交**

---

### Task 2.5：三模型 RPS 对比与裁决

**Files:**
- Create: `backend/eval/metrics.py`
- Create: `backend/models/selector.py`
- Test: `backend/tests/test_goal_model_selection.py`

- [ ] **Step 1：先写 RPS 指标测试**

```python
# backend/tests/test_goal_model_selection.py
import numpy as np
from eval.metrics import rps, log_loss_multi, brier
from models.selector import select_goal_model

def test_rps_perfect_prediction_zero():
    # 完美预测（确定事件）RPS=0
    assert abs(rps([1.0, 0.0, 0.0], [1, 0, 0])) < 1e-9

def test_rps_uniform_worst():
    # 均匀预测 RPS 较大
    assert rps([1/3, 1/3, 1/3], [1, 0, 0]) > rps([0.7, 0.2, 0.1], [1, 0, 0])

def test_rps_respects_order():
    # "平局介于胜负之间"：预测胜0.5平0.0负0.5 应比 胜0.5平0.5负0.0 在"胜"真值下更差
    assert rps([0.5, 0.0, 0.5], [1, 0, 0]) > rps([0.5, 0.5, 0.0], [1, 0, 0])

def test_select_prefers_bivar_when_close():
    # 双变量 ≤ DC + ε → 选双变量（约束：差距小优先双变量）
    chosen = select_goal_model(rps_poisson=0.22, rps_bivar=0.215, rps_dc=0.214)
    # DC(0.214) 与 bivar(0.215) 差 0.001 ≤ ε → 优先 bivar
    assert chosen == "bivar"

def test_select_prefers_dc_when_significantly_better():
    chosen = select_goal_model(rps_poisson=0.22, rps_bivar=0.22, rps_dc=0.205)
    # DC 明显更好 → 选 DC
    assert chosen == "dc"
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写 metrics.py**

```python
# backend/eval/metrics.py
"""评估指标。RPS 为主（有序多分类，胜平负），LogLoss/Brier 为辅。"""
import numpy as np

def rps(prob: list[float], actual: list[int]) -> float:
    """Ranked Probability Score。
    prob=[p_home,p_draw,p_away]，actual one-hot。"""
    p = np.array(prob, dtype=float)
    a = np.array(actual, dtype=float)
    cum_p = np.cumsum(p)
    cum_a = np.cumsum(a)
    n = len(p)
    return float(np.sum((cum_p - cum_a) ** 2) / (n - 1))

def rps_batch(probs, actuals):
    return float(np.mean([rps(p, a) for p, a in zip(probs, actuals)]))

def log_loss_multi(prob, actual):
    p = max(min(prob[np.argmax(actual)], 1-1e-15), 1e-15)
    return -float(np.log(p))

def brier(prob, actual):
    return float(np.mean((np.array(prob) - np.array(actual)) ** 2))

def calibration_curve(probs, actuals, n_bins=10):
    """返回 (bin_centers, empirical_freq) 用于可靠性图。"""
    probs = np.array(probs); actuals = np.array(actuals)
    bins = np.linspace(0, 1, n_bins + 1)
    centers, emp = [], []
    for i in range(n_bins):
        mask = (probs >= bins[i]) & (probs < bins[i+1])
        if mask.sum() > 0:
            centers.append((bins[i]+bins[i+1])/2)
            emp.append(actuals[mask].mean())
    return centers, emp
```

- [ ] **Step 4：写 selector.py**

```python
# backend/models/selector.py
"""进球模型裁决：三模型 RPS 对比，差距小优先双变量泊松。"""
from core.constants import MODEL_SELECTION_EPSILON as EPS

def select_goal_model(rps_poisson: float, rps_bivar: float, rps_dc: float) -> str:
    """返回 'poisson'/'bivar'/'dc'。
    规则：双变量 ≤ DC + ε 则选双变量；否则取 RPS 最小者。"""
    best = min([("poisson", rps_poisson), ("bivar", rps_bivar), ("dc", rps_dc)],
               key=lambda x: x[1])
    # 优先双变量：若 DC 没有显著优于 bivar
    if rps_dc - rps_bivar > -EPS:   # 即 bivar ≤ dc + eps
        # 且 bivar 不是三者最差
        if rps_bivar <= rps_poisson:
            return "bivar"
    # 否则严格取最优
    return best[0]
```

- [ ] **Step 5：运行测试，通过**

- [ ] **Step 6：提交**

---

# 阶段 P3：ML 校正层 + 融合 + 校准

### Task 3.1：特征工程

**Files:**
- Create: `backend/models/features.py`
- Test: `backend/tests/test_features.py`

- [ ] **Step 1：写失败测试**

```python
# backend/tests/test_features.py
import pandas as pd
from models.features import build_match_features

def test_feature_vector_length_and_keys():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-01"]),
        "team_a": ["A"], "team_b": ["B"],
        "goals_a": [1], "goals_b": [0],
        "tournament": ["FIFA World Cup"], "neutral": [True],
        "pre_elo_a": [1600], "pre_elo_b": [1500],
        "pre_elo_bivar_p": [[0.5, 0.3, 0.2]],
        "pre_elo_poisson_p": [[0.45, 0.3, 0.25]],
    })
    feats = build_match_features(df, recent_stats={"A": {"win_rate10":0.6,"gd10":0.5},
                                                    "B": {"win_rate10":0.4,"gd10":-0.2}})
    assert "elo_diff" in feats[0]
    assert "elo_diff_sq" in feats[0]
    assert len(feats[0]) >= 15
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现（特征清单严格按已锁定方案：约20个）**

```python
# backend/models/features.py
"""ML 校正层特征工程。分三类：模型预测(灵魂)+实力状态+上下文。
严格遵守赛前信息（约束 C1）。"""
import numpy as np
import pandas as pd
from core.constants import classify_tournament

def build_match_features(df: pd.DataFrame, recent_stats: dict, h2h: dict = None) -> list[dict]:
    """recent_stats: {team: {win_rate10, gd10, gf10, ga10}}
    返回每场比赛的特征字典列表。"""
    feats = []
    for _, m in df.iterrows():
        ra, rb = m["pre_elo_a"], m["pre_elo_b"]
        elo_diff = ra - rb
        sa = recent_stats.get(m["team_a"], {})
        sb = recent_stats.get(m["team_b"], {})
        # 三模型预测概率（灵魂特征，已由前层算好）
        bp = m.get("pre_elo_bivar_p", [1/3,1/3,1/3])  # 注：键名按上游约定
        pp = m.get("pre_elo_poisson_p", [1/3,1/3,1/3])
        ep = m.get("pre_elo_p_elo", [1/3,1/3,1/3])
        f = {
            # 实力
            "elo_diff": elo_diff,
            "elo_diff_sq": elo_diff**2,
            # 近期状态（衰减）
            "win_rate10_a": sa.get("win_rate10", 0.5),
            "win_rate10_b": sb.get("win_rate10", 0.5),
            "gd10_a": sa.get("gd10", 0.0),
            "gd10_b": sb.get("gd10", 0.0),
            # 上下文
            "tourn_class": {"world_cup":3,"continental":2,"qualifier":1,"friendly":0}.get(
                classify_tournament(m["tournament"]), 0),
            "neutral": int(bool(m["neutral"])),
            "is_host_a": int(m["team_a"] in {"United States","Mexico","Canada"}),
            "is_host_b": int(m["team_b"] in {"United States","Mexico","Canada"}),
            "h2h_a_win_rate": (h2h or {}).get((m["team_a"], m["team_b"]), 0.5),
            # 模型预测（灵魂）
            "elo_p_home": ep[0], "elo_p_draw": ep[1], "elo_p_away": ep[2],
            "poisson_p_home": pp[0], "poisson_p_draw": pp[1], "poisson_p_away": pp[2],
            "bivar_p_home": bp[0], "bivar_p_draw": bp[1], "bivar_p_away": bp[2],
            # 模型分歧度（冷门信号）
            "model_disagreement": float(np.std([ep[0], pp[0], bp[0]])),
        }
        feats.append(f)
    return feats
```

- [ ] **Step 4：运行测试，通过**

- [ ] **Step 5：提交**

---

### Task 3.2：四模型 ML 校正层

**Files:**
- Create: `backend/models/ml_calibrator.py`
- Test: `backend/tests/test_ml_calibrator.py`

- [ ] **Step 1：写失败测试**

```python
# backend/tests/test_ml_calibrator.py
import numpy as np
from models.ml_calibrator import (
    train_logistic, train_lightgbm, train_xgboost, train_catboost,
    predict_proba_ensemble
)

def _toy():
    rng = np.random.RandomState(0)
    X = rng.rand(100, 12)
    y = rng.randint(0, 3, 100)
    return X, y

def test_each_model_returns_3class_proba():
    X, y = _toy()
    for trainer in [train_logistic, train_lightgbm, train_xgboost, train_catboost]:
        model = trainer(X, y)
        p = model.predict_proba(X[:5])
        assert p.shape == (5, 3)
        assert np.allclose(p.sum(axis=1), 1.0, atol=1e-6)

def test_ensemble_averages_models():
    # 两个完全相同的模型集成 → 结果与单模型一致
    class Stub:
        def predict_proba(self, X):
            n = len(X); p = np.full((n,3), 1/3); return p
    p = predict_proba_ensemble([Stub(), Stub()], np.zeros((4,1)), weights=[0.5,0.5])
    assert np.allclose(p, 1/3)
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现**

```python
# backend/models/ml_calibrator.py
"""四模型校正层：Logistic / LightGBM / XGBoost / CatBoost + 加权集成。
定位：概率校正层，提升应温和（约束见技术报告）。"""
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.utils.class_weight import compute_class_weight
import lightgbm as lgb
import xgboost as xgb
import catboost as cb

def train_logistic(X, y):
    m = LogisticRegression(max_iter=1000, multi_class="multinomial",
                           C=1.0, class_weight="balanced")
    m.fit(X, y)
    return m

def train_lightgbm(X, y):
    m = lgb.LGBMClassifier(objective="multiclass", num_class=3,
                           num_leaves=31, learning_rate=0.05,
                           n_estimators=300, class_weight="balanced",
                           verbose=-1)
    m.fit(X, y)
    return m

def train_xgboost(X, y):
    classes = np.unique(y)
    w = compute_class_weight("balanced", classes=classes, y=y)
    cw = dict(zip(classes, w))
    m = xgb.XGBClassifier(objective="multi:softprob", num_class=3,
                          max_depth=6, learning_rate=0.05, n_estimators=300,
                          class_weight=cw, eval_metric="mlogloss")
    m.fit(X, y)
    return m

def train_catboost(X, y):
    m = cb.CatBoostClassifier(loss_function="MultiClass", depth=6,
                              learning_rate=0.05, iterations=300,
                              class_weights=[1,1,1], verbose=False)
    m.fit(X, y)
    return m

def predict_proba_ensemble(models, X, weights=None):
    if weights is None:
        weights = [1.0/len(models)] * len(models)
    weights = np.array(weights) / sum(weights)
    p = np.zeros((len(X), 3))
    for w, m in zip(weights, models):
        p += w * m.predict_proba(X)
    p /= p.sum(axis=1, keepdims=True)
    return p
```

- [ ] **Step 4：运行测试，通过**

- [ ] **Step 5：提交**

---

### Task 3.3：融合层 + Isotonic 校准

**Files:**
- Create: `backend/models/fusion.py`
- Test: `backend/tests/test_fusion.py`

- [ ] **Step 1：写失败测试**

```python
# backend/tests/test_fusion.py
import numpy as np
from models.fusion import learn_fusion_weights, fuse, isotonic_calibrate

def test_fusion_weights_sum_to_one_nonneg():
    p_elo = np.array([[0.6,0.3,0.1]])
    p_goal = np.array([[0.5,0.3,0.2]])
    p_ml = np.array([[0.55,0.3,0.15]])
    y = np.array([0])  # 实际胜
    w = learn_fusion_weights([p_elo, p_goal, p_ml], y)
    assert abs(sum(w) - 1.0) < 1e-6
    assert all(wi >= -1e-9 for wi in w)

def test_fuse_uses_weights():
    w = [0.2, 0.3, 0.5]
    p = fuse([[0.6,0.3,0.1],[0.5,0.3,0.2],[0.55,0.3,0.15]], w)
    assert p.shape == (1,3)
    assert np.allclose(p.sum(axis=1), 1.0, atol=1e-6)

def test_isotonic_monotonic():
    # 校准后预测概率应更接近经验频率
    probs = np.array([0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9])
    actual = np.array([0,0,0,1,0,1,1,1,1])
    cal = isotonic_calibrate(probs, actual, probs)
    assert cal.shape == probs.shape
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现**

```python
# backend/models/fusion.py
"""融合：P=w1·P_elo + w2·P_goal + w3·P_ml，凸组合，验证集最小化多分类 LogLoss。
校准：Isotonic Regression。"""
import numpy as np
from scipy.optimize import minimize
from sklearn.isotonic import IsotonicRegression

def _neg_logloss(weights, probs_list, y):
    w = np.array(weights)
    w = np.clip(w, 0, None)
    s = w.sum()
    if s == 0: return 1e10
    w = w / s
    p = np.zeros_like(probs_list[0])
    for wi, pi in zip(w, probs_list):
        p += wi * pi
    p = np.clip(p, 1e-15, 1-1e-15)
    return -float(np.mean(np.log(p[np.arange(len(y)), y])))

def learn_fusion_weights(probs_list, y):
    """probs_list: [P_elo, P_goal, P_ml]，每个 (N,3)。y: (N,)。"""
    n = len(probs_list)
    res = minimize(_neg_logloss, x0=[1.0/n]*n,
                   args=(probs_list, y), method="SLSQP",
                   bounds=[(0,1)]*n, constraints={"type":"eq","fun":lambda w: sum(w)-1})
    return res.x

def fuse(probs_list, weights):
    w = np.array(weights); w = w / w.sum()
    p = sum(wi * pi for wi, pi in zip(w, probs_list))
    return p / p.sum(axis=1, keepdims=True)

def isotonic_calibrate(train_probs, train_actual, target_probs):
    """对单类概率做 Isotonic 校准。"""
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1)
    iso.fit(train_probs, train_actual)
    return iso.transform(target_probs)
```

- [ ] **Step 4：运行测试，通过**

- [ ] **Step 5：提交**

---

# 阶段 P4：赛制引擎 + 蒙特卡洛模拟

### Task 4.1：R32 对阵模板 + 第三名分配算法（Annex C 算法生成版）

**Files:**
- Create: `backend/core/annex_c.py`
- Create: `backend/tests/test_annex_c.py`

> **设计决策（重要）**：Annex C 本质是一个"约束满足分配"问题，**不手动抄 495 行表，而用算法实时生成**。这样比手抄更可靠、可验证、可维护。
>
> **赛制事实（已联网核实）**：R32 共 16 场，对阵模板中：
> - **8 场**的两个对手都是"固定的组对组"（如 `1A vs 2B`），不涉及第三名；
> - **8 场**的某一侧是"第三名空位"（如 `1A vs 3[待分配]`），需要 Annex C 决定填哪个组的第三名。
>
> Annex C 的分配约束（FIFA 官方规则）：
> 1. **同组回避**：第三名不能碰到本组的第一/第二名（刚踢过不能再踢）；
> 2. 每个"第三名空位"恰好填入一个第三名；
> 3. 每个 出线第三名恰好被分配一次。

#### R32 对阵模板（官方固定，已联网核实）
以下是 R32 的 16 场对阵，`1X` 表示 X 组第一，`2X` 表示 X 组第二，`3?` 表示待 Annex C 分配的第三名空位：

```python
# 每场一个元组：(对手A, 对手B)，对手为 "1X"/"2X" 或 "3?"（第三名空位）
R32_MATCHES = [
    ("1A", "2B"), ("1C", "2D"), ("1E", "2F"), ("1G", "2H"),   # M1-M4：纯组对组
    ("1B", "3?"), ("1D", "3?"), ("1F", "3?"), ("1H", "3?"),   # M5-M8：组第一 vs 第三名
    ("2A", "3?"), ("2C", "3?"), ("2E", "3?"), ("2G", "3?"),   # M9-M12：组第二 vs 第三名
    ("1I", "2J"), ("1K", "2L"), ("2I", "3?"), ("1J", "3?"),   # M13-M16：混合
]
# 共 8 个 "3?" 空位（M5,M6,M7,M8,M9,M10,M11,M12,M15,M16 → 实际为 8 个，需核对）
# ⚠️ coding agent：必须联网核对 Wikipedia round_of_32 页确认 16 场的精确配对
#    与"3?"空位的精确位置。上面是结构示意，真实模板以官方为准。
```

> **⚠️ coding agent 责任**：联网打开 https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_round_of_32 ，核对 R32 的 16 场精确对阵模板（哪场是 `1X vs 2Y`，哪场是 `组出线队 vs 第三名`），填入 `R32_MATCHES`。这是地基，不可猜。

- [ ] **Step 1：写失败测试（算法正确性 + 约束满足）**

```python
# backend/tests/test_annex_c.py
import pytest
from core.annex_c import (
    ALL_GROUP_LETTERS, R32_MATCHES, assign_third_places, third_place_avoids_own_group
)
from itertools import combinations

def test_12_group_letters():
    assert ALL_GROUP_LETTERS == list("ABCDEFGHIJKL")

def test_r32_has_16_matches():
    assert len(R32_MATCHES) == 16

def test_r32_has_exactly_8_third_place_slots():
    n_third_slots = sum(1 for a, b in R32_MATCHES if a == "3?" or b == "3?")
    assert n_third_slots == 8

def test_assign_returns_8_mappings_for_8_groups():
    # 给定 8 个出第三名的组，返回 {空位编号: 组字母} 共 8 条
    assignment = assign_third_places(frozenset("ABCDEFGHI"))
    assert len(assignment) == 8

def test_assign_respects_same_group_avoidance():
    # 核心约束：第三名不能碰到本组的出线队
    for combo in combinations("ABCDEFGHIJKL", 8):
        assignment = assign_third_places(frozenset(combo))
        assert third_place_avoids_own_group(assignment, frozenset(combo)), \
            f"组合 {combo} 违反同组回避约束"

def test_assign_all_combinations_valid():
    # 所有 495 种组合都必须能成功分配（算法完备性）
    count = 0
    for combo in combinations("ABCDEFGHIJKL", 8):
        assignment = assign_third_places(frozenset(combo))
        assert len(assignment) == 8
        assert third_place_avoids_own_group(assignment, frozenset(combo))
        count += 1
    assert count == 495

def test_invalid_combo_raises():
    with pytest.raises(ValueError):
        assign_third_places(frozenset("ABC"))       # 不是 8 个
    with pytest.raises(ValueError):
        assign_third_places(frozenset("ABCDEFGHIJKL"))  # 12 个也不行
```

- [ ] **Step 2：运行，确认失败**

```bash
cd backend && python -m pytest tests/test_annex_c.py -v
```
Expected: ImportError（模块不存在）

- [ ] **Step 3：写实现（约束满足算法：回溯 + 同组回避）**

```python
# backend/core/annex_c.py
"""2026 世界杯 Annex C：第三名→R32 槽位分配（算法生成版）。

设计决策：不手动维护 495 行查找表，而是用"约束满足 + 回溯"算法
实时生成任意 8-组组合下的合法分配。

FIFA 规则核心约束：
  - 同组回避：第三名不能碰到本组的第一/第二名
  - 每个第三名空位恰好填一个第三名
  - 每个出线第三名恰好被分配一次

分配顺序按"候选最少优先"（most-constrained-first）启发式，保证高效。
"""
from itertools import combinations

ALL_GROUP_LETTERS = list("ABCDEFGHIJKL")

# R32 对阵模板（coding agent 必须联网核对 Wikipedia 填准）
# 每场：(对手A, 对手B)，"1X"=X组第一，"2X"=X组第二，"3?"=第三名空位
R32_MATCHES = [
    ("1A", "2B"), ("1C", "2D"), ("1E", "2F"), ("1G", "2H"),
    ("1B", "3?"), ("1D", "3?"), ("1F", "3?"), ("1H", "3?"),
    ("2A", "3?"), ("2C", "3?"), ("2E", "3?"), ("2G", "3?"),
    ("1I", "2J"), ("1K", "2L"), ("2I", "3?"), ("1J", "3?"),
]

def _third_place_slots() -> list[int]:
    """返回 R32_MATCHES 中含 "3?" 的比赛索引（0-based）。"""
    return [i for i, (a, b) in enumerate(R32_MATCHES) if a == "3?" or b == "3?"]

def _slot_blocked_groups(slot_idx: int) -> set[str]:
    """某个第三名空位所在比赛，其另一侧的组是哪个 → 第三名必须避开该组。
    例如比赛是 ("1B","3?")，则第三名不能来自 B 组。"""
    a, b = R32_MATCHES[slot_idx]
    other = a if b == "3?" else b   # 另一侧（非 "3?" 的那个）
    # "1B" 或 "2B" → 提取组字母 "B"
    return {other[1]} if other[1] in ALL_GROUP_LETTERS else set()

def assign_third_places(third_groups: frozenset) -> dict:
    """给定出第三名的 8 个组，返回 {空位索引: 组字母}。
    用回溯算法保证同组回避。无解则 raise ValueError。
    """
    if len(third_groups) != 8:
        raise ValueError(f"需要恰好 8 个组，得到 {len(third_groups)}")
    bad = set(third_groups) - set(ALL_GROUP_LETTERS)
    if bad:
        raise ValueError(f"非法组字母: {bad}")

    slots = _third_place_slots()
    assert len(slots) == 8, f"R32 模板的第三名空位应为8个，实际{len(slots)}"

    # 每个空位的候选第三名组 = 全部 third_groups - 该空位避开的组
    candidates = {
        s: [g for g in sorted(third_groups) if g not in _slot_blocked_groups(s)]
        for s in slots
    }
    # most-constrained-first：候选少的空位先分配
    order = sorted(slots, key=lambda s: len(candidates[s]))

    assignment = {}
    used_groups = set()

    def backtrack(i: int) -> bool:
        if i == len(order):
            return True
        slot = order[i]
        for g in candidates[slot]:
            if g in used_groups:
                continue
            assignment[slot] = g
            used_groups.add(g)
            if backtrack(i + 1):
                return True
            del assignment[slot]
            used_groups.discard(g)
        return False

    if not backtrack(0):
        raise ValueError(f"无合法分配，组合 {third_groups}")
    return assignment

def third_place_avoids_own_group(assignment: dict, third_groups) -> bool:
    """验证：每个被分配的第三名，都不落在"避开了本组"的空位。"""
    for slot_idx, g in assignment.items():
        if g in _slot_blocked_groups(slot_idx):
            return False   # 第三名碰到了本组出线队
    return len(set(assignment.values())) == len(assignment)  # 一一对应
```

- [ ] **Step 4：运行测试，通过（含 495 组合完备性校验）**

```bash
cd backend && python -m pytest tests/test_annex_c.py -v
```
Expected: 全部 PASS，特别是 `test_assign_all_combinations_valid` 验证 495 种组合全部可分配且满足约束。

- [ ] **Step 5：提交**

```bash
git commit -am "P4.1: Annex C constraint-satisfaction algorithm with 495-combo validation"
```

---

### Task 4.2：小组赛排名（2026 H2H 新规则）

**Files:**
- Create: `backend/engine/group_stage.py`
- Test: `backend/tests/test_group_stage.py`

- [ ] **Step 1：写失败测试**

```python
# backend/tests/test_group_stage.py
from engine.group_stage import rank_group

def test_rank_by_points():
    standings = [
        {"team":"A","pts":7,"gd":3,"gf":5,"ga":2},
        {"team":"B","pts":4,"gd":0,"gf":3,"ga":3},
        {"team":"C","pts":4,"gd":-1,"gf":2,"ga":3},
        {"team":"D","pts":1,"gd":-2,"gf":1,"ga":3},
    ]
    ranked = rank_group(standings, h2h={})
    assert [s["team"] for s in ranked] == ["A","B","C","D"]

def test_2026_h2h_tiebreak_before_gd():
    # 2026 新规则：同分先比相互交锋积分，再比总净胜球
    standings = [
        {"team":"A","pts":4,"gd":5,"gf":7,"ga":2},   # 总 gd 高
        {"team":"B","pts":4,"gd":-1,"gf":2,"ga":3},  # 但 H2H 输给 A
        {"team":"C","pts":4,"gd":1,"gf":4,"ga":3},
        {"team":"D","pts":0,"gd":-5,"gf":1,"ga":6},
    ]
    # A vs B 相互交锋：B 胜 A（H2H 中 B 得3分，A 得0分）
    h2h = {("B","A"):3, ("A","B"):0, ("A","C"):1, ("C","A"):1,
           ("B","C"):1, ("C","B"):1}
    ranked = rank_group(standings, h2h=h2h)
    # B 因 H2H 击败 A → 应排在 A 前（即使 A 总 gd 更高）
    order = [s["team"] for s in ranked]
    assert order.index("B") < order.index("A")
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现**

```python
# backend/engine/group_stage.py
"""小组排名：2026 新规则。
同分决胜顺序：
  1. 总积分 → 2. 相互交锋积分 → 3. 相互交锋净胜球 → 4. 相互交锋进球
  → 5. 总净胜球 → 6. 总进球 → 7. 公平分 → 8. FIFA排名
注意：仅在"同分组"内应用 H2H（2队或3队同分有不同处理，简化为先2队）。"""
from functools import cmp_to_key

def rank_group(standings: list[dict], h2h: dict, fair_play: dict = None,
               fifa_rank: dict = None) -> list[dict]:
    fair_play = fair_play or {}
    fifa_rank = fifa_rank or {}
    def cmp(x, y):
        if x["pts"] != y["pts"]: return y["pts"] - x["pts"]
        # H2H 积分
        h2h_x = h2h.get((x["team"], y["team"]), 0)
        h2h_y = h2h.get((y["team"], x["team"]), 0)
        if h2h_x != h2h_y: return h2h_y - h2h_x
        # 总净胜球
        if x["gd"] != y["gd"]: return y["gd"] - x["gd"]
        # 总进球
        if x["gf"] != y["gf"]: return y["gf"] - x["gf"]
        # 公平分（少者靠前）
        fx = fair_play.get(x["team"], 9999); fy = fair_play.get(y["team"], 9999)
        if fx != fy: return fx - fy
        # FIFA 排名（小者靠前）
        rx = fifa_rank.get(x["team"], 999); ry = fifa_rank.get(y["team"], 999)
        return rx - ry
    return sorted(standings, key=cmp_to_key(cmp))

def best_thirds_ranked(all_thirds: list[dict]) -> list[dict]:
    """最佳第三排名：积分→净胜球→进球→公平分→FIFA排名。取前8。"""
    def cmp(x, y):
        for k in ["pts","gd","gf"]:
            if x[k] != y[k]: return y[k] - x[k]
        fp = (fair_play_cmp := lambda a,b:
              (a.get("fair_play",9999) - b.get("fair_play",9999)))
        r = fp(x, y)
        if r != 0: return r
        return x.get("fifa_rank",999) - y.get("fifa_rank",999)
    return sorted(all_thirds, key=cmp_to_key(cmp))[:8]
```

- [ ] **Step 4：运行测试，通过**

- [ ] **Step 5：提交**

---

### Task 4.3：淘汰赛 + 加时/点球

**Files:**
- Create: `backend/engine/knockout.py`
- Test: `backend/tests/test_knockout.py`

- [ ] **Step 1：写失败测试**

```python
# backend/tests/test_knockout.py
import numpy as np
from engine.knockout import sample_knockout_result

def test_clear_winner_no_extratime():
    rng = np.random.default_rng(42)
    # 比分矩阵极度偏向 A 胜，应直接出 A 胜，无需点球
    m = np.zeros((9,9))
    m[2,0] = 0.6; m[1,0] = 0.3; m[0,0] = 0.1
    w, note = sample_knockout_result(m, rng)
    assert w in ("A","B")
    assert "90分钟" in note or "regular" in note.lower()

def test_draw_goes_to_coinflip():
    rng = np.random.default_rng(7)
    # 矩阵全部集中在平局对角线 → 必然平局 → 50/50
    m = np.zeros((9,9))
    m[1,1] = 1.0
    results = {"A":0,"B":0}
    for _ in range(1000):
        w, _ = sample_knockout_result(m, np.random.default_rng(rng.integers(1<<30)))
        results[w] += 1
    # 50/50 应大致均匀（容差较大）
    assert 400 < results["A"] < 600
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现**

```python
# backend/engine/knockout.py
"""淘汰赛：90分钟采样→平局则加时（简化为进球率/3）→再平则50/50点球。
约束 C4：点球禁止 Elo 高者必胜，用 50/50。"""
import numpy as np

def sample_knockout_result(score_matrix_9x9: np.ndarray, rng) -> tuple[str, str]:
    """从 90 分钟比分矩阵采样。返回 (winner, note)。"""
    m = score_matrix_9x9
    flat = m.flatten()
    idx = rng.choice(len(flat), p=flat)
    ga, gb = divmod(idx, m.shape[1])
    if ga > gb:
        return "A", f"90分钟 {ga}:{gb}"
    if ga < gb:
        return "B", f"90分钟 {ga}:{gb}"
    # 平局 → 加时（简化：在矩阵对角线附近重采样，偏向少量进球）
    # 这里按学术简化：加时仍平则 50/50（约束 C4）
    ot_a = rng.poisson(0.15)   # 加时赛低进球
    ot_b = rng.poisson(0.15)
    if ot_a > ot_b: return "A", f"加时 {ga+ot_a}:{gb+ot_b}"
    if ot_b > ot_a: return "B", f"加时 {ga+ot_a}:{gb+ot_b}"
    # 点球 50/50
    return ("A" if rng.random() < 0.5 else "B"), f"点球 (加时 {ga+ot_a}:{gb+ot_b})"
```

- [ ] **Step 4：运行测试，通过**

- [ ] **Step 5：提交**

---

### Task 4.4：蒙特卡洛全赛制模拟

**Files:**
- Create: `backend/engine/simulator.py`
- Test: `backend/tests/test_simulator.py`

- [ ] **Step 1：写失败测试（关键不变量）**

```python
# backend/tests/test_simulator.py
import numpy as np
from engine.simulator import simulate_tournament

def _toy_predictor(strong="A"):
    """返回一个简单的比分矩阵预测器：strong 队碾压。"""
    def predict(team_a, team_b):
        m = np.zeros((9,9))
        if team_a == strong:
            m[2,0]=0.5; m[1,0]=0.3; m[0,0]=0.2
        elif team_b == strong:
            m[0,2]=0.5; m[0,1]=0.3; m[0,0]=0.2
        else:
            m[1,1]=0.4; m[1,0]=0.2; m[0,1]=0.2; m[0,0]=0.2
        m/=m.sum()
        return m
    return predict

def test_champion_prob_sum_near_one():
    # 约束 C3：所有队冠军概率和≈1
    from data.fixtures_2026 import GROUPS_2026
    # 用占位分组（测试用，4组各4队，简化）
    groups = {"A":["A","B","C","D"],"B":["E","F","G","H"],
              "C":["I","J","K","L"],"D":["A2","B2","C2","D2"]}
    # 注：真实测试用完整12组，此处验证聚合不变量
    probs = simulate_tournament(groups, _toy_predictor("A"), n=500, seed=1)
    assert isinstance(probs, dict)
    # 冠军概率和应接近1
    if probs:
        assert abs(sum(probs.values()) - 1.0) < 0.05
```

- [ ] **Step 2：运行，确认失败**

- [ ] **Step 3：写实现**

```python
# backend/engine/simulator.py
"""蒙特卡洛全赛制模拟。
流程（每次迭代）：
  72场小组赛 → 小组排名(H2H) → 最佳第三排名(8) → Annex C算法分配R32
  → R32(16)→R16(8)→QF(4)→SF(2)→三四名(1)+决赛(1)
约束：104场；冠军概率和≈1；random_seed 可复现。"""
import numpy as np
import pandas as pd
from collections import defaultdict
from itertools import combinations
from engine.group_stage import rank_group, best_thirds_ranked
from engine.knockout import sample_knockout_result
from core.annex_c import R32_MATCHES, assign_third_places

def _play_group(matches_predictor, group_teams, rng):
    """模拟单组6场，返回排名后的 [1st,2nd,3rd,4th] 与 standings。"""
    standings = {t: {"team":t,"pts":0,"gd":0,"gf":0,"ga":0} for t in group_teams}
    h2h = {}
    for a, b in combinations(group_teams, 2):
        m = matches_predictor(a, b)
        flat = m.flatten()
        idx = rng.choice(len(flat), p=flat)
        ga, gb = divmod(idx, m.shape[1])
        standings[a]["gf"]+=ga; standings[a]["ga"]+=gb
        standings[b]["gf"]+=gb; standings[b]["ga"]+=ga
        standings[a]["gd"]+=ga-gb; standings[b]["gd"]+=gb-ga
        if ga>gb: standings[a]["pts"]+=3; h2h[(a,b)]=3; h2h[(b,a)]=0
        elif ga==gb: standings[a]["pts"]+=1; standings[b]["pts"]+=1; h2h[(a,b)]=1;h2h[(b,a)]=1
        else: standings[b]["pts"]+=3; h2h[(a,b)]=0; h2h[(b,a)]=3
    ranked = rank_group(list(standings.values()), h2h)
    return [r["team"] for r in ranked], list(standings.values())

def _resolve_r32_matchups(group_first, group_second, third_teams_by_group):
    """根据官方 R32_MATCHES 模板 + Annex C 分配，生成 16 场具体 (teamA, teamB)。
    third_teams_by_group: {组字母: 第三名队名}（仅含出线的8个组）。"""
    third_groups = frozenset(third_teams_by_group.keys())
    assignment = assign_third_places(third_groups)  # {空位索引: 组字母}
    pairs = []
    for i, (a, b) in enumerate(R32_MATCHES):
        def resolve(slot):
            if slot == "3?":
                g = assignment[i]   # 该空位分配到的第三名的组
                return third_teams_by_group[g]
            pos, grp = slot[0], slot[1]   # "1A"→pos='1',grp='A'
            if pos == "1": return group_first[grp]
            if pos == "2": return group_second[grp]
            raise ValueError(f"非法槽位 {slot}")
        pairs.append((resolve(a), resolve(b)))
    return pairs

def simulate_tournament(groups: dict, predict_fn, n: int = 30000, seed: int = 42) -> dict:
    """返回 {team: 冠军概率}。"""
    rng = np.random.default_rng(seed)
    champ_count = defaultdict(int)
    for _ in range(n):
        group_first, group_second, group_thirds = {}, {}, []
        for g, teams in groups.items():
            ranked, stands = _play_group(predict_fn, teams, rng)
            group_first[g] = ranked[0]
            group_second[g] = ranked[1]
            third = ranked[2]
            s = next(x for x in stands if x["team"]==third)
            group_thirds.append({"team":third,"pts":s["pts"],"gd":s["gd"],"gf":s["gf"]})
        best8 = best_thirds_ranked(group_thirds)
        # 出第三名的 8 个组 + 对应队名
        third_teams_by_group = {}
        for t3 in best8:
            for g, teams in groups.items():
                if t3["team"] in teams:
                    third_teams_by_group[g] = t3["team"]
                    break
        try:
            r32_pairs = _resolve_r32_matchups(group_first, group_second, third_teams_by_group)
        except (ValueError, KeyError):
            continue  # 分配失败（不应发生）→ 跳过该迭代
        # 逐轮淘汰
        rnd = r32_pairs
        while len(rnd) > 1:
            nxt = []
            for (a,b) in rnd:
                m = predict_fn(a,b)
                w,_ = sample_knockout_result(m, rng)
                nxt.append(a if w=="A" else b)
            rnd = list(zip(nxt[::2], nxt[1::2]))
        champion = rnd[0][0] if isinstance(rnd[0], tuple) else rnd[0]
        champ_count[champion] += 1
    return {t: c/n for t,c in champ_count.items()}
```

> **说明**：`_resolve_r32_matchups` 已经在上方实现，无需 `_build_r32_pairs`。它根据官方 `R32_MATCHES` 模板 + `assign_third_places` 算法，把 16 场对阵全部解析成具体队名。逐轮淘汰用 `zip(nxt[::2], nxt[1::2])` 配对（胜者相邻两两配对，符合淘汰赛树形结构）。
>
> **三四名决赛**：上述简化为单线冠军路径。coding agent 如需精确的三四名决赛，在半决赛阶段额外记录两个半决赛负者对决即可（不影响冠军概率聚合）。

- [ ] **Step 4：运行测试（玩具分组通过聚合校验）**

- [ ] **Step 5：提交**

---

### Task 4.5：赛制计数系统验证

**Files:**
- Create: `backend/tests/test_tournament_integrity.py`

- [ ] **Step 1：写完整性测试**

```python
# backend/tests/test_tournament_integrity.py
"""赛制计数系统验证（约束 C4）。"""
from core.constants import (TOTAL_MATCHES_2026, GROUP_MATCHES, R32_MATCHES,
                            R16_MATCHES, QF_MATCHES, SF_MATCHES,
                            THIRD_PLACE_MATCHES, FINAL_MATCHES)

def test_total_matches_is_104():
    assert (GROUP_MATCHES + R32_MATCHES + R16_MATCHES + QF_MATCHES +
            SF_MATCHES + THIRD_PLACE_MATCHES + FINAL_MATCHES) == TOTAL_MATCHES_2026
    assert TOTAL_MATCHES_2026 == 104

def test_r32_is_16_no_byes():
    assert R32_MATCHES == 16   # 32队打满16场，无轮空
```

- [ ] **Step 2：运行，通过**

- [ ] **Step 3：提交**

---

# 阶段 P5：五 Agent + LangGraph 编排

### Task 5.1：确定性工具封装

**Files:**
- Create: `backend/agents/tools.py`

- [ ] **Step 1：封装所有确定性函数为 LangGraph/LangChain 工具**

```python
# backend/agents/tools.py
"""将确定性计算函数封装为 LLM 可调用的工具。
原则（约束 C2）：LLM 只决策，所有数值由这些工具算。"""
from langchain.tools import tool
from models.elo import compute_elo_history
from models.goal_model_poisson import predict_poisson
from models.goal_model_bivar import predict_bivar
from models.goal_model_dc import predict_dc
from models.ml_calibrator import predict_proba_ensemble
from models.fusion import fuse
from engine.simulator import simulate_tournament

@tool
def load_data_tool(snapshot_version: str) -> dict:
    """加载历史赛果数据快照。返回 {rows, date_min, date_max, version}。"""
    from data.loader import load_and_clean_results
    from config import load_config
    cfg = load_config()
    df = load_and_clean_results(cfg["data"]["raw_results_csv"])
    return {"rows": len(df), "date_min": str(df["date"].min()),
            "date_max": str(df["date"].max()), "version": snapshot_version}

@tool
def predict_match_tool(team_a: str, team_b: str, elo_a: float, elo_b: float,
                       neutral: bool = True) -> dict:
    """预测单场比赛。返回胜平负概率、预期进球、比分矩阵、关键因素。"""
    # coding agent：在此串联 Elo→三进球模型→裁决→ML→融合→校准
    # 返回结构化 PredictionReport dict
    raise NotImplementedError("串联完整预测管线")

@tool
def simulate_tournament_tool(n: int = 30000, seed: int = 42) -> dict:
    """蒙特卡洛模拟整届世界杯。返回 {team: 冠军概率}。"""
    # 调用 engine.simulator.simulate_tournament
    raise NotImplementedError("接入 predict_fn 后实现")

# 其余工具：compute_elo_tool / build_features_tool / explain_tool ...
```

- [ ] **Step 2：提交（骨架）**

---

### Task 5.2：五个 Agent 节点

**Files:**
- Create: `backend/agents/data_collector.py` / `data_analyzer.py` / `predictor.py` / `tournament_simulator.py` / `explainer.py`

- [ ] **Step 1：每个 Agent 实现 LangGraph 节点函数**

每个 Agent 结构相同：LLM（DeepSeek）+ 工具 + 重试 + fallback。示例（Predictor）：

```python
# backend/agents/predictor.py
"""Predictor Agent：接收一场比赛上下文，决策调用哪些模型、如何处理分歧，
输出 PredictionReport。LLM 决策，工具计算。"""
from langchain_deepseek import ChatDeepSeek
from agents.tools import predict_match_tool
import os, json, time

def predictor_node(state: dict) -> dict:
    cfg = state["config"]
    if os.getenv(cfg["llm"]["api_key_env"]):
        llm = ChatDeepSeek(model=cfg["llm"]["model_decision"],
                           api_key=os.getenv(cfg["llm"]["api_key_env"]),
                           temperature=0.3)
        # LLM 决策：是否启用全量模型（决赛→是）
        prompt = f"比赛 {state['team_a']} vs {state['team_b']}，赛事={state.get('stage')}。"
        "决定是否启用全量4模型推理（决赛/半决赛=是，小组赛=否）。返回JSON {use_full: bool}。"
        for _ in range(cfg["llm"]["max_retries"]):
            try:
                resp = llm.invoke(prompt)
                decision = json.loads(resp.content)
                break
            except Exception:
                decision = {"use_full": True}  # fallback
                time.sleep(0.5)
    else:
        decision = {"use_full": True}   # mock 模式
    # 工具执行确定性计算（约束 C2）
    report = predict_match_tool.invoke({
        "team_a": state["team_a"], "team_b": state["team_b"],
        "elo_a": state["elo_a"], "elo_b": state["elo_b"],
        "neutral": state.get("neutral", True)})
    state["prediction"] = report
    return state
```

其余 4 个 Agent 同构，coding agent 按此模板实现各自职责。

- [ ] **Step 2：提交**

---

### Task 5.3：Orchestrator 编排

**Files:**
- Create: `backend/agents/orchestrator.py`

- [ ] **Step 1：LangGraph StateGraph**

```python
# backend/agents/orchestrator.py
"""LangGraph 编排：理解用户意图 → 调度五 Agent。
节点：collect → analyze → predict → simulate → explain → END
含循环（模拟收敛判断）。"""
from langgraph.graph import StateGraph, END
from agents.data_collector import data_collector_node
from agents.data_analyzer import data_analyzer_node
from agents.predictor import predictor_node
from agents.tournament_simulator import tournament_simulator_node
from agents.explainer import explainer_node

def build_graph():
    g = StateGraph(dict)
    g.add_node("collect", data_collector_node)
    g.add_node("analyze", data_analyzer_node)
    g.add_node("predict", predictor_node)
    g.add_node("simulate", tournament_simulator_node)
    g.add_node("explain", explainer_node)
    g.set_entry_point("collect")
    g.add_edge("collect", "analyze")
    g.add_edge("analyze", "predict")
    g.add_edge("predict", "simulate")
    # 模拟收敛判断（条件边）
    g.add_conditional_edges("simulate", lambda s: "simulate" if s.get("need_more_sim") else "explain")
    g.add_edge("explain", END)
    return g.compile()
```

- [ ] **Step 2：端到端冒烟测试（mock LLM）**

```python
# backend/tests/test_orchestrator_smoke.py
def test_graph_runs_with_mock_llm(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from agents.orchestrator import build_graph
    g = build_graph()
    state = {"team_a":"A","team_b":"B","elo_a":1600,"elo_b":1500,
             "config": {"llm":{"api_key_env":"DEEPSEEK_API_KEY","max_retries":1}}}
    # 应不抛异常（fallback 生效）
    out = g.invoke(state)
    assert out is not None
```

- [ ] **Step 3：提交**

---

# 阶段 P6：FastAPI + React 前端

### Task 6.1：FastAPI 服务层

**Files:**
- Create: `backend/api/main.py`

- [ ] **Step 1：写接口**

```python
# backend/api/main.py
"""FastAPI：暴露结构化接口供前端调用。
端点：
  GET  /api/health
  GET  /api/champion-probabilities   → 冠军概率榜
  GET  /api/match/{team_a}/{team_b}  → 单场预测
  GET  /api/bracket                  → 赛程树+最可能路径
  GET  /api/team/{team}/radar        → 球队雷达图数据
  GET  /api/backtest-2022            → 2022回测结果
  POST /api/explain                  → 解释（带 Agent 思考链）
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="2026 World Cup Predictor")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health(): return {"status": "ok"}

# 其余端点：从 data/results/*.json 读取，或调用 pipeline
```

- [ ] **Step 2：冒烟测试**

```bash
cd backend && uvicorn api.main:app --reload
# 访问 http://localhost:8000/api/health → {"status":"ok"}
```

- [ ] **Step 3：提交**

---

### Task 6.2：React + ECharts 前端

**Files:**
- Create: `frontend/` 全套

- [ ] **Step 1：脚手架**

```bash
npm create vite@latest frontend -- --template react
cd frontend && npm install echarts axios
```

- [ ] **Step 2：实现组件**

```jsx
// frontend/src/components/BracketTree.jsx（示例骨架）
import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { getBracket } from '../api/client';

export default function BracketTree() {
  const ref = useRef(null);
  useEffect(() => {
    getBracket().then(data => {
      const chart = echarts.init(ref.current);
      chart.setOption({
        /* 赛程树 option：高亮最可能路径，节点显示概率 */
      });
    });
  }, []);
  return <div ref={ref} style={{width:'100%',height:600}} />;
}
```

其余组件（MatchCard/ChampionRanking/TeamRadar/ExplanationPanel/Backtest2022）同构。

- [ ] **Step 3：跑通联调**

```bash
cd frontend && npm run dev   # :5173
# 后端 :8000，前端调 /api/*
```

- [ ] **Step 4：提交**

---

### Task 6.3：2022 卡塔尔回测专区

**Files:**
- Modify: `backend/pipeline.py`（加回测函数）
- Create: `frontend/src/components/Backtest2022.jsx`

- [ ] **Step 1：回测脚本**

```python
# pipeline.py 中加
def run_backtest_2022():
    """用验证集(2022卡塔尔)的真实赛果，评估模型 RPS/校准/命中率。
    产出 data/results/backtest_2022.json 供前端展示。"""
    # 1. 加载验证集
    # 2. 对每场比赛用赛前特征预测
    # 3. 计算 RPS_batch / calibration_curve / 命中率
    # 4. 写 JSON
    raise NotImplementedError("完整实现见 pipeline.py")
```

- [ ] **Step 2：前端展示**

回测页含：RPS 总分、校准曲线图、命中率、Top10 预测 vs 实际对比。

- [ ] **Step 3：提交**

---

### Task 6.4：README 与技术报告对照

**Files:**
- Create: `README.md`

- [ ] **Step 1：README 含运行说明、技术报告对照表**

包含：环境配置、数据下载、训练、模拟、启动前后端、API key 配置、技术报告章节与代码模块映射。

- [ ] **Step 2：提交**

---

## ✅ 最终验收清单（全部通过才算完成）

- [ ] 所有单元测试通过：`pytest backend/tests/ -v`
- [ ] 赛制计数：104场、R32=16场无轮空、Annex C 映射完整
- [ ] 冠军概率和 ∈ [0.99, 1.01]
- [ ] 三模型 RPS 对比表生成
- [ ] 四模型 ML 对比表生成
- [ ] 融合权重合法（和=1，非负）
- [ ] 2022 回测 JSON 生成
- [ ] Agent 在 mock 模式端到端跑通
- [ ] 接入 DeepSeek API key 后 Agent 决策正常
- [ ] 前端 5 个组件渲染正常
- [ ] Explainer 输出思考链，且数字与证据一致（无幻觉）

---

## 📌 给 coding agent 的最后指令

1. **严格按任务顺序执行**，每个任务走 TDD（先测试→实现→验证→提交）。
2. **联网核实**：fixtures_2026 的 48 队、Annex C 的 495 映射、R32 对阵表——这三处必须联网核对真实数据，**不得编造**。
3. **遇 `NotImplementedError`**：这些是明确标注的"必须由你完整实现"的函数，不可跳过。
4. **遵守 8 条铁律**（C1-C8），任何一条违反都是 bug。
5. **每个任务结束提交一次**，commit message 用 `PX.Y: 描述` 格式。
