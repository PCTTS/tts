"""Put an arena's 3D pieces (flags, portals, bridges, optionally bells) on its marker tiles in the open TTS game.

Usage:  python -I tools/place_pieces.py arenas/<name> [--board board-vN.json] [--local [folder]]
--local loads the models from this repo (or from a folder holding a copy of props/) instead of the PCTTS site: a
preview only this computer can see. Run again without it, after publishing, before saving the game. TTS keeps a
model it has loaded for as long as it runs, so preview a changed model from a fresh folder.
Reads the arena's map.json (markers) and its board geometry JSON (tile size, level heights; default: the
highest-numbered board-v*.json), finds the locked board named after the arena, removes the pieces placed
before (tag "ArenaPiece") and spawns new ones, locked, relative to the board, for every legend entry with
"piece": true (other markers are only painted on the board):
  flag: a flag in the tile's corner farthest from the board's centre, its triangle pointing back in over its own
        tile (the user's choice: the flag stays over its tile), so a Pokemon
        can stand on the tile. Starts neutral; right-click > Capture tints it to the player's colour (Global.lua).
  bell-attack / bell-defense: a bronze bell ("ATK bell" / "DEF bell") hanging over the middle of the tile in a
        wooden stand whose posts stand on its sides, facing away from the pit (like the painted symbol).
        Pugilis keeps its bells as painted symbols only.
  portal: a round tile lying on the tile, in its starting pair's colour ("pair" in the legend); a die on it
        shuffles every portal's pair (Global.lua).
  trap: a trap piece on the tile; right-click > Spring trap removes it once it's been used (Global.lua).
  tree / gift: a tree tile (Yaksha) or a gift box on the tile, NOT locked: players lift it off / move it themselves.
  zone (capture zone tiles): a frame around each square group of them (2x2), which takes the colour of the player
        with more Pokemon inside (Global.lua). A zone raised above every tile round it, with sloping edges, gets
        the frame drawn in on its flat top (Yaksha's centre).
  bridge tiles (legend "bridge": true, sky with no board): each run of them between two islands is one rope
        bridge, 1 or 2 tiles long, carrying its own snap points; it starts dropped (closed) and the arrows on it
        raise or drop all the bridges (Global.lua).
Models come from tools/build_pieces.py. Global.lua's spawnArenaPiece spawns them, as the map picker does. TTS only
keeps the result in memory: save the game afterwards.
"""
import json, math, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_board import Arena  # noqa: E402
from build_pieces import BELL_LIFT  # noqa: E402  (the stand's beam is built for the bell at this height)
from tts import exec_lua, report  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
BASE_URL = "https://pctts.github.io/tts/"
FLAG_INSET = 0.38        # the pole's distance from the two tile edges of its corner
BELL = {"mesh": "props/bell-v3.obj", "diffuse": "props/bell-v3.jpg", "collider": "props/bell-collider-v3.obj",
        "convex": True, "material": 2}
FLAG = {"mesh": "props/flag-v2.obj", "diffuse": "props/flag-v2.jpg", "collider": "props/flag-collider-v3.obj",
        "convex": False, "material": 3}
STAND = {"mesh": "props/bellstand-v1.obj", "diffuse": "props/stand-wood-v1.jpg", "collider": "props/bellstand-v1.obj",
         "convex": False, "material": 1}
PORTAL = {"mesh": "props/portal-v1.obj", "diffuse": "props/portal-v1.jpg", "collider": "props/portal-v1.obj",
          "convex": True, "material": 3}
BRIDGES = {n: {"mesh": f"props/bridge{n}-v1.obj", "diffuse": "props/bridge-v1.jpg",
               "collider": f"props/bridge-collider{n}-v1.obj", "convex": True, "material": 1} for n in (1, 2)}
TRAP = {"mesh": "props/trap-v1.obj", "diffuse": "props/trap-v1.jpg", "collider": "props/trap-collider-v1.obj",
        "convex": True, "material": 2}
ZONES = {n: {"mesh": f"props/zoneframe{n}-v1.obj", "diffuse": "props/zoneframe-v1.jpg", "collider": f"props/zoneframe{n}-v1.obj",
             "convex": False, "material": 3} for n in (2, 4)}
RAISED_SLANT = 0.8   # tools/build_pieces.py: the raised zone frames sit this far inside the zone's border
RAISED_ZONES = {n: {**ZONES[n], "mesh": f"props/zoneframe{n}-raised-v1.obj", "collider": f"props/zoneframe{n}-raised-v1.obj"}
                for n in (2, 4)}
TREE = {"mesh": "props/tree-v1.obj", "diffuse": "props/tree-v1.jpg", "collider": "props/tree-collider-v1.obj",
        "convex": True, "material": 1}
GIFT = {"mesh": "props/gift-v1.obj", "diffuse": "props/gift-v1.jpg", "collider": "props/gift-v1.obj",
        "convex": True, "material": 3}
