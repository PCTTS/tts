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
WALL_GUTTER = 4   # texture pixels each side of an own wall image's slice: its wrapped edge, outside its UVs
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


def expand_regions(data):
    """map.json "raise": [{"rows": [r0, r1], "cols": [c0, c1], "by": n}] lifts every tile in those rows and columns
    by n levels: one legend serves several boards at different heights (Terrera's floors). Returns the map data with
    each raised tile given its own legend entry (a private-use character), so everything after this sees plain
    tiles. Every tool that reads a map.json calls it."""
    regions = data.get("raise")
    if not regions:
        return data
    grid, legend, made = [list(row) for row in data["grid"]], dict(data["legend"]), {}
    for reg in regions:
        (r0, r1), (c0, c1), by = reg["rows"], reg["cols"], reg["by"]
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                t = legend[grid[r][c]]
                if t.get("void") or not by:
                    continue
                key = (grid[r][c], by)
                if key not in made:
                    made[key] = chr(0xE000 + len(made))
                    legend[made[key]] = {**t, "level": t.get("level", 0) + by}
                grid[r][c] = made[key]
    return {**data, "grid": ["".join(row) for row in grid], "legend": legend}


class Arena:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.data = expand_regions(json.loads((self.folder / "map.json").read_text(encoding="utf-8")))
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
    choices = []   # "vary": "mirror" gives just the image and its mirror image
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
        if spec.get("vary") == "mirror":   # wall images: only mirrored, so their top stays up
            variants = [src, src.transpose(Image.FLIP_LEFT_RIGHT)]
        elif spec.get("vary"):
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
        if surface == "walls" or surface.startswith("walls:"):
            continue  # walls are textured in the wall strip (see draw_texture, own_walls)
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


def wall_fit(a, t, spec):
    """The height a "walls:<surface>" image's top sits at on a tile's walls: "levels": [lo, hi] = level hi's top;
    "top": L = level L's top; default the tile's own top. ("levels" and "top" are the same on every wall, so the
    image lines up from wall to wall; its size: see paint_own_walls.)"""
    if spec.get("levels"):
        return a.floor0() + spec["levels"][1] * LEVEL_H
    if spec.get("top") is not None:
        return a.floor0() + spec["top"] * LEVEL_H
    return a.top(t)


def own_key(a, t):
    """The own_walls() key for a tile's inner walls, or None when its surface has no "walls:<surface>" image:
    (surface, the height of the image's top, the tile's top where another surface's image takes over above it
    ("above", see paint_own_walls) or None)."""
    surface = t.get("surface", "floor")
    spec = (a.data.get("textures") or {}).get(f"walls:{surface}")
    if not spec:
        return None
    return surface, wall_fit(a, t, spec), (a.top(t) if spec.get("above") else None)


def own_outer(a, t):
    """A "walls:<surface>" image with "outer": true is on that surface's walls at the board's outer edge too, all
    the way down (Greenleaf: a hedge on the edge shows hedge, not the soil of the edge under the lawn)."""
    spec = (a.data.get("textures") or {}).get(f"walls:{t.get('surface', 'floor')}")
    return bool(spec and spec.get("outer"))


def own_walls(a):
    """Inner walls with their own image (map.json textures "walls:<surface>": the inner walls a tile of that surface
    stands on, e.g. "walls:stairs" = the sides of the steps; the board's outer edge keeps "walls"):
    {own_key(): [wall strip slices]}, two slices (copies to pick from) per key, taken from the end of the strip;
    and how many slices that leaves the other inner walls."""
    half = a.C // 2
    keys = sorted({own_key(a, t) for r in range(a.R) for c in range(a.C) for t in [a.tile(r, c)] if t} - {None},
                  key=lambda k: (k[0], k[1], -1.0 if k[2] is None else k[2]))
    own = {key: [2 * half - 1 - 2 * i, 2 * half - 2 - 2 * i] for i, key in enumerate(keys)}
    if 2 * len(keys) >= half:
        sys.exit("too many walls:<surface> heights for the wall strip")
    return own, half - 2 * len(keys)


