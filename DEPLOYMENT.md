# GLP AI 应用指挥中心 — 部署交接材料

> **目的**：把这个项目从本机 Mac 迁到公司内网服务器，由 IT 团队协助部署。
> **状态（2026-05-10）**：功能完整，本机 mock 模式已跑通 3 天；阻塞在 DataHub 接口 403（网络层）和需要一台内网服务器。
> **联系人**：高晨（cgao1）

---

## 一、项目做什么

大屏可视化 GLP 集团 AI 应用的使用情况，用于 AI VP 层级的演示和日常可视。

**覆盖指标（7 项上屏，完整口径见 [METRICS.md](./METRICS.md)）**：
1. 今日调用量 + 环比
2. 今日 Tokens + 环比
3. 30 天活跃用户（AI-Buddy）
4. 已上线应用数（80 个）
5. 本月成本 ¥ + 环比
6. 近 7 天调用趋势
7. 调用平台（百炼 / Azure 的调用量 / Tokens / 本月成本）

**数据源**：公司 DataHub 的 4 个接口（均 `/dh-engine/api/mysql/ai-heatmap/*`）+ 每月手动录入的阿里云百炼/Azure 账单。

---

## 二、为什么需要部署到服务器

现在的一切都跑在我本机 Mac，实际使用有 3 个硬问题：

1. **Mac 关机/睡眠数据就停**：launchd 定时任务跑在我电脑上，我不在办公室的时候没人看到更新
2. **公司安全策略**：给我 Mac 开 DataHub 白名单不合规，应该白名单给服务器固定 IP
3. **Vercel 公网需要稳定源**：前端大屏对外 fetch `kpis.json`，这个 JSON 要稳定可访问（当前部署设计是放到 OSS，暂时没接）

**部署目标架构**：
```
┌────────────────────────────────────────────────────┐
│ 内网服务器（新申请，Linux）                          │
│  ├─ cron / systemd                                │
│  │  └─ 每 5 min 跑 collect.py + aggregate.py      │
│  ├─ SQLite 本地留存（heatmap.db）                 │
│  └─ kpis.json → 上传到 OSS（heartjar-data-hz）    │
└─────────────────┬──────────────────────────────────┘
                  │ 调 DataHub HTTP 接口
                  │ （需 IP 白名单）
                  ▼
┌────────────────────────────────────────────────────┐
│ DataHub (datahub.glp.com.cn)                       │
│  /dh-engine/api/mysql/ai-heatmap/*                 │
└────────────────────────────────────────────────────┘

                    Vercel 公网
                         │
                         │ fetch kpis.json (OSS URL)
                         ▼
                    浏览器大屏
```

---

## 三、需要同事协助的事（核心需求）

### 3.1 申请一台 Linux 服务器

| 项 | 要求 |
|---|---|
| 数量 | 1 台 |
| OS | Linux（CentOS / Ubuntu / Rocky 都行，我这边脚本兼容）|
| 位置 | 公司内网（能访问 `datahub.glp.com.cn`）|
| 规格 | 很低。2 vCPU / 2GB RAM / 20GB 磁盘足够（SQLite 数据一年不超过 200MB）|
| 软件 | Python 3.8+、curl、sqlite3、cron/systemd 任一；能 SSH 进去 |
| 网络出口 | **公网可访问**（上传 OSS 需要，heartjar-data-hz 走公网 endpoint）|
| 固定 IP | 需要，**之后要把这个 IP 加到 DataHub 白名单** |

### 3.2 解 DataHub `/dh-engine/*` 的 403

**现象**（我在 Mac 上验证过 4 次，每次都 403）：
```bash
$ curl -X POST https://datahub.glp.com.cn/dh-engine/api/mysql/ai-heatmap/llm-data \
    -H "Content-Type: application/json" \
    -H "appkey: <我的 appkey>" -d '{}'

HTTP/1.1 403 Forbidden
Server: nginx
<html>...403 Forbidden...</html>
```

**判断**：nginx 层直接拒，说明请求没到应用层，**不是 appkey 问题**，是网络层/白名单。

**要同事确认的 3 件事**（找 **DataHub 基础设施/运维** 团队，不是邱宇 —— 邱宇是应用层负责给 appkey 的）：

1. **IP 白名单**：部署服务器固定 IP 是否需要加到白名单？加完后怎么验证？
2. **appkey 的正确传递方式**：header 名是什么？试过 `appkey` / `X-App-Key` / `Authorization: Bearer` 全 403。可能需要签名/时间戳？（接口文档错误码里有 4005 签名校验失败、4014 签名错误，说明有签名机制但文档没给方法）
3. **能跑通的 curl 示例**：哪怕一个接口（`/ai-heatmap/llm-data`）有真实能返回 200 的 curl，我照抄就行

如果 DataHub 团队愿意给近 7 天的历史样本 JSON（`llm-data-detail`），能让我们在接口通之前先做本地联调，降低上线风险。

### 3.3 阿里云 OSS 上传权限

**Bucket**：`heartjar-data-hz`（和现有 `oss_backup.py` 用的同一个，我之前已经在用）
**需要**：一个能 PUT 对象的 RAM 子账号 AccessKey（只给这个 bucket、只给 `oss:PutObject` 权限）
**产物**：一个 key 叫 `ai-heatmap/kpis.json`，前端 Vercel 就 fetch 这个 URL

---

## 四、部署步骤（同事拿到服务器后）

**约 30 分钟搞定。如果 DataHub 白名单已通，全程无需我到场。**

### 4.1 拉代码

