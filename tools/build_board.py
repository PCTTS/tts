"""Build a 3D board for an arena from its map data: an OBJ model (every tile a block at its level) and its texture.

Usage:  python -I tools/build_board.py arenas/<name> [--out DIR] [--tag TAG] [--tile SIZE]
Writes <out>/board-<tag>.obj and <out>/board-<tag>.jpg (defaults: the arena's folder, tag "v1"), plus
<out>/board-<tag>.json describing the geometry (tile size, levels) for the TTS script.

--tile sets the tile size in world units (default 2.35); level heights and the base scale with it.

World layout (TTS units): the grid is centred on x = z = 0, row 0 is the far side (+z), the model's underside
is y = 0. Tiles outside the arena ("void") get no geometry, so the board has the arena's real outline.
TTS mirrors OBJ files on X when it loads them, so x is written negated.
"""
import json, math, random, sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

TILE = 2.35       # world units per tile (matches the old snap grid); --tile changes it
LEVEL_H = 0.7     # height of one level step at TILE 2.35 (scales with the tile size)
FLOOR0 = 0.3      # top of level 0 above the board's underside at TILE 2.35 (scales too)
PX = 128          # texture pixels per tile
SS = 2            # supersampling for the texture art
STRIP = 256       # texture rows under the tile area, used for the walls
DIRS = {"N": (-1, 0, (0, 0, 1)), "S": (1, 0, (0, 0, -1)), "E": (0, 1, (1, 0, 0)), "W": (0, -1, (-1, 0, 0))}


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def shade(rgb, k):
    return tuple(max(0, min(255, round(v * k))) for v in rgb)


def font(size, names=("arialbd.ttf", "seguibl.ttf")):
    for n in names:
        for d in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/msttcorefonts"), Path("/Library/Fonts")):
            if (d / n).exists():
                return ImageFont.truetype(str(d / n), size)
    return ImageFont.load_default(size)


class Arena:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.data = json.loads((self.folder / "map.json").read_text(encoding="utf-8"))
        self.grid = self.data["grid"]
        self.R, self.C = len(self.grid), len(self.grid[0])
        self.legend = self.data["legend"]
        self.palette = {k: hex_rgb(v) for k, v in self.data["palette"].items()}
        bad = {ch for row in self.grid for ch in row if ch not in self.legend}
        if bad or any(len(row) != self.C for row in self.grid):
            sys.exit(f"map.json: rows must all be {self.C} wide and use only legend characters (unknown: {bad})")
        self.max_level = max(t.get("level", 0) for t in self.legend.values() if not t.get("void"))

    def tile(self, r, c):
        if 0 <= r < self.R and 0 <= c < self.C:
            t = self.legend[self.grid[r][c]]
            return None if t.get("void") else t
        return None

    def top(self, t):
        return FLOOR0 + t.get("level", 0) * LEVEL_H


# ------------------------------------------------------------------------------------------------ texture
def surface_layers(a, p):
    """Surfaces textured with an image (map.json "textures": {surface: {"image": path, "span": tiles, "vary": bool}}):
    the image is scaled so one copy covers `span` tiles and repeated across the board (span 1 = one copy per tile).
    With "vary", every copy is turned and mirrored at random so the repetition doesn't show. With "match", the
    image is recoloured so its average equals the surface's palette colour (e.g. the same dirt, darker in a pit).
    Returns surface -> board-sized image."""
    layers = {}
    for surface, spec in (a.data.get("textures") or {}).items():
        src = Image.open(a.folder / spec["image"]).convert("RGB")
        if spec.get("match"):  # recolour so the image's average equals this surface's palette colour
            mean = src.resize((1, 1), Image.BOX).getpixel((0, 0))
            want = a.palette[surface]
            src = Image.merge("RGB", [band.point(lambda v, k=want[i] / max(1, mean[i]): min(255, round(v * k)))
                                      for i, band in enumerate(src.split())])
        size = round(spec.get("span", max(a.R, a.C)) * p)
        tile = src.resize((size, size), Image.LANCZOS)
        # "vary": each copy gets a random quarter-turn and mirror (fixed per position, so rebuilds match)
        variants = [v for t in (tile, tile.transpose(Image.FLIP_LEFT_RIGHT)) for v in
                    (t, t.transpose(Image.ROTATE_90), t.transpose(Image.ROTATE_180), t.transpose(Image.ROTATE_270))]
        rnd = random.Random(f"{a.data.get('name')}/{surface}")
        layer = Image.new("RGB", (a.C * p, a.R * p))
        for y in range(0, a.R * p, size):
            for x in range(0, a.C * p, size):
                layer.paste(rnd.choice(variants) if spec.get("vary") else tile, (x, y))
        layers[surface] = layer
    return layers


