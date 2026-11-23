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
                    draw_marker(layer, painted, 0, 0, p, both, a.palette.get("button"))
                    over.alpha_composite(layer.rotate(turn), (x0, y0t))
                else:
                    draw_marker(over, painted, x0, y0t, p, both, a.palette.get("button"))
    for r in range(a.R):   # slopes (see slopes()): the tile's edge band, darkening toward the bottom of the slope
        for c in range(a.C):
            sloped = slopes(a, r, c) if a.tile(r, c) else {}
            if not sloped:
                continue
            band = a.tile(r, c)["slant"] / TILE * p
            x0, y0t = c * p, r * p
            for i in range(round(band)):
                alpha = round(70 * (i / band) ** 1.5)   # i = distance down the slope from its top edge
                if "N" in sloped:
                    o.line([(x0, y0t + band - i), (x0 + p, y0t + band - i)], fill=(30, 18, 8, alpha))
                if "S" in sloped:
                    o.line([(x0, y0t + p - band + i), (x0 + p, y0t + p - band + i)], fill=(30, 18, 8, alpha))
                if "W" in sloped:
                    o.line([(x0 + band - i, y0t), (x0 + band - i, y0t + p)], fill=(30, 18, 8, alpha))
                if "E" in sloped:
                    o.line([(x0 + p - band + i, y0t), (x0 + p - band + i, y0t + p)], fill=(30, 18, 8, alpha))
    for r in range(a.R):   # slopes down onto stairs (see contact_edges()): darkening toward the bottom
        for c in range(a.C):
            segs = contact_edges(a, r, c) if a.tile(r, c) else []
            if not segs:
                continue
            w = a.tile(r, c)["slant"]
            yy, xx = np.mgrid[0:p, 0:p].astype(np.float32) + 0.5
            px = (c + xx / p - a.C / 2) * TILE            # each pixel's world position
            pz = (a.R / 2 - (r + yy / p)) * TILE
            dist = np.full((p, p), np.inf, np.float32)
            for seg in segs:
                (ax, az), (bx, bz), _, _, round_a, round_b, taper = seg
                dx, dz = bx - ax, bz - az
                ll = dx * dx + dz * dz
                kr = np.zeros_like(px) if ll == 0 else ((px - ax) * dx + (pz - az) * dz) / ll
                k = np.clip(kr, 0, 1)
                d = np.hypot(px - (ax + k * dx), pz - (az + k * dz))
                if taper:   # the twisted face (see taper_height): darker the lower it is
                    top_h = a.top(a.tile(r, c))
                    hw = seg[2] if taper == 2 else seg[3]
                    down = np.clip((top_h - taper_height(seg, top_h, w, px, pz)) / max(1e-9, top_h - hw), 0, 1)
                    d = np.where(down > 0, w * (1 - down), np.inf)
                else:
                    d = np.where(((kr < 0) & (not round_a)) | ((kr > 1) & (not round_b)), np.inf, d)
                dist = np.minimum(dist, d)
            alpha = np.where(dist < w, np.round(70 * np.clip(1 - dist / w, 0, 1) ** 1.5), 0).astype(np.uint8)
            dim = np.zeros((p, p, 4), np.uint8)
            dim[..., :3] = (30, 18, 8)
            dim[..., 3] = alpha
            over.alpha_composite(Image.fromarray(dim, "RGBA"), (c * p, r * p))
    for r in range(a.R):   # rising bands (see rises()): darkening toward their foot, inside the tile
        for c in range(a.C):
            risen = rises(a, r, c) if a.tile(r, c) else {}
            if not risen:
                continue
            band = a.tile(r, c)["slant"] / TILE * p
            x0, y0t = c * p, r * p
            for i in range(round(band)):
                alpha = round(70 * (i / band) ** 1.5)   # i = distance from the tile's edge (the top of the slope)
                if "N" in risen:
                    o.line([(x0, y0t + i), (x0 + p, y0t + i)], fill=(30, 18, 8, alpha))
                if "S" in risen:
                    o.line([(x0, y0t + p - i), (x0 + p, y0t + p - i)], fill=(30, 18, 8, alpha))
                if "W" in risen:
                    o.line([(x0 + i, y0t), (x0 + i, y0t + p)], fill=(30, 18, 8, alpha))
                if "E" in risen:
                    o.line([(x0 + p - i, y0t), (x0 + p - i, y0t + p)], fill=(30, 18, 8, alpha))
    for r in range(a.R):   # rising corners: darkening toward the foot of the cone
        for c in range(a.C):
            rc = rise_corners(a, r, c) if a.tile(r, c) else {}
            if not rc:
                continue
            band = a.tile(r, c)["slant"] / TILE * p
            for corner in rc:
                cx = c * p + (p if corner[1] == "E" else 0)
                cy = r * p + (0 if corner[0] == "N" else p)
                bx0, by0 = int(cx - (band if corner[1] == "E" else 0)), int(cy - (0 if corner[0] == "N" else band))
                size = int(math.ceil(band))
                yy, xx = np.mgrid[by0:by0 + size, bx0:bx0 + size].astype(np.float32) + 0.5
                dist = np.hypot(xx - cx, yy - cy)
                alpha = np.where(dist < band, np.round(70 * np.clip(dist / band, 0, 1) ** 1.5), 0).astype(np.uint8)
                dim = np.zeros((size, size, 4), np.uint8)
                dim[..., :3] = (30, 18, 8)
                dim[..., 3] = alpha
                over.alpha_composite(Image.fromarray(dim, "RGBA"), (bx0, by0))
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
                region = np.array(over.crop((bx0, by0, bx0 + size, by0 + size)))
                on = alpha > 0
                region[on] = np.concatenate([np.broadcast_to(np.array([30, 18, 8], np.uint8), (int(on.sum()), 3)),
                                             alpha[on][:, None]], axis=1)
                over.paste(Image.fromarray(region, "RGBA"), (bx0, by0))
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


