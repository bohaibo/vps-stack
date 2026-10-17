# vps-auth-proxy

在已经装好 3x-ui / Xray 的服务器上，加一套给**指纹浏览器 / 多开浏览器**用的代理。

一个独立 Xray 实例，同时提供：

| 协议 | 默认端口 | 认证 |
| --- | ---: | --- |
| HTTP | 20126 | 用户名 + 密码 |
| SOCKS5 | 59357 | 用户名 + 密码 |

## 为什么单独开一个实例

- **不受面板影响**：3x-ui 改配置、重装、升级 Xray 内核都不会动它；它也不出现在面板入站列表里，不会被误删。
- **只做一件事**：固定 IPv4 出口，私网地址和 BT 协议直接拒绝，防止被当成内网跳板或下载机。
- **凭据独立**：每台服务器随机生成，和订阅、面板的凭据互不相干。

## 用法

前提：服务器已装 3x-ui，能用 `ssh 名称` 免密登录。

```bash
# 安装（默认 20126 / 59357）
bash skills/vps-auth-proxy/scripts/local/install.sh --alias myserver

# 验收：出口 IP、认证、内网拦截、两个协议
bash skills/vps-auth-proxy/scripts/local/verify.sh --alias myserver
```

装完凭据会写进本机的 `~/Desktop/我的服务器-名称-订阅和账号.md`，段落用注释标记包着，
重跑只替换这一段，不会动文档里其他内容。

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--alias` | 必填，ssh 名称 |
| `--http-port` / `--socks-port` | 换端口（被占用时用） |
| `--rotate` | 重新生成用户名密码 |
| `--lang zh\|en` | 写进文档的语言 |
| `--doc 路径` | 文档放在别处时指定 |
| `--xray-bin 路径` | 不用面板自带的 Xray 时指定 |

## 安全提醒

这是一个**带认证的公网代理**。被拿去扫号、发垃圾，连累的是这台服务器的 IP。所以：

- 端口别用 80 / 443 / 8080 这类会被全网扫的端口；
- 不要关掉私网拦截，否则代理能访问服务器自己的内网和面板；
- 怀疑泄露就 `--rotate` 换密码，或者直接 `uninstall`。

## 目录

```
skills/vps-auth-proxy/
  SKILL.md                      # 给智能体看的操作手册
  scripts/local/install.sh      # 本机入口：装 + 更新文档
  scripts/local/verify.sh       # 本机入口：从外面测
  scripts/server/auth_proxy.py  # 服务器端：install / show / verify / uninstall
  references/design.md          # 为什么这样设计
  references/troubleshooting.md
```

## 不含

- 不安装任何浏览器，也不改浏览器配置；
- 不提供订阅、节点、面板功能；
- 不包含任何服务器地址、账号、密钥——全部运行时生成。
