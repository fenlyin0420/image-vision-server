# Image Vision MCP Server

绕过主模型多模态限制，通过百炼（DashScope）Qwen VL 模型实现识图功能。纯 Python，Windows / WSL / Linux 通用。

## 场景

Claude Code 主模型设为 DeepSeek 时，DeepSeek 不支持多模态输入，直接拖图片进对话会 API 校验失败。

本 MCP Server 提供 `analyze_image` 工具：
- DeepSeek 收到「帮我分析这张图」的纯文本请求
- DeepSeek 调用 `analyze_image` 工具（普通 function call，不涉及多模态）
- MCP Server 读取本地图片 → 调百炼视觉 API → 返回文字描述
- DeepSeek 基于文字描述继续处理

## 安装

```bash
git clone https://github.com/fenlyin0420/image-vision-server.git
cd image-vision-server
python -m venv .venv
# Windows: .venv\Scripts\python -m pip install -r requirements.txt
# Linux/WSL: .venv/bin/python -m pip install -r requirements.txt
```

## 配置

**1. 设置环境变量**（百炼 API Key，必填）：

```bash
export DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
# 可选：切换模型（默认 qwen-vl-max）
export VISION_MODEL=qwen-vl-max
```

**2. 在 Claude Code 中注册 MCP Server**（推荐用 CLI，路径自动适配各平台）：

```bash
claude mcp add --scope user image-vision \
  --env DASHSCOPE_API_KEY=sk-xxx \
  -- .venv/bin/python "$PWD/server.py"      # Linux/WSL
  # -- .venv\Scripts\python.exe "$PWD\server.py"   # Windows
```

或手动编辑 `~/.claude.json` 的 `mcpServers` 段。

## 使用

1. 将图片保存到本地文件（截图工具一般已自动保存）
2. 在对话中：

```
帮我分析 D:/screenshots/error.png 这张图
```

```
看看这张架构图的设计有什么问题: /home/me/docs/architecture.png
```

## 支持的格式

PNG, JPG, JPEG, GIF, WebP, BMP, TIFF（单个文件 ≤ 20MB）

## 模型

默认使用 `qwen-vl-max`（百炼 Qwen VL 系列最强模型），可通过环境变量 `VISION_MODEL` 切换。