def paint_own_walls(a, img, layers, p):
    """The slices own_walls() hands out: the image's top where wall_fit() says, one copy fitted to one level
    ("levels": [lo, hi]: fitted from lo up to hi; "scale": "tile": its own shape, a tile wide like the tiles'
    textures, cut off wherever a wall ends), repeated below; "across" copies side by side per tile (default: the
    whole number nearest the image's own shape; 1 at "scale": "tile"). Above its top (a wedge's side, see rises())
    the surface's own texture, at the wall scale. "above": "<surface>" puts that surface's wall image above the
    tiles' own top instead, placed as on that surface's walls, so a wedge's side lines up with the wall beside it
    (Pugilis: the ground floor's cliff down to the step's top, then the step's own image). Each slice keeps a
    WALL_GUTTER each side, filled with the image's own wrapped edge: the walls' UVs stay inside it, so texture
    filtering (and TTS's smaller mipmap copies) never blends in the neighbouring slice, which showed as a dark line
    down one end of a wall."""
    y0, rows = a.R * p, STRIP * SS
    span = a.y_span()
    g = WALL_GUTTER * SS
    iw = p - 2 * g   # the part of a slice the walls map a tile's width onto
    textures = a.data["textures"]

    def row(y):   # the row at height y in a slice's column (see wall_uv in build_mesh)
        return (1 - y / span) * rows

    def first_tile(surface):
        return next(a.tile(r, c) for r in range(a.R) for c in range(a.C)
                    if a.tile(r, c) and a.tile(r, c).get("surface", "floor") == surface)

    def image_column(surface, top, rnd):
        """One slice's column: `surface`'s wall image with its top at height `top` and copies below; the surface's
        own texture above it."""
        spec = textures[f"walls:{surface}"]
        src = Image.open(a.folder / (spec.get("images") or [spec["image"]])[0])
        if spec.get("scale") == "tile" and not spec.get("levels"):   # its own shape, not squeezed to a wall
            across = spec.get("across") or 1
            fit = TILE / across * src.height / src.width
        else:
            fit = (spec["levels"][1] - spec["levels"][0]) * LEVEL_H if spec.get("levels") else LEVEL_H
            across = spec.get("across") or max(1, round(TILE * src.height / (fit * src.width)))
        choices = [v for imgs in texture_choices(a, spec, surface, *src.size) for v in imgs]
        col = Image.new("RGB", (iw, rows), a.palette[surface])
        ytop = round(row(top))
        if surface in layers:   # its own texture above, its bottom row at the image's top
            tall = round(rows * TILE / span)   # one tile of the surface's texture, scaled as on the walls
            r, c = next((r, c) for r in range(a.R) for c in range(a.C)
                        if a.tile(r, c) and a.tile(r, c).get("surface", "floor") == surface)
            above = layers[surface].crop((c * p, r * p, (c + 1) * p, (r + 1) * p)).resize((iw, tall), Image.LANCZOS)
            for k in range(ytop, 0, -tall):
                piece = above.crop((0, max(0, tall - k), iw, tall))
                col.paste(piece, (0, k - piece.height))
        level = top
        while level > 1e-9:   # a copy's height at a time down to the underside
            ra, rb = round(row(level)), round(row(max(0.0, level - fit)))
            full = round(row(level - fit)) - ra   # a partial last band shows the image's top part
            for j in range(across):
                xa, xb = round(j * iw / across), round((j + 1) * iw / across)
                copy = rnd.choice(choices).resize((xb - xa, full), Image.LANCZOS)
                col.paste(copy.crop((0, 0, xb - xa, rb - ra)), (xa, ra))
            level -= fit
        return col

    own, _ = own_walls(a)
    for (surface, top, split), slices in own.items():
        rnd = random.Random(f"{a.data.get('name')}/walls:{surface}/{top:.4f}")
        other = textures[f"walls:{surface}"].get("above") if split is not None else None
        if other and f"walls:{other}" not in textures:
            other = None
        ornd = random.Random(f"{a.data.get('name')}/walls:{surface}/above:{other}/{split}")
        for i in slices:
            col = image_column(surface, top, rnd)
            if other:   # the other surface's wall image down to the tiles' own top
                cut = round(row(split))
                upper = image_column(other, wall_fit(a, first_tile(other), textures[f"walls:{other}"]), ornd)
                col.paste(upper.crop((0, 0, iw, cut)), (0, 0))
            x0 = i * p
            img.paste(col, (x0 + g, y0))
            img.paste(col.crop((iw - g, 0, iw, rows)), (x0, y0))       # the gutters: its edges wrapped round
            img.paste(col.crop((0, 0, g, rows)), (x0 + g + iw, y0))


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
    paint_own_walls(a, img, layers, p)   # the walls with their own image ("walls:<surface>")
    # fine grain everywhere
    noise = Image.effect_noise((W, H), 9).convert("RGB")
    img = ImageChops.add(img, noise, 1.0, -128)

    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    o = ImageDraw.Draw(over)
    for r in range(a.R):
        for c in range(a.C):
            t = a.tile(r, c)
            if not t or t.get("lines") is False:   # "lines": false: no slab lines (Terrera's rock ridge)
                continue
            x0, y0t = c * p, r * p
            # slab bevel: light top/left, dark bottom/right; thin grout line
            o.line([(x0, y0t + 2 * SS), (x0 + p, y0t + 2 * SS)], fill=(255, 255, 255, 60), width=2 * SS)
            o.line([(x0 + 2 * SS, y0t), (x0 + 2 * SS, y0t + p)], fill=(255, 255, 255, 60), width=2 * SS)
            o.line([(x0, y0t + p - 3 * SS), (x0 + p, y0t + p - 3 * SS)], fill=(0, 0, 0, 55), width=2 * SS)
            o.line([(x0 + p - 3 * SS, y0t), (x0 + p - 3 * SS, y0t + p)], fill=(0, 0, 0, 55), width=2 * SS)
            o.rectangle([x0, y0t, x0 + p - 1, y0t + p - 1], outline=(40, 28, 18, 110), width=SS)
            if t.get("surface") == "stairs" and a.data.get("stair_lines", True):   # "stair_lines": false: none
                draw_steps(o, a, r, c, x0, y0t, p)
            if t.get("outline"):
                draw_outline(over, a, r, c, x0, y0t, p)
            painted = painted_marker(t)
            if painted:
                turn = marker_turn(a, r, c, t)
                both = both_ways(a, t)
                if turn:   # drawn upright on its own layer, then turned so its bottom points the right way
                    layer = Image.new("RGBA", (p, p), (0, 0, 0, 0))
                    draw_marker(layer, painted, 0, 0, p, both, a.palette.get("button"), a.palette)
                    over.alpha_composite(layer.rotate(turn), (x0, y0t))
                else:
                    draw_marker(over, painted, x0, y0t, p, both, a.palette.get("button"), a.palette)
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
                (ax, az), (bx, bz), _, _, round_a, round_b, taper = seg[:7]
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
            shade_over(over, dim, c * p, r * p)
    for r in range(a.R):   # rising bands (see rises()): darkening toward their foot, inside the tile
        for c in range(a.C):
            risen = rises(a, r, c) if a.tile(r, c) else {}
            if not risen:
                continue
            band = a.tile(r, c)["slant"] / TILE * p
            x0, y0t = c * p, r * p
            plain_sand = a.tile(r, c).get("shade") is False   # "shade": false: the wedges show just the surface
            for i in range(round(band)):
                alpha = round(70 * (i / band) ** 1.5)   # i = distance from the tile's edge (the top of the slope)
                ink = (0, 0, 0, 0) if plain_sand else (30, 18, 8, alpha)
                if "N" in risen:
                    o.line([(x0, y0t + i), (x0 + p, y0t + i)], fill=ink)
                if "S" in risen:
                    o.line([(x0, y0t + p - i), (x0 + p, y0t + p - i)], fill=ink)
                if "W" in risen:
                    o.line([(x0 + i, y0t), (x0 + i, y0t + p)], fill=ink)
                if "E" in risen:
                    o.line([(x0 + p - i, y0t), (x0 + p - i, y0t + p)], fill=ink)
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
                shade_over(over, dim, bx0, by0)
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