def draw_texture(a):
    W, H = a.C * PX * SS, (a.R * PX + STRIP) * SS
    p = PX * SS
    img = Image.new("RGB", (W, H), a.palette["cliff"])
    d = ImageDraw.Draw(img)
    rnd = random.Random(1)
    layers = surface_layers(a, p)
    for r in range(a.R):
        for c in range(a.C):
            t = a.tile(r, c)
            if t:
                surface = t.get("surface", "floor")
                box = [c * p, r * p, (c + 1) * p, (r + 1) * p]
                if surface in layers:   # an image texture: this tile shows its own part of it
                    img.paste(layers[surface].crop(box), box[:2])
                else:
                    base = a.palette[surface]
                    d.rectangle([box[0], box[1], box[2] - 1, box[3] - 1], fill=shade(base, rnd.uniform(0.96, 1.04)))
    # walls: rock with horizontal strata, darker toward the bottom
    y0 = a.R * p
    for y in range(STRIP * SS):
        k = 0.78 + 0.22 * (1 - y / (STRIP * SS))
        d.line([(0, y0 + y), (W, y0 + y)], fill=shade(a.palette["cliff"], k))
    for y in range(y0 + 6 * SS, H, 15 * SS):
        wob = [(x, y + round(2 * SS * math.sin(x / (37.0 * SS) + y))) for x in range(0, W + 1, 16 * SS)]
        d.line(wob, fill=shade(a.palette["cliff"], 0.7), width=2 * SS)
    # fine grain everywhere
    noise = Image.effect_noise((W, H), 9).convert("RGB")
    img = ImageChops.add(img, noise, 1.0, -128)

    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    o = ImageDraw.Draw(over)
    for r in range(a.R):
        for c in range(a.C):
            t = a.tile(r, c)
            if not t:
                continue
            x0, y0t = c * p, r * p
            # slab bevel: light top/left, dark bottom/right; thin grout line
            o.line([(x0, y0t + 2 * SS), (x0 + p, y0t + 2 * SS)], fill=(255, 255, 255, 60), width=2 * SS)
            o.line([(x0 + 2 * SS, y0t), (x0 + 2 * SS, y0t + p)], fill=(255, 255, 255, 60), width=2 * SS)
            o.line([(x0, y0t + p - 3 * SS), (x0 + p, y0t + p - 3 * SS)], fill=(0, 0, 0, 55), width=2 * SS)
            o.line([(x0 + p - 3 * SS, y0t), (x0 + p - 3 * SS, y0t + p)], fill=(0, 0, 0, 55), width=2 * SS)
            o.rectangle([x0, y0t, x0 + p - 1, y0t + p - 1], outline=(40, 28, 18, 110), width=SS)
            if t.get("surface") == "stairs":
                draw_steps(o, a, r, c, x0, y0t, p)
            draw_marker(o, t.get("marker"), x0, y0t, p)
    for r, c, side in a.data.get("edges", {}).get("fall", []):
        x0, y0t, w = c * p, r * p, 11 * SS
        box = {"N": [x0, y0t, x0 + p, y0t + w], "S": [x0, y0t + p - w, x0 + p, y0t + p],
               "W": [x0, y0t, x0 + w, y0t + p], "E": [x0 + p - w, y0t, x0 + p, y0t + p]}[side]
        o.rectangle(box, fill=a.palette["fall"] + (235,))
    img = Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")
    return img.resize((W // SS, H // SS), Image.LANCZOS)


def draw_steps(o, a, r, c, x0, y0, p):
    """Step lines parallel to the edge(s) facing lower ground. One low side: straight lines. Two adjacent low
    sides (a corner staircase): nested L's whose corners point at the low corner. Opposite sides: no lines."""
    level = a.tile(r, c).get("level", 0)
    low = {s for s, (dr, dc, _) in DIRS.items() if (a.tile(r + dr, c + dc) or {}).get("level", 99) < level}
    horiz = [s for s in ("N", "S") if s in low]   # low side above/below -> horizontal step lines
    vert = [s for s in ("E", "W") if s in low]    # low side left/right -> vertical step lines
    if len(horiz) > 1 or len(vert) > 1:
        return
    dark, light = (60, 40, 25, 90), (255, 245, 225, 52)  # light enough for the surface texture to show through
    for k in (0.28, 0.52, 0.76):
        d = round(k * p)
        yc = (y0 + d if horiz[0] == "N" else y0 + p - d) if horiz else None
        xc = (x0 + d if vert[0] == "W" else x0 + p - d) if vert else None
        segs = []
        if yc is not None:  # runs from the high side to the corner (or the whole width)
            xa, xb = (x0, x0 + p) if xc is None else ((x0, xc) if vert[0] == "E" else (xc, x0 + p))
            segs.append(((xa, yc), (xb, yc)))
        if xc is not None:
            ya, yb = (y0, y0 + p) if yc is None else ((y0, yc) if horiz[0] == "S" else (yc, y0 + p))
            segs.append(((xc, ya), (xc, yb)))
        for (ax, ay), (bx, by) in segs:
            o.line([(ax, ay), (bx, by)], fill=dark, width=3 * SS)
            off = (0, 3 * SS) if ay == by else (3 * SS, 0)
            o.line([(ax + off[0], ay + off[1]), (bx + off[0], by + off[1])], fill=light, width=2 * SS)


def draw_marker(o, marker, x0, y0, p):
    if not marker:
        return
    cx, cy, u = x0 + p / 2, y0 + p / 2, p / 128  # u = one design pixel
    ink = (45, 32, 22, 255)
    if marker.startswith("spawn"):
        col = (47, 111, 214, 255) if marker == "spawn1" else (214, 69, 47, 255)
        r = 40 * u
        o.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 70), outline=col, width=round(7 * u))
        o.text((cx, cy + 2 * u), marker[-1], font=font(round(46 * u)), fill=col, anchor="mm")
    elif marker == "flag":
        o.ellipse([cx - 22 * u, cy + 30 * u, cx + 22 * u, cy + 42 * u], fill=(0, 0, 0, 70))
        o.rectangle([cx - 4 * u, cy - 40 * u, cx + 3 * u, cy + 36 * u], fill=ink)
        o.polygon([(cx + 3 * u, cy - 40 * u), (cx + 44 * u, cy - 26 * u), (cx + 3 * u, cy - 10 * u)],
                  fill=(246, 246, 240, 255), outline=ink)
    elif marker.startswith("bell"):
        gold, deep = (226, 178, 60, 255), (150, 105, 30, 255)
        o.ellipse([cx - 26 * u, cy - 44 * u, cx + 26 * u, cy - 6 * u], fill=gold, outline=ink, width=round(3 * u))
        o.polygon([(cx - 26 * u, cy - 24 * u), (cx + 26 * u, cy - 24 * u), (cx + 36 * u, cy + 8 * u), (cx - 36 * u, cy + 8 * u)],
                  fill=gold, outline=ink)
        o.rectangle([cx - 37 * u, cy + 4 * u, cx + 37 * u, cy + 11 * u], fill=deep, outline=ink)
        o.ellipse([cx - 7 * u, cy + 9 * u, cx + 7 * u, cy + 21 * u], fill=deep, outline=ink)
        attack = marker.endswith("attack")
        o.text((cx, cy + 40 * u), "ATK" if attack else "DEF", font=font(round(24 * u)),
               fill=(192, 57, 43, 255) if attack else (47, 111, 214, 255), anchor="mm", stroke_width=round(2 * u),
               stroke_fill=(255, 255, 255, 220))