```bash
# GitHub
git clone git@github.com:gaochen219/glp-ai-heatmap.git

# 或 GitLab
git clone git@gitlab.g2link-inc.cn:cgao1/glp-ai-heatmap.git

cd glp-ai-heatmap
```

### 4.2 初始化数据库

```bash
mkdir -p data logs
sqlite3 data/heatmap.db < sql/01_schema.sql
sqlite3 data/heatmap.db < sql/02_seed_applications.sql
# 预期最后输出: general 8 / application 52 / foundation 16 / pipeline 4
```

### 4.3 配置环境变量

创建 `.env` 文件（**不进 git**，gitignore 已排除）：

```bash
DATAHUB_BASE=https://datahub.glp.com.cn
DATAHUB_APPKEY=<找邱宇拿的 appkey>

# 阿里云 OSS（用于上传 kpis.json）
OSS_ACCESS_KEY_ID=<OSS RAM 子账号 AK>
OSS_ACCESS_KEY_SECRET=<OSS RAM 子账号 SK>
OSS_BUCKET=heartjar-data-hz
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_KEY=ai-heatmap/kpis.json
```

### 4.4 先跑 mock 模式确认链路通

```bash
python3 scripts/collect.py --mock
python3 scripts/aggregate.py
# 期望: kpis.json 生成，大小 ~1400 bytes，包含 live/users/apps/cost/trend_7d/top5_apps/platforms 字段
cat kpis.json | python3 -m json.tool | head -30
```

### 4.5 切真实接口

编辑 `scripts/tick.sh`，把 `MOCK=1` 改成 `MOCK=0`，或直接跑：

```bash
python3 scripts/collect.py   # 不加 --mock
python3 scripts/aggregate.py
```

如果 DataHub 能通，会看到真实数据；如果 403 还在，先把这步跳过，链路用 mock 先跑起来。

### 4.6 配定时任务

**cron 版本**（推荐，简单）：
```bash
crontab -e
# 追加一行：
*/5 * * * * /path/to/glp-ai-heatmap/scripts/tick.sh
```

**systemd timer 版本**（生产环境更清晰）：
```ini
# /etc/systemd/system/ai-heatmap.service
[Service]
Type=oneshot
WorkingDirectory=/path/to/glp-ai-heatmap
ExecStart=/path/to/glp-ai-heatmap/scripts/tick.sh
Environment=AI_HEATMAP_PY=/usr/bin/python3

# /etc/systemd/system/ai-heatmap.timer
[Timer]
OnBootSec=30s
OnUnitActiveSec=300s
[Install]
WantedBy=timers.target
```
```bash
systemctl enable --now ai-heatmap.timer
```

### 4.7 配 OSS 上传

我还没写 OSS 上传代码（本机没这个需求），服务器部署时要加一个 30 行的 Python 脚本：
- `aggregate.py` 跑完后调 `oss2` SDK，`put_object_from_file(OSS_KEY, 'kpis.json')`
- 依赖：`pip install oss2`
- **这一步我可以在你们拿到服务器访问权之后远程帮忙加上**（或者我先写好，再 merge）

### 4.8 前端 Vercel 部署

这步不急，OSS 链路通了再做：
- HTML 里的 `fetch('kpis.json')` 改成 OSS 的公网 URL（如 `https://heartjar-data-hz.oss-cn-hangzhou.aliyuncs.com/ai-heatmap/kpis.json`）
- Vercel import GitHub 仓库，主分支自动部署
- 确保 OSS bucket 的 `ai-heatmap/kpis.json` 对象设为公开只读

---

## 五、现有待办清单

服务器部署之后才能推进的：
- [ ] DataHub 403 解除 + IP 白名单
- [ ] OSS 上传脚本 + AK 配置
- [ ] Vercel 部署 + 前端 URL 切换
- [ ] `llm-data-detail` 的 4 个维度入参（source/model_name/develop_group/ai_app）标注"待接入"，接口通后验证返回字段是否真有拆分值，schema 可能要微调
- [ ] TOP5 AI 应用面板接回前端（需 `ai_app` 维度有真实值）
- [ ] 月度成本录入流程（每月把百炼 T+1、Azure T+7 账单导出后 `INSERT INTO fact_cost_monthly`）

不依赖服务器，随时可做：
- [ ] 前端 FALLBACK 改成"—"占位（生产环境不该显示假数据）
- [ ] 历史数据回填（接口通后，通过 `llm-data-detail` 按日期范围拉历史）

---

## 六、现有文件结构（参考）

```
glp-ai-heatmap/
├── README / CLAUDE.md             — 项目说明（Claude Code 配置，可忽略）
├── METRICS.md                     — 指标口径权威文档
├── DEPLOYMENT.md                  — 本文件
├── glp_ai_command_center.html     — 单文件大屏（纯 HTML + JS + SVG）
├── kpis.json                      — 前端数据源（aggregate.py 产物）
├── logo.png                       — GLP 图标
├── sql/
│   ├── 01_schema.sql              — 7 张表 + 6 视图
│   └── 02_seed_applications.sql   — 80 应用清单
├── scripts/
│   ├── collect.py                 — 调 DataHub 写 SQLite（--mock 可跑）
│   ├── aggregate.py               — SQLite 聚合到 kpis.json
│   └── tick.sh                    — cron/systemd 入口（调 collect + aggregate）
├── data/                          — SQLite 数据（gitignore）
│   └── heatmap.db
└── logs/                          — 运行日志（gitignore）
    └── cron.log
```

---

## 七、我的信息

- **邮箱/钉钉**：（补）
- **GitHub**：gaochen219
- **GitLab**：cgao1
- **有问题随时找我**
