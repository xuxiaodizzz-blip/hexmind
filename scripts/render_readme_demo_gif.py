"""Render a lightweight animated GIF for the public README hero."""

from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "docs" / "public" / "assets"
GIF_PATH = OUTPUT_DIR / "hexmind-demo.gif"
POSTER_PATH = OUTPUT_DIR / "hexmind-demo-poster.png"

WIDTH = 960
HEIGHT = 600

BG = "#0b0f17"
BG_ALT = "#111827"
CARD = "#151a23"
CARD_ALT = "#1a2230"
BORDER = "#263041"
TEXT = "#f8fafc"
MUTED = "#9aa4b2"
ACCENT = "#00e5ff"
ACCENT_ALT = "#7c9cff"
SUCCESS = "#f8d44c"
RISK = "#ff6f91"


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    windows_font_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    candidates = [
        windows_font_dir / ("segoeuib.ttf" if bold else "segoeui.ttf"),
        windows_font_dir / ("arialbd.ttf" if bold else "arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


FONT_H1 = _load_font(40, bold=True)
FONT_H2 = _load_font(28, bold=True)
FONT_BODY = _load_font(18)
FONT_SMALL = _load_font(14)
FONT_TINY = _load_font(12)


def _new_canvas() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        mix = y / HEIGHT
        r = int(11 + (17 - 11) * mix)
        g = int(15 + (24 - 15) * mix)
        b = int(23 + (39 - 23) * mix)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((-120, -120, 360, 320), fill=(0, 229, 255, 28))
    glow_draw.ellipse((WIDTH - 380, HEIGHT - 300, WIDTH + 120, HEIGHT + 180), fill=(124, 156, 255, 24))
    glow = glow.filter(ImageFilter.GaussianBlur(72))
    return Image.alpha_composite(image.convert("RGBA"), glow).convert("RGB")


def _rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], *, fill: str, outline: str | None = None, radius: int = 18, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _chip(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, color: str) -> None:
    box = (x, y, x + 118, y + 30)
    _rounded(draw, box, fill=BG_ALT, outline=color, radius=15)
    draw.text((x + 14, y + 8), label, font=FONT_TINY, fill=color)


def _header(draw: ImageDraw.ImageDraw, pulse: float) -> None:
    _rounded(draw, (28, 22, WIDTH - 28, 82), fill="#0f1521", outline=BORDER, radius=22)
    _rounded(draw, (48, 38, 86, 66), fill="#0f1b27", outline="#1f9fb7", radius=14)
    draw.text((98, 34), "HexMind", font=FONT_H2, fill=TEXT)
    draw.text((208, 40), "Multi-expert AI decision engine", font=FONT_SMALL, fill=MUTED)
    pulse_alpha = int(170 + 80 * math.sin(pulse))
    draw.ellipse((770, 43, 786, 59), fill=(0, 229, 255, pulse_alpha))
    draw.text((800, 38), "Protocol live", font=FONT_SMALL, fill=ACCENT)


def _sidebar(draw: ImageDraw.ImageDraw, active_index: int) -> None:
    _rounded(draw, (28, 104, 228, HEIGHT - 28), fill="#0f1521", outline=BORDER, radius=24)
    draw.text((52, 132), "Modes", font=FONT_SMALL, fill=MUTED)
    labels = [
        ("White Hat", "#cde6ff"),
        ("Red Hat", RISK),
        ("Black Hat", "#f2f5f7"),
        ("Yellow Hat", SUCCESS),
        ("Green Hat", "#76f7b0"),
    ]
    for idx, (label, color) in enumerate(labels):
        y = 176 + idx * 62
        fill = CARD_ALT if idx == active_index else "#111826"
        outline = color if idx == active_index else BORDER
        _rounded(draw, (46, y, 210, y + 44), fill=fill, outline=outline, radius=16)
        draw.text((62, y + 12), label, font=FONT_SMALL, fill=color)
    draw.text((52, HEIGHT - 94), "Sample asset pack", font=FONT_SMALL, fill=MUTED)
    draw.text((52, HEIGHT - 68), "CLI + API + React UI", font=FONT_BODY, fill=TEXT)


def _persona_card(draw: ImageDraw.ImageDraw, x: int, y: int, title: str, subtitle: str, color: str, offset: int = 0) -> None:
    _rounded(draw, (x, y + offset, x + 190, y + 132 + offset), fill=CARD, outline=BORDER, radius=22)
    _rounded(draw, (x + 18, y + 18 + offset, x + 72, y + 56 + offset), fill="#0f1b27", outline=color, radius=16)
    draw.text((x + 88, y + 18 + offset), title, font=FONT_BODY, fill=TEXT)
    draw.text((x + 88, y + 46 + offset), subtitle, font=FONT_SMALL, fill=MUTED)
    draw.text((x + 18, y + 82 + offset), "View system prompt", font=FONT_SMALL, fill=color)
    draw.text((x + 18, y + 104 + offset), "Bias, domain, and debate style", font=FONT_SMALL, fill=MUTED)


def _scene_personas(frame: int) -> Image.Image:
    image = _new_canvas()
    draw = ImageDraw.Draw(image)
    _header(draw, frame * 0.35)
    _sidebar(draw, frame % 5)

    draw.text((268, 132), "Orchestrate a fleet of digital specialists", font=FONT_H1, fill=TEXT)
    draw.text((268, 186), "Compose domain personas, apply structured hats, and keep the reasoning trail replayable.", font=FONT_BODY, fill=MUTED)
    _chip(draw, 268, 228, "Open-core", ACCENT)
    _chip(draw, 394, 228, "Sample assets", SUCCESS)
    _chip(draw, 534, 228, "Local-first", ACCENT_ALT)

    bob = int(4 * math.sin(frame * 0.8))
    _persona_card(draw, 268, 288, "Backend Engineer", "Reliability and APIs", ACCENT, offset=-bob)
    _persona_card(draw, 482, 300, "Product Manager", "Scope and user value", SUCCESS, offset=bob)
    _persona_card(draw, 696, 288, "Facilitator", "Synthesis and next steps", ACCENT_ALT, offset=-bob)
    return image


def _message(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, title: str, body: str, color: str) -> None:
    _rounded(draw, (x, y, x + w, y + 78), fill=CARD, outline=BORDER, radius=18)
    draw.text((x + 16, y + 12), title, font=FONT_SMALL, fill=color)
    draw.text((x + 16, y + 38), body, font=FONT_SMALL, fill=MUTED)


def _scene_stream(frame: int) -> Image.Image:
    image = _new_canvas()
    draw = ImageDraw.Draw(image)
    _header(draw, 1.4 + frame * 0.4)
    _sidebar(draw, (frame + 2) % 5)

    _rounded(draw, (256, 104, 662, HEIGHT - 28), fill="#101826", outline=BORDER, radius=24)
    _rounded(draw, (680, 104, WIDTH - 28, HEIGHT - 28), fill="#101826", outline=BORDER, radius=24)
    draw.text((282, 132), "Live discussion stream", font=FONT_H2, fill=TEXT)
    draw.text((706, 132), "Decision summary", font=FONT_H2, fill=TEXT)

    pulse = frame % 4
    _message(draw, 282, 184, 352, "White Hat", "We need evidence on onboarding drop-off and baseline activation.", "#cde6ff")
    _message(draw, 308, 278, 326, "Black Hat", "Without guardrails, AI guidance may increase confusion and support load.", RISK)
    _message(draw, 282, 372, 352, "Green Hat", "Start with a narrow, milestone-based copilot before full rollout.", "#76f7b0")
    if pulse > 1:
        _message(draw, 308, 466, 326, "Yellow Hat", "A constrained pilot could improve activation without a full redesign.", SUCCESS)
    else:
        _rounded(draw, (308, 466, 634, 544), fill="#101826", outline="#193344", radius=18)
        draw.text((330, 496), "Streaming next synthesis...", font=FONT_SMALL, fill=ACCENT)

    draw.text((706, 186), "Question", font=FONT_SMALL, fill=MUTED)
    draw.text((706, 214), "Should we launch an AI-guided onboarding flow?", font=FONT_BODY, fill=TEXT)
    draw.text((706, 270), "Consensus", font=FONT_SMALL, fill=MUTED)
    draw.text((706, 298), "Pilot first, measure activation, then expand.", font=FONT_BODY, fill=TEXT)
    draw.text((706, 354), "Next steps", font=FONT_SMALL, fill=MUTED)
    steps = [
        "Define 1-2 onboarding milestones",
        "Gate AI guidance behind explicit entry points",
        "Track activation, confusion, and retention",
    ]
    for idx, step in enumerate(steps):
        draw.text((726, 386 + idx * 34), f"{idx + 1}. {step}", font=FONT_SMALL, fill=TEXT)
    return image


def _bar(draw: ImageDraw.ImageDraw, x: int, baseline: int, height: int, color: str) -> None:
    _rounded(draw, (x, baseline - height, x + 42, baseline), fill=color, radius=12)


def _scene_analytics(frame: int) -> Image.Image:
    image = _new_canvas()
    draw = ImageDraw.Draw(image)
    _header(draw, 2.4 + frame * 0.25)
    _sidebar(draw, (frame + 4) % 5)

    draw.text((268, 132), "Inspect the full decision trail", font=FONT_H1, fill=TEXT)
    draw.text((268, 186), "Archive discussions, compare persona contribution, and review confidence over time.", font=FONT_BODY, fill=MUTED)

    metric_boxes = [
        (268, 236, "Decisions mapped", "2.4M", ACCENT),
        (500, 236, "Consensus rate", "84%", SUCCESS),
        (732, 236, "Avg. debate time", "12s", ACCENT_ALT),
    ]
    for x, y, label, value, color in metric_boxes:
        _rounded(draw, (x, y, x + 184, y + 104), fill=CARD, outline=BORDER, radius=22)
        draw.text((x + 18, y + 20), label, font=FONT_SMALL, fill=MUTED)
        draw.text((x + 18, y + 52), value, font=FONT_H2, fill=color)

    _rounded(draw, (268, 364, 620, HEIGHT - 28), fill=CARD, outline=BORDER, radius=24)
    _rounded(draw, (640, 364, WIDTH - 28, HEIGHT - 28), fill=CARD, outline=BORDER, radius=24)
    draw.text((292, 392), "Hat activity", font=FONT_H2, fill=TEXT)
    draw.text((664, 392), "Convergence path", font=FONT_H2, fill=TEXT)

    baseline = 526
    heights = [
        84 + int(8 * math.sin(frame * 0.7)),
        62 + int(10 * math.sin(frame * 0.7 + 1.2)),
        110 + int(7 * math.sin(frame * 0.7 + 2.1)),
        74 + int(9 * math.sin(frame * 0.7 + 3.4)),
        92 + int(6 * math.sin(frame * 0.7 + 4.2)),
    ]
    colors = ["#cde6ff", RISK, "#f2f5f7", SUCCESS, "#76f7b0"]
    labels = ["W", "R", "B", "Y", "G"]
    for idx, (height, color, label) in enumerate(zip(heights, colors, labels)):
        x = 304 + idx * 58
        _bar(draw, x, baseline, height, color)
        draw.text((x + 14, baseline + 10), label, font=FONT_SMALL, fill=MUTED)

    points = [(684, 500), (740, 452), (792, 468), (848, 414), (904, 430)]
    draw.line(points, fill=ACCENT, width=4)
    for idx, point in enumerate(points):
        draw.ellipse((point[0] - 7, point[1] - 7, point[0] + 7, point[1] + 7), fill=ACCENT)
        if idx < len(points) - 1:
            draw.text((point[0] - 12, point[1] + 16), f"R{idx + 1}", font=FONT_TINY, fill=MUTED)
    draw.text((664, 438), "Disagreement narrows as roles share evidence, risks, and synthesis.", font=FONT_SMALL, fill=MUTED)
    return image


def build_demo_gif() -> tuple[Path, Path]:
    """Generate the README GIF and poster image."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = [
        *[_scene_personas(i) for i in range(4)],
        *[_scene_stream(i) for i in range(4)],
        *[_scene_analytics(i) for i in range(4)],
    ]
    durations = [220, 220, 220, 340] * 3
    frames[0].save(POSTER_PATH)
    frames[0].save(
        GIF_PATH,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    return GIF_PATH, POSTER_PATH


def main() -> None:
    gif_path, poster_path = build_demo_gif()
    print(f"GIF written to: {gif_path}")
    print(f"Poster written to: {poster_path}")


if __name__ == "__main__":
    main()
