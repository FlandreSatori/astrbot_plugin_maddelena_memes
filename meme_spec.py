from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PLUGIN_DIR = Path(__file__).parent
ASSETS_DIR = PLUGIN_DIR / "assets"

Point = tuple[int, int]
Quad = tuple[Point, Point, Point, Point]


@dataclass(frozen=True)
class MemeTemplate:
    """One sign-holding meme.

    text_quad vertex order (image pixel coordinates):
        0: top-left → 1: top-right → 2: bottom-right → 3: bottom-left
    """

    command: str
    image: str | Path
    text_quad: Quad
    aliases: tuple[str, ...] = ()
    id: str = ""
    help_name: str = ""

    def __post_init__(self) -> None:
        command = self.command.strip()
        if not command:
            raise ValueError("MemeTemplate.command must not be empty")
        if len(self.text_quad) != 4:
            raise ValueError(f"MemeTemplate.text_quad must have 4 points, got {len(self.text_quad)}")
        object.__setattr__(self, "command", command)
        object.__setattr__(
            self,
            "aliases",
            tuple(alias.strip() for alias in self.aliases if alias and alias.strip()),
        )
        object.__setattr__(self, "id", (self.id or command).strip())
        object.__setattr__(self, "help_name", (self.help_name or command).strip())

    @property
    def image_path(self) -> Path:
        path = Path(self.image)
        if not path.is_absolute():
            path = ASSETS_DIR / path
        return path

    def all_commands(self) -> tuple[str, ...]:
        names = [self.command, *self.aliases]
        # Preserve order while removing duplicates.
        seen: set[str] = set()
        result: list[str] = []
        for name in names:
            if name not in seen:
                seen.add(name)
                result.append(name)
        return tuple(result)


@dataclass
class MemeRegistry:
    memes: list[MemeTemplate] = field(default_factory=list)
    by_command: dict[str, MemeTemplate] = field(default_factory=dict)

    @classmethod
    def from_templates(cls, templates: list[MemeTemplate]) -> MemeRegistry:
        registry = cls()
        for template in templates:
            registry.register(template)
        return registry

    def register(self, template: MemeTemplate) -> None:
        for name in template.all_commands():
            if name in self.by_command:
                existing = self.by_command[name]
                raise ValueError(
                    f"Duplicate meme command '{name}' "
                    f"(used by '{existing.id}' and '{template.id}')"
                )
            self.by_command[name] = template
        self.memes.append(template)

    @property
    def primary_command(self) -> str:
        if not self.memes:
            raise RuntimeError("No meme templates registered")
        return self.memes[0].command

    @property
    def all_aliases(self) -> set[str]:
        aliases: set[str] = set()
        primary = self.primary_command
        for meme in self.memes:
            for name in meme.all_commands():
                if name != primary:
                    aliases.add(name)
        return aliases

    def resolve(self, command_name: str) -> MemeTemplate | None:
        return self.by_command.get(command_name.strip())