# ------------------------------------------------------------------------------------------------ model
class Mesh:
    def __init__(self):
        self.v, self.vt, self.vn, self.f = [], [], [], []

    def quad(self, corners, uvs, normal):
        """corners/normal in TTS world space; written to OBJ with x negated, wound so the face points along normal."""
        pts = [(-x, y, z) for x, y, z in corners]
        n = (-normal[0], normal[1], normal[2])
        e1 = [pts[1][i] - pts[0][i] for i in range(3)]
        e2 = [pts[2][i] - pts[0][i] for i in range(3)]
        cross = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        order = [0, 1, 2, 3] if sum(cross[i] * n[i] for i in range(3)) > 0 else [3, 2, 1, 0]
        base_v, base_t = len(self.v), len(self.vt)
        self.v += [pts[i] for i in order]
        self.vt += [uvs[i] for i in order]
        self.vn.append(n)
        ni = len(self.vn)
        a, b, c, d = (base_v + 1, base_v + 2, base_v + 3, base_v + 4)
        ta, tb, tc, td = (base_t + 1, base_t + 2, base_t + 3, base_t + 4)
        self.f.append(((a, ta), (b, tb), (c, tc)))
        self.f.append(((a, ta), (c, tc), (d, td)))
        self.f[-2] = tuple((vi, ti, ni) for vi, ti in self.f[-2])
        self.f[-1] = tuple((vi, ti, ni) for vi, ti in self.f[-1])

    def write(self, path):
        lines = ["# PCTTS board, made by tools/build_board.py"]
        lines += [f"v {x:.4f} {y:.4f} {z:.4f}" for x, y, z in self.v]
        lines += [f"vt {u:.5f} {v:.5f}" for u, v in self.vt]
        lines += [f"vn {x:.4f} {y:.4f} {z:.4f}" for x, y, z in self.vn]
        lines += ["f " + " ".join(f"{vi}/{ti}/{ni}" for vi, ti, ni in face) for face in self.f]
        Path(path).write_text("\n".join(lines) + "\n", encoding="ascii")


