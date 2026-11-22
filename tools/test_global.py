"""Offline checks for lua/Global.lua: runs it in real Lua (via lupa) with stand-ins for the TTS API.

Usage:  python -I tools/test_global.py
Checks: the script compiles; onLoad builds well-formed UI XML with unique ids; search finds the right names;
the search panel's result rows get text; spawning creates a figure (or a card in the player's hand) with the
right images; the map picker lists the arenas and puts a board with its flags on the table; statuses arm, stack, replace and clear; the
toolbar's frame, status colour squares and full card lists (who sees them, picking from them); a flag gets its
Capture menu and takes the capturing player's colour. (TTS's own Lua, MoonSharp, has quirks real Lua doesn't — still test in TTS.)
"""
import json, re, sys, xml.etree.ElementTree as ET
from pathlib import Path

import lupa
from lupa import LuaRuntime

REPO = Path(__file__).resolve().parent.parent

PRELUDE = r"""
Vector = setmetatable({}, { __call = function(_, x, y, z) return Vector.new(x, y, z) end })
local VM = {}
VM.__index = VM
VM.__add = function(a, b) return Vector.new(a.x + b.x, a.y + b.y, a.z + b.z) end
VM.__sub = function(a, b) return Vector.new(a.x - b.x, a.y - b.y, a.z - b.z) end
VM.__mul = function(a, k) return Vector.new(a.x * k, a.y * k, a.z * k) end
function Vector.new(x, y, z) return setmetatable({ x = x, y = y, z = z }, VM) end
function VM:normalized()
  local m = math.sqrt(self.x ^ 2 + self.y ^ 2 + self.z ^ 2)
  return Vector.new(self.x / m, self.y / m, self.z / m)
end

calls = { attrs = {}, values = {}, spawned = {}, printed = {} }
UI = {
  setCustomAssets = function(a) calls.assets = a end,
  setXml = function(x) calls.xml = x end,
  setAttribute = function(id, k, v) calls.attrs[id .. "." .. k] = v end,
  getAttribute = function(id, k) return calls.attrs[id .. "." .. k] end,
  setValue = function(id, v) calls.values[id] = v end,
}
WebRequest = { get = function(url, cb)
  local text = ROSTER_JSON
  if url:find("cards/", 1, true) then text = CARDS_JSON elseif url:find("data/pokemon", 1, true) then text = STATS_JSON
  elseif url:find("arenas/index", 1, true) then text = ARENAS_JSON end
  cb({ is_error = false, text = text })
end }
JSON = { decode = function(s) return py_json_decode(s) end, encode = function(t) return py_json_encode(t) end }
function print(s) calls.printed[#calls.printed + 1] = s end
function printToAll(s) calls.printed[#calls.printed + 1] = s end
Wait = { frames = function(f) f() end, time = function(f) f() end }
Player = setmetatable({}, { __index = function(_, c)
  return { color = c, steam_name = c .. "Player", broadcast = function(msg) calls.broadcast = msg end,
    getHandObjects = function() return (handHeld or {})[c] or {} end }
end })
rawset(Player, "Action", { Copy = 0, Cut = 1, Delete = 2, PickUp = 8 })
Color = { fromString = function(c)
  return ({ Red = { r = 0.856, g = 0.1, b = 0.094 }, Blue = { r = 0.118, g = 0.53, b = 1 } })[c] or { r = 1, g = 1, b = 1 }
end }
objects = {}
local function stub(o)
  o.hasTag = o.hasTag or function(tag) for _, t in ipairs(o.tags or {}) do if t == tag then return true end end return false end
  o.getLock = o.getLock or function() return o.locked or false end
  o.getStates = o.getStates or function() return nil end            -- every real TTS object has these
  o.getCustomObject = o.getCustomObject or function() return {} end
  o.getRotation = o.getRotation or function() return Vector(0, 0, 0) end
  o.getScale = o.getScale or function() return o.scale or Vector(1, 1, 1) end
  o.setScale = o.setScale or function(v) o.scale = Vector(v[1], v[2], v[3]) end
  o.destruct = o.destruct or function() o.destroyed = true end
  o.clearContextMenu = o.clearContextMenu or function() end
  o.addContextMenuItem = o.addContextMenuItem or function() end
  o.UI = o.UI or { setXml = function() end, setAttribute = function() end }
  objects[#objects + 1] = o
  return o
end
-- team stands: near (south) at z = -26.4 facing the near player, far (north) turned 180 degrees
local function makeStand(z, yaw)
  local s = { tags = { "Stand" }, type = "Generic", locked = true, snaps = {} }
  s.getSnapPoints = function() return s.snaps end
  s.setSnapPoints = function(p) s.snaps = p end
  s.getCustomObject = function() return { mesh = "https://pctts.github.io/tts/props/stand-v4.obj" } end
  s.setCustomObject = function(c) s.newMesh = c.mesh end
  s.reload = function() s.reloaded = true end
  s.UI = { setXml = function(x) s.uiXml = x end, getXml = function() return s.uiXml or "" end }
  s.getPosition = function() return Vector(0, 0.961, z) end
  s.getRotation = function() return Vector(0, yaw, 0) end
  s.positionToWorld = function(v)
    if yaw == 0 then return Vector(v.x, 0.961 + v.y, z + v.z) end
    return Vector(-v.x, 0.961 + v.y, z - v.z)
  end
  s.positionToLocal = function(v)
    if yaw == 0 then return Vector(v.x, v.y - 0.961, v.z - z) end
    return Vector(-v.x, v.y - 0.961, z - v.z)
  end
  return stub(s)
end
southStand, northStand = makeStand(-26.4, 0), makeStand(26.4, 180)
function spawnObjectData(t)
  calls.spawned[#calls.spawned + 1] = t
  local kind = t.data.Name == "CardCustom" and "Card" or ((t.data.Name == "Figurine_Custom" or (t.data.CustomMesh and t.data.CustomMesh.TypeIndex == 1)) and "Figurine" or "Generic")
  local cm = t.data.CustomMesh
  return stub({ tags = t.data.Tags, type = kind, getName = function() return t.data.Nickname end,
    getPosition = function() return t.position end,
    getCustomObject = function() return cm and { mesh = cm.MeshURL, diffuse = cm.DiffuseURL } or {} end })
end

-- the 3D board on the table (Pugilis)
board = { type = "Generic", locked = true, tags = { "Board3D" }, getName = function() return "Pugilis" end,
  getPosition = function() return Vector(0.01, 0.961, -0.01) end }
stub(board)
Tables = { getCustomURL = function() return calls.tableURL or "https://example.com/old-table.jpg" end,
  setCustomURL = function(u) calls.tableURL = u end }
function getAllObjects()
  local live = {}
  for _, o in ipairs(objects) do if not o.destroyed then live[#live + 1] = o end end
  return live
end
"""


