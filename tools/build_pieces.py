"""Build the arena pieces: a floating golden-bronze bell and a capturable flag.

Usage:  python -I tools/build_pieces.py
Writes (only files that are missing: bump a version when what a file holds changes, TTS caches by link):
  props/bell-v3.obj, props/bell-v3.jpg, props/bell-collider-v3.obj
  (superseded, kept for older saves: v1 a church bell with a loop, v2 a rocket-nozzle bell)
  props/flag-v1.obj, props/flag-v1.jpg, props/flag-collider-v1.obj
tools/place_pieces.py puts them on an arena's marker tiles.

Bell: the board's bell icon turned around its axis: a dome, a straight flaring skirt, a darker rim band and a ball
clapper hanging in the open mouth; hollow and dark inside. Its own frame: y = 0 is the bottom of the rim, centred on
the y axis.
Flag: a dark pole on a small round foot with a white cloth that waves out along +x, and a white ball on top.
The whole model is tinted to show who holds the flag: white parts take the tint's colour, the dark pole stays
dark. Its own frame: y = 0 is the tile top, the pole stands on the y axis.
"""
import math, sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_props import SmoothMesh  # noqa: E402  (OBJ with smooth normals; TTS's X mirroring handled)

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "props"
SEG = 64                              # segments around lathed parts

# --- bell (units: a tile is about 3.25 across) -------------------------------------------------------
# The bell is the board's bell icon (tools/build_board.py, draw_marker) turned around its axis, in the icon's design
# units (a tile is 128 there): a dome (the top half of the icon's ellipse), a straight flaring skirt (its trapezoid),
# a rim band that steps out a little, and the ball clapper hanging in the mouth. BELL_UNIT scales it to the world.
ICON_DOME = (26, 25, 19)                 # dome: radius, centre height, rise
ICON_SKIRT = ((26, 24), (34.75, -4))     # skirt: top and bottom (radius, height); the rim covers the rest of it
ICON_RIM = (37, -4, -11)                 # rim band: radius, top, bottom
ICON_CLAPPER = (6.5, -15)                # clapper ball: radius, centre height
ICON_WALL = 2.5                          # wall thickness
BELL_UNIT = 0.8 / ICON_RIM[0]            # world units per icon unit: the mouth is 1.6 across
BELL_TOP = (ICON_DOME[1] + ICON_DOME[2] - ICON_RIM[2]) * BELL_UNIT   # height of the dome's top above the mouth
BRONZE = (204, 156, 70)
BRONZE_DEEP = (122, 84, 34)
BRONZE_LIGHT = (236, 198, 118)
BRONZE_RIM = (150, 105, 30)              # the icon's darker gold: rim band and clapper

# --- flag ---------------------------------------------------------------------------------------------
POLE_R, POLE_H = 0.05, 3.3
FOOT_R = 0.28
FINIAL_R = 0.11
CLOTH_L, CLOTH_H, CLOTH_TOP = 1.7, 1.0, 3.2
WAVE_A, WAVES, DROOP = 0.10, 1.25, 0.12
CLOTH_NX, CLOTH_NY = 32, 8
FLAG_WHITE = (246, 246, 243)
POLE_DARK = (50, 38, 28)


def norm(v):
    m = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / m for c in v)


class PieceMesh(SmoothMesh):
    def face4(self, corners, uvs, normals):
        """A quad with one normal per corner, wound to face along their average. Uses the diagonals for the
        winding, so a quad with two corners on the axis (a cone tip) still faces the right way."""
        f = norm(tuple(sum(n[i] for n in normals) for i in range(3)))
        facing = (-f[0], f[1], f[2])                                     # worked out as written (x mirrored),
        p = [(-x, y, z) for x, y, z in corners]                          # like SmoothMesh.quad_smooth
        d1 = [p[2][i] - p[0][i] for i in range(3)]
        d2 = [p[3][i] - p[1][i] for i in range(3)]
        cross = (d1[1] * d2[2] - d1[2] * d2[1], d1[2] * d2[0] - d1[0] * d2[2], d1[0] * d2[1] - d1[1] * d2[0])
        order = [0, 1, 2, 3] if sum(cross[i] * facing[i] for i in range(3)) > 0 else [3, 2, 1, 0]
        bv, bt, bn = len(self.v), len(self.vt), len(self.vn)
        self.v += [p[i] for i in order]                                  # TTS mirrors OBJ on X
        self.vt += [uvs[i] for i in order]
        self.vn += [(-normals[i][0], normals[i][1], normals[i][2]) for i in order]
        idx = [(bv + k + 1, bt + k + 1, bn + k + 1) for k in range(4)]
        self.f.append((idx[0], idx[1], idx[2]))
        self.f.append((idx[0], idx[2], idx[3]))

    def flat(self, corners, uv, normal):
        self.face4(corners, [uv] * 4, [normal] * 4)


