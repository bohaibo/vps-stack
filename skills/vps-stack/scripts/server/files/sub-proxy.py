#!/usr/bin/env python3
"""Subscription front for 3x-ui: forwards only known subscription paths, adds traffic usage
headers (Subscription-Userinfo) from the server NIC counters, and never logs request URLs."""
import base64, datetime as dt, http.server, json, os, pathlib, re, threading, time, urllib.error, urllib.request

CFG = json.loads(pathlib.Path('/etc/vps-stack/sub-proxy.json').read_text())
STATE = pathlib.Path('/var/lib/vps-stack-sub/traffic.json')
LOCK = threading.Lock()
HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers',
       'transfer-encoding', 'upgrade', 'content-length', 'subscription-userinfo', 'profile-title',
       'profile-update-interval'}


def cycle_dates(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    day = CFG.get('reset_day')
    if not day:
        return 'since-install', ''
    y, m = now.year, now.month
    if now.day < day:
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    start = dt.date(y, m, day)
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return start.isoformat(), dt.date(ny, nm, day).isoformat()


def counters():
    p = pathlib.Path('/sys/class/net') / CFG['interface'] / 'statistics'
    return int((p / 'rx_bytes').read_text()), int((p / 'tx_bytes').read_text())


def save(s):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(s))
    os.chmod(tmp, 0o600)
    tmp.replace(STATE)


def sample():
    with LOCK:
        rx, tx = counters()
        boot = pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        start, reset = cycle_dates()
        try:
            s = json.loads(STATE.read_text())
        except (FileNotFoundError, ValueError):
            s = None
        if not s or s.get('cycle') != start:
            s = {'cycle': start, 'rx': 0, 'tx': 0, 'last_rx': rx, 'last_tx': tx, 'boot': boot}
        same = s['boot'] == boot
        s['rx'] += max(0, rx - s['last_rx']) if same else rx
        s['tx'] += max(0, tx - s['last_tx']) if same else tx
        s.update(last_rx=rx, last_tx=tx, boot=boot, updated=int(time.time()))
        save(s)
        return {'upload': s['rx'], 'download': s['tx'], 'total': CFG.get('total_bytes') or 0,
                'expire': 0, 'cycle_start': start, 'next_reset': reset}


def sampler():
    while True:
        try:
            sample()
        except Exception as e:
            print('traffic sampler error: ' + type(e).__name__, flush=True)
        time.sleep(30)



def yaml_filename(v):
    """3x-ui 给 Clash 订阅的文件名没有后缀，浏览器下载下来认不出是 YAML；补上 .yaml。
    客户端里显示的名字来自 Profile-Title，不受影响。"""
    def fix(m):
        name = m.group(2)
        return m.group(1) + (name if name.lower().endswith(('.yaml', '.yml')) else name + '.yaml') + m.group(3)
    v = re.sub(r"(filename\*=UTF-8'')([^;\s]+)()", fix, v)
    return re.sub(r'(filename=")([^"]+)(")', fix, v)

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *args):
        pass

    def do_HEAD(self):
        self.handle_request(True)

    def do_GET(self):
        self.handle_request(False)

    def handle_request(self, head):
        path = self.path.split('?', 1)[0]
        if self.path != path or not any(re.fullmatch(re.escape(p) + r'[A-Za-z0-9_-]{1,128}', path) for p in CFG['paths']):
            self.send_error(404)
            return
        headers = {'Host': CFG['upstream_host'], 'User-Agent': self.headers.get('User-Agent', 'SubscriptionClient')}
        req = urllib.request.Request(CFG['upstream'] + path, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                status, upheaders, body = r.status, r.headers, r.read(2 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as e:
            status, upheaders, body = e.code, e.headers, e.read(4096)
        except Exception:
            self.send_error(502, 'Subscription service unavailable')
            return
        if len(body) > 2 * 1024 * 1024:
            self.send_error(502)
            return
        self.send_response(status)
        is_yaml = 'yaml' in (upheaders.get('Content-Type') or '')
        for k, v in upheaders.items():
            if k.lower() == 'content-disposition' and is_yaml:
                v = yaml_filename(v)
            if k.lower() not in HOP:
                self.send_header(k, v)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        if status == 200:
            info = sample()
            self.send_header('Subscription-Userinfo', '; '.join(f'{k}={info[k]}' for k in ('upload', 'download', 'total', 'expire')))
            title = CFG.get('profile_title', 'XXD VPS')
            self.send_header('Profile-Title', 'base64:' + base64.b64encode(title.encode()).decode())
            self.send_header('Profile-Update-Interval', '12')
            if info['next_reset']:
                self.send_header('X-Subscription-Reset', info['next_reset'])
        self.end_headers()
        if not head:
            self.wfile.write(body)


if __name__ == '__main__':
    if CFG.get('reset_day') and not 1 <= CFG['reset_day'] <= 28:
        raise SystemExit('reset_day must be 1..28')
    STATE.parent.mkdir(parents=True, exist_ok=True)
    sample()
    threading.Thread(target=sampler, daemon=True).start()
    http.server.ThreadingHTTPServer(('127.0.0.1', 2097), Handler).serve_forever()
