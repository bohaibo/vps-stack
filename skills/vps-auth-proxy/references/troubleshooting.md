# 常见问题与修复

先看脚本 `停止：` 后面的原因，再对照这里。修好后重跑同一条命令。

## install

**找不到 Xray 内核**

```
找不到 Xray 内核：/usr/local/x-ui/bin/xray-linux-amd64
```

这台机器还没装 3x-ui 面板。先装面板，或用 `--xray-bin` 指向已有的 Xray 可执行文件。

**端口被占用**

```
20126 没有在监听
```

`ss -lntp | grep 20126` 看是谁占的。换一对端口重跑：`--http-port 20226 --socks-port 59457`。

**服务起不来**

`journalctl -u auth-proxy -n 30`。常见原因：

- 配置文件 JSON 语法坏了（手工改过的话）；
- 端口小于 1024 但服务不是 root 跑的（本方案以 root 运行，一般不会）；
- Xray 路径变了（升级 3x-ui 后重新指定 `--xray-bin`）。

**`ProtectSystem=strict` 导致起不来**

本方案只允许写 `/tmp`。如果改过配置路径，把新路径加进单元的 `ReadWritePaths`。

## 外面连不上

按顺序排：

1. 服务器本机通不通：`ssh 名称 'curl -sS -x http://账号:密码@127.0.0.1:20126 https://api.ipify.org'`。
2. UFW：`ufw status | grep 20126`。
3. **服务商后台的安全组**——最常见，UFW 放行了但云厂商安全组没放行，外面照样超时。
4. 本机网络到服务器通不通：`nc -z -w5 IP 20126`，超时说明线路本身不通。

## 认证相关

**407 Proxy Authentication Required**

浏览器里用户名或密码填错了，或者文档里的密码已经 `--rotate` 换过。重新从文档里抄一遍。

**浏览器一直弹认证框**

密码里有特殊字符时，某些客户端要手动转义；建议直接用 `--rotate` 生成新的（只含字母数字）。

## 安全问题

**怀疑凭据泄露**

`install.sh --alias 名称 --rotate` 立刻换密码，旧密码立即失效。同时在服务商后台看流量有没有异常。

**想彻底停掉**

服务器上 `python3 auth_proxy.py uninstall`。防火墙规则会保留，需要的话 `ufw delete allow 20126/tcp`。

## 文档

**重新生成登录信息后，代理那一段没了**

文档被整体重写时会覆盖这一段。重跑 `install.sh` 补回——它会替换标记之间的内容，不动其他段落。

**文档里 IP 是占位符**

`install.sh` 取不到 ssh 配置里的地址时（比如用了跳板机），会写 `<服务器IP>`。用 `--ip 真实地址` 重跑。