def draw_marker(im, marker, x0, y0, p, both=False, button=None):
    """Paints a marker on the image im, upright in the tile at (x0, y0). both: its number as N/N (draw_pair).
    button: the buttons' ring colour (the map's palette "button"; default yellow)."""
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
        yellow = tuple(button) + (255,) if button else (245, 212, 38, 255)
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
    elif marker == "splash":   # a fountain's splash area: wet ground, ripple rings and droplets (looks the same any way up)
        o.ellipse([cx - 52 * u, cy - 52 * u, cx + 52 * u, cy + 52 * u], fill=(30, 60, 90, 46))
        for rr, alpha in ((44, 120), (30, 95), (16, 70)):
            o.ellipse([cx - rr * u, cy - rr * u, cx + rr * u, cy + rr * u], outline=(200, 232, 250, alpha), width=round(3 * u))
        for k in range(10):
            ang = k * 2 * math.pi / 10 + 0.3
            dx, dy = math.cos(ang) * 50 * u, math.sin(ang) * 50 * u
            o.ellipse([cx + dx - 3 * u, cy + dy - 3 * u, cx + dx + 3 * u, cy + dy + 3 * u], fill=(210, 236, 252, 150))
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

    def tri_facing(self, corners, uvs, normal):
        """A flat triangle (TTS world space) wound so it faces along normal (like quad)."""
        pts = [(-x, y, z) for x, y, z in corners]
        n = (-normal[0], normal[1], normal[2])
        e1 = [pts[1][i] - pts[0][i] for i in range(3)]
        e2 = [pts[2][i] - pts[0][i] for i in range(3)]
        cross = (e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0])
        order = [0, 1, 2] if sum(cross[i] * n[i] for i in range(3)) > 0 else [0, 2, 1]
        base_v, base_t = len(self.v), len(self.vt)
        self.v += [pts[i] for i in order]
        self.vt += [uvs[i] for i in order]
        self.vn.append(n)
        ni = len(self.vn)
        self.f.append(tuple((base_v + k + 1, base_t + k + 1, ni) for k in range(3)))

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

    features = {}

    def lows(r, c):   # a tile's slopes and inner corners (cached)
        if (r, c) not in features:
            features[(r, c)] = (slopes(a, r, c), inner_corners(a, r, c))
        return features[(r, c)]

    def surface_at(r, c, px, pz):   # a tile's surface height at a point on its edge (or inside it)
        t = a.tile(r, c)
        sl, inn = lows(r, c)
        risen, rcorners, segs = rises(a, r, c), rise_corners(a, r, c), contact_edges(a, r, c)
        if not sl and not inn and not risen and not rcorners and not segs:
            return a.top(t)
        return surface_height(a.top(t), (x(c), x(c + 1), z(r), z(r + 1)), sl, inn, t["slant"], px, pz, risen,
                              rcorners, segs)

    def edge_breaks(r, c):   # where a tile's surface can bend along any of its edges (fractions of the edge)
        sl, inn = lows(r, c)
        segs = contact_edges(a, r, c)
        if not sl and not inn and not rises(a, r, c) and not rise_corners(a, r, c) and not segs:
            return [0.0, 1.0]
        f = a.tile(r, c)["slant"] / TILE
        if any(seg[6] for seg in segs):   # the finer grid by a taper (see slope_surface)
            fine = [f * i / 8 for i in range(1, 8)] + [f / 16, f / 32]
            return sorted({0.0, f, 1.0 - f, 1.0} | set(fine) | {1.0 - g for g in fine})
        return [0.0, f, 1.0 - f, 1.0]

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
            if rises(a, r, c) or rise_corners(a, r, c):   # slopes up to higher ground (and maybe down too): the fine surface
                slope_surface(m, t, top, (x0, x1, z0, z1), sloped, inner, tuv, risen=rises(a, r, c),
                              rcorners=rise_corners(a, r, c))
            elif contact_edges(a, r, c):   # sloping down onto nearby stairs (see contact_edges)
                slope_surface(m, t, top, (x0, x1, z0, z1), {}, {}, tuv, segments=contact_edges(a, r, c))
            elif not sloped and not inner:
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
                fs = sorted(set(edge_breaks(r, c) + (edge_breaks(r + dr, c + dc) if nb else [])))
                if len(fs) > 2:   # a slope along this edge, here or next door: the wall follows both surfaces
                    profile_wall(m, edge, fs, lambda px, pz: surface_at(r, c, px, pz),
                                 (lambda px, pz: surface_at(r + dr, c + dc, px, pz)) if nb else (lambda px, pz: low),
                                 normal, lambda f, y: wall_uv(us + f * (PX - 1), y))
                    continue
                if low >= wall_top:
                    continue
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
    if not w or t.get("slant_to"):   # "slant_to" tiles: see contact_edges()
        return {}
    level, out = t.get("level", 0), {}
    for side, (dr, dc, _) in DIRS.items():
        nb = a.tile(r + dr, c + dc)
        where = f"slanted tile row {r} col {c}"
        if nb is None:
            sys.exit(f"{where}: slopes next to the sky aren't supported")
        if nb.get("level", 0) < level:
            out[side] = a.level_top(nb)
        elif nb.get("level", 0) == level and (nb.get("slant", 0) != w or nb.get("slant_to")):
            sys.exit(f"{where}: neighbours at the same level need the same slant")
    if len(set(out.values()) | set(inner_corners(a, r, c).values())) > 1:
        sys.exit(f"slanted tile row {r} col {c}: all its lower neighbours must be one level")
    return out


