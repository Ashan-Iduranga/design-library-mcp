"""The shape of one library entry.

pydantic checks every entry when it is created or loaded from JSON, so bad data
(an unknown type, a rating of 9, code from a non-open source) is rejected in one
place instead of being checked separately by the CLI, web app and MCP server.
"""

import hashlib
import re
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

# Code may only be stored when it comes from one of these licenses.
# "Own" means you wrote it yourself.
OPEN_LICENSES = {"MIT", "Apache-2.0", "ISC", "Own"}

# Inspiration/gallery sites: we keep the link and our notes, never their content.
LINK_ONLY = "link-only"


class EntryType(str, Enum):
    style = "style"
    component = "component"
    screen = "screen"
    interaction = "interaction"
    layout = "layout"
    palette = "palette"
    token = "token"


class Framework(str, Enum):
    html = "html"
    tailwind = "tailwind"
    react = "react"
    none = "none"


class StyleNotes(BaseModel):
    palette: str = ""
    fonts: str = ""
    spacing: str = ""
    mood: str = ""

    def as_text(self) -> str:
        """One string for full-text search."""
        return " ".join([self.palette, self.fonts, self.spacing, self.mood]).strip()


def now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:50].rstrip("-") or "entry"


def new_id(title: str, salt: str = "") -> str:
    """Readable, stable-ish id: 'glass-pricing-card-3f9a1c'.

    The short hash keeps ids unique when two entries share a title.
    """
    digest = hashlib.sha1(f"{title}|{salt}|{now().isoformat()}".encode()).hexdigest()[:6]
    return f"{slugify(title)}-{digest}"


class Entry(BaseModel):
    id: str
    title: str = Field(min_length=1)
    source: str = ""
    url: str = ""
    license: str = LINK_ONLY
    type: EntryType
    tags: list[str] = []
    framework: Framework = Framework.none
    style_notes: StyleNotes = StyleNotes()
    notes: str = ""  # your free-form notes (or the page description if you gave none)
    code: str | None = None
    prompt: str | None = None
    preview_image_url: str | None = None  # hotlinked, never downloaded
    local_image: str | None = None  # e.g. "assets/mine/hero.png" (relative to library/)
    when_to_use: str = ""
    avoid_when: str = ""
    my_rating: int = Field(default=3, ge=1, le=5)
    favorite: bool = False
    added_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

    @field_validator("id")
    @classmethod
    def id_is_safe_filename(cls, value: str) -> str:
        # The id becomes a filename, so keep it to [a-z0-9-].
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value):
            raise ValueError("id may only contain lowercase letters, digits and '-'")
        return value

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, tags: list[str]) -> list[str]:
        cleaned: list[str] = []
        for tag in tags:
            tag = re.sub(r"\s+", "-", tag.strip().lower())  # "hover effect" -> "hover-effect"
            if tag and tag not in cleaned:
                cleaned.append(tag)
        return cleaned

    @field_validator("local_image")
    @classmethod
    def image_inside_assets(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.replace("\\", "/")
        if not value.startswith("assets/mine/") or ".." in value:
            raise ValueError("local_image must be a path under assets/mine/")
        return value

    @model_validator(mode="after")
    def code_needs_open_license(self) -> "Entry":
        if self.code and self.license not in OPEN_LICENSES:
            raise ValueError(
                f"code can only be stored for open licenses {sorted(OPEN_LICENSES)}, "
                f"got license={self.license!r}"
            )
        return self
