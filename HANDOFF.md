# GLP AI 应用指挥中心 — 交接文档

> **给**：接手本项目的前端/全栈同事
> **作者**：高晨（cgao1）
> **最后更新**：2026-05-12
> **配套文档**：[DEPLOYMENT.md](./DEPLOYMENT.md) 架构 + API 契约 · [METRICS.md](./METRICS.md) 指标口径 · [CLAUDE.md](./CLAUDE.md) 项目速览

---

## 0. TL;DR（5 分钟速览）

- **是什么**：单文件 HTML 大屏，展示 GLP 集团 AI 应用的调用量、Tokens、活跃用户、成本、热力图。给 AI VP 层级演示/日常可视。
- **当前状态**：前端结构+视觉完成，等后端 4 个 API endpoint 上线联调。所有本地开发走 `?mock=1`，真实数据只有**生产环境内网**能拉到。
- **唯一主文件**：`glp_ai_command_center.html`（单文件 HTML+CSS+JS，2200 行，不依赖构建）。其他都是配套文档和图标。
- **打开即用**：浏览器打开 `glp_ai_command_center.html?mock=1` 就能看到完整效果。
- **已部署**：`http://test.langfuse.glp-inc.cn/ai-command-center`（test 环境，手动同步代码）。
- **三个硬约束**：① 生产/非生产网络隔离 → 只有生产能拿真实数据 ② appkey 放后端配置，**永远不能进 HTML** ③ 大屏是挂着看的，**不做交互依赖**（tab 切换、弹窗、搜索框都没必要）。

---

## 1. 项目背景

### 1.1 用途

给 AI VP 和相关领导的大屏/录屏：告诉他们"集团 AI 应用现在用得怎么样"。具体覆盖 7 项上屏指标：

| # | 指标 | 口径 |
|---|---|---|
| 1 | 今日调用量 + 日环比 | 分钟级实时 |
| 2 | 今日 Tokens + 日环比 | 分钟级实时 |
| 3 | 30 天活跃用户 | 仅 AI-Buddy |
| 4 | 已上线应用数 | 80 个，前端硬编码 |
| 5 | 本月成本 ¥ + 月环比 | **接口待后端补**，当前显 "—" |
| 6 | 近 7 天调用趋势 | **不含当日**（避免今天分钟级数据和前 6 天完整日混口径）|
| 7 | 调用平台 / 团队 / 模型 三张表 | 均为近 7 天不含当日 |

完整口径见 [METRICS.md](./METRICS.md)。

### 1.2 谁在用

- **主要受众**：AI VP、数字化部门领导、集团数字化战略会议
- **使用场景**：演示、录屏、日常挂在办公室显示器
- **不是**：交互式 BI 工具（所以没 tab、没筛选、没下钻，全是只读展示）

---

## 2. 架构

### 2.1 整体架构（一张图看懂）

```
┌────────────────────────────────────────────────────┐
│ 浏览器（test.langfuse.glp-inc.cn/ai-command-center）│
│  │                                                 │
│  └─ fetch('/ai-heatmap/api/live')      同域         │
│     fetch('/ai-heatmap/api/trend?days=7')          │
│     fetch('/ai-heatmap/api/cost')                  │
│     fetch('/ai-heatmap/api/users')                 │
└────────────────┬───────────────────────────────────┘
                 │
┌────────────────▼───────────────────────────────────┐
│ vibeportal 后端（同一台服务器）                      │
│  ├─ appkey / appsecret 存配置文件                   │
│  ├─ HMAC-SHA1 签名（DataHub 要求）                  │
│  └─ 4 条 SQL 到 DataHub MySQL                       │
└────────────────┬───────────────────────────────────┘
                 │
┌────────────────▼───────────────────────────────────┐
│ DataHub (datahub.glp.com.cn)                       │
│  └─ MySQL: model_usage_stats / model_bill /         │
│            smart_cube_log                           │
└────────────────────────────────────────────────────┘
```

### 2.2 为什么是这个架构

**我们尝试过 / 弃用的方案**（`.archive/` 里保留了代码，不要复活）：