def shade_over(over, dim, x, y):
    """Lays a slope's shading (an RGBA array) on the overlay in place of what's painted there, like the straight
    slopes' shading lines do: the grid lines don't run down a slope (the user's choice on Yaksha)."""
    h, w = dim.shape[:2]
    region = np.array(over.crop((x, y, x + w, y + h)))
    on = dim[..., 3] > 0
    region[on] = dim[on]
    over.paste(Image.fromarray(region, "RGBA"), (x, y))


FRINGE = {"reach": 0.42, "wobble": 0.3, "rough": 1.0, "tufts": 160}   # defaults (board v3's look)


def draw_coords(over, a, p):
    """Coordinates in the board's edge tiles: x = 1..C along both player edges (from player 1's left), y = 1..R up
    both side edges (from player 1's side). Each number faces out from its own edge (its bottom toward that edge).
    "coords": {"cols": [first, last], "rows": [first, last]} (tile indices) numbers only those columns/rows, from 1;
    "inset": how far in from the edge a number's centre sits, in tiles (default 0.15); "repeat": n starts the count
    again after n (Spectra: 1-8 twice along each edge, for d8 rolls); "sides": [near, right, far, left] puts a badge
    with that text on each edge (Spectra: the d4 directions), see side_badges."""
    spec = a.data["coords"]
    opts = spec if isinstance(spec, dict) else {}
    cols = range(a.C) if "cols" not in opts else range(spec["cols"][0], spec["cols"][1] + 1)
    rows = range(a.R) if "rows" not in opts else range(spec["rows"][0], spec["rows"][1] + 1)
    k = opts.get("inset", 0.15)
    rep = opts.get("repeat")
    f = font(round(p * 0.15))
    size = round(p * 0.28)

    def num(i):   # the i-th number along a run (from 0)
        return str(i % rep + 1 if rep else i + 1)

    def label(text, cx, cy, edge):
        layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((size / 2, size / 2), text, font=f, fill=(236, 226, 208, 190), anchor="mm",
                                   stroke_width=max(1, round(p * 0.012)), stroke_fill=(0, 0, 0, 150))
        layer = layer.rotate(MARKER_TURN[edge])
        over.alpha_composite(layer, (round(cx - size / 2), round(cy - size / 2)))

    for c in cols:
        label(num(c - cols.start), c * p + p / 2, (a.R - k) * p, (1, 0))         # player 1's edge
        label(num(c - cols.start), c * p + p / 2, p * k, (-1, 0))                # player 2's edge
    for r in rows:
        label(num(rows.stop - 1 - r), p * k, r * p + p / 2, (0, -1))              # left edge
        label(num(rows.stop - 1 - r), (a.C - k) * p, r * p + p / 2, (0, 1))       # right edge
    if opts.get("sides"):
        side_badges(over, a, p, opts["sides"])


SIDE_EDGES = ((1, 0), (0, 1), (-1, 0), (0, -1))   # "sides" order: player 1's edge, right, player 2's edge, left


def side_badge_spot(a, edge):
    """Where an edge's badge goes: on the boundary between two edge tiles nearest the edge's middle, both open (not
    solid) and at the same height, so the badge lies flat across them. Returns (boundary, along_x)."""
    along_x = edge[0] != 0
    n = a.C if along_x else a.R
    line = (a.R - 1 if edge[0] > 0 else 0) if along_x else (a.C - 1 if edge[1] > 0 else 0)

    def at(i):
        return a.tile(line, i) if along_x else a.tile(i, line)
    ok = [b for b in range(1, n) if at(b - 1) and at(b) and not at(b - 1).get("solid") and not at(b).get("solid")
          and abs(a.top(at(b - 1)) - a.top(at(b))) < 1e-6]
    if not ok:
        sys.exit(f"coords sides: no two open tiles at one height along the {edge} edge for its badge")
    return min(ok, key=lambda b: (abs(b - n / 2), b)), along_x


