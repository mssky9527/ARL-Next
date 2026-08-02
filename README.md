<div align="center">

  # ARL-Next
  **AI 原生自动化资产侦察与漏洞监控平台**

  *Next-Generation AI-Native Asset Reconnaissance & Vulnerability Monitoring Platform*

  <p>
    <a href="https://github.com/owl234/ARL-Next/releases"><img src="https://img.shields.io/github/v/release/owl234/ARL-Next?style=flat-square&color=blue" alt="Release"></a>
    <a href="https://github.com/owl234/ARL-Next/stargazers"><img src="https://img.shields.io/github/stars/owl234/ARL-Next?style=flat-square" alt="Stars"></a>
    <a href="https://github.com/owl234/ARL-Next/blob/main/LICENSE"><img src="https://img.shields.io/github/license/owl234/ARL-Next?style=flat-square" alt="License"></a>
  </p>

  <p>
    <a href="https://hub.docker.com/"><img src="https://img.shields.io/badge/docker-ready-blue.svg?style=flat-square&logo=docker" alt="Docker"></a>
    <img src="https://img.shields.io/badge/python-3.13%2B-blue?style=flat-square&logo=python" alt="Python">
    <img src="https://img.shields.io/badge/node.js-18%2B-green?style=flat-square&logo=node.js" alt="Node.js">
    <img src="https://img.shields.io/badge/vue-3.x-4fc08d?style=flat-square&logo=vuedotjs" alt="Vue">
    <img src="https://img.shields.io/badge/MCP-Ready-purple?style=flat-square" alt="MCP">
  </p>
</div>

<br/>

---

## 💡 什么是 ARL-Next？

> **ARL-Next** 是 ARL (资产侦察灯塔) 的现代化重构版本。现已进化为 **AI 原生、高性能、全维度闭环的安全监控平台**。

### ✨ 核心特性

* **🤖 AI 原生**：内置 MCP 接口，允许 AI Agent 直接对话接管系统。（👉 [MCP 配置指南](./mcp-server/README.md)）
* **🚀 极速架构**：升级 Chromium 与 Nuclei。耗时任务全面剥离为微服务，根除高并发假死。
* **🌐 资产闭环**：集成 ICP 与天眼查，全自动挖掘企业多维资产。
* **🛡️ 威胁情报**：内置 GitHub 监控雷达，实时追踪最新 CVE 与代码泄露。
* **⚡ 极简运维**：提供 2 分钟极速部署包，支持 Web 端平滑热更新与 Basic Auth 前置防御。
* **🇨🇳 国内特化**：针对国内网络深度优化，直连阿里云预构建镜像，彻底根绝 GFW 阻断与依赖下载失败问题。

<details>
<summary><b>🤔 对比原版 ARL 解决了哪些痛点？</b></summary>

1. **解决任务假死**：高耗能截图与 OSINT 独立成微服务集群，主节点不再阻塞。
2. **告别编译与臃肿**：引入 `uv` 极速包管理与 Docker 多阶段构建，彻底剥离底层 C 编译链，镜像体积锐减且杜绝了依赖报错。
3. **重构技术底座**：前端升级 Vue3，后端重写高并发数据库索引，清剿数十项深层 Bug。
4. **增强反爬伪装**：升级特征隐藏机制，大幅降低被 WAF 封禁的概率。
</details>

---

## 📸 界面预览

* **全局仪表盘**：实时展示系统资源消耗、后台任务状态、多维风险统计及最新日志流。
  
  <img src="./img/dashboard1.png" alt="仪表盘" width="800">

<details>
<summary><b>🖼️ 点击展开查看更多核心界面</b></summary>

* **OSINT 资产侦察**：支持 ICP 与天眼查等情报关联检索，一键同步企业多维资产并无缝下发任务。
  
  <img src="./img/enterprise-asset-search1.png" alt="资产侦察" width="800">

* **任务与指纹管理**：支持任务全生命周期追踪、自定义 PoC 组合及全局指纹检索。
  
  <img src="./img/task-new1.png" alt="任务新建" width="800">
  
  <img src="./img/task-management.png" alt="任务管理" width="800">

* **威胁情报雷达**：支持最新 CVE 漏洞追踪与 **GitHub** 代码泄露实时监控。
  
  <img src="./img/threat-intel-radar1.png" alt="威胁情报雷达" width="800">

* **系统设置**：集成 API 热配置、字典云管理、队列并发热扩缩容及告警通道测试。
  
  <img src="./img/system-settings1.png" alt="系统设置" width="800">

