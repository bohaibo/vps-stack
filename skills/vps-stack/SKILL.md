---
name: vps-stack
description: 把一台全新的 Debian / Ubuntu VPS 从零配置成自用代理栈：ssh 名称免密登录、3x-ui（Reality 443 + TLS 2443）、Clash / Shadowrocket 订阅与 AI 分流、Let's Encrypt IP 证书自动续期、CLIProxyAPI 与 30 分钟自动更新、可选的浏览器 HTTP / SOCKS5 认证代理、SSH/防火墙加固、每日备份与验收。用户只需提供服务器 IP、SSH 登录方式和想用的 ssh 名称。Use when the user asks to 配置服务器、部署 VPS、搭节点、装 3x-ui、装 CLIProxyAPI、新买的搬瓦工/DMIT 配一下、以后 ssh xxx 能登录、给服务器加个带账号密码的代理、指纹浏览器代理，or to re-check / repair / extend a server set up this way.
---

# VPS 代理栈

把用户刚买的一台 VPS，配置成一整套自用代理服务：节点订阅 + AI 接口网关 + 可选的多开浏览器代理。

全部动作由本目录的脚本完成，你负责：问清楚信息、按顺序运行脚本、读懂报错并修复、最后把结果交给用户。

每一部分为什么这样设计，见 [references/design.md](references/design.md)；出错时先查 [references/troubleshooting.md](references/troubleshooting.md)。

## 用户通常只发来一段话

常见开场是"请按这套方案配置我新买的服务器，方案地址是 <仓库地址>，先下载项目，读 skills/vps-stack/SKILL.md，严格按里面的步骤用脚本完成部署和验收"，后面跟着 IP、登录方式、ssh 名称。

遇到这种消息，直接照本文件往下走：**不要**再问一遍已经给了的信息，也**不要**让用户自己跑脚本。

## 语言

用户用什么语言和你说话，你就全程用那种语言交流（问问题、报进度、交付说明都是）。本文件里的中文模板，按用户的语言转述即可。

保存登录信息时用 `--lang` 生成对应语言的文件：中文 `zh`（默认）、English `en`、한국어 `ko`、日本語 `ja`、العربية `ar`、Español `es`、Français `fr`、Русский `ru`、Deutsch `de`、Português `pt`；其他语言用 `en`。脚本自己的终端输出是中文，你转述给用户就行。

## 必须遵守

1. **只操作用户这次给的这台服务器。** 不登录、不读取、不修改任何其他服务器；`~/.ssh/config` 里已有的条目一律不动。
2. **不在对话里显示任何秘密。** 密码、私钥、面板密码、订阅地址、CLIProxyAPI Key、代理的用户名密码都不要打印、复述或写进命令参数。脚本已经避免输出它们；登录信息只通过 `remote.sh save` 写进本机文件，你只告诉用户文件路径。
3. **每台服务器独立生成凭据。** 不复制别的服务器的数据库、UUID、Reality 密钥、订阅路径或 Key。
4. **证书必须是 Let's Encrypt 签发、浏览器信任的 IP 证书。** 申请失败就停下来解决（通常是服务商安全组没放行 TCP 80），绝不改用自签名证书继续。
5. **不改脚本里固定的版本**（3x-ui v3.8.5、Xray v26.7.28）。新版 Xray 会让 Shadowrocket 连不上，换版本必须先在测试机上用真实客户端验证。
6. 脚本报错时，按提示修复原因后**重跑同一个阶段**。每个阶段都可以重复执行，不要手工绕过检查，也不要删掉服务器重装来"解决"普通问题。

## 第一步：问用户要信息

用户常常是复制 README 里的那段话来的，消息里已经写了 IP、登录方式、名称。**已经给了的不要再问**，只补问缺的必填项；"默认"表示 root / 22；可选项没写就用默认值。缺信息时用一条消息问齐，不要一项一项追问：

```text
请告诉我这几项（服务商后台都能看到）：
1. 服务器 IP：
2. 登录方式：初始密码，或者密钥文件在电脑上的路径（zip 也可以）
3. SSH 用户名和端口：不知道就写"默认"（root / 22）
4. 以后想用什么名字登录：比如 bwg，以后输入 ssh bwg 就能进服务器

可选：
5. 机房在哪个城市（用来设时区，不填我按服务商机房判断）
6. 每月流量额度和重置日（只用于在客户端显示用量；不填默认 1000G，重置日按开通日自动推算）
7. 要不要顺便加一个浏览器代理（指纹浏览器 / 多开浏览器填 HTTP 或 SOCKS5 那种）
```