def rises(a, r, c):
    """A tile with "slant" and "rise" builds a wedge UP to its higher neighbours inside its own edge band ("rise":
    [surfaces]: only toward those), from its own level to theirs: Pugilis's pit rises onto the foot of its stairs,
    so the stairs themselves stay flat. {side: the top of the wedge}, the neighbour's level. One level up only."""
    t = a.tile(r, c)
    if not (t and t.get("rise") and t.get("slant")):
        return {}
    level, out, to = t.get("level", 0), {}, t["rise"]
    for side, (dr, dc, _) in DIRS.items():
        nb = a.tile(r + dr, c + dc)
        if nb and nb.get("level", 0) > level and (to is True or nb.get("surface") in to) and not nb.get("plain"):
            if nb.get("level", 0) > level + 1:
                sys.exit(f"rising tile row {r} col {c}: higher ground more than one level up")
            out[side] = a.level_top(nb)
    return out


def rise_corners(a, r, c):
    """A rising tile's outer corners: {"NE"/...: the top}, where the diagonal neighbour is one it rises toward but
    neither side beside it is higher: the wedges round a corner meet in a quarter cone there."""
    t = a.tile(r, c)
    if not (t and t.get("rise") and t.get("slant")):
        return {}
    level, out, to = t.get("level", 0), {}, t["rise"]
    for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        diag = a.tile(r + dr, c + dc)
        beside = (a.tile(r + dr, c), a.tile(r, c + dc))
        if (diag and diag.get("level", 0) == level + 1 and (to is True or diag.get("surface") in to) and not diag.get("plain")
                and all(b and b.get("level", 0) <= level for b in beside)):
            out[("N" if dr < 0 else "S") + ("W" if dc < 0 else "E")] = a.level_top(diag)
    return out


