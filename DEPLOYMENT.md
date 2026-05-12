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
**响应包装**：DataHub 原生响应为 `{status, message, pagination, data:[...]}`。后端 vibeportal **可以透传此结构**，前端 `unwrapResponse()` 会统一解包；也可以在后端自行解包成"裸响应"，前端兼容两种。
**HTTP**：成功 200；失败建议 HTTP 5xx + `{error: "..."}` JSON，前端降级为 "—" 占位
**DataHub 业务 code**：2000 = 成功，其他见 docx §2（4005/4014 签名错、4006 缺参等）。前端仅检查 `status !== 2000` 作失败处理。

### 1. `GET /ai-heatmap/api/live`

**用途**：首屏 KPI 1 + 2（今日调用量 / Tokens + 日环比）
**对应 SQL**：Q1（`model_usage_stats` 今日 vs 昨日 full-day）
**真实响应**（已通过 `verify_datahub.py` 验证）：
```json
{
  "status": 2000, "message": "", "pagination": null,
  "data": [{
    "requests_today": 4313,
    "tokens_today":   158879144,
    "requests_yday":  3066,
    "tokens_yday":    99710848,
    "requests_change_rate": "+40.67%",
    "tokens_change_rate":   "+59.34%"
  }]
}
```
注意：`data` 是 **数组、长度为 1**，前端取 `data[0]`。

### 2. `GET /ai-heatmap/api/trend?days=7`

**用途**：近 7 天调用趋势折线 + 调用平台 / 团队 / 模型三张表（共用同一份数据，前端按维度聚合）
**对应 SQL**：Q2（按 `source × workspace × team × model × t_date` 聚合）
**时间口径**：**近 7 天不含当日**（SQL 过滤 `from_unixtime(start_time) < CURDATE()`）
  - 理由：今日数据分钟级实时，和前 6 天完整日口径不同，放一起会让折线末端误导性偏低
  - KPI 区的"今日调用量/Tokens"走 `/live`（Q1），仍是分钟级实时；两处口径区分明确
**真实响应**（fixture 摘录）：
```json
{
  "status": 2000, "message": "", "pagination": null,
  "data": [
    { "source": "bailian", "workspace": "llm-01j2krtwyx37oap1",
      "team": "AI创新", "model": "qwen3.6-plus",
      "t_date": "2026-05-09", "requests": 237, "tokens": 1899214 },
    { "source": "azure", "workspace": null,
      "team": null, "model": null,
      "t_date": "2026-05-09", "requests": 974, "tokens": 49350524 }
    // ... 多行，按 source × workspace × team × model × t_date 粒度
  ]
}
```

**展示层映射**（前端 `SOURCE_LABEL` 处理，后端照实返回原值）：
- `source: "bailian"` → 展示为 `百炼`
- `source: "azure"` / `"Azure"` → 展示为 `Azure`
- `team` / `model` 为 `null` / `""` 时 → 前端聚合归并为 `未归类`（真实数据大量行 team/model 为 null，云平台治理规划中）
- `workspace` 字段**前端忽略**，不上屏

**字段别名**：真实返回使用 `t_date`，前端 `unwrapResponse('/trend', ...)` 会把 `t_date` 同时赋给 `day`，下游聚合代码用哪个都行。

**前端聚合产物**（全部基于近 7 天累计，倒序排列，不截断）：
- 折线图：按 `t_date` 求和 → requests 日序列
- 调用平台表：按 `source` 求和
- 调用团队表：按 `team` 求和
- 调用模型表：按 `model` 求和

### 3. `GET /ai-heatmap/api/cost`  —  **DataHub 接口未开放**

**状态（2026-05-12）**：DataHub 尚未提供账单对应的 REST endpoint（docx 只给了 SQL，REST 路径待发布）。前端本月成本 KPI 当前显 "—"。
**用途**：KPI 5（本月成本 + 月环比）+ 后续可考虑给平台表加成本列
**对应 SQL**：Q3（`model_bill`，按 source × month 聚合，含当月和上月）
**建议响应**（等 DataHub 发布 REST 接口或 vibeportal 直连 MySQL 后对齐包装格式）：
```json
{
  "status": 2000, "message": "", "pagination": null,
  "data": [
    { "source": "bailian", "current_cny": 78320.50, "prev_cny": 85120.00 },
    { "source": "azure",   "current_cny": 50130.20, "prev_cny": 55230.80 }
  ]
}
```
或保留汇总形式：
```json
{
  "status": 2000,
  "data": [{
    "current_month": "2026-05", "prev_month": "2026-04",
    "by_source": [ ... ],
    "total_current_cny": 128450.70, "total_prev_cny": 140350.80,
    "change_rate": "-8.48%"
  }]
}
```
接口就位后前端加个解包分支即可，视觉结构不变。

### 4. `GET /ai-heatmap/api/users`

**用途**：KPI 3（30 天活跃用户）
**对应 SQL**：Q4（`smart_cube_log`，`url='/api/user/info'`，AI-Buddy only）
**真实响应**（已验证）：
```json
{
  "status": 2000, "message": "", "pagination": null,
  "data": [{
    "distinct_users_30d": 348,
    "distinct_users_90d": 707
  }]
}
```
注意：`data` 是数组、长度为 1，前端取 `data[0]`。
"仅含 AI-Buddy" 口径由前端写死标注（`scope_note` 可选字段，后端不需要返回）。

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

## 六、已验证事项（2026-05-12）

`verify_datahub.py` 脚本从 Mac 实跑，3/3 通过：

| endpoint | HTTP | biz code | 备注 |
|---|---|---|---|
| `/dh-engine/api/mysql/ai-heatmap/llm-data`          | 200 | 2000 | 今日 4313 次请求 / 1.58 亿 tokens |
| `/dh-engine/api/mysql/ai-heatmap/ai-active-users`   | 200 | 2000 | 30 天 348 活跃 / 90 天 707 |
| `/dh-engine/api/mysql/ai-heatmap/llm-data-detail`   | 200 | 2000 | 7 天 28 行；team/model 大量 null |

**已确认**：
- HMAC-SHA1 签名协议（docx Python 示例）正确
- 响应统一 `{status, message, pagination, data:[...]}` 包装
- `source` 值为小写 `bailian` / `azure`
- 近 7 天真实 team 维度只有 `AI创新` / `系统研发` 2 个有值（其余 null）
- 真实 model 维度 6 个：`qwen3.6-plus` / `qwen3-max` / `qwen-plus` / `qwen3.5-plus-2026-02-15` / `deepseek-v4-pro` / `deepseek-v3`（其余 null）

---

## 七、仍待确认

### 后端侧（问写 vibeportal 后端的同事）
- [ ] 4 个 `/ai-heatmap/api/*` endpoint 上线排期？
- [ ] 后端是否透传 DataHub 原生包装，还是自行解包成裸响应？（前端两种都兼容）
- [ ] 失败时返回什么格式？（建议：HTTP 5xx + `{error: "..."}` JSON）
- [ ] 是否加 `Cache-Control: max-age=30` 减轻 DataHub 压力？

### DataHub 侧
- [ ] 账单成本接口（Q3 对应的 REST path，docx 里只有 SQL 没有路径）
- [ ] `team` / `model` 维度什么时候能覆盖更全（当前大部分 null）

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
