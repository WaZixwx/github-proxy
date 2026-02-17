# GitHub Cloudflare 全自动加速工具

一个基于 **Cloudflare Workers + 本地 Python 脚本** 的 GitHub Git 操作全自动加速工具，跨平台适配 Windows/macOS/Linux，无需修改 hosts，无需管理员权限，一键配置即可享受 GitHub clone/pull/push 加速。

⚠️ **重要提醒**：本工具仅作用于 **Git 命令操作**（clone/pull/push/fetch），**不支持 GitHub 网页加速**（网页代理仅作演示，存在非常多的功能限制）。

---

## 功能特性

- **Git 操作加速**：通过 Cloudflare 全球边缘节点中转 GitHub 请求，显著提升 clone/pull/push 速度
- **跨平台适配**：完美支持 Windows/macOS/Linux 及所有 Unix-like 系统
- **一键配置**：自动配置 Git `insteadOf` 规则，无需手动修改命令
- **凭证自动管理**：自动配置系统原生 Git 凭证助手，一次输入 Token 永久保存
- **开机自启**：支持一键添加/取消开机自启，重启电脑自动生效
- **实时状态栏**：可选常驻终端的网速/延迟监控栏，直观查看加速效果
- **灵活清理**：支持单独清理加速规则/凭证/配置，或一键重置所有
- **零第三方依赖**：仅使用 Python 标准库，开箱即用

---

## 快速开始

### 前置要求

- 已安装 Git 并添加到系统环境变量（PATH）
- 已安装 Python 3.6 或更高版本
- 一个 Cloudflare 账号（免费版即可）

### 1. 部署 Cloudflare Workers

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 **Workers & Pages** → **Create application** → **Create Worker**
3. 给 Worker 命名（如 `github-proxy`），点击 **Deploy**
4. 部署成功后，点击 **Edit code**，将本仓库的 {insert\_element\_0\_YHdvcmtlcnMuanNg} 代码完整粘贴到左侧编辑器
5. 点击 **Save and deploy**，记录下 Worker 访问域名（如 `https://github-proxy.your-name.workers.dev`）
6. （可选）绑定自定义域：在 Worker 设置 → **Triggers** → **Custom Domains** 中添加你的自定义域（如 `github.proxy.example.com`）

### 2. 运行本地配置脚本

1. 下载本仓库的 `github_cf_proxy.py` 到本地任意目录
2. 打开终端（Windows 用 PowerShell/Git Bash，macOS/Linux 用 Terminal）
3. 进入脚本所在目录，执行：
    ```Bash
    python github_cf_proxy.py
    ```
4.  选择 1. 配置 / 更新加速规则，输入你的 Cloudflare Worker 域名（如 https://github-proxy.your-name.workers.dev）。
5.  等待配置完成，脚本会自动配置加速规则和 Git 凭证。

## 3. 验证加速效果

在终端执行：
```Bash
git ls-remote https://github.com/octocat/Hello-World.git
```
如果能正常返回 commit 哈希列表，说明加速配置成功！

---

## 详细教程

### Cloudflare Workers 部署详解

1. **创建 Worker**：

    - 登录 Cloudflare 后，进入 Workers & Pages 页面

    - 点击「Create application」→「Create Worker」

    - 输入 Worker 名称，点击「Deploy」（先不用改代码）

2. **粘贴 Worker 代码**：

    - 部署成功后，点击「Edit code」

    - 将本仓库 `worker/worker.js` 的代码完整复制到左侧编辑器

    - 点击「Save and deploy」

3. **绑定自定义域（推荐）**：

    - 进入 Worker 设置 →「Triggers」→「Custom Domains」

    - 点击「Add custom domain」，输入你的自定义域（如 `github-proxy.example.com`）

    - 等待 DNS 解析生效（通常几分钟内）

### 本地脚本使用详解

#### 主菜单选项说明

|选项|功能|说明|
|---|---|---|
|1|配置/更新加速规则|首次运行或更换 Worker 域名时使用|
|2|测试加速效果|验证 Git 连接是否正常，无需克隆完整仓库|
|3|管理开机自启|一键添加/取消开机自启，重启电脑自动配置|
|4|清理选项|单独清理加速规则/Git 凭证/脚本配置|
|5|一键重置所有|清除所有配置，恢复初始状态|
|6|显示/隐藏实时网速状态栏|开启后常驻终端显示加速状态/网速/延迟|
|7|退出|退出工具|
#### Git 凭证配置

- 首次使用 Git 推送/拉取时，输入 GitHub 用户名和 **Personal Access Token**（不是密码）

- Token 获取：GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)

- 脚本会自动配置系统原生凭证，后续无需重复输入

#### 实时状态栏说明

- 开启后，终端顶部会显示：`[加速状态] | [实时速率] | [节点延迟] | [自启状态]`

