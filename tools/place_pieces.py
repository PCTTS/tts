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
  gate (Fontaine): a water gate on a river tile: four stone posts (GateFrame) and a sluice block (Gate) that rises
        to close it; legend "gate": its number, "branch" and "part" ("edge"/"inner"): which water it lets through.
  fountain (Fontaine): a marble fountain on a solid tile.
  statue (Spectra): a small stone pawn, NOT locked: players move it when the dice say so.
  blockerN (Valora): a steel block filling the tile (Door), opened and closed by gear N: it slides into the wall
        beside it (the one across from another blocker of its set, if any: a doorway's two halves part), or sinks
        into the floor where there's no wall. Blockers start closed.
  gears (Valora, map.json "gears": [{"at": [row, col], "size": 3|4, "turn": "ccw"|"cw", "number": n}]): a steel
        plate (Gear) over each gear's tiles that Global.lua turns. Its tiles have "snap": false: the plate carries
        their snap points. A capture zone on a gear (legend "lift": its thickness) sits on the plate.
  water tiles (legend "water": true, with "branch" and "part"): Fontaine's river, a water slab on each tile that
        Global.lua lowers out of sight when its stretch drains.
  zone (capture zone tiles): a frame around each square group of them (2x2), which takes the colour of the player
        with more Pokemon inside (Global.lua). A zone raised above every tile round it, with sloping edges, gets
        the frame drawn in on its flat top (Yaksha's centre).
  bridge tiles (legend "bridge": true, sky with no board): each run of them between two islands is one rope
        bridge, 1 or 2 tiles long, carrying its own snap points; it starts dropped (closed) and the arrows on it
        raise or drop all the bridges (Global.lua).
  grass bridge tiles (legend "bridge": "grass", Greenleaf's creek: 2 lines of 5 tiles between two walls): one grass
        bridge in two halves, a mat over each line, level with the land at its ends. Each half grows out of the wall
        beside its line (sx, sz: the move from open into that wall); it starts closed, inside its wall. Both halves
        share a "group"; the first ("lead") carries the arrows, on top of its wall ("hy": the wall's top above the
        mat's), which open or close it (Global.lua, the rope bridges' rules).
  flower-<name> (Greenleaf): a flat bloom (Flower) carrying the tile's snap point; its spots are the tiles marked
        landing-<name>1, 2, 3 (painted), passed on as "targets": "dx,dy,dz;..." from the flower's tile top to each
        spot's. Its button throws the Pokemon on it to one of them at random (Global.lua).
Models come from tools/build_pieces.py. Global.lua's spawnArenaPiece spawns them, as the map picker does. TTS only
keeps the result in memory: save the game afterwards.
"""
import json, math, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_board import Arena, expand_regions  # noqa: E402
from build_pieces import BELL_LIFT, DOOR_H, GRASS_TILES, gear_file  # noqa: E402  (the stand's beam is built for the bell at this height)
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
RAISED_SLANTS = {0.8: "raised", 0.559: "raised60", 0.352: "raised70"}   # tools/build_pieces.py: a raised zone's slope -> its frames
RAISED_ZONES = {s: {n: {**ZONES[n], "mesh": f"props/zoneframe{n}-{name}-v1.obj", "collider": f"props/zoneframe{n}-{name}-v1.obj"}
                    for n in (2, 4)} for s, name in RAISED_SLANTS.items()}
TREE = {"mesh": "props/tree-v1.obj", "diffuse": "props/tree-v1.jpg", "collider": "props/tree-collider-v1.obj",
        "convex": True, "material": 1}
GIFT = {"mesh": "props/gift-v1.obj", "diffuse": "props/gift-v1.jpg", "collider": "props/gift-v1.obj",
        "convex": True, "material": 3}
GATE_FRAME = {"mesh": "props/gateframe-v1.obj", "diffuse": "props/gate-v1.jpg", "collider": "props/gateframe-v1.obj",
              "convex": False, "material": 1}
GATE = {"mesh": "props/gate-v1.obj", "diffuse": "props/gate-v1.jpg", "collider": "props/gate-v1.obj",
        "convex": True, "material": 1}
WATER = {"mesh": "props/water-v1.obj", "diffuse": "props/water-v1.jpg", "collider": "props/water-v1.obj",
         "convex": True, "material": 3}   # matte: shiny water mirrors the sky white at low angles
FOUNTAIN = {"mesh": "props/fountain-v1.obj", "diffuse": "props/fountain-v1.jpg", "collider": "props/fountain-v1.obj",
            "convex": False, "material": 0}
STATUE = {"mesh": "props/statue-v1.obj", "diffuse": "props/statue-v1.jpg", "collider": "props/statue-collider-v1.obj",
          "convex": True, "material": 3}   # matte stone
GEAR_PLATES = {n: {"mesh": f"props/gear{n}-v1.obj", "collider": f"props/gear{n}-v1.obj", "convex": True, "material": 3}
               for n in (3, 4)}
DOOR = {"mesh": "props/door-v1.obj", "collider": "props/door-v1.obj", "convex": True, "material": 3}
FLOWER = {"mesh": "props/flower-v1.obj", "collider": "props/flower-v1.obj", "convex": True, "material": 3}
GRASS_BRIDGE = {"mesh": "props/grassbridge-v2.obj", "diffuse": "props/grassbridge-v2.jpg",
                "collider": "props/grassbridge-collider-v2.obj", "convex": True, "material": 3}
WATER_DEPTH = 0.62   # Fontaine: the water's surface above the river bed (the canal walls are 0.968 high)
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
        top = info["floor0"] + tile.get("level", 0) * info["level_height"] - tile.get("sink", 0.0) + tile.get("lift", 0.0)
        cx = sum((c + 0.5 - C / 2) * T for _, c in group) / len(group)
        cz = sum((R / 2 - r - 0.5) * T for r, _ in group) / len(group)
        # raised above every tile round it, with sloping edges: the frame that sits inside the slopes
        around = [(r + dr, c + dc) for r, c in group for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                  if (r + dr, c + dc) not in cells]
        lower = [n for n in around if (level_at(data, *n) or -1) < tile.get("level", 0)]
        raised = tile.get("slant") and len(lower) == len(around)
        if raised and tile["slant"] not in RAISED_SLANTS:
            sys.exit(f"capture zone {sorted(group)}: raised zone frames exist for slants {list(RAISED_SLANTS)} only")
        out.append((size, (cx, top, cz), tile["slant"] if raised else None))
    return out


def level_at(data, r, c):
    """A grid tile's level, or None outside the grid or on void."""
    if 0 <= r < len(data["grid"]) and 0 <= c < len(data["grid"][0]):
        t = data["legend"][data["grid"][r][c]]
        return None if t.get("void") else t.get("level", 0)
    return None


def bridges(data, grid, info):
    """One entry per block of bridge tiles: [(kind, rows, cols, top, along_x)]. A rope bridge (legend "bridge": true)
    is a run of 1 or 2 tiles along a row or a column with an island tile at each end (a single tile: islands on two
    opposite sides). A grass bridge ("bridge": "grass") is a block of tiles with land at both ends of each of its
    lines. top: the land's height at its ends (the deck is level with it)."""
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
        kind = data["legend"][data["grid"][r0][c0]]["bridge"]
        if len(rows) == 1 and len(cols) == 1:
            along_x = bool(grid.tile(r0, c0 - 1) and grid.tile(r0, c0 + 1))
        else:
            along_x = len(cols) >= len(rows)
        if along_x:
            ends = [(r, cols[0] - 1) for r in rows] + [(r, cols[-1] + 1) for r in rows]
        else:
            ends = [(rows[0] - 1, c) for c in cols] + [(rows[-1] + 1, c) for c in cols]
        lands = [grid.tile(*e) for e in ends]
        n_along, n_across = (len(cols), len(rows)) if along_x else (len(rows), len(cols))
        if kind is True and (len(run) != len(rows) * len(cols) or n_across != 1 or not all(lands) or n_along not in BRIDGES):
            sys.exit(f"bridge tiles {sorted(run)}: a bridge must be 1 or 2 tiles in a line with an island at each end")
        if kind is not True and (len(run) != len(rows) * len(cols) or not all(lands) or any(t.get("bridge") for t in lands)):
            sys.exit(f"bridge tiles {sorted(run)}: a grass bridge must be a block of tiles with land at both ends of each line")
        out.append((kind, rows, cols, info["floor0"] + lands[0].get("level", 0) * info["level_height"], along_x))
    return out


def grass_halves(data, grid, info, rows, cols, top, group):
    """A grass bridge's two halves (pieces): a mat over each of its two lines, growing out of the wall along that
    line's outer side (each half's back, its own +z, faces its wall: the second half is turned round)."""
    R, C, T, lh = info["rows"], info["cols"], info["tile"], info["level_height"]
    if len(rows) != 2 or len(cols) != GRASS_TILES:
        sys.exit(f"grass bridge {rows}x{cols}: it must be 2 lines of {GRASS_TILES} tiles, running along a row")
    out = []
    for i, r in enumerate(rows):
        wall_r = r - 1 if i == 0 else r + 1
        walls = [grid.tile(wall_r, c) for c in cols]
        land_level = round((top - info["floor0"]) / lh)
        if not all(w and w.get("solid") and w.get("level", 0) > land_level for w in walls):
            sys.exit(f"grass bridge line {r}: it needs a wall along its whole outer side (row {wall_r}) to grow out of")
        out.append({"kind": "Bridge", "name": "Grass bridge", "model": GRASS_BRIDGE,
                    "pos": [sum((c + 0.5 - C / 2) * T for c in cols) / len(cols), top, (R / 2 - r - 0.5) * T],
                    "yaw": 0 if i == 0 else 180, "desc": "", "tiles": len(cols), "tile": round(T, 5),
                    "sx": 0.0, "sz": round(T if i == 0 else -T, 5), "group": group, "lead": i == 0,
                    "hy": round((min(w["level"] for w in walls) - land_level) * lh, 5)})
    return out


def flower_targets(data, info, name, r, c):
    """A flower's spots (tiles marked landing-<name>1, 2, ...) in number order, as "dx,dy,dz;..." from the flower's
    tile top to each spot's tile top (world units)."""
    T, lh = info["tile"], info["level_height"]
    me = data["legend"][data["grid"][r][c]]
    spots = {}
    for rr, row in enumerate(data["grid"]):
        for cc, ch in enumerate(row):
            m = data["legend"][ch].get("marker", "")
            if m.startswith(f"landing-{name}") and m[len(f"landing-{name}"):].isdigit():
                t = data["legend"][ch]
                dy = (t.get("level", 0) - me.get("level", 0)) * lh - t.get("sink", 0.0) + me.get("sink", 0.0)
                spots[int(m[len(f"landing-{name}"):])] = (round((cc - c) * T, 4), round(dy, 4), round((r - rr) * T, 4))
    if sorted(spots) != list(range(1, len(spots) + 1)) or not spots:
        sys.exit(f"flower-{name} at ({r}, {c}): its spots must be landing-{name}1, 2, ... (found {sorted(spots)})")
    return ";".join(",".join(f"{v:g}" for v in spots[k]) for k in sorted(spots))


def board_json(arena, name=None):
    if name:
        return arena / name
    boards = sorted(arena.glob("board-v*.json"), key=lambda p: int(re.search(r"v(\d+)", p.name).group(1)))
    return boards[-1]


def blocker_opening(data, r, c, T):
    """Where a blocker goes when it opens, as a world offset (x, y, z): into a wall beside it (preferring the one
    straight across from another blocker of its set, so a doorway's two halves part to its two sides), else down
    into the floor."""
    grid, legend = data["grid"], data["legend"]
    me = legend[grid[r][c]]

    def at(rr, cc):
        return legend[grid[rr][cc]] if 0 <= rr < len(grid) and 0 <= cc < len(grid[0]) else None
    walls, mates = [], []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        t = at(r + dr, c + dc)
        if t and t.get("solid") and t.get("level", 0) > me.get("level", 0):
            walls.append((dr, dc))
        if t and t.get("marker") == me.get("marker"):
            mates.append((dr, dc))
    pick = next((w for w in walls if (-w[0], -w[1]) in mates), walls[0] if walls else None)
    if pick:
        return (round(pick[1] * T, 5), 0.0, round(-pick[0] * T, 5))
    return (0.0, round(-(DOOR_H + 0.03), 5), 0.0)


def pieces(arena, info):
    data = expand_regions(json.loads((arena / "map.json").read_text(encoding="utf-8")))
    grid = Arena(arena)
    R, C, T = info["rows"], info["cols"], info["tile"]
    out = []
    for r, row in enumerate(data["grid"]):
        for c, ch in enumerate(row):
            tile = data["legend"].get(ch, {})
            marker = tile.get("marker", "")
            cx, cz = (c + 0.5 - C / 2) * T, (R / 2 - r - 0.5) * T
            if not tile.get("void") and tile.get("water"):   # Fontaine's river: a water tile, in its gate's stretch
                bed = info["floor0"] + tile["level"] * info["level_height"] - tile.get("sink", 0.0)
                out.append({"kind": "Water", "name": "River water", "model": WATER, "pos": [cx, bed + WATER_DEPTH, cz],
                            "yaw": 0, "desc": "", "branch": tile["branch"], "part": tile["part"]})
            if tile.get("void") or not tile.get("piece") or not (
                    marker in BELLS or marker in ("flag", "portal", "trap", "tree", "gift", "gate", "fountain", "statue")
                    or marker.startswith("blocker") or marker.startswith("flower-")):
                continue
            top = info["floor0"] + tile["level"] * info["level_height"] - tile.get("sink", 0.0)
            if marker == "gate":   # its frame of posts, and the sluice block (Global.lua lowers it: gates start open)
                fields = {"gate": tile["gate"], "branch": tile["branch"], "part": tile["part"]}
                out.append({"kind": "GateFrame", "name": f"Water gate {tile['gate']}", "model": GATE_FRAME,
                            "pos": [cx, top, cz], "yaw": 0, "desc": "", **fields})
                out.append({"kind": "Gate", "name": f"Water gate {tile['gate']}", "model": GATE,
                            "pos": [cx, top, cz], "yaw": 0, "desc": "", **fields})
            elif marker == "fountain":
                out.append({"kind": "Fountain", "name": "Fountain", "model": FOUNTAIN, "pos": [cx, top, cz], "yaw": 0,
                            "desc": "Fountain. A Pokémon that ends its turn next to it takes 1/16 of its HP in water damage."})
            elif marker.startswith("blocker"):   # starts closed, filling the tile
                n = int(marker[len("blocker"):])
                sx, sy, sz = blocker_opening(data, r, c, T)
                out.append({"kind": "Door", "name": f"Blocker {n}", "model": {**DOOR, "diffuse": f"props/door-{n}-v1.jpg"},
                            "pos": [cx, top, cz], "yaw": 0, "desc": "", "door": n, "sx": sx, "sy": sy, "sz": sz})
            elif marker.startswith("flower-"):   # a flat bloom carrying the tile's snap point; its spots go along
                name = marker[len("flower-"):]
                out.append({"kind": "Flower", "name": f"{name.capitalize()} flower",
                            "model": {**FLOWER, "diffuse": f"props/flower-{name}-v1.jpg"}, "pos": [cx, top, cz], "yaw": 0,
                            "desc": "", "targets": flower_targets(data, info, name, r, c), "tile": round(T, 5)})
            elif marker == "statue":
                out.append({"kind": "Statue", "name": "Statue", "model": STATUE, "pos": [cx, top, cz], "yaw": 0,
                            "desc": "", "free": True})
            elif marker in ("tree", "gift"):
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
    for g in data.get("gears", []):
        (r0, c0), n, num = g["at"], g["size"], g.get("number", 0)
        tile = data["legend"][data["grid"][r0][c0]]
        top = info["floor0"] + tile.get("level", 0) * info["level_height"]
        diffuse = "props/" + gear_file(n, g["turn"], num)
        if not (REPO / diffuse).exists():
            sys.exit(f"gear {g}: no {diffuse} (add the kind to GEAR_KINDS in tools/build_pieces.py)")
        out.append({"kind": "Gear", "name": f"Gear {num}" if num else "Gear", "model": {**GEAR_PLATES[n], "diffuse": diffuse},
                    "pos": [(c0 + n / 2 - C / 2) * T, top, (R / 2 - r0 - n / 2) * T], "yaw": 0, "desc": "",
                    "gear": num, "size": n, "turn": g["turn"], "tile": round(T, 5)})
    for size, pos, slant in zones(data, info):
        out.append({"kind": "Zone", "name": "Capture zone", "model": (RAISED_ZONES[slant] if slant else ZONES)[size], "pos": list(pos), "yaw": 0,
                    "desc": "", "tiles": size, "tile": round(T, 5)})
    groups = 0
    for kind, rows, cols, top, along_x in bridges(data, grid, info):
        if kind is True:
            run = [(r, c) for r in rows for c in cols]
            cx = sum((c + 0.5 - C / 2) * T for _, c in run) / len(run)
            cz = sum((R / 2 - r - 0.5) * T for r, _ in run) / len(run)
            out.append({"kind": "Bridge", "name": "Rope bridge", "model": BRIDGES[len(run)], "pos": [cx, top, cz],
                        "yaw": 0 if along_x else 90, "desc": "", "tiles": len(run), "tile": round(T, 5)})
        else:
            groups += 1
            out += grass_halves(data, grid, info, rows, cols, top, groups)
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