</details>

---

## 🏗️ 架构设计

ARL-Next 采用前后端解耦的微服务架构。下面是系统的完整数据流与模块调度图：

```mermaid
graph TD
    User["👨‍💻 安全分析师"] -->|HTTPS + Basic Auth| Nginx["🖥️ Frontend (Nginx / Vue3)"]
    Agent["🤖 AI 大模型"] -.->|MCP 协议| MCP["🤖 MCP Server (AI扩展)"]
    
    Nginx -->|REST API| Backend["⚙️ Backend API (Flask)"]
    MCP -->|工具调用| Backend
    
    Backend <--> DB[("🗄️ MongoDB (资产大宽表)")]
    
    Backend -->|下发任务| MQ(("⚡ RabbitMQ"))
    MQ -->|异步消费| Workers["⚙️ Celery Workers 集群"]
    
    Workers -->|结果落地| DB
    
    Workers --> OSINT["🧩 OSINT 情报微服务"]
    Workers --> Puppeteer["🧩 Puppeteer 截图微服务"]
    Workers --> Nuclei["🔥 Nuclei 扫描与爬虫引擎"]
    Autoheal["🛡️ Autoheal 自愈守护"] -.->|监控探活| Workers
    
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:1px;
    classDef core fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    class Nginx,Backend,Workers core;
```

### 核心模块解析：

1. 🖥️ **展示层 (Frontend)**：基于 **Vue 3.5** + **Vite 5.4** 构建，生产环境由 **Nginx** 托管，提供 HTTPS 安全网关与 **Basic Auth 前置防御**。
2. ⚙️ **业务 API 层 (Backend)**：基于 **Python 3.13+** 与 **Flask**，处理核心业务逻辑与 JWT 鉴权。
3. 🤖 **AI 扩展层 (MCP Server)**：*(新!)* 独立集成 **Model Context Protocol** 服务，赋能外部 AI 大模型/Agent 直接接入并调度底层检索工具。
4. ⚡ **消息与执行层 (Broker & Workers)**：采用 **RabbitMQ** + **Celery** 分布式集群，高效解耦调度 **Nuclei** 扫描与威胁监控等高并发任务。
5. 🗄️ **数据存储 (Database)**：基于 **MongoDB 7.0**，承载千万级大宽表资产数据与漏洞结果落地。
6. 🧩 **扩展微服务群 (Microservices)**：*(新!)* 包含 Node.js Puppeteer 渲染容器与 OSINT 情报容器，专职无头渲染与异步信息收集，彻底消除主节点任务阻塞。

---

## 🚀 部署指南

### 生产部署 (公网单VPS一键部署) ⭐ 推荐

**适用场景**：国内云服务器、企业内网。
**基准耗时**：裸机从零部署约 **13 分钟**；自带 Docker 环境仅需 **2 分钟**。

**核心优势**：
* **⚡ 国内满速**：直连阿里云公开镜像，无惧 GitHub 网络阻断。
* **📦 极简轻量**：免环境配置、免 `docker login`，剔除冗余编译链，镜像减重超 700MB。
* **🛡️ 极致防护**：自动签发 SSL 并强制生成 **Basic Auth 前置拦截**，核心组件全内网隔离。
* **🔄 平滑热更**：支持从 Web 端一键平滑重启升级，彻底免去 SSH 登录。
* **🩺 智能就绪检测**：内置 API 健康轮询机制，确保服务 100% 启动后无缝访问，告别 502 报错。
* **🚀 性能调优**：Nginx 深度定制，强制开启 Gzip 压缩拦截大文件明文传输，带宽消耗锐减，前端秒级响应。

#### 🚀 部署方式选择

**方法一：防阻断一键部署（⭐ 推荐，适用于国内服务器）**

在全新的 Ubuntu/Debian 终端 (需 root 权限) 直接复制执行以下连缀命令。它会自动安装 Docker、从阿里云镜像提取最新部署脚本并一键拉起：

