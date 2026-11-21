"""Write arenas/index.json: every arena the map picker in TTS can put on the table.

Usage:  python -I tools/build_arena_index.py
For each arenas/<folder>/map.json with a "board" entry ({"mesh", "texture", "geometry"}: the published board
files, from tools/build_board.py), the index has the arena's board files, its table image, a snap point over
every tile except "solid" ones (walls) (at the tile's top, position only: players set a Pokemon's facing themselves) and its 3D pieces
(legend entries with "piece": true, placed as tools/place_pieces.py does). Positions are in the board's frame
(the board sits on the table with no rotation). Global.lua downloads the index when the game loads.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from place_pieces import pieces  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SNAP_LIFT = 0.02   # snap points float this far above the tile tops


def arena_entry(folder):
    data = json.loads((folder / "map.json").read_text(encoding="utf-8"))
    board = data["board"]
    info = json.loads((folder / board["geometry"]).read_text(encoding="utf-8"))
    rel = folder.relative_to(REPO).as_posix()
    R, C, T = info["rows"], info["cols"], info["tile"]
    snaps = []
    for r, row in enumerate(data["grid"]):
        for c, ch in enumerate(row):
            tile = data["legend"][ch]
            if tile.get("void") or tile.get("solid"):   # nothing stands on solid tiles (walls)
                continue
            top = info["floor0"] + tile.get("level", 0) * info["level_height"] - tile.get("sink", 0.0) + SNAP_LIFT
            snaps.append([round((c + 0.5 - C / 2) * T, 4), round(top, 4), round((R / 2 - r - 0.5) * T, 4)])
    name, items = pieces(folder, info)
    out_pieces = [{**{k: v for k, v in p.items() if k != "model"}, "yaw": round(p["yaw"], 2),
                   "pos": [round(v, 4) for v in p["pos"]], **p["model"]} for p in items]   # (+ pair, tiles, tile)
    return name, {"mesh": f"{rel}/{board['mesh']}", "texture": f"{rel}/{board['texture']}",
                  "table": data.get("table", ""), "snaps": snaps, "pieces": out_pieces}


def main():
    index = {}
    for folder in sorted(p.parent for p in (REPO / "arenas").glob("*/map.json")):
        if "board" in json.loads((folder / "map.json").read_text(encoding="utf-8")):
            name, entry = arena_entry(folder)
            index[name] = entry
            print(f"{name}: {entry['mesh']}, {entry['texture']}, {len(entry['snaps'])} snap points, {len(entry['pieces'])} pieces")
    (REPO / "arenas" / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"wrote arenas/index.json ({len(index)} arenas)")


if __name__ == "__main__":
    main()
