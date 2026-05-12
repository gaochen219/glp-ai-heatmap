# GLP AI 应用指挥中心 — 部署 & API 契约

> **状态（2026-05-12）**：架构已对齐，待同事后端 endpoint 上线联调。
> **部署位置**：`http://test.langfuse.glp-inc.cn/ai-command-center`（test 环境，生产另行单独部署）
> **联系人**：高晨（cgao1）

---

## 一、项目做什么

大屏可视化 GLP 集团 AI 应用使用情况，AI VP 层级演示/日常可视。

**7 项上屏指标**（完整口径见 [METRICS.md](./METRICS.md)）：
1. 今日调用量 + 日环比（分钟级实时）
2. 今日 Tokens + 日环比（分钟级实时）
3. 30 天活跃用户（仅 AI-Buddy）
4. 已上线应用数（80 个，前端硬编码）
5. 本月成本 ¥ + 月环比 **（账单接口待同事补充，暂显 "—"）**
6. 近 7 天调用趋势 **（不含当日，口径明确区别于 KPI 1/2）**
7. 调用平台 / 团队 / 模型三张表（均为近 7 天不含当日）

---

## 二、架构（已确认）

```
┌──────────────────────────────────────────────────┐
│ 浏览器（test.langfuse.glp-inc.cn/ai-command-center） │
│   ↕ fetch('/ai-heatmap/api/*')  同域                │
├──────────────────────────────────────────────────┤
│ vibeportal 后端（同一台服务器）                      │
│   ├─ appkey / appsecret 存配置文件                  │
│   ├─ HMAC-SHA1 签名                                 │
│   └─ 转发 SQL 到 DataHub / 直连 MySQL                │
├──────────────────────────────────────────────────┤
│ DataHub (datahub.glp.com.cn)                      │
│   └─ MySQL: model_usage_stats / model_bill /       │
│            smart_cube_log                          │
└──────────────────────────────────────────────────┘
```

**关键约束**：
- 生产/非生产网络隔离 → 真实数据只有生产能看到，test 环境永远是 mock
- 前端不再碰 appkey / 跨域 / 签名，全由 vibeportal 后端处理
- 暂时手动 push GitLab → 同事拉代码同步

---

## 三、API 契约（前端 ↔ 后端）

**路径前缀**：`/ai-heatmap/api/`（方便 Nginx 二级目录配置）
**方法**：`GET`，无入参（除 `/trend?days=7` 可选）
**响应**：`Content-Type: application/json`，HTTP 200 + 业务 body
**失败**：非 200 或 `{error: "..."}`，前端降级为 "—" 占位

### 1. `GET /ai-heatmap/api/live`

**用途**：首屏 KPI 1 + 2（今日调用量 / Tokens + 日环比）
**对应 SQL**：Q1（`model_usage_stats` 今日 vs 昨日 full-day）
**响应**：
```json
{
  "requests_today": 120214,
  "tokens_today":   3095817941,
  "requests_yday":  112254,
  "tokens_yday":    2480826598,
  "requests_change_rate": "+7.09%",
  "tokens_change_rate":   "+24.79%"
}
```

### 2. `GET /ai-heatmap/api/trend?days=7`

**用途**：近 7 天调用趋势折线 + 调用平台 / 团队 / 模型三张表（共用同一份数据，前端按维度聚合）
**对应 SQL**：Q2（按 `source × workspace × team × model × day` 聚合）
**时间口径**：**近 7 天不含当日**（SQL 过滤 `from_unixtime(start_time) < CURDATE()`）
  - 理由：今日数据分钟级实时，和前 6 天完整日口径不同，放一起会让折线末端误导性偏低
  - KPI 区的"今日调用量/Tokens"走 `/live`（Q1），仍是分钟级实时；两处口径区分明确
**响应**：
```json
{
  "days": 7,
  "series": [
    {
      "day": "2026-05-05", "source": "bailian",
      "workspace": "llm-01j2krtwyx37oap1",
      "team": "AI创新", "model": "qwen3.6-plus",
      "requests": 237, "tokens": 1899214
    },
    { "day": "2026-05-05", "source": "Azure", "workspace": "...",
      "team": "光储运维", "model": "gpt-4o-mini",
      "requests": 120, "tokens": 840000 }
    // ... 按 source×workspace×team×model×day 粒度，多行
  ]
}
```