- 状态栏刷新间隔为 2 秒，测速仅下载 10KB 以内的小文件，无流量负担

- 关闭终端后状态栏消失，但不影响加速功能

---

## 常见问题

### Q: 浏览器访问 GitHub 网页能加速吗？

A: **不能**。本工具仅作用于 Git 命令操作，浏览器访问 GitHub 网页需要额外配置系统代理/浏览器代理插件（与本工具不冲突）。

### Q: Git 操作一直超时怎么办？

A: 1. 检查 Cloudflare Worker 是否正常运行；2. 确认 Worker 域名输入正确；3. 更换本地 DNS 为 `1.1.1.1` 或 `223.5.5.5`；4. 尝试更换 Worker 二级域名。

### Q: 如何取消加速？

A: 运行脚本，选择「4. 清理选项」→「1. 仅清理加速规则」，或选择「5. 一键重置所有」。

### Q: 需要一直开着终端吗？

A: **不需要**。只要完成一次「配置加速规则」，即使关闭终端、重启电脑，加速功能依然生效。仅实时状态栏需要终端保持打开。

### Q: 支持 GitHub LFS 吗？

A: 支持。本工具通过 Git 原生规则加速，LFS 操作会自动走代理。

---

## ⚠️ GitHub Token 权限安全警告
> **核心声明**：本加速脚本本身不会收集、上传、泄露你的 Token 及任何敏感数据，所有凭证仅加密存储在你的本地设备中；以下警告仅针对「Token 全权限勾选」本身的安全风险，与脚本功能无关。

### 一、核心风险警告
1. **全权限勾选会大幅提升泄露后的危害范围**
   你勾选了 Token 的全部权限，意味着该 Token 不仅能操作你的代码仓库，还拥有**组织管理、仓库删除、用户设置修改、GitHub Packages 操作、SSH 密钥管理**等高风险权限。一旦 Token 意外泄露，攻击者可完全接管你的 GitHub 账号及所有关联资源。
2. **不符合最小权限安全原则**
   本加速脚本仅用于 Git 的 `clone/pull/push/fetch` 基础操作，仅需 `repo` 基础权限即可完全满足需求，额外勾选的所有权限均为非必要权限，属于过度授权。
3. **永久有效期会放大长期风险**
   若你同时设置了 Token 为「永不过期」，一旦泄露，在你手动撤销前，该 Token 会长期保持有效，风险持续存在。

### 二、安全整改建议
| 操作项 | 具体执行步骤 | 安全收益 |
|--------|--------------|----------|
| 缩减 Token 权限 | 1. 进入 GitHub Tokens (classic) 页面<br>2. 撤销当前全权限的 Token<br>3. 重新生成 Token，仅勾选 `repo` 权限（公开仓库可仅勾选 `repo:public_repo`） | 大幅缩小泄露后的危害范围，仅保留脚本必需的仓库读写权限 |
| 设置 Token 有效期 | 重新生成 Token 时，建议设置 30/90/180 天的有限有效期，避免永久有效 | 即使意外泄露，到期后 Token 自动失效，降低长期风险 |
| 定期轮换 Token | 每 3-6 个月重新生成一次 Token，同步更新本地 Git 凭证 | 即使有未发现的泄露，也能快速切断风险 |

### 三、应急处理方案
若你怀疑 Token 已泄露、或设备被他人访问，请立即执行以下操作：
1. 进入 GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 找到当前使用的 Token，点击 **Revoke** 立即撤销该 Token，使其永久失效
3. 重新生成仅勾选 `repo` 权限的新 Token，更新本地 Git 凭证
4. 检查你的 GitHub 仓库、组织、设置是否有异常操作，如有异常立即联系 GitHub 官方支持


### 四、补充安全说明
- 本地凭证安全：Windows 系统凭证存储在「凭据管理器」、macOS 存储在「钥匙串」、Linux 存储在 `~/.git-credentials`，均为系统级加密存储，仅本机可访问
- 传输安全：Git 操作时 Token 仅通过 HTTPS 加密链路直接传输给 GitHub 官方服务器，Cloudflare Worker 仅做流量中转，不会读取、存储你的 Token
- 脚本安全：本脚本所有代码均为开源可见，无任何数据外发、敏感信息收集的逻辑，仅执行本地 Git 配置命令

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

- 提交 Issue 前请先搜索是否已有相关问题

- 提交 Pull Request 前请确保代码符合项目风格，无第三方依赖

---

## 许可证

本项目采用 [MIT 许可证](LICENSE)，可自由使用、修改和分发。

---

## 免责声明

本工具仅供学习和个人使用，请勿用于非法用途。使用本工具造成的任何后果由使用者自行承担。

## End

- 2026/02/17 WaZixwx [intrduce.wazixwx.com] [wazixwx@wazixwx.com]