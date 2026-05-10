# AI 应用指挥中心 — 指标口径与数据源清单

> 数据之单一真相源（SSOT）。所有新增/修改前必须先看这里，改完要回写这里。
> 最后更新：2026-05-09

## 目录

- [A. 上屏指标（7 项）](#a-上屏指标7-项)
- [B. 分析留存（只入库，不上屏）](#b-分析留存只入库不上屏)
- [C. 数据源详情（4 个 DataHub 接口 + 手动录入）](#c-数据源详情4-个-datahub-接口--手动录入)
- [D. 数据流与频次](#d-数据流与频次)
- [E. 已知坑与注意事项](#e-已知坑与注意事项)

---

## A. 上屏指标（7 项）

> 前 5 项在 KPI 单行；第 6 项折线；第 7 项平台数字面板。TOP 5 应用暂下线（`ai_app` 维度待接入）。

### KPI 行 · 5 卡

| # | 展示名 | 计算口径 | 数值类型 | 来源接口 → 表 | 采集频次 | 上屏刷新 | 动画 |
|---|---|---|---|---|---|---|---|
| 1 | **今日调用量** | 0 点至当前时刻所有平台 `requests_today` 总和 | 整数（千分位） | `llm-data` → `fact_llm_daily.requests_today` | 5 min | 60 s | 开场 2s 计数 |
| 2 | **今日 TOKENS** | 0 点至当前时刻所有平台 `tokens_today` 总和 | 自适应单位（M/B）| `llm-data` → `fact_llm_daily.tokens_today` | 5 min | 60 s | 开场 2.2s 计数 |
| 3 | **30 天活跃用户** | 近 30 天登录过 AI 应用的去重用户数 | 整数 | `ai-active-users` → `fact_active_users.distinct_users_30d` | 1 h | 60 s | 开场 1.8s 计数 |
| 4 | **已上线应用** | `dim_applications` 中 `complexity != 'planned'` 的行数 | 整数 | 本地 `v_apps_count.total_online` | 手动 | 60 s | 开场 1.4s 计数 |
| 5 | **本月成本** | 当前月 `fact_cost_monthly.cost_cny` 全平台求和 | `¥` + 千分位整数 | 手动录入 → `fact_cost_monthly` | 月度 | 60 s | 开场 2s 计数 |

**1、2 卡附带环比**：接口直接返回 `requests_change_rate` / `tokens_change_rate`，格式 `"106.09%"`。前端 `↑ +` / `↓ -` + 绝对值 2 位小数 + `vs 昨日`。绿涨红跌。

**5 卡附带环比**：aggregate.py 本地计算 `(本月 - 上月) / 上月 × 100`（上月数据来自 `fact_cost_monthly` 前一月 sum）。格式同上，后缀 `vs 上月`。

### 分析区 · 2 面板

| # | 展示名 | 计算口径 | 粒度 | 来源 | 采集频次 | 上屏刷新 |
|---|---|---|---|---|---|---|
| 6 | **近 7 天调用趋势** | `fact_llm_detail.requests` group by `t_date`，近 7 天（含昨日，不含今天）| 每日 1 点 | `llm-data-detail` → `fact_llm_detail` | 每日凌晨 | 60 s |
| 7 | **调用平台** | 每平台：昨日 `requests` / `tokens` 之和 + 当前月 `cost_cny` | 平台（百炼 / Azure / ...）| `llm-data-detail` + `fact_cost_monthly` | 明细每日、成本月度 | 60 s |

**注**：
- 第 6 项横轴用 `t_date[5:].replace('-','/')`，显示为 `05/08` 这种短格式
- 第 7 项如果当月成本还没录入，显示 `—`（灰色占位），不是 `¥0`
- 第 7 项**昨日流量 + 本月成本混排**是刻意的：昨日是动态指标，本月成本是累计指标，分开展示避免误导

---

## B. 分析留存（只入库，不上屏）

这些指标进 SQLite，供 DBeaver 分析用，但**不推到 kpis.json**。

| 指标 | 表/视图 | 用途 |
|---|---|---|
| 90 天活跃用户 | `fact_active_users.distinct_users_90d` | 长周期留存分析 |
| llm 全量明细 | `fact_llm_detail` | 按模型/团队/应用下钻的原始数据 |
| 各平台总人数 | `dim_platforms` | 未来计算"渗透率"的分母 |
| 模型目录 | `dim_models` | 维度表，和 `fact_llm_detail.model_name` 关联 |
| TOP 5 AI 应用（昨日） | `v_top5_yday` 视图 | `ai_app` 维度接入后再上屏；视图已备好 |
| 模型来源占比 | `v_source_share_yday` 视图 | 环形版本下线后保留视图，留作分析 |
| llm_daily 历史快照 | `fact_llm_daily` | 比较"接口返回的环比"vs "本地算的环比"，用于校准 |

---

## C. 数据源详情（4 个 DataHub 接口 + 手动录入）

### C.1 `llm-data`（已发布，当前 403）

- **URL**: `POST https://datahub.glp.com.cn/dh-engine/api/mysql/ai-heatmap/llm-data`
- **入参**: 无
- **出参 6 字段**:

| 字段 | 类型 | 含义 | 示例 |
|---|---|---|---|
| `requests_today` | int | 今日调用量 | 1016 |
| `tokens_today` | int | 今日 Tokens | 9,731,223 |
| `requests_yday` | int | 昨日同时刻调用量 | 493 |
| `tokens_yday` | int | 昨日同时刻 Tokens | 16,782,065 |
| `requests_change_rate` | string | 调用量环比 | "106.09%" |
| `tokens_change_rate` | string | Tokens 环比 | "-42.01%" |

- **落库**: `fact_llm_daily`（每次快照新增一行，不覆盖，主键 `snapshot_at`）

### C.2 `llm-data-detail`（待发布，4 个维度入参"待接入"）

- **URL**: `POST .../ai-heatmap/llm-data-detail`
- **入参**:
  - `start_date` / `end_date` — 必填，`yyyy-MM-dd`（**这两个已接入**）
  - `source` / `model_name` / `develop_group` / `ai_app` — 选填，**文档标注"待接入"**
- **出参 7 字段**:

| 字段 | 类型 | 含义 | 当前状态 |
|---|---|---|---|
| `t_date` | string | 调用日期 | ✓ |
| `source` | string | 模型来源平台 | ✓ |
| `develop_group` | string | 开发团队 | 标注"待接入" |
| `ai_app` | string | 应用场景 | 标注"待接入" |
| `model_name` | string | 模型 | 标注"待接入" |
| `requests` | int | 调用量 | ✓ |
| `tokens` | int | Tokens | ✓ |

- **落库**: `fact_llm_detail`，PK `(t_date, source, develop_group, ai_app, model_name)`，同 PK upsert
- **"待接入"的不确定性**: 字段在返回值中是否始终为 `all`、还是会真有拆分值，只有接口通了才能验证。**不要假设**。

### C.3 `ai-active-users`（已发布，当前 403）

- **URL**: `POST .../ai-heatmap/ai-active-users`
- **入参**: 无
- **出参 2 字段**:

| 字段 | 类型 | 含义 | 备注 |
|---|---|---|---|
| `distinct_users_30d` | int | 30 天活跃用户 | **仅含 AI-Buddy** |
| `distinct_users_90d` | int | 90 天活跃用户 | **仅含 AI-Buddy** |

- **落库**: `fact_active_users`（每次快照新增一行，主键 `snapshot_at`）
- **关键约束**: 其它 toC 应用的活跃用户暂未接入；想扩时要和邱宇/薛耀庭对"从 AI-Buddy 日志表 join 用户中心"的方案

### C.4 `ai-all-pers`（已发布，当前 403）

- **URL**: `POST .../ai-heatmap/ai-all-pers`
- **入参**: 无
- **出参 2 字段**:

| 字段 | 类型 | 含义 | 示例 |
|---|---|---|---|
| `pers_cnt` | string | 平台总人数 | "527" |
| `company_descr` | string | 平台名称 | "资产平台" / "新能源" |

- **落库**: `dim_platforms`（`company_descr` 做 PK，`INSERT OR REPLACE` 全量刷新）
- **用途**: 未来做"渗透率 = 活跃人数 / 平台人数"的分母；当前只入库，不上屏

### C.5 手动录入 · 月度成本

- **来源**: 阿里云百炼控制台月度账单、Azure Portal 月度账单
- **频次**: 每月 1 次（Azure 延迟 T+7，百炼延迟 T+1）
- **录入方式**: 手工执行 SQL

```sql
INSERT OR REPLACE INTO fact_cost_monthly (ym, platform, cost_cny, note)
VALUES
  ('2026-05', '百炼',  78320, '百炼控制台导出-2026-05'),
  ('2026-05', 'Azure', 50130, 'Azure Portal 导出-2026-05');
```

- **落库**: `fact_cost_monthly`，PK `(ym, platform)`
- **选填字段**: `tokens` / `requests`（账单里有的话）、`note`

---

## D. 数据流与频次

```
内网 launchd（待配）
  ├─ 每 5 min: scripts/collect.py --only llm-data
  ├─ 每 1 h:   scripts/collect.py --only ai-active-users
  ├─ 每日 01:10: scripts/collect.py --only llm-data-detail
  ├─ 每日 01:15: scripts/collect.py --only ai-all-pers
  └─ 每 1 min:  scripts/aggregate.py → 生成 kpis.json
                                     → （未来）put 到 OSS

Vercel 公网 HTML
  └─ 每 60 s: fetch kpis.json
```

**频次选择原因**：
- `llm-data` 5 min：接口是"今日累计到现在"的瞬时值，5 min 拉取足以支持大屏"实时感"
- `ai-active-users` 1 h：30 天窗口，小时内变化微乎其微
- `llm-data-detail` 每日：按日聚合的数据，没必要高频；选凌晨 1 点保证昨日数据完整
- `ai-all-pers` 每日：人员数据半年才变一次，但接口免费，每日刷一次无所谓
- 聚合脚本每 1 min：上屏延迟上界 = 1 min 聚合 + 60 s 前端轮询 ≈ 最多 2 min 看到新数据

---

## E. 已知坑与注意事项

1. **DataHub 当前 403**（nginx 层），脚本需用 `--mock` 参数跑通链路，接口通后再切换
2. **`llm-data-detail` 的 4 个"待接入"维度**：返回值是否会真的出现拆分数据未知；前端用 `WHERE ai_app != 'all'` 过滤，但这可能过滤掉所有行
3. **"昨日"的定义**：DataHub 的 `requests_yday` 是"昨日截止当前时刻"（小时对齐），我们本地 `fact_llm_detail.t_date = date('now','-1 day')` 是"完整昨天"。两个口径在不同卡片里，**别混用**
4. **TOP 5 应用已下线**：原因是 `ai_app` 维度未接入；视图和后端保留，接口通了验证有真实值后再加回前端
5. **AI 渗透率已下线**（2026-05-08）：`ai-active-users` 没按平台切分，分子拿不到；等用户中心 join 方案落地
6. **成本和流量混排**：平台面板里"昨日调用量 + 本月成本"是刻意的混合周期，因为成本没有日级数据（账单延迟）。面板副标已标注
7. **前端 fallback**：`kpis.json` 拉不到时用 HTML 内置 FALLBACK，但数值是硬编码的 demo 值，**生产环境要 fallback 到"—"占位而不是假数据**（待改）
