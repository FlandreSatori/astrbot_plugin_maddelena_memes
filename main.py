from __future__ import annotations

import asyncio
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

PLUGIN_DIR = Path(__file__).parent
IMAGE_PATH = PLUGIN_DIR / "Maddelena.jpg"
TEXT_CANVAS_SIZE = (1120, 430)
TEXT_PADDING = 48
TEXT_QUAD = [
    (188, 560),
    (535, 540),
    (605, 925),
    (265, 945),
]
COMMAND_NAME = "小画家说"
COMMAND_ALIASES = {"maddelena说", "maddelenasays"}
FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
]


def _find_font_path() -> str | None:
    for font_path in FONT_CANDIDATES:
        if Path(font_path).exists():
            return font_path
    return None


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = _find_font_path()
    if font_path is None:
        logger.warning("[maddelena] 未找到系统中文字体，将使用默认字体")
        return ImageFont.load_default()
    return ImageFont.truetype(font_path, size)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            trial = current + char
            bbox = draw.textbbox((0, 0), trial, font=font, spacing=10, align="center")
            if bbox[2] - bbox[0] <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = char
        if current:
            lines.append(current)
    return lines or [""]


def _fit_text(text: str, canvas_size: tuple[int, int], padding: int) -> tuple[Image.Image, int]:
    text_layer = Image.new("RGBA", canvas_size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(text_layer)
    max_width = canvas_size[0] - padding * 2
    max_height = canvas_size[1] - padding * 2

    best_lines = [text]
    best_font: ImageFont.ImageFont | ImageFont.FreeTypeFont = _load_font(24)
    best_size = 24

    for font_size in range(84, 15, -2):
        font = _load_font(font_size)
        lines = _wrap_text(draw, text, font, max_width)
        bbox = draw.multiline_textbbox((0, 0), "\n".join(lines), font=font, spacing=10, align="center")
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        if text_width <= max_width and text_height <= max_height:
            best_lines = lines
            best_font = font
            best_size = font_size
            break

    content = "\n".join(best_lines)
    bbox = draw.multiline_textbbox((0, 0), content, font=best_font, spacing=10, align="center")
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (canvas_size[0] - text_width) / 2 - bbox[0]
    y = (canvas_size[1] - text_height) / 2 - bbox[1]
    draw.multiline_text(
        (x, y),
        content,
        font=best_font,
        fill=(30, 30, 30, 255),
        spacing=10,
        align="center",
    )
    return text_layer, best_size


def _find_coeffs(pa: list[tuple[int, int]], pb: list[tuple[int, int]]) -> list[float]:
    import numpy

    matrix = []
    for p1, p2 in zip(pa, pb):
        matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0] * p1[0], -p2[0] * p1[1]])
        matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1] * p1[0], -p2[1] * p1[1]])

    a = numpy.matrix(matrix, dtype=float)
    b = numpy.array(pb).reshape(8)
    res = numpy.dot(numpy.linalg.inv(a.T * a) * a.T, b)
    return numpy.array(res).reshape(8).tolist()


def render_maddelena(text: str) -> bytes:
    cleaned = text.replace("\\n", "\n").strip()
    if not cleaned:
        raise ValueError("请输入要写在纸上的内容")
    if len(cleaned) > 200:
        raise ValueError("文本过长，最多支持 200 个字符")
    if not IMAGE_PATH.exists():
        raise FileNotFoundError("缺少 Maddelena.jpg")

    base = Image.open(IMAGE_PATH).convert("RGBA")
    text_layer, _ = _fit_text(cleaned, TEXT_CANVAS_SIZE, TEXT_PADDING)
    src_quad = [
        (0, 0),
        (TEXT_CANVAS_SIZE[0] - 1, 0),
        (TEXT_CANVAS_SIZE[0] - 1, TEXT_CANVAS_SIZE[1] - 1),
        (0, TEXT_CANVAS_SIZE[1] - 1),
    ]
    coeffs = _find_coeffs(TEXT_QUAD, src_quad)
    warped = text_layer.transform(base.size, Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC)
    result = Image.alpha_composite(base, warped)

    output = BytesIO()
    result.convert("RGB").save(output, format="PNG")
    return output.getvalue()


@register(
    "astrbot_plugin_maddelena_memes",
    "GitHub Copilot",
    "生成玛德蕾娜举牌表情包",
    "0.0.1",
)
class MaddelenaMemesPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command(COMMAND_NAME, alias=COMMAND_ALIASES)
    async def handle_maddelena(self, event: AstrMessageEvent):
        message_str = event.message_str.strip()
        parts = message_str.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            yield event.plain_result(f"请输入文本。用法: /{COMMAND_NAME} 你好")
            return

        text = parts[1]
        try:
            loop = asyncio.get_running_loop()
            image_bytes = await loop.run_in_executor(None, render_maddelena, text)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(image_bytes)
                temp_path = temp_file.name
            try:
                yield event.image_result(temp_path)
            finally:
                Path(temp_path).unlink(missing_ok=True)
        except Exception as exc:
            logger.error(f"[maddelena] 生成图片失败: {exc!s}")
            yield event.plain_result(f"生成图片失败: {exc!s}")