**展示层映射**（前端处理，后端照实返回）：
- `source: "bailian"` → 展示为 `百炼`
- `source: "Azure"` → 保持 `Azure`
- `workspace` 字段**前端忽略**，仅聚合 key 使用（不上屏）
- `team` / `model` 原样展示

**前端聚合产物**：
- 折线图：按 `day` 求和 → requests 日序列
- 调用平台表：按 `source` 求和（近 7 天累计，倒序）
- 调用团队表：按 `team` 求和（近 7 天累计，倒序）
- 调用模型表：按 `model` 求和（近 7 天累计，倒序）

### 3. `GET /ai-heatmap/api/cost`  —  **待后端补充**

**状态（2026-05-12）**：账单数据接口同事待补，前端本月成本 KPI 暂显 "—"。
**用途**：KPI 5（本月成本 + 月环比）+ 后续可考虑给平台表加成本列
**对应 SQL**：Q3（`model_bill`，按 source × month 聚合，含当月和上月）
**响应**（约定中，后端可基于此调整）：
```json
{
  "current_month": "2026-05",
  "prev_month":    "2026-04",
  "by_source": [
    { "source": "bailian", "current_cny": 78320.50, "prev_cny": 85120.00 },
    { "source": "Azure",   "current_cny": 50130.20, "prev_cny": 55230.80 }
  ],
  "total_current_cny": 128450.70,
  "total_prev_cny":    140350.80,
  "change_rate":       "-8.48%"
}
```
接口就位后前端一次接回，不需要再改结构。

### 4. `GET /ai-heatmap/api/users`

**用途**：KPI 3（30 天活跃用户）
**对应 SQL**：Q4（`smart_cube_log`，`url='/api/user/info'`，AI-Buddy only）
**响应**：
```json
{
  "distinct_users_30d": 403,
  "distinct_users_90d": 696,
  "scope_note": "仅含 AI-Buddy"
}
```

---

## 四、硬编码在前端的部分

| 数据 | 位置 | 原因 |
|---|---|---|
| 80 应用清单（热力图格子）| HTML `GRID.sections` | 应用增减频率低，不走 DataHub |
| 7 部门清单 | HTML `DEPTS` | 基本不变 |
| 热度分级（high/mid/planned）| HTML `GRID.sections[].tiles[].c` | 手工维护 |

**应用清单维护流程**：直接改 HTML → commit → push GitLab → 同事拉代码同步。

---

## 五、前端刷新策略

| 数据 | 频率 | 理由 |
|---|---|---|
| `/live` | 60s | 数据高频变动，大屏感知需要 |
| `/trend` | 5 min | 按天聚合，无需更频繁 |
| `/cost` | 30 min | 账单日级更新（Azure T+7、百炼 T+1）|
| `/users` | 1h | 按天 distinct，半小时内基本不变 |

**失败处理**：单个 endpoint 失败 → 对应区域显示 "—"，不影响其他区域。连续 3 次失败 → header 状态切 "CACHE · OFFLINE"。

**长期挂屏**：每 24h 自动 `location.reload()`，防止内存泄漏 / token 过期。

---

## 六、仍待确认

### 后端侧（问写后端的同事）
- [ ] 4 个 endpoint 上线排期？
- [ ] `/cost` 的 MTD 过滤条件（`model_bill.day` 字段格式？是 `YYYY-MM-DD` 还是 `YYYYMMDD`？）
- [ ] 失败时后端返回什么格式？（建议：HTTP 5xx + `{error: "..."}` JSON）
- [ ] 是否加 `Cache-Control: max-age=30` 减轻 DataHub 压力？

### 生产部署（问运维）
- [ ] 生产环境的域名是什么？
- [ ] 生产的 vibeportal 已有 appkey 吗，还是要新申请？
- [ ] 生产部署流程和 test 一样（手动拉代码）还是自动化？

---

## 七、本仓库文件

```
glp-ai-heatmap/
├── glp_ai_command_center.html   # 大屏主文件（v8 + 新数据层）
├── logo.png                      # GLP 图标
├── METRICS.md                    # 指标口径权威文档
├── DEPLOYMENT.md                 # 本文件
└── .archive/                     # 旧方案归档（SQLite + cron，已弃）
    ├── scripts/
    ├── sql/
    └── kpis.json
```

---

## 八、我的信息

- **GitHub**：gaochen219
- **GitLab**：cgao1
- **有问题随时找我**
