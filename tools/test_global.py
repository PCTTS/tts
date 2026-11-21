"""Offline checks for lua/Global.lua: runs it in real Lua (via lupa) with stand-ins for the TTS API.

Usage:  python -I tools/test_global.py
Checks: the script compiles; onLoad builds well-formed UI XML with unique ids; search finds the right names;
the search panel's result rows get text; spawning creates a figure (or a card in the player's hand) with the
right images; the map list reads names from a fake map board; statuses arm, stack, replace and clear; the
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
  cb({ is_error = false, text = url:find("cards/", 1, true) and CARDS_JSON or ROSTER_JSON })
end }
JSON = { decode = function(s) return py_json_decode(s) end, encode = function(t) return py_json_encode(t) end }
function print(s) calls.printed[#calls.printed + 1] = s end
function printToAll(s) calls.printed[#calls.printed + 1] = s end
Wait = { frames = function(f) f() end }
Player = setmetatable({}, { __index = function(_, c)
  return { color = c, steam_name = c .. "Player", broadcast = function(msg) calls.broadcast = msg end }
end })
Color = { fromString = function(c)
  return ({ Red = { r = 0.856, g = 0.1, b = 0.094 }, Blue = { r = 0.118, g = 0.53, b = 1 } })[c] or { r = 1, g = 1, b = 1 }
end }
objects = {}
local function stub(o)
  o.hasTag = o.hasTag or function(tag) for _, t in ipairs(o.tags or {}) do if t == tag then return true end end return false end
  o.getLock = o.getLock or function() return o.locked or false end
  o.getStates = o.getStates or function() return nil end            -- every real TTS object has these
  o.getCustomObject = o.getCustomObject or function() return {} end
  objects[#objects + 1] = o
  return o
end
-- team stands: near (south) at z = -26.4 facing the near player, far (north) turned 180 degrees
local function makeStand(z, yaw)
  local s = { tags = { "Stand" }, type = "Generic", locked = true }
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
  local kind = t.data.Name == "CardCustom" and "Card" or (t.data.Name == "Figurine_Custom" and "Figurine" or "Generic")
  return stub({ tags = t.data.Tags, type = kind, getName = function() return t.data.Nickname end,
    getPosition = function() return t.position end })
end

-- a fake map board with three states
local states = {
  ["2"] = { CustomImage = { ImageURL = "https://pctts.github.io/tts/maps/fontaine.jpg" } },
  ["3"] = { CustomImage = { ImageURL = "https://example.com/uc?id=abc" } },
}
board = {
  type = "Figurine", locked = true, getPosition = function() return Vector(0, -30, 0) end,
  getStates = function() return { {}, {} } end,
  getCustomObject = function() return { image = "https://pctts.github.io/tts/maps/terrera-mountain.jpg" } end,
  getData = function() return { CustomImage = { ImageURL = "https://pctts.github.io/tts/maps/terrera-mountain.jpg" }, States = states } end,
  getStateId = function() return 1 end,
  setState = function(id) calls.state = id end,
}
stub(board)
function getAllObjects() return objects end
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
    g.CARDS_JSON = (REPO / "cards" / "index.json").read_text(encoding="utf-8")
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
        check((bar.get("width"), bar.get("height")) == ("38", "190"), f"toolbar is 38 x 190 ({bar.get('width')} x {bar.get('height')})")
        hud = next(e for e in root.iter() if e.get("id") == "hud")
        check(hud.get("rectAlignment") == "UpperRight" and hud.get("height") == "66.667%" and bar in list(hud),
              "the toolbar sits in a frame over the top two-thirds of the screen (so a third of the way down)")
        dock = next(e for e in root.iter() if e.get("id") == "dock")
        panels = [e for e in dock if (e.get("id") or "").endswith("_White")]
        check(len(panels) == 5 and all(e.get("rectAlignment") == "UpperRight" and not e.get("pivot") for e in panels)
              and dock.get("height") == "190" and dock in list(hud),
              "White's five panels hang from the top of a dock the toolbar's height (so their top stays put)")
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
    check(len(list(calls.assets.values())) == 5, "five toolbar icons registered")
    printed = [str(p) for p in calls.printed.values()]
    check(any("Pokémon: 704" in p for p in printed), "roster downloaded (704 names)")
    check(any("Item cards: 246" in p for p in printed) and any("Warrior skill cards: 67" in p for p in printed),
          "cards downloaded (246 items, 67 warrior skills)")

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
    check(spawned is not None and spawned.data.Nickname == "Charizard"
          and spawned.data.CustomImage.ImageURL.endswith("figures/charizard.webp")
          and spawned.data.CustomImage.ImageSecondaryURL.endswith("figures/charizard-back.webp"),
          "clicking row 1 spawns Charizard with front and back images")
    check(abs(spawned.position.x - (-17.625)) < 0.01 and abs(spawned.position.z - (-28.0)) < 0.01,
          f"White's Pokemon goes on the first pedestal of the near stand ({spawned.position.x:.2f}, {spawned.position.z:.2f})")

    # maps
    lst = g.mapList()
    got = [(m.name, bool(m.current)) for m in lst.values()]
    check(got == [("Fontaine", False), ("Map 3", False), ("Terrera Mountain", True)], f"map list -> {got}")
    g.toolClick(player, "-1", "tool_maps")
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
    check(any("is back to normal" in str(p) for p in calls.printed.values()), "clearing says it's back to normal")
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
    check(abs(card.position.x - (-17.625)) < 0.01 and abs(card.position.z - (-26.4 - 5.1105 - lift_z)) < 0.01
          and card.rotation.y == 270 and abs(card.rotation.z - 16.492) < 0.01 and card.data.SidewaysCard,
          "the item card lies landscape in the first item slot on White's stand, tilted to the slope")
    check("1/2 hp" in card.data.Description, "the card's description is its effect")
    g.searchChanged(player, "belief", "skillsIn_White")
    g.searchPick(player, "-1", "skillsRes_White_1")
    sk = calls.spawned[n + 2]
    check(sk.data.Nickname == "Belief" and sk.data.Tags[1] == "WarriorSkill"
          and abs(sk.position.x - (-17.625)) < 0.01 and abs(sk.position.z - (-26.4 - 8.5481 - lift_z)) < 0.01,
          "the warrior skill card goes in the first skill slot (below the item)")
    g.searchPick(player, "-1", "itemsRes_White_1")
    check(len(calls.spawned) == n + 2, "a stale click on the other panel's rows does nothing")
    g.spawnCard("items", "Sitrus Berry", "White")
    check(abs(calls.spawned[n + 3].position.x - (-10.575)) < 0.01, "the next item card takes the next column")
    g.spawnCard("items", "Sitrus Berry", "Green")
    far = calls.spawned[n + 4]
    check(abs(far.position.x - 17.625) < 0.01 and abs(far.position.z - (26.4 + 5.1105 + lift_z)) < 0.01 and far.rotation.y == 450,
          "a far-side seat (Green) uses the far stand, starting from its own left")
    snaps = g.standSnapPoints()
    first = snaps[1].position
    check(len(snaps) == 12 and abs(first[2] - (2.0644 + 0.55 * 0.9589)) < 0.01 and snaps[1].rotation_snap,
          "12 card snap points per stand, lifted off the slope, snapping rotation")
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
    check(calls.attrs["items_White.height"] == 108 + 10 * 32 + 20, f"the item panel keeps its full size while typing ({calls.attrs['items_White.height']})")
    g.searchChanged(player, "", "itemsIn_White")
    check(calls.attrs["itemsList.visibility"] == "White|Green", "clearing the search box brings the list back")
    g.closePanel(green); g.closePanel(player)
    check(calls.attrs["itemsList.active"] == "false" and calls.attrs["itemsListCover.active"] == "false", "closing both panels hides the list")
    i = list(g.listNames["items"].values()).index("Sitrus Berry") + 1
    n = len(calls.spawned)
    g.listPick(player, "-1", f"itemsAll_{i}")
    check(len(calls.spawned) == n + 1 and calls.spawned[n + 1].data.Nickname == "Sitrus Berry", "clicking Sitrus Berry in the list spawns it")

    # flags: a spawned flag gets the menu; Capture tints it to the player's colour, Make neutral resets it
    lua.execute(r"""
      flagObj = { memo = "", menu = {} }
      flagObj.hasTag = function(t) return t == "Flag" or t == "ArenaPiece" end
      flagObj.clearContextMenu = function() flagObj.menu = {} end
      flagObj.addContextMenuItem = function(label, fn) flagObj.menu[#flagObj.menu + 1] = { label = label, fn = fn } end
      flagObj.setColorTint = function(c) flagObj.tint = c end
      flagObj.setDescription = function(d) flagObj.desc = d end
      onObjectSpawn(flagObj)
      onObjectSpawn(board)   -- not a flag: no menu, no error
    """)
    f = g.flagObj
    check([f.menu[i].label for i in (1, 2)] == ["Capture", "Make neutral"], "a spawned flag gets Capture and Make neutral")
    f.menu[1].fn("Red")
    check(f.tint.r > 0.8 and f.tint.g < 0.2 and f.memo == "Red" and f.desc.startswith("Held by Red."),
          f"Capture by Red tints it red and records Red ({f.desc})")
    check(any(str(p) == "RedPlayer captured a flag." for p in calls.printed.values()), "capturing is announced")
    f.menu[1].fn("Grey")
    check(f.memo == "Red" and "Take a seat" in str(calls.broadcast), "a spectator can't capture it")
    f.menu[1].fn("Blue")
    check(f.memo == "Blue" and f.tint.b == 1, "Blue can take it over")
    f.menu[2].fn("Blue")
    check(f.memo == "" and f.tint.r == 0.6 and f.desc.startswith("Neutral."), "Make neutral resets it")

    print("\nall checks passed" if not failures else f"\n{len(failures)} check(s) failed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
