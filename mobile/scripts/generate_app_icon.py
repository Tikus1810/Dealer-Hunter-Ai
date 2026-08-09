"""Generates windows/runner/resources/app_icon.ico from BrandMark's own
design (gradient squircle + wolf silhouette + AI-spark badge), so the
Windows taskbar/title-bar icon matches the in-app brand mark instead of
Flutter's default template icon — pure-Python (svgelements + Pillow,
no Cairo/GTK), rendered at 512px and downsampled per ICO size for
anti-aliased edges.

Run manually when `assets/branding/wolf_howl.svg` or the icon's palette
changes: `python scripts/generate_app_icon.py`. Not part of the Flutter
build itself — this is a design asset, not user data, checked in as the
already-generated .ico (see CLAUDE.md: no placeholder code — this is a
genuinely one-off asset build script, not a stub for a missing feature).
"""

from pathlib import Path

from PIL import Image, ImageDraw
from svgelements import SVG, Path as SvgPath

ROOT = Path(__file__).resolve().parent.parent
WOLF_SVG = ROOT / "assets" / "branding" / "wolf_howl.svg"
OUT_ICO = ROOT / "windows" / "runner" / "resources" / "app_icon.ico"

RENDER_SIZE = 512
SEED = (10, 132, 255)  # AppColors.seed, #0A84FF
SEED_LIGHT = (144, 199, 255)  # Color.lerp(seed, white, 0.22) approximation


def flatten_subpath(subpath, steps_per_segment=24):
    """Flattens by sampling each segment's own (fast, closed-form)
    parametrization directly, rather than `Path.point()` — that goes
    through arc-length reparametrization across the *whole* path, which
    falls back to a numeric-integration path without numpy installed and
    is orders of magnitude slower for no visual benefit here (this is a
    fixed rasterization for an icon, not an animation that needs evenly
    spaced points)."""
    p = SvgPath(subpath)
    points = []
    for segment in p:
        if segment.__class__.__name__ == "Move":
            continue
        for i in range(steps_per_segment + 1):
            points.append(segment.point(i / steps_per_segment))
    return points


def draw_wolf(canvas: Image.Image, box):
    """Draws the wolf silhouette (from wolf_howl.svg's two subpaths)
    scaled/centered into `box` (left, top, right, bottom)."""
    svg = SVG.parse(str(WOLF_SVG))
    path_el = next(el for el in svg.elements() if isinstance(el, SvgPath))
    subpaths = list(path_el.as_subpaths())

    left, top, right, bottom = box
    w, h = right - left, bottom - top
    scale = min(w, h) / 512

    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for subpath in subpaths:
        pts = flatten_subpath(subpath)
        poly = [(left + pt.real * scale, top + pt.imag * scale) for pt in pts]
        draw.polygon(poly, fill=(0, 0, 0, 255))
    canvas.alpha_composite(layer)


def draw_gradient_squircle(size: int, corner_ratio: float) -> Image.Image:
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gradient = Image.new("RGBA", (size, size))
    gpix = gradient.load()
    for y in range(size):
        for x in range(size):
            t = (x / size + y / size) / 2  # topLeft -> bottomRight
            r = round(SEED_LIGHT[0] + (SEED[0] - SEED_LIGHT[0]) * t)
            g = round(SEED_LIGHT[1] + (SEED[1] - SEED_LIGHT[1]) * t)
            b = round(SEED_LIGHT[2] + (SEED[2] - SEED_LIGHT[2]) * t)
            gpix[x, y] = (r, g, b, 255)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=int(size * corner_ratio), fill=255
    )
    base.paste(gradient, (0, 0), mask)
    return base


def draw_spark(canvas: Image.Image, cx, cy, r, color):
    pull = r * 0.16
    draw = ImageDraw.Draw(canvas)
    pts = []
    steps = 24

    def quad(p0, p1, p2, t):
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
        return (x, y)

    corners = [
        (cx, cy - r),
        (cx + r, cy),
        (cx, cy + r),
        (cx - r, cy),
    ]
    controls = [
        (cx + pull, cy - pull),
        (cx + pull, cy + pull),
        (cx - pull, cy + pull),
        (cx - pull, cy - pull),
    ]
    for i in range(4):
        p0 = corners[i]
        p1 = controls[i]
        p2 = corners[(i + 1) % 4]
        for s in range(steps):
            pts.append(quad(p0, p1, p2, s / steps))
    draw.polygon(pts, fill=color)


def build_icon() -> Image.Image:
    size = RENDER_SIZE
    canvas = draw_gradient_squircle(size, corner_ratio=0.28)
    pad = int(size * 0.2)
    draw_wolf(canvas, (pad, pad, size - pad, size - pad))

    badge_d = int(size * 0.36)
    badge_cx = size - int(size * 0.08) - badge_d // 2
    badge_cy = size - int(size * 0.08) - badge_d // 2
    draw = ImageDraw.Draw(canvas)
    draw.ellipse(
        (badge_cx - badge_d // 2, badge_cy - badge_d // 2, badge_cx + badge_d // 2, badge_cy + badge_d // 2),
        fill=(255, 255, 255, 255),
    )
    draw_spark(canvas, badge_cx, badge_cy, badge_d * 0.32, SEED + (255,))
    return canvas


def main():
    icon = build_icon()
    sizes = [16, 24, 32, 48, 64, 128, 256]
    OUT_ICO.parent.mkdir(parents=True, exist_ok=True)
    # Pass the *full-resolution* source and let Pillow's ICO writer
    # downsample to each requested size itself.
    icon.save(OUT_ICO, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"Wrote {OUT_ICO} ({OUT_ICO.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
