<div align="center">

# motion-skill

**A Claude Code skill that makes 4K motion graphics videos with code. Claude drafts a numbered storyboard, renders the video after you approve it, then adds music and sound effects on the beat. No AI video generation, no editing skills needed.**

[![Video tutorial · YouTube](https://img.shields.io/badge/video%20tutorial-YouTube-FF0000?logo=youtube&logoColor=white)](https://youtu.be/LmCttBxh5xg)
[![Video tutorial · Bilibili](https://img.shields.io/badge/video%20tutorial-Bilibili-00A1D6?logo=bilibili&logoColor=white)](https://www.bilibili.com/video/BV1n3s16fEkM)
[![CI](https://github.com/risingjerry/motion-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/risingjerry/motion-skill/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-7C5CFF.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/risingjerry/motion-skill?color=E8735F)](https://github.com/risingjerry/motion-skill/releases)

English · [简体中文](README.zh-CN.md)

![Example promo: a coin flips into an app icon, unfolds into a phone screen, then folds back into the icon and wordmark](docs/demo.gif)

</div>

The 10-second promo above (for "Tallybird", a made-up budgeting app) ships as the example in this repo. One command rebuilds it on your machine as a 4K video with sound. Every pixel comes from code and real assets — no image or video model is involved.

> **Coming from the video?** This is the free skill from the tutorial ([YouTube](https://youtu.be/LmCttBxh5xg) · [Bilibili](https://www.bilibili.com/video/BV1n3s16fEkM), in Chinese).
> The Apple Music, AirPods and Douyin case videos shown there use those brands' assets, so they can't ship in an open-source repo. The method behind them is all in this skill.

## Get started in three steps

**1. Install Claude Code** — the Claude desktop app's Code tab or the `claude` CLI both work.

**2. Paste this into Claude Code. It installs everything for you.**

```text
Install this skill: https://github.com/risingjerry/motion-skill
Follow the "Manual install" section of its README and put it in ~/.claude/skills/motion.
If Node.js, Python, ffmpeg or Chrome is missing, install it first (Homebrew on a Mac).
Then run the doctor check and the 1080p example, and show me the result.
```

For 3D product shots, also install the free [Blender](https://www.blender.org/download/). You never need to open it; Claude runs it in the background.

**3. Make a folder, add your assets, and say one sentence.**

1. Create a folder with your high-resolution logo (SVG or transparent PNG) and real screenshots of your app (blur out avatars, phone numbers and other personal info).
2. Open that folder in Claude Code.
3. Say:

```text
Use the motion skill to make a 10-second promo for my app. The assets are in this folder.
Show me a numbered storyboard first and wait for my OK.
Every shot should morph out of the previous one — no cross-dissolves.
```

You get a storyboard image first. Say what to change ("3 to 4 is too fast") until you like it, then let it render. Once the picture is final, drop your sound effects and music into the folder and ask Claude to place them on the beats.

## The 12 tips from the video, built in

Everything the tutorial teaches is the skill's default behavior. Repeating it in your prompt makes it even more reliable.

| # | Tip | What the skill does |
|---|---|---|
| 1 | Use real, high-res assets — no store promo images, no logo drawn from memory | Asks for the real logo and screenshots first; asks you when something is missing |
| 2 | Numbered storyboard first; build only after you approve | Draws a storyboard board (`render.mjs board`); no final render without your OK |
| 3 | Every shot morphs out of the last one — no cross-dissolves | Each storyboard cell says which shape becomes which; offers 2–3 options when you're unsure |
| 4 | Keep the action at the exact center of the frame | `layout_check.py` measures the subject's distance from center on every frame |
| 5 | Something is always moving | A slow push runs through the whole piece; no frozen frames |
| 6 | Picture first, sound last | Mixes only after the picture is locked, reading beats from the render's beat sheet |
| 7 | Add depth of field for a cinematic look | The 3D template blurs cards by their distance from focus |
| 8 | End on the app icon only — no slogan | Ends on the icon and wordmark |
| 9 | Words slide up into place one by one — no bounce, no per-character fades | `slideUp()`, with automatic Chinese word splitting |
| 10 | Let Claude write the Suno music prompt so the biggest hit lands on the icon | Writes the prompt from the cut's length and beats; after you generate it, `mix.py` aligns the hit, trims and sets loudness |
| 11 | One light in 3D scenes | The Blender studio script uses one light and a black background |
| 12 | Compare the animation with the real object, detail by detail | Same-angle renders next to real photos; scripts check collisions, lid seams and rotation speed |

A few more lessons from making the case videos: you need both music and sound effects (effects alone feel empty); one whoosh for everything gets boring; no strangers' faces or posts inside your UI shots; don't hard-cut from a pitch-black 3D shot into bright live footage. All of it is in [`references/`](references/).

## Manual install

Needs Node.js 20+, Python 3.9+, ffmpeg and Google Chrome (or Chromium). Blender is optional.

```bash
git clone https://github.com/risingjerry/motion-skill.git ~/.claude/skills/motion
cd ~/.claude/skills/motion
npm install
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/doctor.py
```

Every line of the doctor report should start with `OK`, and the last line says all required pieces are present. If something is missing, it prints how to install it. On Windows use `%USERPROFILE%\.claude\skills\motion` and `.venv\Scripts\` instead of `.venv/bin/`.

To use it in one project only, clone into `your-project/.claude/skills/motion` instead.

<details>
<summary>Install with <code>npx skills</code> instead</summary>

```bash
npx skills add risingjerry/motion-skill -g -a claude-code
cd ~/.claude/skills/motion
npm install
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

`-a claude-code` puts the skill in `~/.claude/skills/motion`. Without `-a`, the CLI asks which agents to install for. The skill runs its own scripts, so the `npm install` / `pip install` step is still needed in the installed folder.

</details>

## Run the example first

```bash
.venv/bin/python examples/minimal/build.py
```

It writes to `examples/minimal/out/`:

| File | What it is |
|---|---|
| `storyboard.png` | Numbered storyboard (on a real job, Claude stops here until you approve) |
| `ad.mp4` | 3840×2160, 30 fps silent cut |
| `frames.jpg` + `frames/` | 3 frames pulled from the 4K cut (full-size PNGs) |
| `ad-sound.mp4` | The cut with music and sound effects (video stream copied, not re-encoded) |
| `mix.wav` | The mix, -14 LUFS, true peak ≤ -1 dBTP |

The terminal prints the layout check (`LAYOUT_CHECK GREEN`) and a mix report (where the music's biggest hit lands and the loudness). Add `--scale 1` for a quick 1080p run.

![Storyboard: six numbered shots, each with timing, picture, action and how it turns into the next shot](docs/storyboard.png)

## Use with Claude Code, Codex and other agents

Once it is in `~/.claude/skills/motion`, Claude Code finds the skill by itself. More things to ask:

- "Use the motion skill to make a 12-second launch video for my budgeting app. The logo is `assets/logo.svg`, screenshots are in `assets/screens/`."
- "I have a GLB model of my earbuds case. Make a Blender single-light studio shot of it opening — show me the storyboard first."
- "Animate our logo for a 5-second intro, and make a 20-second explainer of how sync works using our real screenshots."
- "Slow down the morph from shot 3 to shot 4, and land the music's biggest hit on the icon."
- "The picture is final. Write a Suno prompt for the music so the loudest hit lands when the icon appears."
- "I put sound effects and music in the sound folder. Place them on the right beats."

Codex, Cursor and other agents read [`AGENTS.md`](AGENTS.md) at the repo root. The skill instructions ([`SKILL.md`](SKILL.md), [`references/`](references/)) are written in Chinese; Claude and other modern agents follow them fine in any language you talk to them in.

## What it does

1. **Asks, then collects real assets** — the real logo, real screenshots (personal info removed), brand colors. For a physical product, real photos first.
2. **Numbered storyboard, then waits for you** — `render.mjs board` draws one storyboard image. No final render without your OK.
3. **Builds the page** — starts from `templates/2d.html` (flat) or `templates/3d.html` (CSS 3D); every beat lives in one place.
4. **Checks frame by frame** — pulls 3–4 frames from every transition into a contact sheet; scripts measure whether text overlaps the subject and whether the subject stays centered; for 3D, mesh collisions, rotation speed and lid seams.
5. **Renders 4K only** — `render.mjs video --scale 2`.
6. **Adds sound last** — the music's biggest hit lands on the key moment, effects sit on the beats, music ducks under effects, loudness hits -14 LUFS.

The craft rules (every shot morphs out of the previous one, action stays at the center, the frame never freezes, one light for 3D, end on the icon and wordmark only…) are in [`SKILL.md`](SKILL.md) and [`references/`](references/).

## Three levels

| Level | On screen | Tools |
|---|---|---|
| 1. Flat motion | Real logo, screenshots and shapes morphing into each other | `templates/2d.html`, `scripts/render.mjs` |
| 2. Browser 3D + live footage | UI cards in 3D space with a moving camera; silhouette transitions into real footage | `templates/3d.html`, `scripts/silhouette.py` |
| 3. Blender studio | Physical product model, one light, real materials | `scripts/blender/studio.py`, `motion_check.py`, `seam_check.py` |

## Scripts

| Script | Purpose |
|---|---|
| `scripts/render.mjs` | HTML → stills / 4K mp4 / element position probe / storyboard board |
| `scripts/sheet.py` | Pull frames by time from the full-resolution cut into a contact sheet |
| `scripts/layout_check.py` | Text ≥ 40 px from the subject (at 4K), subject centered |
| `scripts/seam_check.py` | Seam offset between two parts at the real camera angle ≤ 1 px |
| `scripts/blender/studio.py` | Single-light studio + EEVEE/Cycles render; reads GLB/glTF/USDZ/OBJ/FBX/STL/PLY; `--demo` ships a sample model |
| `scripts/blender/motion_check.py` | Per-frame mesh collisions (BVH), angular speed ≤ 6°/frame, no speed jumps |
| `scripts/silhouette.py` | Person mask (macOS Vision, optional) → smooth vector silhouette, pulling out from a close-up |
| `scripts/audio/synth.py` | Code-synthesized sound-effect pack and music bed (royalty-free) |
| `scripts/audio/mix.py` | Align music to the hit, place effects on beats, sidechain ducking, loudness normalization, mux into the video |
| `scripts/encode.py` | PNG frames → mp4 |
| `scripts/doctor.py` | Dependency check (`--json` for agents) |

Check scripts print `... GREEN` or `... RED` on their last line and exit 0 (green), 1 (red) or 2 (usage error).

## Limits

- **Speed**: a 10-second HTML piece renders to 4K in about 1–3 minutes; Blender EEVEE at 4K takes a few to a dozen seconds per frame, so a 15-second 3D shot can take an hour. Run one 4K job at a time, or the machine may stall.
- **Automatic person masks need macOS 14+** (the built-in Vision framework). Elsewhere, export a black-and-white mask with rembg, MediaPipe or your editor; the silhouette script works the same.
- **Blender is optional**: levels 1 and 2 work without it.
- **Nobody "listened" to the mix**: scripts align timing and measure loudness, but whether it sounds good needs a human with headphones.
- **No brand assets, 3D models, sound libraries or music are included.** The example uses a hand-made SVG and code-synthesized sound. You need the rights to your own assets.
- Tested by the author on macOS; CI runs the tests and the example on Ubuntu.

## FAQ

### What is motion-skill?
A free, open-source (MIT) Claude skill for motion graphics. Installed in Claude Code, it makes Claude follow one fixed workflow for product videos: collect real assets → numbered storyboard → HTML page or Blender scene → frame-by-frame 4K render → self-check on extracted frames → music and sound effects aligned to the beats.

### Is it free? Do I need an account or API key?
The skill is free and needs no extra account or key; every script runs on your machine. You only need Claude Code itself (billed through your Claude plan). Sound libraries or music generators such as Suno are your own choice.

### Are the Apple Music, AirPods and Douyin videos from the tutorial in the repo?
No. They use those brands' logos, models and UI, which can't be redistributed. The repo ships the same technique as a made-up example (Tallybird), plus every rule and check script learned while making those videos.

### Can I mix in AI-generated images or video?
Yes. The skill never calls an image or video model by itself, but anything you put in the asset folder — including AI-generated images or clips — is used as an asset.

### Which Claude model should I use?
Any model available in Claude Code works. Newer, stronger models write more detailed animation and check their own frames more carefully.

### How do I make a product video or motion graphics without AI video generation?
Write the animation as code. Here each frame is an HTML page (or Blender scene) computed from time `t`; a headless browser captures every frame and ffmpeg encodes them to 4K. Changing "a bit slower here" means changing one number and re-rendering.

### Can Claude Code make videos?
Yes, with this skill. Claude writes the animation page, renders it with the bundled scripts, checks the frames itself and mixes the sound. You provide real assets and approve the storyboard.

### Do I need to know how to code or use Blender?
No. Claude writes the code and runs Blender in the background; you never open it. Your job is to supply real assets, look at the storyboard and give feedback.

### How long can the videos be?
It is designed for short pieces — launch videos, promos, logo intros, product shots, explainer segments; the rules were tuned on 8–20 second videos. Longer renders work, but the workflow (every shot morphs out of the previous one) suits short pieces.

### Why a storyboard first?
At the storyboard stage, changing a sentence changes a shot; after rendering, the same change means starting over. Numbered shots let you say exactly "3 to 4 is too fast".

### How does the music's climax land on the key moment?
`mix.py` finds the strongest hit in the music (or takes the second you give it) and shifts the whole track so that hit lands on the beat you name. It only shifts — no time-stretching, no pitch change.

### Can I use another brand's logo?
Only for brands you own or are allowed to use. Practice pieces must not pose as official work or be run as ads.

### Does it work on Windows or Linux?
The HTML rendering, check scripts, sound scripts and Blender parts are written to be cross-platform, and CI runs them on Linux. The author has only tested on macOS. Automatic person masks are macOS-only.

## Data and privacy

Everything runs on your machine. Nothing goes online (except `npm install` / `pip install` fetching dependencies), no file is uploaded, and no account or key is needed. Rendering uses a local headless browser with a fresh, empty profile, so it never reads your everyday browser data.

## Uninstall

```bash
rm -rf ~/.claude/skills/motion
```

## Support, contributing and security

Questions, bug reports and ideas are welcome in [Issues](https://github.com/risingjerry/motion-skill/issues) — include the output of `python3 scripts/doctor.py --json` and the failing command. See [CONTRIBUTING.md](CONTRIBUTING.md). Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## Credits

The idea was inspired by a video from Rourke (GenHQ): https://www.youtube.com/watch?v=cDb-wPq0Iyk. This project is not affiliated with Rourke or GenHQ; all text and code here were written independently.

## License

[MIT](LICENSE). The Tallybird name and logo in the example are made up and ship under MIT with the repo; the sounds `synth.py` generates are free for commercial use too.

---

If it helped you ship a video, a ⭐ helps others find it.

[![Star History Chart](https://api.star-history.com/svg?repos=risingjerry/motion-skill&type=Date)](https://star-history.com/#risingjerry/motion-skill&Date)
