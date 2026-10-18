# vps-stack

把一台刚买的 VPS，从空白系统配置成一整套自用代理服务。全部由脚本完成，AI 按 `skills/vps-stack/SKILL.md` 一步步执行。

## 配好之后你有什么

- **一条自己的线路**：电脑、手机、路由器都能用。主、备两个节点，主力连不上时在客户端里手动切到备用。
- **导入就能用**：常用网站和 AI 工具的分流规则已经配好，国内网站自动直连，不用自己写规则。
- **CLIProxyAPI**：自己的 API 接口和管理后台，会自动更新到最新版。
- **浏览器代理**：一个带用户名密码的 HTTP / SOCKS5 出口，给指纹浏览器、多开浏览器用（默认安装）。
- **安全**：服务器只能用你电脑上的密钥登录；用正规 HTTPS 证书，打开不会报"不安全"。
- **基本不用管**：证书、规则、CLIProxyAPI 自动更新，配置每天自动备份。

## 怎么用

把下面这段话连同服务器信息发给 AI（Claude Code、Codex 等支持 skill 的工具都行）：

```text
请按「vps-stack」方案配置我新买的服务器。
方案地址：https://github.com/bohaibo/vps-stack
请先把这个项目下载到本机，完整阅读 skills/vps-stack/SKILL.md，
严格按里面的步骤和规则，用项目里的脚本完成部署和验收。
我的服务器：
- IP：
- 登录方式：初始密码（请让我在终端里自己输入）
- SSH 用户名和端口：默认
- 以后想用这个名字登录：bo
- 节点名称前缀（两个节点在客户端里显示为「前缀-main」「前缀-backup」）：
```

剩下的它会问你要、跑脚本、验收，最后把登录信息写成一份文件放在桌面。

## 它会做什么

| 阶段 | 内容 | 端口 |
| --- | --- | --- |
| connect | 生成密钥、写入 `ssh 名称`、验证免密登录 | 22 |
| base | 时区、BBR + fq、UFW、关闭 SSH 密码登录 | 22 |
| cert | Let's Encrypt **IP 证书**、6 小时续期、Nginx | 80 / 443 |
| xui | 3x-ui v3.8.5 + Xray v26.7.28，Reality 443 + TLS 2443，两套订阅身份 | 443 / 2443 / 53998 |
| sub | 规则镜像 + 订阅中间层（按网卡流量显示用量） | 2096 |
| cliproxy | CLIProxyAPI + 管理中心，30 分钟自动更新 | 8318 |
| maint | 规则每日刷新、配置每日备份（保留 7 份） | — |
| proxy | 独立的 HTTP / SOCKS5 认证代理（默认安装） | 20126 / 59357 |
| verify | 全量验收，`--full` 额外做一次证书续期演练 | — |

## 安全提醒

- 这是**带认证的公网服务**，端口别用 80 / 443 / 8080 这类会被全网扫的端口。
- 代理的私网拦截不要关，否则等于把服务器内网交给任何拿到凭据的人。
- 怀疑泄露：节点在面板里换订阅 ID，浏览器代理用 `proxy --rotate` 换密码。

## 目录

```
skills/vps-stack/
  SKILL.md                         # 操作手册（AI 读这个）
  scripts/local/connect.sh         # 本机：密钥 / 密码 → ssh 名称
  scripts/local/remote.sh          # 本机：上传并执行某个阶段
  scripts/server/vps-stack.py      # 服务器端：init / base / cert / xui / sub / cliproxy / maint / proxy / verify / backup / export
  scripts/server/auth_proxy.py     # 服务器端：浏览器代理的 install / show / verify / uninstall
  scripts/server/files/            # 订阅模板、规则源、刷新脚本等
  references/design.md             # 为什么这样设计
  references/troubleshooting.md    # 出错怎么修
```

## 要求

- 服务器：Ubuntu 22.04+ / Debian 12+，1 GB 内存起（建议 2 GB）。
- 本机：`bash`、`ssh`（OpenSSH 8.4+）、`unzip`。Windows 用 WSL 或 Git Bash。
- 服务商后台的安全组要放行：22、80、443、2443、2096、8318、53998、20126、59357。

## 不含

- 不提供上游账号或 API Key（CLIProxyAPI 装好是空的，自己加）。
- 不包含任何服务器地址、账号、密钥——全部运行时生成。
- 不做 Hysteria2 等 UDP 协议、域名、CDN。
- 3x-ui / Xray 不自动升级（新版内核会让 Shadowrocket 连不上）。

## 许可

MIT。部署流程部分基于开源项目改写，原版权声明保留在 [LICENSE](LICENSE) 中。