def side_badges(over, a, p, texts):
    """A round badge with each edge's text (e.g. a d4 direction), facing out from its edge like the numbers."""
    k = 0.16   # the badge's centre, this far in from the edge (tiles)
    size = round(p * 0.36)
    f = font(round(p * 0.17))
    for edge, text in zip(SIDE_EDGES, texts):
        b, along_x = side_badge_spot(a, edge)
        if along_x:
            cx, cy = b * p, ((a.R - k) if edge[0] > 0 else k) * p
        else:
            cx, cy = ((a.C - k) if edge[1] > 0 else k) * p, b * p
        layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        r = p * 0.13
        d.ellipse([size / 2 - r, size / 2 - r, size / 2 + r, size / 2 + r], fill=(20, 16, 28, 210),
                  outline=(232, 196, 96, 240), width=max(1, round(p * 0.018)))
        d.text((size / 2, size / 2 + p * 0.005), str(text), font=f, fill=(240, 206, 110, 255), anchor="mm")
        over.alpha_composite(layer.rotate(MARKER_TURN[edge]), (round(cx - size / 2), round(cy - size / 2)))


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
    if marker == "spawn1" or marker.startswith(("sand-", "ice-")) or marker == "cracked":   # quicksand and ice
        return 0                                                                    # arrows point the way they push
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


NUMBERED = ("passage-in", "passage-out", "trapdoor", "button", "zone-number", "blocker", "tunnel", "passage",
            "landing")   # markers that carry a number
SAND_DIRS = {"n": (0, -1), "s": (0, 1), "e": (1, 0), "w": (-1, 0),   # quicksand pushes (image directions, y down)
             "ne": (1, -1), "nw": (-1, -1), "se": (1, 1), "sw": (-1, 1)}


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


def sand_arrow(o, cx, cy, u, way, scale=1.0, col=(66, 44, 24, 235)):
    """An arrow centred on (cx, cy) pointing `way` (image direction, y down), for quicksand."""
    dx, dy = way
    n = math.hypot(dx, dy)
    dx, dy = dx / n, dy / n
    ln, head, w = 32 * u * scale, 20 * u * scale, max(1, round(8 * u * scale))
    tip = (cx + dx * ln, cy + dy * ln)
    neck = (tip[0] - dx * head, tip[1] - dy * head)
    o.line([(cx - dx * ln, cy - dy * ln), neck], fill=col, width=w)
    o.polygon([tip, (neck[0] - dy * head * 0.75, neck[1] + dx * head * 0.75),
               (neck[0] + dy * head * 0.75, neck[1] - dx * head * 0.75)], fill=col)