**密码的处理：**

- 最好让用户自己在终端输入：让用户在自己的终端运行 `! bash <本skill目录>/scripts/local/connect.sh --alias 名称 --host IP --password-prompt`，密码不会进入对话。
- 如果用户已经把密码发在对话里：先把它写进一个只有本人可读的临时文件，再用 `--password-file`；脚本用完会自动删除该文件。不要把密码直接写在 `connect.sh` 的命令行参数里。

  ```bash
  umask 077; d=$(mktemp -d); printf '%s' '用户给的密码' > "$d/pw"; echo "$d/pw"
  ```

- 部署完成后服务器会关闭密码登录，这个密码就不能再用来 SSH 了。提醒用户：服务商后台的 VNC/救援控制台仍可能用它，建议在后台改掉。

**时区：** 按机房所在地设置，不要只看 IP 地理库。常见：洛杉矶/圣何塞/美西 `America/Los_Angeles`，纽约/美东 `America/New_York`，底特律 `America/Detroit`，香港 `Asia/Hong_Kong`，东京 `Asia/Tokyo`，新加坡 `Asia/Singapore`，法兰克福 `Europe/Berlin`，伦敦 `Europe/London`。搬瓦工和 DMIT 的美国机房多数在洛杉矶。实在判断不了用 `Etc/UTC`，并告诉用户。

**ssh 名称：** 只能用字母、数字、连字符，字母开头。如果 `ssh -G 名称` 显示它已经指向别的服务器，请用户换一个。

## 第二步：建立 `ssh 名称` 免密登录

本目录记为 `$SKILL`（本 SKILL.md 所在目录；从下载的项目里读到本文件时，就是 `项目目录/skills/vps-stack`）。本机需要 `bash`、`ssh`（OpenSSH 8.4+）、`unzip`。Windows 用 WSL 或 Git Bash。

```bash
# 密钥文件（OpenSSH 私钥或服务商给的 zip）
bash "$SKILL/scripts/local/connect.sh" --alias 名称 --host IP --port 端口 --user 用户名 --key 密钥路径

# 初始密码（密码文件用完自动删除）
bash "$SKILL/scripts/local/connect.sh" --alias 名称 --host IP --port 端口 --user 用户名 --password-file 文件路径
```

脚本会：把密钥放进 `~/.ssh/vps-stack/名称/`（用密码时新生成一把 ED25519 密钥并写入服务器）、在 `~/.ssh/config` 最前面加一个 Host 段（先备份原文件）、验证 `ssh 名称` 能免密登录。

macOS 如果提示读不到"下载"文件夹里的文件，请用户把文件拖到桌面再给你路径。

## 第三步：部署

```bash
R="$SKILL/scripts/local/remote.sh"
bash "$R" 名称 upload
bash "$R" 名称 init --ip IP --alias 名称 --timezone 时区 [--quota-gb 1000 --reset-day 1]
bash "$R" 名称 base       # 时区、依赖、BBR、防火墙、关闭 SSH 密码登录
bash "$R" 名称 cert       # Let's Encrypt IP 证书 + 6 小时续期 + Nginx
bash "$R" 名称 xui        # 3x-ui、固定 Xray、Reality 443、TLS 2443、两套订阅身份
bash "$R" 名称 sub        # 规则镜像、订阅中间层、订阅检查
bash "$R" 名称 cliproxy   # CLIProxyAPI + Management Center
bash "$R" 名称 maint      # CLIProxyAPI 自动更新、规则每日刷新、每日备份
bash "$R" 名称 verify --full
```

- 逐个阶段跑，每跑完一个用一句话告诉用户进度（例如"证书已签发，开始装 3x-ui"）。
- `init` 会核对这台机器的公网 IP 是否就是用户给的 IP，并拒绝覆盖不是本工具创建的 3x-ui；遇到这两种情况先问用户，不要强行继续。
- 只支持 Ubuntu 22.04+ / Debian 12+。其他系统请用户在服务商后台重装为 Ubuntu 24.04 LTS。
- 某阶段失败：读 `停止：` 后面的原因，对照 troubleshooting 修复，再重跑这个阶段。

