#!/bin/bash
# AI heatmap 定时任务入口
# 被 launchd 每 5 分钟调用一次，里面判断时间决定跑什么
#
# 行为：
#   - 每次: collect.py --only llm-data（5 min 粒度）
#   - 每小时整点附近: 追加 collect.py --only ai-active-users
#   - 每日 01:10 附近: 追加 collect.py --only llm-data-detail + ai-all-pers
#   - 每次最后: aggregate.py 生成 kpis.json
#
# 接口 403 未解前用 --mock；接口通后改这里的 MODE 或删掉 --mock

set -e

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
# 优先用环境变量 AI_HEATMAP_PY 指定的 Python（部署时在 plist/systemd 里设）
# 否则从 PATH 找；最后兜底常见路径
if [ -n "$AI_HEATMAP_PY" ]; then
  PY="$AI_HEATMAP_PY"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
elif [ -x /usr/bin/python3 ]; then
  PY="/usr/bin/python3"
else
  echo "[fatal] python3 not found" >&2
  exit 127
fi
LOG="$ROOT/logs/cron.log"

# 接口通之前设 1，通了改 0（或删掉相关逻辑）
MOCK=1
MOCK_ARG=""
[ "$MOCK" = "1" ] && MOCK_ARG="--mock"

HOUR=$(date +%-H)
MIN=$(date +%-M)
DATE=$(date +%Y-%m-%d\ %H:%M:%S)

echo "===== $DATE  tick  (mock=$MOCK) =====" >> "$LOG"

# 每次都跑 llm-data（高频快照）
$PY scripts/collect.py $MOCK_ARG --only llm-data >> "$LOG" 2>&1 || echo "[warn] llm-data failed" >> "$LOG"

# 每小时在 5 分钟窗口内跑一次 active-users（避免漏掉）
if [ "$MIN" -lt 5 ]; then
  $PY scripts/collect.py $MOCK_ARG --only ai-active-users >> "$LOG" 2>&1 || echo "[warn] active-users failed" >> "$LOG"
fi

# 凌晨 01:10 附近跑每日任务
if [ "$HOUR" = "1" ] && [ "$MIN" -ge 10 ] && [ "$MIN" -lt 15 ]; then
  $PY scripts/collect.py $MOCK_ARG --only llm-data-detail >> "$LOG" 2>&1 || echo "[warn] detail failed" >> "$LOG"
  $PY scripts/collect.py $MOCK_ARG --only ai-all-pers    >> "$LOG" 2>&1 || echo "[warn] all-pers failed" >> "$LOG"
fi

# 每次都重新聚合（便宜，< 1s）
$PY scripts/aggregate.py >> "$LOG" 2>&1 || echo "[warn] aggregate failed" >> "$LOG"

echo "[done] $DATE" >> "$LOG"
