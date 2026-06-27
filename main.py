from __future__ import annotations

import asyncio
import math
import tempfile
from dataclasses import dataclass, replace
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

PLUGIN_DIR = Path(__file__).parent
IMAGE_PATH = PLUGIN_DIR / "Maddelena.jpg"
TEXT_QUAD = [
    (188, 560),
    (535, 540),
    (605, 925),
    (265, 945),
]
COMMAND_NAME = "小画家说"
COMMAND_ALIASES = {"老玛说", "玛德蕾娜说"}
DEFAULT_TEXT_COLOR = (30, 30, 30, 255)
FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
]
ESCAPE_MAP = {
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "\\": "\\",
    "[": "[",
    "]": "]",
}


@dataclass(frozen=True)
class StyleState:
    color: tuple[int, int, int, int] = DEFAULT_TEXT_COLOR
    underline: bool = False
    strike: bool = False


@dataclass(frozen=True)
class StyledChar:
    char: str
    style: StyleState


@dataclass(frozen=True)
class RenderConfig:
    padding_x: int
    padding_y: int
    line_spacing: int
    char_spacing: int
    font_min_size: int
    font_max_size: int
    font_path: str | None
    text_color: tuple[int, int, int, int]
    stroke_width: int
    stroke_fill: tuple[int, int, int, int]
    align: str


def _clamp_int(value: object, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _normalize_align(value: object) -> str:
    normalized = str(value or "center").strip().lower()
    if normalized in {"left", "center", "right"}:
        return normalized
    return "center"


def _parse_color(value: object, default: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    text = str(value or "").strip()
    if not text:
        return default
    if text.startswith("#"):
        text = text[1:]
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) == 6:
        text = f"{text}ff"
    if len(text) != 8:
        return default
    try:
        return tuple(int(text[index:index + 2], 16) for index in range(0, 8, 2))  # type: ignore[return-value]
    except ValueError:
        return default


def _find_font_path(configured_font_path: object = None) -> str | None:
    custom_path = Path(str(configured_font_path or "").strip())
    if str(configured_font_path or "").strip() and custom_path.exists() and custom_path.is_file():
        return str(custom_path)
    for font_path in FONT_CANDIDATES:
        if Path(font_path).exists():
            return font_path
    return None


def _load_font(size: int, font_path: str | None) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_path is None:
        logger.warning("[maddelena] 未找到可用字体，将使用默认字体")
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(font_path, size)
    except OSError:
        logger.warning(f"[maddelena] 加载字体失败: {font_path}")
        return ImageFont.load_default()


def _get_render_config(config: AstrBotConfig | dict | None) -> RenderConfig:
    config_data = config or {}
    getter = getattr(config_data, "get", None)
    if callable(getter):
        get_value = getter
    else:
        get_value = lambda key, default=None: default

    font_path = _find_font_path(get_value("font_path", ""))
    text_color = _parse_color(get_value("text_color", "#1e1e1e"), DEFAULT_TEXT_COLOR)
    return RenderConfig(
        padding_x=_clamp_int(get_value("padding_x", 28), 28, 0, 200),
        padding_y=_clamp_int(get_value("padding_y", 28), 28, 0, 200),
        line_spacing=_clamp_int(get_value("line_spacing", 8), 8, 0, 80),
        char_spacing=_clamp_int(get_value("char_spacing", 0), 0, 0, 20),
        font_min_size=_clamp_int(get_value("font_min_size", 18), 18, 8, 200),
        font_max_size=_clamp_int(get_value("font_max_size", 72), 72, 12, 260),
        font_path=font_path,
        text_color=text_color,
        stroke_width=_clamp_int(get_value("stroke_width", 0), 0, 0, 12),
        stroke_fill=_parse_color(get_value("stroke_fill", "#ffffff"), (255, 255, 255, 255)),
        align=_normalize_align(get_value("align", "center")),
    )


def _paper_canvas_size() -> tuple[int, int]:
    top_width = math.dist(TEXT_QUAD[0], TEXT_QUAD[1])
    bottom_width = math.dist(TEXT_QUAD[3], TEXT_QUAD[2])
    left_height = math.dist(TEXT_QUAD[0], TEXT_QUAD[3])
    right_height = math.dist(TEXT_QUAD[1], TEXT_QUAD[2])
    return (
        max(120, round((top_width + bottom_width) / 2)),
        max(120, round((left_height + right_height) / 2)),
    )


def _decode_escape(text: str, index: int) -> tuple[str, int]:
    if index + 1 >= len(text):
        return "\\", index + 1
    escaped = ESCAPE_MAP.get(text[index + 1])
    if escaped is None:
        return text[index + 1], index + 2
    return escaped, index + 2


def _parse_markup(text: str, default_style: StyleState) -> list[StyledChar]:
    chars: list[StyledChar] = []
    stack = [default_style]
    index = 0
    while index < len(text):
        if text[index] == "\\":
            escaped, index = _decode_escape(text, index)
            chars.append(StyledChar(escaped, stack[-1]))
            continue
        if text.startswith("[color=", index):
            end = text.find("]", index)
            if end != -1:
                color = _parse_color(text[index + 7:end], stack[-1].color)
                stack.append(replace(stack[-1], color=color))
                index = end + 1
                continue
        if text.startswith("[/color]", index):
            if len(stack) > 1:
                stack.pop()
            index += 8
            continue
        if text.startswith("[u]", index):
            stack.append(replace(stack[-1], underline=True))
            index += 3
            continue
        if text.startswith("[/u]", index):
            if len(stack) > 1:
                stack.pop()
            index += 4
            continue
        if text.startswith("[s]", index):
            stack.append(replace(stack[-1], strike=True))
            index += 3
            continue
        if text.startswith("[/s]", index):
            if len(stack) > 1:
                stack.pop()
            index += 4
            continue
        chars.append(StyledChar(text[index], stack[-1]))
        index += 1
    return chars


def _measure_char(draw: ImageDraw.ImageDraw, styled_char: StyledChar, font: ImageFont.ImageFont) -> float:
    if styled_char.char == "\t":
        return draw.textlength("    ", font=font)
    return draw.textlength(styled_char.char, font=font)


def _wrap_styled_chars(
    draw: ImageDraw.ImageDraw,
    styled_chars: list[StyledChar],
    font: ImageFont.ImageFont,
    max_width: int,
    char_spacing: int,
) -> tuple[list[list[StyledChar]], list[float]]:
    lines: list[list[StyledChar]] = [[]]
    widths: list[float] = [0.0]

    for styled_char in styled_chars:
        if styled_char.char in {"\r"}:
            continue
        if styled_char.char == "\n":
            lines.append([])
            widths.append(0.0)
            continue

        char_width = _measure_char(draw, styled_char, font)
        extra_spacing = char_spacing if lines[-1] else 0
        next_width = widths[-1] + extra_spacing + char_width
        if next_width > max_width and lines[-1]:
            lines.append([])
            widths.append(0.0)
            extra_spacing = 0
            next_width = char_width

        lines[-1].append(styled_char)
        widths[-1] = next_width

    return lines, widths


def _font_line_height(draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), "国Ag", font=font)
    return max(1, bbox[3] - bbox[1])


