# GLP AI 应用指挥中心

单文件 HTML 大屏，后端由 vibeportal 提供 4 个 `/ai-heatmap/api/*` endpoint（同域）。用于 GLP Digital Technology AI VP 演示/日常可视。

> **架构/API 契约权威**：[DEPLOYMENT.md](./DEPLOYMENT.md)
> **指标口径权威**：[METRICS.md](./METRICS.md)

## 架构

```
浏览器 ─ fetch('/ai-heatmap/api/*') ─► vibeportal 后端 ─► DataHub MySQL
                                            │               (同域，无 CORS)
                                            └─ appkey/签名在后端配置文件
```

**硬约束**：生产/非生产网络隔离 → 真实数据只有生产环境能拉到。test 环境走 mock。

## 4 个 API endpoint

| 路径 | 对应 SQL | 刷新频率 |
|---|---|---|
| `GET /ai-heatmap/api/live` | Q1（`model_usage_stats` 今日 vs 昨日）| 60s |
| `GET /ai-heatmap/api/trend?days=7` | Q2（按 day × source 聚合）| 5 min |
| `GET /ai-heatmap/api/cost` | Q3（`model_bill` 当月/上月按 source）| 30 min |
| `GET /ai-heatmap/api/users` | Q4（`smart_cube_log`，AI-Buddy only）| 1h |

SQL 原文见 DEPLOYMENT.md §三，或 `AI Heatmap Deployment 5.12更新.docx`。

## 目录

```
├── glp_ai_command_center.html   # 主文件（单文件 HTML+JS+SVG）
├── logo.png
├── DEPLOYMENT.md                # 架构 + API 契约 + 待办
├── METRICS.md                   # 指标口径
├── CLAUDE.md                    # 本文件
├── .archive/                    # 旧方案归档（SQLite + cron），已弃
└── *.docx / *.xlsx              # 接口文档 / KPI 源数据，gitignore 排除
```

## 本地调试

```bash
open glp_ai_command_center.html?mock=1   # 强制走内置 mock 数据
open glp_ai_command_center.html           # 走 /ai-heatmap/api/*（生产/test 部署用）
```

前端通过 URL 参数 `?mock=1` 切换数据源，`MOCK_MODE` 常量位于 HTML 脚本开头的 DATA LAYER 段。

## 7 项上屏指标

KPI 区（5 卡单行）: 今日调用量 · 今日 Tokens · 30 天活跃用户 · 已上线应用 · 本月成本
  前 2 卡 neon 绿大号（带环比），后 3 卡 leaf 绿中号
热力图：7 部门 × 80 应用（general 8 / application 52 / foundation 16 / pipeline 4），主屏铺满
分析区（2 栏）: 近 7 天趋势折线 · 调用平台数字面板（昨日调用量 / Tokens / 本月成本）

TOP 5 应用面板已下线（等 `ai_app` 维度真实接入后加回）。

→ 完整口径见 [METRICS.md](./METRICS.md)

## 视觉（v8 — matrix 简约科技感）

- 绿色三层: `#39FFAD` neon / `#C7E8D6` leaf / `#6E9A85` moss
- 背景：白色向上漂浮粒子（1~2.2px，22~40s 慢速）+ 点阵网格 + 扫描光带
- 卡片/面板四角 L 形方括号，替代整圈描边
- KPI 数字带"解码动画"（片假名/数字乱跳后收敛，2s）
- 节制动画：开场解码 + hot 脉冲 + LIVE 呼吸 + tile 随机 flash

## 失败占位

单个 endpoint 失败 → 对应指标显示 "—"，不影响其他区域。连续 3 次失败 → header 状态切 "CACHE · OFFLINE"。
24h 自动 `location.reload()` 防内存泄漏 / token 过期（长期挂屏）。

## 应用清单维护

80 应用清单硬编码在 HTML `GRID.sections` 中。新增/下线 → 改 HTML → commit → push GitLab → 同事拉代码同步。

## 录屏方式

Mac: Cmd+Shift+5，全屏打开 HTML 后录制。