| 阶段 | 装了什么 | 端口 |
| --- | --- | --- |
| base | BBR + fq、UFW、sshd 只认密钥 | 22 |
| cert | Let's Encrypt IP 证书、Nginx | 80 / 443 |
| xui | 3x-ui + 固定 Xray，两个节点两套身份 | 443 / 2443 / 53998 |
| sub | 规则镜像 + 订阅中间层 | 2096 |
| cliproxy | CLIProxyAPI + 管理中心 | 8318 |
| maint | 自动更新、规则刷新、每日备份 | — |

## 可选：浏览器代理

指纹浏览器、多开浏览器通常只支持填一个 HTTP / SOCKS5 代理加用户名密码，不吃订阅。用户提到比特浏览器、AdsPower、多开窗口、浏览器代理时，在 `maint` 之后加一步：

```bash
bash "$R" 名称 proxy            # 默认 HTTP 20126 / SOCKS5 59357
bash "$R" 名称 proxy --rotate   # 换一对新的用户名密码
bash "$R" 名称 proxy --check    # 只做只读检查
```

- 这是**独立于面板**的一个 Xray 实例，面板重装、升级都不影响它；服务名 `vps-stack-proxy`。
- 凭据每台服务器独立随机生成，写进 `/etc/vps-stack/proxy.json`（600），终端不显示；`save` 时会自动出现在登录信息文件里。
- 出站固定 IPv4，私网地址和 BT 协议一律拒绝，避免被当成内网跳板或下载机。
- 端口被占用时换一对（`--http-port 20226 --socks-port 59457`），并告诉用户改了什么。
- 别忘了服务商后台的安全组也要放行这两个端口。

## 第四步：交付

1. `verify --full` 必须全部 PASS。有 FAIL 就先修，修不了就如实告诉用户哪一项没通过、影响是什么。
2. 保存登录信息到本机（不会显示在终端）：

   ```bash
   bash "$R" 名称 save --lang zh   # → 桌面「我的服务器-名称-订阅和账号.md」；其他语言是「my-server-名称-subscriptions-and-accounts-语言.md」
   ```

3. 从用户这台电脑测一下能不能连到服务器（返回 404 表示连通、证书正常）：

   ```bash
   curl -sS -o /dev/null -w '%{http_code}\n' --max-time 10 https://IP:2096/
   ```

   超时说明用户当前网络到这个 IP 不通，见 troubleshooting 的"国内连不上"。

4. 用简短的话告诉用户：
   - 以后用 `ssh 名称` 登录；
   - 登录信息文件的路径（让用户自己打开，你不要读出来）；
   - 电脑装 Clash Verge Rev，导入文件里的 **Clash 订阅**，选"规则"模式并打开"虚拟网卡模式"（TUN，第一次按提示安装服务；只开系统代理时，浏览器的 WebRTC 会暴露真实 IP）；iPhone 用 Shadowrocket 导入 **Shadowrocket 订阅**；路由器 OpenClash 用 Clash 订阅；
   - CLIProxyAPI 现在是空的，要在管理中心添加自己的上游账号或供应商 Key；
   - 加了浏览器代理的话，浏览器里选 **HTTP** 那一组，IP / 端口 / 用户名 / 密码照抄；这个代理是固定出口，和节点订阅无关，节点挂了它照样能用；
   - 导入后打开 <https://ip.net.coffee/claude/>，显示服务器的 IP 就说明通了；要出差的话，出发前在手机和电脑上都测一遍。

## 以后的复核和维护

用户说"帮我检查一下 名称 这台服务器"时：先 `bash "$R" 名称 upload`，再 `bash "$R" 名称 verify --full`，只读复核，有问题再按对应阶段修。

- CLIProxyAPI 和管理中心每 30 分钟自动检查新版：SHA-256 校验 → 等到没有在途请求的空闲时刻（最多推迟 24 小时）→ 原子替换并重启（约 1 秒）→ 健康检查 → 失败自动回滚，同一坏版本 24 小时内不重试。日志：`journalctl -u cliproxy-auto-update`。
- 3x-ui 和 Xray **不自动升级**。
- 用户说检测网站提示 **WebRTC 泄露**、显示国内 IP：这是客户端只开了系统代理造成的，服务器和订阅都不用改，改用虚拟网卡模式即可，详见 troubleshooting 的客户端一节。
- 服务器上的工具副本在 `/opt/vps-stack/tool/`，命令 `vps-stack verify` / `vps-stack backup` / `vps-stack proxy --check` 可直接在服务器上运行。
- 更新项目后想让老服务器用上新规则：`upload` 之后重跑 `sub`，节点不断线。
