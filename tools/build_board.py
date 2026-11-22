"""Build a 3D board for an arena from its map data: an OBJ model (every tile a block at its level) and its texture.

Usage:  python -I tools/build_board.py arenas/<name> [--out DIR] [--tag TAG] [--tile SIZE]
Writes <out>/board-<tag>.obj and <out>/board-<tag>.jpg (defaults: the arena's folder, tag "v1"), plus
<out>/board-<tag>.json describing the geometry (tile size, levels) for the TTS script.

--tile sets the tile size in world units (default 2.35); level heights and the base scale with it.

World layout (TTS units): the grid is centred on x = z = 0, row 0 is the far side (+z), the model's underside
is y = 0. Tiles outside the arena ("void") get no geometry, so the board has the arena's real outline.
TTS mirrors OBJ files on X when it loads them, so x is written negated.

Floating islands (map.json "float": {lift, cliff, depth, power, max}, world units): everything is lifted `lift`
above the table; where land meets the sky its edge drops `cliff`, and below that the rock hangs down, deeper the
farther a point is from the island's edge (depth * distance-in-tiles ^ power, at most `max`), so each island
tapers to rough points underneath. No geometry under the sky tiles.
"""
import json, math, random, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageStat

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
        self.float = self.data.get("float")
        self.lift = self.float.get("lift", 0.0) if self.float else 0.0

    def tile(self, r, c):
        if 0 <= r < self.R and 0 <= c < self.C:
            t = self.legend[self.grid[r][c]]
            return None if t.get("void") else t
        return None

    def floor0(self):
        """Top of level 0 above the model's underside."""
        return FLOOR0 + self.lift

    def top(self, t):
        """A tile's surface height ("sink" lowers the look only: rules-wise it stays at its level)."""
        return self.floor0() + t.get("level", 0) * LEVEL_H - t.get("sink", 0.0)

    def level_top(self, t):
        """The height of a tile's level (ignoring "sink")."""
        return self.floor0() + t.get("level", 0) * LEVEL_H

    def y_span(self):
        """The model's full height (the highest tile top)."""
        return self.floor0() + self.max_level * LEVEL_H

    def rim(self):
        """Floating islands: how high the cliff at an island's edge reaches down to (the underside starts there)."""
        return self.floor0() - self.float.get("cliff", 0.45)

    def away_from_pit(self, r, c):
        """The grid direction (dr, dc) pointing away from this tile's lower neighbours, or None if it has none."""
        t = self.tile(r, c)
        dr = dc = 0
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            n = self.tile(nr, nc)
            if n and n.get("level", 0) < t.get("level", 0):
                dr, dc = dr - (nr - r), dc - (nc - c)
        if not (dr or dc):
            return None
        return (0, 1 if dc > 0 else -1) if abs(dc) >= abs(dr) else (1 if dr > 0 else -1, 0)


# ------------------------------------------------------------------------------------------------ texture
def recolor(img, frm, to, amount):
    """Move one colour `amount` of the way toward another. Pixels count as that colour in proportion to how far
    their brightness sits between the two (so anti-aliased edges shift smoothly, without halos); pixels at least
    as bright as `to` are left alone."""
    def lum(c):
        return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    lf, lt = lum(frm), lum(to)
    delta = [to[i] - frm[i] for i in range(3)]
    out = []
    pixels = img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata()
    for px in pixels:
        t = max(0.0, min(1.0, (lt - lum(px)) / (lt - lf))) * amount
        out.append(tuple(max(0, min(255, round(px[i] + t * delta[i]))) for i in range(3)))
    res = Image.new("RGB", img.size)
    res.putdata(out)
    return res


def texture_choices(a, spec, surface, w, h):
    """The copies a texture spec can use, as [per image: [copies]], each w x h. "vary" gives every orientation
    (four quarter-turns, each also mirrored); "match" recolours to the palette colour of `surface`, or of the
    palette entry it names (e.g. "match": "stairs")."""
    choices = []
    for path in spec.get("images") or [spec["image"]]:
        src = Image.open(a.folder / path).convert("RGB")
        for rule in spec.get("recolor", []):
            src = recolor(src, hex_rgb(rule["from"]), hex_rgb(rule["to"]), rule.get("amount", 1.0))
        if spec.get("match"):
            typical = ImageStat.Stat(src).median   # the median ignores dark/light details, so they keep contrast
            key = spec["match"] if isinstance(spec["match"], str) else surface
            want = hex_rgb(key) if key.startswith("#") else a.palette[key]
            src = Image.merge("RGB", [band.point(lambda v, k=want[i] / max(1, typical[i]): min(255, round(v * k)))
                                      for i, band in enumerate(src.split())])
        variants = [src]
        if spec.get("vary"):
            variants = [v for t in (src, src.transpose(Image.FLIP_LEFT_RIGHT)) for v in
                        (t, t.transpose(Image.ROTATE_90), t.transpose(Image.ROTATE_180), t.transpose(Image.ROTATE_270))]
        choices.append([v.resize((w, h), Image.LANCZOS) for v in variants])
    return choices


