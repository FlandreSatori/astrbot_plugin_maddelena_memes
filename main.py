from __future__ import annotations

import base64
import asyncio

from dataclasses import replace

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Image

from .meme_spec import MemeRegistry, MemeTemplate
from .render import get_render_config, parse_command_options, render_meme
from .templates import get_registry

USAGE_FLAGS = (
    "可选参数: -r 禁用自动换行并缩小字号；-s10 指定字号（可叠加）\n"
    "支持 \\n、\\t、[color=#ff0000]红字[/color]、[u]下划线[/u]、[s]删除线[/s]"
)


def _extract_command_name(message_str: str) -> str:
    first = message_str.strip().split(maxsplit=1)[0]
    return first.lstrip("/").strip()


def _build_usage(meme: MemeTemplate) -> str:
    triggers = " / ".join(f"/{name}" for name in meme.all_commands())
    return f"请输入文本。用法: /{meme.command} 你好\n触发词: {triggers}\n{USAGE_FLAGS}"


@register(
    "astrbot_plugin_maddelena_memes",
    "FlandreSatori",
    "生成举牌表情包（可扩展多模板）",
    "0.3.0",
)
class MaddelenaMemesPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context, config)
        self.config = config or {}
        self.registry: MemeRegistry = get_registry()

    def _resolve_meme(self, event: AstrMessageEvent) -> MemeTemplate | None:
        return self.registry.resolve(_extract_command_name(event.message_str))

    @filter.command(
        get_registry().primary_command,
        alias=get_registry().all_aliases,
    )
    async def handle_meme(self, event: AstrMessageEvent):
        meme = self._resolve_meme(event)
        if meme is None:
            event.stop_event()
            yield event.plain_result("未找到对应的表情包模板")
            return

        message_str = event.message_str.strip()
        parts = message_str.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            event.stop_event()
            yield event.plain_result(_build_usage(meme))
            return

        options = parse_command_options(parts[1])
        if not options.text.strip():
            event.stop_event()
            yield event.plain_result("请输入要写在纸上的内容")
            return

        try:
            loop = asyncio.get_running_loop()
            logger.info(
                f"[maddelena][font] handle_meme meme={meme.id} "
                f"config.font_path={self.config.get('font_path', '')!r}"
            )
            render_config = replace(
                get_render_config(self.config),
                no_auto_wrap=options.no_auto_wrap,
                fixed_font_size=options.fixed_font_size,
            )
            logger.info(
                f"[maddelena][font] before render font_path={render_config.font_path!r} "
                f"fixed_size={render_config.fixed_font_size} no_auto_wrap={render_config.no_auto_wrap}"
            )
            image_bytes = await loop.run_in_executor(
                None,
                render_meme,
                options.text,
                meme,
                render_config,
            )
            # 直接将内存中的字节流转为 base64
            b64_str = base64.b64encode(image_bytes).decode("utf-8")
            
            event.stop_event()
            # 构造 base64 协议的 URL 直接发送（跳过本地文件系统）
            yield event.chain_result([Image(url=f"base64://{b64_str}")])
        except Exception as exc:
            logger.error(f"[maddelena] 生成图片失败 ({meme.id}): {exc!s}")
            event.stop_event()
            yield event.plain_result(f"生成图片失败: {exc!s}")
