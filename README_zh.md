# Image Gen Skill

![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)

> [English](./README.md) | 简体中文

一个面向 AI 编程助手 (Claude Code, Codex, Cursor 等) 的 Agent Skill, 通过任意 OpenAI 兼容的图片接口 (`/v1/images/generations` 与 `/v1/images/edits`), 根据文字描述**生成新图片或编辑已有图片**.

助手会写好提示词, 调用随附的脚本, 把图片保存到本地, 检查生成效果, 然后告诉你文件路径.

## 目录

- [功能特性](#功能特性)
- [适用场景](#适用场景)
- [环境要求](#环境要求)
- [安装](#安装)
- [配置](#配置)
- [使用方法](#使用方法)
- [命令行参数](#命令行参数)
- [输出格式](#输出格式)
- [项目结构](#项目结构)
- [扩展新的服务商](#扩展新的服务商)
- [测试](#测试)
- [安全说明](#安全说明)

## 功能特性

- **生成与编辑**: 支持文生图, 也支持基于一张或多张参考图进行编辑.
- **兼容 OpenAI 接口**: 把 `IMAGE_GEN_BASE_URL` 指向 OpenAI 或任何兼容的网关即可.
- **零依赖**: 只用 Python 3.9+ 标准库, 不需要 `pip install`.
- **透明背景**: 可输出带 alpha 通道的 PNG, 适合图标, Logo, 精灵图.
- **尺寸灵活**: 支持任意 `宽x高`, 宽高比在 1:3 到 3:1 之间.
- **不覆盖已有文件**: 同名文件已存在时自动加 `-2`, `-3` 等后缀. 扩展名按接口实际返回的数据决定 (`.png`, `.jpg`, `.webp`).
- **自动重试**: 遇到超时, 限流 (429) 和 5xx 错误时按指数退避重试.
- **服务商可扩展**: 新增一个服务商只需写一个 Python 类, 命令行用法不变.

## 适用场景

| 场景 | 示例需求 |
| --- | --- |
| 日常生图 | "画一只在窗台上晒太阳的橘猫" |
| 图片编辑 | "把这张照片的背景换成海边, 人物不要变" |
| 开发前出设计稿 | "先帮我出一版这个记账 App 首页的设计稿看看" |
| 项目素材 | 应用图标, Logo, 空状态插画, 首屏背景, Banner, 占位图 |

每个场景的完整示例见 [references/prompting.md](references/prompting.md).

## 环境要求

- Python **3.9+**
- 一个 OpenAI 兼容图片接口的 API Key, 以及可用的模型 (如 `gpt-image-2`)

## 安装

使用 [`skills`](https://www.npmjs.com/package/skills) 命令行工具:

```bash
npx skills add https://github.com/chendefine/agent-skills --skill image-gen
```

也可以手动把 `image-gen` 目录复制到助手的 skills 目录:

| 助手 | Skill 目录 |
| --- | --- |
| Claude Code | `~/.claude/skills/image-gen` |
| Codex / 多助手共用 | `~/.agents/skills/image-gen` |
| 其他 | `<your_agent_skill_dir>/image-gen` |

## 配置

脚本**只从环境变量读取配置**, 自身不会加载任何 `.env` 文件. 变量名见 [`.env.example`](.env.example).

| 变量 | 必填 | 说明 |
| --- | --- | --- |
| `IMAGE_GEN_API_KEY` | 是 | 图片服务的 API Key |
| `IMAGE_GEN_BASE_URL` | 是 | 包含 `/v1` 的接口地址, 如 `https://api.openai.com/v1` |
| `IMAGE_GEN_MODEL` | 是 | 默认模型 ID, 如 `gpt-image-2` |
| `IMAGE_GEN_PROVIDER` | 否 | 服务商 ID, 默认 `openai` |
| `IMAGE_GEN_TIMEOUT` | 否 | 请求超时秒数, 默认 `300` |

写进 shell 配置文件, 助手启动时就会继承这些变量:

```bash
export IMAGE_GEN_PROVIDER=openai
export IMAGE_GEN_BASE_URL=https://api.openai.com/v1
export IMAGE_GEN_API_KEY=sk-...
export IMAGE_GEN_MODEL=gpt-image-2
```

也可以放在单独的 env 文件里, 只在执行某条命令时加载:

```bash
set -a; . /path/to/image-gen.env; set +a
python3 scripts/image_gen.py --prompt "..."
```

## 使用方法

### 通过助手使用

装好 skill 后, 直接用自然语言描述需求:

```text
给开发者工具 "Forge" 生成一个 1024x1024 的透明背景 Logo, 保存到 public/logo.png
```

助手会先读取项目上下文 (品牌色, 素材目录, 展示尺寸), 写好提示词, 执行脚本, 打开结果检查. 如果有问题, 会在原图上编辑修正.

### 直接在命令行使用

脚本也可以单独使用:

```bash
# 生成
python3 scripts/image_gen.py \
  --prompt "一只橘色虎斑猫坐在洒满午后阳光的窗台上, 眯着眼睛晒太阳, 温暖柔和的插画风格"

# 编辑已有图片
python3 scripts/image_gen.py \
  --input-image ./photo.jpg \
  --prompt "把背景替换为晴天的海边沙滩. 人物的姿势, 面部, 服装和光线方向保持不变." \
  --output ./photo-beach.png

# 直接输出到最终路径的透明素材
python3 scripts/image_gen.py \
  --size 1024x1024 --transparent --output public/logo.png \
  --prompt "开发者工具 'Forge' 的 Logo: 铁砧与代码括号结合的抽象图形, 扁平几何风格, 双色, 不含文字, 透明背景."
```

> [!NOTE]
> 一次请求通常需要 30–120 秒. 如果由助手或 CI 执行脚本, 请把命令超时设为至少 5 分钟.

## 命令行参数

```text
python3 scripts/image_gen.py --prompt TEXT [options]
```

| 参数 | 说明 |
| --- | --- |
| `--prompt TEXT` | **必填.** 要生成什么, 或要怎样修改输入图片. |
| `--input-image PATH` | 开启编辑模式. 可重复传入多张参考图. |
| `--n N` | 生成数量, 默认一张. |
| `--size WxH` | 输出尺寸, 宽高比 1:3 到 3:1 (如 `1536x1024`). 默认由模型决定. |
| `--transparent` | 请求透明背景 (带 alpha 通道的 PNG). |
| `--output PATH`, `-o` | 指定输出文件. 生成多张时依次为 `name-1.png`, `name-2.png` 等. |
| `--output-dir DIR` | 输出目录, 默认 `./generated-images`, 文件名为 `<时间戳>-<提示词摘要>.<扩展名>`. 不能和 `--output` 同时使用. |
| `--model ID` | 本次调用覆盖 `IMAGE_GEN_MODEL`. |

没有传的参数不会发给接口, 按服务端默认值处理. 尺寸较大时服务商可能会调整实际像素, 但宽高比不变.

## 输出格式

成功时脚本向 stdout 输出一个 JSON 对象:

```json
{
  "mode": "generate",
  "provider": "openai",
  "model": "gpt-image-2",
  "files": ["/abs/path/generated-images/20261012-153000-an-orange-tabby-cat.png"]
}
```

如果接口返回了改写后的提示词, JSON 中还会有 `revised_prompts` 字段.

失败时脚本以退出码 `1` 结束, 并在 stderr 输出 `image_gen: error: <信息>`, 其中包含接口返回的原始错误信息.

## 项目结构

```text
image-gen/
├── SKILL.md                 # 助手加载的指令
├── agents/openai.yaml       # Codex 类助手的展示信息
├── references/prompting.md  # 各场景的提示词示例
├── scripts/
│   ├── image_gen.py         # 命令行入口
│   ├── test_image_gen.py    # 离线测试
│   └── providers/
│       ├── __init__.py      # 服务商注册表
│       ├── base.py          # 服务商接口与公共类型
│       └── openai.py        # OpenAI 兼容的 Images API 实现
└── .env.example             # 配置变量名
```

## 扩展新的服务商

1. 在 [`scripts/providers/base.py`](scripts/providers/base.py) 中继承 `Provider`, 实现 `generate()` 和 `edit()`, 两者都返回 `GeneratedImage` 列表.
2. 在 [`scripts/providers/__init__.py`](scripts/providers/__init__.py) 的 `PROVIDERS` 中注册该类.
3. 通过 `IMAGE_GEN_PROVIDER=<name>` 选用.

命令行参数, JSON 输出格式和 `SKILL.md` 都不需要改动.

## 测试

测试离线运行, 不需要 API Key:

```bash
python3 scripts/test_image_gen.py
```

## 安全说明

- API Key 请放在环境变量或被 git 忽略的 env 文件中. `.env` 已在 `.gitignore` 中.
- Skill 会要求助手不得打印或回显 `IMAGE_GEN_API_KEY`.
- 输入图片会上传到 `IMAGE_GEN_BASE_URL` 指向的服务. 请只使用你信任的网关.
