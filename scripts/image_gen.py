#!/usr/bin/env python3
"""Generate or edit images through a configurable image provider.

Configuration is read only from the process environment (set by the caller):
  IMAGE_GEN_PROVIDER   provider id (default: openai)
  IMAGE_GEN_BASE_URL   API base URL, e.g. https://api.openai.com/v1
  IMAGE_GEN_API_KEY    API key
  IMAGE_GEN_MODEL      model id used unless --model is given
  IMAGE_GEN_TIMEOUT    request timeout in seconds (default: 300)

Prints one JSON object describing the saved files to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from providers import ImageRequest, ProviderConfig, ProviderError, get_provider  # noqa: E402

DEFAULT_OUTPUT_DIR = "generated-images"
SIZE_PATTERN = re.compile(r"^(\d+)x(\d+)$")
MAX_ASPECT = 3.0


class UsageError(Exception):
    pass


def resolve_settings(environ) -> dict[str, str]:
    return {k: v.strip() for k, v in environ.items() if k.startswith("IMAGE_GEN_") and v and v.strip()}


def parse_size(value: str) -> str:
    match = SIZE_PATTERN.match(value.strip().lower())
    if not match:
        raise UsageError(f"--size must look like WIDTHxHEIGHT (e.g. 1536x1024), got {value!r}")
    width, height = int(match[1]), int(match[2])
    if width <= 0 or height <= 0:
        raise UsageError("--size width and height must be positive")
    ratio = width / height
    if ratio > MAX_ASPECT or ratio < 1 / MAX_ASPECT:
        raise UsageError(f"--size aspect ratio must be between 1:3 and 3:1, got {width}x{height}")
    return f"{width}x{height}"


def slugify(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^\w]+", "-", text.lower(), flags=re.UNICODE).strip("-_")
    return slug[:limit].rstrip("-_") or "image"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(2, 10_000):
        candidate = path.with_name(f"{path.stem}-{i}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise UsageError(f"could not find a free filename near {path}")


def plan_paths(count: int, extensions: list[str], prompt: str, output: str | None, output_dir: str | None) -> list[Path]:
    if output:
        target = Path(output).expanduser()
        stem, parent = target.stem, target.parent
        names = [stem] if count == 1 else [f"{stem}-{i}" for i in range(1, count + 1)]
    else:
        parent = Path(output_dir or DEFAULT_OUTPUT_DIR).expanduser()
        base = f"{datetime.now():%Y%m%d-%H%M%S}-{slugify(prompt)}"
        names = [base] if count == 1 else [f"{base}-{i}" for i in range(1, count + 1)]
    return [parent / f"{name}.{ext}" for name, ext in zip(names, extensions)]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate images, or edit input images, via the configured provider.",
    )
    parser.add_argument("--prompt", required=True, help="what to generate / how to edit (required)")
    parser.add_argument("--model", help="model id; defaults to IMAGE_GEN_MODEL")
    parser.add_argument(
        "--input-image", "--input_image", dest="input_images", action="append", default=[],
        metavar="PATH", help="input image for editing; repeat for multiple images",
    )
    parser.add_argument("--n", "-n", type=int, help="number of images to generate")
    parser.add_argument("--size", help="WIDTHxHEIGHT, aspect ratio between 1:3 and 3:1")
    parser.add_argument("--transparent", action="store_true", help="request a transparent background")
    out = parser.add_mutually_exclusive_group()
    out.add_argument("--output", "-o", help="output file path (numbered when more than one image)")
    out.add_argument(
        "--output-dir", "--output_dir", dest="output_dir",
        help=f"output directory (default: ./{DEFAULT_OUTPUT_DIR})",
    )
    return parser


def main(argv: list[str] | None = None, environ: dict[str, str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = resolve_settings(os.environ if environ is None else environ)

    try:
        prompt = args.prompt.strip()
        if not prompt:
            raise UsageError("--prompt must not be empty")
        if args.n is not None and args.n < 1:
            raise UsageError("--n must be at least 1")
        size = parse_size(args.size) if args.size else None

        images = []
        for raw in args.input_images:
            path = Path(raw).expanduser()
            if not path.is_file():
                raise UsageError(f"input image not found: {raw}")
            images.append(path)

        model = args.model or settings.get("IMAGE_GEN_MODEL")
        missing = [
            name for name, value in (
                ("IMAGE_GEN_BASE_URL", settings.get("IMAGE_GEN_BASE_URL")),
                ("IMAGE_GEN_API_KEY", settings.get("IMAGE_GEN_API_KEY")),
                ("IMAGE_GEN_MODEL (or --model)", model),
            ) if not value
        ]
        if missing:
            raise UsageError(
                f"missing environment variables: {', '.join(missing)}. "
                "Pass them in the environment of this command (see .env.example for the names)."
            )

        provider_name = settings.get("IMAGE_GEN_PROVIDER") or "openai"
        provider = get_provider(
            provider_name,
            ProviderConfig(
                base_url=settings["IMAGE_GEN_BASE_URL"],
                api_key=settings["IMAGE_GEN_API_KEY"],
                timeout=float(settings.get("IMAGE_GEN_TIMEOUT") or 300),
            ),
        )
        request = ImageRequest(
            model=model, prompt=prompt, images=images, n=args.n, size=size, transparent=args.transparent,
        )
        results = provider.run(request)

        paths = plan_paths(len(results), [r.extension for r in results], prompt, args.output, args.output_dir)
        saved = []
        for result, path in zip(results, paths):
            path.parent.mkdir(parents=True, exist_ok=True)
            path = unique_path(path)
            path.write_bytes(result.data)
            saved.append(str(path.resolve()))
    except (UsageError, ProviderError, OSError, ValueError) as err:
        print(f"image_gen: error: {err}", file=sys.stderr)
        return 1

    summary = {
        "mode": "edit" if request.is_edit else "generate",
        "provider": provider.name,
        "model": model,
        "files": saved,
    }
    revised = [r.revised_prompt for r in results if r.revised_prompt]
    if revised:
        summary["revised_prompts"] = revised
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
