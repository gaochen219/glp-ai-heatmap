#!/usr/bin/env python3
"""
本地开发代理（Mac / 任何能访问 datahub.glp.com.cn 的机器）
=========================================================

作用：起一个本地 HTTP 服务器，**同时** serve 前端 HTML 和代理 /ai-heatmap/api/* 到
DataHub（带 HMAC-SHA1 签名）。让你在 Mac 本地就能看到**真实数据**的大屏，不需要等
vibeportal 后端。

使用方式
  export DATAHUB_APP_KEY=...
  export DATAHUB_APP_SECRET=...
  python3 local_proxy.py

  然后打开：http://localhost:8765/

  Ctrl+C 停止

端口占用：默认 8765，改 PORT 常量即可。

路由
  GET  /                                   →  glp_ai_command_center.html
  GET  /glp_ai_command_center.html         →  同上
  GET  /logo.png                           →  静态
  GET  /ai-heatmap/api/live                →  POST DataHub /llm-data
  GET  /ai-heatmap/api/trend?days=7        →  POST DataHub /llm-data-detail（自动计算日期窗口）
  GET  /ai-heatmap/api/users               →  POST DataHub /ai-active-users
  GET  /ai-heatmap/api/cost                →  占位 (204 No Content) — DataHub REST 未开放

安全
  - AppSecret 只存在服务端进程环境变量里，不进任何前端资产
  - 本脚本**仅限本地开发**。不要部署到公网
  - 默认只监听 127.0.0.1（不接收外部连接）
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import mimetypes
import os
import sys
import time
import traceback
import urllib.parse
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    import requests
except ImportError:
    sys.stderr.write(
        "[fatal] 缺少 requests 库：\n"
        "    pip install requests\n"
    )
    sys.exit(2)

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8765

DATAHUB_BASE = "https://datahub.glp.com.cn"
DATAHUB_PATH = {
    "live":  "/dh-engine/api/mysql/ai-heatmap/llm-data",
    "trend": "/dh-engine/api/mysql/ai-heatmap/llm-data-detail",
    "users": "/dh-engine/api/mysql/ai-heatmap/ai-active-users",
}

STATIC_FILES = {
    "/": "glp_ai_command_center.html",
    "/glp_ai_command_center.html": "glp_ai_command_center.html",
    "/logo.png": "logo.png",
}


# ─── Config loader (shared logic with verify_datahub.py) ───
def load_config():
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


# ─── DataHub signing ──────────────────────────────────────
class DataHubCaller:
    def __init__(self, app_key: str, app_secret: str, base_url: str = DATAHUB_BASE):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url.rstrip("/")

    def _sign(self, uri: str, ts_ms: int) -> str:
        message = (self.app_secret + uri + str(ts_ms)).encode("utf-8")
        digest = hmac.new(self.app_secret.encode("utf-8"), message, hashlib.sha1).digest()
        return base64.b64encode(digest).decode("utf-8")

    def post(self, uri: str, payload: dict | None = None, timeout: int = 10) -> tuple[int, bytes, str]:
        ts = int(time.time() * 1000)
        headers = {
            "Content-Type": "application/json",
            "a": self.app_key,
            "t": str(ts),
            "s": self._sign(uri, ts),
        }
        body = json.dumps(payload or {}).encode("utf-8")
        resp = requests.post(self.base_url + uri, data=body, headers=headers, timeout=timeout)
        ctype = resp.headers.get("Content-Type") or "application/json"
        return resp.status_code, resp.content, ctype


# ─── HTTP handler ─────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    # Per-class, set by main()
    caller: DataHubCaller = None  # type: ignore

    # Reduce noise; keep GET logs short
    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def _send_json(self, status: int, obj: dict):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, status: int, ctype: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, rel_name: str):
        path = ROOT / rel_name
        if not path.exists():
            self._send_json(404, {"error": f"static file not found: {rel_name}"})
            return
        ctype, _ = mimetypes.guess_type(str(path))
        ctype = ctype or "application/octet-stream"
        if ctype.startswith("text/"):
            ctype += "; charset=utf-8"
        self._send_bytes(200, ctype, path.read_bytes())

    def _handle_api(self, key: str, datahub_uri: str, payload: dict):
        try:
            status, raw, ctype = self.caller.post(datahub_uri, payload)
        except Exception as e:
            traceback.print_exc()
            self._send_json(502, {"error": f"upstream error: {e}"})
            return
        # Pass through DataHub response (ensure JSON content type)
        if "json" not in (ctype or ""):
            ctype = "application/json; charset=utf-8"
        self._send_bytes(status, ctype, raw)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query or "")

        # static
        if path in STATIC_FILES:
            self._serve_static(STATIC_FILES[path])
            return

        # api
        if path == "/ai-heatmap/api/live":
            self._handle_api("live", DATAHUB_PATH["live"], {})
            return
        if path == "/ai-heatmap/api/users":
            self._handle_api("users", DATAHUB_PATH["users"], {})
            return
        if path == "/ai-heatmap/api/trend":
            try:
                days = int((qs.get("days") or ["7"])[0])
            except ValueError:
                days = 7
            days = max(1, min(days, 90))
            today = date.today()
            end_d = today - timedelta(days=1)      # yesterday
            start_d = today - timedelta(days=days) # days back
            self._handle_api("trend", DATAHUB_PATH["trend"], {
                "start_date": start_d.isoformat(),
                "end_date":   end_d.isoformat(),
            })
            return
        if path == "/ai-heatmap/api/cost":
            # DataHub REST 尚未开放账单接口；前端会降级显示 "—"
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        # fallback
        self._send_json(404, {"error": f"not found: {path}"})


def main():
    app_key, app_secret = load_config()
    Handler.caller = DataHubCaller(app_key, app_secret)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/"
    print("=" * 60)
    print(f"  GLP AI Heatmap · 本地代理已启动")
    print(f"  访问:     {url}")
    print(f"  DataHub:  {DATAHUB_BASE}")
    print(f"  AppKey:   {app_key[:6]}...{app_key[-4:]}  (已脱敏)")
    print(f"  Ctrl+C 停止")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[bye] 代理已停止")
        server.server_close()


if __name__ == "__main__":
    main()