def build_mesh(a):
    W, H = a.C * PX, a.R * PX + STRIP
    y_span = FLOOR0 + a.max_level * LEVEL_H
    m = Mesh()

    def x(c):
        return (c - a.C / 2) * TILE

    def z(r):
        return (a.R / 2 - r) * TILE

    def wall_uv(u_px, y):
        return u_px / W, 1 - (a.R * PX + STRIP * (1 - y / y_span)) / H

    for r in range(a.R):
        for c in range(a.C):
            t = a.tile(r, c)
            if not t:
                continue
            top = a.top(t)
            x0, x1, z0, z1 = x(c), x(c + 1), z(r), z(r + 1)  # z0 is the far (+z) edge
            u0, u1 = (c * PX + 1) / W, ((c + 1) * PX - 1) / W
            v0, v1 = 1 - (r * PX + 1) / H, 1 - ((r + 1) * PX - 1) / H
            m.quad([(x0, top, z0), (x1, top, z0), (x1, top, z1), (x0, top, z1)],
                   [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], (0, 1, 0))
            bu = (0.5, 1 - (H - 2) / H)
            m.quad([(x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1)], [bu] * 4, (0, -1, 0))
            for side, (dr, dc, normal) in DIRS.items():
                nb = a.tile(r + dr, c + dc)
                low = a.top(nb) if nb else 0.0
                if low >= top:
                    continue
                if side == "N":
                    edge = [(x0, z0), (x1, z0)]
                elif side == "S":
                    edge = [(x1, z1), (x0, z1)]
                elif side == "E":
                    edge = [(x1, z0), (x1, z1)]
                else:
                    edge = [(x0, z1), (x0, z0)]
                (ax, az), (bx, bz) = edge
                us = ((r * 5 + c * 3 + len(side)) % a.C) * PX
                m.quad([(ax, top, az), (bx, top, bz), (bx, low, bz), (ax, low, az)],
                       [wall_uv(us, top), wall_uv(us + PX - 1, top), wall_uv(us + PX - 1, low), wall_uv(us, low)], normal)
    return m


def main(argv):
    if not argv:
        sys.exit(__doc__)
    folder = Path(argv[0])
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else folder
    tag = argv[argv.index("--tag") + 1] if "--tag" in argv else "v1"
    if "--tile" in argv:
        global TILE, LEVEL_H, FLOOR0
        k = float(argv[argv.index("--tile") + 1]) / TILE
        TILE, LEVEL_H, FLOOR0 = TILE * k, LEVEL_H * k, FLOOR0 * k
    out.mkdir(parents=True, exist_ok=True)
    a = Arena(folder)
    mesh = build_mesh(a)
    mesh.write(out / f"board-{tag}.obj")
    draw_texture(a).save(out / f"board-{tag}.jpg", quality=95)
    levels = [[(a.tile(r, c) or {}).get("level", -1) for c in range(a.C)] for r in range(a.R)]
    info = {"name": a.data["name"], "rows": a.R, "cols": a.C, "tile": TILE, "level_height": LEVEL_H,
            "floor0": FLOOR0, "levels": levels}
    (out / f"board-{tag}.json").write_text(json.dumps(info), encoding="utf-8")
    print(f"{a.data['name']}: {a.R}x{a.C} tiles, {len(mesh.f)} triangles -> {out / f'board-{tag}'}.obj/.jpg/.json")


if __name__ == "__main__":
    main(sys.argv[1:])
