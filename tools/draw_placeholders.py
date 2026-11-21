"""Placeholder art for arenas that don't have the user's own textures yet (original, procedural).

Usage:  python -I tools/draw_placeholders.py
Writes (only files that are missing: bump a version when what a file holds changes, TTS caches by link):
  arenas/illusio/textures/grass1.png, grass2.png  island tops: short grass, two variants
  arenas/illusio/textures/stone.png              the raised high ground: pale lavender stone
  arenas/illusio/textures/rock.png               cliffs and the islands' undersides: layered rock, seamless left-right
  misc/sky-placeholder-v1.jpg                    table image under floating islands: sky and soft clouds
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

REPO = Path(__file__).resolve().parent.parent
N = 512


def noise(h, w, cells, rng, wrap_x=False):
    """Smooth value noise in 0..1: a random grid of cells^2 values, upsampled. wrap_x makes it seamless left-right."""
    gh, gw = max(2, cells), max(2, cells)
    if not wrap_x:
        grid = rng.random((gh + 1, gw + 1))
        img = Image.fromarray((grid * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        return np.asarray(img, np.float32) / 255
    grid = np.tile(rng.random((gh + 1, gw)), (1, 3))          # three periods side by side; keep the middle one
    img = Image.fromarray((grid * 255).astype(np.uint8)).resize((3 * w, h), Image.BICUBIC)
    return np.asarray(img, np.float32)[:, w:2 * w] / 255


def fbm(h, w, rng, base=4, octaves=5, wrap_x=False):
    out, amp, total = np.zeros((h, w), np.float32), 1.0, 0.0
    for o in range(octaves):
        out += amp * noise(h, w, base * 2 ** o, rng, wrap_x)
        total += amp
        amp *= 0.5
    return out / total


def mix(a, b, t):
    a, b = np.array(a, np.float32), np.array(b, np.float32)
    return a + (b - a) * t[..., None]


def to_img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


def grass(seed):
    rng = np.random.default_rng(seed)
    t = fbm(N, N, rng, 3)
    img = mix((70, 118, 44), (128, 176, 74), np.clip((t - 0.3) * 2.2, 0, 1))
    img *= (0.92 + 0.16 * fbm(N, N, rng, 16, 3))[..., None]
    out = to_img(img)
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(2600):                                   # blades: short strokes, mostly upright-ish
        x, y = rng.random() * N, rng.random() * N
        ang = rng.normal(-np.pi / 2, 0.6)
        ln = rng.uniform(5, 13)
        light = rng.random() < 0.5
        col = (160, 205, 100, 120) if light else (40, 80, 28, 120)
        d.line([(x, y), (x + ln * np.cos(ang), y + ln * np.sin(ang))], fill=col, width=2)
    return out.filter(ImageFilter.GaussianBlur(0.5))


def stone():
    rng = np.random.default_rng(31)
    t = fbm(N, N, rng, 3)
    img = mix((160, 152, 178), (206, 200, 218), t)
    img *= (0.94 + 0.12 * fbm(N, N, rng, 24, 2))[..., None]
    out = to_img(img)
    d = ImageDraw.Draw(out, "RGBA")
    for _ in range(7):                                      # hairline cracks: short random walks
        x, y = rng.random() * N, rng.random() * N
        ang = rng.random() * 2 * np.pi
        pts = [(x, y)]
        for _ in range(rng.integers(6, 14)):
            ang += rng.normal(0, 0.5)
            x, y = x + 12 * np.cos(ang), y + 12 * np.sin(ang)
            pts.append((x, y))
        d.line(pts, fill=(90, 82, 104, 110), width=2)
    for _ in range(500):                                    # speckles
        x, y = rng.random() * N, rng.random() * N
        r = rng.uniform(0.8, 2.2)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(120, 110, 140, 90) if rng.random() < 0.6 else (235, 230, 245, 90))
    return out.filter(ImageFilter.GaussianBlur(0.4))


def rock():
    """Layered rock: bands along the rows, wavy, seamless left-right (wall slices sit side by side)."""
    rng = np.random.default_rng(47)
    h, w = 1024, N
    warp = fbm(h, w, rng, 3, 4, wrap_x=True)
    rows = np.arange(h, dtype=np.float32)[:, None] / h
    bands = 0.5 + 0.5 * np.sin((rows * 9 + warp * 1.6) * 2 * np.pi)
    t = 0.55 * bands + 0.45 * fbm(h, w, rng, 6, 4, wrap_x=True)
    img = mix((78, 68, 84), (138, 126, 142), t)
    img *= (0.9 + 0.2 * fbm(h, w, rng, 32, 2, wrap_x=True))[..., None]
    return to_img(img).filter(ImageFilter.GaussianBlur(0.6))


def sky():
    """Looking down past the islands: blue, lighter toward the middle, with soft drifting clouds."""
    rng = np.random.default_rng(5)
    h, w = 1211, 2048
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    img = mix((150, 196, 238), (92, 146, 214), np.clip(r / 1.3, 0, 1))
    c = fbm(h, w, rng, 5, 6)
    cloud = np.clip((c - 0.5) / 0.22, 0, 1) ** 1.5
    img = img + (np.array((252, 252, 255), np.float32) - img) * (0.85 * cloud)[..., None]
    shade = np.clip((fbm(h, w, rng, 10, 3) - 0.5) * 0.25, -0.1, 0.1)
    img *= (1 + shade * cloud)[..., None]
    return to_img(img)


def main():
    files = {
        "arenas/illusio/textures/grass1.png": lambda p: grass(1).save(p),
        "arenas/illusio/textures/grass2.png": lambda p: grass(2).save(p),
        "arenas/illusio/textures/stone.png": lambda p: stone().save(p),
        "arenas/illusio/textures/rock.png": lambda p: rock().save(p),
        "misc/sky-placeholder-v1.jpg": lambda p: sky().save(p, quality=90),
    }
    for rel, make in files.items():
        path = REPO / rel
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            make(path)
            print("wrote", rel)


if __name__ == "__main__":
    main()
