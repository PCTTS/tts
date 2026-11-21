"""Put an arena's pieces (bells, flags) on its marker tiles in the open TTS game.

Usage:  python -I tools/place_pieces.py arenas/<name> [--board board-vN.json] [--local [folder]]
--local loads the models from this repo (or from a folder holding a copy of props/) instead of the PCTTS site: a
preview only this computer can see. Run again without it, after publishing, before saving the game. TTS keeps a
model it has loaded for as long as it runs, so preview a changed model from a fresh folder.
Reads the arena's map.json (markers) and its board geometry JSON (tile size, level heights; default: the
highest-numbered board-v*.json), finds the locked board named after the arena, removes the pieces placed
before (tag "ArenaPiece") and spawns new ones, locked, relative to the board:
  bell-attack / bell-defense: a bronze bell floating over the middle of the tile ("ATK bell" / "DEF bell").
  flag: a flag in the tile's corner farthest from the board's centre, its cloth flying outward, so a Pokemon
        can stand on the tile. Starts neutral; right-click > Capture tints it to the player's colour (Global.lua).
Models come from tools/build_pieces.py. TTS only keeps the result in memory: save the game afterwards.
"""
import json, math, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tts import exec_lua, report  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
BASE_URL = "https://pctts.github.io/tts/"
BELL_LIFT = 0.9          # gap between the tile top and the bell's lip
FLAG_INSET = 0.38        # the pole's distance from the two tile edges of its corner
BELL = {"mesh": "props/bell-v3.obj", "diffuse": "props/bell-v3.jpg", "collider": "props/bell-collider-v3.obj",
        "convex": True, "material": 2}
FLAG = {"mesh": "props/flag-v1.obj", "diffuse": "props/flag-v1.jpg", "collider": "props/flag-collider-v1.obj",
        "convex": False, "material": 3}
BELLS = {"bell-attack": ("ATK bell", "attack"), "bell-defense": ("DEF bell", "defense")}


def board_json(arena, name=None):
    if name:
        return arena / name
    boards = sorted(arena.glob("board-v*.json"), key=lambda p: int(re.search(r"v(\d+)", p.name).group(1)))
    return boards[-1]


def pieces(arena, info):
    data = json.loads((arena / "map.json").read_text(encoding="utf-8"))
    R, C, T = info["rows"], info["cols"], info["tile"]
    out = []
    for r, row in enumerate(data["grid"]):
        for c, ch in enumerate(row):
            tile = data["legend"].get(ch, {})
            marker = tile.get("marker", "")
            if tile.get("void") or not (marker in BELLS or marker == "flag"):
                continue
            cx, cz = (c + 0.5 - C / 2) * T, (R / 2 - r - 0.5) * T
            top = info["floor0"] + tile["level"] * info["level_height"]
            if marker in BELLS:
                name, stat = BELLS[marker]
                out.append({"kind": "Bell", "name": name, "model": BELL, "pos": [cx, top + BELL_LIFT, cz], "yaw": 0,
                            "desc": f"Attack this bell to give all your Pokemon the {stat} bonus until the end of the turn. "
                                    "Each bell can only be rung once per turn."})
            else:
                sx, sz = (1 if cx >= 0 else -1), (1 if cz >= 0 else -1)
                pos = [cx + sx * (T / 2 - FLAG_INSET), top, cz + sz * (T / 2 - FLAG_INSET)]
                yaw = math.degrees(math.atan2(-sz, sx))      # TTS yaw that turns the model's +x toward (sx, sz)
                out.append({"kind": "Flag", "name": "Flag", "model": FLAG, "pos": pos, "yaw": yaw % 360, "desc": ""})
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
local yaw = board.getRotation().y
for _, p in ipairs(list) do
  local m = p.model
  local data = {
    Name = "Custom_Model", Nickname = p.name, Description = p.desc, Tags = { p.kind, "ArenaPiece" },
    Locked = true, ColorDiffuse = { r = 1, g = 1, b = 1 }, Memo = "",
    Transform = { posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = 1, scaleY = 1, scaleZ = 1 },
    CustomMesh = { MeshURL = %(base)s .. m.mesh, DiffuseURL = %(base)s .. m.diffuse, NormalURL = "",
      ColliderURL = %(base)s .. m.collider, Convex = m.convex, MaterialIndex = m.material, TypeIndex = 0,
      CastShadows = true },
  }
  if p.kind == "Flag" then   -- neutral; Global's onObjectSpawn gives it the Capture menu
    data.ColorDiffuse, data.Description = FLAG_NEUTRAL, flagDescription(nil)
  end
  spawnObjectData({ data = data, position = board.positionToWorld(Vector(p.pos[1], p.pos[2], p.pos[3])),
    rotation = { 0, yaw + p.yaw, 0 } })
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
