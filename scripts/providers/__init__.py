"""Provider registry. Add new backends here."""

from __future__ import annotations

from .base import GeneratedImage, ImageRequest, Provider, ProviderConfig, ProviderError
from .openai import OpenAIProvider

PROVIDERS: dict[str, type[Provider]] = {
    OpenAIProvider.name: OpenAIProvider,
}


def get_provider(name: str, config: ProviderConfig) -> Provider:
    try:
        cls = PROVIDERS[name.strip().lower()]
    except KeyError:
        supported = ", ".join(sorted(PROVIDERS))
        raise ProviderError(f"unknown provider {name!r}; supported: {supported}") from None
    return cls(config)


__all__ = [
    "GeneratedImage",
    "ImageRequest",
    "Provider",
    "ProviderConfig",
    "ProviderError",
    "PROVIDERS",
    "get_provider",
]
