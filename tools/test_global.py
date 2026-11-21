"""Offline checks for lua/Global.lua: runs it in real Lua (via lupa) with stand-ins for the TTS API.

Usage:  python -I tools/test_global.py
Checks: the script compiles; onLoad builds well-formed UI XML with unique ids; search finds the right names;
the search panel's result rows get text; spawning creates a figure with the right images; the map list
reads names from a fake map board. (TTS's own Lua, MoonSharp, has quirks real Lua doesn't — still test in TTS.)
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
WebRequest = { get = function(url, cb) calls.url = url; cb({ is_error = false, text = ROSTER_JSON }) end }
JSON = { decode = function(s) return py_json_decode(s) end, encode = function(t) return py_json_encode(t) end }
function print(s) calls.printed[#calls.printed + 1] = s end
function printToAll(s) calls.printed[#calls.printed + 1] = s end
Wait = { frames = function(f) f() end }
local hand = { position = Vector(9.5, 2.9, -28.6), forward = Vector(0, 0, 1), rotation = Vector(0, 0, 0) }
Player = setmetatable({}, { __index = function(_, c)
  return { getHandTransform = function() if c == "White" then return hand end end }
end })
function spawnObjectData(t) calls.spawned[#calls.spawned + 1] = t; return { getName = function() return t.data.Nickname end } end

-- a fake map board with three states
local states = {
  ["2"] = { CustomImage = { ImageURL = "https://pctts.github.io/tts/maps/fontaine.jpg" } },
  ["3"] = { CustomImage = { ImageURL = "https://example.com/uc?id=abc" } },
}
board = {
  getStates = function() return { {}, {} } end,
  getCustomObject = function() return { image = "https://pctts.github.io/tts/maps/terrera-mountain.jpg" } end,
  getData = function() return { CustomImage = { ImageURL = "https://pctts.github.io/tts/maps/terrera-mountain.jpg" }, States = states } end,
  getStateId = function() return 1 end,
  setState = function(id) calls.state = id end,
}
function getAllObjects() return { board } end
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
    g.ROSTER_JSON = (REPO / "figures" / "index.json").read_text(encoding="utf-8")
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

    # UI: well-formed XML, unique ids, icons registered
    xml = calls.xml
    try:
        root = ET.fromstring("<root>" + xml + "</root>")
        ids = [e.get("id") for e in root.iter() if e.get("id")]
        check(len(ids) == len(set(ids)), f"UI XML parses; {len(ids)} ids, all unique")
        bar = next(e for e in root.iter() if e.get("id") == "toolbar")
        check((bar.get("width"), bar.get("height")) == ("38", "114"), f"toolbar is 38 x 114 ({bar.get('width')} x {bar.get('height')})")
    except ET.ParseError as e:
        check(False, f"UI XML parses ({e})")
    check(len(list(calls.assets.values())) == 3, "three toolbar icons registered")
    check(any("roster: 704" in str(p) for p in calls.printed.values()), "roster downloaded (704 names)")

    # search
    names, _ = g.searchRoster("gard", 8)
    names = list(names.values())
    check(names[:2] == ["Gardevoir", "Gardevoir Mega"] and "Zygarde 10%" in names, f"'gard' -> {names}")
    names = list(g.searchRoster("mega z", 8)[0].values())
    check(set(names) == {"Absol Mega Z", "Garchomp Mega Z", "Lucario Mega Z"}, f"'mega z' -> {names}")

    # panel rows get text
    player = lua.table_from({"color": "White"})
    g.dexSearch(player, "char")
    check(calls.attrs["dexRes_White_1.text"] == "Charizard" and calls.attrs["dexRes_White_1.active"] == "true",
          "search panel row 1 shows 'Charizard'")
    check(calls.attrs["dexRes_White_8.active"] == "false", "unused rows hidden")

    # spawning
    g.dexPick(player, "-1", "dexRes_White_1")
    spawned = calls.spawned[1]
    check(spawned is not None and spawned.data.Nickname == "Charizard"
          and spawned.data.CustomImage.ImageURL.endswith("figures/charizard.webp")
          and spawned.data.CustomImage.ImageSecondaryURL.endswith("figures/charizard-back.webp"),
          "clicking row 1 spawns Charizard with front and back images")
    check(abs(spawned.position.z - (-23.6)) < 0.01, "figure appears in front of the White seat")

    # maps
    lst = g.mapList()
    got = [(m.name, bool(m.current)) for m in lst.values()]
    check(got == [("Fontaine", False), ("Map 3", False), ("Terrera Mountain", True)], f"map list -> {got}")
    g.toggleMaps(player)
    check(calls.attrs["maps_White.active"] == "true" and calls.attrs["dex_White.active"] == "false",
          "map button opens the map panel (and closes the search panel)")

    # statuses: arm one, pick up a figure, check tint/description/memo; toggles and clearing
    lua.execute(r"""
      fig = { memo = "", tint = nil, desc = nil, type = "Figurine", name = "Figurine_Custom",
        hasTag = function(t) return t == "Pokemon" end, getLock = function() return false end,
        getName = function() return "Garchomp" end,
        setColorTint = function(c) fig.tint = c end, setDescription = function(d) fig.desc = d end }
      setmetatable(fig, { __index = function(t, k) return rawget(t, k) end })
      board_obj = { getLock = function() return true end }
    """)
    fig = g.fig
    player.broadcast = lambda *a: None
    g.toggleStatus(player)
    check(calls.attrs["status_White.active"] == "true", "swirl button opens the status panel")
    g.statusPick(player, "-1", "statusRes_White_burn")
    check(g.armed["White"] == "burn", "picking Burned arms it")
    g.onObjectPickUp("White", g.board_obj)
    check(g.armed["White"] == "burn", "picking up a locked object (the board) doesn't use it")
    g.onObjectPickUp("White", fig)
    tint = fig.tint
    check(g.armed["White"] is None and tint.r > 0.9 and tint.b < 0.5, f"pick-up applies it: orange tint ({tint.r:.2f}, {tint.g:.2f}, {tint.b:.2f})")
    check(fig.desc == "Status: Burned" and '"burn"' in fig.memo, f"description and memo record it ({fig.desc})")
    g.statusPick(player, "-1", "statusRes_White_confused"); g.onObjectPickUp("White", fig)
    check(fig.desc == "Status: Burned, Confused", "Confused stacks on Burned")
    g.statusPick(player, "-1", "statusRes_White_paralysis"); g.onObjectPickUp("White", fig)
    check(fig.desc == "Status: Paralyzed, Confused", "a new main status replaces the old one")
    g.statusPick(player, "-1", "statusRes_White_clear"); g.onObjectPickUp("White", fig)
    check(fig.desc == "" and fig.tint.r == 1 and fig.tint.b == 1, "Clear all removes statuses and tint")
    g.statusPick(player, "-1", "statusRes_White_drowsy"); g.toggleDex(player)
    check(g.armed["White"] is None, "switching panels cancels a waiting status")

    print("\nall checks passed" if not failures else f"\n{len(failures)} check(s) failed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
