# Image Gen Skill

![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)

> English | [简体中文](./README_zh.md)

An agent skill that lets AI coding agents (Claude Code, Codex, Cursor, and others) **generate new images or edit existing ones** from a text prompt through any OpenAI-compatible image API (`/v1/images/generations` and `/v1/images/edits`).

The agent writes a clear prompt, calls one bundled script, saves the image to disk, checks the result, and reports the file path to you.

## Contents

- [Features](#features)
- [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [CLI Reference](#cli-reference)
- [Output](#output)
- [Project Structure](#project-structure)
- [Adding a Provider](#adding-a-provider)
- [Testing](#testing)
- [Security](#security)

## Features

- **Generate and edit**: text-to-image, plus edits based on one or more reference images.
- **Works with any OpenAI-compatible gateway**: point `IMAGE_GEN_BASE_URL` at OpenAI or at any compatible service.
- **No dependencies**: Python 3.9+ standard library only. Nothing to `pip install`.
- **Transparent backgrounds**: PNGs with an alpha channel for icons, logos, and sprites.
- **Flexible sizes**: any `WIDTHxHEIGHT` with an aspect ratio between 1:3 and 3:1.
- **Never overwrites files**: adds `-2`, `-3`, … to the name if the file already exists. The extension matches the bytes the API returned (`.png`, `.jpg`, `.webp`).
- **Automatic retries**: retries timeouts, rate limits (429), and 5xx errors with exponential backoff.
- **Pluggable providers**: add a new vendor with one Python class. The CLI stays the same.

## Use Cases

| Scenario | Example request |
| --- | --- |
| Everyday generation | "Draw an orange cat sunbathing on a windowsill" |
| Photo editing | "Replace the background of this photo with a beach, keep the person unchanged" |
| Design mockups before coding | "Show me a draft of the home screen for this bookkeeping app" |
| Project assets | App icons, logos, empty-state illustrations, hero backgrounds, banners, placeholders |

See [references/prompting.md](references/prompting.md) for complete examples of each scenario.

## Requirements

- Python **3.9+**
- An API key for an OpenAI-compatible image API, with a model such as `gpt-image-2`

## Installation

With the [`skills`](https://www.npmjs.com/package/skills) CLI:

```bash
npx skills add https://github.com/chendefine/agent-skills --skill image-gen
```

Or copy the `image-gen` directory into your agent's skills directory by hand:

| Agent | Skill directory |
| --- | --- |
| Claude Code | `~/.claude/skills/image-gen` |
| Codex / shared agents | `~/.agents/skills/image-gen` |
| Others | `<your_agent_skill_dir>/image-gen` |

## Configuration

The script reads its configuration **only from environment variables**. It never loads a `.env` file itself. Variable names are listed in [`.env.example`](.env.example).

| Variable | Required | Description |
| --- | --- | --- |
| `IMAGE_GEN_API_KEY` | yes | API key for the image provider |
| `IMAGE_GEN_BASE_URL` | yes | API base URL including `/v1`, e.g. `https://api.openai.com/v1` |
| `IMAGE_GEN_MODEL` | yes | Default model id, e.g. `gpt-image-2` |
| `IMAGE_GEN_PROVIDER` | no | Provider id. Default `openai` |
| `IMAGE_GEN_TIMEOUT` | no | Request timeout in seconds. Default `300` |

Export them in your shell profile so your agent inherits them:

```bash
export IMAGE_GEN_PROVIDER=openai
export IMAGE_GEN_BASE_URL=https://api.openai.com/v1
export IMAGE_GEN_API_KEY=sk-...
export IMAGE_GEN_MODEL=gpt-image-2
```

Or keep them in an env file and load it for a single command:

```bash
set -a; . /path/to/image-gen.env; set +a
python3 scripts/image_gen.py --prompt "..."
```

## Usage

### Through an agent

Once the skill is installed, describe what you want in plain language:

```text
Generate a 1024x1024 transparent logo for a developer tool called "Forge" and save it to public/logo.png
```

The agent reads the project for context (brand colors, asset folders, display size), writes the prompt, runs the script, opens the result to check it, and fixes it with an edit if something is off.

### From the command line

The script also works on its own:

```bash
# Generate
python3 scripts/image_gen.py \
  --prompt "An orange tabby cat sunbathing on a windowsill, warm soft illustration style"

# Edit an existing image
python3 scripts/image_gen.py \
  --input-image ./photo.jpg \
  --prompt "Replace the background with a sunny beach. Keep the person's pose, face, clothes, and lighting unchanged." \
  --output ./photo-beach.png

# Transparent asset at its final path
python3 scripts/image_gen.py \
  --size 1024x1024 --transparent --output public/logo.png \
  --prompt "Logo mark for a developer tool named 'Forge': a stylized anvil combined with a code bracket. Flat, geometric, two colors, no text, transparent background."
```

> [!NOTE]
> A request usually takes 30–120 seconds. If your agent or CI runs the script, give the command a timeout of at least 5 minutes.

## CLI Reference

```text
python3 scripts/image_gen.py --prompt TEXT [options]
```

| Option | Description |
| --- | --- |
| `--prompt TEXT` | **Required.** What to generate, or how to change the input images. |
| `--input-image PATH` | Turns on edit mode. Repeat for several reference images. |
| `--n N` | Number of images. Default: one. |
| `--size WxH` | Output size, aspect ratio between 1:3 and 3:1 (e.g. `1536x1024`). Default: chosen by the model. |
| `--transparent` | Ask for a transparent background (PNG with alpha). |
| `--output PATH`, `-o` | Exact output file. With several images: `name-1.png`, `name-2.png`, … |
| `--output-dir DIR` | Output directory. Default: `./generated-images`, files named `<timestamp>.<ext>` (e.g. `20261012-153000.png`). Cannot be used with `--output`. |
| `--model ID` | Overrides `IMAGE_GEN_MODEL` for this call. |

Any option you leave out is not sent, so the server's default applies. The provider may change the pixel size of large requests but keeps the aspect ratio.

## Output

On success the script prints one JSON object to stdout:

```json
{
  "mode": "generate",
  "provider": "openai",
  "model": "gpt-image-2",
  "files": ["/abs/path/generated-images/20261012-153000.png"]
}
```

If the API returns revised prompts, the object also has a `revised_prompts` field.

On failure the script exits with code `1` and prints `image_gen: error: <message>` to stderr. The message includes the API's own error text.

## Project Structure

```text
image-gen/
├── SKILL.md                 # Instructions the agent loads
├── agents/openai.yaml       # Display metadata for Codex-style agents
├── references/prompting.md  # Prompt examples by scenario
├── scripts/
│   ├── image_gen.py         # CLI entry point
│   ├── test_image_gen.py    # Offline tests
│   └── providers/
│       ├── __init__.py      # Provider registry
│       ├── base.py          # Provider interface and shared types
│       └── openai.py        # OpenAI-compatible Images API
└── .env.example             # Configuration variable names
```

## Adding a Provider

1. Subclass `Provider` in [`scripts/providers/base.py`](scripts/providers/base.py) and implement `generate()` and `edit()`. Both return a list of `GeneratedImage`.
2. Register the class in `PROVIDERS` in [`scripts/providers/__init__.py`](scripts/providers/__init__.py).
3. Select it with `IMAGE_GEN_PROVIDER=<name>`.

Nothing else needs to change: not the CLI flags, the JSON output, or `SKILL.md`.

## Testing

The tests run offline and need no API key:

```bash
python3 scripts/test_image_gen.py
```

## Security

- Keep your API key in environment variables or a git-ignored env file. `.env` is already in `.gitignore`.
- The skill tells the agent never to print or echo `IMAGE_GEN_API_KEY`.
- Input images are uploaded to the API at `IMAGE_GEN_BASE_URL`. Only use a gateway you trust.
