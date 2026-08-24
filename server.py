#!/usr/bin/env python3
"""
MCP Server: 图片识别服务
主模型 DeepSeek 不支持多模态 — 拖入图片会报 API 校验错误。
本 MCP 提供 analyze_image 工具，绕过主模型直接调百炼视觉 API，
将图片转为文字描述后再交给 DeepSeek 处理。

用法:
  1. 将图片保存到本地文件
  2. 对话中告诉 Claude: "帮我分析 D:/screenshots/error.png"
  3. DeepSeek 调用本工具 -> 百炼识图 -> 返回文字

启动 (uvx, 需 DASHSCOPE_API_KEY 已注入环境变量):
  uvx --from git+https://github.com/fenlyin0420/image-vision-server.git image-vision-server
"""

import base64
import mimetypes
import os
import sys
from pathlib import Path

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ---------------------------------------------------------------------------
# 配置 (从系统环境变量读取)
# ---------------------------------------------------------------------------

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
VISION_MODEL = os.getenv("VISION_MODEL", "qwen3.7-flash")
API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".tif"}
MAX_IMAGE_SIZE_MB = 20

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def check_api_key() -> str | None:
    if not DASHSCOPE_API_KEY or DASHSCOPE_API_KEY.startswith("your_"):
        return "❌ DASHSCOPE_API_KEY 未配置。请在系统环境变量中设置百炼 API Key。"
    return None


def validate_image(path: str) -> tuple[bytes, str] | tuple[None, str]:
    """验证并读取图片文件，返回 (image_bytes, mime_type) 或 (None, error_msg)。"""
    file_path = Path(path)

    if not file_path.exists():
        return None, f"❌ 文件不存在: {path}"

    if not file_path.is_file():
        return None, f"❌ 路径不是文件: {path}"

    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return None, f"❌ 不支持的图片格式: {ext}。支持的格式: {', '.join(SUPPORTED_EXTENSIONS)}"

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_IMAGE_SIZE_MB:
        return None, f"❌ 图片过大: {file_size_mb:.1f}MB (上限 {MAX_IMAGE_SIZE_MB}MB)"

    try:
        image_bytes = file_path.read_bytes()
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type or not mime_type.startswith("image/"):
            # 兜底: 根据扩展名推断
            mime_map = {
                ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp",
                ".tiff": "image/tiff", ".tif": "image/tiff",
            }
            mime_type = mime_map.get(ext, "image/png")
        return image_bytes, mime_type
    except Exception as e:
        return None, f"❌ 读取文件失败: {e}"


async def call_vision_api(image_bytes: bytes, mime_type: str, prompt: str) -> str:
    """调用百炼视觉 API 分析图片。"""
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{image_b64}"

    body = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": 2000,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
        )

        if resp.status_code != 200:
            detail = resp.text[:500]
            return f"❌ 百炼 API 调用失败 (HTTP {resp.status_code}): {detail}"

        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            return f"❌ API 返回格式异常: {e}\n原始响应: {str(data)[:500]}"


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

server = Server("image-vision-server")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyze_image",
            description=(
                "分析本地图片文件，返回图片的文字描述。"
                "当主模型不支持多模态时，通过此工具间接实现「识图」。\n"
                f"支持的格式: {', '.join(SUPPORTED_EXTENSIONS)}\n"
                "使用方式: 先将图片保存到本地文件，然后在对话中提供文件路径。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "图片文件的绝对路径，例如 D:\\screenshots\\error.png",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "对图片的提问，默认为「请详细描述这张图片的内容」。可以指定关注点，如「这张图中的报错信息是什么？」",
                    },
                },
                "required": ["image_path"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "analyze_image":
        return [TextContent(type="text", text=f"未知工具: {name}")]

    # 检查 API Key
    err = check_api_key()
    if err:
        return [TextContent(type="text", text=err)]

    image_path = arguments.get("image_path", "")
    if not image_path:
        return [TextContent(type="text", text="❌ 请提供 image_path 参数")]

    prompt = arguments.get("prompt", "请详细描述这张图片的内容。")

    # 验证并读取图片
    image_bytes, mime_type_or_err = validate_image(image_path)
    if image_bytes is None:
        return [TextContent(type="text", text=mime_type_or_err)]

    # 调用视觉 API
    result = await call_vision_api(image_bytes, mime_type_or_err, prompt)

    return [TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def run():
    """同步控制台入口，供 [project.scripts] 在 uvx/pip 安装后调用。"""
    import asyncio

    asyncio.run(main())


if __name__ == "__main__":
    run()
