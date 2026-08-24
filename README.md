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

API Key 先设置到系统环境变量，注册时通过 `--env` 参数显式声明注入点；配置文件里只存 `${VAR}` 引用，Claude Code 在连接建立时才展开为真实值——密钥全程不以明文落盘：

```bash
# 1. 设置环境变量（Windows 用户级 / POSIX shell profile）
setx DASHSCOPE_API_KEY "sk-xxxxxxxxxxxxxxxx"
export DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx     # macOS / Linux

# 2. 注册（${VAR} 用单引号包住，防止 shell 当场展开）
claude mcp add --scope user image-vision \
  --env 'DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}' \
  -- uvx --from git+https://github.com/fenlyin0420/image-vision-server.git image-vision-server
```

连接时也可以直接给明文值（`--env DASHSCOPE_API_KEY=sk-xxx`），机制上等效，但密钥会明文留在配置文件里，不推荐。未在 `env` 块声明的变量仍按进程环境正常继承。

可选：切换视觉模型（默认 `qwen3.7-flash`），同样走环境变量或 `--env`：

```bash
setx VISION_MODEL "qwen-vl-max"     # Windows
export VISION_MODEL=qwen-vl-max     # macOS / Linux
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
