#!/usr/bin/env python3
"""
采集脚本：DataHub 4 接口 → SQLite heatmap.db
支持 --mock 模式：接口 403 未解前可先用假数据跑通链路
接口通后去掉 --mock，或环境变量 DATAHUB_MOCK=0

用法：
  python3 scripts/collect.py --mock            # 所有接口用 mock 数据
  python3 scripts/collect.py                   # 真实调用 DataHub
  python3 scripts/collect.py --only llm-data   # 只采指定接口
"""
from __future__ import annotations
import argparse, json, os, sqlite3, sys, random
from datetime import datetime, timedelta, date
from pathlib import Path
from urllib import request, error

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "heatmap.db"
ENV_PATH = ROOT / ".env"

ENDPOINTS = {
    "llm-data":         "/dh-engine/api/mysql/ai-heatmap/llm-data",
    "llm-data-detail":  "/dh-engine/api/mysql/ai-heatmap/llm-data-detail",
    "ai-active-users":  "/dh-engine/api/mysql/ai-heatmap/ai-active-users",
    "ai-all-pers":      "/dh-engine/api/mysql/ai-heatmap/ai-all-pers",
}

# ─── 环境变量 ────────────────────────────────────────────
def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

# ─── HTTP ────────────────────────────────────────────────
def post_datahub(endpoint: str, appkey: str, base_url: str, payload: dict) -> dict:
    url = base_url.rstrip("/") + endpoint
    body = json.dumps(payload).encode("utf-8")
    # header 名待接口组确认；先按最常见 "appkey" 放一份，同时放 X-App-Key 兜底
    req = request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "appkey": appkey,
        "X-App-Key": appkey,
    })
    try:
        with request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except error.HTTPError as e:
        raise RuntimeError(f"{endpoint} HTTP {e.code}: {e.read()[:200].decode('utf-8','ignore')}")
    except error.URLError as e:
        raise RuntimeError(f"{endpoint} URLError: {e.reason}")

# ─── Mock 数据（接口通之前用）──────────────────────────────
def mock_llm_data() -> dict:
    base_req = random.randint(120_000, 135_000)
    return {
        "requests_today": base_req,
        "tokens_today":   random.randint(2_500_000_000, 3_200_000_000),
        "requests_yday":  int(base_req * random.uniform(0.85, 1.1)),
        "tokens_yday":    random.randint(2_400_000_000, 3_100_000_000),
        "requests_change_rate": f"{random.uniform(-10, 15):.2f}%",
        "tokens_change_rate":   f"{random.uniform(-15, 10):.2f}%",
    }

def mock_active_users() -> dict:
    return {"distinct_users_30d": random.randint(350, 420),
            "distinct_users_90d": random.randint(680, 750)}

def mock_all_pers() -> list[dict]:
    return [
        {"company_descr": "资产平台",    "pers_cnt": 527},
        {"company_descr": "IDC",         "pers_cnt": 480},
        {"company_descr": "新能源",      "pers_cnt": 320},
        {"company_descr": "基金/其他",   "pers_cnt": 180},
        {"company_descr": "财务",        "pers_cnt": 210},
        {"company_descr": "HR",          "pers_cnt": 95},
        {"company_descr": "Legal/IA/PR", "pers_cnt": 60},
    ]

def mock_llm_detail(start: date, end: date) -> list[dict]:
    # 模拟按天 + 按平台拆分；"待接入"维度默认 all
    sources = ["百炼", "Azure"]
    rows = []
    d = start
    while d <= end:
        for s in sources:
            rows.append({
                "t_date": d.isoformat(),
                "source": s,
                "develop_group": "all",
                "ai_app": "all",
                "model_name": "all",
                "requests": random.randint(40_000, 80_000),
                "tokens":   random.randint(800_000_000, 1_600_000_000),
            })
        d += timedelta(days=1)

    # 额外：昨日按应用的 TOP 明细（模拟"维度接入后"的数据形态，供前端演示）
    # 接口真实返回若 ai_app 仍为 "all"，这批行就不会出现
    yday = end
    top_apps = [
        ("AI 智能助理",       42_380),
        ("制度流程助理",      28_420),
        ("AI 智能问数",       19_630),
        ("税金分析助手",      12_210),
        ("GLP AI 文档翻译",   10_280),
        ("AI 智能巡检",        8_150),
        ("SAP/PTP 智能提单",   6_940),
    ]
    for name, req in top_apps:
        rows.append({
            "t_date": yday.isoformat(),
            "source": "百炼",
            "develop_group": "all",
            "ai_app": name,
            "model_name": "all",
            "requests": req,
            "tokens":   req * random.randint(18_000, 24_000),
        })
    return rows

