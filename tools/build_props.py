"""Build the table props: the slanted team stand (pedestals on top, item/skill cards on the slope) and a pillar.

Usage:  python -I tools/build_props.py
Writes props/stand-v1.obj, props/pillar-v1.obj, props/props-v1.jpg (shared texture) and props/stand-v1.json
(slot positions the TTS script uses: pedestals on top, two card slots per pedestal on the slope).

Stand, in its own frame (as placed on the near/south trim): the back face (toward the board) is z = 0 and the
stand extends toward -z (toward the player); y = 0 is the table top. Cross-section: a flat top for the
pedestals, a slope down toward the player for the cards, and a small lip at the bottom so cards don't slide.
The far/north stand is the same model turned 180 degrees.
"""
import json, math, sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_standee import StandeeMesh  # noqa: E402  (quad + tri; OBJ with TTS's X mirroring handled)

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "props"
SLOTS, SLOT_W = 6, 7.05          # pedestal columns and their spacing (the original pedestal spacing)
LENGTH = SLOTS * SLOT_W
TOP_H, TOP_D = 2.6, 3.2          # top surface height above the table, and its depth
RUN, LOW_H = 7.6, 0.35           # slope: horizontal run toward the player, height at its bottom
LIP_H, LIP_W = 0.22, 0.25        # lip at the bottom of the slope
CARD_SCALE = 1.5                 # cards lie landscape: 3.06 x 2.19 at scale 1
CARD_ALONG = 2.19 * CARD_SCALE   # card size along the slope
PILLAR_H, SEG = 2.6, 28          # pillar height (level with the stand top), segments around
TEX_W, TEX_H = 1024, 256         # texture: four 256px regions
REGIONS = {"top": 0, "slope": 1, "side": 2, "pillar": 3}
COLOURS = {"top": "#CDB38A", "slope": "#BFA27A", "side": "#8E6C48", "pillar": "#B39572"}


def region_uv(name, fu, fv):
    """fu, fv in 0..1 within a region -> texture UV."""
    i = REGIONS[name]
    return ((i * 256 + 2 + fu * 252) / TEX_W, 1 - (2 + fv * 252) / TEX_H)


def face(m, name, corners, normal):
    m.quad(corners, [region_uv(name, 0, 0), region_uv(name, 1, 0), region_uv(name, 1, 1), region_uv(name, 0, 1)], normal)


def stand():
    m = StandeeMesh()
    x0, x1 = -LENGTH / 2, LENGTH / 2
    zc, zd = -TOP_D, -TOP_D - RUN          # top front edge, slope bottom
    ze = zd - LIP_W                        # front of the lip
    yl = LOW_H + LIP_H                     # top of the lip
    slope_n = (0, RUN, -(TOP_H - LOW_H))
    ln = math.hypot(slope_n[1], slope_n[2])
    slope_n = (0, slope_n[1] / ln, slope_n[2] / ln)
    face(m, "top", [(x0, TOP_H, 0), (x1, TOP_H, 0), (x1, TOP_H, zc), (x0, TOP_H, zc)], (0, 1, 0))
    face(m, "slope", [(x0, TOP_H, zc), (x1, TOP_H, zc), (x1, LOW_H, zd), (x0, LOW_H, zd)], slope_n)
    face(m, "side", [(x0, LOW_H, zd), (x1, LOW_H, zd), (x1, yl, zd), (x0, yl, zd)], (0, 0, 1))       # lip, inner
    face(m, "top", [(x0, yl, zd), (x1, yl, zd), (x1, yl, ze), (x0, yl, ze)], (0, 1, 0))              # lip, top
    face(m, "side", [(x0, yl, ze), (x1, yl, ze), (x1, 0, ze), (x0, 0, ze)], (0, 0, -1))              # front
    face(m, "side", [(x0, 0, 0), (x1, 0, 0), (x1, TOP_H, 0), (x0, TOP_H, 0)], (0, 0, 1))             # back
    face(m, "side", [(x0, 0, ze), (x1, 0, ze), (x1, 0, 0), (x0, 0, 0)], (0, -1, 0))                  # bottom
    # end caps: the main body (a convex pentagon, as a fan) plus the lip block
    for x, nx in ((x0, -1), (x1, 1)):
        body = [(x, 0, 0), (x, TOP_H, 0), (x, TOP_H, zc), (x, LOW_H, zd), (x, 0, zd)]
        for a, b in ((1, 2), (2, 3), (3, 4)):
            uv = [region_uv("side", 0.5, 0.5)] * 3
            m.tri([body[0], body[a], body[b]], uv, (nx, 0, 0))
        face(m, "side", [(x, 0, zd), (x, yl, zd), (x, yl, ze), (x, 0, ze)], (nx, 0, 0))
    return m


