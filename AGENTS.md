# AGENTS.md

Guidance for coding agents working **on** this repository. For how the skill is *used*, read [SKILL.md](SKILL.md) (loaded by agents at runtime) and [README.md](README.md) (for humans).

## What this is

`image-gen` is an agent skill. An agent reads `SKILL.md`, writes a prompt, and runs `scripts/image_gen.py` to generate or edit images. The script calls an image provider, saves the files, and prints a JSON summary.

```text
SKILL.md                    runtime instructions for the agent (frontmatter + body)
agents/openai.yaml          display metadata (English)
references/prompting.md     scenario prompt examples, linked from SKILL.md
scripts/image_gen.py        CLI: args, validation, env settings, output paths, JSON summary
scripts/providers/base.py   Provider ABC, ImageRequest, GeneratedImage, ProviderConfig, ProviderError
scripts/providers/__init__.py  PROVIDERS registry + get_provider()
scripts/providers/openai.py    OpenAI-compatible /images/generations (JSON) and /images/edits (multipart)
scripts/test_image_gen.py   offline unittest suite with a local stub HTTP server
README.md / README_zh.md    user docs (keep both in sync)
.env.example                configuration variable names
```

## Commands

```bash
python3 -I scripts/test_image_gen.py   # offline tests, no API key, ~1s
python3 scripts/image_gen.py --help
```

For a live check, load `.env` into the environment of that one command only (the script never reads it):

```bash
(set -a; . ./.env; set +a; python3 scripts/image_gen.py --prompt "..." --output-dir /tmp/out)
```

Live calls take 30–120s each; use a timeout of at least 5 minutes. Remove `__pycache__/` after running tests.

## Design rules (do not break these)

- **Python 3.9+, standard library only.** No third-party packages, no `requirements.txt`.
- **CLI parameters are fixed:** `--prompt` (required), `--model` (falls back to `IMAGE_GEN_MODEL`; one of the two is required), `--input-image` (repeatable), `--n`, `--size`, `--transparent`, `--output` / `--output-dir`. Don't add flags (quality, format, mask, dry-run, etc.) unless asked.
- **Unset optionals are never sent to the API.** The request body holds `model` and `prompt` plus only the options the caller gave. `--transparent` maps to `background=transparent`.
- **`--size` is free-form `WxH`.** It is not an enum; only the aspect ratio is checked, and it must be between 1:3 and 3:1.
- **Configuration comes only from the process environment** (`IMAGE_GEN_PROVIDER`, `_BASE_URL`, `_API_KEY`, `_MODEL`, `_TIMEOUT`). The script must never load `.env`. That file exists only for local testing.
- **Output:** never overwrite files (add a `-2`, `-3` suffix); the extension comes from the image bytes; stdout is exactly one JSON object; errors go to stderr as `image_gen: error: ...` with exit code 1.
- **Providers are pluggable.** A new vendor is a `Provider` subclass in `scripts/providers/<name>.py` plus one entry in `PROVIDERS`. The CLI, the JSON output, and `SKILL.md` stay unchanged.

## Documentation rules

- **`SKILL.md` frontmatter `description`** only says *when* to trigger the skill. Don't name OpenAI, specific endpoints, or vendors.
- **`SKILL.md` body** never mentions environment variables or setup. On missing configuration it points the user to the README. Environment details belong in `README.md` / `README_zh.md`.
- **`--model`:** `SKILL.md` tells the agent not to pass it unless the user explicitly names a model. Examples leave it out.
- **Prompt guidance:** describe requirements and expectations in plain sentences, with no "magic words" or keyword stuffing. The model optimizes prompts itself.
- **Keep docs in sync with the CLI.** When you change behavior, update `SKILL.md`, both READMEs, `references/prompting.md` if examples are affected, and the tests.

## Testing conventions

- Tests run the CLI in-process through `main(argv, environ)`, against a local `HTTPServer` stub. They never touch the network and never read the real environment.
- Each behavior change needs a test that asserts on the exact request the stub received: JSON fields, multipart field names (`image` vs `image[]`), and that absent options really are absent.

## Security

- Never print, log, or commit `IMAGE_GEN_API_KEY` or the contents of `.env` (it is git-ignored).
- Don't hardcode real keys or private gateway URLs in code, tests, or docs. Use `.env.example`-style placeholders.