def inner_corners(a, r, c):
    """A slanted tile's inner (concave) corners: {"NE"/"NW"/"SE"/"SW": the bottom of the dip}, where the diagonal
    neighbour is lower but both sides beside it are not."""
    t = a.tile(r, c)
    if not (t and t.get("slant")) or t.get("slant_to"):
        return {}
    level, out = t.get("level", 0), {}
    for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        diag = a.tile(r + dr, c + dc)
        beside = (a.tile(r + dr, c), a.tile(r, c + dc))
        if diag and diag.get("level", 0) < level and all(b and b.get("level", 0) >= level for b in beside):
            out[("N" if dr < 0 else "S") + ("W" if dc < 0 else "E")] = a.level_top(diag)
    return out


def contact_edges(a, r, c):
    """A tile with "slant" and "slant_to": [surfaces] (Pugilis's floor) slopes down onto nearby tiles with those
    surfaces (its stairs), by its distance to the edges of their flat tops where higher ground meets them: a
    straight slope along an edge, rounding off past the edge's ends (a dip in a corner tile, the "funnel" of the
    user's stair model, that carries the slope round onto the stair's corner). A stair that itself slopes down
    to the pit has a smaller flat top, so its edges end short of the tile's corners and the funnels move in with
    them. Only at the top of a stair's run (its sides opposite its lower ground): the ground beside a straight
    stair stays a sheer side wall, and the slope ends against it without rounding off (a channel: slope,
    landing, slope). A stair with "follow": true instead has the slope come down onto all its higher sides, its
    foot following the stair's own surface along each edge (level with the landing, then down its cut to the pit):
    one bevel along the whole side, nothing to round off. Returns [((x0, z0), (x1, z1), bottom at the start,
    bottom at the end, round_start, round_end)] in world units, or []."""
    t = a.tile(r, c)
    if not (t and t.get("slant") and t.get("slant_to")):
        return []
    to, level, wg = t["slant_to"], t.get("level", 0), t["slant"] / TILE

    def wx(col):
        return (col - a.C / 2) * TILE

    def wz(row):
        return (a.R / 2 - row) * TILE
    out = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            tr, tc = r + dr, c + dc
            nb = a.tile(tr, tc)
            if ((dr, dc) == (0, 0) or not nb or nb.get("surface") not in to or nb.get("level", 0) >= level
                    or nb.get("plain")):   # "plain": true: a stair left with sheer sides
                continue
            cut = slopes(a, tr, tc)   # its own slopes down: its flat top ends short of those sides
            c0, c1 = tc + (wg if "W" in cut else 0), tc + 1 - (wg if "E" in cut else 0)
            r0, r1 = tr + (wg if "N" in cut else 0), tr + 1 - (wg if "S" in cut else 0)
            own = nb.get("level", 0)

            def side_level(side):
                sdr, sdc, _ = DIRS[side]
                o = a.tile(tr + sdr, tc + sdc)
                return None if o is None else o.get("level", 0)
            lower = {sd for sd in DIRS if (side_level(sd) if side_level(sd) is not None else own) < own}
            follow = nb.get("follow")
            contact = {sd for sd in DIRS if (side_level(sd) or -1) > own and (follow or OPPOSITE[sd] in lower)}
            flat = a.level_top(nb)
            for side in contact:
                ends = ("W", "E") if side in "NS" else ("N", "S")   # the sides at its start and its end
                rounds = [not ((side_level(e) or -1) > own and e not in contact) for e in ends]   # not at a side wall
                if follow:   # a bevel ends where the stair ends; it only rounds into the next bevel
                    rounds = [e in contact for e in ends]
                pieces = []   # (start, end) in tiles along the side, bottom at each, taper
                sdr, sdc, _ = DIRS[side]

                def walled(e):   # higher ground just past this end of the bevel (beside the slope's own tile)
                    edr, edc, _ = DIRS[e]
                    past = a.tile(tr + sdr + edr, tc + sdc + edc)
                    return past is not None and past.get("level", 0) > own
                if follow:    # the whole edge: down each cut at its ends, the landing between
                    lo, hi = (tc, tc + 1) if side in "NS" else (tr, tr + 1)
                    a0, a1 = lo + (wg if ends[0] in cut else 0), hi - (wg if ends[1] in cut else 0)
                    if ends[0] in cut:   # against a wall there, it narrows to nothing at the wall's corner
                        pieces.append((lo, a0, cut[ends[0]], flat, 1 if not rounds[0] and walled(ends[0]) else 0))
                    pieces.append((a0, a1, flat, flat, 0))
                    if ends[1] in cut:
                        pieces.append((a1, hi, flat, cut[ends[1]], 2 if not rounds[1] and walled(ends[1]) else 0))
                else:
                    pieces.append(((c0, c1) if side in "NS" else (r0, r1)) + (flat, flat, 0))
                for k, (u0, u1, b0, b1, taper) in enumerate(pieces):
                    if side in "NS":
                        row = tr if side == "N" else tr + 1
                        if not follow:
                            row = r0 if side == "N" else r1
                        (ca, ra), (cb, rb) = (u0, row), (u1, row)
                    else:
                        col = tc if side == "W" else tc + 1
                        if not follow:
                            col = c0 if side == "W" else c1
                        (ca, ra), (cb, rb) = (col, u0), (col, u1)
                    gap_c = max(0.0, min(ca, cb) - (c + 1), c - max(ca, cb))   # from this tile, in tiles
                    gap_r = max(0.0, min(ra, rb) - (r + 1), r - max(ra, rb))
                    lo_t, hi_t = (c, c + 1) if side in "NS" else (r, r + 1)   # this tile along the edge
                    s0, s1 = (ca, cb) if side in "NS" else (ra, rb)
                    start_ok = rounds[0] if k == 0 else True
                    end_ok = rounds[1] if k == len(pieces) - 1 else True
                    if (not start_ok and hi_t <= s0 + 1e-9) or (not end_ok and lo_t >= s1 - 1e-9):
                        continue   # wholly past an end that stops at a wall: not this tile's slope
                    if math.hypot(gap_c, gap_r) < wg:   # near enough to shape it
                        start_round = rounds[0] if k == 0 else pieces[k - 1][4] == 0
                        end_round = rounds[1] if k == len(pieces) - 1 else pieces[k + 1][4] == 0
                        out.append(((wx(ca), wz(ra)), (wx(cb), wz(rb)), b0, b1, start_round, end_round, taper))
    return out


OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


def edge_distance(seg, px, pz):
    """(distance, bottom there) from (px, pz) to a contact edge (see contact_edges); past an end that doesn't
    round off (a side wall there), no distance: infinite. A tapering piece (taper 1: it narrows to nothing at its
    start, 2: at its end, where it meets higher ground) has its own shape: see taper_height."""
    (ax, az), (bx, bz), b0, b1, round_a, round_b, taper = seg
    dx, dz = bx - ax, bz - az
    ll = dx * dx + dz * dz
    k = 0.0 if ll == 0 else ((px - ax) * dx + (pz - az) * dz) / ll
    if taper:   # see taper_height
        return math.inf, b0
    if (k < 0 and not round_a) or (k > 1 and not round_b):
        return math.inf, b0
    k = max(0.0, min(1.0, k))
    return math.hypot(px - (ax + k * dx), pz - (az + k * dz)), b0 + (b1 - b0) * k


def profile_wall(m, edge, fs, mine, theirs, normal, uv, eps=1e-6):
    """The wall along a tile edge where this tile's surface stands above its neighbour's, both followed along the
    edge (fs: fractions of the edge where either can bend): e.g. beside a slope whose neighbour at the same level
    doesn't slope that way, or a slope coming down onto a lower slope. The neighbour builds its own higher parts."""
    (ax, az), (bx, bz) = edge
    pts = [(f, ax + (bx - ax) * f, az + (bz - az) * f) for f in fs]
    for (f0, x0, z0), (f1, x1, z1) in zip(pts, pts[1:]):
        h0, h1, l0, l1 = mine(x0, z0), mine(x1, z1), theirs(x0, z0), theirs(x1, z1)
        d0, d1 = h0 - l0, h1 - l1
        if d0 <= eps and d1 <= eps:
            continue
        if d0 < -eps or d1 < -eps:   # they cross: keep the part where this tile is higher
            k = d0 / (d0 - d1)
            fx, fz, fh = x0 + (x1 - x0) * k, z0 + (z1 - z0) * k, h0 + (h1 - h0) * k
            if d0 > 0:
                f1, x1, z1, h1, l1, d1 = f0 + (f1 - f0) * k, fx, fz, fh, fh, 0.0
            else:
                f0, x0, z0, h0, l0, d0 = f0 + (f1 - f0) * k, fx, fz, fh, fh, 0.0
        if d0 > eps and d1 > eps:
            m.quad([(x0, h0, z0), (x1, h1, z1), (x1, l1, z1), (x0, l0, z0)],
                   [uv(f0, h0), uv(f1, h1), uv(f1, l1), uv(f0, l0)], normal)
        elif d0 > eps:
            m.tri_facing([(x0, h0, z0), (x1, h1, z1), (x0, l0, z0)], [uv(f0, h0), uv(f1, h1), uv(f0, l0)], normal)
        else:
            m.tri_facing([(x0, h0, z0), (x1, h1, z1), (x1, l1, z1)], [uv(f0, h0), uv(f1, h1), uv(f1, l1)], normal)