def pillar():
    """Unit radius (scale x/z per object): base ring, shaft, cap ring."""
    m = StandeeMesh()
    rings = [(1.15, 0.0), (1.15, 0.22), (1.0, 0.22), (1.0, PILLAR_H - 0.22), (1.15, PILLAR_H - 0.22), (1.15, PILLAR_H)]
    pts = [(math.cos(2 * math.pi * i / SEG), math.sin(2 * math.pi * i / SEG)) for i in range(SEG)]
    for (r0, y0), (r1, y1) in zip(rings, rings[1:]):
        for i in range(SEG):
            (ca, sa), (cb, sb) = pts[i], pts[(i + 1) % SEG]
            mx, mz = (ca + cb) / 2, (sa + sb) / 2
            n = math.hypot(mx, mz)
            if y0 != y1:
                normal = (mx / n, 0, mz / n)          # a wall: faces outward
            else:
                normal = (0, 1 if r1 < r0 else -1, 0)  # a flat ledge: top of the base ring / underside of the cap
            uv = [region_uv("pillar", i / SEG, y0 / PILLAR_H), region_uv("pillar", (i + 1) / SEG, y0 / PILLAR_H),
                  region_uv("pillar", (i + 1) / SEG, y1 / PILLAR_H), region_uv("pillar", i / SEG, y1 / PILLAR_H)]
            m.quad([(r0 * ca, y0, r0 * sa), (r0 * cb, y0, r0 * sb), (r1 * cb, y1, r1 * sb), (r1 * ca, y1, r1 * sa)], uv, normal)
    for y, ny in ((PILLAR_H, 1), (0.0, -1)):  # caps
        for i in range(SEG):
            (ca, sa), (cb, sb) = pts[i], pts[(i + 1) % SEG]
            uv = [region_uv("top", 0.5, 0.5)] * 3
            m.tri([(0, y, 0), (1.15 * ca, y, 1.15 * sa), (1.15 * cb, y, 1.15 * sb)], uv, (0, ny, 0))
    return m


def texture():
    img = Image.new("RGB", (TEX_W, TEX_H))
    d = ImageDraw.Draw(img)
    for name, i in REGIONS.items():
        h = COLOURS[name]
        d.rectangle([i * 256, 0, i * 256 + 255, TEX_H], fill=tuple(int(h[k:k + 2], 16) for k in (1, 3, 5)))
    return ImageChops.add(img, Image.effect_noise((TEX_W, TEX_H), 8).convert("RGB"), 1.0, -128)


def slots():
    """Slot positions in the stand's frame. Card rotation is (0, yaw, tilt): the card is turned a quarter so it
    lies landscape, then tilted to the slope (see Global.lua for the yaw)."""
    tilt = math.degrees(math.atan2(TOP_H - LOW_H, RUN))
    length = math.hypot(RUN, TOP_H - LOW_H)
    ux, uy = -RUN / length, -(TOP_H - LOW_H) / length          # down the slope: (z, y) per unit
    first = 0.35 + CARD_ALONG / 2
    cards = {}
    for kind, t in (("items", first), ("skills", first + CARD_ALONG + 0.3)):
        cards[kind] = {"z": round(-TOP_D + ux * t, 4), "y": round(TOP_H + uy * t + 0.03, 4)}
    return {"x": [round((i - (SLOTS - 1) / 2) * SLOT_W, 4) for i in range(SLOTS)],
            "pedestal": {"z": -TOP_D / 2, "y": TOP_H}, "cards": cards, "tilt": round(tilt, 3),
            "card_scale": CARD_SCALE, "depth": TOP_D + RUN + LIP_W, "length": LENGTH, "pillar_height": PILLAR_H}


def main():
    OUT.mkdir(exist_ok=True)
    stand().write(OUT / "stand-v1.obj")
    pillar().write(OUT / "pillar-v1.obj")
    texture().save(OUT / "props-v1.jpg", quality=92)
    info = slots()
    (OUT / "stand-v1.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(json.dumps(info))


if __name__ == "__main__":
    main()
