# Prompting examples

The image model optimizes prompts itself. Good prompts here are complete *requirements*, not stylistic incantations. Each example shows a user request, the context gathered, and the resulting command.

## Everyday generation

User: "画一只在窗台上晒太阳的橘猫"

```bash
python3 <skill_dir>/scripts/image_gen.py \
  --prompt "一只橘色虎斑猫坐在洒满午后阳光的窗台上, 眯着眼睛晒太阳, 温暖柔和的插画风格"
```

Keep the user's wording and intent; add only details that make the expectation explicit.

## Editing

User: "把这张照片的背景换成海边, 人物不要变" (`./photo.jpg`)

```bash
python3 <skill_dir>/scripts/image_gen.py \
  --input-image ./photo.jpg \
  --prompt "把背景替换为晴天的海边沙滩. 人物的姿势, 面部, 服装和光线方向保持不变." \
  --output ./photo-beach.png
```

Multiple inputs — say which image plays which role:

```bash
python3 <skill_dir>/scripts/image_gen.py \
  --input-image ./product.png --input-image ./logo.png \
  --prompt "Place the logo from the second image on the front of the box in the first image, sized to about one third of the box width. Keep everything else in the first image unchanged."
```

## Design drafts

User: "先帮我出一版这个记账 App 首页的设计稿看看"

Context gathered: React Native app, brand color `#16a34a` in `theme.ts`, home screen should show monthly balance, a spending chart, recent transactions.

```bash
python3 <skill_dir>/scripts/image_gen.py \
  --size 1024x1536 --n 2 --output docs/design/home.png \
  --prompt "Mobile app home screen design mockup for a personal bookkeeping app. Top: current month balance card with income and expense totals. Middle: a weekly spending bar chart. Bottom: list of recent transactions with category icons, names, dates, amounts. Bottom tab bar with Home, Stats, Add, Profile. Clean modern UI, light theme, primary color #16a34a, rounded cards, generous spacing. Flat screenshot of the screen only, no phone frame."
```

Tips:
- List sections top-to-bottom with the real content they hold; mention real labels/text when known.
- State the theme (light/dark), primary color, and density.
- Say "screenshot only, no device frame / no perspective" when the draft is meant to be implemented.
- After the user picks a direction, iterate with `--input-image` on that draft.

## Development assets

User: "空状态页需要一张插画"

Context gathered: `src/assets/illustrations/` holds SVG-like flat illustrations in indigo/slate, displayed at about 320×240 on a white card.

```bash
python3 <skill_dir>/scripts/image_gen.py \
  --size 1536x1152 --transparent --output src/assets/illustrations/empty-inbox.png \
  --prompt "Empty-state illustration for an inbox with no messages: an open, empty envelope tray with a small paper plane flying away. Flat vector style matching a minimal SaaS app, indigo and slate palette, no text, centered subject with even padding, transparent background."
```

App icon / logo:

```bash
python3 <skill_dir>/scripts/image_gen.py \
  --size 1024x1024 --transparent --output public/logo.png \
  --prompt "Logo mark for a developer tool named 'Forge': a stylized anvil combined with a code bracket. Flat, geometric, two colors (#0f172a and #f97316), centered, readable at 32px, no text, transparent background."
```

Banner / hero background with room for overlay text:

```bash
python3 <skill_dir>/scripts/image_gen.py \
  --size 3072x1024 --output public/images/hero-bg.png \
  --prompt "Wide abstract background for a website hero section, soft gradient waves in deep blue and teal. Keep the left half calm and low-contrast so white headline text placed there stays readable. No text, no logos."
```

Tips:
- Choose `--size` near the rendered aspect ratio (bounded to 1:3–3:1); scale down in code if needed.
- Use `--transparent` for anything placed on varying backgrounds.
- State "no text" when the UI will overlay its own text, or give the exact text in quotes when it must appear.
- Match the existing asset style; look at a few current assets before prompting.
