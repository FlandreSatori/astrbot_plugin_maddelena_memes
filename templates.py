"""Meme template registry.

To add a new meme, you only need to:
1. Put the base image into the `assets/` folder
2. Append a MemeTemplate below with:
   - command / aliases: trigger words
   - image: filename under assets/ (or an absolute path)
   - text_quad: four corner points of the writable area

text_quad order (pixel coordinates on the image):
    top-left → top-right → bottom-right → bottom-left
"""

from __future__ import annotations

from .meme_spec import MemeRegistry, MemeTemplate

# ---------------------------------------------------------------------------
# Register memes here
# ---------------------------------------------------------------------------

MEMES: list[MemeTemplate] = [
    MemeTemplate(
        id="maddelena",
        command="小画家说",
        aliases=("老玛说", "玛德蕾娜说"),
        image="Maddelena.jpg",
        text_quad=(
            (188, 560),  # top-left
            (535, 540),  # top-right
            (605, 925),  # bottom-right
            (265, 945),  # bottom-left
        ),
    ),
    MemeTemplate(
        id="喵梦",
        command="喵梦说",
        image="喵梦.png",
        text_quad=(
            (342,177),  # top-left
            (600, 177),  # top-right
            (600, 347),  # bottom-right
            (342, 347),  # bottom-left
        ),
    ),
    MemeTemplate(
        id="睦子米",
        command="睦子米说",
        aliases=("睦说", "若叶睦说"),
        image="睦子米.png",
        text_quad=(
            (342,177),  # top-left
            (600, 177),  # top-right
            (600, 347),  # bottom-right
            (342, 347),  # bottom-left
        ),
    ),
    MemeTemplate(
        id="祥子",
        command="祥子说",
        image="祥子.png",
        text_quad=(
            (342,177),  # top-left
            (600, 177),  # top-right
            (600, 347),  # bottom-right
            (342, 347),  # bottom-left
        ),
    ),
	
    # MemeTemplate(
    #     id="example",
    #     command="某某说",
    #     aliases=("别名1", "别名2"),
    #     image="example.jpg",
    #     text_quad=(
    #         (x1, y1),  # top-left
    #         (x2, y2),  # top-right
    #         (x3, y3),  # bottom-right
    #         (x4, y4),  # bottom-left
    #     ),
    # ),
]


def get_registry() -> MemeRegistry:
    return MemeRegistry.from_templates(MEMES)