```bash
# 1. 安装基础依赖
apt-get update && apt-get install -y docker.io docker-compose-v2 openssl curl && \
# 2. 创建并进入工作目录
mkdir -p ~/ARL-Next && cd ~/ARL-Next && \
# 3. 从阿里云公开仓库拉取最新镜像
docker pull crpi-laul1izptqrf0tkf.cn-beijing.personal.cr.aliyuncs.com/owl234-arl-prod/arl-web:latest && \
# 4. 核心黑科技：绕过 GFW 网络阻断，直接从镜像中提取全套部署配置
docker rm -f arl-temp 2>/dev/null || true && \
docker create --name arl-temp crpi-laul1izptqrf0tkf.cn-beijing.personal.cr.aliyuncs.com/owl234-arl-prod/arl-web:latest && \
docker cp arl-temp:/code/start-prod.sh ./ && \
docker cp arl-temp:/code/docker-compose.prod.yml ./ && \
docker cp arl-temp:/code/updater ./ && \
docker cp arl-temp:/code/version.txt ./ && \
docker cp arl-temp:/code/frontend ./ && \
docker rm arl-temp && \
# 5. 赋予权限并执行一键安装脚本
chmod +x start-prod.sh && \
bash start-prod.sh
```

**方法二：Github 浅克隆部署（适用于海外服务器 / 需保留源码）**

> [!WARNING]
> 该方法极度依赖对 Github 的网络连通性。如果 `git clone` 卡住，国内机器请务必使用 **方法一** 或手动下载源码 Zip 包上传。

若网络允许，可直接拉取源码运行：

> 💡 **提示**：`start-prod.sh` 内置了全套环境探针。即使是全新的裸机，脚本也会自动检测并安装 Docker 等基础依赖，全程无需人工干预。

```bash
git clone --depth 1 https://github.com/owl234/ARL-Next.git && cd ARL-Next
chmod +x start-prod.sh
bash start-prod.sh
```

---

### 🔑 登录与配置

访问 `https://<你的服务器IP>:5173` 即可登录（首次自签名证书请无视浏览器不安全提示）。

> [!IMPORTANT]
> **默认安全凭据（双重验证）：**
> 1. **首层网关拦截 (Basic Auth)**：弹窗账号 `admin` / 密码 `arl_next`
> 2. **系统业务面板**：系统账号 `admin` / 密码 `arlpass`

> [!TIP]
> **商业证书替换 (可选)**：将您申请的真实 SSL 证书重命名为 `arl.crt` 和 `arl.key` 放至 `ssl-certs/` 目录，然后再次执行 `bash start-prod.sh` 即可。
---

### 开发环境部署 (前端本地 + Docker后端)

- 👥 **适用群体**：二次开发与安全研究者。
- ⚡ **核心优势**：前后端彻底解耦，双端热重载（Hot Reload）极速生效。
- ⚙️ **前置条件**：本地已安装 Docker 与 Node.js (脚本会自动处理 pnpm 依赖)。

#### 🚀 一键启动

```bash
git clone https://github.com/owl234/ARL-Next.git && cd ARL-Next
# 自动在后台拉起后端 Docker 容器，并在前台启动 Vite 前端服务
bash start-dev.sh
```

访问 `http://localhost:5173` 开始开发（默认凭据：`admin` / `arlpass`）。

> [!NOTE]
> **开发指南：**
> * **双端热重载**：后端修改本地代码保存即生效，前端 Vite 实时热重载。
> * **API与安全**：后端接口暴露于 `5001` 端口；若需开启 HTTPS，请将自签证书放至 `certs/` 目录。

---

## 🗄️ 数据库直连 (开发环境专用)

生产环境默认切断了所有底层端口映射以保证安全。开发调试时，可通过以下凭据直连排查：

| 组件名称 | 直连地址 / URI | 账号 | 密码 | 协议/用途 |
| :--- | :--- | :--- | :--- | :--- |
| **🍃 MongoDB** | `mongodb://admin:admin@127.0.0.1:27018/arl?authSource=admin` | `admin` | `admin` | DB 读写直连 |
| **🐇 RabbitMQ** | `http://127.0.0.1:15673` | `admin` | `admin` | Web 管理后台 |
| **🐇 RabbitMQ** | `127.0.0.1:5673` | `admin` | `admin` | AMQP 协议端口 |

---

## ❓ 常见问题 (FAQ)

<details>
<summary><b>Q: 点击 Web 端的“一键系统更新”时，提示 <code>[ERROR]触发更新失败，服务返回异常状态码</code> 怎么办？</b></summary>
<br/>

**A:** 这种情况通常是因为底层的守护进程卡死。请通过 SSH 登录到您的宿主机终端，执行以下命令重启更新服务即可恢复：

```bash
sudo systemctl restart arl-updater.service
```

</details>

---

## 📜 版本更新历史

