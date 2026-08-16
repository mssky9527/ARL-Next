# ARL-Next MCP Server

> 让 Claude Code 直接对接 ARL（资产侦察灯塔），以极其节省 Token 的 CSV 格式获取目标资产情报。

## 它能做什么

当前暴露 **2 个工具**：

1. `export_task_assets`：一键导出目标所有资产为本地 CSV 并返回战术大盘摘要（适合指令：“请使用 arl-next mcp工具导出 dcdapp.com 的所有资产数据”）。
2. `get_task_detail_export`：按需在对话中获取单维度的 CSV 数据（支持列裁剪与分页）。

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ARL_HOST` | ARL 后端 API 地址 | `https://127.0.0.1:5003` |
| `ARL_TOKEN` | ARL API Token | 空（必填） |

## 快速开始

### 方式 A：Python 虚拟环境（Claude Code 推荐）

```bash
cd mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

注册到 Claude Code（替换地址与 Token）：

```bash
claude mcp add -s user arl-next-mcp \
  "$(pwd)/.venv/bin/python" "$(pwd)/server.py" \
  --env ARL_HOST="https://<你的ARL地址>:5003" \
  --env ARL_TOKEN="<你的Token>"
```

### 方式 B：Docker

```bash
docker build -t arl-next-mcp:latest .
```

客户端 MCP 配置：

```json
"ARL-Next": {
  "command": "docker",
  "args": ["run", "-i", "--rm", "-e", "ARL_HOST", "-e", "ARL_TOKEN", "arl-next-mcp:latest"],
  "env": {
    "ARL_HOST": "https://<你的ARL地址>:5003",
    "ARL_TOKEN": "<你的Token>"
  }
}
```

## 工具参考

### 1. `export_task_assets`

一键全量导出目标全部 13 维资产到本地 CSV，并返回极简 Markdown 战术总览。

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `target` | string | ❌ | 目标名称（如 `dcdapp.com`），自动检索最新任务 ID。 |
| `task_id` | string | ❌ | 24位 ARL 任务 ID，若提供则优先使用。 |
| `output_dir` | string | ❌ | 自定义本地保存目录（默认保存到 `recon/<target>/arl/`）。 |

**自然语言触发词**：
- *"请使用 arl-next mcp 工具导出 dcdapp.com 的所有资产数据"*
- *"导出目标 XX 的所有资产"*
- *"把 XX 的扫描结果存到本地"*

---

### 2. `get_task_detail_export`

在对话流中按需提取特定维度的 CSV 数据，支持列过滤。

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `target` | string | ❌ | 目标域名（如 `dcdapp.com`）。 |
| `task_id` | string | ❌ | 24位任务 ID。 |
| `tab` | string | ❌ | 数据表名（如 `site`, `domain`, `ip`, `cert`, `wih`, `fileleak`, `vuln` 等 13 个表），默认 `site`。 |
| `page` | integer | ❌ | 页码，默认 1。 |
| `limit` | integer | ❌ | 每页条数，默认 100。 |
| `columns` | array | ❌ | 指定返回的列名列表（例如 `["IP", "开放端口"]`）。 |

## 依赖

`mcp>=1.0.0,<2.0.0`、`requests`、`urllib3`（见 `requirements.txt`）。
