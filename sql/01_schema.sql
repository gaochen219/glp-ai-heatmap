-- ═══════════════════════════════════════════════════════════════════
-- GLP AI 应用指挥中心 — SQLite schema
-- 创建 heatmap.db：在 DBeaver 里 New Connection → SQLite → 新建文件
--   data/heatmap.db → 打开 SQL Editor → 粘贴本文件执行一次
-- 然后执行 02_seed_applications.sql 灌入 68 应用
-- ═══════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ─────────────────────────────────────────────────────────────────
-- 维度：AI 应用清单（手动维护，热力图格子来源）
-- ─────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dim_applications;
CREATE TABLE dim_applications (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  name          TEXT    NOT NULL,                               -- 应用名称
  section       TEXT    NOT NULL CHECK (section IN
                   ('general','application','foundation','pipeline')),
  subsection    TEXT    NOT NULL,                               -- 子分类
  dept_idx      INTEGER NOT NULL CHECK (dept_idx BETWEEN 0 AND 6),
                                                                -- 0 Asset 1 IDC 2 新能源
                                                                -- 3 基金/其他 4 财务 5 HR
                                                                -- 6 Legal/IA/PR
  complexity    TEXT    NOT NULL DEFAULT 'mid' CHECK (complexity IN
                   ('high','mid','planned')),
  is_hot        INTEGER NOT NULL DEFAULT 0,                     -- 0/1：脉冲动画
  display_order INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT    DEFAULT (datetime('now')),
  updated_at    TEXT    DEFAULT (datetime('now'))
);
CREATE INDEX idx_app_section    ON dim_applications(section);
CREATE INDEX idx_app_subsection ON dim_applications(subsection);
CREATE INDEX idx_app_dept       ON dim_applications(dept_idx);