1. ~~前端直连 DataHub REST~~ → 浏览器会看到 appkey，CORS 跨域麻烦，弃用
2. ~~本机 Mac cron + SQLite + OSS~~ → 数据源在生产内网，本地 Mac 根本调不通 DataHub，弃用

**当前方案的优点**：
- appkey / 签名全在后端，前端零密钥
- 同域请求，无 CORS
- 后端可自由切换数据源（从 SQL 换到 REST、换数据库都不用动前端）

### 2.3 硬约束（接手必须知道）

1. **生产/非生产网络隔离**：`test.langfuse.glp-inc.cn` 在非生产环境，**访问不了生产的 DataHub**。所以 test 环境永远是 mock 数据，真实数据只有生产能看。
2. **前端永远不碰 appkey**：任何"把 appkey 放前端"的想法都直接否掉。就算内网也不行（浏览器 F12 就能看）。
3. **本地 Mac 调不通 DataHub**：公司内网隔离。本地只能 `?mock=1`。

---

## 3. 文件结构

```
glp-ai-heatmap/                          # GitLab: cgao1/glp-ai-heatmap  GitHub: gaochen219/glp-ai-heatmap
├── glp_ai_command_center.html           # ★ 主文件：单文件 HTML+CSS+JS
├── logo.png                             # GLP 图标，HTML 里用 <svg> 替代文字 logo，保留作备
│
├── HANDOFF.md                           # ★ 本文件
├── DEPLOYMENT.md                        # 部署 + API 契约（单一真相源）
├── METRICS.md                           # 指标口径权威文档
├── CLAUDE.md                            # 项目速览
│
├── *.docx                               # DataHub 接口文档 / SQL，gitignore 排除
│   ├── AI Heatmap Deployment 5.12更新.docx   ← 最重要，SQL + Python 签名示例
│   ├── 大模型数据明细（含参） 5.12更新.docx  ← llm-data-detail REST 接口
│   ├── 大模型数据统计.docx
│   ├── 平台清单.docx
│   └── AI 活跃用户数.docx
├── *.xlsx                               # KPI 源数据，gitignore 排除
│
├── .archive/                            # 旧方案归档，仅本地备查，gitignore 排除
│   ├── scripts/                         # 旧方案的 collect.py / aggregate.py / tick.sh
│   ├── sql/                             # 旧方案的 SQLite schema
│   ├── data/                            # 旧方案的 heatmap.db
│   ├── kpis.json                        # 旧方案产物
│   └── com.cgao1.ai-heatmap.tick.plist  # 旧方案 launchd 定时
│
└── logs/                                # 本地调试日志，gitignore 排除
```

**不要动 `.archive/`**，那是历史归档。当前方案不用 SQLite、不用 cron、不用 OSS。

---

## 4. 主文件内部结构（`glp_ai_command_center.html`）

文件分 3 段：

### 4.1 `<style>` — CSS（约 1000 行）

按自上而下读：
- **设计变量**（`:root`）：颜色、字体、圆角。配色方案见 §6.1
- **背景层**（`body::before/after`、`#particles`、`#fx`）：粒子 / 扫描线 / 网格
- **HEADER**：左侧品牌、右侧 meta 卡片（LIVE 状态 / Source / Clock）
- **KPI ROW**（`#kpi-row`）：5 张卡，前 2 张主色调（primary），后 3 张次色调（secondary）
- **HEATMAP**（`#heatmap-section`）：热力图 table + 图例
- **ANALYSIS**（`#analysis`）：2 行 2 列
  - row1: 近 7 天趋势折线 + 调用平台面板
  - row2: 调用团队表 + 调用模型表（新增，通用 `.brk-table` 样式）
- **FOOTER**

### 4.2 `<body>` — HTML 结构（约 250 行）

HTML 静态骨架。动态内容（热力图 tile / KPI 数字 / 表格行）由 JS 生成。

### 4.3 `<script>` — JavaScript（约 1000 行）

按顺序分 4 段：

