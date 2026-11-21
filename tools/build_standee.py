"""Build a 3D standee for a figure image: a cut-out of the artwork standing on a round base with a facing arrow.

Usage:  python -I tools/build_standee.py <figure image> --out DIR --tag TAG
        python -I tools/build_standee.py --mesh models/standee-v2.obj     (the mesh with the HP sign)
Writes DIR/<TAG>.obj and DIR/<TAG>.png (the artwork plus a strip for the base).

Why a model instead of TTS's figurine: a custom model's colour tint recolours its whole texture (a figurine's
tint only reaches its stand), so statuses can tint the artwork. Seen from behind, the same texture shows
mirrored, so no separate back image is needed. The front faces -z (towards a seat with rotation 0); the
base's arrow points to the art's left, which counts as the Pokemon's facing.
"""
import math, sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_board import Mesh  # noqa: E402  (writes OBJ with TTS's X mirroring handled)

SIZE = 2.0        # artwork width and height (world units)
BASE_R = 0.7      # base radius
BASE_H = 0.15     # base height
SEGMENTS = 32
# The HP sign (standee-v2): a thin solid plate above the head. Global.lua puts the HP label on each face (object UI,
# HP_HEIGHT -255 = PLATE_Y); TTS draws one object's UI in a fixed order, but solid geometry hides UI behind it, so
# from either side only that side's label shows, the right way round.
PLATE_W, PLATE_H, PLATE_D, PLATE_Y = 1.7, 0.5, 0.04, 2.55   # width, height, thickness, centre height
IMG, STRIP = 512, 128   # texture: artwork on top, base strip underneath
TEX_W, TEX_H = IMG, IMG + STRIP


class StandeeMesh(Mesh):
    def tri(self, pts, uvs, normal):
        """A triangle, as a quad with a repeated corner (Mesh only writes quads)."""
        self.quad([pts[0], pts[1], pts[2], pts[2]], [uvs[0], uvs[1], uvs[2], uvs[2]], normal)


def texture(figure_path):
    return standee_texture(Image.open(figure_path))


def standee_texture(art):
    """The standee's texture for a figure image (square, feet at the bottom): the art, and the base strip under it."""
    tex = Image.new("RGBA", (TEX_W, TEX_H), (0, 0, 0, 0))
    art = art.convert("RGBA")
    if art.size != (IMG, IMG):
        art = art.resize((IMG, IMG), Image.LANCZOS)
    tex.alpha_composite(art, (0, 0))
    S = 4  # draw the base strip at 4x for smooth edges
    strip = Image.new("RGBA", (TEX_W * S, STRIP * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)
    c, r = 64 * S, 62 * S
    d.ellipse([c - r, c - r, c + r, c + r], fill=(43, 43, 48, 255), outline=(95, 95, 105, 255), width=5 * S)
    # arrow pointing left (towards -x in the world = the art's left)
    d.polygon([(c - 46 * S, c), (c - 6 * S, c - 30 * S), (c - 6 * S, c - 12 * S), (c + 40 * S, c - 12 * S),
               (c + 40 * S, c + 12 * S), (c - 6 * S, c + 12 * S), (c - 6 * S, c + 30 * S)], fill=(236, 236, 240, 255))
    d.rectangle([128 * S, 0, 256 * S - 1, STRIP * S - 1], fill=(58, 58, 64, 255))  # base side colour
    tex.alpha_composite(strip.resize((TEX_W, STRIP), Image.LANCZOS), (0, IMG))
    return tex


def mesh(plate=False):
    m = StandeeMesh()

    def uv(px, py):
        return px / TEX_W, 1 - py / TEX_H

    # artwork: front faces -z, back faces +z with the same UVs (so it reads mirrored from behind)
    y0, y1, h = BASE_H - 0.02, BASE_H - 0.02 + SIZE, SIZE / 2
    corners = [(-h, y1, 0), (h, y1, 0), (h, y0, 0), (-h, y0, 0)]
    uvs = [uv(0.5, 0.5), uv(IMG - 0.5, 0.5), uv(IMG - 0.5, IMG - 0.5), uv(0.5, IMG - 0.5)]
    m.quad(corners, uvs, (0, 0, -1))
    m.quad(corners, uvs, (0, 0, 1))

    # base: a short cylinder; its top shows the disc with the arrow
    ring = [(BASE_R * math.cos(2 * math.pi * i / SEGMENTS), BASE_R * math.sin(2 * math.pi * i / SEGMENTS))
            for i in range(SEGMENTS)]

    def top_uv(x, z):
        return uv(64 + 61 * x / BASE_R, IMG + 64 - 61 * z / BASE_R)

    for i in range(SEGMENTS):
        (xa, za), (xb, zb) = ring[i], ring[(i + 1) % SEGMENTS]
        m.tri([(0, BASE_H, 0), (xa, BASE_H, za), (xb, BASE_H, zb)], [top_uv(0, 0), top_uv(xa, za), top_uv(xb, zb)], (0, 1, 0))
        m.tri([(0, 0, 0), (xb, 0, zb), (xa, 0, za)], [uv(192, IMG + 64)] * 3, (0, -1, 0))
        mx, mz = (xa + xb) / 2, (za + zb) / 2
        n = math.hypot(mx, mz)
        side = [uv(130, IMG + 4), uv(254, IMG + 4), uv(254, IMG + 124), uv(130, IMG + 124)]
        m.quad([(xa, BASE_H, za), (xb, BASE_H, zb), (xb, 0, zb), (xa, 0, za)], side, (mx / n, 0, mz / n))
    if plate:  # a dark box (the base side's colour), PLATE_D thick
        dark = [uv(192, IMG + 64)] * 4
        x0, x1, y0, y1, z0, z1 = -PLATE_W / 2, PLATE_W / 2, PLATE_Y - PLATE_H / 2, PLATE_Y + PLATE_H / 2, -PLATE_D / 2, PLATE_D / 2
        m.quad([(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)], dark, (0, 0, -1))   # front
        m.quad([(x0, y1, z1), (x1, y1, z1), (x1, y0, z1), (x0, y0, z1)], dark, (0, 0, 1))    # back
        m.quad([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], dark, (0, 1, 0))    # top
        m.quad([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], dark, (0, -1, 0))   # bottom
        m.quad([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], dark, (-1, 0, 0))   # sides
        m.quad([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], dark, (1, 0, 0))
    return m


def main(argv):
    if argv[:1] == ["--mesh"]:   # just the mesh with the HP sign: python -I tools/build_standee.py --mesh models/standee-v2.obj
        mesh(plate=True).write(argv[1])
        print("wrote", argv[1])
        return
    if len(argv) < 1 or "--out" not in argv or "--tag" not in argv:
        sys.exit(__doc__)
    out, tag = Path(argv[argv.index("--out") + 1]), argv[argv.index("--tag") + 1]
    out.mkdir(parents=True, exist_ok=True)
    mesh().write(out / f"{tag}.obj")
    texture(argv[0]).save(out / f"{tag}.png")
    print("wrote", out / tag, "(.obj, .png)")


if __name__ == "__main__":
    main(sys.argv[1:])
