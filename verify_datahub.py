#!/usr/bin/env python3
"""
DataHub 接口验证脚本
====================

在公司办公室电脑（能访问 datahub.glp.com.cn）上运行，一次性验证 3 个 REST 接口：
  1) /ai-heatmap/llm-data          —— 今日 vs 昨日 请求量/Token
  2) /ai-heatmap/ai-active-users   —— 30/90 天活跃用户
  3) /ai-heatmap/llm-data-detail   —— 明细（带 start_date/end_date/source/team/model 入参）

输出：
  - 终端打印每个接口的 HTTP 状态、业务 code、返回 JSON 摘要
  - 完整 JSON 保存到 fixtures/<endpoint>.json，后续作为前端联调 fixture
  - 最后一段是总结：哪些通了、哪些失败、建议下一步

运行方式
  前提：pip install requests   （几乎所有公司电脑都有）

  方式 A（推荐，用环境变量）：
    export DATAHUB_APP_KEY='Nzc1NDEyMzI4NTA=YWktaGVhdG1hcDE3'
    export DATAHUB_APP_SECRET='lXa3RhR1ZoZEcxaGNERTM=TnpjMU5ERXlNekk0TlRBPV'
    python3 verify_datahub.py

  方式 B（在 .env 里写好）：
    # .env 文件内容（在项目根目录，已 gitignore 排除）
    DATAHUB_APP_KEY=...
    DATAHUB_APP_SECRET=...
    python3 verify_datahub.py

安全
  - 真实 AppKey / AppSecret 绝不写进本脚本或 commit 进 git
  - fixtures/ 目录 gitignore 排除（会包含真实数据）
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    sys.stderr.write(
        "[fatal] 缺少 requests 库。请先安装：\n"
        "    pip install requests\n"
        "    或使用公司内部 PyPI 镜像：pip install -i <mirror> requests\n"
    )
    sys.exit(2)


BASE_URL = "https://datahub.glp.com.cn"
ROOT = Path(__file__).resolve().parent
FIXTURES_DIR = ROOT / "fixtures"


# ─── Config loader ─────────────────────────────────────────
def load_config():
    """优先读环境变量；没有再读 .env 文件。"""
    app_key = os.environ.get("DATAHUB_APP_KEY")
    app_secret = os.environ.get("DATAHUB_APP_SECRET")

    env_file = ROOT / ".env"
    if (not app_key or not app_secret) and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k == "DATAHUB_APP_KEY" and not app_key:
                app_key = v
            elif k == "DATAHUB_APP_SECRET" and not app_secret:
                app_secret = v

    if not app_key or not app_secret:
        sys.stderr.write(
            "[fatal] 没找到 DATAHUB_APP_KEY / DATAHUB_APP_SECRET。\n"
            "  方式 A: export DATAHUB_APP_KEY=... && export DATAHUB_APP_SECRET=...\n"
            "  方式 B: 在 .env 文件里写好\n"
        )
        sys.exit(3)
    return app_key, app_secret


# ─── Signature & request ───────────────────────────────────
class DataHubClient:
    def __init__(self, app_key: str, app_secret: str, base_url: str = BASE_URL):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url.rstrip("/")

    @staticmethod
    def _sign_hmac_sha1(key: str, message: str) -> str:
        digest = hmac.new(key.encode("utf-8"), message.encode("utf-8"), hashlib.sha1).digest()
        return base64.b64encode(digest).decode("utf-8")

    def _sign(self, uri: str, timestamp_ms: int) -> str:
        # 严格对齐 docx 里的 Java 实现：消息 = appCode + uri + timestamp
        message = self.app_secret + uri + str(timestamp_ms)
        return self._sign_hmac_sha1(self.app_secret, message)

    def post(self, uri: str, payload: dict | None = None, timeout: int = 10) -> dict:
        timestamp_ms = int(time.time() * 1000)
        headers = {
            "Content-Type": "application/json",
            "a": self.app_key,
            "t": str(timestamp_ms),
            "s": self._sign(uri, timestamp_ms),
        }
        body = json.dumps(payload or {}).encode("utf-8")
        resp = requests.post(self.base_url + uri, data=body, headers=headers, timeout=timeout)
        return {
            "http_status": resp.status_code,
            "headers": dict(resp.headers),
            "body": _safe_json(resp),
            "raw_text": resp.text[:500],  # 保留前 500 字符方便排查
        }


def _safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return None


# ─── Output helpers ────────────────────────────────────────
def banner(msg: str, ch: str = "=") -> None:
    print("\n" + ch * 72)
    print(f"  {msg}")
    print(ch * 72)


def hr() -> None:
    print("─" * 72)


def truncate(obj, maxlen: int = 600) -> str:
    s = json.dumps(obj, ensure_ascii=False, indent=2)
    if len(s) > maxlen:
        return s[:maxlen] + f"\n  ... (已截断，完整 JSON 见 fixtures/)"
    return s


def save_fixture(name: str, payload: dict) -> Path:
    FIXTURES_DIR.mkdir(exist_ok=True)
    out = FIXTURES_DIR / f"{name}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


# ─── Per-endpoint runners ──────────────────────────────────
def test_endpoint(client: DataHubClient, label: str, uri: str, payload: dict | None = None) -> dict:
    """返回 {ok, code, http_status, summary} 供最后统计。"""
    banner(f"[{label}] {uri}", ch="━")
    print(f"  payload: {json.dumps(payload or {}, ensure_ascii=False)}")
    hr()
    try:
        res = client.post(uri, payload)
    except requests.exceptions.RequestException as e:
        print(f"  ✗ 网络错误: {e}")
        return {"ok": False, "label": label, "reason": f"RequestException: {e}"}
    except Exception as e:
        print(f"  ✗ 脚本错误: {e}")
        return {"ok": False, "label": label, "reason": f"ScriptError: {e}"}

    http_status = res["http_status"]
    body = res["body"]
    print(f"  HTTP {http_status}")

    if http_status != 200:
        # 403/401 之类的 nginx 层拒绝，body 一般是 HTML
        print(f"  raw (前 500 字符):\n{res['raw_text']}")
        return {
            "ok": False,
            "label": label,
            "reason": f"HTTP {http_status}",
            "raw": res["raw_text"],
        }

    if not isinstance(body, dict):
        print("  ✗ 返回不是 JSON：\n" + res["raw_text"])
        return {"ok": False, "label": label, "reason": "not JSON"}

    # 业务 code 判断
    code = body.get("code", body.get("status"))
    if code is not None and code != 2000:
        print(f"  ✗ 业务 code={code}  message={body.get('message')}")
        save_fixture(label, body)
        return {"ok": False, "label": label, "reason": f"biz code {code}"}

    # 成功
    print(f"  ✓ 业务 code={code}")
    print(f"  JSON 摘要：\n{truncate(body)}")
    path = save_fixture(label, body)
    print(f"  → 已保存: {path.relative_to(ROOT)}")
    return {"ok": True, "label": label, "code": code, "data": body}


# ─── main ──────────────────────────────────────────────────
def main():
    banner("DataHub 接口验证脚本")
    app_key, app_secret = load_config()
    print(f"  BASE_URL:    {BASE_URL}")
    print(f"  APP_KEY:     {app_key[:6]}...{app_key[-4:]}   (已脱敏)")
    print(f"  APP_SECRET:  {app_secret[:4]}...{app_secret[-4:]}  (已脱敏)")
    print(f"  FIXTURES_DIR: {FIXTURES_DIR}")

    client = DataHubClient(app_key, app_secret)

    # 近 7 天（不含当日），对齐前端口径
    today = date.today()
    end_d = today - timedelta(days=1)         # 昨天
    start_d = today - timedelta(days=7)       # 7 天前

    results = []
    results.append(test_endpoint(
        client,
        "live",
        "/dh-engine/api/mysql/ai-heatmap/llm-data",
        {},
    ))
    results.append(test_endpoint(
        client,
        "users",
        "/dh-engine/api/mysql/ai-heatmap/ai-active-users",
        {},
    ))
    results.append(test_endpoint(
        client,
        "trend",
        "/dh-engine/api/mysql/ai-heatmap/llm-data-detail",
        {
            "start_date": start_d.isoformat(),
            "end_date":   end_d.isoformat(),
        },
    ))

    # ─── Summary ──────────────────────────────────────────
    banner("总结")
    ok_count = sum(1 for r in results if r.get("ok"))
    fail_count = len(results) - ok_count
    for r in results:
        icon = "✓" if r.get("ok") else "✗"
        reason = r.get("reason", f"code={r.get('code')}")
        print(f"  {icon}  {r['label']:<8}  {reason}")
    print()
    print(f"  通过 {ok_count}/{len(results)} · 失败 {fail_count}")

    # ─── 下一步建议 ───────────────────────────────────────
    banner("下一步", ch="─")
    if ok_count == len(results):
        print("  1. 把 fixtures/*.json 发给高晨（cgao1）")
        print("  2. 我会用这几份真实 JSON 替换前端 MOCK，验证 parse 逻辑")
        print("  3. 同时催 vibeportal 后端开发 4 个 /ai-heatmap/api/* endpoint")
    else:
        print("  ✗ 有接口没通，排查方向：")
        print("    - HTTP 403 (nginx 层)  → 网络/白名单问题；确认当前机器 IP 已加白")
        print("    - HTTP 4xx JSON code=4005/4014  → 签名错误；检查 AppSecret 是否正确")
        print("    - HTTP 4xx JSON code=4006/4007  → 入参错误；检查 payload 字段")
        print("    - 连不上                → 检查 DNS：ping datahub.glp.com.cn")
        print("    - 把失败的 fixtures/*.json 发给高晨")

    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