<details open>
<summary><b>🚀 v1.1.8 (当前版本)</b></summary><br/>

* **架构跃升**：核心运行环境全面跨代至 **Python 3.13** 与 **MongoDB 7.0**。新增 `upgrade-mongo.sh` 自动化脚本，实现数据库大版本的无损平滑迁移。
* **内存治理**：引入极限防 OOM 机制。切换 RabbitMQ 为 Alpine 镜像，限制 MongoDB 最大内存池为 1GB；导出引擎重构为 `$group` 流式处理，彻底杜绝海量资产溢出。
* **CI/CD 重构**：全线引入 Docker 多阶段构建与 `uv` 极速包管理器，大幅缩减镜像体积。补全自动发版流，实现海外预构建镜像后直推国内阿里云私库。
* **稳定与安全**：底层引入 `contextvars` 根治异步任务上下文丢失；修复 `InfoHunter` 外部命令注入隐患；重构适配 `urllib3` 废弃 `get_host` 后的兼容性崩溃。
* **指纹与交互**：扩充 Vite、React、TOS 等现代 Web 指纹，站点监控新增 `body_length` 异动感知。前端新增 CIDR 气泡悬浮组件以优化聚合视图，MCP 新增 `asset_wih` 调度。
</details>

<details>
<summary><b>v1.1.7</b></summary><br/>

* **核心底座**：重构数据库落库机制，全面引入 `bulk_write` 与批量入库，为13张核心资产表增加联合唯一索引，彻底杜绝极端并发下的数据冗余，大幅提升大任务流性能。
* **网络引擎**：重构底层网络请求工具，引入自适应连接池及 10MB 响应截断保护机制，有效防止因恶意站点超大返回包导致的内存泄漏与任务假死。
* **爬虫自愈**：升级浏览器渲染微服务，新增滚动重启（Rolling Restart）与资源防泄漏自愈机制，根除大批量网页截图时可能产生的僵尸进程。
* **安全控制**：系统设置新增对平台 Basic Auth 防护的图形化热切换支持，底层自动重构并重载 Nginx 网关配置。
* **威胁雷达**：重构 Github CVE 与黑客工具监控逻辑，修复时区导致的数据遗漏，全面改用原子级 `upsert` 防竞争锁确保推送不重复。
* **任务调度**：深度重构 WIH 域名的多层级迭代探测逻辑，并增强全线端口扫描、Web 指纹等组件的错误容忍与忙碌重试策略。
* **前端交互**：大幅优化与重构 Dashboard 仪表盘统计、资产搜索、Github 管理、任务详情等多个核心视图页面，带来更优质的信息呈现。
* **UI 修正**：资产站点表格对齐原版经典字段，恢复状态码、标题展示，修复 WIH 来源映射，并修复“添加标签”功能的交互反馈。
* **部署增强**：增加启动环境自动化巡检，自动识别并清理因 Docker 导致错误生成的幽灵 `.htpasswd` 目录以确保服务正常启动。
* **其他杂项**：精简代码库，清理已废弃截图资源，并在开发文档中补充规范了版本推送的消息标准。
</details>

<details>
<summary><b>v1.1.6</b></summary><br/>

* **架构**：Puppeteer 从后台 Worker 中彻底分离为独立的 Node.js HTTP 微服务容器，大幅释放后台调度压力。
* **性能**：重构指纹识别引擎，引入 Aho-Corasick 多模式匹配算法与内存缓存，极速提升 Web 资产扫描效率。
* **爬虫**：优化 URL 去重算法，底层哈希池引入 Set 结构替代 List，将检索复杂度从 O(N²) 降至 O(1)，消除大规模爬取时的 CPU 瓶颈。
* **部署**：支持 Github 浅拉取 (Shallow clone) 部署兼容；启动脚本新增 API 动态健康检测，彻底消除早期 502 报错。
* **修复**：修复了任务列表 (Task List) 与资产侦察 (Asset Recon) 数据展示异常及状态同步问题。
</details>

<details>
<summary><b>v1.1.5</b></summary><br/>

* **架构**：重构 `icp_query` 为独立 `osint_service` 微服务，引入纯异步调度，降低主节点负载。
* **调度**：实现轻重任务队列分离 (FOFA 等轻查询独立)，并在系统设置中支持精细化并发数配置。
* **部署**：自动分配 2G Swap 解决 OOM 崩溃；多阶段构建缩减镜像体积；新增 Autoheal 容器自愈服务，自动监控并重启假死节点。
* **安全**：热更新服务 (`updater.py`) 增设内网白名单拦截机制，阻断公网调用；修复 Nginx 与 SSE 跨域限制。
* **功能**：任务列表新增“模糊/精确/数值”条件过滤及组合导出；核心任务层增加站点防重复插入机制。
</details>