```
L1323  背景粒子（matrixRain 的白色上浮版本，见 §6.2）
L1358  DASHBOARD LOGIC
   ├─ GRID / DEPTS 常量（80 应用 + 7 部门）
   ├─ 启动时生成热力图 DOM
   ├─ fmtInt / fmtTokens / fmtMoney / parseRate 格式化
   ├─ animateDecode (KPI 数字解码动画)
   ├─ renderSpark / renderTrend / renderPlatforms（原子 SVG 渲染器）

L1804  DATA LAYER
   ├─ API_BASE = '/ai-heatmap/api'
   ├─ MOCK_MODE = 看 URL ?mock=1
   ├─ APPS_HARDCODED （硬编码的应用数）
   ├─ MOCK 对象（完整 4 个 endpoint 的假数据）
   ├─ fetchEndpoint(path) 封装（带 mock 分支）
   ├─ failCount + markResult（3 次失败降级）

L1901  RENDER
   ├─ renderLive / renderCost / renderUsers / renderAppsStatic
   ├─ SOURCE_LABEL (bailian → 百炼)
   ├─ aggregateTrend (/trend 响应拆成 byDay/byPlat/byTeam/byModel)
   ├─ renderTrendData / renderBreakdown (团队/模型表通用)
   ├─ renderPlatformsMerged (合并 trend + cost 数据)

L2118  POLLERS
   ├─ pollLive / pollTrend / pollCost / pollUsers
   └─ 初始化 + 独立 setInterval（60s / 5min / 30min / 1h）
```

### 4.4 为什么用单文件 HTML（不用 React / Vue）

- **需求简单**：一个只读大屏，数据每分钟刷新。没状态、没路由、没组件复用。
- **部署简单**：拖个 HTML 到任何静态服务都能跑，也能直接 `file://` 在本地打开。vibeportal 后端也不用配前端构建。
- **性能足够**：单页，首屏 <1s，无框架开销。
- **改起来也不难**：2200 行里 CSS 占一半，JS 主要是渲染函数，没有你需要背的 React 心智模型。

如果后续要做多页（比如加个运营管理后台），再考虑上框架。现在保持单文件。

---

## 5. 数据流 & API 契约

### 5.1 4 个 endpoint 一览

| # | Endpoint | 用途 | 刷新 | 状态 |
|---|---|---|---|---|
| 1 | `GET /ai-heatmap/api/live` | KPI 1+2（今日调用量/Tokens+日环比）| 60s | 后端开发中 |
| 2 | `GET /ai-heatmap/api/trend?days=7` | 折线图 + 3 张下钻表 | 5 min | 后端开发中 |
| 3 | `GET /ai-heatmap/api/cost` | KPI 5（本月成本）| 30 min | **账单接口待同事补充** |
| 4 | `GET /ai-heatmap/api/users` | KPI 3（30 天活跃）| 1h | 后端开发中 |

完整响应 schema 见 [DEPLOYMENT.md §三](./DEPLOYMENT.md)。这里只给快速参考：

#### 5.1.1 `/live` 响应
```json
{
  "requests_today": 120214, "tokens_today": 3095817941,
  "requests_yday":  112254, "tokens_yday":  2480826598,
  "requests_change_rate": "+7.09%", "tokens_change_rate": "+24.79%"
}
```

#### 5.1.2 `/trend` 响应（数据量最大的一个）
```json
{
  "days": 7,
  "series": [
    { "day": "2026-05-05", "source": "bailian",
      "workspace": "llm-01j2krtwyx37oap1",
      "team": "AI创新", "model": "qwen3.6-plus",
      "requests": 237, "tokens": 1899214 }
    // ... 多行，按 source×workspace×team×model×day 粒度
  ]
}
```
**重要**：
- `source` 后端传原始英文（`bailian` / `Azure`），前端 `displaySource()` 映射成中文展示
- `workspace` 字段前端忽略（不展示，也不参与聚合 key）
- 时间口径：**近 7 天不含当日**（后端 SQL 已过滤 `< CURDATE()`）