BELLS = {"bell-attack": ("ATK bell", "attack"), "bell-defense": ("DEF bell", "defense")}


def zones(data, info):
    """One frame per square group of capture zone tiles: [(size, (cx, top, cz))]."""
    R, C, T = info["rows"], info["cols"], info["tile"]
    cells = {(r, c) for r, row in enumerate(data["grid"]) for c, ch in enumerate(row)
             if data["legend"][ch].get("marker") == "zone" and data["legend"][ch].get("piece")}
    out, seen = [], set()
    for start in sorted(cells):
        if start in seen:
            continue
        group, todo = [], [start]
        seen.add(start)
        while todo:
            r, c = todo.pop()
            group.append((r, c))
            for n in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if n in cells and n not in seen:
                    seen.add(n)
                    todo.append(n)
        rows, cols = sorted({r for r, _ in group}), sorted({c for _, c in group})
        size = len(rows)
        if len(cols) != size or len(group) != size * size or size not in ZONES:
            sys.exit(f"capture zone tiles {sorted(group)}: only square 2x2 or 4x4 zones have a frame")
        tile = data["legend"][data["grid"][rows[0]][cols[0]]]
        top = info["floor0"] + tile.get("level", 0) * info["level_height"] - tile.get("sink", 0.0)
        cx = sum((c + 0.5 - C / 2) * T for _, c in group) / len(group)
        cz = sum((R / 2 - r - 0.5) * T for r, _ in group) / len(group)
        # raised above every tile round it, with sloping edges: the frame that sits inside the slopes
        around = [(r + dr, c + dc) for r, c in group for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                  if (r + dr, c + dc) not in cells]
        lower = [n for n in around if (level_at(data, *n) or -1) < tile.get("level", 0)]
        raised = tile.get("slant") and len(lower) == len(around)
        if raised and tile["slant"] != RAISED_SLANT:
            sys.exit(f"capture zone {sorted(group)}: a raised zone's frame fits slant {RAISED_SLANT} only")
        out.append((size, (cx, top, cz), bool(raised)))
    return out


def level_at(data, r, c):
    """A grid tile's level, or None outside the grid or on void."""
    if 0 <= r < len(data["grid"]) and 0 <= c < len(data["grid"][0]):
        t = data["legend"][data["grid"][r][c]]
        return None if t.get("void") else t.get("level", 0)
    return None


def bridges(data, grid, info):
    """One bridge per run of bridge tiles: [(tiles, (cx, top, cz), yaw)]. A run lies along a row or a column with an
    island tile at each end (a single tile: islands on two opposite sides); the deck is level with those islands."""
    R, C, T = info["rows"], info["cols"], info["tile"]
    cells = {(r, c) for r, row in enumerate(data["grid"]) for c, ch in enumerate(row) if data["legend"][ch].get("bridge")}
    out, seen = [], set()
    for start in sorted(cells):
        if start in seen:
            continue
        run, todo = [], [start]
        seen.add(start)
        while todo:
            r, c = todo.pop()
            run.append((r, c))
            for n in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if n in cells and n not in seen:
                    seen.add(n)
                    todo.append(n)
        rows, cols = sorted({r for r, _ in run}), sorted({c for _, c in run})
        r0, c0 = rows[0], cols[0]
        along_x = len(rows) == 1 and (len(cols) > 1 or (grid.tile(r0, c0 - 1) and grid.tile(r0, c0 + 1)))
        ends = [(r0, cols[0] - 1), (r0, cols[-1] + 1)] if along_x else [(rows[0] - 1, c0), (rows[-1] + 1, c0)]
        lands = [grid.tile(*e) for e in ends]
        if len(rows) > 1 and len(cols) > 1 or not all(lands) or len(run) not in BRIDGES:
            sys.exit(f"bridge tiles {sorted(run)}: a bridge must be 1 or 2 tiles in a line with an island at each end")
        top = info["floor0"] + lands[0].get("level", 0) * info["level_height"]
        cx = sum((c + 0.5 - C / 2) * T for _, c in run) / len(run)
        cz = sum((R / 2 - r - 0.5) * T for r, _ in run) / len(run)
        out.append((len(run), (cx, top, cz), 0 if along_x else 90))
    return out


def board_json(arena, name=None):
    if name:
        return arena / name
    boards = sorted(arena.glob("board-v*.json"), key=lambda p: int(re.search(r"v(\d+)", p.name).group(1)))
    return boards[-1]


