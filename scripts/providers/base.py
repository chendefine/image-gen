"""Provider-neutral request/response types and the Provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


class ProviderError(Exception):
    """Raised when a provider cannot fulfil a request."""


@dataclass
class ProviderConfig:
    base_url: str
    api_key: str
    timeout: float = 300.0
    max_retries: int = 2


@dataclass
class ImageRequest:
    model: str
    prompt: str
    images: list[Path] = field(default_factory=list)
    n: int | None = None
    size: str | None = None
    transparent: bool = False

    @property
    def is_edit(self) -> bool:
        return bool(self.images)


@dataclass
class GeneratedImage:
    data: bytes
    revised_prompt: str | None = None

    @property
    def extension(self) -> str:
        return detect_extension(self.data)


def detect_extension(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return "png"


class Provider(ABC):
    """An image generation backend.

    To add a vendor, subclass this, implement ``generate`` and ``edit``, and
    register the class in ``providers/__init__.py``.
    """

    name: str = ""

    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    def generate(self, request: ImageRequest) -> list[GeneratedImage]:
        """Create images from a text prompt."""

    @abstractmethod
    def edit(self, request: ImageRequest) -> list[GeneratedImage]:
        """Create images from a prompt plus one or more input images."""

    def run(self, request: ImageRequest) -> list[GeneratedImage]:
        return self.edit(request) if request.is_edit else self.generate(request)