#### 5.1.3 `/cost` 响应（待后端补接口）
```json
{
  "current_month": "2026-05", "prev_month": "2026-04",
  "by_source": [
    { "source": "bailian", "current_cny": 78320.50, "prev_cny": 85120.00 },
    { "source": "Azure",   "current_cny": 50130.20, "prev_cny": 55230.80 }
  ],
  "total_current_cny": 128450.70, "total_prev_cny": 140350.80,
  "change_rate": "-8.48%"
}
```

#### 5.1.4 `/users` 响应
```json
{
  "distinct_users_30d": 403, "distinct_users_90d": 696,
  "scope_note": "仅含 AI-Buddy"
}
```

### 5.2 后端 4 条 SQL

见 `AI Heatmap Deployment 5.12更新.docx`（根目录），里面有：
- Q1（今日 vs 昨日 full-day）→ `/live`
- Q2（按 `source × workspace × team × model × day` 聚合，**过滤 < CURDATE()**）→ `/trend`
- Q3（`model_bill`，按 source × month）→ `/cost`
- Q4（`smart_cube_log`，AI-Buddy only）→ `/users`

docx 里还有 **Python HMAC-SHA1 签名完整示例**，后端对接 DataHub 照抄即可（headers `a/t/s` 三字段）。

### 5.3 前端如何消费数据

**关键设计原则**：**4 个 endpoint 独立 fetch、独立刷新、独立失败降级**。

```javascript
// L2118 附近
async function pollLive(animate = false) {
  try {
    const d = await fetchEndpoint('/live');
    renderLive(d, animate);
    markResult('live', true);
  } catch (e) {
    console.warn('[live]', e);
    renderLive(null, false);   // 渲染 "—" 占位
    markResult('live', false); // 计入失败次数
  }
}
```

- 某个 endpoint 挂了，只有对应区域显示 "—"，其他区域不受影响
- 连续 3 次失败 → header 状态 pill 从 `DATAHUB · LIVE` 切到 `CACHE · OFFLINE`
- 24h 自动 `location.reload()` — 大屏长期挂着，防内存泄漏 / token 过期

---

## 6. 视觉设计

### 6.1 配色（matrix 简约科技感）

```
─ 主绿 neon ────────── #39FFAD   关键数据（大数字、告警、LIVE）
─ 次绿 leaf ────────── #C7E8D6   主文字
─ 灰绿 moss ────────── #6E9A85   说明文字、边框
─ 深灰 moss-dim ────── #446B58   次要说明
─ 背景 bg-0 ────────── #020806   页面底
─ 卡片 bg-card ─────── rgba(6,16,12,0.82)  毛玻璃

─ 蓝 cyan ──────────── #6BD3FF   Azure 平台标识
─ 琥珀 amber ────────── #FFB547   警告（暂未使用）
─ 玫 rose ──────────── #FF6F8C   下行箭头
```

### 6.2 背景动画

- **白色浮点**：1~2.2px 白色小圆点向上飘，22~40s 穿过屏幕。非常克制，不抢视线
- **扫描光带**：8s 一次全屏淡绿横扫
- **点阵网格**：34px 间隔小点阵

所有动画都是 CSS `@keyframes`，没用任何动画库。

### 6.3 字体

- 主文字：Inter / PingFang SC
- 数字和代号：JetBrains Mono（等宽，数字严格对齐）
- 标题：Sora

通过 Google Fonts CDN。**无外网环境下会 fallback**（已保留系统字体兜底，不会崩）。

### 6.4 不要做的

- ❌ 加 tab 切换（大屏非交互）
- ❌ 加搜索框 / 筛选器（大屏非交互）
- ❌ 加更多随机闪烁 / 粒子 / 发光（已经在"视觉舒适度"的边界，再加就刺眼）
- ❌ 改成渐变彩色（绿色科技感是产品调性，别变成"数据可视化模板"）

---

## 7. 本地开发

### 7.1 开发环境要求

**什么都不需要**。只要有浏览器。

可选：
- VS Code + Live Server 扩展（可热更新）
- Python 3 `python3 -m http.server 8080`（HTTP 访问，避免 `file://` 的 CORS 问题）