-- ─────────────────────────────────────────────────────────────────
-- 维度：各平台总人数（ai-all-pers 快照，半年变一次）
-- ─────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dim_platforms;
CREATE TABLE dim_platforms (
  company_descr TEXT    PRIMARY KEY,   -- "资产平台" / "新能源" ...
  pers_cnt      INTEGER NOT NULL,
  updated_at    TEXT    DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────────────
-- 维度：模型目录（llm-data-detail 里的 model_name + source）
-- ─────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dim_models;
CREATE TABLE dim_models (
  model_name TEXT PRIMARY KEY,
  source     TEXT NOT NULL,            -- "Azure" / "百炼" / "火山" / ...
  is_active  INTEGER DEFAULT 1,
  note       TEXT,
  updated_at TEXT DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────────────
-- 事实：llm-data 每 5 min 快照（6 字段全量汇总，留历史）
-- ─────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS fact_llm_daily;
CREATE TABLE fact_llm_daily (
  snapshot_at          TEXT    PRIMARY KEY,   -- ISO8601 采集时刻
  requests_today       INTEGER NOT NULL,
  tokens_today         INTEGER NOT NULL,
  requests_yday        INTEGER,
  tokens_yday          INTEGER,
  requests_change_rate TEXT,                  -- "106.09%"
  tokens_change_rate   TEXT
);
CREATE INDEX idx_llm_daily_date
  ON fact_llm_daily(date(snapshot_at));

-- ─────────────────────────────────────────────────────────────────
-- 事实：llm-data-detail 明细（按日期 × 平台 × 团队 × 应用 × 模型）
-- 主键设计 = 接口返回的 5 个维度；同日 upsert
-- ─────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS fact_llm_detail;
CREATE TABLE fact_llm_detail (
  t_date        TEXT    NOT NULL,     -- yyyy-MM-dd
  source        TEXT    NOT NULL,     -- "all" 或平台名
  develop_group TEXT    NOT NULL DEFAULT 'all',
  ai_app        TEXT    NOT NULL DEFAULT 'all',
  model_name    TEXT    NOT NULL DEFAULT 'all',
  requests      INTEGER NOT NULL,
  tokens        INTEGER NOT NULL,
  collected_at  TEXT    DEFAULT (datetime('now')),
  PRIMARY KEY (t_date, source, develop_group, ai_app, model_name)
);
CREATE INDEX idx_detail_date   ON fact_llm_detail(t_date);
CREATE INDEX idx_detail_app    ON fact_llm_detail(ai_app);
CREATE INDEX idx_detail_source ON fact_llm_detail(source);

-- ─────────────────────────────────────────────────────────────────
-- 事实：ai-active-users 每小时快照
-- ─────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS fact_active_users;
CREATE TABLE fact_active_users (
  snapshot_at        TEXT    PRIMARY KEY,
  distinct_users_30d INTEGER NOT NULL,
  distinct_users_90d INTEGER NOT NULL,
  scope_note         TEXT                   -- "仅含 AI-Buddy" 等
);
CREATE INDEX idx_users_date
  ON fact_active_users(date(snapshot_at));

-- ─────────────────────────────────────────────────────────────────
-- 事实：手动录入月度成本（Azure T+7、百炼 T+1）
-- ─────────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS fact_cost_monthly;
CREATE TABLE fact_cost_monthly (
  ym         TEXT    NOT NULL,         -- "2026-05"
  platform   TEXT    NOT NULL,         -- "Azure" / "百炼" / ...
  cost_cny   REAL    NOT NULL,
  tokens     INTEGER,                  -- 可选
  requests   INTEGER,                  -- 可选
  note       TEXT,
  entered_at TEXT    DEFAULT (datetime('now')),
  PRIMARY KEY (ym, platform)
);
CREATE INDEX idx_cost_ym ON fact_cost_monthly(ym);

-- ─────────────────────────────────────────────────────────────────
-- 视图：上屏用的聚合（供采集脚本生成 kpis.json）
-- ─────────────────────────────────────────────────────────────────
DROP VIEW IF EXISTS v_latest_llm;
CREATE VIEW v_latest_llm AS
  SELECT * FROM fact_llm_daily
  ORDER BY snapshot_at DESC
  LIMIT 1;

DROP VIEW IF EXISTS v_latest_users;
CREATE VIEW v_latest_users AS
  SELECT * FROM fact_active_users
  ORDER BY snapshot_at DESC
  LIMIT 1;

DROP VIEW IF EXISTS v_apps_count;
CREATE VIEW v_apps_count AS
  SELECT
    SUM(CASE WHEN complexity != 'planned' THEN 1 ELSE 0 END) AS total_online,
    SUM(CASE WHEN complexity  = 'planned' THEN 1 ELSE 0 END) AS planned,
    COUNT(*) AS total
  FROM dim_applications;

DROP VIEW IF EXISTS v_cost_current_month;
CREATE VIEW v_cost_current_month AS
  SELECT
    strftime('%Y-%m', 'now', 'localtime') AS ym,
    COALESCE(SUM(cost_cny), 0)            AS cost_cny
  FROM fact_cost_monthly
  WHERE ym = strftime('%Y-%m', 'now', 'localtime');

DROP VIEW IF EXISTS v_trend_7d;
CREATE VIEW v_trend_7d AS
  SELECT t_date, SUM(requests) AS requests, SUM(tokens) AS tokens
  FROM fact_llm_detail
  WHERE t_date >= date('now', 'localtime', '-7 days')
  GROUP BY t_date
  ORDER BY t_date;

DROP VIEW IF EXISTS v_top5_yday;
CREATE VIEW v_top5_yday AS
  SELECT ai_app AS name, SUM(requests) AS requests
  FROM fact_llm_detail
  WHERE t_date = date('now', 'localtime', '-1 day')
    AND ai_app != 'all'
  GROUP BY ai_app
  ORDER BY requests DESC
  LIMIT 5;

DROP VIEW IF EXISTS v_source_share_yday;
CREATE VIEW v_source_share_yday AS
  SELECT source, SUM(requests) AS requests
  FROM fact_llm_detail
  WHERE t_date = date('now', 'localtime', '-1 day')
    AND source != 'all'
  GROUP BY source
  ORDER BY requests DESC;