def _render_styled_text(text: str, config: RenderConfig) -> Image.Image:
    canvas_size = _paper_canvas_size()
    text_layer = Image.new("RGBA", canvas_size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(text_layer)
    max_width = max(20, canvas_size[0] - config.padding_x * 2)
    max_height = max(20, canvas_size[1] - config.padding_y * 2)
    styled_chars = _parse_markup(text, StyleState(color=config.text_color))

    min_size = min(config.font_min_size, config.font_max_size)
    max_size = max(config.font_min_size, config.font_max_size)
    chosen_font = _load_font(min_size, config.font_path)
    chosen_lines: list[list[StyledChar]] = [[StyledChar("", StyleState(color=config.text_color))]]
    chosen_widths = [0.0]
    chosen_line_height = _font_line_height(draw, chosen_font)

    for font_size in range(max_size, min_size - 1, -2):
        font = _load_font(font_size, config.font_path)
        lines, widths = _wrap_styled_chars(draw, styled_chars, font, max_width, config.char_spacing)
        line_height = _font_line_height(draw, font)
        total_height = len(lines) * line_height + max(0, len(lines) - 1) * config.line_spacing
        if total_height <= max_height:
            chosen_font = font
            chosen_lines = lines
            chosen_widths = widths
            chosen_line_height = line_height
            break

    total_height = len(chosen_lines) * chosen_line_height + max(0, len(chosen_lines) - 1) * config.line_spacing
    y = (canvas_size[1] - total_height) / 2

    for line, line_width in zip(chosen_lines, chosen_widths):
        if config.align == "left":
            x = float(config.padding_x)
        elif config.align == "right":
            x = float(canvas_size[0] - config.padding_x - line_width)
        else:
            x = float((canvas_size[0] - line_width) / 2)

        for index, styled_char in enumerate(line):
            if index > 0:
                x += config.char_spacing
            draw_char = "    " if styled_char.char == "\t" else styled_char.char
            if draw_char:
                draw.text(
                    (x, y),
                    draw_char,
                    font=chosen_font,
                    fill=styled_char.style.color,
                    stroke_width=config.stroke_width,
                    stroke_fill=config.stroke_fill,
                )
                bbox = draw.textbbox(
                    (x, y),
                    draw_char,
                    font=chosen_font,
                    stroke_width=config.stroke_width,
                )
                if styled_char.style.underline and not draw_char.isspace():
                    underline_y = bbox[3] - max(1, chosen_line_height // 14)
                    draw.line((bbox[0], underline_y, bbox[2], underline_y), fill=styled_char.style.color, width=max(1, chosen_line_height // 18))
                if styled_char.style.strike and not draw_char.isspace():
                    strike_y = (bbox[1] + bbox[3]) / 2
                    draw.line((bbox[0], strike_y, bbox[2], strike_y), fill=styled_char.style.color, width=max(1, chosen_line_height // 18))
            x += _measure_char(draw, styled_char, chosen_font)
        y += chosen_line_height + config.line_spacing

    return text_layer


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [value] for row, value in zip(matrix, vector)]

    for pivot_index in range(size):
        pivot_row = max(range(pivot_index, size), key=lambda row_index: abs(augmented[row_index][pivot_index]))
        if abs(augmented[pivot_row][pivot_index]) < 1e-9:
            raise ValueError("透视矩阵不可逆")
        augmented[pivot_index], augmented[pivot_row] = augmented[pivot_row], augmented[pivot_index]

        pivot = augmented[pivot_index][pivot_index]
        for column_index in range(pivot_index, size + 1):
            augmented[pivot_index][column_index] /= pivot

        for row_index in range(size):
            if row_index == pivot_index:
                continue
            factor = augmented[row_index][pivot_index]
            for column_index in range(pivot_index, size + 1):
                augmented[row_index][column_index] -= factor * augmented[pivot_index][column_index]

    return [augmented[row_index][-1] for row_index in range(size)]


def _find_coeffs(pa: list[tuple[int, int]], pb: list[tuple[int, int]]) -> list[float]:
    matrix: list[list[float]] = []
    vector: list[float] = []
    for (x1, y1), (x2, y2) in zip(pa, pb):
        matrix.append([x1, y1, 1, 0, 0, 0, -x2 * x1, -x2 * y1])
        vector.append(x2)
        matrix.append([0, 0, 0, x1, y1, 1, -y2 * x1, -y2 * y1])
        vector.append(y2)
    return _solve_linear_system(matrix, vector)


def render_maddelena(text: str, config: RenderConfig | None = None) -> bytes:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("请输入要写在纸上的内容")
    if len(cleaned) > 500:
        raise ValueError("文本过长，最多支持 500 个字符")
    if not IMAGE_PATH.exists():
        raise FileNotFoundError("缺少 Maddelena.jpg")

    render_config = config or _get_render_config(None)
    base = Image.open(IMAGE_PATH).convert("RGBA")
    text_layer = _render_styled_text(cleaned, render_config)
    src_quad = [
        (0, 0),
        (text_layer.size[0] - 1, 0),
        (text_layer.size[0] - 1, text_layer.size[1] - 1),
        (0, text_layer.size[1] - 1),
    ]
    coeffs = _find_coeffs(TEXT_QUAD, src_quad)
    warped = text_layer.transform(base.size, Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC)
    result = Image.alpha_composite(base, warped)

    output = BytesIO()
    result.convert("RGB").save(output, format="PNG")
    return output.getvalue()


@register(
    "astrbot_plugin_maddelena_memes",
    "FlandreSatori",
    "生成玛德蕾娜举牌表情包",
    "0.1.0",
)
class MaddelenaMemesPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context, config)
        self.config = config or {}

    @filter.command(COMMAND_NAME, alias=COMMAND_ALIASES)
    async def handle_maddelena(self, event: AstrMessageEvent):
        message_str = event.message_str.strip()
        parts = message_str.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            yield event.plain_result(
                "请输入文本。用法: /小画家说 你好\n"
                "支持 \\n、\\t、[color=#ff0000]红字[/color]、[u]下划线[/u]、[s]删除线[/s]"
            )
            return

        text = parts[1]
        try:
            loop = asyncio.get_running_loop()
            render_config = _get_render_config(self.config)
            image_bytes = await loop.run_in_executor(None, render_maddelena, text, render_config)
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
