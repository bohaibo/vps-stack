#!/usr/bin/env python3
"""在服务器上运行独立的 HTTP / SOCKS5 认证代理。

这个实例和面板管理的 Xray 完全分开：面板改配置、重装、升级内核都不会影响它，
它也不会出现在面板的入站列表里。只用来给指纹浏览器、多开浏览器这类客户端当出口代理。

子命令：
  install   安装/更新（重复执行安全，默认保留已有端口和凭据）
  show      输出可直接粘进文档的 Markdown（含凭据，只在本地重定向使用）
  verify    只读检查
  uninstall 卸载

本文件不含任何服务器地址或凭据，全部在运行时生成。
"""
import argparse
import json
import os
import pathlib
import secrets
import string
import subprocess
import sys
import time

ETC = pathlib.Path('/etc/vps-stack')
CONF = ETC / 'proxy.json'
UNIT = pathlib.Path('/etc/systemd/system/vps-stack-proxy.service')
SERVICE = 'vps-stack-proxy'
DEFAULT_XRAY = '/usr/local/x-ui/bin/xray-linux-amd64'
DEFAULT_HTTP = 20126
DEFAULT_SOCKS = 59357
USER_PREFIX = 'pxy'
ALPHABET = string.ascii_letters + string.digits

PRIVATE_NETS = ['127.0.0.0/8', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16',
                '169.254.0.0/16', '100.64.0.0/10', '::1/128', 'fc00::/7', 'fe80::/10']


def say(msg):
    print('[vps-stack-proxy] ' + msg, flush=True)


def die(msg):
    print('[vps-stack-proxy] 停止：' + msg, file=sys.stderr, flush=True)
    sys.exit(2)


def run(cmd, check=True, quiet=False):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if check and p.returncode:
        die(f"{' '.join(cmd)} 失败：{(p.stderr or p.stdout).strip()[:300]}")
    if not quiet and p.stdout.strip():
        say(p.stdout.strip())
    return p


def rand(n):
    return ''.join(secrets.choice(ALPHABET) for _ in range(n))


def config(http_port, socks_port, user, pw):
    """一个实例同时监听 HTTP 和 SOCKS5，出站固定 IPv4，私网和 BT 一律拒绝。"""
    acct = [{'user': user, 'pass': pw}]
    return {
        'log': {'loglevel': 'warning', 'access': 'none'},
        'inbounds': [
            {'tag': 'socks-in', 'listen': '0.0.0.0', 'port': socks_port, 'protocol': 'socks',
             'settings': {'auth': 'password', 'accounts': acct, 'udp': False},
             'sniffing': {'enabled': False}},
            {'tag': 'http-in', 'listen': '0.0.0.0', 'port': http_port, 'protocol': 'http',
             'settings': {'accounts': acct, 'allowTransparent': False},
             'sniffing': {'enabled': False}},
        ],
        'outbounds': [
            {'tag': 'direct', 'protocol': 'freedom', 'settings': {'domainStrategy': 'ForceIPv4'}},
            {'tag': 'block', 'protocol': 'blackhole', 'settings': {}},
        ],
        'routing': {
            'domainStrategy': 'AsIs',
            'rules': [
                {'type': 'field', 'ip': PRIVATE_NETS, 'outboundTag': 'block'},
                {'type': 'field', 'protocol': ['bittorrent'], 'outboundTag': 'block'},
            ],
        },
    }


UNIT_TEXT = """[Unit]
Description=Authenticated HTTP + SOCKS5 proxy (Xray)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={xray} run -config {conf}
Restart=on-failure
RestartSec=3
LimitNOFILE=1048576
NoNewPrivileges=true
ProtectHome=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/tmp

[Install]
WantedBy=multi-user.target
"""


def load():
    if not CONF.exists():
        die(f'还没安装：{CONF} 不存在，先运行 install')
    try:
        return json.loads(CONF.read_text())
    except Exception as exc:
        die(f'配置文件读不出来：{exc}')


def endpoints(conf):
    """从配置里取出端口和账号。"""
    out = {'http': None, 'socks': None, 'user': None, 'pass': None}
    for ib in conf.get('inbounds', []):
        proto = ib.get('protocol')
        if proto in ('http', 'socks'):
            out[proto] = ib.get('port')
        if out['user'] is None:
            acct = ((ib.get('settings') or {}).get('accounts') or [None])[0]
            if acct:
                out['user'], out['pass'] = acct.get('user'), acct.get('pass')
    return out