### 7.2 打开项目

```bash
# 方式 1：直接打开（file://），用 mock 数据
open "glp_ai_command_center.html?mock=1"

# 方式 2：起 HTTP 服务
python3 -m http.server 8080
# 然后浏览器访问 http://localhost:8080/glp_ai_command_center.html?mock=1
```

### 7.3 Mock / Real / 本地真实数据 三种模式

**方式 A — Mock（无网络要求，最快）**
```bash
open "glp_ai_command_center.html?mock=1"
```
走内置 `MOCK` 常量。本地开发视觉调试用。

**方式 B — 生产/test 环境（真实数据，由 vibeportal 后端提供）**
```
http://test.langfuse.glp-inc.cn/ai-command-center
```
不加 URL 参数，前端 fetch 同域 `/ai-heatmap/api/*`。只有部署到内网服务器才能跑。

**方式 C — 本地直连 DataHub（真实数据，Mac 上也能看）** ★ 推荐
```bash
pip install requests          # 仅首次
export DATAHUB_APP_KEY=...
export DATAHUB_APP_SECRET=...
python3 local_proxy.py
```
然后访问 `http://127.0.0.1:8765/`。

`local_proxy.py` 同时做两件事：
1. serve 当前目录的 HTML + 静态资源
2. 把 `/ai-heatmap/api/*` 代理到 DataHub（带 HMAC-SHA1 签名）

**等同于 vibeportal 后端的 1:1 行为**，前端代码零改动。接手后未来后端上线，`local_proxy.py` 也可以继续用作本地开发代理。

AppKey / AppSecret 只在 Python 进程里，**不进浏览器**。脚本默认只监听 `127.0.0.1`，不接收外部连接。不要部署到公网。

### 7.4 修改 80 应用清单

应用清单在 `GRID` 常量里（L1383 附近）。结构：

```javascript
{
  sections: [
    { id: 'general', label: '整体 · AI Buddy 2.0', subs: [
      { label: '集团通用', tiles: [
        { name: 'AI 智能助理', dept: 0, c: 'high', hot: true },
        //                    └ 部门 idx ── 热度 ─ 脉冲动画
      ]},
    ]},
    // ...
  ]
}
```

- `dept: 0-6` 对应 `DEPTS` 数组 `['Asset','IDC','新能源','基金/其他','财务','HR','Legal/IA/PR']`
- `c: 'high' | 'mid' | 'planned'` → 视觉强度（绿实 / 绿虚 / 灰虚）
- `hot: true` → 脉冲动画（仅用于重点应用，目前只有 1 个）

改完保存 → 刷新浏览器即可。应用数自动重新统计到 KPI 4。

### 7.5 修改样式

CSS 在文件头 `<style>` 段。**不支持**：
- Sass / Less（直接 CSS）
- CSS Modules（全局样式）
- 构建步骤

所以写 CSS 时注意命名，全项目共享同一个全局空间。

### 7.6 调试技巧

- **DevTools Console**：失败的 endpoint 会 `console.warn('[live]', e)` 输出，正常请求不打 log
- **Network 面板**：过滤 `ai-heatmap` 能看到所有数据请求
- **强制失败**：在 URL 里带 `?mock=1` 然后改 `fetchEndpoint` 里的 mock 分支返回 `throw new Error('test')` 测降级行为
- **大屏尺寸模拟**：DevTools 开 Responsive，设 2560×1440 或 3840×2160 看挂大屏效果

---

## 8. 部署

### 8.1 当前部署（test 环境）

- **URL**：`http://test.langfuse.glp-inc.cn/ai-command-center`
- **托管方式**：vibeportal 应用（带后端），同一服务器提供前端静态文件 + 4 个 API endpoint
- **更新流程**：`git push` → 同事在服务器手动 `git pull`（后续可能做自动化）

### 8.2 生产部署（待做）

- 生产/非生产网络隔离 → 必须**单独部署到生产环境**
- 生产域名：**待定**
- 生产 appkey：**待申请**（找 DataHub 团队）

