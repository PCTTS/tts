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


def board(arena, kind):
    """The published board file (kind: mesh/texture) an arena's map.json names, as the arena index lists it."""
    b = json.loads((REPO / "arenas" / arena / "map.json").read_text(encoding="utf-8"))["board"]
    return f"arenas/{arena}/{b[kind]}"

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
local guids = 0
function stub(o)
  if not o.guid then guids = guids + 1; o.guid = string.format("g%05d", guids) end
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
  o.getSnapPoints = o.getSnapPoints or function() return o.snaps or {} end
  o.setSnapPoints = o.setSnapPoints or function(p) o.snaps = p end
  o.setLock = o.setLock or function(v) o.locked = v end
  o.setRotation = o.setRotation or function(v) o.rot = Vector(v[1] or v.x, v[2] or v.y, v[3] or v.z) end
  o.UI = o.UI or { setXml = function(x) o.uiXml = x end, setAttribute = function() end,
    setCustomAssets = function(a) o.assets = a end, getXml = function() return o.uiXml or "" end }
  objects[#objects + 1] = o
  return o
end
function getObjectFromGUID(g)
  for _, o in ipairs(objects) do if o.guid == g and not o.destroyed then return o end end
end
-- team stands: near (south) at z = -26.4 facing the near player, far (north) turned 180 degrees
local function makeStand(z, yaw)
  local s = { tags = { "Stand" }, type = "Generic", locked = true, snaps = {} }
  s.getSnapPoints = function() return s.snaps end
  s.setSnapPoints = function(p) s.snaps = p end
  s.getCustomObject = function() return { mesh = s.newMesh or "https://pctts.github.io/tts/props/stand-v4.obj" } end
  s.setCustomObject = function(c) s.newMesh = c.mesh end
  s.reload = function() s.reloaded = true; onObjectSpawn(s) end   -- TTS respawns a reloaded object
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
  return stub({ tags = t.data.Tags, type = kind, memo = t.data.Memo, name = t.data.Name, locked = t.data.Locked,
    getName = function() return t.data.Nickname end,
    getPosition = function()   -- always a Vector in TTS, whatever it was spawned with
      local p = t.position or {}
      return p.x and p or Vector(p[1] or 0, p[2] or 0, p[3] or 0)
    end,
    setPosition = function(v) t.position = Vector(v[1] or v.x, v[2] or v.y, v[3] or v.z) end,
    getRotation = function()
      local r = t.rotation or {}
      return r.x and r or Vector(r[1] or 0, r[2] or 0, r[3] or 0)
    end,
    setRotation = function(v) t.rotation = Vector(v[1] or v.x, v[2] or v.y, v[3] or v.z) end,
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
        check("tooltip" not in xml and "tooltip" not in (REPO / "lua" / "Global.lua").read_text(encoding="utf-8"),
              "no hover text on any button (toolbar or pieces)")
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
    check('onClick="closePanel"' in maps_panel, "the map panel has an X to close it")
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

    # on load: the stands get the plain model and 9 pedestals of their own (the old backgammon discs go), the spectator
    # stand appears with its 6, and the turn track for the arena on the table (Pugilis: 15 turns) with its token on 1
    lua.execute(r"""
      function pedsOf(stand)
        local xs = {}
        for _, p in ipairs(standPedestals(stand)) do xs[#xs + 1] = p.x end
        return xs
      end
      function tagged(tag)
        local out = {}
        for _, o in ipairs(getAllObjects()) do if o.hasTag(tag) then out[#out + 1] = o end end
        return out
      end
    """)
    sx, nx = list(g.pedsOf(g.southStand).values()), list(g.pedsOf(g.northStand).values())
    nine = [-18.8, -14.1, -9.4, -4.7, 0, 4.7, 9.4, 14.1, 18.8]
    check(str(g.southStand.newMesh).endswith("props/stand-v2.obj") and g.southStand.reloaded
          and all(abs(a - b) < 1e-6 for a, b in zip(sx, nine)) and len(sx) == 9 and len(nx) == 9
          and json.loads(g.southStand.memo)["slots"] == 9 and len(g.southStand.snaps) == 27,
          "on load each team stand gets the plain model and 9 pedestals of its own, 27 card snap points")
    spect = list(g.tagged("SpectatorStand").values())
    seats = sorted((round(p.getPosition().x, 3), round(p.getPosition().z, 3)) for p in g.tagged("Pedestal").values()
                   if json.loads(p.memo or "{}").get("spect"))
    check(len(spect) == 1 and spect[0].getPosition().x == 37.0 and spect[0].getRotation().y == 180
          and spect[0].getCustomObject().mesh.endswith("props/spectators-v3.obj")
          and seats == [(37.1, z) for z in (-12.5, -7.5, -2.5, 2.5, 7.5, 12.5)]
          and all(abs(p.getPosition().y - (0.961 + 2.6)) < 1e-9 for p in g.tagged("Pedestal").values()),
          "the spectator stand at the right end, as tall as the team stands, turned so its turn track faces the board, "
          "with 6 evenly spaced pedestals along its middle, 3 on each half")
    token = list(g.tagged("TurnToken").values())
    sp = spect[0]
    gold = ET.fromstring(sp.uiXml)
    check(len(g.tagged("TurnTrack")) == 0 and json.loads(sp.memo)["turns"] == 15 and len(sp.snaps) == 15
          and abs(sp.snaps[1].position[3] - (-14)) < 1e-9 and abs(sp.snaps[1].position[2] - 2.6) < 1e-9
          and abs(sp.snaps[1].position[1] - 2.7) < 1e-9 and gold.get("position") == "270 1400 -261"
          and gold.get("color") == "#E8C462" and gold.find("Text").text == "15" and gold.find("Text").get("rotation") == "0 0 90"
          and len(token) == 1
          and abs(token[0].getPosition().z - 14) < 1e-9 and abs(token[0].getPosition().x - 34.3) < 1e-9
          and abs(token[0].getPosition().y - (0.961 + 2.6 + 0.1)) < 1e-9 and token[0].getRotation().y == 0,
          "the stand's turn track (slots 1-15 along its board side) shows Pugilis's last turn (15) in gold; the token "
          "snaps to the slots and starts on 1 at the far end (the left, seen from the board)")
    lua.execute(r"""
      local s = tagged("SpectatorStand")[1]
      local movers = { s }
      for _, o in ipairs(tagged("Pedestal")) do
        if (o.memo or ""):find("spect", 1, true) then movers[#movers + 1] = o end
      end
      for _, o in ipairs(movers) do local p = o.getPosition(); o.setPosition({ p.x - 5.7, p.y, p.z }) end
      oldSeatCount = #tagged("Pedestal")
      ensureSpectators()
    """)
    seats = sorted((round(p.getPosition().x, 3), round(p.getPosition().z, 3)) for p in g.tagged("Pedestal").values()
                   if json.loads(p.memo or "{}").get("spect"))
    check(g.tagged("SpectatorStand")[1].getPosition().x == 37.0 and seats == [(37.1, z) for z in (-12.5, -7.5, -2.5, 2.5, 7.5, 12.5)]
          and len(g.tagged("Pedestal")) == g.oldSeatCount,
          "a spectator stand out of place moves back with its pedestals")
    lua.execute("calls.spawned = {}")

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
    check(abs(spawned.position.x - (-18.8)) < 0.01 and abs(spawned.position.z - (-28.0)) < 0.01,
          f"White's Pokemon goes on the first pedestal of the near stand ({spawned.position.x:.2f}, {spawned.position.z:.2f})")

    # maps: the arenas from arenas/index.json; picking one puts its board, snap points and pieces on the table
    got = [(m.name, bool(m.current)) for m in g.mapList().values()]
    check(got == [("Avia", False), ("Chrysalia", False), ("Fontaine", False), ("Greenleaf", False), ("Illusio", False), ("Ingis", False),
                  ("Pugilis", True), ("Snow", False), ("Spectra", False), ("Terrera Mountain", False), ("Valora", False),
                  ("Violight", False), ("Viperia", False), ("Yaksha", False)],
          f"map list shows the fourteen arenas, Pugilis on the table ({got})")

    def row(name):   # the map panel's row for an arena (alphabetical)
        return f"mapRes_White_{[m.name for m in g.mapList().values()].index(name) + 1}"
    g.toolClick(player, "-1", "tool_maps")
    check(calls.attrs["maps_White.active"] == "true" and calls.attrs["dex_White.active"] == "false"
          and calls.attrs[row("Pugilis") + ".text"] == "Pugilis" and calls.attrs[row("Pugilis") + ".colors"].startswith("#8DB8F7"),
          "map button opens the map panel (and closes the search panel); the map on the table is highlighted, no label")
    n = len(calls.spawned)
    g.mapPick(player, "-1", row("Pugilis"))
    check(len(calls.spawned) == n, "picking the arena that's already on the table does nothing")
    lua.execute("board.destroyed = true")
    g.refreshMaps("White")
    g.mapPick(player, "-1", row("Pugilis"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    brd = new[0].data if new else None
    flags = [s for s in new[1:] if s.data.Tags[1] == "Flag"]
    check(brd is not None and brd.Nickname == "Pugilis" and brd.Tags[1] == "Board3D" and brd.Locked
          and brd.CustomMesh.MeshURL.endswith(board("pugilis", "mesh")) and brd.CustomMesh.ColliderURL == brd.CustomMesh.MeshURL
          and brd.CustomMesh.DiffuseURL.endswith(board("pugilis", "texture")) and not brd.CustomMesh.Convex,
          "picking Pugilis puts its 3D board on the table (its own mesh as collider)")
    check(len(flags) == 4 and backdrop(new, "misc/pugilis-dirt-v1.jpg") and calls.tableURL is None,
          "with its 4 flags and its surroundings on the backdrop panel (the table itself untouched)")

    # Illusio: floating islands with 6 flags, 6 portals in their starting colours, 6 bridges that start dropped
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", row("Illusio"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new if s.data.Tags[1] not in ("TurnTrack", "TurnToken")]   # (a new turn track too)
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith(board("illusio", "mesh"))
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
    g.mapPick(player, "-1", row("Ingis"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new if s.data.Tags[1] not in ("TurnTrack", "TurnToken")]   # (a new turn track too)
    zones = [s for s in new if s.data.Tags[1] == "Zone"]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith(board("ingis", "mesh"))
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
    g.mapPick(player, "-1", row("Viperia"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new if s.data.Tags[1] not in ("TurnTrack", "TurnToken")]   # (a new turn track too)
    vmap = json.loads((REPO / "arenas" / "viperia" / "map.json").read_text(encoding="utf-8"))
    walls = sum(row.count("#") for row in vmap["grid"])
    vidx = json.loads((REPO / "arenas" / "index.json").read_text(encoding="utf-8"))["Viperia"]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith(board("viperia", "mesh"))
          and kinds.count("Flag") == 3 and len(kinds) == 5 and len(vidx["snaps"]) == 16 * 15 - walls
          and backdrop(new, "misc/jungle-placeholder-v1.jpg"),
          f"picking Viperia: its board, 3 flags, snap points on all {16 * 15 - walls} tiles but the {walls} walls, the jungle table")
    sp = g.tagged("SpectatorStand")[1]
    tok = list(g.tagged("TurnToken").values())
    check(not [x for x in new if x.data.Tags[1] in ("TurnTrack", "TurnToken", "SpectatorStand")]
          and json.loads(sp.memo)["turns"] == 10 and ET.fromstring(sp.uiXml).get("position") == "270 400 -261"
          and ET.fromstring(sp.uiXml).find("Text").text == "10"
          and len(tok) == 1 and abs(tok[0].getPosition().z - 14) < 1e-9 and abs(tok[0].getPosition().x - 34.3) < 1e-9,
          "a new map tints its own last turn (Viperia: 10) and puts the token back on 1")

    # Violight: 4 capture zone frames round the spire, no snap points on the spire, the steel table
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", row("Violight"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new if s.data.Tags[1] not in ("TurnTrack", "TurnToken")]   # (a new turn track too)
    lidx = json.loads((REPO / "arenas" / "index.json").read_text(encoding="utf-8"))["Violight"]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith(board("violight", "mesh"))
          and kinds.count("Zone") == 4 and len(kinds) == 6 and len(lidx["snaps"]) == 256 - 4
          and backdrop(new, "misc/violight-placeholder-v1.jpg"),
          "picking Violight: its board, 4 zone frames, snap points on every tile but the 4 of the spire, the steel table")

    # Chrysalia: its board, 3 capture zone frames and 2 traps
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", row("Chrysalia"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new if s.data.Tags[1] not in ("TurnTrack", "TurnToken")]   # (a new turn track too)
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith(board("chrysalia", "mesh"))
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
    g.mapPick(player, "-1", row("Yaksha"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new if s.data.Tags[1] not in ("TurnTrack", "TurnToken")]   # (a new turn track too)
    zones = [s for s in new if s.data.Tags[1] == "Zone"]
    free =[s for s in new if s.data.Tags[1] in ("Tree", "Gift")]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith(board("yaksha", "mesh"))
          and len(zones) == 3 and sum(z.data.CustomMesh.MeshURL.endswith("zoneframe4-raised60-v1.obj") for z in zones) == 1
          and kinds.count("Tree") == 6 and kinds.count("Gift") == 14 and all(not s.data.Locked for s in free)
          and all(s.data.Locked for s in new if s.data.Tags[1] in ("Board3D", "Zone")),
          "picking Yaksha: its board, a 4x4 (raised: drawn in on its flat top) and two 2x2 zone frames, 6 trees and 14 gifts that players can move")

    # Spectra: its board, 14 statues that players move (not locked), 4 flags, no snap points on the crypts
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", row("Spectra"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new if s.data.Tags[1] not in ("TurnTrack", "TurnToken")]   # (a new turn track too)
    statues = [s for s in new if s.data.Tags[1] == "Statue"]
    sidx = json.loads((REPO / "arenas" / "index.json").read_text(encoding="utf-8"))["Spectra"]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith(board("spectra", "mesh"))
          and len(statues) == 14 and all(not s.data.Locked for s in statues) and kinds.count("Flag") == 4
          and len(sidx["snaps"]) == 256 - 53 and backdrop(new, "misc/graveyard-placeholder-v1.jpg"),
          "picking Spectra: its board, 14 statues players can move, 4 flags, snap points on all but the 53 crypt tiles, the graveyard table")

    # Fontaine: its river's water on every river tile, 8 gates (posts and sluice block) starting open, 4 fountains
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", row("Fontaine"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new if s.data.Tags[1] not in ("TurnTrack", "TurnToken")]   # (a new turn track too)
    fidx = json.loads((REPO / "arenas" / "index.json").read_text(encoding="utf-8"))["Fontaine"]
    gates = [s for s in new if s.data.Tags[1] == "Gate"]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith(board("fontaine", "mesh"))
          and kinds.count("Water") == 56 and kinds.count("GateFrame") == 8 and kinds.count("Gate") == 8
          and kinds.count("Fountain") == 4 and kinds.count("Zone") == 3 and len(fidx["snaps"]) == 256 - 4
          and all(json.loads(s.data.Memo)["open"] for s in gates) and backdrop(new, "misc/valley-placeholder-v1.jpg"),
          "picking Fontaine: its board, the river's water, 8 gates (open), 4 fountains, 3 zones, the valley table")
    check(abs((json.loads(gates[0].data.Memo)["y"] - gates[0].position.y) - 1.16) < 1e-6,
          "an open gate's sluice block starts sunk into the river bed")

    # gates drain the river past them: an edge gate its whole branch (with its quarter of the middle), an inner
    # gate the part past it
    lua.execute(r"""
      for _, o in ipairs(objects) do if o.hasTag("ArenaPiece") then o.destroyed = true end end
      local function piece(tag, memo, y)
        local o = { tags = { tag, "ArenaPiece" }, guid = tag .. #objects, menu = {}, snaps = {}, ui = {}, pos = Vector(0, y, 0) }
        o.hasTag = function(t) return t == tag or t == "ArenaPiece" end
        o.memo = JSON.encode(memo)
        o.getPosition = function() return o.pos end
        o.setPositionSmooth = function(p) o.pos = p end
        o.getSnapPoints = function() return o.snaps end
        o.setSnapPoints = function(s) o.snaps = s end
        o.setDescription = function(d) o.desc = d end
        o.clearContextMenu = function() o.menu = {} end
        o.addContextMenuItem = function(label, fn) o.menu[#o.menu + 1] = { label = label, fn = fn } end
        o.UI = { setXml = function(x) o.ui.xml = x end, setCustomAssets = function(a) o.ui.assets = a end }
        objects[#objects + 1] = o
        onObjectSpawn(o)
        return o
      end
      fFrame = piece("GateFrame", { gate = 1, branch = 1, part = "edge" }, 0.41)
      fEdge = piece("Gate", { gate = 1, branch = 1, part = "edge", open = true, y = 0.41 }, 0.41 - 1.16)
      fInner = piece("Gate", { gate = 2, branch = 1, part = "inner", open = true, y = 0.41 }, 0.41 - 1.16)
      fOther = piece("Gate", { gate = 3, branch = 2, part = "edge", open = true, y = 0.41 }, 0.41 - 1.16)
      wEdge = piece("Water", { branch = 1, part = "edge", y = 1.03 }, 1.03)
      wInner = piece("Water", { branch = 1, part = "inner", y = 1.03 }, 1.03)
      wOther = piece("Water", { branch = 2, part = "inner", y = 1.03 }, 1.03)
    """)
    fr = g.fFrame
    check('onClick="Global/gateClicked"' in str(fr.ui.xml) and 'id="gate_1"' in str(fr.ui.xml)
          and [fr.menu[i].label for i in (1, 2)] == ["Open gate", "Close gate"] and fr.desc.startswith("Water gate."),
          "a gate's posts get the arrows button (for gate 1) and Open / Close gate")
    check(g.wEdge.interactable is False and g.fEdge.interactable is False and len(list(g.wEdge.snaps.values())) == 1,
          "the water and the sluice block can't be clicked; a water tile has a snap point")
    lua.execute('gateClicked(nil, nil, "gate_2")')
    up = lambda o: abs(o.pos.y - 1.03) < 1e-6
    check(abs(g.fInner.pos.y - 0.41) < 1e-6 and up(g.wEdge) and not up(g.wInner) and up(g.wOther),
          "closing an inner gate raises its block and drains only the river past it")
    lua.execute('fFrame.menu[2].fn("Red")')
    check(abs(g.fEdge.pos.y - 0.41) < 1e-6 and not up(g.wEdge) and not up(g.wInner) and up(g.wOther),
          "closing the edge gate (right-click) drains its whole branch; another branch keeps its water")
    lua.execute('gateClicked(nil, nil, "gate_1"); gateClicked(nil, nil, "gate_2")')
    check(abs(g.fEdge.pos.y - (0.41 - 1.16)) < 1e-6 and up(g.wEdge) and up(g.wInner),
          "opening them again sinks the blocks and fills the river")

    # Terrera Mountain: the centre and two side floors at three heights, 2 flags, a control zone frame on each board
    lua.execute('for _, o in ipairs(objects) do if o.hasTag("ArenaPiece") then o.destroyed = true end end')   # the gate stand-ins
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", row("Terrera Mountain"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new if s.data.Tags[1] not in ("TurnTrack", "TurnToken")]   # (a new turn track too)
    tidx = json.loads((REPO / "arenas" / "index.json").read_text(encoding="utf-8"))["Terrera Mountain"]
    zone_y = sorted(round(s.position.y - 0.961, 2) for s in new if s.data.Tags[1] == "Zone")
    heights = sorted({round(p[1], 2) for p in tidx["snaps"]})
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith(board("terrera", "mesh"))
          and kinds.count("Flag") == 2 and kinds.count("Zone") == 3 and len(tidx["snaps"]) == 128 + 64 + 64
          and len(heights) == 3 and zone_y == [0.41, 1.38, 2.35] and backdrop(new, "misc/cave-placeholder-v1.jpg"),
          f"picking Terrera Mountain: its board (centre and two side floors at three heights {heights}), 2 flags, a zone "
          f"on each floor at its height {zone_y}, the cave table")

    # Snow: 18 tiles deep, so the table stretches front to back (its trims keep their width outside the board), the
    # snowfield covers the board's depth (a hair higher, over the trim), and the stands move back a tile with what's
    # on them; picking a 16-tile map puts it all back
    lua.execute(r"""
      for _, o in ipairs(objects) do if o.hasTag("ArenaPiece") then o.destroyed = true end end
      tableObj = { scale = Vector(1, 1, 1) }
      tableObj.getScale = function() return tableObj.scale end
      tableObj.setScale = function(v) tableObj.scale = Vector(v[1], v[2], v[3]) end
      tableObj.getBounds = function() return { size = Vector(110.3, 1, 75.246 * tableObj.scale.z) } end
      Tables.getTableObject = function() return tableObj end
      for _, st in ipairs({ southStand, northStand }) do   -- stands that can move
        local pz = st.getPosition().z
        st.getPosition = function() return Vector(0, 0.961, pz) end
        st.setPosition = function(v) pz = v[3] or v.z end
      end
      local function loose(name, pos, locked)
        local o = { tags = {}, pos = pos, locked = locked }
        o.getName = function() return name end
        o.getPosition = function() return o.pos end
        o.setPosition = function(v) o.pos = Vector(v[1], v[2], v[3]) end
        objects[#objects + 1] = o
        return o
      end
      onPedestal = loose("Lokix", Vector(-17.625, 3.8, -28.0))
      disc = loose("disc", Vector(-10.575, 3.68, 28.0), true)
      inHand = loose("card", Vector(3.5, 3.0, -30.0)); inHand.held_by_color = "Red"
      onBoard = loose("Pikachu", Vector(1.6, 1.4, -24.4))
      for _, o in ipairs({ onPedestal, disc, inHand, onBoard }) do o.hasTag = function() return false end end
    """)
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", row("Snow"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new if s.data.Tags[1] not in ("TurnTrack", "TurnToken")]   # (a new turn track too)
    sidx = json.loads((REPO / "arenas" / "index.json").read_text(encoding="utf-8"))["Snow"]
    panel = [s for s in new if s.data.Tags[1] == "ArenaBackdrop"]
    k = (58.4775 + 75.246 - 51.981) / 75.246
    stand_z = 58.4775 / 2 + 0.4095
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith(board("snow", "mesh"))
          and kinds.count("Flag") == 4 and len(sidx["snaps"]) == 324 and abs(sidx["depth"] - 58.4775) < 1e-4
          and backdrop(new, "misc/snowfield-placeholder-v1.jpg"),
          "picking Snow: its 18x18 board, 4 flags, a snap point on every tile, the snowfield table")
    check(abs(g.tableObj.scale.z - k) < 1e-6 and len(panel) == 1 and abs(panel[0].data.Transform.scaleZ - 58.4775 / 51.981) < 1e-6
          and abs(panel[0].position[2] - 0.9625) < 1e-9,
          f"the table stretches {k:.4f}x front to back (the trims keep their width outside the board) and the snowfield is "
          f"stretched to the board's depth, a hair higher where it lies over the trim")
    zs = lambda: (g.southStand.getPosition().z, g.northStand.getPosition().z)
    sz, nz = zs()
    check(abs(sz + stand_z) < 1e-6 and abs(nz - stand_z) < 1e-6 and abs(g.onPedestal.pos.z - (-28.0 - (stand_z - 26.4))) < 1e-6
          and abs(g.disc.pos.z - (28.0 + stand_z - 26.4)) < 1e-6 and abs(g.inHand.pos.z + 30.0) < 1e-9
          and abs(g.onBoard.pos.z + 24.4) < 1e-9,
          f"the stands move back a tile to the usual gap from the board (z {nz:.3f}), taking the Pokemon on a pedestal and "
          f"the (locked) pedestal discs with them; a card in a hand and a Pokemon on the board stay put")
    lua.execute('for _, o in ipairs(objects) do if o.hasTag("ArenaPiece") then o.destroyed = true end end')
    g.mapPick(player, "-1", row("Spectra"))
    sz, nz = zs()
    spanel = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1) if calls.spawned[i].data.Tags[1] == "ArenaBackdrop"][-1]
    check(abs(g.tableObj.scale.z - 1) < 1e-9 and abs(sz + 26.4) < 1e-6 and abs(nz - 26.4) < 1e-6
          and abs(g.onPedestal.pos.z + 28.0) < 1e-6 and abs(g.disc.pos.z - 28.0) < 1e-6
          and spanel.data.Transform.scaleZ == 1 and abs(spanel.position[2] - 0.9615) < 1e-9,
          "picking a 16-tile map (Spectra) puts the table, the stands (and what's on them) and the panel back")
    lua.execute("for _, o in ipairs({ onPedestal, disc, inHand, onBoard }) do o.destroyed = true end")

    # Valora: 5 gear plates (3 numbered), 10 blockers (closed), 3 capture zones lifted onto the gear plates
    lua.execute('for _, o in ipairs(objects) do if o.hasTag("ArenaPiece") then o.destroyed = true end end')   # the gate stand-ins
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", row("Valora"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new if s.data.Tags[1] not in ("TurnTrack", "TurnToken")]   # (a new turn track too)
    vidx = json.loads((REPO / "arenas" / "index.json").read_text(encoding="utf-8"))["Valora"]
    gears = [json.loads(s.data.Memo) for s in new if s.data.Tags[1] == "Gear"]
    doors = [(s, json.loads(s.data.Memo)) for s in new if s.data.Tags[1] == "Door"]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith(board("valora", "mesh"))
          and len(gears) == 5 and sorted(m["gear"] for m in gears) == [0, 0, 1, 2, 3] and kinds.count("Zone") == 3
          and len(doors) == 10 and all(s.data.Locked and m["open"] is False and abs(m["x"] - s.position.x) < 1e-6
                                       and abs(m["z"] - s.position.z) < 1e-6 for s, m in doors)
          and len(vidx["snaps"]) == 256 - 32 - 66 and backdrop(new, "misc/foundry-placeholder-v1.jpg"),
          "picking Valora: its board, 5 gears (numbered 1-3 and two plain), 10 blockers that start closed, 3 zones, "
          "snap points on all but the walls and the gear tiles (the plates carry those), the foundry table")

    # a gear turns 270 degrees the way it points, carrying what stands on it round; a numbered gear's doors button
    # opens and closes its blockers (sliding into the wall beside them, or sinking)
    T = 3.24875
    lua.execute(r"""
      for _, o in ipairs(objects) do if o.hasTag("ArenaPiece") then o.destroyed = true end end
      local function obj(tags, memo, pos)
        local o = { tags = tags, guid = "v" .. #objects, menu = {}, snaps = {}, ui = {}, pos = pos, rot = Vector(0, 0, 0) }
        o.memo = memo and JSON.encode(memo) or ""
        o.getPosition = function() return o.pos end
        o.setPosition = function(p) o.pos = Vector(p[1] or p.x, p[2] or p.y, p[3] or p.z) end
        o.setPositionSmooth = function(p) o.pos = p end
        o.getRotation = function() return o.rot end
        o.setRotation = function(r) o.rot = Vector(r[1], r[2], r[3]) end
        o.setLock = function(l) o.locked = l; o.lockLog = (o.lockLog or "") .. tostring(l) .. " " end
        o.getSnapPoints = function() return o.snaps end
        o.setSnapPoints = function(s) o.snaps = s end
        o.setDescription = function(d) o.desc = d end
        o.clearContextMenu = function() o.menu = {} end
        o.addContextMenuItem = function(label, fn) o.menu[#o.menu + 1] = { label = label, fn = fn } end
        o.UI = { setXml = function(x) o.ui.xml = x end, setCustomAssets = function(a) o.ui.assets = a end }
        o.hasTag = function(t) for _, x in ipairs(o.tags) do if x == t then return true end end return false end
        o.getLock = function() return o.locked or false end
        objects[#objects + 1] = o
        return o
      end
      gearPlate = obj({ "Gear", "ArenaPiece" }, { gear = 2, size = 4, turn = "ccw", tile = 3.24875 }, Vector(10, 0.961, 20))
      gearPlate.locked = true
      smallGear = obj({ "Gear", "ArenaPiece" }, { gear = 0, size = 3, turn = "cw", tile = 3.24875 }, Vector(-10, 0.961, 0))
      smallGear.locked = true
      rider = obj({ "Pokemon" }, nil, Vector(10 + 1.5 * 3.24875, 1.03, 20 + 0.5 * 3.24875))
      rider.rot = Vector(0, 33, 0)
      offGear = obj({ "Pokemon" }, nil, Vector(10 + 2.5 * 3.24875, 1.03, 20))
      held = obj({ "Pokemon" }, nil, Vector(10, 1.5, 20)); held.held_by_color = "Red"
      doorA = obj({ "Door", "ArenaPiece" }, { door = 2, open = false, x = 1, y = 1.37, z = 8, sx = -3.24875, sy = 0, sz = 0 }, Vector(1, 1.37, 8))
      doorB = obj({ "Door", "ArenaPiece" }, { door = 3, open = false, x = 2, y = 1.37, z = 14, sx = 0, sy = -1.94, sz = 0 }, Vector(2, 1.37, 14))
      doorC = obj({ "Door", "ArenaPiece" }, { door = 1, open = false, x = 3, y = 1.37, z = 0, sx = 0, sy = 0, sz = 3.24875 }, Vector(3, 1.37, 0))
      for _, o in ipairs({ gearPlate, smallGear, doorA, doorB, doorC }) do onObjectSpawn(o) end
      getObjectFromGUID = function(guid) for _, o in ipairs(objects) do if o.guid == guid and not o.destroyed then return o end end end
    """)
    gp, sg = g.gearPlate, g.smallGear
    xml = str(gp.ui.xml)
    check(len(list(gp.snaps.values())) == 16 and len(list(sg.snaps.values())) == 9
          and f'id="gear_{gp.guid}"' in xml and 'onClick="Global/gearClicked"' in xml and 'id="doors_2"' in xml
          and 'onClick="Global/doorsClicked"' in xml and [a.name for a in gp.ui.assets.values()] == ["turnccw", "doors"]
          and [a.name for a in sg.ui.assets.values()] == ["turncw"] and 'doors_' not in str(sg.ui.xml)
          and [m.label for m in gp.menu.values()] == ["Turn gear", "Blockers 2 open/close"]
          and g.doorA.interactable is False,
          "a gear plate carries a snap point per tile and its turn button (+ the doors button and menu on a numbered "
          "gear); blockers can't be clicked")
    lua.execute(f'gearClicked(nil, nil, "gear_{gp.guid}")')
    r, off, h = g.rider, g.offGear, g.held
    # counter-clockwise seen from above, 270 degrees: an offset (dx, dz) ends at (dz, -dx)
    check(abs(r.pos.x - (10 + 0.5 * T)) < 1e-6 and abs(r.pos.z - (20 - 1.5 * T)) < 1e-6 and abs(r.pos.y - 1.03) < 1e-9
          and r.rot.y == 33 and r.locked is False and r.lockLog == "true false "
          and abs(gp.rot.y - 90) < 1e-6 and not g.turningGears[gp.guid],
          f"turning a counter-clockwise gear carries a Pokemon 270 degrees round it, facing kept, unlocked after "
          f"({r.pos.x:.3f}, {r.pos.z:.3f}; plate yaw {gp.rot.y:.1f})")
    check(abs(off.pos.x - (10 + 2.5 * T)) < 1e-9 and abs(h.pos.x - 10) < 1e-9 and h.lockLog is None,
          "a Pokemon off the gear, or held in a hand, stays where it is")
    lua.execute("smallRider = rider; rider.pos = Vector(-10, 1.03, 3.24875); turnGear(smallGear)")
    check(abs(r.pos.x - (-10 - T)) < 1e-6 and abs(r.pos.z - 0) < 1e-6 and abs(sg.rot.y - 270) < 1e-6,
          f"a clockwise gear turns the other way: from its far side to its left ({r.pos.x:.3f}, {r.pos.z:.3f})")
    lua.execute('doorsClicked(nil, nil, "doors_2")')
    dA, dB, dC = g.doorA, g.doorB, g.doorC
    check(abs(dA.pos.x - (1 - T)) < 1e-6 and json.loads(dA.memo)["open"] is True and abs(dB.pos.y - 1.37) < 1e-9
          and abs(dC.pos.z) < 1e-9,
          "the doors button opens its own blockers (sliding into the wall), not the others")
    lua.execute('doorsClicked(nil, nil, "doors_3"); gearPlate.menu[2].fn("Red")')
    check(abs(dA.pos.x - 1) < 1e-6 and json.loads(dA.memo)["open"] is False and abs(dB.pos.y - (1.37 - 1.94)) < 1e-6,
          "pressed again they close; a blocker with no wall beside it sinks into the floor")

    # Avia: 5 flags and 16 floating platforms on their first tiles (picked before Greenleaf: Avia is deeper than the
    # play area and stretches the table; Greenleaf puts it back for the stand checks further on)
    lua.execute('for _, o in ipairs(objects) do if o.hasTag("ArenaPiece") then o.destroyed = true end end')
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", row("Avia"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new if s.data.Tags[1] not in ("TurnTrack", "TurnToken")]
    aidx = json.loads((REPO / "arenas" / "index.json").read_text(encoding="utf-8"))["Avia"]
    plats = [(s, json.loads(s.data.Memo)) for s in new if s.data.Tags[1] == "Platform"]
    T = 3.24875
    first = next((m for s, m in plats if abs(s.position.x - 0.01 + 4 * T) < 1e-3 and abs(s.position.z + 0.01 - 6 * T) < 1e-3), None)
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith(board("avia", "mesh"))
          and kinds.count("Flag") == 5 and len(plats) == 16
          and all(s.data.Nickname == "Floating platform" and s.data.Locked and m["at"] == 1 and len(m["route"]) == 2
                  and abs(m["y"] - s.position.y) < 1e-6 and abs(s.position.y - 0.961 - 3.3147) < 1e-3 for s, m in plats)
          and first is not None and all(abs(a - b) < 1e-3 for a, b in zip(first["route"][0] + first["route"][1], [T, 0, 0, T, 0, -T]))
          and sorted(m["arms"] for _, m in plats) == sorted(["ne", "nw", "se", "sw"] * 4) and first["arms"] == "sw"
          and all(s.data.CustomMesh.DiffuseURL.endswith("props/platform-v1.jpg") for s, _ in plats)
          and len(aidx["snaps"]) == 205 and aidx["turns"] == 10 and backdrop(new, "misc/clouds-placeholder-v1.jpg"),
          "picking Avia: its board, 5 flags, 16 floating platforms on their first tiles level with the low ground (the "
          "one at row 2 col 4 goes right then down: its arrow's arms point left and down from the bend), a snap point on every land tile, the clouds table, 10 turns")
    # Greenleaf: 4 flags, 4 traps, 3 flowers (each with its 3 spots), the grass bridge's two halves inside their hedges
    lua.execute('for _, o in ipairs(objects) do if o.hasTag("ArenaPiece") then o.destroyed = true end end')   # the stand-ins
    n = len(calls.spawned)
    g.refreshMaps("White")
    g.mapPick(player, "-1", row("Greenleaf"))
    new = [calls.spawned[i] for i in range(n + 1, len(calls.spawned) + 1)]
    kinds = [s.data.Tags[1] for s in new if s.data.Tags[1] not in ("TurnTrack", "TurnToken")]   # (a new turn track too)
    gidx = json.loads((REPO / "arenas" / "index.json").read_text(encoding="utf-8"))["Greenleaf"]
    flowers = {s.data.Nickname: json.loads(s.data.Memo) for s in new if s.data.Tags[1] == "Flower"}
    halves = [(s, json.loads(s.data.Memo)) for s in new if s.data.Tags[1] == "Bridge"]
    red = [[round(v, 3) for v in t] for t in flowers.get("Red flower", {}).get("targets", [])]
    check(kinds[0] == "Board3D" and new[0].data.CustomMesh.MeshURL.endswith(board("greenleaf", "mesh"))
          and kinds.count("Flag") == 4 and kinds.count("Trap") == 4 and sorted(flowers) == ["Blue flower", "Red flower", "Violet flower"]
          and all(len(m["targets"]) == 3 for m in flowers.values()) and len(halves) == 2
          and all(s.data.Nickname == "Grass bridge" and m["tiles"] == 5 and m["group"] == 1 and m["up"] is False
                  and abs(s.position.x - m["x"] - m["sx"]) < 1e-6 and abs(s.position.z - m["z"] - m["sz"]) < 1e-6
                  and abs(abs(m["sz"]) - 3.24875) < 1e-3 and abs(m["hy"] - 2 * 0.9677) < 1e-3 for s, m in halves)
          and sorted(m["lead"] for _, m in halves) == [False, True] and halves[0][1]["sz"] == -halves[1][1]["sz"]
          and len(gidx["snaps"]) == 256 - 53 - 10 - 3 and backdrop(new, "misc/garden-placeholder-v1.jpg"),
          "picking Greenleaf: its board, 4 flags, 4 traps, 3 flowers with 3 spots each, the grass bridge's two halves "
          "closed inside the hedges either side of the creek, snap points on all but the hedges, the creek and the "
          "flowers, the garden table")
    T = 3.24875
    want = [[-T, 0, -2 * T], [3 * T, 0, -2 * T], [3 * T, 0, 0]]
    check(len(red) == 3 and all(abs(a - b) < 2e-3 for t, w in zip(red, want) for a, b in zip(t, w)),
          f"the red flower's spots 1-3 are where the board paints them, from its tile ({red})")

    # the grass bridge: two halves that grow out of their hedges together (a Pokemon on either keeps both open), the
    # arrows on top of the lead half's hedge; a flower flings the Pokemon on it to a free spot at random, in an arc
    lua.execute(r"""
      for _, o in ipairs(objects) do if o.hasTag("ArenaPiece") then o.destroyed = true end end
      function standIn(tags, memo, pos)
        local o = { tags = tags, guid = "gl" .. #objects, menu = {}, snaps = {}, ui = {}, pos = pos, rot = Vector(0, 0, 0) }
        o.memo = memo and JSON.encode(memo) or ""
        o.getPosition = function() return o.pos end
        o.setPosition = function(p)
          o.pos = Vector(p[1] or p.x, p[2] or p.y, p[3] or p.z)
          o.top = math.max(o.top or -1e9, o.pos.y)
          o.moves = (o.moves or 0) + 1
        end
        o.setPositionSmooth = function(p) o.pos = p end
        o.positionToLocal = function(v) return Vector(v.x - o.pos.x, v.y - o.pos.y, v.z - o.pos.z) end
        o.getRotation = function() return o.rot end
        o.setLock = function(l) o.locked = l; o.lockLog = (o.lockLog or "") .. tostring(l) .. " " end
        o.getLock = function() return o.locked or false end
        o.getSnapPoints = function() return o.snaps end
        o.setSnapPoints = function(s) o.snaps = s end
        o.setDescription = function(d) o.desc = d end
        o.clearContextMenu = function() o.menu = {} end
        o.addContextMenuItem = function(label, fn) o.menu[#o.menu + 1] = { label = label, fn = fn } end
        o.UI = { setXml = function(x) o.ui.xml = x end, setCustomAssets = function(a) o.ui.assets = a end }
        o.hasTag = function(t) for _, x in ipairs(o.tags) do if x == t then return true end end return false end
        objects[#objects + 1] = o
        return o
      end
      getObjectFromGUID = function(guid) for _, o in ipairs(objects) do if o.guid == guid and not o.destroyed then return o end end end
      local T = 3.24875
      grassN = standIn({ "Bridge", "ArenaPiece" }, { up = false, x = 200, y = 1.3824, z = T / 2, sx = 0, sz = T, tiles = 5,
        tile = T, group = 1, lead = true, hy = 1.9354 }, Vector(200, 1.3824, 1.5 * T))
      grassS = standIn({ "Bridge", "ArenaPiece" }, { up = false, x = 200, y = 1.3824, z = -T / 2, sx = 0, sz = -T, tiles = 5,
        tile = T, group = 1, lead = false, hy = 1.9354 }, Vector(200, 1.3824, -1.5 * T))
      for _, o in ipairs({ grassN, grassS }) do o.locked = true; onObjectSpawn(o) end
    """)
    gn, gs = g.grassN, g.grassS
    at = lambda o, z: abs(o.pos.x - 200) < 1e-6 and abs(o.pos.y - 1.3824) < 1e-6 and abs(o.pos.z - z) < 1e-6
    check(len(list(gn.snaps.values())) == 0 and len(list(gs.snaps.values())) == 0
          and 'position="0 0 -196"' in str(gn.ui.xml) and 'onClick="Global/bridgeClicked"' in str(gn.ui.xml) and gs.ui.xml is None
          and [m.label for m in gs.menu.values()] == ["Open the bridge", "Close the bridge"] and str(gn.desc).startswith("Closed."),
          "closed, the grass halves have no snap points (none hidden in the hedges); the lead's arrows sit on top of its "
          "hedge; Open / Close in the menu")
    g.bridgeClicked(player)
    check(at(gn, T / 2) and at(gs, -T / 2) and gn.moves == 120 and gs.moves == 120 and not g.movingBridges[gn.guid]
          and len(list(gn.snaps.values())) == 5 and len(list(gs.snaps.values())) == 5 and 'position="0 325 -196"' in str(gn.ui.xml)
          and json.loads(gs.memo)["up"] and str(gs.desc).startswith("Open:"),
          f"its arrows grow both halves out of their hedges to meet over the creek, a little each frame ({gn.moves} "
          f"steps), with a snap point on each tile; the arrows stay on the hedge")
    lua.execute(r"""
      onGrass = standIn({ "Pokemon" }, nil, Vector(200 + 2 * 3.24875, 1.40, -3.24875 / 2))
    """)
    g.bridgeClicked(player)
    both_open = at(gn, T / 2) and at(gs, -T / 2)
    lua.execute("onGrass.destroyed = true")
    g.bridgeClicked(player)
    check(both_open and at(gn, 1.5 * T) and at(gs, -1.5 * T) and len(list(gn.snaps.values())) == 0
          and 'position="0 0 -196"' in str(gn.ui.xml) and not json.loads(gn.memo)["up"],
          "with a Pokemon on one half both stay open; once it's gone the arrows draw both back into their hedges")
    gs.menu[1].fn("Red")
    check(at(gn, T / 2) and at(gs, -T / 2), "right-click > Open the bridge on either half opens both")

    lua.execute(r"""
      flower = standIn({ "Flower", "ArenaPiece" }, { targets = { { 3.24875, 0, 0 }, { 0, 0, 3.24875 }, { -3.24875, 0.9677, 0 } },
        tile = 3.24875 }, Vector(100, 1.3824, 0))
      flower.locked = true
      onObjectSpawn(flower)
      flung = standIn({ "Pokemon" }, nil, Vector(100, 1.3824 + 0.06 + 0.01, 0))
      flung.rot = Vector(0, 77, 0)
      blockMon = standIn({ "Pokemon" }, nil, Vector(100 + 3.24875, 1.40, 0.4))
      gift = standIn({ "Gift" }, nil, Vector(100, 1.45, 3.24875 - 0.5))
      flingOk = flowerClicked(nil, nil, "fling_" .. flower.guid)
    """)
    fl, mon = g.flower, g.flung
    check(len(list(fl.snaps.values())) == 1 and abs(fl.snaps[1].position[2] - 0.08) < 1e-9
          and f'id="fling_{fl.guid}"' in str(fl.ui.xml) and 'onClick="Global/flowerClicked"' in str(fl.ui.xml)
          and fl.ui.assets[1].url.endswith("ui/icons/fling-v3.png") and [m.label for m in fl.menu.values()] == ["Fling Pokémon"]
          and str(fl.desc).startswith("Flower."),
          "a flower carries its tile's snap point, the fling button and menu, and its description")
    check(abs(mon.pos.x - (100 - T)) < 1e-6 and abs(mon.pos.z) < 1e-6 and abs(mon.pos.y - (1.3824 + 0.9677 + 0.01)) < 1e-6
          and mon.rot.y == 77 and mon.lockLog == "true false " and not g.flinging[fl.guid],
          f"its button throws the Pokemon on it to the one free spot (the others hold a Pokemon and a gift box), at the "
          f"same height above the ground, facing kept, unlocked after ({mon.pos.x:.3f}, {mon.pos.y:.3f}, {mon.pos.z:.3f})")
    check(mon.top > 1.3824 + 3.5, f"it flies there in an arc (top {mon.top:.2f}), no jump cut")
    lua.execute(r"""
      blockMon.destroyed = true; gift.destroyed = true
      landed = {}
      for i = 1, 40 do
        flung.pos = Vector(100, 1.3824 + 0.07, 0)
        flingFromFlower(flower)
        local k = string.format("%.2f,%.2f", flung.pos.x - 100, flung.pos.z)
        landed[k] = (landed[k] or 0) + 1
      end
    """)
    spots = sorted(dict(g.landed.items()))
    check(spots == ["-3.25,0.00", "0.00,3.25", "3.25,0.00"], f"with all three free, it lands on each of them at random ({spots})")
    lua.execute(r"""
      flung.pos = Vector(100, 1.3824 + 0.07, 0)
      s1 = standIn({ "Pokemon" }, nil, Vector(100 + 3.24875, 1.40, 0))
      s2 = standIn({ "Pokemon" }, nil, Vector(100, 1.40, 3.24875))
      s3 = standIn({ "Pokemon" }, nil, Vector(100 - 3.24875, 2.36, 0))
      allTaken = flingFromFlower(flower)
      s1.destroyed = true; s2.destroyed = true; s3.destroyed = true
      flung.pos = Vector(130, 1.40, 0)
      noneOn = flingFromFlower(flower)
      flung.destroyed = true
    """)
    check(g.allTaken is False and g.noneOn is False, "with all three spots taken, or nobody on the flower, nothing is thrown")

    # Avia's platforms: one glides along its L, round the bend, to the other end and back, carrying the Pokemon on it
    lua.execute(r"""
      for _, o in ipairs(objects) do if o.hasTag("ArenaPiece") then o.destroyed = true end end
      local T = 3.24875
      plat = standIn({ "Platform", "ArenaPiece" }, { route = { { T, 0, 0 }, { T, 0, -T } }, at = 1, x = 300, y = 4.28, z = 0,
        tile = T, arms = "sw" }, Vector(300, 4.28, 0))
      plat.locked = true
      onObjectSpawn(plat)
      trail, offL = {}, false
      local set = plat.setPosition
      plat.setPosition = function(p)
        set(p)
        trail[#trail + 1] = { plat.pos.x, plat.pos.z }
        -- along the L: first along x (z stays 0), then along -z (x stays 300 + T); never cutting the corner
        local x, z = plat.pos.x - 300, plat.pos.z
        if not ((math.abs(z) < 1e-9 and x <= T + 1e-9) or (math.abs(x - T) < 1e-9 and z <= 1e-9)) then offL = true end
      end
      onPlat = standIn({ "Pokemon" }, nil, Vector(300.3, 4.35, 0.2))
      onPlat.rot = Vector(0, 55, 0)
      besides = standIn({ "Pokemon" }, nil, Vector(300 - 3.24875, 4.35, 0))
      glideOk = platformClicked(nil, nil, "glide_" .. plat.guid)
    """)
    pl, rider, other = g.plat, g.onPlat, g.besides
    check(len(list(pl.snaps.values())) == 1 and abs(pl.snaps[1].position[2] - 0.02) < 1e-9
          and f'id="glide_{pl.guid}"' in str(pl.ui.xml) and 'onClick="Global/platformClicked"' in str(pl.ui.xml)
          and 'image="glide-sw"' in str(pl.ui.xml) and pl.ui.assets[1].url.endswith("ui/icons/glide-sw-v3.png")
          and [m.label for m in pl.menu.values()] == ["Move platform"]
          and str(pl.desc).startswith("Floating platform."),
          "a platform carries its tile's snap point, its button (an L icon the shape of its track), the menu and its "
          "description")
    check(abs(pl.pos.x - (300 + T)) < 1e-6 and abs(pl.pos.z + T) < 1e-6 and abs(pl.pos.y - 4.28) < 1e-9
          and json.loads(pl.memo)["at"] == 3 and pl.moves == 120 and not g.offL and not g.gliding[pl.guid]
          and abs(rider.pos.x - (300.3 + T)) < 1e-6 and abs(rider.pos.z - (0.2 - T)) < 1e-6 and abs(rider.pos.y - 4.35) < 1e-9
          and rider.rot.y == 55 and rider.lockLog == "true false " and abs(other.pos.x - (300 - T)) < 1e-9
          and other.lockLog is None,
          f"its button glides it along its rail, round the bend, to the far end ({pl.moves} steps), the Pokemon on it "
          f"carried along (facing kept, unlocked after), the one beside it left alone")
    lua.execute('trail = {}; plat.menu[1].fn("Red")')
    check(abs(pl.pos.x - 300) < 1e-6 and abs(pl.pos.z) < 1e-6 and json.loads(pl.memo)["at"] == 1 and not g.offL
          and abs(rider.pos.x - 300.3) < 1e-6 and abs(rider.pos.z - 0.2) < 1e-6,
          "pressed again (right-click > Move platform) it glides back the same way, round the bend, with its rider")
    lua.execute("plat.destroyed = true; onPlat.destroyed = true; besides.destroyed = true")

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
    check(abs(card.position.x - (-18.8)) < 0.01 and abs(card.position.z - (-26.4 - 4.5856 - lift_z)) < 0.01
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
          and abs(sk.position.x - (-18.8)) < 0.01 and abs(sk.position.z - (-26.4 - 6.9252 - lift_z)) < 0.01,
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
    check(abs(calls.spawned[n + 3].position.x - (-14.1)) < 0.01, "the next item card takes the next column")
    g.spawnCard("items", "Sitrus Berry", "Green")
    far = calls.spawned[n + 4]
    check(abs(far.position.x - 18.8) < 0.01 and abs(far.position.z - (26.4 + 4.5856 + lift_z)) < 0.01 and far.rotation.y == 450,
          "a far-side seat (Green) uses the far stand, starting from its own left")
    snaps = g.standSnapPoints(6)
    first = snaps[1].position
    check(len(snaps) == 18 and len(g.standSnapPoints(9)) == 27 and abs(first[2] - (2.2198 + 0.55 * 0.9589)) < 0.01
          and abs(first[1] - (-17.625)) < 1e-9 and abs(g.standSnapPoints(9)[1].position[1] - (-18.8)) < 1e-9 and snaps[1].rotation_snap,
          "card snap points per stand: 3 rows of 6 (or 9), lifted off the slope, snapping rotation")
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

    # HP signs: each pedestal's sign shows the HP of its Pokemon; typing sets or changes it. A Pokemon taken off its
    # pedestal leaves a phantom there (and the sign keeps its HP); put on another pedestal, that one takes it over.
    lua.execute(r"""
      local keep = {}   -- clear the Pokemon spawned by earlier checks (one is on pedestal 1)
      for _, o in ipairs(objects) do if not (o.hasTag and o.hasTag("Pokemon")) then keep[#keep + 1] = o end end
      objects = keep
      pedestalUI = {}
      south = {}
      for _, p in ipairs(standPedestals(southStand)) do south[#south + 1] = p.obj end
      function mon(name, guid, ped)
        local m = stub({ memo = JSON.encode({ pokemon = name }), guid = guid, name = "Custom_Model", tags = { "Pokemon" } })
        m.pos = ped and (ped.getPosition() + Vector(0, 0.25, 0)) or Vector(0, 3.3, 0)
        m.getPosition = function() return m.pos end
        m.setPosition = function(v) m.pos = Vector(v[1] or v.x, v[2] or v.y, v[3] or v.z) end
        m.getName = function() return name end
        return m
      end
      hpFig = mon("Gengar", "abc123", south[1])
      refreshPedestals()
    """)
    h, gmax = g.hpFig, json.loads((REPO / "data" / "pokemon.json").read_text(encoding="utf-8"))["Gengar"]["hp"]
    peds = g.south

    def ui(i):
        root = ET.fromstring("<root>" + (peds[i].uiXml or "") + "</root>")
        return {e.get("id"): e for e in root.iter() if e.get("id")}, [p for p in root if p.tag == "Panel"], root

    ids, panels, root = ui(1)
    p1 = peds[1].guid
    f1 = ids[f"hpIn_{p1}_F"]
    check(len(panels) == 2 and json.loads(h.memo).get("hp") == gmax and f1.get("text") == str(gmax)
          and panels[0].get("active") == "true" and ui(2)[1][0].get("active") == "false"
          and json.loads(peds[1].memo)["mon"] == "abc123",
          f"pedestal 1's sign shows the Gengar on it ({gmax}/{gmax}), which is now its Pokemon; empty pedestals' signs are blank")
    check((panels[0].get("rotation"), panels[1].get("rotation")) == ("-90 0 0", "90 0 180")
          and panels[0].get("position") == "0 -3 -280" and panels[1].get("position") == "0 3 -280",
          "a label on each face of the sign floating above the pedestal, facing out")
    bench = ids.get(f"bench_{p1}")
    assets = {a.name: a.url for a in peds[1].assets.values()}
    check(bench is not None and bench.get("onClick") == "Global/benchClicked" and bench.get("position") == "120 -4 -280"
          and bench.get("rotation") == "-90 0 0" and bench.get("tooltip") is None
          and assets.get("bench", "").endswith("ui/icons/spectate-v3.png") and "phantom" not in assets
          and not any(e.get("image") == "phantom" for e in root.iter("Image")),
          "while the stand holds 9, a bench button stands beside the sign, facing its player; no phantom while Gengar stands on it")

    def hp():
        return json.loads(h.memo)["hp"]
    g.hpEdited(player, "-35", f"hpIn_{p1}_F")
    check(hp() == gmax - 35 and ui(1)[0][f"hpIn_{p1}_B"].get("text") == str(gmax - 35),
          "typing -35 on the sign takes 35 HP from that Pokemon and updates both faces")
    g.hpEdited(player, "+500", f"hpIn_{p1}_B")
    check(hp() == gmax, "+500 heals only up to the max")
    g.hpEdited(player, "120/230", f"hpIn_{p1}_F")
    check(hp() == 120, "typing a number sets it (a trailing /max is ignored)")
    g.hpEdited(player, "0", f"hpIn_{p1}_F")
    check(hp() == 0 and ui(1)[0][f"hpIn_{p1}_F"].get("textColor") == "#FF6B6B", "0 HP turns the number red")
    g.hpEdited(player, "lots", f"hpIn_{p1}_F")
    check(hp() == 0 and ui(1)[0][f"hpIn_{p1}_F"].get("text") == "0", "something that isn't a number changes nothing")

    lua.execute("hpFig.pos = Vector(0, 3.3, 0); refreshPedestals()")   # deployed on the board
    ids, panels, root = ui(1)
    ph = [e for e in root.iter("Image") if e.get("image") == "phantom"]
    assets = {a.name: a.url for a in peds[1].assets.values()}
    check(len(ph) == 1 and ph[0].get("rotation") == "-90 0 0" and ph[0].get("position") == "0 0 -138"
          and ph[0].get("raycastTarget") == "false" and assets.get("phantom", "").endswith("figures/gengar.webp")
          and panels[0].get("active") == "true" and ids[f"hpIn_{p1}_F"].get("text") == "0"
          and json.loads(peds[1].memo)["mon"] == "abc123",
          "taken to the board, Gengar leaves a see-through phantom of its picture on its pedestal, and the sign keeps its HP")
    n = len(calls.spawned)
    g.spawnPokemon("Absol", "White")
    check(abs(calls.spawned[n + 1].position.x - (-14.1)) < 0.01, "a new Pokemon skips the phantom's pedestal")
    lua.execute("objects[#objects].destroyed = true")
    lua.execute("hpFig.pos = south[3].getPosition() + Vector(0, 0.25, 0); refreshPedestals()")   # onto pedestal 3
    check(ui(3)[1][0].get("active") == "true" and json.loads(peds[3].memo)["mon"] == "abc123"
          and "mon" not in json.loads(peds[1].memo) and ui(1)[1][0].get("active") == "false"
          and not any(e.get("image") == "phantom" for e in ui(1)[2].iter("Image")),
          "put on another pedestal, that one takes it over (its sign shows the HP); the first is empty again")
    lua.execute("hpFig.pos = south[1].getPosition() + Vector(0, 0.25, 0); refreshPedestals()")
    lua.execute("other = mon('Abra', 'abra01', nil); hpFig.pos = Vector(0, 3.3, 0); refreshPedestals()")
    lua.execute("other.pos = south[1].getPosition() + Vector(0, 0.25, 0); refreshPedestals()")
    check(json.loads(peds[1].memo)["mon"] == "abra01", "another Pokemon put on a phantom's pedestal takes it over")
    lua.execute("other.destroyed = true; hpFig.pos = south[1].getPosition() + Vector(0, 0.25, 0); refreshPedestals()")
    lua.execute("hpFig.destroyed = true; refreshPedestals()")
    check("mon" not in json.loads(peds[1].memo) and ui(1)[1][0].get("active") == "false",
          "a pedestal whose Pokemon is deleted is empty again")

    # benching: the button sends a pedestal's Pokemon to its player's half of the spectator stand; once 3 of the 9
    # are sat out, their pedestals and cards go and the other 6 slide to the usual spacing with their Pokemon and cards
    lua.execute(r"""
      gen = mon("Gengar", "gen001", nil)
      gen.pos = Vector(5, 1.4, 5)   -- out on the board: benched from there
      south[1].memo = JSON.encode({ mon = "gen001" })
      abra = mon("Abra", "abra02", south[3])
      function card(x)
        local c = stub({ type = "Card", tags = { "Item" } })
        c.pos = southStand.positionToWorld(Vector(x, STAND.cards.items.y, STAND.cards.items.z))
        c.getPosition = function() return c.pos end
        c.setPosition = function(v) c.pos = Vector(v[1] or v.x, v[2] or v.y, v[3] or v.z) end
        return c
      end
      for _, o in ipairs(objects) do if o.type == "Card" then o.destroyed = true end end   -- the cards dealt earlier
      card3, card4 = card(-9.4), card(-4.7)
      genItem = card(-18.8)
      genSkill = card(-18.8)
      genSkill.tags = { "WarriorSkill" }
      genSkill.pos = southStand.positionToWorld(Vector(-18.8, STAND.cards.skills.y, STAND.cards.skills.z))
      refreshPedestals()
      benchClicked(nil, nil, "bench_" .. south[1].guid)
    """)
    gp, gi, gs = g.gen.pos, g.genItem.pos, g.genSkill.pos
    check(abs(gi.x - 39.65) < 1e-6 and abs(gi.z - (-12.5)) < 1e-6 and abs(gs.x - 39.65) < 1e-6 and abs(gs.z - (-12.5)) < 1e-6
          and abs(gs.y - (0.961 + 2.6 + 0.02)) < 1e-6 and abs(gi.y - (0.961 + 2.6 + 0.05)) < 1e-6
          and g.genItem.rot.y == 0 and g.genItem.locked is False
          and json.loads(g.gen.memo)["cards"] == [g.genSkill.guid, g.genItem.guid],
          "its cards fly along and lie stacked beside its seat (the skill below, the item on top), reading from the board side")
    check(abs(gp.x - 37.1) < 1e-6 and abs(gp.z - (-12.5)) < 1e-6 and abs(gp.y - (0.961 + 2.6 + 0.25 + 0.02)) < 1e-6
          and json.loads(g.south[1].memo).get("benched") and "mon" not in json.loads(g.south[1].memo)
          and g.gen.locked is False and not g.flying["gen001"] and f"bench_{p1}" not in (peds[1].uiXml or ""),
          "the bench button flies Gengar to the near half's first spectator seat (the player's end); its pedestal is sat out")
    lua.execute('benchClicked(nil, nil, "bench_" .. south[2].guid)')   # an empty pedestal is just sat out
    check(json.loads(g.south[2].memo).get("benched") and len(list(g.pedsOf(g.southStand).values())) == 9,
          "an empty pedestal can be sat out too; with 2 out the stand still holds 9")
    lua.execute('benchClicked(nil, nil, "bench_" .. south[4].guid)')
    xs = list(g.pedsOf(g.southStand).values())
    six = [-17.625, -10.575, -3.525, 3.525, 10.575, 17.625]
    check(len(xs) == 6 and all(abs(a - b) < 1e-6 for a, b in zip(xs, six)) and g.south[1].destroyed and g.south[4].destroyed
          and g.card4.destroyed and not g.card3.destroyed and abs(g.card3.pos.x - (-17.625)) < 1e-6
          and not g.genItem.destroyed and abs(g.genItem.pos.x - 39.65) < 1e-6
          and abs(g.abra.pos.x - (-17.625)) < 1e-6 and json.loads(g.southStand.memo)["slots"] == 6
          and len(g.southStand.snaps) == 18 and not g.sliding[g.southStand.guid]
          and all("bench_" not in (p.uiXml or "") for p in (g.south[3], g.south[5])),
          "the third sat out: their pedestals go (and cards left in their columns; Gengar's stay with it); the other 6 "
          "slide to the usual spacing with Abra and its card")
    n = len(calls.spawned)
    g.spawnCard("items", "Sitrus Berry", "White")
    check(abs(calls.spawned[n + 1].position.x - (-10.575)) < 0.01, "cards now go in the 6 columns (the first is Abra's)")

    # a new map: the stands go back to 9 and everyone comes home (the benched to the free pedestals)
    lua.execute("resetStands()")
    xs = list(g.pedsOf(g.southStand).values())
    check(len(xs) == 9 and all(abs(a - b) < 1e-6 for a, b in zip(xs, nine)) and json.loads(g.southStand.memo)["slots"] == 9
          and len(g.southStand.snaps) == 27 and abs(g.abra.pos.x - (-9.4)) < 1e-6 and abs(g.card3.pos.x - (-9.4)) < 1e-6
          and abs(g.gen.pos.x - (-18.8)) < 1e-6 and abs(g.gen.pos.z - (-28.0)) < 1e-6
          and all("home" not in json.loads(p.obj.memo or "{}") for p in g.standPedestals(g.southStand).values())
          and "home" not in json.loads(g.gen.memo),
          "picking a map: the stand goes back to 9 just as it was: Abra (and its card) slides back to slot 3, the sat-out "
          "pedestals reappear in slots 1, 2 and 4, and Gengar flies home to slot 1")
    lift_y, lift_z = 0.15 * __import__("math").cos(__import__("math").radians(16.492)), 0.15 * __import__("math").sin(__import__("math").radians(16.492))
    gi, gs = g.genItem.pos, g.genSkill.pos
    check(abs(gi.x - (-18.8)) < 1e-6 and abs(gi.z - (-26.4 - 4.5856 - lift_z)) < 0.01 and abs(gi.y - (0.961 + 2.2198 + lift_y)) < 0.01
          and abs(gs.x - (-18.8)) < 1e-6 and abs(gs.z - (-26.4 - 6.9252 - lift_z)) < 0.01 and g.genItem.rot.y == 270
          and "cards" not in json.loads(g.gen.memo),
          "and its cards fly back with it, each to its own row in its old column")

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
      local function hand(c, x, z, sx, sz, sy)
        local h = { color = c, pos = Vector(x, 3.29, z), scale = Vector(sx, sy or 11.9, sz), rot = Vector(0, 0, 0) }
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
          hand(t.data.FogColor, t.position[1], t.position[3], t.data.Transform.scaleX, t.data.Transform.scaleZ, t.data.Transform.scaleY)
          return
        end
        return realSpawn(t)
      end
    """)
    changed = g.ensureHandZones()
    live = {h.color: h for h in g.Hands.getHands().values()}
    red, pink = live.get("Red"), live.get("Pink")
    edge_z, edge_x = 75.3 / 2 + 2.28, 110.3 / 2 + 2.28   # centres where the big zones' were (same spacebar camera)
    check(changed and sorted(live) == sorted(["Red", "White", "Blue", "Green", "Orange", "Yellow", "Pink", "Purple"])
          and [h.data.FogColor for h in g.spawnedHands.values()] == ["Green"]
          and abs(red.pos.z + edge_z) < 1e-6 and red.pos.y == 2.85 and red.pos.x == -9.48
          and abs(pink.pos.x - edge_x) < 1e-6 and pink.rot.y == 270,
          "TTS's default hand zones are moved just past the table's edge (Brown/Teal removed, missing Green spawned)")
    check(all(max(h.scale.x, h.scale.y, h.scale.z) <= 0.1 + 1e-9 for h in live.values()),
          "the hand zones are tiny (0.1 a side), so nothing dragged near the edge catches on them")
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
      pStatue = obj({ "Statue", "ArenaPiece" })
      pFlower = obj({ "Flower", "ArenaPiece" })
      pieceSetup(pBoard)
      pieceSetup(pPillar)
      delFlag = onPlayerAction(nil, Player.Action.Delete, { pCard, pFlag })
      cutStand = onPlayerAction(nil, Player.Action.Cut, { pStand })
      delTree = onPlayerAction(nil, Player.Action.Delete, { pTree, pCard })
      pickCard = onPlayerAction(nil, Player.Action.PickUp, { pCard })
      pickTree = onPlayerAction(nil, Player.Action.PickUp, { pTree })
      delStatue = onPlayerAction(nil, Player.Action.Delete, { pStatue })
      pickStatue = onPlayerAction(nil, Player.Action.PickUp, { pStatue })
      delFlower = onPlayerAction(nil, Player.Action.Delete, { pFlower })
    """)
    check(g.pBoard.interactable is False and g.pPillar.interactable is False,
          "the board and the pillars can't be clicked, selected or deleted (not interactive)")
    check(g.delFlag is False and g.cutStand is False and g.delFlower is False,
          "deleting a flag or a flower, or cutting a stand, is refused")
    check(g.delStatue is False and g.pickStatue is True, "a statue can be picked up and moved, not deleted")
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