def listening(port):
    p = subprocess.run(['ss', '-Hlnt'], capture_output=True, text=True)
    return f':{port} ' in p.stdout


def cmd_install(a):
    xray = a.xray_bin or DEFAULT_XRAY
    if not os.path.exists(xray):
        die(f'找不到 Xray 内核：{xray}（这台机器应该先装好 3x-ui 面板；'
            '或用 --xray-bin 指定路径）')

    user = pw = None
    http_port, socks_port = a.http_port, a.socks_port
    if CONF.exists() and not a.rotate:
        cur = endpoints(load())
        http_port = http_port or cur['http'] or DEFAULT_HTTP
        socks_port = socks_port or cur['socks'] or DEFAULT_SOCKS
        user, pw = cur['user'], cur['pass']
        say('已有配置：沿用原来的端口和凭据（要换密码加 --rotate）')
    else:
        http_port = http_port or DEFAULT_HTTP
        socks_port = socks_port or DEFAULT_SOCKS
        user, pw = USER_PREFIX + rand(13), rand(24)

    if http_port == socks_port:
        die('HTTP 和 SOCKS5 不能用同一个端口')

    ETC.mkdir(parents=True, exist_ok=True)
    old = os.umask(0o077)
    try:
        CONF.write_text(json.dumps(config(http_port, socks_port, user, pw), indent=2) + '\n')
    finally:
        os.umask(old)
    CONF.chmod(0o600)

    UNIT.write_text(UNIT_TEXT.format(xray=xray, conf=CONF))
    UNIT.chmod(0o644)

    run(['systemctl', 'daemon-reload'])
    run(['systemctl', 'enable', SERVICE])
    run(['systemctl', 'restart', SERVICE])
    time.sleep(2)
    if run(['systemctl', 'is-active', SERVICE], check=False, quiet=True).stdout.strip() != 'active':
        run(['journalctl', '-u', SERVICE, '-n', '20', '--no-pager'], check=False)
        die('服务没起来，看上面的日志')

    for port in (http_port, socks_port):
        ok = False
        for _ in range(10):
            if listening(port):
                ok = True
                break
            time.sleep(1)
        if not ok:
            die(f'{port} 没有在监听，检查端口是否被别的程序占用：ss -lntp | grep {port}')

    if a.no_firewall is False and os.path.exists('/usr/sbin/ufw'):
        if 'Status: active' in run(['ufw', 'status'], check=False, quiet=True).stdout:
            for port, label in ((http_port, 'http'), (socks_port, 'socks5')):
                run(['ufw', 'allow', f'{port}/tcp', 'comment', f'vps-stack {label}'],
                    check=False, quiet=True)
            say('防火墙已放行（服务商后台的安全组也要放行同样端口）')
        else:
            say('UFW 未启用，跳过防火墙')

    say(f'完成：HTTP {http_port} / SOCKS5 {socks_port}，凭据写在 {CONF}（600，不会显示在这里）')
    return 0


def cmd_show(a):
    conf = load()
    e = endpoints(conf)
    if not e['user']:
        die('配置里没有账号')
    zh = a.lang == 'zh'
    ip = a.ip or '<服务器IP>'
    L = {
        'title': f'## HTTP / SOCKS5 代理（{ip}）' if zh else f'## HTTP / SOCKS5 proxy ({ip})',
        'lead': '两种任选，**建议先用 HTTP**（浏览器内核对 HTTP 代理认证的兼容性最好）。' if zh
                else 'Pick either one; **HTTP is recommended** (browsers handle HTTP proxy auth best).',
        'item': '项目' if zh else 'Item',
        'value': '值' if zh else 'Value',
        'type': '代理类型' if zh else 'Type',
        'host': 'IP / 主机' if zh else 'Host',
        'port': '端口' if zh else 'Port',
        'user': '用户名' if zh else 'Username',
        'pass': '密码' if zh else 'Password',
        'a': '### 方式 A：HTTP 代理（推荐）' if zh else '### Option A: HTTP proxy (recommended)',
        'b': '### 方式 B：SOCKS5 代理' if zh else '### Option B: SOCKS5 proxy',
    }

    def table(kind, port):
        return (f"| {L['item']} | {L['value']} |\n| --- | --- |\n"
                f"| {L['type']} | {kind} |\n"
                f"| {L['host']} | `{ip}` |\n"
                f"| {L['port']} | `{port}` |\n"
                f"| {L['user']} | `{e['user']}` |\n"
                f"| {L['pass']} | `{e['pass']}` |\n")

    out = f"{L['title']}\n\n{L['lead']}\n\n"
    if e['http']:
        out += L['a'] + '\n\n' + table('HTTP', e['http']) + '\n'
    if e['socks']:
        out += L['b'] + '\n\n' + table('SOCKS5', e['socks']) + '\n'
    print(out, end='')
    return 0


