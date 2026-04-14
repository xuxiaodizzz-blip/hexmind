# Sharing Assets

HexMind keeps its GitHub-facing visual assets under `docs/public/assets/`.

Current generated files:

- `hexmind-demo.gif`: animated README hero
- `hexmind-demo-poster.png`: static poster frame
- `hexmind-social-preview.png`: image intended for the repository social preview card

Regenerate them with:

```bash
python scripts/render_readme_demo_gif.py
```

Recommended GitHub setup after regeneration:

1. Open the repository settings page.
2. Navigate to the social preview section.
3. Upload `docs/public/assets/hexmind-social-preview.png`.

That image is optimized for repository link sharing on X, Discord, Slack, and similar surfaces.