def taper_height(seg, top, w, px, pz):
    """The surface of a tapering bevel end (see contact_edges; numpy arrays or numbers): one twisted face, the
    same kind as a bevel's end beside a pit (the user's sketch). Its edges: the rung across the bevel where the
    piece starts (the foot level with the landing, up to the top: green), the top curving round to the wall's
    top corner (blue: a quarter circle about the landing's corner, like the funnels' tops; a quarter ellipse if
    the piece isn't as long as the slope is wide), the wall's vertical corner edge (red), and the stair's cut
    edge from the landing down to the base (orange). Straight lines join each point of orange to the point of
    the curve the same share of the way round. Outside it: the top."""
    (ax, az), (bx, bz), b0, b1, _, _, taper = seg
    px, pz = np.asarray(px, float), np.asarray(pz, float)
    dx, dz = bx - ax, bz - az
    ll = dx * dx + dz * dz
    length = math.sqrt(ll)
    k = ((px - ax) * dx + (pz - az) * dz) / ll
    u = np.hypot(px - (ax + k * dx), pz - (az + k * dz))   # out from the stair's edge
    if taper == 2:   # v: along from the narrow end (the wall); hw/hn: the foot at the wide/narrow end
        v, hw, hn = (1 - k) * length, b0, b1
    else:
        v, hw, hn = k * length, b1, b0
    inside = (k >= 0) & (k <= 1) & ((u / w) ** 2 + ((length - v) / length) ** 2 < 1)
    # which straight line through the point: the one from orange's point s of the way down (0, L(1 - s)) to the
    # curve's point s of the way round (w cos a, L(1 - sin a)), a = s * 90 degrees; found by halving
    lo, hi = np.zeros_like(u), np.ones_like(u)
    for _ in range(40):
        sm = (lo + hi) / 2
        ang = sm * math.pi / 2
        side = w * np.cos(ang) * (v - length * (1 - sm)) - length * (sm - np.sin(ang)) * u
        lo, hi = np.where(side < 0, sm, lo), np.where(side < 0, hi, sm)
    sm = (lo + hi) / 2
    ang = sm * math.pi / 2
    du, dv = w * np.cos(ang), length * (sm - np.sin(ang))
    dd = du * du + dv * dv
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.clip(np.where(dd > 1e-18, (u * du + (v - length * (1 - sm)) * dv) / np.maximum(dd, 1e-18), 1.0), 0, 1)
    h = (1 - t) * (hw + sm * (hn - hw)) + t * top
    return np.where(inside, h, top)