def lathe(m, run, uv, seg=SEG):
    """Turn a profile [(radius, height), ...] around the y axis. The visible side is on the right of the
    direction of travel (going up the outside, or down the inside). Smooth along the run and around."""
    seg_n = [norm((y1 - y0, -(r1 - r0))) for (r0, y0), (r1, y1) in zip(run, run[1:])]
    vert_n = [norm(tuple(sum(seg_n[j][k] for j in (i - 1, i) if 0 <= j < len(seg_n)) for k in range(2)))
              for i in range(len(run))]
    ring = [(math.cos(2 * math.pi * k / seg), math.sin(2 * math.pi * k / seg)) for k in range(seg + 1)]
    for i in range(len(run) - 1):
        (r0, y0), (r1, y1) = run[i], run[i + 1]
        (n0r, n0y), (n1r, n1y) = vert_n[i], vert_n[i + 1]
        for k in range(seg):
            (ca, sa), (cb, sb) = ring[k], ring[k + 1]
            corners = [(r0 * ca, y0, r0 * sa), (r0 * cb, y0, r0 * sb), (r1 * cb, y1, r1 * sb), (r1 * ca, y1, r1 * sa)]
            normals = [(n0r * ca, n0y, n0r * sa), (n0r * cb, n0y, n0r * sb), (n1r * cb, n1y, n1r * sb), (n1r * ca, n1y, n1r * sa)]
            fu0, fu1 = k / seg, (k + 1) / seg
            m.face4(corners, [uv(fu0, y0), uv(fu1, y0), uv(fu1, y1), uv(fu0, y1)], normals)


def sphere_profile(radius, centre_y, n=16):
    return [(radius * math.sin(math.pi * i / n), centre_y - radius * math.cos(math.pi * i / n)) for i in range(n + 1)]


def box(m, x0, x1, y0, y1, z0, z1, uv=(0.5, 0.5)):
    m.flat([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], uv, (0, 1, 0))
    m.flat([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], uv, (0, -1, 0))
    m.flat([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], uv, (0, 0, -1))
    m.flat([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], uv, (0, 0, 1))
    m.flat([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], uv, (-1, 0, 0))
    m.flat([(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)], uv, (1, 0, 0))


# ------------------------------------------------------------------------------------------------ bell
BELL_TEX = 512
BELL_V0, BELL_V1 = 8, 504           # texture rows used for heights BELL_TOP .. 0


def bell_v(y):
    y = min(BELL_TOP, max(0.0, y))
    return 1 - (BELL_V0 + (1 - y / BELL_TOP) * (BELL_V1 - BELL_V0)) / BELL_TEX


def bell_region(u0, u1):
    return lambda fu, y: ((u0 + fu * (u1 - u0)) / BELL_TEX, bell_v(y))


def W(r, h):
    """Icon units -> the bell's own frame (y = 0 at the bottom of the rim)."""
    return (r * BELL_UNIT, (h - ICON_RIM[2]) * BELL_UNIT)


def dome_points(shrink=0.0, n=14):
    """The dome from its edge up to the top (or, shrunk by the wall, the inside of it)."""
    r, c, rise = ICON_DOME
    return [W((r - shrink) * math.cos(a), c + (rise - shrink) * math.sin(a)) for a in (math.pi / 2 * i / n for i in range(n + 1))]


def bell():
    m = PieceMesh()
    body, inside, rim = bell_region(4, 252), bell_region(260, 380), bell_region(392, 508)
    (r0, h0), (r1, h1) = ICON_SKIRT
    rr, rt, rb = ICON_RIM
    t = ICON_WALL
    lathe(m, [W(r1, h1), W(r0, h0)], body)                               # skirt (straight, crisp edges)
    lathe(m, dome_points(), body)                                        # dome
    lathe(m, [W(rr, rb), W(rr, rt)], rim)                                # rim band
    lathe(m, [W(rr, rt), W(r1, h1)], rim)                                # the ledge where the skirt meets it
    # inside: the dome and the skirt line moved in by the wall, from the top down to the bottom of the rim
    r_low = r1 + (r1 - r0) / (h1 - h0) * (rb - h1)                       # the skirt's line carried down to rb
    inner = dome_points(t)[::-1] + [W(r0 - t, h0), W(r1 - t, h1), W(r_low - t, rb)]
    lathe(m, inner, inside)
    lathe(m, [inner[-1], W(rr, rb)], rim)                                # underside of the rim
    cr, ch = ICON_CLAPPER
    lathe(m, sphere_profile(cr * BELL_UNIT, W(0, ch)[1]), rim, 32)       # clapper
    return m


def bell_collider():
    m = PieceMesh()
    (r0, h0), (r1, h1) = ICON_SKIRT
    rr, rt, rb = ICON_RIM
    cr, ch = ICON_CLAPPER
    run = [W(0, ch - cr), W(rr, rb), W(rr, rt), W(r0, h0)] + dome_points(n=4)[1:]
    lathe(m, run, lambda fu, y: (0.5, 0.5), 16)
    return m


