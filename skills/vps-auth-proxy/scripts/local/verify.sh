#!/usr/bin/env bash
# 从本机测一遍代理能不能用：出口 IP、认证、内网拦截、两个协议。
#
#   verify.sh --alias myserver
#
# 凭据只在脚本内部使用，不会打印。
set -euo pipefail

ALIAS=""
HERE="$(cd "$(dirname "$0")" && pwd)"
SERVER_PY="$HERE/../server/auth_proxy.py"

while [ $# -gt 0 ]; do
  case "$1" in
    --alias) ALIAS="$2"; shift 2 ;;
    *) echo "未知参数：$1" >&2; exit 2 ;;
  esac
done
[ -n "$ALIAS" ] || { echo "用法：verify.sh --alias <ssh名称>" >&2; exit 2; }

read -r HOST <<<"$(ssh -G "$ALIAS" 2>/dev/null | awk '$1=="hostname"{print $2}')"
read -r USER_NAME PW HTTP_PORT SOCKS_PORT <<<"$(ssh -o BatchMode=yes "$ALIAS" \
  "python3 -c \"import json;d=json.load(open('/etc/auth-proxy/proxy.json'));e={i['protocol']:i for i in d['inbounds']};a=e['http']['settings']['accounts'][0];print(a['user'],a['pass'],e['http']['port'],e['socks']['port'])\"" \
  < /dev/null)"

[ -n "${HTTP_PORT:-}" ] || { echo "[verify] 服务器上还没装代理" >&2; exit 2; }

BAD=0
check() { if [ "$2" = 1 ]; then echo "PASS  $1"; else echo "FAIL  $1${3:+（$3）}"; BAD=$((BAD+1)); fi; }

echo "服务器：$HOST  HTTP：$HTTP_PORT  SOCKS5：$SOCKS_PORT"

HTTP_URL="http://$USER_NAME:$PW@$HOST:$HTTP_PORT"

out=$(curl -sS --max-time 20 -x "$HTTP_URL" https://api.ipify.org 2>/dev/null || true)
[ "$out" = "$HOST" ] && check "HTTP 代理出口是这台服务器" 1 || check "HTTP 代理出口是这台服务器" 0 "拿到 ${out:-空}"

code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 -x "http://$HOST:$HTTP_PORT" http://example.com 2>/dev/null || true)
[ "$code" = 407 ] && check "匿名访问被拒绝（407）" 1 || check "匿名访问被拒绝（407）" 0 "返回 ${code:-空}"

code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 12 -x "$HTTP_URL" http://127.0.0.1:22 2>/dev/null || true)
[ "$code" != 200 ] && check "内网地址被拦截" 1 || check "内网地址被拦截" 0 "返回 200"

sout=$(curl -sS --max-time 20 --socks5-hostname "$HOST:$SOCKS_PORT" -U "$USER_NAME:$PW" \
  https://api.ipify.org 2>/dev/null || true)
[ "$sout" = "$HOST" ] && check "SOCKS5 代理出口是这台服务器" 1 || check "SOCKS5 代理出口是这台服务器" 0 "拿到 ${sout:-空}"

code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 -x "$HTTP_URL" https://www.google.com 2>/dev/null || true)
[ "$code" = 200 ] && check "访问境外站点正常" 1 || check "访问境外站点正常" 0 "返回 ${code:-空}"

echo
[ "$BAD" = 0 ] && echo "全部通过" || { echo "$BAD 项未通过"; exit 1; }
