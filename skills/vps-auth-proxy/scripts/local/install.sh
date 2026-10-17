#!/usr/bin/env bash
# 在服务器上装好 HTTP / SOCKS5 认证代理，并把凭据写进本机的登录信息文档。
#
#   install.sh --alias myserver                        # 用默认端口 20126 / 59357
#   install.sh --alias myserver --http-port 20126 --socks-port 59357
#   install.sh --alias myserver --rotate               # 重新生成用户名密码
#
# 凭据不会出现在终端里，只会写进权限 600 的文档。
set -euo pipefail

ALIAS="" HTTP_PORT="" SOCKS_PORT="" LANG_CODE="zh" DOC="" ROTATE="" IP=""
HERE="$(cd "$(dirname "$0")" && pwd)"
SERVER_PY="$HERE/../server/auth_proxy.py"

while [ $# -gt 0 ]; do
  case "$1" in
    --alias) ALIAS="$2"; shift 2 ;;
    --http-port) HTTP_PORT="$2"; shift 2 ;;
    --socks-port) SOCKS_PORT="$2"; shift 2 ;;
    --lang) LANG_CODE="$2"; shift 2 ;;
    --doc) DOC="$2"; shift 2 ;;
    --ip) IP="$2"; shift 2 ;;
    --rotate) ROTATE="--rotate"; shift ;;
    *) echo "未知参数：$1" >&2; exit 2 ;;
  esac
done

[ -n "$ALIAS" ] || { echo "用法：install.sh --alias <ssh名称> [--http-port 20126] [--socks-port 59357]" >&2; exit 2; }
[ -f "$SERVER_PY" ] || { echo "找不到 $SERVER_PY" >&2; exit 2; }

say() { echo "[auth-proxy] $*"; }

# 登录用户不是 root 时用 sudo
if [ "$(ssh -o BatchMode=yes "$ALIAS" 'id -u')" = 0 ]; then SUDO=""; else SUDO="sudo"; fi

ARGS="install"
[ -n "$HTTP_PORT" ] && ARGS="$ARGS --http-port $HTTP_PORT"
[ -n "$SOCKS_PORT" ] && ARGS="$ARGS --socks-port $SOCKS_PORT"
[ -n "$ROTATE" ] && ARGS="$ARGS $ROTATE"

say "在 $ALIAS 上安装代理实例"
ssh -o BatchMode=yes "$ALIAS" "$SUDO python3 - $ARGS" < "$SERVER_PY"

# 文档里的服务器地址：优先用 --ip，其次问 ssh 配置，最后让用户在文档里自己改
if [ -z "$IP" ]; then
  IP="$(ssh -G "$ALIAS" 2>/dev/null | awk '$1=="hostname"{print $2}')"
fi

# 定位文档
if [ -z "$DOC" ]; then
  dir="$HOME/Desktop"; [ -d "$dir" ] || dir="$HOME"
  if [ "$LANG_CODE" = zh ]; then DOC="$dir/我的服务器-${ALIAS}-订阅和账号.md"
  else DOC="$dir/my-server-${ALIAS}-subscriptions-and-accounts-${LANG_CODE}.md"; fi
fi

umask 077
SHOW_ARGS="show --lang $LANG_CODE"
[ -n "$IP" ] && SHOW_ARGS="$SHOW_ARGS --ip $IP"
SECTION="$(ssh -o BatchMode=yes "$ALIAS" "python3 - $SHOW_ARGS" < "$SERVER_PY")"
[ -n "$SECTION" ] || { echo "[auth-proxy] 取不到代理信息" >&2; exit 2; }

NEW="$DOC.new"
if [ -f "$DOC" ]; then
  # 去掉上一次写入的段落：标记包着的整段，以及没有标记的同名小节
  awk -v h1='## HTTP / SOCKS5 代理' -v h2='## HTTP / SOCKS5 proxy' '
       /^<!-- vps-auth-proxy:begin -->/{skip=1;next}
       /^<!-- vps-auth-proxy:end -->/{skip=0;next}
       index($0,h1)==1 || index($0,h2)==1 {skip=1;next}
       skip && /^## /{skip=0}
       !skip{print}' "$DOC" > "$NEW"
else
  printf '# %s 服务器登录信息\n' "$ALIAS" > "$NEW"
fi

{
  printf '\n<!-- vps-auth-proxy:begin -->\n'
  printf '%s\n' "$SECTION"
  printf '<!-- vps-auth-proxy:end -->\n'
} >> "$NEW"

mv -f "$NEW" "$DOC"
chmod 600 "$DOC"

say "登录信息已更新：${DOC}"
say "如果别的工具重新生成了这份文档，重跑本脚本即可补回这一段"