def draw_marker(im, marker, x0, y0, p, both=False, button=None, palette=None):
    """Paints a marker on the image im, upright in the tile at (x0, y0). both: its number as N/N (draw_pair).
    button: the buttons' ring colour (the map's palette "button"; default yellow). palette: the map's palette
    (colours some markers look up: "passage<n>", "flower-<name>")."""
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
    elif marker.startswith("passage"):   # a secret passage both ways (Greenleaf): a burrow ringed in its pair's colour
        n = marker[len("passage"):]       # (the map's palette "passage<n>"), its pair's number on it
        col = tuple((palette or {}).get(f"passage{n}", (176, 116, 236)))
        r = 42 * u
        o.ellipse([cx - r - 5 * u, cy - r - 5 * u, cx + r + 5 * u, cy + r + 5 * u], fill=col + (80,))
        o.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (255,), outline=(22, 16, 10, 255), width=round(3 * u))
        for k, shade_col in ((0.8, (52, 36, 22, 255)), (0.64, (26, 18, 11, 255)), (0.46, (10, 7, 5, 255))):
            o.ellipse([cx - r * k, cy - r * k, cx + r * k, cy + r * k], fill=shade_col)
        if both:
            draw_pair(im, n, cx, cy, round(28 * u), col + (255,), stroke_width=round(2 * u), stroke_fill=(10, 7, 5, 255))
        else:
            o.text((cx, cy + 2 * u), n, font=font(round(34 * u)), fill=col + (255,), anchor="mm",
                   stroke_width=round(2 * u), stroke_fill=(10, 7, 5, 255))
    elif marker.startswith("landing-"):   # where a flower can throw a Pokémon (Greenleaf): a ring of petals in the
        rest = marker[len("landing-"):]    # flower's colour (palette "flower-<name>"), the spot's number
        name, n = rest.rstrip("0123456789"), rest[len(rest.rstrip("0123456789")):]
        col = tuple((palette or {}).get(f"flower-{name}", (220, 60, 70)))
        for k in range(8):
            a = k * math.pi / 4
            px, py = cx + math.cos(a) * 34 * u, cy + math.sin(a) * 34 * u
            petal = [(px + math.cos(a) * 13 * u * math.cos(t) - math.sin(a) * 8 * u * math.sin(t),
                      py + math.sin(a) * 13 * u * math.cos(t) + math.cos(a) * 8 * u * math.sin(t))
                     for t in (i * math.pi / 8 for i in range(16))]
            o.polygon(petal, fill=col + (190,), outline=(30, 22, 16, 200))
        o.ellipse([cx - 26 * u, cy - 26 * u, cx + 26 * u, cy + 26 * u], fill=(34, 28, 20, 120))
        if both:
            draw_pair(im, n, cx, cy, round(26 * u), col + (255,), stroke_width=round(2 * u), stroke_fill=(20, 14, 10, 255))
        else:
            o.text((cx, cy + 2 * u), n, font=font(round(32 * u)), fill=col + (255,), anchor="mm",
                   stroke_width=round(2 * u), stroke_fill=(20, 14, 10, 255))
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
    elif marker.startswith("sand-"):   # quicksand (Terrera): an arrow the way it drags a Pokémon that ends its turn here
        sand_arrow(o, cx, cy, u, SAND_DIRS[marker[len("sand-"):]])
    elif marker.startswith("ice-"):   # ice (Snow): a deep blue arrow the way it slides a Pokémon (dirs as sand-)
        sand_arrow(o, cx, cy, u, SAND_DIRS[marker[len("ice-"):]], 1.1, (24, 62, 112, 235))
    elif marker.startswith("tunnel"):   # a tunnel's mouth (Terrera): a dark burrow, its number (the d4 roll) on it;
        n, _, way = marker[len("tunnel"):].partition("-")   # "tunnel3-se": also quicksand pushing south-east
        r = 34 * u
        for k, col in ((1.18, (150, 118, 84, 255)), (1.0, (58, 40, 26, 255)), (0.78, (30, 20, 13, 255)),
                       (0.55, (14, 9, 6, 255))):
            o.ellipse([cx - r * k, cy - r * k * 0.86, cx + r * k, cy + r * k * 0.86], fill=col)
        pale = (236, 220, 186, 255)
        if both:
            draw_pair(im, n, cx, cy, round(28 * u), pale, stroke_width=round(2 * u), stroke_fill=(20, 14, 8, 255))
        else:
            o.text((cx, cy + 2 * u), n, font=font(round(34 * u)), fill=pale, anchor="mm", stroke_width=round(2 * u),
                   stroke_fill=(20, 14, 8, 255))
        if way:   # a small arrow in the inner corner
            dx, dy = SAND_DIRS[way]
            sand_arrow(o, cx + dx * 44 * u, cy + dy * 44 * u, u, (dx, dy), 0.45)
    elif marker == "cracked":   # unstable ground (Terrera): hatched like the user's board, cracks through it
        layer = Image.new("RGBA", (p, p), (0, 0, 0, 0))   # its own tile-sized layer: the hatching stays in the tile
        ld = ImageDraw.Draw(layer)
        for k in range(-128, 129, 22):
            ld.line([(k * u, p), ((k + 128) * u, 0)], fill=(52, 36, 24, 150), width=round(3 * u))
        rnd = random.Random(f"{x0},{y0}")   # a different crack pattern on each tile
        for _ in range(3):
            x, y = rnd.uniform(0.15, 0.85) * p, rnd.uniform(0.15, 0.85) * p
            pts = [(x, y)]
            ang = rnd.uniform(0, 2 * math.pi)
            for _ in range(5):
                ang += rnd.uniform(-0.9, 0.9)
                x, y = x + math.cos(ang) * 12 * u, y + math.sin(ang) * 12 * u
                pts.append((x, y))
            ld.line(pts, fill=(24, 16, 10, 220), width=round(3 * u))
        im.alpha_composite(layer, (round(x0), round(y0)))
    elif marker.startswith("blocker"):   # where a blocker stands when closed (Valora): a dark slot in a hazard-striped
        n = marker[len("blocker"):]       # frame, the number of the gear that opens and closes it
        m0, band = 5 * u, 13 * u
        stripes = Image.new("RGBA", (p, p), (236, 186, 32, 255))
        sd = ImageDraw.Draw(stripes)
        for k in range(-p, 2 * p, round(18 * u)):
            sd.polygon([(k, 0), (k + 9 * u, 0), (k + 9 * u + p, p), (k + p, p)], fill=(26, 24, 22, 255))
        mask = Image.new("L", (p, p), 0)
        md = ImageDraw.Draw(mask)
        md.rectangle([m0, m0, p - m0, p - m0], fill=255)
        md.rectangle([m0 + band, m0 + band, p - m0 - band, p - m0 - band], fill=0)
        layer = Image.new("RGBA", (p, p), (0, 0, 0, 0))
        layer.paste(stripes, (0, 0), mask)
        im.alpha_composite(layer, (round(x0), round(y0)))
        o.rectangle([x0 + m0 + band, y0 + m0 + band, x0 + p - m0 - band, y0 + p - m0 - band], fill=(34, 34, 38, 255))
        gold = (245, 200, 60, 255)
        if both:
            draw_pair(im, n, cx, cy, round(30 * u), gold, stroke_width=round(2 * u), stroke_fill=(20, 18, 16, 255))
        else:
            o.text((cx, cy + 2 * u), n, font=font(round(38 * u)), fill=gold, anchor="mm", stroke_width=round(2 * u),
                   stroke_fill=(20, 18, 16, 255))
    elif marker == "lantern":   # an iron lantern with a lit flame in a warm glow (Spectra: on crypt corners)
        for rr, alpha in ((58, 26), (48, 40), (38, 56)):
            o.ellipse([cx - rr * u, cy - rr * u, cx + rr * u, cy + rr * u], fill=(255, 150, 50, alpha))
        iron, glass = (34, 32, 38, 255), (250, 190, 92, 255)
        o.ellipse([cx - 9 * u, cy - 50 * u, cx + 9 * u, cy - 34 * u], outline=iron, width=round(4 * u))   # ring
        o.polygon([(cx - 13 * u, cy - 37 * u), (cx + 13 * u, cy - 37 * u), (cx + 26 * u, cy - 22 * u),
                   (cx - 26 * u, cy - 22 * u)], fill=iron)                                                  # cap
        o.rectangle([cx - 21 * u, cy - 22 * u, cx + 21 * u, cy + 25 * u], fill=glass, outline=iron, width=round(4 * u))
        for bx in (-7, 7):                                                                                  # frame bars
            o.line([(cx + bx * u, cy - 22 * u), (cx + bx * u, cy + 25 * u)], fill=iron, width=round(2 * u))
        o.polygon([(cx, cy - 14 * u), (cx + 9 * u, cy + 4 * u), (cx + 7 * u, cy + 14 * u), (cx, cy + 19 * u),
                   (cx - 7 * u, cy + 14 * u), (cx - 9 * u, cy + 4 * u)], fill=(240, 104, 26, 255))         # flame
        o.polygon([(cx, cy - 3 * u), (cx + 5 * u, cy + 8 * u), (cx, cy + 15 * u), (cx - 5 * u, cy + 8 * u)],
                  fill=(255, 232, 130, 255))
        o.polygon([(cx - 26 * u, cy + 25 * u), (cx + 26 * u, cy + 25 * u), (cx + 18 * u, cy + 36 * u),
                   (cx - 18 * u, cy + 36 * u)], fill=iron)                                                  # base
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