### 8.3 部署清单（给后端 / 运维同事）

1. 把仓库代码拷到 vibeportal 项目目录
2. 把 `glp_ai_command_center.html` + `logo.png` 作为静态资源托管
3. 后端实现 4 个 endpoint：
   - `GET /ai-heatmap/api/live`
   - `GET /ai-heatmap/api/trend?days=7`
   - `GET /ai-heatmap/api/cost`
   - `GET /ai-heatmap/api/users`
4. DataHub 签名参数放配置文件：`APP_KEY / APP_SECRET`
5. 失败时返回 HTTP 5xx + `{error: "..."}` JSON
6. 建议加 `Cache-Control: max-age=30` 减轻 DataHub 压力
7. Nginx 配置：域名二级目录 `/ai-heatmap/*` 路由到 vibeportal

---

## 9. 常见任务 how-to

### 9.1 新增一个 KPI 卡

1. `<div id="kpi-row">` 里加一个 `<div class="kpi secondary">` 结构（复制现有的改）
2. 对应的 ID（`l2-xxx`）要新增
3. 如果需要后端数据：
   - 在 `MOCK` 里加 mock 响应
   - 写一个 `renderXxx()` 函数
   - 写一个 `pollXxx()` poller
   - `window.addEventListener('load')` 里加上初始化 + `setInterval`
4. 去 `METRICS.md` 登记口径

### 9.2 新增一个分析区面板

保持"总分"结构：KPI 卡 = 总，分析区 = 分。新增指标都放分析区。

- 分析区现在是 2 行 2 列 grid（`#analysis { grid-template-columns: 1.4fr 1fr }`）
- 加一行就是再开一个 `<div class="panel">`，grid-auto-rows 自动延展
- 用现有的 `.panel` + `.panel-head` + `.panel-body` 结构
- 表格数据可复用 `.brk-table` 通用样式（团队/模型表用的那套）

### 9.3 改某个指标的刷新频率

直接改 `window.addEventListener('load')` 里的 `setInterval` 毫秒数。

```javascript
setInterval(() => pollLive(false),   60 * 1000);   // ← 改这里
setInterval(() => pollTrend(false),  5 * 60 * 1000);
setInterval(() => pollCost(false),  30 * 60 * 1000);
setInterval(() => pollUsers(false), 60 * 60 * 1000);
```

### 9.4 接入真实后端（关键一步）

等后端 endpoint 就绪后：

1. **先对字段**：让后端随便跑一个 endpoint，把 JSON 丢给你
2. 和 `MOCK.live` / `MOCK.trend` / `MOCK.cost` / `MOCK.users` 对 schema
3. 如果字段名对不上，**优先改后端**（契约已公开）
4. 如果后端返回的 `source` 是其他拼法（`BaiLian` / `qianwen` 等），改 `SOURCE_LABEL` 常量加映射
5. 如果后端 `days` 粒度变了（比如给 30 天），前端 `aggregateTrend` 不用动（它只按 `day` 字段聚合）
6. 测试降级：断网、手动 throw 看 "—" 占位

### 9.5 Push 代码到 GitLab + GitHub

仓库配了双 remote（`origin` = GitHub + GitLab 双推）：

```bash
git push origin main
# 会同时推到 github.com:gaochen219/glp-ai-heatmap 和
#           gitlab.g2link-inc.cn:cgao1/glp-ai-heatmap
```

公司内部协作用 GitLab，外部备份用 GitHub。

---

## 10. 避坑清单

### 10.1 时间相关

- **SQLite / MySQL `date('now')` 默认 UTC**：SQL 里必须显式用 `CURDATE()`（MySQL）或 `date('now','localtime')`（SQLite）。旧方案踩过这个坑，`.archive/` 里的 SQL 已修。
- **"近 7 天"口径**：SQL 明确过滤 `< CURDATE()`，即**不含今天**。否则今天的分钟级数据会让折线末端看起来异常低。
- **docx 里 Q2 已经同步**：`where ... and from_unixtime(start_time) < CURDATE()`。后端照抄即可。