def main():
    lua = LuaRuntime(unpack_returned_tuples=True)

    def to_lua(v):
        if isinstance(v, dict):
            return lua.table_from({k: to_lua(x) for k, x in v.items()})
        if isinstance(v, list):
            return lua.table_from([to_lua(x) for x in v])
        return v

    def from_lua(v):
        if lupa.lua_type(v) == "table":
            keys = list(v.keys())
            if keys and all(isinstance(k, int) for k in keys) and sorted(keys) == list(range(1, len(keys) + 1)):
                return [from_lua(v[k]) for k in sorted(keys)]
            return {str(k): from_lua(v[k]) for k in keys}
        return v

    g = lua.globals()
    g.py_json_decode = lambda s: to_lua(json.loads(s)) if s else None
    g.py_json_encode = lambda t: json.dumps(from_lua(t))
    g.ROSTER_JSON = (REPO / "figures" / "index.txt").read_text(encoding="utf-8")
    g.CARDS_JSON = (REPO / "cards" / "index.txt").read_text(encoding="utf-8")
    g.STATS_JSON = (REPO / "data" / "pokemon.txt").read_text(encoding="utf-8")
    g.ARENAS_JSON = (REPO / "arenas" / "index.txt").read_text(encoding="utf-8")
    lua.execute(PRELUDE)

    src = (REPO / "lua" / "Global.lua").read_text(encoding="utf-8")
    # TTS runs Lua 5.2 (MoonSharp); lupa runs 5.5, which also accepts newer syntax. Flag 5.3+ operators.
    code = re.sub(r"--\[(=*)\[.*?\]\1\]|\[(=*)\[.*?\]\2\]", "", src, flags=re.S)   # long comments/strings
    code = re.sub(r"--[^\n]*|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'", "", code)  # comments, strings
    newer = [op for op in ("//", "<<", ">>", " & ", " | ", " ~ ") if op in code]
    assert not newer, f"Lua 5.3+ operators TTS can't run: {newer}"
    res = g.load(src, "Global.lua")  # a function, or (nil, error message)
    fn = res[0] if isinstance(res, tuple) else res
    assert fn, f"syntax error: {res[1]}"
    fn()
    g.onLoad("")
    calls = g.calls
    failures = []

    def check(ok, what):
        print(("ok    " if ok else "FAIL  ") + what)
        if not ok:
            failures.append(what)

    def backdrop(spawned, image):
        """The arena's surroundings went onto one locked backdrop panel showing `image`, and only one is on the table."""
        bd = [x for x in spawned if x.data.Tags and x.data.Tags[1] == "ArenaBackdrop"]
        live = [o for o in g.getAllObjects().values() if o.hasTag("ArenaBackdrop")]
        return (len(bd) == 1 and bd[0].data.Locked and bd[0].data.CustomMesh.DiffuseURL.endswith(image)
                and bd[0].data.CustomMesh.MeshURL.endswith("props/backdrop-v1.obj") and len(live) == 1)

    # UI: well-formed XML, unique ids, icons registered
    xml = calls.xml
    try:
        root = ET.fromstring("<root>" + xml + "</root>")
        ids = [e.get("id") for e in root.iter() if e.get("id")]
        check(len(ids) == len(set(ids)), f"UI XML parses; {len(ids)} ids, all unique")
        bar = next(e for e in root.iter() if e.get("id") == "toolbar")
        check((bar.get("width"), bar.get("height")) == ("38", "228"), f"toolbar is 38 x 228, six icons ({bar.get('width')} x {bar.get('height')})")
        hud = next(e for e in root.iter() if e.get("id") == "hud")
        check(hud.get("rectAlignment") == "UpperRight" and hud.get("height") == "66.667%" and bar in list(hud),
              "the toolbar sits in a frame over the top two-thirds of the screen (so a third of the way down)")
        dock = next(e for e in root.iter() if e.get("id") == "dock")
        panels = [e for e in dock if (e.get("id") or "").endswith("_White")]
        check(len(panels) == 6 and all(e.get("rectAlignment") == "UpperRight" and not e.get("pivot") for e in panels)
              and dock.get("height") == "228" and dock in list(hud),
              "White's six panels hang from the top of a dock the toolbar's height (so their top stays put)")
        lists = {k: next(e for e in root.iter() if e.get("id") == k + "List") for k in ("items", "skills")}
        counts = {k: len([b for b in v.iter("Button")]) for k, v in lists.items()}
        check(counts == {"items": 246, "skills": 67}, f"scrolling lists hold every item and warrior skill ({counts})")
        body = next(e for e in root.iter() if e.get("id") == "skillsListBody")
        cover = next((e for e in root.iter() if e.get("id") == "skillsListCover"), None)
        check(cover is not None and cover.get("height") == "20", "each list has a cover strip over its sideways scrollbar")
        check((body.get("height"), body.get("padding")) == (str(67 * 32 - 4), "0 20 0 0"),
              f"a list's body is as tall as its rows, with room for the scrollbar ({body.get('height')}, {body.get('padding')})")
        sw = next(e for e in root.iter() if e.get("id") == "statusSwatch_White_burn")
        check(sw.get("color") == "#FF4421", "each status row has a full-colour square in its type's colour (Burned: Fire #FF4421)")
    except ET.ParseError as e:
        check(False, f"UI XML parses ({e})")
    check(len(list(calls.assets.values())) == 6, "six toolbar icons registered")
    check(len(g.catalog.dex.list) == 704, "roster downloaded (704 names)")
    check(len(g.catalog["items"].list) == 246 and len(g.catalog.skills.list) == 67,
          "cards downloaded (246 items, 67 warrior skills)")
    check('class="hint"' not in xml and "Msg_" not in xml, "the panels have no hint lines")
    maps_panel = xml[xml.index('id="maps_White"'):xml.index('</VerticalLayout>', xml.index('id="maps_White"'))]
    check('onClick="closePanel"' not in maps_panel and 'onClick="closePanel"' in xml, "the map panel has no X (the others keep theirs)")
    check(g.onChat is None, "no chat commands")

    # search
    names, _ = g.searchRoster("gard", 8)
    names = list(names.values())
    check(names[:2] == ["Gardevoir", "Gardevoir Mega"] and "Zygarde 10%" in names, f"'gard' -> {names}")
    names = list(g.searchRoster("mega z", 8)[0].values())
    check(set(names) == {"Absol Mega Z", "Garchomp Mega Z", "Lucario Mega Z"}, f"'mega z' -> {names}")

    # panel rows get text
    player = lua.table_from({"color": "White"})
    g.searchChanged(player, "char", "dexIn_White")
    check(calls.attrs["dexRes_White_1.text"] == "Charizard" and calls.attrs["dexRes_White_1.active"] == "true",
          "search panel row 1 shows 'Charizard'")
    check(calls.attrs["dexRes_White_8.active"] == "false", "unused rows hidden")

    # spawning
    g.searchPick(player, "-1", "dexRes_White_1")
    spawned = calls.spawned[1]
    check(spawned is not None and spawned.data.Nickname == "Charizard" and spawned.data.Name == "Custom_Model"
          and spawned.data.CustomMesh.MeshURL.endswith("models/standee-v1.obj")
          and spawned.data.CustomMesh.ColliderURL.endswith("models/standee-v1.obj")
          and spawned.data.CustomMesh.DiffuseURL.endswith("standees/v3/charizard.webp") and spawned.data.CustomMesh.TypeIndex == 1,
          "clicking row 1 spawns Charizard as a standee (art on an arrowed base)")
    memo = json.loads(spawned.data.Memo)
    want = json.loads((REPO / "data" / "pokemon.json").read_text(encoding="utf-8"))["Charizard"]["hp"]
    check(memo.get("hp") == want and memo.get("maxHp") == want, f"it starts at full HP ({memo})")
    check(memo.get("owner") == "White", "it belongs to White (who spawned it)")
    check(abs(spawned.position.x - (-17.625)) < 0.01 and abs(spawned.position.z - (-28.0)) < 0.01,
          f"White's Pokemon goes on the first pedestal of the near stand ({spawned.position.x:.2f}, {spawned.position.z:.2f})")

    # maps: the arenas from arenas/index.json; picking one puts its board, snap points and pieces on the table
    got = [(m.name, bool(m.current)) for m in g.mapList().values()]
    check(got == [("Chrysalia", False), ("Illusio", False), ("Ingis", False), ("Pugilis", True), ("Violight", False),
                  ("Viperia", False), ("Yaksha", False)],
          f"map list shows the seven arenas, Pugilis on the table ({got})")
    g.toolClick(player, "-1", "tool_maps")
    check(calls.attrs["maps_White.active"] == "true" and calls.attrs["dex_White.active"] == "false"
          and calls.attrs["mapRes_White_4.text"] == "Pugilis" and calls.attrs["mapRes_White_4.colors"].startswith("#8DB8F7"),
          "map button opens the map panel (and closes the search panel); the map on the table is highlighted, no label")
    n = len(calls.spawned)
    g.mapPick(player, "-1", "mapRes_White_4")
    check(len(calls.spawned) == n, "picking the arena that's already on the table does nothing")
    lua.execute("board.destroyed = true")
    g.refreshMaps("White")
    g.mapPick(player, "-1", "mapRes_White_4")
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    brd = new[0].data if new else None
    flags = [s for s in new[1:] if s.data.Tags[1] == "Flag"]
    check(brd is not None and brd.Nickname == "Pugilis" and brd.Tags[1] == "Board3D" and brd.Locked
          and brd.CustomMesh.MeshURL.endswith("arenas/pugilis/board-v29.obj") and brd.CustomMesh.ColliderURL == brd.CustomMesh.MeshURL
          and brd.CustomMesh.DiffuseURL.endswith("arenas/pugilis/board-v29.jpg") and not brd.CustomMesh.Convex,
          "picking Pugilis puts its 3D board on the table (its own mesh as collider)")
    check(len(flags) == 4 and backdrop(new, "misc/table-placeholder-v1.jpg") and calls.tableURL is None,
          "with its 4 flags and its surroundings on the backdrop panel (the table itself untouched)")

    # Illusio: floating islands with 6 flags, 6 portals in their starting colours, 6 bridges that start dropped
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", "mapRes_White_2")
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith("arenas/illusio/board-v6.obj")
          and kinds.count("Flag") == 6 and kinds.count("Portal") == 6 and kinds.count("Bridge") == 6
          and backdrop(new, "misc/sky-placeholder-v1.jpg"),
          "picking Illusio: its board, 6 flags, 6 portals, 6 bridges and the sky under the table")
    portals = [s for s in new if s.data.Tags[1] == "Portal"]
    pairs = sorted(json.loads(p.data.Memo)["pair"] for p in portals)
    tints = {json.loads(p.data.Memo)["pair"]: round(p.data.ColorDiffuse.g, 3) for p in portals}
    check(pairs == [1, 1, 2, 2, 3, 3] and len(set(tints.values())) == 3, "the portals start in three pairs, one colour each")
    br = [s for s in new if s.data.Tags[1] == "Bridge"]
    st = [json.loads(b.data.Memo) for b in br]
    check(all(not s["up"] and abs(b.position.y - (s["y"] - 1.6)) < 1e-6 and abs(s["y"] - (0.961 + 3.3147)) < 0.01
              for b, s in zip(br, st)) and sorted(s["tiles"] for s in st) == [1, 1, 2, 2, 2, 2],
          "the bridges (two 1-tile, four 2-tile) start dropped 1.6 below the islands")

    # Ingis: its board with the rock coordinates, three capture zone frames (neutral), the volcanic table
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", "mapRes_White_3")
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new]
    zones = [s for s in new if s.data.Tags[1] == "Zone"]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith("arenas/ingis/board-v5.obj")
          and len(zones) == 3 and len(kinds) == 5 and all(abs(z.data.ColorDiffuse.r - 0.6) < 1e-6 for z in zones)
          and backdrop(new, "misc/volcano-placeholder-v1.jpg"),
          "picking Ingis: its board, 3 neutral capture zone frames and the volcanic table")
    idx = json.loads((REPO / "arenas" / "index.json").read_text(encoding="utf-8"))["Ingis"]
    lava = [p for p in idx["snaps"] if abs(p[1] - (0.415 - 0.1 + 0.02)) < 0.01]
    high = [p for p in idx["snaps"] if abs(p[1] - (0.415 + 0.968 + 0.02)) < 0.01]
    check(len(idx["snaps"]) == 256 and len(lava) == 44 and len(high) == 52,
          f"a snap point on all 256 tiles: 52 on the ridge, 44 on the (slightly sunken) lava ({len(high)}, {len(lava)})")

    # Viperia: 16 x 15, its 3 flags, no snap points on the walls, the jungle table
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", "mapRes_White_6")
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new]
    vmap = json.loads((REPO / "arenas" / "viperia" / "map.json").read_text(encoding="utf-8"))
    walls = sum(row.count("#") for row in vmap["grid"])
    vidx = json.loads((REPO / "arenas" / "index.json").read_text(encoding="utf-8"))["Viperia"]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith("arenas/viperia/board-v1.obj")
          and kinds.count("Flag") == 3 and len(kinds) == 5 and len(vidx["snaps"]) == 16 * 15 - walls
          and backdrop(new, "misc/jungle-placeholder-v1.jpg"),
          f"picking Viperia: its board, 3 flags, snap points on all {16 * 15 - walls} tiles but the {walls} walls, the jungle table")

    # Violight: 4 capture zone frames round the spire, no snap points on the spire, the steel table
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", "mapRes_White_5")
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new]
    lidx = json.loads((REPO / "arenas" / "index.json").read_text(encoding="utf-8"))["Violight"]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith("arenas/violight/board-v1.obj")
          and kinds.count("Zone") == 4 and len(kinds) == 6 and len(lidx["snaps"]) == 256 - 4
          and backdrop(new, "misc/violight-placeholder-v1.jpg"),
          "picking Violight: its board, 4 zone frames, snap points on every tile but the 4 of the spire, the steel table")

    # Chrysalia: its board, 3 capture zone frames and 2 traps
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", "mapRes_White_1")
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith("arenas/chrysalia/board-v1.obj")
          and kinds.count("Zone") == 3 and kinds.count("Trap") == 2 and len(kinds) == 7   # + the backdrop
          and backdrop(new, "misc/mulch-placeholder-v2.jpg"),
          "picking Chrysalia: its board, 3 zone frames, 2 traps (no ball bag), the mulch table")
    lua.execute(r"""
      trapObj = { tags = { "Trap", "ArenaPiece" }, menu = {} }
      trapObj.hasTag = function(t) return t == "Trap" or t == "ArenaPiece" end
      trapObj.clearContextMenu = function() trapObj.menu = {} end
      trapObj.addContextMenuItem = function(label, fn) trapObj.menu[#trapObj.menu + 1] = { label = label, fn = fn } end
      trapObj.setDescription = function(d) trapObj.desc = d end
      trapObj.destruct = function() trapObj.gone = true end
      onObjectSpawn(trapObj)
    """)
    tr = g.trapObj
    np_ = len(list(calls.printed.values()))
    tr.menu[1].fn("Red")
    check(tr.menu[1].label == "Spring trap" and tr.gone and len(list(calls.printed.values())) == np_,
          "right-click > Spring trap removes the trap, without a chat message")

    # Yaksha: a big 4x4 capture zone and two 2x2 ones, 6 tree tiles and 14 gift boxes that players move (not locked)
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", "mapRes_White_7")
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new]
    zones = [s for s in new if s.data.Tags[1] == "Zone"]
    free =[s for s in new if s.data.Tags[1] in ("Tree", "Gift")]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith("arenas/yaksha/board-v4.obj")
          and len(zones) == 3 and sum(z.data.CustomMesh.MeshURL.endswith("zoneframe4-raised60-v1.obj") for z in zones) == 1
          and kinds.count("Tree") == 6 and kinds.count("Gift") == 14 and all(not s.data.Locked for s in free)
          and all(s.data.Locked for s in new if s.data.Tags[1] in ("Board3D", "Zone")),
          "picking Yaksha: its board, a 4x4 (raised: drawn in on its flat top) and two 2x2 zone frames, 6 trees and 14 gifts that players can move")

    # bridges: the arrows raise them all; dropping skips one with a Pokemon on it; right-click does just one
    lua.execute(r"""
      for _, o in ipairs(objects) do if o.hasTag("ArenaPiece") then o.destroyed = true end end   -- the stand-ins above
      testBridges = {}
      for i = 1, 3 do
        local b = { tags = { "Bridge", "ArenaPiece" }, guid = "br" .. i, menu = {}, snaps = {}, ui = {} }
        b.hasTag = function(t) return t == "Bridge" or t == "ArenaPiece" end
        b.memo = JSON.encode({ up = false, y = 4.276, tiles = (i == 1) and 1 or 2, tile = 3.24875 })
        b.pos = Vector(i * 10, 4.276 - 1.6, 0)
        b.getPosition = function() return b.pos end
        b.setPositionSmooth = function(p) b.pos = p end
        b.positionToLocal = function(v) return Vector(v.x - b.pos.x, v.y - b.pos.y, v.z - b.pos.z) end
        b.getSnapPoints = function() return b.snaps end
        b.setSnapPoints = function(s) b.snaps = s end
        b.setDescription = function(d) b.desc = d end
        b.clearContextMenu = function() b.menu = {} end
        b.addContextMenuItem = function(label, fn) b.menu[#b.menu + 1] = { label = label, fn = fn } end
        b.UI = { setXml = function(x) b.ui.xml = x end, setCustomAssets = function(a) b.ui.assets = a end }
        testBridges[i] = b
        objects[#objects + 1] = b
        onObjectSpawn(b)
      end
    """)
    tb = g.testBridges
    b2 = tb[2]
    check(len(list(b2.snaps.values())) == 2 and abs(b2.snaps[1].position[1] + 3.24875 / 2) < 1e-6 and not b2.snaps[1].rotation_snap
          and len(list(tb[1].snaps.values())) == 1, "a bridge gets a snap point on each of its tiles (position only)")
    check('onClick="Global/bridgeClicked"' in str(b2.ui.xml) and b2.ui.assets[1].url.endswith("ui/icons/updown-v3.png")
          and [b2.menu[i].label for i in (1, 2)] == ["Raise this bridge", "Drop this bridge"],
          "it gets the clear arrows button and the right-click menu")
    g.bridgeClicked(player)
    check(all(abs(b.pos.y - 4.276) < 1e-6 and json.loads(b.memo)["up"] for b in tb.values()),
          "clicking the arrows raises every bridge")
    lua.execute(r"""
      onBridge = { tags = { "Pokemon" }, memo = '{"pokemon":"Pikachu"}', getName = function() return "Pikachu" end }
      onBridge.hasTag = function(t) return t == "Pokemon" end
      onBridge.getPosition = function() return Vector(20 + 1.6, 4.276 + 0.1, 0.3) end
      objects[#objects + 1] = onBridge
    """)
    g.bridgeClicked(player)
    check(abs(tb[1].pos.y - (4.276 - 1.6)) < 1e-6 and abs(tb[2].pos.y - 4.276) < 1e-6 and abs(tb[3].pos.y - (4.276 - 1.6)) < 1e-6,
          "clicking again drops them, except the one Pikachu is standing on")
    g.bridgeClicked(player)
    check(all(json.loads(b.memo)["up"] for b in tb.values()), "the next click raises them all again")
    tb[3].menu[2].fn("Red")
    check(abs(tb[3].pos.y - (4.276 - 1.6)) < 1e-6 and abs(tb[1].pos.y - 4.276) < 1e-6, "right-click > Drop this bridge drops just that one")

    # portals: the die gives every portal a new partner at random (three pairs, each its own colour)
    lua.execute(r"""
      testPortals = {}
      for i = 1, 6 do
        local p = { tags = { "Portal", "ArenaPiece" }, guid = "pt" .. i, menu = {}, ui = {} }
        p.hasTag = function(t) return t == "Portal" or t == "ArenaPiece" end
        p.memo = JSON.encode({ pair = math.floor((i + 1) / 2) })
        p.setColorTint = function(c) p.tint = c end
        p.setDescription = function(d) p.desc = d end
        p.clearContextMenu = function() p.menu = {} end
        p.addContextMenuItem = function(label, fn) p.menu[#p.menu + 1] = { label = label, fn = fn } end
        p.UI = { setXml = function(x) p.ui.xml = x end, setCustomAssets = function(a) p.ui.assets = a end }
        testPortals[i] = p
        objects[#objects + 1] = p
        onObjectSpawn(p)
      end
    """)
    tp = g.testPortals
    check('onClick="Global/portalClicked"' in str(tp[1].ui.xml) and tp[1].ui.assets[1].url.endswith("ui/icons/die-v3.png")
          and "magenta portal" in str(tp[1].desc) and tp[1].menu[1].label == "Shuffle portals",
          "a portal gets its colour, the clear die button and a Shuffle menu")
    seen, ok = set(), True
    for _ in range(30):
        g.portalClicked(player)
        pr = [json.loads(p.memo)["pair"] for p in tp.values()]
        ok = ok and sorted(pr) == [1, 1, 2, 2, 3, 3] and all(
            (p.tint.r, p.tint.g, p.tint.b) == tuple(g.portalTint(json.loads(p.memo)["pair"])[k] for k in "rgb") for p in tp.values())
        seen.add(frozenset(frozenset(i for i, x in enumerate(pr) if x == k) for k in (1, 2, 3)))
    check(ok and len(seen) > 3,
          f"the die re-pairs all six at random: always three colour pairs ({len(seen)} different pairings in 30 shuffles)")

    # statuses: arm one, pick up a figure, check tint/description/memo; toggles and clearing
    lua.execute(r"""
      fig = { memo = "", tint = nil, desc = nil, type = "Figurine", name = "Figurine_Custom",
        hasTag = function(t) return t == "Pokemon" end, getLock = function() return false end,
        getName = function() return "Garchomp" end,
        setColorTint = function(c) fig.tint = c end, setDescription = function(d) fig.desc = d end }
      setmetatable(fig, { __index = function(t, k) return rawget(t, k) end })
      board_obj = { getLock = function() return true end, hasTag = function() return false end }
    """)
    fig = g.fig
    player.broadcast = lambda *a: None
    g.toolClick(player, "-1", "toolIcon_status")
    check(calls.attrs["status_White.active"] == "true", "swirl button opens the status panel")
    g.statusPick(player, "-1", "statusRes_White_burn")
    check(g.armed["White"] == "burn", "picking Burned arms it")
    g.onObjectPickUp("White", g.board_obj)
    check(g.armed["White"] == "burn", "picking up a locked object (the board) doesn't use it")
    g.onObjectPickUp("White", fig)
    tint = fig.tint
    check(g.armed["White"] is None and tint.r > 0.9 and tint.b < 0.5, f"pick-up applies it: Fire-red tint ({tint.r:.2f}, {tint.g:.2f}, {tint.b:.2f})")
    check(fig.desc == "Status: Burned" and '"burn"' in fig.memo, f"description and memo record it ({fig.desc})")
    g.statusPick(player, "-1", "statusRes_White_confused"); g.onObjectPickUp("White", fig)
    check(fig.desc == "Status: Burned, Confused", "Confused stacks on Burned")
    g.statusPick(player, "-1", "statusRes_White_paralysis"); g.onObjectPickUp("White", fig)
    check(fig.desc == "Status: Paralyzed, Confused", "a new main status replaces the old one")
    g.statusPick(player, "-1", "statusRes_White_clear"); g.onObjectPickUp("White", fig)
    check(fig.desc == "" and fig.tint.r == 1 and fig.tint.b == 1, "Clear status returns it to normal (no statuses, no tint)")
    g.statusPick(player, "-1", "statusRes_White_drowsy"); g.toolClick(player, "-1", "tool_dex")
    check(g.armed["White"] is None, "switching panels cancels a waiting status")

    # cards: search items and skills, click a result -> a one-card custom deck dropped into the player's hand
    g.toolClick(player, "-1", "tool_items")
    check(calls.attrs["items_White.active"] == "true" and calls.attrs["dex_White.active"] == "false", "potion icon opens item search")
    g.searchChanged(player, "sitrus", "itemsIn_White")
    check(calls.attrs["itemsRes_White_1.text"] == "Sitrus Berry", "'sitrus' finds Sitrus Berry")
    n = len(calls.spawned)
    g.searchPick(player, "-1", "itemsRes_White_1")
    card = calls.spawned[n + 1]
    deck = card.data.CustomDeck if card else None
    entry = deck and next(iter(deck.values()))
    check(card is not None and card.data.Name == "CardCustom" and card.data.Nickname == "Sitrus Berry"
          and "/cards/items/sitrus-berry-" in entry.FaceURL and "cards/back-items-v" in entry.BackURL
          and card.data.CardID == int(next(iter(deck.keys()))) * 100, "clicking it spawns the Sitrus Berry card")
    lift_z = 0.15 * __import__("math").sin(__import__("math").radians(16.492))
    check(abs(card.position.x - (-17.625)) < 0.01 and abs(card.position.z - (-26.4 - 4.5856 - lift_z)) < 0.01
          and card.rotation.y == 270 and abs(card.rotation.z - 16.492) < 0.01 and card.data.SidewaysCard
          and (card.data.Transform.scaleX, card.data.Transform.scaleZ) == (1.5, 1.5),
          "the item card lies landscape in the first item slot on White's stand, tilted to the slope, scaled evenly (1.5)")
    lua.execute(r"""
      oldCard = { type = "Card", scale = Vector(1.0, 1, 1.5) }
      oldCard.getScale = function() return oldCard.scale end
      oldCard.setScale = function(v) oldCard.scale = Vector(v[1], v[2], v[3]) end
      fixedOld = unstretchCard(oldCard)
      fixedAgain = unstretchCard(oldCard)
    """)
    check(g.fixedOld and not g.fixedAgain and g.oldCard.scale.x == 1.5 and g.oldCard.scale.z == 1.5,
          "a card spawned before the fix (1.0 x 1.5, art stretched) is rescaled to 1.5 x 1.5, once")
    check("1/2 hp" in card.data.Description, "the card's description is its effect")
    g.searchChanged(player, "belief", "skillsIn_White")
    g.searchPick(player, "-1", "skillsRes_White_1")
    sk = calls.spawned[n + 2]
    check(sk.data.Nickname == "Belief" and sk.data.Tags[1] == "WarriorSkill"
          and abs(sk.position.x - (-17.625)) < 0.01 and abs(sk.position.z - (-26.4 - 6.9252 - lift_z)) < 0.01,
          "the warrior skill card goes in the first skill slot (below the item)")
    g.searchChanged(player, "levitate", "abilitiesIn_White")
    g.searchPick(player, "-1", "abilitiesRes_White_1")
    ab = calls.spawned[n + 3]
    check(ab.data.Nickname == "Levitate" and ab.data.Tags[1] == "Ability" and "/cards/abilities/levitate-" in next(iter(ab.data.CustomDeck.values())).FaceURL
          and abs(ab.position.z - (-26.4 - 9.2648 - lift_z)) < 0.01,
          "the ability card goes in the first ability slot (the bottom row)")
    n = n + 1
    g.searchPick(player, "-1", "itemsRes_White_1")
    check(len(calls.spawned) == n + 2, "a stale click on the other panel's rows does nothing")
    g.spawnCard("items", "Sitrus Berry", "White")
    check(abs(calls.spawned[n + 3].position.x - (-10.575)) < 0.01, "the next item card takes the next column")
    g.spawnCard("items", "Sitrus Berry", "Green")
    far = calls.spawned[n + 4]
    check(abs(far.position.x - 17.625) < 0.01 and abs(far.position.z - (26.4 + 4.5856 + lift_z)) < 0.01 and far.rotation.y == 450,
          "a far-side seat (Green) uses the far stand, starting from its own left")
    snaps = g.standSnapPoints()
    first = snaps[1].position
    check(len(snaps) == 18 and abs(first[2] - (2.2198 + 0.55 * 0.9589)) < 0.01 and snaps[1].rotation_snap,
          "18 card snap points per stand (3 rows), lifted off the slope, snapping rotation")
    g.spawnPokemon("Gengar", "Grey")
    check(abs(calls.spawned[n + 5].position.x - (-35)) < 0.01, "a spectator's Pokemon appears in the left strip")

    # full lists: shown to whoever has the panel open with an empty search box, hidden while typing or closed
    green = lua.table_from({"color": "Green"})
    g.toolClick(player, "-1", "tool_items")     # (it was open: this closes it)
    g.searchChanged(player, "", "itemsIn_White")
    g.toolClick(player, "-1", "tool_items")
    check(calls.attrs["itemsList.active"] == "true" and calls.attrs["itemsList.visibility"] == "White",
          "opening the item panel shows White the full item list")
    g.toolClick(green, "-1", "tool_items")
    check(calls.attrs["itemsList.visibility"] == "White|Green" and calls.attrs["itemsListCover.visibility"] == "White|Green",
          "Green opening it too adds Green to the list's viewers (and its cover's)")
    g.searchChanged(player, "sitrus", "itemsIn_White")
    check(calls.attrs["itemsList.visibility"] == "Green" and calls.attrs["itemsRes_White_1.active"] == "true",
          "typing hides the list for White only, and shows White's search results")
    check(calls.attrs["items_White.height"] == 86 + 10 * 32 + 20, f"the item panel keeps its full size while typing ({calls.attrs['items_White.height']})")
    g.searchChanged(player, "", "itemsIn_White")
    check(calls.attrs["itemsList.visibility"] == "White|Green", "clearing the search box brings the list back")
    g.closePanel(green); g.closePanel(player)
    check(calls.attrs["itemsList.active"] == "false" and calls.attrs["itemsListCover.active"] == "false", "closing both panels hides the list")
    i = list(g.listNames["items"].values()).index("Sitrus Berry") + 1
    n = len(calls.spawned)
    g.listPick(player, "-1", f"itemsAll_{i}")
    check(len(calls.spawned) == n + 1 and calls.spawned[n + 1].data.Nickname == "Sitrus Berry", "clicking Sitrus Berry in the list spawns it")

    # HP signs: the stand's sign above a pedestal shows the HP of the Pokemon on it; typing sets or changes it
    lua.execute(r"""
      local keep = {}   -- clear the Pokemon spawned by earlier checks (one is on pedestal 1)
      for _, o in ipairs(objects) do if not (o.hasTag and o.hasTag("Pokemon")) then keep[#keep + 1] = o end end
      objects = keep
      southStand.guid = "s0uth1"
      southStand.ui = {}
      southStand.UI = { setXml = function(x) southStand.ui.xml = x end }
      southStand.getCustomObject = function() return { mesh = "https://pctts.github.io/tts/props/stand-v4.obj" } end
      southStand.getSnapPoints = function() return { 1 } end
      northStand.UI = { setXml = function() end }
      hpFig = { memo = '{"pokemon":"Gengar"}', guid = "abc123", name = "Custom_Model", tags = { "Pokemon" } }
      hpFig.pos = Vector(-17.625, 0.961 + 2.6 + 0.25, -28.0)                -- resting on White's first pedestal
      hpFig.getPosition = function() return hpFig.pos end
      hpFig.getCustomObject = function() return { mesh = "https://pctts.github.io/tts/models/standee-v1.obj" } end
      hpFig.UI = { getXml = function() return "" end, setXml = function() end }
      hpFig.hasTag = function(t) return t == "Pokemon" end
      objects[#objects + 1] = hpFig
      getObjectFromGUID = function(g) if g == "s0uth1" then return southStand end end
      refreshPedestals()
    """)
    h, gmax = g.hpFig, json.loads((REPO / "data" / "pokemon.json").read_text(encoding="utf-8"))["Gengar"]["hp"]

    def sign():
        root = ET.fromstring("<root>" + g.southStand.ui.xml + "</root>")
        return {e.get("id"): e for e in root.iter() if e.get("id")}, [p for p in root if p.tag == "Panel"]

    ids, panels = sign()
    f1, b1 = ids["hpIn_s0uth1_1_F"], ids["hpIn_s0uth1_1_B"]
    check(len(panels) == 12 and json.loads(h.memo).get("hp") == gmax and f1.get("text") == str(gmax)
          and panels[0].get("active") == "true" and panels[2].get("active") == "false",
          f"the stand's first sign shows the Gengar on its pedestal ({gmax}/{gmax}); empty pedestals' signs are blank")
    check((panels[0].get("rotation"), panels[1].get("rotation")) == ("-90 0 0", "90 0 180")
          and panels[0].get("position") == "-1762 -163 -540" and panels[1].get("position") == "-1762 -157 -540",
          "a label on each face of the board above pedestal 1, facing out")

    def hp():
        return json.loads(h.memo)["hp"]
    g.hpEdited(player, "-35", "hpIn_s0uth1_1_F")
    check(hp() == gmax - 35 and sign()[0]["hpIn_s0uth1_1_B"].get("text") == str(gmax - 35),
          "typing -35 on the sign takes 35 HP from that Pokemon and updates both faces")
    g.hpEdited(player, "+500", "hpIn_s0uth1_1_B")
    check(hp() == gmax, "+500 heals only up to the max")
    g.hpEdited(player, "120/230", "hpIn_s0uth1_1_F")
    check(hp() == 120, "typing a number sets it (a trailing /max is ignored)")
    g.hpEdited(player, "0", "hpIn_s0uth1_1_F")
    check(hp() == 0 and sign()[0]["hpIn_s0uth1_1_F"].get("textColor") == "#FF6B6B", "0 HP turns the number red")
    g.hpEdited(player, "lots", "hpIn_s0uth1_1_F")
    check(hp() == 0 and sign()[0]["hpIn_s0uth1_1_F"].get("text") == "0", "something that isn't a number changes nothing")

    lua.execute("hpFig.pos = Vector(0, 3.3, 0); refreshPedestals()")   # moved onto the board
    check(sign()[1][0].get("active") == "false" and hp() == 0, "moved off the pedestal: the sign goes blank, the Pokemon keeps its HP")
    lua.execute("hpFig.pos = Vector(-3.525, 0.961 + 2.6 + 0.25, -28.0); refreshPedestals()")   # onto pedestal 3
    check(sign()[1][4].get("active") == "true" and sign()[0]["hpIn_s0uth1_3_F"].get("text") == "0",
          "put on another pedestal, that pedestal's sign shows its HP")

    # Pokemon on the old model with its own sign go back to the plain standee
    lua.execute(r"""
      oldFig = { memo = '{"pokemon":"Gengar"}', guid = "old111", name = "Custom_Model", reloaded = false }
      oldFig.hasTag = function(t) return t == "Pokemon" end
      oldFig.getCustomObject = function() return { mesh = "https://pctts.github.io/tts/models/standee-v2.obj" } end
      oldFig.setCustomObject = function(c) oldFig.newMesh = c.mesh end
      oldFig.reload = function() oldFig.reloaded = true end
      plainStandee(oldFig)
    """)
    check(g.oldFig.reloaded and str(g.oldFig.newMesh).endswith("models/standee-v1.obj"), "a standee with the old sign goes back to the plain model")

    # flags: a flag takes the colour of the last Pokemon put down on its tile (its owner's), keeps it when the Pokemon
    # leaves, and a left-click on it makes it neutral. Its pole stands in the tile's corner farthest from the centre.
    lua.execute(r"""
      for _, o in ipairs(objects) do if o.hasTag("ArenaPiece") or o.hasTag("Pokemon") then o.destroyed = true end end
      flagObj = { memo = "", guid = "fl1", pos = Vector(4.8838 + 1.24438, 1.38, 4.8638 + 1.24438) }   -- tile centre (4.8838, 4.8638)
      flagObj.hasTag = function(t) return t == "Flag" or t == "ArenaPiece" end
      flagObj.getPosition = function() return flagObj.pos end
      flagObj.setColorTint = function(c) flagObj.tint = c end
      flagObj.setDescription = function(d) flagObj.desc = d end
      objects[#objects + 1] = flagObj
      onObjectSpawn(flagObj)
      onObjectSpawn(board)   -- not a flag: no error
      function flagMon(name, owner, x, z)
        local m = { tags = { "Pokemon" }, pos = Vector(x, 1.4, z) }
        m.memo = JSON.encode({ pokemon = name, owner = owner, hp = 100, maxHp = 100 })
        m.hasTag = function(t) return t == "Pokemon" end
        m.getPosition = function() return m.pos end
        m.getName = function() return name end
        m.UI = { getXml = function() return "" end, setXml = function() end }
        objects[#objects + 1] = m
        return m
      end
      function clicker(color, hover) return { color = color, getHoverObject = function() return hover end } end
    """)
    f = g.flagObj
    check(f.desc.startswith("Flag. It takes the colour"), "a spawned flag says how it works")
    lua.execute('onObjectDrop("Red", flagMon("Gengar", "Red", 4.0, 5.9))')
    check(f.tint.r > 0.8 and f.tint.g < 0.2 and f.memo == "Red", "a Red Pokemon put down on the flag's tile: the flag turns red")
    lua.execute('onObjectDrop("Blue", flagMon("Onix", "Blue", 4.9, 2.2))')
    check(f.memo == "Red", "a Pokemon put down on the next tile doesn't touch it")
    lua.execute('gengar = flagMon("Absol", "Blue", 5.5, 4.5); onObjectDrop("Blue", gengar)')
    check(f.memo == "Blue" and f.tint.b == 1, "the last Pokemon put down there wins: Blue")
    lua.execute('gengar.pos = Vector(-9, 1.4, -9); onObjectDrop("Blue", gengar)')
    check(f.memo == "Blue", "it keeps the colour when that Pokemon moves away")
    lua.execute('boxed = onPlayerAction(clicker("Green", board), Player.Action.Select, { flagObj })')
    check(g.boxed is False and f.memo == "Blue", "a box selection that catches the flag doesn't clear it")
    lua.execute('clicked = onPlayerAction(clicker("Red", flagObj), Player.Action.Select, { flagObj })')
    check(g.clicked is False and f.memo == "" and f.tint.r == 0.6, "a left-click on it makes it neutral (and doesn't select it)")

    # capture zones: the frame takes the colour of whoever has more (not fainted) Pokemon in it; ties are neutral.
    # A Pokemon without an owner belongs to the first seated player to put it down.
    lua.execute(r"""
      for _, o in ipairs(objects) do if o.hasTag("ArenaPiece") or o.hasTag("Pokemon") then o.destroyed = true end end
      zoneObj = { tags = { "Zone", "ArenaPiece" }, guid = "zn1", memo = JSON.encode({ tiles = 2, tile = 3.24875 }) }
      zoneObj.hasTag = function(t) return t == "Zone" or t == "ArenaPiece" end
      zoneObj.pos = Vector(0, 1.38, 0)
      zoneObj.positionToLocal = function(v) return Vector(v.x - zoneObj.pos.x, v.y - zoneObj.pos.y, v.z - zoneObj.pos.z) end
      zoneObj.setColorTint = function(c) zoneObj.tint = c end
      zoneObj.setDescription = function(d) zoneObj.desc = d end
      objects[#objects + 1] = zoneObj
      function zoneMon(name, owner, x, z, hp)
        local m = { tags = { "Pokemon" }, pos = Vector(x, 1.4, z) }
        m.memo = JSON.encode({ pokemon = name, owner = owner, hp = hp or 100, maxHp = 100 })
        m.hasTag = function(t) return t == "Pokemon" end
        m.getPosition = function() return m.pos end
        m.getName = function() return name end
        m.UI = { getXml = function() return "" end, setXml = function() end }
        objects[#objects + 1] = m
        return m
      end
      onObjectSpawn(zoneObj)
    """)
    z = g.zoneObj
    check(z.desc.startswith("Capture zone.") and abs(z.tint.r - 0.6) < 1e-6, "an empty zone's frame is neutral")
    g.zoneMon("Gengar", "Red", -1.6, 1.6); g.zoneMon("Onix", "Red", 1.6, -1.6); b = g.zoneMon("Absol", "Blue", 1.6, 1.6)
    g.zoneMon("Eevee", "Blue", 5.0, 0)   # outside the zone
    g.refreshZones()
    check(z.tint.r > 0.8 and z.tint.b < 0.2 and json.loads(z.memo).get("holder") == "Red",
          "two Red Pokemon to one Blue: the frame turns red")
    lua.execute('zoneMon("Pidgey", "Blue", -1.6, -1.6); refreshZones()')
    check(abs(z.tint.r - 0.6) < 1e-6 and json.loads(z.memo).get("holder") is None, "two each: a tie, back to neutral")
    lua.execute('zoneMon("Rattata", "Blue", 0.5, 0.5, 0); refreshZones()')
    check(abs(z.tint.r - 0.6) < 1e-6, "a fainted Pokemon (0 HP) doesn't count")
    lua.execute('zoneMon("Zubat", "Blue", -0.5, 0.5); refreshZones()')
    check(z.tint.b == 1 and json.loads(z.memo).get("holder") == "Blue", "three Blue to two Red: blue")
    lua.execute(r"""
      stray = zoneMon("Mew", nil, 9, 9)
      onObjectDrop("Green", stray)
      onObjectDrop("Red", stray)
      onObjectDrop("Grey", zoneMon("Ditto", nil, 9, 9))
    """)
    check(json.loads(g.stray.memo).get("owner") == "Green", "an ownerless Pokemon belongs to the first seated player to put it down")

    # hand zones: TTS's default ones (10, over the stands) are moved to the 8 just past the table's edge (Brown and Teal
    # removed, a missing one spawned), and the cards a player held are put back into their hand; a correct layout is
    # left alone
    lua.execute(r"""
      handObjs = {}
      local function hand(c, x, z, sx, sz)
        local h = { color = c, pos = Vector(x, 3.29, z), scale = Vector(sx, 11.9, sz), rot = Vector(0, 0, 0) }
        h.getValue = function() return h.color end
        h.getPosition = function() return h.pos end
        h.getScale = function() return h.scale end
        h.setPosition = function(v) h.pos = Vector(v[1], v[2], v[3]) end
        h.setRotation = function(v) h.rot = Vector(v[1], v[2], v[3]) end
        h.setScale = function(v) h.scale = Vector(v[1], v[2], v[3]) end
        h.destruct = function() h.gone = true end
        handObjs[#handObjs + 1] = h
        return h
      end
      for _, c in ipairs({ "Red", "Brown", "White" }) do hand(c, 0, -34.43, 15.33, 6.35) end
      for _, c in ipairs({ "Blue", "Teal", "Orange", "Yellow", "Pink", "Purple" }) do hand(c, 0, 34.43, 15.33, 6.35) end
      handByColor = function(c) for _, h in ipairs(handObjs) do if h.color == c and not h.gone then return h end end end
      heldCard = { pos = Vector(0, 3, -34.4) }
      heldCard.setPosition = function(v) heldCard.pos = Vector(v[1], v[2], v[3]) end
      handHeld = { Red = { heldCard } }
      Hands = { getHands = function()
        local live = {}
        for _, h in ipairs(handObjs) do if not h.gone then live[#live + 1] = h end end
        return live
      end }
      Tables.getTableObject = function() return { getBounds = function() return { size = Vector(110.3, 1, 75.3) } end } end
      spawnedHands = {}
      local realSpawn = spawnObjectData
      spawnObjectData = function(t)
        if t.data.Name == "HandTrigger" then
          spawnedHands[#spawnedHands + 1] = t
          hand(t.data.FogColor, t.position[1], t.position[3], t.data.Transform.scaleX, t.data.Transform.scaleZ)
          return
        end
        return realSpawn(t)
      end
    """)
    changed = g.ensureHandZones()
    live = {h.color: h for h in g.Hands.getHands().values()}
    red, pink = live.get("Red"), live.get("Pink")
    edge_z, edge_x = 75.3 / 2 + 3.56 / 2 + 0.5, 110.3 / 2 + 3.56 / 2 + 0.5
    check(changed and sorted(live) == sorted(["Red", "White", "Blue", "Green", "Orange", "Yellow", "Pink", "Purple"])
          and [h.data.FogColor for h in g.spawnedHands.values()] == ["Green"]
          and abs(red.pos.z + edge_z) < 1e-6 and red.pos.y == 2.85 and red.pos.x == -9.48 and red.scale.z == 3.56
          and abs(pink.pos.x - edge_x) < 1e-6 and pink.rot.y == 270,
          "TTS's default hand zones are moved just past the table's edge (Brown/Teal removed, missing Green spawned)")
    hc = g.heldCard.pos
    check(abs(hc.x + 9.48) < 1e-6 and abs(hc.z + edge_z) < 1e-6, "a card Red was holding is put back into Red's moved hand")
    check(not g.ensureHandZones(), "a correct layout is left alone")

    # the board isn't interactive; players can't delete or cut the stands or fixed map pieces (other things they can)
    lua.execute(r"""
      local function obj(tags)
        local o = { tags = tags }
        o.hasTag = function(t) for _, x in ipairs(o.tags) do if x == t then return true end end return false end
        return o
      end
      pBoard, pFlag, pStand, pCard, pTree = obj({ "Board3D" }), obj({ "Flag", "ArenaPiece" }), obj({ "Stand" }), obj({ "Item" }), obj({ "Tree", "ArenaPiece" })
      pPillar = obj({ "Pillar" })
      pieceSetup(pBoard)
      pieceSetup(pPillar)
      delFlag = onPlayerAction(nil, Player.Action.Delete, { pCard, pFlag })
      cutStand = onPlayerAction(nil, Player.Action.Cut, { pStand })
      delTree = onPlayerAction(nil, Player.Action.Delete, { pTree, pCard })
      pickCard = onPlayerAction(nil, Player.Action.PickUp, { pCard })
      pickTree = onPlayerAction(nil, Player.Action.PickUp, { pTree })
    """)
    check(g.pBoard.interactable is False and g.pPillar.interactable is False,
          "the board and the pillars can't be clicked, selected or deleted (not interactive)")
    check(g.delFlag is False and g.cutStand is False, "deleting a flag or cutting a stand is refused")
    check(g.delTree is True and g.pickCard is True and g.pickTree is True,
          "a tree or a card can still be deleted; other actions aren't blocked")

    # saving: the downloads are saved as the text that came in (cheap), and a load without internet uses them.
    # TTS's Lua (MoonSharp) fails "pattern too complex" on patterns over text this size (real Lua doesn't), so the
    # reader of the saved text must not use patterns at all.
    reader = re.search(r"local function readSavedState\(saved\)(.*?)\nend\n", src, re.S).group(1)
    check(not re.search(r"g?match\(|gsub\(|:find\([^)]*\)(?<!true\))", reader.split("elseif")[0]),
          "the saved-text reader splits with plain find/sub (no Lua patterns on 280 KB of text)")
    saved = g.onSave()
    check(saved.startswith("PCTTS-STATE-1") and len(saved) > 100000 and "Charizard\t" in saved,
          f"the save holds the downloaded roster, cards and stats as text ({len(saved) // 1024} KB)")

    # the downloads are plain text (tools/fast_data.py; JSON took TTS ~15 s per 100 KB): read back, each is the
    # same table as its JSON (an empty field is nil), and the reader uses plain find/sub only
    fast = src[src.index("local function splitPlain"):src.index("function onLoad(saved)")]
    check(not re.search(r"g?match\(|gsub\(|:find\([^)]*\)(?<!true\))", fast),
          "the plain-text reader splits with plain find/sub only")

    def same(a, b):
        if isinstance(b, dict):
            b = {k: v for k, v in b.items() if v is not None and v != ""}   # empty = nil (the script reads card.effect or "")
            a = {k: v for k, v in a.items() if v != ""} if isinstance(a, dict) else a
            return isinstance(a, dict) and set(a) == set(b) and all(same(a[k], b[k]) for k in b)
        if isinstance(b, list):
            return isinstance(a, list) and len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
        if isinstance(b, float) or isinstance(a, float):
            return isinstance(a, (int, float)) and abs(a - b) < 1e-4
        return a == b
    for key, stem in (("roster", "figures/index"), ("cards", "cards/index"), ("stats", "data/pokemon"),
                      ("arenas", "arenas/index")):
        got = from_lua(g.readData(key, (REPO / f"{stem}.txt").read_text(encoding="utf-8")))
        want = json.loads((REPO / f"{stem}.json").read_text(encoding="utf-8"))
        check(same(got, want), f"{stem}.txt reads back as the same table as {stem}.json")
    lua.execute(r"""
      WebRequest.get = function(url, cb) cb({ is_error = true, error = "offline" }) end
      catalog.dex = { index = {}, list = {}, keys = {} }
      stats = {}
    """)
    g.onLoad(saved)
    check(len(g.catalog.dex.list) == 704 and g.stats["Gengar"] is not None,
          "offline, a load falls back to the saved copies (roster, stats)")
    printed = [str(p) for p in calls.printed.values()]
    check(not printed, f"nothing was printed to the console ({printed[:3]})")

    print("\nall checks passed" if not failures else f"\n{len(failures)} check(s) failed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