def surface_layers(a, p):
    """Surfaces textured with images (map.json "textures": {surface: {...}}):
      "image": path, or "images": [paths] — with several, each copy picks one at random (equal chances)
      "span": tiles one copy covers (1 = one copy per tile); copies repeat across the board
      "vary": every copy gets a random quarter-turn and mirror, so the repetition doesn't show
      "match": recolour so each image's typical (median) colour equals the surface's palette colour (e.g. the same
               dirt, darker in a pit); details darker or lighter than the base keep their contrast
      "recolor": [{"from", "to", "amount"}] first moves a colour part of the way toward another
      "offset": [row, col] a copy's top-left corner lands on that tile (default the board's corner)
    Random choices are seeded by arena and surface, so rebuilds come out the same. Returns surface -> board image."""
    layers = {}
    for surface, spec in (a.data.get("textures") or {}).items():
        if surface == "walls":
            continue  # inner walls are textured in the wall strip (see draw_texture)
        size = round(spec.get("span", max(a.R, a.C)) * p)
        choices = texture_choices(a, spec, surface, size, size)
        rnd = random.Random(f"{a.data.get('name')}/{surface}")
        layer = Image.new("RGB", (a.C * p, a.R * p))
        oy, ox = (v * p % size for v in spec.get("offset", (0, 0)))
        for y in range(oy - size if oy else 0, a.R * p, size):
            for x in range(ox - size if ox else 0, a.C * p, size):
                layer.paste(rnd.choice(rnd.choice(choices)), (x, y))
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
    # wall strip, below the tiles. Left half: rock with horizontal strata, darker toward the bottom (outer walls).
    # Right half: the "walls" texture, if the map has one (inner walls); otherwise rock too. With "outer": true
    # in the walls texture, the left half (the board's outer edge) gets it as well.
    y0 = a.R * p
    for y in range(STRIP * SS):
        k = 0.78 + 0.22 * (1 - y / (STRIP * SS))
        d.line([(0, y0 + y), (W, y0 + y)], fill=shade(a.palette["cliff"], k))
    for y in range(y0 + 6 * SS, H, 15 * SS):
        wob = [(x, y + round(2 * SS * math.sin(x / (37.0 * SS) + y))) for x in range(0, W + 1, 16 * SS)]
        d.line(wob, fill=shade(a.palette["cliff"], 0.7), width=2 * SS)
    wall_spec = (a.data.get("textures") or {}).get("walls")
    if wall_spec:
        # one tile's worth of texture per slice, stretched so it looks the same scale on a wall as on a tile:
        # the strip spans the board's full height range, a slice one tile's width
        tall = round(STRIP * SS * TILE / a.y_span())
        choices = texture_choices(a, wall_spec, "walls", p, tall)
        rnd = random.Random(f"{a.data.get('name')}/walls")
        first = 0 if wall_spec.get("outer") else a.C // 2   # "outer": the board's outer edge uses it too
        for i in range(first, a.C):
            piece = rnd.choice(rnd.choice(choices))
            for k in range(0, STRIP * SS, tall):   # a tall board needs more than one copy down the strip
                img.paste(piece.crop((0, 0, p, min(tall, STRIP * SS - k))), (i * p, y0 + k))
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
            if t.get("outline"):
                draw_outline(over, a, r, c, x0, y0t, p)
            painted = painted_marker(t)
            if painted:
                turn = marker_turn(a, r, c, t)
                both = both_ways(a, t)
                if turn:   # drawn upright on its own layer, then turned so its bottom points the right way
                    layer = Image.new("RGBA", (p, p), (0, 0, 0, 0))
                    draw_marker(layer, painted, 0, 0, p, both)
                    over.alpha_composite(layer.rotate(turn), (x0, y0t))
                else:
                    draw_marker(over, painted, x0, y0t, p, both)
    # slopes (see slopes()): the tile's edge band, darkening toward the bottom of the slope. The shading is laid over
    # what's painted there, so the grid lines (each tile's edge lines) run on down the slopes.
    for r in range(a.R):
        for c in range(a.C):
            sloped = slopes(a, r, c) if a.tile(r, c) else {}
            if not sloped:
                continue
            band = a.tile(r, c)["slant"] / TILE * p
            x0, y0t = c * p, r * p
            dim = Image.new("RGBA", (p, p), (0, 0, 0, 0))
            sd = ImageDraw.Draw(dim)
            for i in range(round(band)):
                alpha = round(70 * (i / band) ** 1.5)   # i = distance down the slope from its top edge
                if "N" in sloped:
                    sd.line([(0, band - i), (p, band - i)], fill=(30, 18, 8, alpha))
                if "S" in sloped:
                    sd.line([(0, p - band + i), (p, p - band + i)], fill=(30, 18, 8, alpha))
                if "W" in sloped:
                    sd.line([(band - i, 0), (band - i, p)], fill=(30, 18, 8, alpha))
                if "E" in sloped:
                    sd.line([(p - band + i, 0), (p - band + i, p)], fill=(30, 18, 8, alpha))
            over.alpha_composite(dim, (x0, y0t))
    for r in range(a.R):   # inner corners: the same darkening around the corner point
        for c in range(a.C):
            inner = inner_corners(a, r, c) if a.tile(r, c) else {}
            if not inner:
                continue
            band = a.tile(r, c)["slant"] / TILE * p
            for corner in inner:
                cx = c * p + (p if corner[1] == "E" else 0)
                cy = r * p + (0 if corner[0] == "N" else p)
                bx0, by0 = int(cx - (band if corner[1] == "E" else 0)), int(cy - (0 if corner[0] == "N" else band))
                size = int(math.ceil(band))
                yy, xx = np.mgrid[by0:by0 + size, bx0:bx0 + size].astype(np.float32) + 0.5
                t = np.clip(1 - np.hypot(xx - cx, yy - cy) / band, 0, 1)
                alpha = np.round(70 * t ** 1.5).astype(np.uint8)
                dim = np.zeros((size, size, 4), np.uint8)
                dim[..., :3] = (30, 18, 8)
                dim[..., 3] = alpha
                over.alpha_composite(Image.fromarray(dim, "RGBA"), (bx0, by0))
    for r, c, text in a.data.get("spots", []):   # numbered spots, painted like field markings, facing the sides
        layer = Image.new("RGBA", (p, p), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        u = p / 128
        ld.ellipse([p / 2 - 36 * u, p / 2 - 36 * u, p / 2 + 36 * u, p / 2 + 36 * u], outline=(246, 246, 240, 215),
                   width=round(4 * u))
        ld.text((p / 2, p / 2 + 1 * u), str(text), font=font(round(36 * u)), fill=(246, 246, 240, 225), anchor="mm")
        over.alpha_composite(layer.rotate(MARKER_TURN[(0, -1) if c < a.C / 2 else (0, 1)]), (c * p, r * p))
    if a.data.get("coords"):
        draw_coords(over, a, p)
    for r, c, side in a.data.get("edges", {}).get("fall", []):
        x0, y0t, w = c * p, r * p, 11 * SS
        box = {"N": [x0, y0t, x0 + p, y0t + w], "S": [x0, y0t + p - w, x0 + p, y0t + p],
               "W": [x0, y0t, x0 + w, y0t + p], "E": [x0 + p - w, y0t, x0 + p, y0t + p]}[side]
        o.rectangle(box, fill=a.palette["fall"] + (235,))
    img = Image.alpha_composite(img.convert("RGBA"), over).convert("RGB")
    img = grass_fringe(a, img, layers, p)
    return img.resize((W // SS, H // SS), Image.LANCZOS)


FRINGE = {"reach": 0.42, "wobble": 0.3, "rough": 1.0, "tufts": 160}   # defaults (board v3's look)


def draw_coords(over, a, p):
    """Coordinates in the board's edge tiles: x = 1..C along both player edges (from player 1's left), y = 1..R up
    both side edges (from player 1's side). Each number faces out from its own edge (its bottom toward that edge).
    "coords": {"cols": [first, last], "rows": [first, last]} (tile indices) numbers only those columns/rows, from 1;
    "inset": how far in from the edge a number's centre sits, in tiles (default 0.15)."""
    spec = a.data["coords"]
    cols = range(a.C) if spec is True else range(spec["cols"][0], spec["cols"][1] + 1)
    rows = range(a.R) if spec is True else range(spec["rows"][0], spec["rows"][1] + 1)
    k = spec.get("inset", 0.15) if isinstance(spec, dict) else 0.15
    f = font(round(p * 0.15))
    size = round(p * 0.28)

    def label(text, cx, cy, edge):
        layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((size / 2, size / 2), text, font=f, fill=(236, 226, 208, 190), anchor="mm",
                                   stroke_width=max(1, round(p * 0.012)), stroke_fill=(0, 0, 0, 150))
        layer = layer.rotate(MARKER_TURN[edge])
        over.alpha_composite(layer, (round(cx - size / 2), round(cy - size / 2)))

    for c in cols:
        label(str(c - cols.start + 1), c * p + p / 2, (a.R - k) * p, (1, 0))     # player 1's edge
        label(str(c - cols.start + 1), c * p + p / 2, p * k, (-1, 0))            # player 2's edge
    for r in rows:
        label(str(rows.stop - r), p * k, r * p + p / 2, (0, -1))                  # left edge
        label(str(rows.stop - r), (a.C - k) * p, r * p + p / 2, (0, 1))           # right edge


def grass_fringe(a, img, layers, p):
    """Slanted tiles with "fringe": {"surface", "reach", "wobble", "rough", "tufts"} (or just the surface's
    name): that surface (the lawn around them) creeps up the bottom of each slope to `reach` (a fraction of the
    slope) give or take `wobble`; `rough` adds fine jaggedness to its top edge; `tufts` = blade tufts tried per
    slope, leaning up the slope just above the edge. The edge comes from a smooth function of the board position,
    so it runs on across tiles and corners."""
    rnd = random.Random(f"{a.data.get('name')}/fringe")
    phases = [(rnd.uniform(0, 6.3), rnd.uniform(0, 6.3)) for _ in range(6)]

    def ragged(gx, gy, rough):   # -1..1, wavy along any edge (gx, gy: board pixels at SS)
        u, v = gx / SS, gy / SS
        broad = sum(np.sin(u / w + a) * np.cos(v / (w * 1.3) + b) + np.sin((u + v) / (w * 0.8) + a + b)
                    for w, (a, b) in zip((9.0, 15.0, 26.0), phases[:3]))
        fine = sum(np.sin(u / w + a + v / (w * 0.7)) * np.cos(v / w - u / (w * 1.9) + b)
                   for w, (a, b) in zip((1.6, 2.5, 3.7), phases[3:]))
        return np.clip(broad / 3.2 + rough * fine / 4.5, -1, 1)

    tufts = Image.new("RGBA", img.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(tufts)
    out = np.asarray(img, np.float32).copy()
    for r in range(a.R):
        for c in range(a.C):
            t = a.tile(r, c)
            sloped = slopes(a, r, c) if t else {}
            if not (sloped and t.get("fringe")):
                continue
            spec = t["fringe"] if isinstance(t["fringe"], dict) else {"surface": t["fringe"]}
            f = {**FRINGE, **spec}
            band = t["slant"] / TILE * p

            def edge_at(gx, gy):   # how far up the slope the grass gets
                return band * (f["reach"] + f["wobble"] * ragged(gx, gy, f["rough"]))
            x0, y0 = c * p, r * p
            yy, xx = np.mgrid[0:p, 0:p].astype(np.float32) + 0.5
            dists = {"N": yy, "S": p - yy, "W": xx, "E": p - xx}
            d = np.minimum.reduce([dists[s] for s in sloped])
            for corner in inner_corners(a, r, c):   # and around inner corners
                d = np.minimum(d, np.hypot(xx - (p if corner[1] == "E" else 0), yy - (0 if corner[0] == "N" else p)))
            reach = edge_at(x0 + xx, y0 + yy)
            soft = min(3 * SS, max(1.0, 0.5 * float(reach.mean())))   # a thin fringe gets a crisper edge
            alpha = np.clip((reach - d) / soft + 0.5, 0, 1)[..., None]
            src = f["surface"]
            grass = (np.asarray(layers[src].crop((x0, y0, x0 + p, y0 + p)), np.float32) if src in layers
                     else np.full((p, p, 3), a.palette[src], np.float32))
            tile = out[y0:y0 + p, x0:x0 + p]
            out[y0:y0 + p, x0:x0 + p] = tile * (1 - alpha) + grass * alpha
            # tufts: a few blades each, rooted just below the ragged edge, leaning up the slope
            for _ in range(int(f["tufts"] * len(sloped))):
                px, py = rnd.uniform(0, p), rnd.uniform(0, p)
                ds = {s: float(dists[s][int(py), int(px)]) for s in sloped}
                side = min(ds, key=ds.get)
                edge = edge_at(x0 + px, y0 + py)
                if not (edge - 3 * SS < ds[side] < edge + 4 * SS):
                    continue
                ux, uy = {"N": (0, 1), "S": (0, -1), "W": (1, 0), "E": (-1, 0)}[side]   # up the slope
                for _ in range(rnd.randint(2, 4)):
                    ln = rnd.uniform(6, 13) * SS
                    ang = math.atan2(uy, ux) + rnd.uniform(-0.6, 0.6)
                    bx, by = x0 + px + rnd.uniform(-2, 2) * SS, y0 + py + rnd.uniform(-2, 2) * SS
                    col = rnd.choice([(58, 104, 38, 230), (92, 146, 56, 230), (136, 186, 82, 220)])
                    td.line([(bx, by), (bx + ln * math.cos(ang), by + ln * math.sin(ang))], fill=col, width=SS)
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")
    return Image.alpha_composite(img.convert("RGBA"), tufts).convert("RGB")


def draw_steps(o, a, r, c, x0, y0, p):
    """Step lines parallel to the edge(s) facing lower ground. One low side: straight lines. Two adjacent low
    sides (a corner staircase): nested L's whose corners point at the low corner. Opposite sides: no lines."""
    level = a.tile(r, c).get("level", 0)
    low = {s for s, (dr, dc, _) in DIRS.items() if (a.tile(r + dr, c + dc) or {}).get("level", 99) < level}
    horiz = [s for s in ("N", "S") if s in low]   # low side above/below -> horizontal step lines
    vert = [s for s in ("E", "W") if s in low]    # low side left/right -> vertical step lines
    if len(horiz) > 1 or len(vert) > 1:
        return
    dark, light = (60, 40, 25, 18), (255, 245, 225, 10)  # faint, so the surface texture shows through
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


# A marker's turn (degrees counter-clockwise) so its bottom points along a grid direction (dr, dc): drawn
# upright, its bottom points down the image (+r).
MARKER_TURN = {(1, 0): 0, (0, 1): 90, (-1, 0): 180, (0, -1): 270}


def side_turn(a, x_px, p):
    """The turn that points a drawing's bottom at the board's nearer left/right edge (x_px: its centre, in pixels)."""
    return MARKER_TURN[(0, -1) if x_px < a.C * p / 2 else (0, 1)]


def marker_turn(a, r, c, t):
    """How a painted marker is turned (the user's rule: drawings face the board's sides, never either player):
    spawn circles face their own player (spawn1 upright for player 1, spawn2 upside down for player 2); an
    explicit "orient" wins ("away-from-pit": bottom away from the lower neighbours); anything else has its bottom
    toward the nearer left/right edge."""
    marker = painted_marker(t) or ""
    if marker == "spawn1":
        return 0
    if marker.startswith("spawn2"):
        return 180
    if both_ways(a, t):   # N/N reads the same from either player's end: not turned
        return 0
    if t.get("orient") == "away-from-pit" and a.away_from_pit(r, c):
        return MARKER_TURN[a.away_from_pit(r, c)]
    return MARKER_TURN[(0, -1) if c < a.C / 2 else (0, 1)]


def painted_marker(t):
    """What gets painted on a tile: its "decal" (painted even when the marker is a 3D piece, e.g. a capture zone
    tile's number), else its marker unless "paint": false."""
    return t.get("decal") or (t.get("marker") if t.get("paint", True) else None)


NUMBERED = ("passage-in", "passage-out", "trapdoor", "button", "zone-number")   # markers that carry a number


def both_ways(a, t):
    """With the map's "numbers": "both", a numbered marker shows its number as N/N (see draw_pair)."""
    return a.data.get("numbers") == "both" and (painted_marker(t) or "").startswith(NUMBERED)


def draw_outline(over, a, r, c, x0, y0, p):
    """Legend "outline": "#rrggbb": a glowing line round each group of tiles with that outline (drawn on the
    tile's edges that face a tile without it), glowing inward."""
    col = hex_rgb(a.tile(r, c)["outline"])
    u = p / 128
    layer = Image.new("RGBA", (p, p), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w = round(5 * u)
    edges = {"N": [(0, w / 2), (p, w / 2)], "S": [(0, p - w / 2), (p, p - w / 2)],
             "W": [(w / 2, 0), (w / 2, p)], "E": [(p - w / 2, 0), (p - w / 2, p)]}
    for side, (dr, dc, _) in DIRS.items():
        if (a.tile(r + dr, c + dc) or {}).get("outline") != a.tile(r, c)["outline"]:
            d.line(edges[side], fill=col + (255,), width=w)
    glow = layer.filter(ImageFilter.GaussianBlur(7 * u))
    over.alpha_composite(glow, (x0, y0))
    over.alpha_composite(glow, (x0, y0))
    over.alpha_composite(layer, (x0, y0))


def draw_pair(im, text, cx, cy, size, fill, **style):
    """A painted number as a diagonal fraction centred on (cx, cy): upright at the top left (135 degrees), upside
    down at the bottom right (-45 degrees), a diagonal stroke between them. Each player reads the number on their
    top left, and it looks the same from either end of the board. Each number is centred on its ink, so the two
    line up."""
    f = font(size)
    sw = style.get("stroke_width", 0)
    left, top, right, bottom = f.getbbox(text, anchor="ls", stroke_width=sw)
    k = size * 0.42   # each number's centre, this far left/up (or right/down) of the centre
    pad = round(size)
    layer = Image.new("RGBA", (2 * pad, 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((pad - (left + right) / 2, pad - (top + bottom) / 2), text, font=f, fill=fill,
                               anchor="ls", **style)
    im.alpha_composite(layer, (round(cx - k - pad), round(cy - k - pad)))
    im.alpha_composite(layer.rotate(180), (round(cx + k - pad), round(cy + k - pad)))
    stroke = Image.new("RGBA", (2 * pad, 2 * pad), (0, 0, 0, 0))
    o = ImageDraw.Draw(stroke)
    reach = size * 0.55   # the stroke, bottom left to top right
    ends = [(pad - reach, pad + reach), (pad + reach, pad - reach)]
    if sw:
        o.line(ends, fill=style.get("stroke_fill"), width=round(size * 0.09) + 2 * sw)
    o.line(ends, fill=fill, width=round(size * 0.09))
    im.alpha_composite(stroke, (round(cx - pad), round(cy - pad)))


def draw_marker(im, marker, x0, y0, p, both=False):
    """Paints a marker on the image im, upright in the tile at (x0, y0). both: its number as N/N (draw_pair)."""
    if not marker:
        return
    o = ImageDraw.Draw(im)
    cx, cy, u = x0 + p / 2, y0 + p / 2, p / 128  # u = one design pixel
    ink = (45, 32, 22, 255)
    if marker.startswith("spawn"):   # spawn1, spawn2, spawn2-star (a controlled spawn: a star above the number)
        col = (47, 111, 214, 255) if marker == "spawn1" else (214, 69, 47, 255)
        r = 40 * u
        o.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 70), outline=col, width=round(7 * u))
        star = marker.endswith("-star")
        o.text((cx, cy + (8 if star else 2) * u), marker[5], font=font(round((38 if star else 46) * u)), fill=col,
               anchor="mm")
        if star:
            pts = [(cx + (10 if k % 2 == 0 else 4) * u * math.cos(-math.pi / 2 + k * math.pi / 5),
                    cy - 20 * u + (10 if k % 2 == 0 else 4) * u * math.sin(-math.pi / 2 + k * math.pi / 5)) for k in range(10)]
            o.polygon(pts, fill=col)
    elif marker == "flag":
        o.ellipse([cx - 22 * u, cy + 30 * u, cx + 22 * u, cy + 42 * u], fill=(0, 0, 0, 70))
        o.rectangle([cx - 4 * u, cy - 40 * u, cx + 3 * u, cy + 36 * u], fill=ink)
        o.polygon([(cx + 3 * u, cy - 40 * u), (cx + 44 * u, cy - 26 * u), (cx + 3 * u, cy - 10 * u)],
                  fill=(246, 246, 240, 255), outline=ink)
    elif marker == "well":   # a small round pond with a stone rim
        r_out, r_in = 50 * u, 41 * u
        o.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=(118, 114, 104, 255), outline=(62, 58, 52, 255),
                  width=round(2 * u))
        for k in range(12):   # rim stones
            ang = k * math.pi / 6
            o.line([(cx + r_in * math.cos(ang), cy + r_in * math.sin(ang)),
                    (cx + r_out * math.cos(ang), cy + r_out * math.sin(ang))], fill=(70, 66, 58, 255), width=round(2 * u))
        o.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=(40, 96, 150, 255), outline=(30, 52, 70, 255),
                  width=round(3 * u))
        o.ellipse([cx - r_in * 0.8, cy - r_in * 0.8, cx + r_in * 0.6, cy + r_in * 0.6], fill=(62, 132, 186, 255))
        for k, (dx, dy, rr) in enumerate(((-12, -10, 9), (8, 6, 13), (-4, 14, 6))):   # ripples
            o.arc([cx + (dx - rr) * u, cy + (dy - rr) * u, cx + (dx + rr) * u, cy + (dy + rr) * u], 200, 340,
                  fill=(190, 225, 245, 200), width=round(2 * u))
    elif marker.startswith("passage-in"):   # a secret passage's entrance: a dark hole, glowing violet rim, its number
        n = marker[len("passage-in"):]
        r = 42 * u
        o.ellipse([cx - r - 4 * u, cy - r - 4 * u, cx + r + 4 * u, cy + r + 4 * u], outline=(150, 90, 210, 90), width=round(6 * u))
        o.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(14, 10, 20, 255), outline=(176, 116, 236, 255), width=round(5 * u))
        if both:
            draw_pair(im, n, cx, cy, round(34 * u), (206, 160, 250, 255))
        else:
            o.text((cx, cy + 2 * u), n, font=font(round(40 * u)), fill=(206, 160, 250, 255), anchor="mm")
    elif marker.startswith("passage-out"):   # where a passage comes out (one way): a violet ring, its number, chevrons out
        n = marker[len("passage-out"):]
        r = 36 * u
        o.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(60, 30, 90, 90), outline=(176, 116, 236, 255), width=round(4 * u))
        if both:
            draw_pair(im, n, cx, cy, round(30 * u), (214, 176, 250, 255))
        else:
            o.text((cx, cy + 2 * u), n, font=font(round(34 * u)), fill=(214, 176, 250, 255), anchor="mm")
        for k in range(4):   # chevrons pointing outward: you come out here, you can't go back in
            a = k * math.pi / 2 + math.pi / 4
            px, py = cx + math.cos(a) * 50 * u, cy + math.sin(a) * 50 * u
            for side in (-1, 1):
                b2 = a + math.pi + side * 0.6
                o.line([(px, py), (px + math.cos(b2) * 9 * u, py + math.sin(b2) * 9 * u)], fill=(196, 146, 246, 255),
                       width=round(3 * u))
    elif marker.startswith("trapdoor"):   # a wooden hatch with its pair's number
        h = 40 * u
        wood, dark_wood = (128, 92, 56, 255), (70, 48, 28, 255)
        o.rectangle([cx - h, cy - h, cx + h, cy + h], fill=wood, outline=dark_wood, width=round(4 * u))
        for k in (-20, 0, 20):   # plank gaps
            o.line([(cx - h, cy + k * u), (cx + h, cy + k * u)], fill=dark_wood, width=round(2 * u))
        for sx in (-1, 1):       # hinges
            o.rectangle([cx + sx * 22 * u - 6 * u, cy - h - 3 * u, cx + sx * 22 * u + 6 * u, cy - h + 12 * u],
                        fill=(58, 58, 62, 255))
        if both:
            draw_pair(im, marker[len("trapdoor"):], cx, cy, round(34 * u), (246, 232, 200, 255),
                      stroke_width=round(3 * u), stroke_fill=dark_wood)
        else:
            o.text((cx, cy + 2 * u), marker[len("trapdoor"):], font=font(round(40 * u)), fill=(246, 232, 200, 255),
                   anchor="mm", stroke_width=round(3 * u), stroke_fill=dark_wood)
    elif marker.startswith("button"):   # a round pressure plate in a dark recess, a glowing yellow ring, its number
        n = marker[len("button"):]
        yellow = (245, 212, 38, 255)
        o.ellipse([cx - 48 * u, cy - 48 * u, cx + 48 * u, cy + 48 * u], fill=(16, 14, 22, 255))
        o.ellipse([cx - 42 * u, cy - 42 * u, cx + 42 * u, cy + 42 * u], fill=(58, 56, 68, 255), outline=yellow,
                  width=round(5 * u))
        o.ellipse([cx - 33 * u, cy - 33 * u, cx + 33 * u, cy + 33 * u], fill=(78, 74, 92, 255),
                  outline=(40, 38, 50, 255), width=round(2 * u))
        o.arc([cx - 29 * u, cy - 29 * u, cx + 29 * u, cy + 29 * u], 200, 290, fill=(150, 146, 168, 255),
              width=round(3 * u))
        if both:
            draw_pair(im, n, cx, cy, round(30 * u), yellow, stroke_width=round(2 * u), stroke_fill=(30, 26, 10, 255))
        else:
            o.text((cx, cy + 2 * u), n, font=font(round(38 * u)), fill=yellow, anchor="mm", stroke_width=round(2 * u),
                   stroke_fill=(30, 26, 10, 255))
    elif marker.startswith("zone-number"):   # a capture zone's number, painted faintly on each of its tiles
        n = marker[len("zone-number"):]
        fill = (236, 226, 255, 120)
        if both:
            draw_pair(im, n, cx, cy, round(40 * u), fill)
        else:
            o.text((cx, cy + 2 * u), n, font=font(round(52 * u)), fill=fill, anchor="mm")
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

    def tri(self, corners, uvs, down=True):
        """A flat triangle (TTS world space), facing down (or up), its normal from its corners."""
        p = [(-x, y, z) for x, y, z in corners]          # as written: x mirrored
        e1 = [p[1][i] - p[0][i] for i in range(3)]
        e2 = [p[2][i] - p[0][i] for i in range(3)]
        n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
        order = [0, 1, 2]
        if (n[1] > 0) == down:                           # wound the wrong way: flip it
            order, n = [0, 2, 1], [-v for v in n]
        ln = math.sqrt(sum(v * v for v in n)) or 1.0
        base_v, base_t = len(self.v), len(self.vt)
        self.v += [p[i] for i in order]
        self.vt += [uvs[i] for i in order]
        self.vn.append(tuple(v / ln for v in n))
        ni = len(self.vn)
        self.f.append(tuple((base_v + k + 1, base_t + k + 1, ni) for k in range(3)))

    def write(self, path):
        lines = ["# PCTTS board, made by tools/build_board.py"]
        lines += [f"v {x:.4f} {y:.4f} {z:.4f}" for x, y, z in self.v]
        lines += [f"vt {u:.5f} {v:.5f}" for u, v in self.vt]
        lines += [f"vn {x:.4f} {y:.4f} {z:.4f}" for x, y, z in self.vn]
        lines += ["f " + " ".join(f"{vi}/{ti}/{ni}" for vi, ti, ni in face) for face in self.f]
        Path(path).write_text("\n".join(lines) + "\n", encoding="ascii")


def build_mesh(a):
    W, H = a.C * PX, a.R * PX + STRIP
    y_span = a.y_span()
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
            sloped = slopes(a, r, c)
            inner = inner_corners(a, r, c)

            def tuv(px, pz):   # the tile's texture seen from above, so the slopes show its edge band
                return u0 + (px - x0) / (x1 - x0) * (u1 - u0), v0 + (z0 - pz) / (z0 - z1) * (v1 - v0)
            if not sloped and not inner:
                m.quad([(x0, top, z0), (x1, top, z0), (x1, top, z1), (x0, top, z1)],
                       [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], (0, 1, 0))
            elif inner:   # a finer surface: straight slopes along low sides, a rounded dip into each inner corner
                slope_surface(m, t, top, (x0, x1, z0, z1), sloped, inner, tuv)
            else:   # the top shrinks in on those sides; each slope runs from its edge down to the tile's edge
                w = {s: (t["slant"] if s in sloped else 0.0) for s in DIRS}
                tx0, tx1, tz0, tz1 = x0 + w["W"], x1 - w["E"], z0 - w["N"], z1 + w["S"]
                corners = [(tx0, tz0), (tx1, tz0), (tx1, tz1), (tx0, tz1)]
                m.quad([(px, top, pz) for px, pz in corners], [tuv(px, pz) for px, pz in corners], (0, 1, 0))
                for side, low in sloped.items():
                    dh, run = top - low, t["slant"]
                    up, bottom, normal = {
                        "N": ([(tx0, tz0), (tx1, tz0)], [(x1, z0), (x0, z0)], (0, run, dh)),
                        "S": ([(tx1, tz1), (tx0, tz1)], [(x0, z1), (x1, z1)], (0, run, -dh)),
                        "E": ([(tx1, tz0), (tx1, tz1)], [(x1, z1), (x1, z0)], (dh, run, 0)),
                        "W": ([(tx0, tz1), (tx0, tz0)], [(x0, z0), (x0, z1)], (-dh, run, 0)),
                    }[side]
                    ln = math.sqrt(sum(v * v for v in normal))
                    pts = [(px, top, pz) for px, pz in up] + [(px, low, pz) for px, pz in bottom]
                    m.quad(pts, [tuv(px, pz) for px, _, pz in pts], tuple(v / ln for v in normal))
            if not a.float:   # floating islands get their rocky underside instead (below)
                bu = (0.5, 1 - (H - 2) / H)
                m.quad([(x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1)], [bu] * 4, (0, -1, 0))
            for side, (dr, dc, normal) in DIRS.items():
                nb = a.tile(r + dr, c + dc)
                low = a.top(nb) if nb else (a.rim() if a.float else 0.0)
                wall_top = sloped.get(side, top)   # under a slope: the step from its bottom down to a sunken neighbour
                if low >= wall_top:
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
                half = a.C // 2   # strip slices: left half rock (outer walls), right half inner walls
                us = (((r * 5 + c * 3 + len(side)) % half) + (half if nb else 0)) * PX
                m.quad([(ax, wall_top, az), (bx, wall_top, bz), (bx, low, bz), (ax, low, az)],
                       [wall_uv(us, wall_top), wall_uv(us + PX - 1, wall_top), wall_uv(us + PX - 1, low), wall_uv(us, low)],
                       normal)
    if a.float:
        underside(a, m, wall_uv)
    return m


def slopes(a, r, c):
    """A tile with "slant": w slopes down to lower land on its sides instead of a wall: {side: the bottom of the
    slope}, which is the neighbour's level (a sunken neighbour, like lava, gets a short wall below that). The slope
    sits inside the tile (the top shrinks by w on that side), so its neighbours stay flat. Inner corners (a lower
    diagonal neighbour, both sides beside it at this tile's level) dip down too: see inner_corners(). Supported:
    raised areas whose tiles all share the same slant, one level step, not next to the sky (else the build stops)."""
    t = a.tile(r, c)
    w = t.get("slant", 0)
    if not w:
        return {}
    level, out = t.get("level", 0), {}
    for side, (dr, dc, _) in DIRS.items():
        nb = a.tile(r + dr, c + dc)
        where = f"slanted tile row {r} col {c}"
        if nb is None:
            sys.exit(f"{where}: slopes next to the sky aren't supported")
        if nb.get("level", 0) < level:
            out[side] = a.level_top(nb)
        elif nb.get("level", 0) == level and nb.get("slant", 0) != w:
            sys.exit(f"{where}: neighbours at the same level need the same slant")
    if len(set(out.values()) | set(inner_corners(a, r, c).values())) > 1:
        sys.exit(f"slanted tile row {r} col {c}: all its lower neighbours must be one level")
    return out


def inner_corners(a, r, c):
    """A slanted tile's inner (concave) corners: {"NE"/"NW"/"SE"/"SW": the bottom of the dip}, where the diagonal
    neighbour is lower but both sides beside it are not."""
    t = a.tile(r, c)
    if not (t and t.get("slant")):
        return {}
    level, out = t.get("level", 0), {}
    for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        diag = a.tile(r + dr, c + dc)
        beside = (a.tile(r + dr, c), a.tile(r, c + dc))
        if diag and diag.get("level", 0) < level and all(b and b.get("level", 0) >= level for b in beside):
            out[("N" if dr < 0 else "S") + ("W" if dc < 0 else "E")] = a.level_top(diag)
    return out


def slope_surface(m, t, top, box, sloped, inner, tuv, steps=4):
    """A slanted tile as a grid of triangles: the height at a point is the lowest that any of its low features
    allows: straight slopes inward from each low side, a round dip (a quarter cone) around each inner corner, each
    reaching the top `slant` in. The grid has lines `steps` apart across each slope band, so a hip crease or the
    top of a slope falls on grid lines; each cell is split along whichever diagonal follows the surface better."""
    x0, x1, z0, z1 = box
    w = t["slant"]
    corner_pts = {"NW": (x0, z0), "NE": (x1, z0), "SW": (x0, z1), "SE": (x1, z1)}

    def height(px, pz):
        h = top
        for side, base in sloped.items():
            d = {"N": z0 - pz, "S": pz - z1, "W": px - x0, "E": x1 - px}[side]
            h = min(h, top - (top - base) * max(0.0, 1 - d / w))
        for corner, base in inner.items():
            cx, cz = corner_pts[corner]
            h = min(h, top - (top - base) * max(0.0, 1 - math.hypot(px - cx, pz - cz) / w))
        return h

    xs = sorted({x0 + w * i / steps for i in range(steps + 1)} | {x1 - w * i / steps for i in range(steps + 1)})
    zs = sorted({z0 - w * i / steps for i in range(steps + 1)} | {z1 + w * i / steps for i in range(steps + 1)},
                reverse=True)
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            pts = [(xs[i], zs[j]), (xs[i + 1], zs[j]), (xs[i + 1], zs[j + 1]), (xs[i], zs[j + 1])]
            v = [(px, height(px, pz), pz) for px, pz in pts]
            mid = height((xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2)
            a_err = abs((v[0][1] + v[2][1]) / 2 - mid)   # split along 0-2, or along 1-3
            b_err = abs((v[1][1] + v[3][1]) / 2 - mid)
            tris = ((0, 1, 2), (0, 2, 3)) if a_err <= b_err else ((0, 1, 3), (1, 2, 3))
            for tri in tris:
                m.tri([v[k] for k in tri], [tuv(v[k][0], v[k][2]) for k in tri], down=False)


def underside(a, m, wall_uv, S=4):
    """Floating islands: the rock under every land tile, as a surface on a grid S x finer than the tiles. A point
    on an island's edge sits at the rim (where the cliff ends, so it meets the walls); farther in it hangs lower,
    with some rough jitter. Textured with the wall strip's rock (its layers follow the height)."""
    f = a.float
    rim = a.rim()
    land = np.array([[a.tile(r, c) is not None for c in range(a.C)] for r in range(a.R)])
    segs = []                                          # tile edges between land and anything else, in tile units
    for r in range(a.R):
        for c in range(a.C):
            if not land[r, c]:
                continue
            for dr, dc, seg in ((-1, 0, (c, r, c + 1, r)), (1, 0, (c, r + 1, c + 1, r + 1)),
                                (0, -1, (c, r, c, r + 1)), (0, 1, (c + 1, r, c + 1, r + 1))):
                rr, cc = r + dr, c + dc
                if not (0 <= rr < a.R and 0 <= cc < a.C and land[rr, cc]):
                    segs.append(seg)
    X, Y = np.meshgrid(np.arange(a.C * S + 1) / S, np.arange(a.R * S + 1) / S)   # X = column, Y = row (tiles)
    dist = np.full(X.shape, np.inf)
    for x0, y0, x1, y1 in segs:
        px, py = np.clip(X, min(x0, x1), max(x0, x1)), np.clip(Y, min(y0, y1), max(y0, y1))
        dist = np.minimum(dist, np.hypot(X - px, Y - py))
    rng = np.random.default_rng(sum(map(ord, a.data.get("name", ""))))
    inner = np.minimum(1.0, dist * 2)                  # 0 on the edge (no jitter there, so it meets the walls)
    depth = np.minimum(f.get("max", 2.6), f.get("depth", 1.25) * dist ** f.get("power", 1.15))
    Yw = rim - depth - np.abs(rng.normal(0, 0.14, X.shape)) * inner
    Xj = X + rng.uniform(-0.3, 0.3, X.shape) / S * (dist > 1e-6)
    Zj = Y + rng.uniform(-0.3, 0.3, X.shape) / S * (dist > 1e-6)

    def vert(j, i):
        x, z, y = (Xj[j, i] - a.C / 2) * TILE, (a.R / 2 - Zj[j, i]) * TILE, float(Yw[j, i])
        return (x, y, z), wall_uv(X[j, i] * PX, y)

    for j in range(a.R * S):
        for i in range(a.C * S):
            if not land[j // S, i // S]:
                continue
            q = [vert(j, i), vert(j, i + 1), vert(j + 1, i + 1), vert(j + 1, i)]
            for tri in ((q[0], q[1], q[2]), (q[0], q[2], q[3])):
                m.tri([p for p, _ in tri], [uv for _, uv in tri])


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
            "floor0": a.floor0(), "levels": levels}
    (out / f"board-{tag}.json").write_text(json.dumps(info), encoding="utf-8")
    print(f"{a.data['name']}: {a.R}x{a.C} tiles, {len(mesh.f)} triangles -> {out / f'board-{tag}'}.obj/.jpg/.json")


if __name__ == "__main__":
    main(sys.argv[1:])
