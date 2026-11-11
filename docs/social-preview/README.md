# Social preview kit

Source for `docs/social-preview.jpg` (1280x640, the GitHub social preview card). The icon and wordmark stay inside the centered square, so chat apps that crop link previews to a square don't cut them off.

## Rebuild

Needs Python 3 and Google Chrome or Chromium.

```bash
python3 docs/social-preview/render.py
```

Defaults use the files in this folder. Override with `--background`, `--icon`, `--name "Line1|Line2"`, `--tagline`, `--out`.
Then upload `docs/social-preview.jpg` in Settings > General > Social preview (GitHub requires < 1 MB).

## Background prompt

`background.jpg` was generated with Codex image generation:

> Abstract expressive oil painting filling the whole frame, wide 16:9: thick visible brushstrokes, canvas texture, soft painterly blending, diagonal sweeping strokes, editorial OpenAI-blog-cover aesthetic. ABSOLUTELY NO text, letters, logos, symbols, faces or objects. Keep the center calmer and mid-tone so white text stays readable. Palette: deep violet and indigo family with accents of coral, pink, turquoise and golden yellow.

## Credits

- Icon: `clapperboard` from [Lucide](https://lucide.dev) (ISC license), rendered white.
- Background: AI-generated, no third-party artwork.