WALL_ENDS = {"N": ("W", "E"), "S": ("E", "W"), "E": ("N", "S"), "W": ("S", "N")}   # the sides at a wall's two ends
                                                                                   # (its edge runs start -> end)


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
    curve = a.data.get("curve_steps", 24)   # triangles round each inner corner's dip (see slope_surface)
    own, inner_n = own_walls(a)   # walls with their own image ("walls:<surface>") and the slices left for the rest
    textures = a.data.get("textures") or {}

    def surface_key(surface):   # the own_walls() key of a surface's walls (its first tile's)
        t0 = next((a.tile(r, c) for r in range(a.R) for c in range(a.C)
                   if a.tile(r, c) and a.tile(r, c).get("surface", "floor") == surface), None)
        return own_key(a, t0) if t0 else None

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
        if sl and rises(a, r, c):   # the step where a wedge's band ends over a slope (see slope_surface)
            return [0.0, f, f * 65 / 64, 1.0 - f * 65 / 64, 1.0 - f, 1.0]
        if any(seg[6] and seg[7] != "triangles" for seg in segs):   # the finer grid by a taper (see slope_surface)
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
                slope_surface(m, t, top, (x0, x1, z0, z1), sloped, inner, tuv, curve, risen=rises(a, r, c),
                              rcorners=rise_corners(a, r, c))
            elif contact_edges(a, r, c):   # sloping down onto nearby stairs (see contact_edges)
                slope_surface(m, t, top, (x0, x1, z0, z1), {}, {}, tuv, curve, segments=contact_edges(a, r, c))
            elif not sloped and not inner:
                m.quad([(x0, top, z0), (x1, top, z0), (x1, top, z1), (x0, top, z1)],
                       [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], (0, 1, 0))
            elif inner:   # a finer surface: straight slopes along low sides, a rounded dip into each inner corner
                slope_surface(m, t, top, (x0, x1, z0, z1), sloped, inner, tuv, curve)
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
                pick = r * 5 + c * 3 + len(side)
                key = own_key(a, t) if nb or own_outer(a, t) else None
                if key in own:   # this tile's own inner wall image (see own_walls), inside its slice's gutters
                    us = own[key][pick % len(own[key])] * PX
                    ua, ub = us + WALL_GUTTER, us + PX - WALL_GUTTER
                else:
                    us = ((pick % (inner_n if nb else half)) + (half if nb else 0)) * PX
                    ua, ub = us, us + PX - 1
                fs = sorted(set(edge_breaks(r, c) + (edge_breaks(r + dr, c + dc) if nb else [])))
                uv_for = None
                if key in own and key[2] is not None:   # "above": under a wedge at either end of this wall (its band,
                    # out to the wedge's foot) the other surface's wall image all the way down, the tile's own image
                    # only below its flat top (Pugilis: the ground floor's cliff under the middle stairs' wedges)
                    okey = surface_key(textures[f"walls:{key[0]}"]["above"])
                    risen, rc = rises(a, r, c), rise_corners(a, r, c)
                    s0, s1 = WALL_ENDS[side]

                    def corner(s, side=side):   # the corner at an end of this wall: "NE", ...
                        return "".join(sorted((side, s), key=lambda q: q in "WE"))
                    band0, band1 = (s0 in risen or corner(s0) in rc), (s1 in risen or corner(s1) in rc)
                    if okey in own and (band0 or band1):
                        os_ = own[okey][pick % len(own[okey])] * PX
                        oa, ob, fw = os_ + WALL_GUTTER, os_ + PX - WALL_GUTTER, t["slant"] / TILE

                        def uv_for(f0, f1, oa=oa, ob=ob, ua=ua, ub=ub, fw=fw, band0=band0, band1=band1):
                            mid = (f0 + f1) / 2
                            lo, hi = (oa, ob) if (band0 and mid < fw) or (band1 and mid > 1 - fw) else (ua, ub)
                            return lambda f, y: wall_uv(lo + f * (hi - lo), y)
                if len(fs) > 2:   # a slope along this edge, here or next door: the wall follows both surfaces
                    profile_wall(m, edge, fs, lambda px, pz: surface_at(r, c, px, pz),
                                 (lambda px, pz: surface_at(r + dr, c + dc, px, pz)) if nb else (lambda px, pz: low),
                                 normal, lambda f, y: wall_uv(ua + f * (ub - ua), y), uv_for=uv_for)
                    continue
                if low >= wall_top:
                    continue
                m.quad([(ax, wall_top, az), (bx, wall_top, bz), (bx, low, bz), (ax, low, az)],
                       [wall_uv(ua, wall_top), wall_uv(ub, wall_top), wall_uv(ub, low), wall_uv(ua, low)],
                       normal)
    if a.float:
        underside(a, m, wall_uv)
    return m