<details>
<summary><b>v1.1.4</b></summary><br/>

* **修复**：补齐策略中缺失的 Host 碰撞配置，确保后台任务能正常联动与下发。
* **修复**：修复全局背景样式，解决长页面滚动时底部可能出现的白边与背景闪烁问题。
* **部署**：全方位重构一键部署与热更新底层健壮性。新增并发防冲突锁、配置文件原子级写入、网络断连自动重试机制；自动清理遗留幽灵容器与磁盘废弃镜像；增加平滑停机时间（60秒）以防产生扫描脏数据；并修复了多项可能导致部署瘫痪的边缘隐患。
* **构建**：升级 GitHub Actions 构建依赖版本。
</details>

<details>
<summary><b>v1.1.3</b></summary><br/>

* **AI原生**：首次引入 MCP (Model Context Protocol) Server，赋能外部 AI 大模型无缝接管资产调度与检索。
* **UI重构**：前端样式系统全面解耦重构，新增动态主题色与自定义背景，打造极客专属工作台。
* **安全**：生产环境 Nginx 全面启用 Basic Auth 强制前置拦截，容器启动自动生成强密码凭证，实现极致防护。
* **功能**：新增全局资产指纹细粒度检索功能，支持在全系统中穿透式定位目标站点。
</details>

<details>
<summary><b>v1.1.2</b></summary><br/>

* **核心**：新增系统一键升级机制，支持平滑热更新。
* **组件**：Nuclei 扫描引擎升级至 v3.11.0。
* **前端**：极致性能优化，修复 Auth 拦截器等验证问题。
</details>

<details>
<summary><b>v1.1.1</b></summary><br/>

* **资产**：资产范围 (Scope) 扩充，全面支持并严格区分 Domain 与 IP 类型的目标校验与调度。
* **功能**：新增自定义 PoC 源码在线读取、编辑与全可视化创建管理，增强了级联删除逻辑。
* **功能**：新增字典配置模块，提供弱口令字典查询、预览及可视化读写管理。
* **优化**：360 搜索引擎采集逻辑新增反爬熔断保护，追加高价值关键字深度挖掘；生产环境 Nginx 开启 Gzip 压缩。
* **修复**：修复前端详情页高级搜索表单及组件数据联动异常。
</details>

<details>
<summary><b>v1.1.0</b></summary><br/>

* **新增**：全新引入 GitHub 威胁情报雷达（支持 CVE 漏洞雷达、安全武器库及黑客动态监测）。
* **新增**：完善告警生态，支持 Telegram 机器人推送告警。
* **重构**：前端系统设置与 Github 管理页面结构重构，全面启用 HTTP/2 多路复用，大幅降低前端并发加载延迟。
* **修复**：修复 HTTP 存活检测与站点截图组件在 Docker 下的超时和崩溃 Bug，及仪表盘漏洞趋势无数据的 Bug。
</details>

<details>
<summary><b>v1.0.9</b></summary><br/>

* **重构**：分离后端 ARL 内部漏洞与 Nuclei 引擎扫描结果的统计逻辑。
* **交互**：Dashboard 漏洞统计卡片 UI 极简重构，支持按漏洞类型与危害等级点击下钻（Drill-down）。
* **交互**：资产查询页面支持接收仪表盘的联动请求，实现页面跳转与高级筛选项的自动填充。
</details>

<details>
<summary><b>v1.0.8</b></summary><br/>

* **功能**：完善 POC 导入机制，支持批量拖拽上传验证脚本，并提供标准 Python POC 模板下载。
* **架构**：引入 Celery 任务并发热扩缩容机制，修改并发数配置后即时生效，无需重启服务。
* **重构**：重构仪表盘底层查询逻辑，统一基于站点表单库进行海量数据的高效查询。
* **部署**：深度分离开发与生产环境启动脚本，增加 POC 独立数据卷挂载。
* **优化**：优化前端站点截图预览样式防变形，并持续迭代系统内置指纹库。
</details>

---

## 🤝 致谢

本项目站在巨人的肩膀上，特此鸣谢以下项目与团队：

