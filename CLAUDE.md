# GLP AI 应用指挥中心

单文件 HTML 大屏 + 本地 SQLite 留存 + OSS 快照发布。用于 GLP Digital Technology AI VP 演示/录屏。

> **指标口径权威文档**：[METRICS.md](./METRICS.md) — 新增/修改指标前先看这里，改完回写。

## 架构

```
内网 cron（launchd）
  ├─ scripts/collect.py   → POST DataHub 4 接口 → 写 data/heatmap.db
  └─ scripts/aggregate.py → 读 heatmap.db → 生成 kpis.json
                          → 上传 OSS（公开只读）
Vercel 公网 HTML
  └─ fetch OSS URL（每 60s 轮询，fallback 到 FALLBACK_DATA）
```

接口 403 未解前：`collect.py --mock` 跑完整链路。

## 目录

```
├── glp_ai_command_center.html  # 主文件（A+C 布局）
├── kpis.json                   # 前端数据源（aggregate.py 产物）
├── .env                        # DATAHUB_APPKEY / DATAHUB_URL，gitignore 排除
├── sql/
│   ├── 01_schema.sql           # 7 张表 + 6 个视图（SQLite）
│   └── 02_seed_applications.sql# 80 应用 + 7 平台 seed
├── data/
│   └── heatmap.db              # SQLite（gitignore 排除）
├── scripts/
│   ├── collect.py              # DataHub → heatmap.db（--mock 可跑）
│   └── aggregate.py            # heatmap.db → kpis.json
└── *.docx / *.xlsx             # 接口文档 & KPI 需求表，gitignore 排除
```

## DataHub 接口（4 个，全部 POST，当前 nginx 403）

| 接口 | 用途 | 采集频次 |
|---|---|---|
| `/ai-heatmap/llm-data` | 今日调用量 / Tokens / 环比 | 5 min |
| `/ai-heatmap/llm-data-detail` | 明细（日 × 平台 × 应用 × 团队 × 模型）| 每日 |
| `/ai-heatmap/ai-active-users` | 30/90 天活跃用户（仅 AI-Buddy）| 1 h |
| `/ai-heatmap/ai-all-pers` | 各平台总人数 | 每日 |

`llm-data-detail` 的 `source/model_name/develop_group/ai_app` 4 个维度入参标"待接入"，接口通后需验证。

## 建库（DBeaver，5 分钟）

1. DBeaver → 新建连接 → SQLite → 数据库路径 `data/heatmap.db`（自动创建）
2. SQL Editor 依次执行 `sql/01_schema.sql` 和 `sql/02_seed_applications.sql`
3. 末尾的校验 SELECT 应返回 4 个 section，共 80 应用

## 跑数据链路

**自动（已配 launchd，mock 模式）**：
- `~/Library/LaunchAgents/com.cgao1.ai-heatmap.tick.plist` 每 5 min 调 `scripts/tick.sh`
- 查看运行: `launchctl list | grep ai-heatmap`
- 日志: `logs/cron.log`（任务）/ `logs/launchd.log`（launchd 标准输出）
- 停用: `launchctl unload ~/Library/LaunchAgents/com.cgao1.ai-heatmap.tick.plist`
- 接口通后: 编辑 `scripts/tick.sh` 把 `MOCK=1` 改 `MOCK=0`，无需重载 plist（脚本每次读变量）

**手动**：
```bash
python3 scripts/collect.py --mock   # 接口未通前用 mock；通了去掉 --mock
python3 scripts/aggregate.py        # 产出 kpis.json
open glp_ai_command_center.html     # 浏览器刷新看效果
```

## 7 项上屏指标

KPI 区（5 卡单行）: 今日调用量 · 今日 Tokens · 30 天活跃用户 · 已上线应用 · 本月成本
  前 2 卡用 neon 绿大号（带环比），后 3 卡用 leaf 绿中号
热力图：7 部门 × 80 应用（general 8 / application 52 / foundation 16 / pipeline 4），主屏铺满
分析区（下滑查看，2 栏）: 近 7 天趋势折线 · 调用平台数字面板（昨日调用量 / Tokens / 本月成本）
  TOP 5 AI 应用已下线（等 `llm-data-detail` 的 `ai_app` 维度真实接入后再加回）；`v_top5_yday` 视图保留
  模型来源环形 2026-05-09 换成数字面板（原 donut 空间感太空）
  AI 渗透率已下线（口径未定）

→ 指标完整口径见 [METRICS.md](./METRICS.md)

## 视觉 5 原则

- 三层绿: `#5DFF9F` 关键数据 / `#AEE8C4` 主文字 / `#6B8F7D` 说明边框
- 降发光：只留 L1 大数字 + logo 的轻发光
- 双层背景：页面 `#03080A` + 卡片 `#0B1412` + 1px `#1B6B3A` 边
- 数字等宽 `ui-monospace`，标题 Segoe UI / PingFang SC
- 节制动画：只保留 KPI 开场计数 + hot 脉冲 + LIVE 呼吸；删除随机格子亮起 / 粒子背景 / 活动流

## 录屏方式

Mac: Cmd+Shift+5，全屏打开 HTML 后录制