def slopes(a, r, c):
    """A tile with "slant": w slopes down to lower land on its sides instead of a wall: {side: the bottom of the
    slope}, which is the neighbour's level (a sunken neighbour, like lava, gets a short wall below that). The slope
    sits inside the tile (the top shrinks by w on that side), so its neighbours stay flat. Inner corners (a lower
    diagonal neighbour, both sides beside it at this tile's level) dip down too: see inner_corners(). Supported:
    raised areas whose tiles all share the same slant, one level step, not next to the sky (else the build stops; the
    board's outer edge is fine: a wall straight down there)."""
    t = a.tile(r, c)
    w = t.get("slant", 0)
    if not w or t.get("slant_to") or t.get("sheer"):   # "slant_to" tiles: see contact_edges(); "sheer": its drops
        return {}                                          # to lower ground stay walls (its slant is for its wedges up)
    level, out = t.get("level", 0), {}
    for side, (dr, dc, _) in DIRS.items():
        nb = a.tile(r + dr, c + dc)
        where = f"slanted tile row {r} col {c}"
        if nb is None:
            if 0 <= r + dr < a.R and 0 <= c + dc < a.C:   # void inside the grid: sky
                sys.exit(f"{where}: slopes next to the sky aren't supported")
            continue   # the board's outer edge: its wall goes straight down (following the slopes beside it)
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
    if not (t and t.get("slant")) or t.get("slant_to") or t.get("sheer"):
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
                        out.append(((wx(ca), wz(ra)), (wx(cb), wz(rb)), b0, b1, start_round, end_round, taper,
                                    nb.get("bevel_end", "curved")))
    return out


OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


def edge_distance(seg, px, pz):
    """(distance, bottom there) from (px, pz) to a contact edge (see contact_edges); past an end that doesn't
    round off (a side wall there), no distance: infinite. A tapering piece (taper 1: it narrows to nothing at its
    start, 2: at its end, where it meets higher ground) has its own shape: see taper_height."""
    (ax, az), (bx, bz), b0, b1, round_a, round_b, taper = seg[:7]
    dx, dz = bx - ax, bz - az
    ll = dx * dx + dz * dz
    k = 0.0 if ll == 0 else ((px - ax) * dx + (pz - az) * dz) / ll
    if taper:   # see taper_height
        return math.inf, b0
    if (k < 0 and not round_a) or (k > 1 and not round_b):
        return math.inf, b0
    k = max(0.0, min(1.0, k))
    return math.hypot(px - (ax + k * dx), pz - (az + k * dz)), b0 + (b1 - b0) * k


def profile_wall(m, edge, fs, mine, theirs, normal, uv, eps=1e-6, uv_for=None):
    """The wall along a tile edge where this tile's surface stands above its neighbour's, both followed along the
    edge (fs: fractions of the edge where either can bend): e.g. beside a slope whose neighbour at the same level
    doesn't slope that way, or a slope coming down onto a lower slope. The neighbour builds its own higher parts.
    uv_for(f0, f1), if given, picks the uv function for the piece between two breaks (see build_mesh)."""
    (ax, az), (bx, bz) = edge
    pts = [(f, ax + (bx - ax) * f, az + (bz - az) * f) for f in fs]
    for (f0, x0, z0), (f1, x1, z1) in zip(pts, pts[1:]):
        suv = uv_for(f0, f1) if uv_for else uv
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
                   [suv(f0, h0), suv(f1, h1), suv(f1, l1), suv(f0, l0)], normal)
        elif d0 > eps:
            m.tri_facing([(x0, h0, z0), (x1, h1, z1), (x0, l0, z0)], [suv(f0, h0), suv(f1, h1), suv(f0, l0)], normal)
        else:
            m.tri_facing([(x0, h0, z0), (x1, h1, z1), (x1, l1, z1)], [suv(f0, h0), suv(f1, h1), suv(f1, l1)], normal)


def taper_height(seg, top, w, px, pz):
    """The surface of a tapering bevel end (see contact_edges; numpy arrays or numbers): one twisted face, the
    same kind as a bevel's end beside a pit (the user's sketch). Its edges: the rung across the bevel where the
    piece starts (the foot level with the landing, up to the top: green), the top curving round to the wall's
    top corner (blue: a quarter circle about the landing's corner, like the funnels' tops; a quarter ellipse if
    the piece isn't as long as the slope is wide), the wall's vertical corner edge (red), and the stair's cut
    edge from the landing down to the base (orange). Straight lines join each point of orange to the point of
    the curve the same share of the way round. Outside it: the top."""
    (ax, az), (bx, bz), b0, b1, _, _, taper = seg[:7]
    style = seg[7] if len(seg) > 7 else "curved"
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
    if style == "triangles":   # one flat plane from the landing-level foot to the wall's top corner (the stair's
        # cut meets it in a vertical triangle in line with the wall)
        h = top - (top - hw) * np.maximum(0.0, 1 - (u + (length - v)) / w)
        return np.where((k < 0) | (k > 1), top, h)
    if style == "twisted":     # straight top from the rung's top to the wall's top corner
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            t = np.where(v > 1e-12, u * length / (np.maximum(v, 1e-12) * w), np.where(u > 1e-12, np.inf, 0.0))
            sw = np.clip(v / length, 0, 1)
            h = sw * (hw + t * (top - hw)) + (1 - sw) * (hn + t * (top - hn))
            return np.where((k < 0) | (k > 1) | (t >= 1), top, h)
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
    """A tile's surface height at (px, pz): the lowest that any of its low features allows (see slope_surface), then
    raised by any wedges up to higher ground (risen, and rcorners round a corner), each within its own band: a wedge
    stands solid on top of the tile's slopes (Pugilis's top-right stair: the wedges up to the floor run the full
    length of its edges, over its cut down to the pit)."""
    x0, x1, z0, z1 = box
    corner_pts = {"NW": (x0, z0), "NE": (x1, z0), "SW": (x0, z1), "SE": (x1, z1)}
    h = top
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
    for side, high in (risen or {}).items():
        d = {"N": z0 - pz, "S": pz - z1, "W": px - x0, "E": x1 - px}[side]
        if d <= w + 1e-9:
            h = max(h, top + (high - top) * max(0.0, 1 - d / w))
    for corner, high in (rcorners or {}).items():
        cx, cz = corner_pts[corner]
        dc = math.hypot(px - cx, pz - cz)
        if dc <= w + 1e-9:
            h = max(h, top + (high - top) * max(0.0, 1 - dc / w))
    return h


