---
name: vps-auth-proxy
description: 在一台已装好 3x-ui / Xray 的服务器上，加一套给指纹浏览器、多开浏览器（比特浏览器、AdsPower 等）用的独立代理：同一个 Xray 实例同时提供 HTTP 和 SOCKS5，带用户名密码认证，私网和 BT 一律拒绝，凭据自动写进本机登录信息文档。Use when the user asks to 给服务器加代理、指纹浏览器代理、多开浏览器代理、比特浏览器代理、HTTP 代理 20126、SOCKS5 代理、加个带账号密码的代理、出口 IP 固定，or to re-check / rotate / remove such a proxy.
---

# HTTP / SOCKS5 认证代理

在一台已经跑着 3x-ui 的机器上，额外开一个**独立**的 Xray 实例，同时提供 HTTP 和 SOCKS5 代理，给指纹浏览器、多开浏览器这类客户端当固定出口。

它和面板完全分开：不在面板的入站列表里，改面板、重装 3x-ui、升级内核都不会影响它。

设计理由见 [references/design.md](references/design.md)；出错先看 [references/troubleshooting.md](references/troubleshooting.md)。

## 语言

用户用什么语言就全程用那种语言。写进文档的那段用 `--lang` 控制：中文 `zh`（默认）、English `en`；其他语言用 `en`。

## 必须遵守

1. **只操作用户这次指定的服务器。**
2. **不在对话里显示凭据。** 用户名、密码、文档路径都不要打印；凭据只通过脚本写进权限 600 的文档，你只告诉用户文件在哪。
3. **每台服务器独立生成凭据。** 不复制别的服务器的用户名密码。
4. **默认端口 20126（HTTP）/ 59357（SOCKS5）**；被占用时换一对，并告诉用户改了什么。
5. 这是**带认证的公网代理**，被拿去扫号、发垃圾会连累服务器 IP。端口不要改成 80/443/8080 这类常见端口，也不要关掉私网拦截。

## 前提

服务器已装 3x-ui（脚本复用它的 Xray 内核 `/usr/local/x-ui/bin/xray-linux-amd64`），并且能用 `ssh 名称` 免密登录。

没装面板的话，用 `--xray-bin` 指向任意一份 Xray 可执行文件。

## 安装

```bash
bash scripts/local/install.sh --alias 名称
# 换端口 / 重新生成密码
bash scripts/local/install.sh --alias 名称 --http-port 20126 --socks-port 59357
bash scripts/local/install.sh --alias 名称 --rotate
```

脚本会：

- 生成用户名（`pxy` + 13 位）和密码（24 位），写入 `/etc/auth-proxy/proxy.json`（600）
- 装 `auth-proxy.service`，`enable` 开机自启，重启后自动恢复
- UFW 放行这两个端口（服务商有安全组的话，后台也要放行）
- 把「HTTP / SOCKS5 代理」一段写进本机 `~/Desktop/我的服务器-名称-订阅和账号.md`（用标记包起来，重跑只替换这一段）

重复执行是安全的：已有配置会沿用原来的端口和凭据，加 `--rotate` 才换密码。

## 验收

```bash
bash scripts/local/verify.sh --alias 名称
```

六项要全 PASS：HTTP 出口是这台服务器、匿名访问 407、内网被拦、SOCKS5 出口正确、境外站点可访问。

服务器上也能自查（脚本从标准输入送过去，不用先在服务器上留文件）：

```bash
ssh 名称 'python3 - verify' < scripts/server/auth_proxy.py
```

## 交付

告诉用户：

- 文档在哪（让他自己打开，不要念出账号密码）；
- 浏览器里选 **HTTP** 那一组，IP / 端口 / 用户名 / 密码照抄；
- 这个代理是**固定出口**，和节点订阅无关：节点挂了它照样能用，反过来也一样；
- 服务商后台的安全组要放行同样端口，否则外面连不上。

## 维护

- 换密码：`install.sh --alias 名称 --rotate`，然后重新导入文档里的新凭据。
- 卸载：服务器上 `python3 auth_proxy.py uninstall`（配置文件和服务一起删；防火墙规则保留，自己 `ufw delete`）。
- 重新生成登录信息文档会覆盖这一段，重跑 `install.sh` 补回。