### 10.2 安全相关

- **appkey 永远不进前端**：即便内网，也不要硬编码到 HTML。`.gitignore` 已排除 `.env` / `*.docx`（docx 里有真实 AppKey 示例）
- **不要把 docx / xlsx commit 进 git**：gitignore 已配，提醒你不要手误 `git add -A` 然后连 docx 一起上传

### 10.3 UI 相关

- **div 里的数字会导致 `animateDecode` 残留**：每次渲染都会重置 text，不用担心，但别手动改 `innerHTML` 插入 HTML 到 KPI 数字 div（会破坏动画循环）
- **平台 source 中英文映射**：`aggregateTrend` 内部已统一成中文 key。后端改 source 命名（比如从 `bailian` 改 `Bailian`）只需要加一行 `SOURCE_LABEL['Bailian'] = '百炼'`
- **热力图 tile 数量超过 52 个**：`application` section 设计上限 52。如果某个子类超了会换行，但超过面板高度会压缩。真要塞更多 → 考虑改 `.tile-stack` 为多列

### 10.4 数据相关

- **`ai_app` 字段当前是 null**：docx 明确说"跟云平台治理规划有关，当前按团队区分，未按应用区分"。所以 TOP 5 AI 应用面板无法做（历史 commit 曾经有过，后来下线）。等云平台改了再接。
- **本月成本接口没好**：同事正在补 `model_bill` SQL。前端接口返回 `null` 就显 "—"，已处理好。
- **`workspace` 字段忽略**：前端只用 `source / team / model / day` 聚合。`workspace`（云资源 ID）对大屏无意义。

---

## 11. 仍未完成 / 待办

### 11.1 等后端（阻塞联调）

- [ ] 4 个 API endpoint 上线（`/live` `/trend` `/users` 优先，`/cost` 可后补）
- [ ] 后端的失败响应格式确认（建议 HTTP 5xx + `{error: "..."}` JSON）
- [ ] 后端加 `Cache-Control` 头（可选，减压 DataHub）

### 11.2 等真实数据（验证）

- [ ] 同事跑一次真实 `/trend` JSON 给你做 fixture，替换 MOCK 验证前端 parse
- [ ] 验证 `source` 返回是否真是 `bailian` / `Azure`（小写 / 大写）
- [ ] 验证 `team` / `model` 有多少真实取值（影响团队/模型表的视觉密度）

### 11.3 等确认（设计决策）

- [ ] 生产域名 + 生产 appkey 申请
- [ ] 生产部署流程：继续手动拉代码，还是搞 CI/CD
- [ ] 80 应用清单的维护流程：谁改 HTML、多久更新一次

### 11.4 可选优化

- [ ] FALLBACK 里目前还有 mock 数据，生产环境严格应该全 "—"（看同事意见）
- [ ] 24h reload 可以换成更精细的内存监控 + 按需 reload
- [ ] 加埋点统计：大屏实际被打开的频率，指导后续优化方向

---

## 12. 联系方式

- **作者**：高晨（cgao1）
- **GitHub**：gaochen219
- **GitLab**：cgao1
- **钉钉**：（补）

**有任何卡住的地方直接找我**，尤其：
- 后端 endpoint 字段对不上
- DataHub 签名跑不通（docx Python 示例应该直接 work）
- 生产部署流程卡在哪步
- UI/视觉上想改但不确定是否合设计调性的

---

## 13. Git 历史关键 commit（按时间倒序）

- **703d12e** 分析区扩展：团队/模型表格 + 口径标注（2026-05-12）
- **a8dd9ec** 切换新架构：同域后端 + 4 个 API endpoint + v8 视觉（2026-05-12）
- **c614060** 重构大屏：7 指标 + 本地 SQLite 留存 + 准备服务器部署（旧方案，已归档）
- **05c6146** 前端接入真实数据 schema + 新增昨日同期对比卡片
- **d8bf77a** 初始化 GLP AI 应用指挥中心大屏

看 `git log --stat` 能更清楚某次改了哪些文件。