def cmd_verify(a):
    conf = load()
    e = endpoints(conf)
    bad = 0

    def check(name, ok, detail=''):
        nonlocal bad
        if not ok:
            bad += 1
        print(('PASS  ' if ok else 'FAIL  ') + name + (f'（{detail}）' if detail else ''))

    mode = oct(CONF.stat().st_mode)[-3:]
    check('配置文件权限 600', mode == '600', f'当前 {mode}')
    check('服务在运行', run(['systemctl', 'is-active', SERVICE], check=False,
                        quiet=True).stdout.strip() == 'active')
    check('开机自启', run(['systemctl', 'is-enabled', SERVICE], check=False,
                       quiet=True).stdout.strip() == 'enabled')
    for kind in ('http', 'socks'):
        if e[kind]:
            check(f'{kind.upper()} {e[kind]} 在监听', listening(e[kind]))

    # 不带凭据必须被拒；带凭据必须能出去，且私网被拦
    base = f'127.0.0.1:{e["http"]}'
    anon = subprocess.run(['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '8',
                           '-x', f'http://{base}', 'http://example.com'],
                          capture_output=True, text=True)
    check('匿名访问被拒绝', '407' in (anon.stdout + anon.stderr), (anon.stdout or anon.stderr)[:60])
    auth = f'http://{e["user"]}:{e["pass"]}@{base}'
    ok = subprocess.run(['curl', '-sS', '--max-time', '15', '-x', auth, 'https://api.ipify.org'],
                        capture_output=True, text=True)
    check('带凭据可以出网', ok.returncode == 0 and ok.stdout.strip() != '', ok.stdout.strip()[:40])
    priv = subprocess.run(['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '10',
                           '-x', auth, 'http://127.0.0.1:22'], capture_output=True, text=True)
    check('内网地址被拦截', priv.stdout.strip() not in ('200', ''), f'返回 {priv.stdout.strip()}')
    return 0 if bad == 0 else 1


def cmd_uninstall(a):
    run(['systemctl', 'disable', '--now', SERVICE], check=False, quiet=True)
    for f in (UNIT, CONF):
        if f.exists():
            f.unlink()
            say(f'已删除 {f}')
    run(['systemctl', 'daemon-reload'], check=False, quiet=True)
    say('已卸载（防火墙规则保留，需要的话自己 ufw delete allow <端口>/tcp）')
    return 0


def main():
    ap = argparse.ArgumentParser(description='独立的 HTTP / SOCKS5 认证代理')
    sp = ap.add_subparsers(dest='cmd', required=True)

    i = sp.add_parser('install')
    i.add_argument('--http-port', type=int)
    i.add_argument('--socks-port', type=int)
    i.add_argument('--xray-bin')
    i.add_argument('--rotate', action='store_true', help='重新生成用户名和密码')
    i.add_argument('--no-firewall', action='store_true')

    s = sp.add_parser('show')
    s.add_argument('--lang', default='zh')
    s.add_argument('--ip', help='写进文档的服务器地址，不填用占位符')

    sp.add_parser('verify')
    sp.add_parser('uninstall')

    a = ap.parse_args()
    if os.geteuid() != 0:
        die('需要 root 权限运行')
    return {'install': cmd_install, 'show': cmd_show,
            'verify': cmd_verify, 'uninstall': cmd_uninstall}[a.cmd](a) or 0


if __name__ == '__main__':
    sys.exit(main())