# ─── SQLite 写入 ─────────────────────────────────────────
def upsert_llm_daily(conn, data: dict):
    conn.execute("""
      INSERT OR REPLACE INTO fact_llm_daily
        (snapshot_at, requests_today, tokens_today,
         requests_yday, tokens_yday,
         requests_change_rate, tokens_change_rate)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(timespec="seconds"),
          data.get("requests_today"), data.get("tokens_today"),
          data.get("requests_yday"), data.get("tokens_yday"),
          data.get("requests_change_rate"), data.get("tokens_change_rate")))

def upsert_active_users(conn, data: dict):
    conn.execute("""
      INSERT OR REPLACE INTO fact_active_users
        (snapshot_at, distinct_users_30d, distinct_users_90d, scope_note)
      VALUES (?, ?, ?, ?)
    """, (datetime.now().isoformat(timespec="seconds"),
          data.get("distinct_users_30d"), data.get("distinct_users_90d"),
          "仅含 AI-Buddy"))

def upsert_platforms(conn, rows: list[dict]):
    for r in rows:
        conn.execute("""
          INSERT OR REPLACE INTO dim_platforms (company_descr, pers_cnt, updated_at)
          VALUES (?, ?, datetime('now'))
        """, (r["company_descr"], r["pers_cnt"]))

def upsert_llm_detail(conn, rows: list[dict]):
    for r in rows:
        conn.execute("""
          INSERT OR REPLACE INTO fact_llm_detail
            (t_date, source, develop_group, ai_app, model_name,
             requests, tokens, collected_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (r["t_date"], r["source"],
              r.get("develop_group","all"), r.get("ai_app","all"),
              r.get("model_name","all"),
              r["requests"], r["tokens"]))

# ─── 主流程 ──────────────────────────────────────────────
def collect(conn, env, use_mock: bool, only: str | None):
    base_url = env.get("DATAHUB_BASE", "https://datahub.glp.com.cn")
    appkey = env.get("DATAHUB_APPKEY", "")

    def should_run(name): return (only is None) or (only == name)

    if should_run("llm-data"):
        data = mock_llm_data() if use_mock else post_datahub(
            ENDPOINTS["llm-data"], appkey, base_url, {})
        upsert_llm_daily(conn, data)
        print(f"[ok] llm-data → fact_llm_daily")

    if should_run("ai-active-users"):
        data = mock_active_users() if use_mock else post_datahub(
            ENDPOINTS["ai-active-users"], appkey, base_url, {})
        upsert_active_users(conn, data)
        print(f"[ok] ai-active-users → fact_active_users")

    if should_run("ai-all-pers"):
        rows = mock_all_pers() if use_mock else post_datahub(
            ENDPOINTS["ai-all-pers"], appkey, base_url, {}).get("data", [])
        upsert_platforms(conn, rows)
        print(f"[ok] ai-all-pers → dim_platforms ({len(rows)} 平台)")

    if should_run("llm-data-detail"):
        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=6)
        payload = {"start_date": start.isoformat(), "end_date": end.isoformat()}
        if use_mock:
            rows = mock_llm_detail(start, end)
        else:
            # 真实接口返回结构未知，占位按 {"data":[...]} 拆
            resp = post_datahub(ENDPOINTS["llm-data-detail"], appkey, base_url, payload)
            rows = resp.get("data", resp if isinstance(resp, list) else [])
        upsert_llm_detail(conn, rows)
        print(f"[ok] llm-data-detail → fact_llm_detail ({len(rows)} 行)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true",
                    help="用 mock 数据而不是真实调用 DataHub（接口 403 未解前用）")
    ap.add_argument("--only", choices=list(ENDPOINTS.keys()),
                    help="只采指定接口")
    args = ap.parse_args()

    use_mock = args.mock or os.getenv("DATAHUB_MOCK") == "1"
    env = load_env()
    if not DB_PATH.exists():
        print(f"[err] {DB_PATH} 不存在；请先在 DBeaver 跑 sql/01_schema.sql 和 02_seed_applications.sql")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    try:
        collect(conn, env, use_mock, args.only)
        conn.commit()
        print(f"[done] mode={'MOCK' if use_mock else 'REAL'}  db={DB_PATH}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