def slope_surface(m, t, top, box, sloped, inner, tuv, curve=24, risen=None, rcorners=None, segments=None, steps=4):
    """A slanted tile as a grid of triangles: the height at a point is the lowest that any of its low features
    allows: straight slopes inward from each low side, a round dip (a quarter cone) around each inner corner, each
    reaching the top `slant` in. The grid has lines `steps` apart across each slope band, so a hip crease or the
    top of a slope falls on grid lines; each cell is split along whichever diagonal follows the surface better.
    On a tile with only straight slopes and dips, each dip's corner square (`slant` a side) is drawn instead as an
    exact cone, a fan of `curve` triangles from the corner (its height changes in a straight line from it), with
    the flat top round it fanned from the square's far corner: round, for a handful of triangles (a finer grid
    made the board too heavy for TTS to load). Its edges meet the neighbours' straight profiles."""
    x0, x1, z0, z1 = box
    w = t["slant"]

    def height(px, pz):
        return surface_height(top, box, sloped, inner, w, px, pz, risen, rcorners, segments)

    xs = sorted({x0 + w * i / steps for i in range(steps + 1)} | {x1 - w * i / steps for i in range(steps + 1)})
    zs = sorted({z0 - w * i / steps for i in range(steps + 1)} | {z1 + w * i / steps for i in range(steps + 1)},
                reverse=True)
    if risen and sloped:   # a wedge's band ends over a slope: a step there, nearly upright
        step = w + w / 64
        xs = sorted(set(xs) | {x0 + step, x1 - step})
        zs = sorted(set(zs) | {z0 - step, z1 + step}, reverse=True)
    if any(seg[6] and seg[7] != "triangles" for seg in segments or ()):   # a ruled taper face fans into the corner
        fine = [w * i / 8 for i in range(1, 8)] + [w / 16, w / 32]
        xs = sorted(set(xs) | {x0 + f for f in fine} | {x1 - f for f in fine})
        zs = sorted(set(zs) | {z0 - f for f in fine} | {z1 + f for f in fine}, reverse=True)
    fans = []   # (corner point, direction into the tile along x and z) of each dip drawn as a cone
    if not (risen or rcorners or segments):
        for corner in inner:
            fans.append(((x0 if corner[1] == "W" else x1, z0 if corner[0] == "N" else z1),
                         (1 if corner[1] == "W" else -1, -1 if corner[0] == "N" else 1)))

    def in_fan_square(px, pz):
        return any(0 <= (px - cx) * dx <= w and 0 <= (pz - cz) * dz <= w for (cx, cz), (dx, dz) in fans)

    def vert(px, pz):
        return (px, height(px, pz), pz)

    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            if in_fan_square((xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2):
                continue
            pts = [(xs[i], zs[j]), (xs[i + 1], zs[j]), (xs[i + 1], zs[j + 1]), (xs[i], zs[j + 1])]
            v = [vert(px, pz) for px, pz in pts]
            mid = height((xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2)
            a_err = abs((v[0][1] + v[2][1]) / 2 - mid)   # split along 0-2, or along 1-3
            b_err = abs((v[1][1] + v[3][1]) / 2 - mid)
            tris = ((0, 1, 2), (0, 2, 3)) if a_err <= b_err else ((0, 1, 3), (1, 2, 3))
            for tri in tris:
                m.tri([v[k] for k in tri], [tuv(v[k][0], v[k][2]) for k in tri], down=False)
    for (cx, cz), (dx, dz) in fans:
        apex, far = vert(cx, cz), vert(cx + dx * w, cz + dz * w)
        arc = [vert(cx + dx * w * math.cos(a), cz + dz * w * math.sin(a))
               for a in (math.pi / 2 * k / curve for k in range(curve + 1))]
        for k in range(curve):
            for tri in ((apex, arc[k], arc[k + 1]), (far, arc[k + 1], arc[k])):   # the cone, the flat top round it
                m.tri(list(tri), [tuv(px, pz) for px, _, pz in tri], down=False)


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


def set_tile(size):
    """Build for tiles `size` world units wide (levels and the floor scale with them)."""
    global TILE, LEVEL_H, FLOOR0
    k = size / TILE
    TILE, LEVEL_H, FLOOR0 = TILE * k, LEVEL_H * k, FLOOR0 * k


def main(argv):
    if not argv:
        sys.exit(__doc__)
    folder = Path(argv[0])
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else folder
    tag = argv[argv.index("--tag") + 1] if "--tag" in argv else "v1"
    if "--tile" in argv:
        set_tile(float(argv[argv.index("--tile") + 1]))
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