def pieces(arena, info):
    data = json.loads((arena / "map.json").read_text(encoding="utf-8"))
    grid = Arena(arena)
    R, C, T = info["rows"], info["cols"], info["tile"]
    out = []
    for r, row in enumerate(data["grid"]):
        for c, ch in enumerate(row):
            tile = data["legend"].get(ch, {})
            marker = tile.get("marker", "")
            if tile.get("void") or not tile.get("piece") or not (marker in BELLS or marker in ("flag", "portal", "trap", "tree", "gift")):
                continue
            cx, cz = (c + 0.5 - C / 2) * T, (R / 2 - r - 0.5) * T
            top = info["floor0"] + tile["level"] * info["level_height"] - tile.get("sink", 0.0)
            if marker in ("tree", "gift"):
                name, model = ("Tree", TREE) if marker == "tree" else ("Gift", GIFT)
                out.append({"kind": name, "name": name if marker == "tree" else "Gift box", "model": model,
                            "pos": [cx, top, cz], "yaw": 0, "desc": "", "free": True})
            elif marker == "trap":
                out.append({"kind": "Trap", "name": "Trap", "model": TRAP, "pos": [cx, top, cz], "yaw": 0, "desc": ""})
            elif marker == "portal":
                out.append({"kind": "Portal", "name": "Portal", "model": PORTAL, "pos": [cx, top, cz], "yaw": 0,
                            "desc": "", "pair": tile.get("pair", 1)})
            elif marker in BELLS:
                name, stat = BELLS[marker]
                desc = (f"Attack this bell to give all your Pokemon the {stat} bonus until the end of the turn. "
                        "Each bell can only be rung once per turn.")
                out.append({"kind": "Bell", "name": name, "model": BELL, "pos": [cx, top + BELL_LIFT, cz], "yaw": 0, "desc": desc})
                # the stand's posts sit on the bell's sides as seen from the side away from the pit (where its
                # painted symbol is read from): beam across that direction
                away = grid.away_from_pit(r, c)
                out.append({"kind": "BellStand", "name": name + " stand", "model": STAND, "pos": [cx, top, cz],
                            "yaw": 90 if away and away[1] else 0, "desc": desc})
            else:
                sx, sz = (1 if cx >= 0 else -1), (1 if cz >= 0 else -1)
                pos = [cx + sx * (T / 2 - FLAG_INSET), top, cz + sz * (T / 2 - FLAG_INSET)]
                yaw = math.degrees(math.atan2(-sz, sx)) + 180   # TTS yaw that turns the model's +x toward (-sx, -sz)
                out.append({"kind": "Flag", "name": "Flag", "model": FLAG, "pos": pos, "yaw": yaw % 360, "desc": ""})
    for size, pos, raised in zones(data, info):
        out.append({"kind": "Zone", "name": "Capture zone", "model": (RAISED_ZONES if raised else ZONES)[size], "pos": list(pos), "yaw": 0,
                    "desc": "", "tiles": size, "tile": round(T, 5)})
    for tiles, pos, yaw in bridges(data, grid, info):
        out.append({"kind": "Bridge", "name": "Rope bridge", "model": BRIDGES[tiles], "pos": list(pos), "yaw": yaw,
                    "desc": "", "tiles": tiles, "tile": round(T, 5)})
    return data["name"], out


LUA = r"""
local arena, list = %(arena)s, JSON.decode(%(pieces)s)
local board = nil
for _, o in ipairs(getAllObjects()) do
  if o.getName() == arena and o.getLock() and o.name == "Custom_Model" then board = o end
end
if not board then return "no locked board named " .. arena end
local removed = 0
for _, o in ipairs(getAllObjects()) do
  if o.hasTag("ArenaPiece") then o.destruct(); removed = removed + 1 end
end
for _, p in ipairs(list) do
  for k, v in pairs(p.model) do p[k] = v end   -- the index's flat form
  spawnArenaPiece(p, board.getPosition(), %(base)s)   -- Global.lua (boards are never turned)
end
return "removed " .. removed .. ", placed " .. #list .. " on " .. arena .. " (" .. board.guid .. ")"
"""


def main(argv):
    if not argv:
        sys.exit(__doc__)
    arena = REPO / argv[0] if not Path(argv[0]).is_absolute() else Path(argv[0])
    info = json.loads(board_json(arena, argv[argv.index("--board") + 1] if "--board" in argv else None).read_text(encoding="utf-8"))
    name, items = pieces(arena, info)
    for p in items:
        print(f"{p['name']:9s} at ({p['pos'][0]:7.3f}, {p['pos'][1]:6.3f}, {p['pos'][2]:7.3f}) yaw {p['yaw']:.0f}")
    q = lambda s: json.dumps(s)
    base = BASE_URL
    if "--local" in argv:
        i = argv.index("--local")
        folder = Path(argv[i + 1]) if i + 1 < len(argv) and not argv[i + 1].startswith("--") else REPO
        base = "file:///" + folder.resolve().as_posix() + "/"     # TTS wants the spaces left unescaped
    report(exec_lua(LUA % {"arena": q(name), "pieces": q(json.dumps(items)), "base": q(base)}, wait=10))


if __name__ == "__main__":
    main(sys.argv[1:])
