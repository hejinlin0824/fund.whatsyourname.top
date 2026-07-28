#!/usr/bin/env bash
# 一次性部署：migrate → 全量测试(失败即中止) → collectstatic → 重启 :8188 → 健康检查
# 用法：ssh 到服务器后 `bash deploy.sh`，或本地 `ssh ... 'cd ... && bash deploy.sh'`
cd ~/home/claude_PJ/Jijin_Kanban || { echo "project dir not found"; exit 1; }

echo "=== [1/6] makemigrations ==="
venv/bin/python manage.py makemigrations --noinput 2>&1 | tail -3

echo "=== [2/6] migrate ==="
venv/bin/python manage.py migrate --noinput 2>&1 | tail -3

echo "=== [3/6] test (full suite) ==="
venv/bin/python manage.py test 2>&1 | tee /tmp/jk_test.log | tail -6
TEST_RC=${PIPESTATUS[0]}
if [ "$TEST_RC" != "0" ]; then
  echo "!!! TESTS FAILED (rc=$TEST_RC) — 中止，不重启。详见 /tmp/jk_test.log"
  exit 1
fi

echo "=== [3/5] collectstatic ==="
venv/bin/python manage.py collectstatic --noinput 2>&1 | tail -1

echo "=== [4/5] restart runserver :8188 (kill old by port-PID, setsid detach) ==="
PID=$(ss -ltnp 2>/dev/null | grep ":8188" | grep -oP 'pid=\K[0-9]+' | head -1)
if [ -n "$PID" ]; then echo "killing old pid $PID"; kill -9 "$PID" 2>/dev/null; sleep 2; fi
setsid bash -c 'exec venv/bin/python manage.py runserver 0.0.0.0:8188 --noreload </dev/null >>server.log 2>&1' &
sleep 5

echo "=== [5/5] healthcheck ==="
ss -ltnp 2>/dev/null | grep ":8188" | head -1 || echo "NOT LISTENING"
curl -s -o /dev/null -w "localhost  HTTP %{http_code}\n" http://127.0.0.1:8188/ || true
echo "=== deploy done ==="