* **核心架构**：基于原版 [ARL 灯塔](https://github.com/TophantTechnology/ARL) 重构，并参考了 [Aabyss-Team/ARL](https://github.com/Aabyss-Team/ARL) 与 [adysec/ARL](https://github.com/adysec/ARL) 等优秀衍生版。
* **指纹引擎**：感谢 **威零安全团队** (<img src="./img/weiling.jpg" width="18" height="18" align="absmiddle" /> 公众号) 提供的万级高质量指纹数据支撑。
* **功能模块**：企业资产查询深度借鉴了 [ICP_Query](https://github.com/HG-ha/ICP_Query)，威胁监控模块汲取了 [github-cve-monitor](https://github.com/yhy0/github-cve-monitor) 的设计思路。

ARL-Next 将秉持开源互助的初心，持续为信息安全社区贡献力量！

---

## 💖 赞助与支持

本项目的持续开发与维护离不开社区的支持。感谢以下赞助者为开源生态做出的贡献。如果你觉得本项目对你有帮助，欢迎赞助支持。

<p>
  <img src="./img/buymeacoffee.png" width="200" alt="Buy Me A Coffee" />
</p>
<a href="https://github.com/robotfish001">
  <img src="https://github.com/robotfish001.png" width="50" height="50" style="border-radius: 50%;" alt="robotfish-001" title="robotfish-001"/>
</a>
<a href="https://github.com/phpmac">
  <img src="https://github.com/phpmac.png" width="50" height="50" style="border-radius: 50%;" alt="phpmac" title="phpmac"/>
</a>

---

## ⚠️ 声明与免责

> 本工具仅面向合法授权的企业安全建设、SRC 漏洞挖掘及学术研究。使用本工具时，请务必遵守当地法律法规（如《中华人民共和国网络安全法》）及目标平台的测试规范。**未经授权的探测属非法行为。**
> 
> 使用者因使用本工具造成的任何直接或间接的法律责任，由使用者自行承担，项目作者及贡献者不负任何连带责任。

---

## 💬 问题反馈与交流

- **反馈建议**：如遇 Bug 或有功能建议，欢迎提交 GitHub Issues。
- **技术交流**：欢迎添加个人微信或加入 QQ 群，探讨安全开发与红蓝对抗技术。
- **获取动态**：关注微信公众号【owl安全】，不定期获取安全干货与项目更新提醒！

<table align="center">
  <tr>
    <td align="center" style="padding: 0 40px;"><b>个人微信</b></td>
    <td align="center" style="padding: 0 40px;"><b>微信公众号 (owl安全)</b></td>
    <td align="center" style="padding: 0 40px;"><b>QQ交流群</b></td>
  </tr>
  <tr>
    <td align="center" style="padding: 0 40px;"><img src="./img/wechat.png" alt="个人微信" width="250" /></td>
    <td align="center" style="padding: 0 40px;"><img src="./img/wechat_public.jpg" alt="微信公众号 owl安全" width="250" /></td>
    <td align="center" style="padding: 0 40px;"><img src="./img/qq_group.jpg" alt="QQ交流群" width="250" /></td>
  </tr>
</table>


---

## 🌟 Star History

**⭐ 如果本项目为你的安全工作带来了便利，不妨点个 Star 支持一下！**

<div align="center">

<a href="https://www.star-history.com/?repos=owl234%2Farl-next&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=owl234/arl-next&type=date&theme=dark&legend=top-left&sealed_token=vNF3XBBUYjnOkZ1XfTODaJEURB73qlNr1zXyCH6HOUbJGKju3QmIb7pVDyjCK67Ra-ukzG7dgZ3B3HDpCKJ3raveN9bOCec7r6gDILhjGrYbcVEV2Gy5Ew" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=owl234/arl-next&type=date&legend=top-left&sealed_token=vNF3XBBUYjnOkZ1XfTODaJEURB73qlNr1zXyCH6HOUbJGKju3QmIb7pVDyjCK67Ra-ukzG7dgZ3B3HDpCKJ3raveN9bOCec7r6gDILhjGrYbcVEV2Gy5Ew" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=owl234/arl-next&type=date&legend=top-left&sealed_token=vNF3XBBUYjnOkZ1XfTODaJEURB73qlNr1zXyCH6HOUbJGKju3QmIb7pVDyjCK67Ra-ukzG7dgZ3B3HDpCKJ3raveN9bOCec7r6gDILhjGrYbcVEV2Gy5Ew" />
 </picture>
</a>

</div>


