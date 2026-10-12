---
name: image-gen
description: Generate new images or edit existing ones from a text prompt. Use when the user asks to create, draw, render, or modify a picture; when sketching UI/page/app design mockups before implementation; or when a project needs image assets such as icons, logos, illustrations, backgrounds, banners, placeholders, or transparent PNGs.
---

# Image Gen

Turn a request into one call of the bundled script, save the result to disk, look at it, and report the file path.

## Run

Python 3.9+, standard library only:

```bash
python3 <skill_dir>/scripts/image_gen.py --prompt "<clear description>" [options]
```

| Option | Required | Description |
| --- | --- | --- |
| `--prompt` | yes | What to generate, or how to change the input images. |
| `--input-image PATH` | no | Switches to edit mode. Repeat for several reference images (first one is usually the image being edited). |
| `--n N` | no | Number of images. Omit for one. |
| `--size WxH` | no | Any `WIDTHxHEIGHT` whose aspect ratio is between 1:3 and 3:1, e.g. `1024x1024`, `1536x1024`, `1024x1536`. Omit to let the model choose. |
| `--transparent` | no | Request a transparent background (PNG with alpha). For icons, logos, sprites, stickers. |
| `--output PATH` | no | Exact output file. With several images it becomes `name-1.png`, `name-2.png`, … |
| `--output-dir DIR` | no | Output directory (default `./generated-images`); files are named `<timestamp>.<ext>`. |
| `--model ID` | no | Do **not** pass this unless the user explicitly names a model; the configured default model is used otherwise. |

Only pass optional flags the request actually needs; anything omitted is left to the server's defaults.

Behavior worth knowing:

- The provider may adjust pixel dimensions (e.g. a large `3072x1024` request can come back as `2172x724`); the aspect ratio is kept. Resize in code if exact pixels matter.
- Existing files are never overwritten; a `-2`, `-3`, … suffix is added instead.
- The file extension follows the bytes the API returned (`.png`, `.jpg`, `.webp`), even if `--output` named another one.
- A call usually takes 30–120 seconds. Use a generous command timeout (≥ 5 minutes) and do not retry just because it is slow.
- On success stdout is JSON:

  ```json
  {"mode": "generate", "provider": "openai", "model": "…", "files": ["/abs/path/image.png"]}
  ```

  On failure the script exits non-zero and prints `image_gen: error: …` on stderr, including the API's own error message. Read it before retrying; do not loop on the same failing request. If it reports missing configuration, tell the user to set up the skill as described in its README; do not guess values.

## Write the prompt

The image model already expands and optimizes prompts. A good prompt states the requirement and the expected result in plain sentences. Do **not** add keyword soup ("masterpiece, 8k, best quality, trending…").

### Decide how much to change the user's words

First decide which of these situations you are in:

1. **The user asked for an image and the request is already specific.** Subject, style, and intent are clear and consistent. Pass the user's wording through almost as-is, in their language. Add only facts the model cannot know (exact text to render, target use, project colors) and a size or `--transparent` flag if needed. Do not restyle, embellish, or "improve" the idea; a rewrite tends to drift from what the user meant.
2. **The user asked for an image and the request is vague, ambiguous, or contradictory.** Examples: "make a logo" with no product, name, or style; "minimalist but packed with detail"; an edit where it's unclear which part should change. Each call costs time and money, so don't guess. Ask a short clarifying question before generating, ideally with 2–4 concrete options to pick from (style, mood, composition, layout), plus your recommended default. Ask only about what would change the result; settle minor details yourself.
3. **The image is a step inside a larger task.** The user's goal is something else (a web page, an app, a README, a slide deck, a game) and the image is an intermediate asset. Don't interrupt the user. Work out the requirements yourself from the task, the conversation, and the codebase, write a complete prompt following the guidance below, generate, check the result, and continue the main task. Mention the generated asset when you report the overall result.

### What a complete prompt covers

When you write or extend a prompt (mostly situation 3, partly 1), cover what applies:

- **Subject and content** – what must appear, including any exact text to render (in quotes).
- **Purpose and context** – where the image will be used (landing-page hero, app icon, README banner, empty-state illustration…). This lets the model pick sensible composition and detail.
- **Style** – what the user asked for or what the project already uses (e.g. flat vector, photo, 3D, pixel art; the project's brand colors). Don't invent a style the context doesn't support.
- **Composition** – layout, framing, empty space for overlay text, background.
- **Constraints** – what must not appear (no text, no device frame, no watermark), when it matters.
- **For edits** – what to change *and* what must stay unchanged; refer to multiple inputs by order ("the first image", "the logo in the second image").

Fill gaps from the conversation and the codebase (brand colors in CSS/Tailwind config, existing asset style, target dimensions) before asking. See [references/prompting.md](references/prompting.md) for scenario-specific examples.

## Scenarios

**Everyday generation / editing.** Save to the directory the user mentions, otherwise the default `./generated-images`. For edits, pass the user's file(s) via `--input-image`.

**Design drafts before development.** Generate mockups of pages, screens, or components to agree on direction before writing code. Describe the page's sections, content, and visual tone; use a size matching the target viewport (e.g. `1536x1024` desktop, `1024x1536` mobile). Save drafts somewhere obvious such as `docs/design/` or the location the user prefers. Offer `--n 2`–`3` when the user wants options. Iterate by editing the chosen draft rather than starting over.

**Assets during development.** Inspect the project first: where assets live (`public/`, `src/assets/`, `static/`…), naming conventions, and how the asset will be displayed. Write directly to the final path with `--output`, pick `--size` close to the rendered aspect ratio, and use `--transparent` for icons, logos, and anything placed over varying backgrounds. After saving, wire the asset into the code if that is part of the task.

## After generating

1. Open each output file with your image-viewing/Read tool and check it against the request (content, text spelling, transparency, layout).
2. If something is off, run an edit with the previous output as `--input-image` and a prompt describing only the correction.
3. Report the saved path(s) to the user. Mention `revised_prompts` from the JSON only if present and useful.

## Extending to other providers

Providers live in `scripts/providers/`. To add one, subclass `Provider` in `providers/base.py`, implement `generate()` and `edit()` for the vendor's API, and register the class in `providers/__init__.py`. The CLI and this document stay unchanged.

Run the offline tests with `python3 <skill_dir>/scripts/test_image_gen.py`.