def surface_height(top, box, sloped, inner, w, px, pz, risen=None, rcorners=None, segments=None):
    """A tile's surface height at (px, pz): raised by any wedges up to higher ground (risen, and rcorners round a
    corner), then the lowest that any of its low features allows (see slope_surface)."""
    x0, x1, z0, z1 = box
    corner_pts = {"NW": (x0, z0), "NE": (x1, z0), "SW": (x0, z1), "SE": (x1, z1)}
    h = top
    for side, high in (risen or {}).items():
        d = {"N": z0 - pz, "S": pz - z1, "W": px - x0, "E": x1 - px}[side]
        h = max(h, top + (high - top) * max(0.0, 1 - d / w))
    for corner, high in (rcorners or {}).items():
        cx, cz = corner_pts[corner]
        h = max(h, top + (high - top) * max(0.0, 1 - math.hypot(px - cx, pz - cz) / w))
    for side, base in sloped.items():
        d = {"N": z0 - pz, "S": pz - z1, "W": px - x0, "E": x1 - px}[side]
        h = min(h, top - (top - base) * max(0.0, 1 - d / w))
    for corner, base in inner.items():
        cx, cz = {"NW": (x0, z0), "NE": (x1, z0), "SW": (x0, z1), "SE": (x1, z1)}[corner]
        h = min(h, top - (top - base) * max(0.0, 1 - math.hypot(px - cx, pz - cz) / w))
    for seg in segments or ():
        if seg[6]:
            h = min(h, float(taper_height(seg, top, w, px, pz)))
            continue
        dist, base = edge_distance(seg, px, pz)
        h = min(h, top - (top - base) * max(0.0, 1 - dist / w))
    return h


def slope_surface(m, t, top, box, sloped, inner, tuv, steps=4, risen=None, rcorners=None, segments=None):
    """A slanted tile as a grid of triangles: the height at a point is the lowest that any of its low features
    allows: straight slopes inward from each low side, a round dip (a quarter cone) around each inner corner, each
    reaching the top `slant` in. The grid has lines `steps` apart across each slope band, so a hip crease or the
    top of a slope falls on grid lines; each cell is split along whichever diagonal follows the surface better."""
    x0, x1, z0, z1 = box
    w = t["slant"]

    def height(px, pz):
        return surface_height(top, box, sloped, inner, w, px, pz, risen, rcorners, segments)

    xs = sorted({x0 + w * i / steps for i in range(steps + 1)} | {x1 - w * i / steps for i in range(steps + 1)})
    zs = sorted({z0 - w * i / steps for i in range(steps + 1)} | {z1 + w * i / steps for i in range(steps + 1)},
                reverse=True)
    if any(seg[6] for seg in segments or ()):   # a taper's curved face fans into the wall's corner: finer there
        fine = [w * i / 8 for i in range(1, 8)] + [w / 16, w / 32]
        xs = sorted(set(xs) | {x0 + f for f in fine} | {x1 - f for f in fine})
        zs = sorted(set(zs) | {z0 - f for f in fine} | {z1 + f for f in fine}, reverse=True)
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
