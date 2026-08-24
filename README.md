# Image Vision MCP Server

绕过主模型多模态限制，通过百炼（DashScope）Qwen VL 模型实现识图功能。纯 Python，Windows / WSL / Linux 通用。

## 场景

Claude Code 主模型设为 DeepSeek 时，DeepSeek 不支持多模态输入，直接拖图片进对话会 API 校验失败。

本 MCP Server 提供 `analyze_image` 工具：
- DeepSeek 收到「帮我分析这张图」的纯文本请求
- DeepSeek 调用 `analyze_image` 工具（普通 function call，不涉及多模态）
- MCP Server 读取本地图片 → 调百炼视觉 API → 返回文字描述
- DeepSeek 基于文字描述继续处理

## 安装与注册

无需克隆仓库，uvx 从 GitHub 直接拉取运行。在 Claude Code 中注册（user 作用域，全项目可用）：

```bash
claude mcp add-json --scope user image-vision \
  '{"command":"uvx","args":["--from","git+https://github.com/fenlyin0420/image-vision-server.git","image-vision-server"]}'
```

首次调用会自动构建环境（之后走缓存，秒级启动）。

开发调试时可克隆仓库本地运行：

```bash
git clone https://github.com/fenlyin0420/image-vision-server.git
cd image-vision-server
uvx --from . image-vision-server   # 等价于 uv run server.py
```

## 配置（敏感信息注入）

API Key 不写入任何配置文件——设置到系统/用户环境变量中，MCP 子进程会自动继承父进程的环境：

```bash
# Windows（用户级，新开的终端生效）
setx DASHSCOPE_API_KEY "sk-xxxxxxxxxxxxxxxx"

# macOS / Linux（写入 ~/.bashrc 或 ~/.zshrc）
export DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
```

可选：切换视觉模型（默认 `qwen3.7-flash`）：

```bash
setx VISION_MODEL "qwen-vl-max"    # Windows
export VISION_MODEL=qwen-vl-max    # macOS / Linux
```

如需在 MCP 配置里显式声明而非依赖继承，可用 `${VAR}` 展开语法引用环境变量（不要写明文密钥）：

```json
{ "command": "uvx", "args": ["..."], "env": { "DASHSCOPE_API_KEY": "${DASHSCOPE_API_KEY}" } }
```

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

默认使用 `qwen3.7-flash`（以 server.py 中默认值为准），可通过环境变量 `VISION_MODEL` 切换，例如 `qwen-vl-max`。
