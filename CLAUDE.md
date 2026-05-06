# GLP AI 应用指挥中心

单文件 HTML 大屏展示页，用于 GLP Digital Technology AI VP 演示/录屏，替代 PPT 热力图。

## 文件

- `glp_ai_command_center.html` — 唯一文件，无依赖，直接浏览器打开

## 设计规范

- 风格：暗黑科技大屏，模拟实时运营指挥中心
- 主色：GLP 绿 `#1B6B3A`，霓虹绿 `#5DFF9F`，背景 `#03080A`
- 字体：Segoe UI / PingFang SC / Microsoft YaHei
- 全屏，overflow hidden，不可滚动（主表格内部可滚动）

## 布局（从上到下）

```
HEADER     — GLP logo + 标题 + 实时时钟
KPI BAR    — 今日调用量 / 活跃用户 / AI渗透率 / 已上线应用 / 今日Tokens
MAIN BODY  — 左：热力图主表格（可滚动）| 右：侧边栏（260px）
FOOTER     — LIVE 状态栏
```

侧边栏从上到下：实时活动流 → 部门使用排行（进度条）→ 图例

## 主表格结构

行 = AI 应用（按分区分组），列 = 7 个部门

**列顺序（index 0-6）：**
Asset（资产管理）/ IDC（数据中心）/ 新能源 / 基金/其他 / 财务 / HR / Legal/IA/PR

**4 大分区（section）：**
1. 整体 General — AI Buddy 2.0 集团通用助手
2. 应用 Application — 6 个子分类（管理决策 / 创新业务 / 流程自动化 / 行业资讯 / 业务系统助手 / 业务知识库）
3. 基础建设 Foundation — 安全 / 治理 / 研发 / 数据
4. 新项目 Pipeline — 规划中

**格子（tile）3 种状态：**
- `complexity-high`：深绿实框，高频应用
- `complexity-mid`：浅绿实框，中频应用
- `complexity-planned`：虚线透明，规划中
- `hot` 额外类：常驻脉冲动画（当前只有"AI智能助理"）

## 动画逻辑

| 效果 | 位置 | 参数 |
|------|------|------|
| 格子随机亮起 | `activateRandomTile()` | 每 200-600ms 触发，持续 0.8-3s |
| KPI 开场计数 | `animateCounter()` | cubic easing，2s 内从 0 到目标值 |
| KPI 缓慢增长 | 3 个 setInterval | calls +1-8 每 1.5s，users 波动每 3s，tokens +1-3 每 2.5s |
| 实时活动流 | `addFeedItem()` | 每 1.5-4s 插入一条，最多保留 10 条 |
| 粒子背景 | 底部 IIFE | 35 颗粒子，30fps，标签页隐藏自动暂停 |

## KPI 当前数值（演示用）

- 今日调用量：128,547（持续增长）
- 活跃用户：847（在 840-860 之间波动）
- AI渗透率：73.2%
- 已上线应用：68
- 今日 Tokens：2,847M（持续增长）

## 部门使用排行（当前数值）

Asset 94% / IDC 87% / 财务 82% / 新能源 76% / Legal/IA/PR 71% / HR 65% / 基金/其他 58%

## 录屏方式

Mac：Cmd+Shift+5，选区域录屏，全屏打开 HTML 后录制