def bell_texture():
    s = BELL_TEX
    rng = np.random.default_rng(11)
    img = np.zeros((s, s, 3), np.float32)
    rows = np.arange(s)
    y = BELL_TOP * (1 - (rows - BELL_V0) / (BELL_V1 - BELL_V0))   # the height each texture row shows
    base, deep, light, rim = (np.array(c, np.float32) for c in (BRONZE, BRONZE_DEEP, BRONZE_LIGHT, BRONZE_RIM))
    # body: a little darker toward the rim and the top, lightest a little above the middle
    t = np.clip(1 - np.abs(y - 0.55 * BELL_TOP) / (0.6 * BELL_TOP), 0, 1)[:, None]
    img[:, :256] = (base * (0.86 + 0.14 * t) + (light - base) * 0.18 * t)[:, None, :]
    img[:, 256:384] = (deep * 0.8)[None, None, :]                                       # inside
    img[:, 384:] = rim[None, None, :]                                                    # rim band, clapper
    img *= (1 + rng.normal(0, 0.025, (s, s, 1))).astype(np.float32)                     # faint casting texture
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")
    return out.filter(ImageFilter.GaussianBlur(0.6))


# ------------------------------------------------------------------------------------------------ flag
FLAG_TW, FLAG_TH = 512, 256


def flag_uv(px, py):
    return px / FLAG_TW, 1 - py / FLAG_TH


def cloth_point(fx, fy):
    """fx 0..1 from the pole out, fy 0..1 from the top edge down -> position and front normal."""
    x = POLE_R + fx * CLOTH_L
    ph = 2 * math.pi * WAVES * fx
    amp = WAVE_A * fx ** 0.7
    z = amp * math.sin(ph)
    dz = (WAVE_A * 0.7 * fx ** -0.3 * math.sin(ph) if fx > 0 else 0) + amp * 2 * math.pi * WAVES * math.cos(ph)
    dz /= CLOTH_L
    y = CLOTH_TOP - fy * CLOTH_H - DROOP * fx ** 2
    return (x, y, z), norm((-dz, 0.0, 1.0))


def flag():
    m = PieceMesh()
    dark = lambda fu, y: flag_uv(392 + 48 * fu, 8 + 240 * (1 - y / POLE_H))
    white = lambda fu, y: flag_uv(460 + 44 * fu, 128)
    lathe(m, [(FOOT_R, 0.0), (FOOT_R, 0.05), (FOOT_R * 0.8, 0.10), (POLE_R * 1.6, 0.13), (POLE_R, 0.15)], dark, 32)
    lathe(m, [(POLE_R, 0.15), (POLE_R, POLE_H)], dark, 24)
    lathe(m, sphere_profile(FINIAL_R, POLE_H + FINIAL_R * 0.8), white, 24)
    for i in range(CLOTH_NX):
        for j in range(CLOTH_NY):
            cells = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            pts, ns, uvs = [], [], []
            for ci, cj in cells:
                fx, fy = ci / CLOTH_NX, cj / CLOTH_NY
                p, n = cloth_point(fx, fy)
                pts.append(p)
                ns.append(n)
                uvs.append(flag_uv(6 + fx * 372, 6 + fy * 244))
            m.face4(pts, uvs, ns)                                              # front
            m.face4(pts, uvs, [tuple(-c for c in n) for n in ns])              # back
    return m


def flag_collider():
    """The pole and the cloth as two boxes (used as a non-convex collider on a locked flag)."""
    m = PieceMesh()
    box(m, -FOOT_R, FOOT_R, 0, POLE_H + 2 * FINIAL_R, -FOOT_R, FOOT_R)
    box(m, POLE_R, POLE_R + CLOTH_L, CLOTH_TOP - CLOTH_H - DROOP, CLOTH_TOP, -WAVE_A - 0.05, WAVE_A + 0.05)
    return m


def flag_texture():
    rng = np.random.default_rng(12)
    img = np.zeros((FLAG_TH, FLAG_TW, 3), np.float32)
    img[:, :] = FLAG_WHITE
    weave = rng.normal(0, 3.0, (FLAG_TH, FLAG_TW, 1)).astype(np.float32)
    img += weave
    img[:, 384:452] = POLE_DARK
    img[:, 384:452] *= (1 + rng.normal(0, 0.06, (1, 68, 1))).astype(np.float32)     # grain along the pole
    img[:, 452:] = FLAG_WHITE
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(out)
    hem = (222, 222, 217)
    d.rectangle([6, 6, 377, 249], outline=hem, width=9)        # hem around the cloth
    d.rectangle([6, 6, 26, 249], fill=(214, 214, 208))         # the sleeve around the pole
    return out


def main():
    OUT.mkdir(exist_ok=True)
    files = {
        "bell-v3.obj": lambda p: bell().write(p),
        "bell-v3.jpg": lambda p: bell_texture().save(p, quality=92),
        "bell-collider-v3.obj": lambda p: bell_collider().write(p),
        "flag-v1.obj": lambda p: flag().write(p),
        "flag-v1.jpg": lambda p: flag_texture().save(p, quality=92),
        "flag-collider-v1.obj": lambda p: flag_collider().write(p),
    }
    for name, make in files.items():
        if not (OUT / name).exists():
            make(OUT / name)
            print("wrote props/" + name)


if __name__ == "__main__":
    main()
