--[[ PCTTS_MOD — Global script for the Pokemon Conquest tabletop mod.
Source: https://github.com/PCTTS/tts (lua/Global.lua). Edit there, not in TTS.

Toolbar (right edge, a third of the way down the screen), one panel open at a time, each player gets their own:
  * Pokéball: search the roster, click a result and that figure goes on your next free pedestal.
  * Potion:   scroll through (or search) the item cards, click one and it goes in the next free item slot.
  * Swords:   scroll through (or search) the warrior skill cards, click one and it goes in the next free skill slot.
  * Sparkle:  the same for Pokémon ability cards (the bottom row of the stand).
Team stands (tagged "Stand") sit on the two long sides: pedestals on top (9 for a whole team; once 3 have been
sent to the spectator stand with the bench button in front of their pedestals, the other 6 slide apart), an item,
a warrior skill and an ability card on the slope under each. Which stand is yours depends on your seat colour
(SEAT_SIDE). A Pokémon taken off its pedestal leaves a phantom of itself there; picking a map brings everyone back
to their stands (9 slots again). The spectator stand at the table's right end carries the turn track (1-15, the
arena's last turn in gold) and its Poké Ball token.
  * Swirl:    pick a status, then pick up a Pokémon to give it that status (it's tinted in the status's
              type colour). One main status at a time; Confused and Flinched can stack on top.
              "Clear status" returns a Pokémon to normal.
  * Map:      pick which arena goes on the table (3D boards from arenas/index.json, with snap points and pieces).
Flags take the colour of the last Pokémon put down on their tile (left-click one to make it neutral); capture zones
take the colour of the player with more Pokémon in them.
Water gates (Fontaine): click the arrows on a gate (or right-click it) to open or close it; the river past it
drains or fills.
Gears (Valora): click the turning arrow on a gear (or right-click it) to turn it 270 degrees, carrying what stands
on it round; a numbered gear's doors button opens or closes its blockers.
HP: the sign above each pedestal shows "current/max" HP of its Pokémon (wherever it is); click the number and type 120 (set), -35 or +20.

The roster (figures/index.json) and the cards (cards/index.json) are downloaded from the PCTTS site when the
game loads, so new Pokémon and changed cards appear without editing the mod. The last copies are kept in the
save, so everything still works if the site can't be reached.
--]]

BASE_URL = "https://pctts.github.io/tts/"
ICONS = {
  pokeball = "ui/icons/pokeball-v3.png", map = "ui/icons/map-v3.png", status = "ui/icons/status-v3.png",
  item = "ui/icons/item-v3.png", skill = "ui/icons/skill-v3.png", ability = "ui/icons/ability-v3.png",
}
PIECE_ICONS = { die = "ui/icons/die-v3.png", updown = "ui/icons/updown-v3.png",   -- buttons on arena pieces
  turnccw = "ui/icons/turnccw-v3.png", turncw = "ui/icons/turncw-v3.png", doors = "ui/icons/doors-v3.png",
  fling = "ui/icons/fling-v3.png", bench = "ui/icons/spectate-v3.png",
  ["glide-ne"] = "ui/icons/glide-ne-v3.png", ["glide-nw"] = "ui/icons/glide-nw-v3.png",   -- a platform's L, by the
  ["glide-se"] = "ui/icons/glide-se-v3.png", ["glide-sw"] = "ui/icons/glide-sw-v3.png" }  -- arms from its bend
-- Toolbar geometry in UI units. Icons are drawn at 64 px, close to their on-screen size: TTS doesn't smooth
-- UI images it shrinks, so a much larger image looks jagged.
BAR_ICON, BAR_MARGIN, BAR_GAP = 32, 3, 6
TOOLS = {
  { kind = "dex", icon = "pokeball" },        -- Spawn a Pokémon
  { kind = "items", icon = "item" },          -- Item cards
  { kind = "skills", icon = "skill" },        -- Warrior skill cards
  { kind = "abilities", icon = "ability" },   -- Pokémon ability cards
  { kind = "status", icon = "status" },       -- Give a status
  { kind = "maps", icon = "map" },            -- Choose the map
}
-- The toolbar and its panels sit in a frame covering the top two-thirds of the screen, the toolbar at the frame's
-- middle: a third of the way down the screen at any resolution. A panel's top stays level with the toolbar's.
HUD_HEIGHT = "66.667%"
-- Searchable catalogues behind the search panels.
SEARCH_KINDS = { "dex", "items", "skills", "abilities" }
CARD_KINDS = { "items", "skills", "abilities" }   -- the stand's card rows, top to bottom
-- Panels that also list every name to scroll through (shown while the search box is empty), LIST_ROWS rows tall.
LIST_KINDS = { items = true, skills = true, abilities = true }
LIST_ROWS = 10
CATALOGS = {
  dex = { title = "Spawn a Pokémon" },
  items = { title = "Item cards",
    deckBase = 1000, tag = "Item" },
  skills = { title = "Warrior skill cards",
    deckBase = 3000, tag = "WarriorSkill" },
  abilities = { title = "Pokémon ability cards",
    deckBase = 5000, tag = "Ability" },
}
ROSTER_URL = BASE_URL .. "figures/index.txt"   -- (tools/fast_data.py, from the .json)
CARDS_URL = BASE_URL .. "cards/index.txt"
STATS_URL = BASE_URL .. "data/pokemon.txt"   -- every Pokémon's stats from the sheet (tools/build_stats.py)
ARENAS_URL = BASE_URL .. "arenas/index.txt"   -- the map picker's arenas (tools/build_arena_index.py)

-- Type colours, the same as the damage calculator sheets' type cells (their conditional formatting).
TYPE_COLORS = {
  Normal = "#ABAA95", Fire = "#FF4421", Water = "#2F9BFE", Electric = "#FFCC2E", Grass = "#74CE53", Ice = "#66CBFF",
  Fighting = "#B95742", Poison = "#A7569B", Ground = "#D9BD5A", Flying = "#859AFF", Psychic = "#FF5697", Bug = "#AABB21",
  Rock = "#B9AA69", Ghost = "#6667BA", Dragon = "#7767EB", Dark = "#765544", Steel = "#ABAABA", Fairy = "#EE99EE",
}
-- Statuses from the rules, each in the colour of the type that inflicts it. `strength` = how far the figure's tint
-- moves from white toward that colour (default STATUS_TINT). Volatile ones can stack on a main status.
STATUS_TINT = 0.6
STATUSES = {
  { key = "burn", label = "Burned", type = "Fire", strength = 0.75 },
  { key = "paralysis", label = "Paralyzed", type = "Electric", strength = 0.75 },
  { key = "poison", label = "Poisoned", type = "Poison", strength = 0.45 },
  { key = "toxic", label = "Badly poisoned", type = "Poison", strength = 0.8 },
  { key = "frostbite", label = "Frostbitten", type = "Ice", strength = 0.9 },
  { key = "drowsy", label = "Drowsy", type = "Normal", strength = 0.85 },
  { key = "confused", label = "Confused", type = "Psychic", volatile = true },
  { key = "flinched", label = "Flinched", type = "Dark", volatile = true },
}
STATUS_BY_KEY, STATUS_ROWS = {}, {}  -- rows: every status, then "clear"
for _, s in ipairs(STATUSES) do
  s.color = TYPE_COLORS[s.type]
  STATUS_BY_KEY[s.key] = s
  STATUS_ROWS[#STATUS_ROWS + 1] = s
end
STATUS_ROWS[#STATUS_ROWS + 1] = { key = "clear", label = "Clear status", color = "#9E9E9E" }

STANDEE_MESH = "models/standee-v1.obj"  -- a Pokémon: art on a round base with a facing arrow (build_standee.py)
FIGURE_SCALE = 1.5   -- ImageScalar for the old flat figurines (only used if the roster has no standees)
FRONT_YAW = 0        -- added to the seat's rotation so the figure's front faces its player
RESULTS = 8          -- search results shown at once
MAX_MAPS = 16        -- rows in the map panel
ROW_TEXT = "#111111" -- result rows: dark text on light grey (TTS can reset text colour when a row's text changes)
ROW_STEP = 32        -- height of one result row plus spacing
SEARCH_BASE = 86     -- search panel height with no results (title, search box)
MAPS_BASE = 48       -- map and status panel height with no rows (title)
NO_SEAT_SPOT = { -35, 4, 22 }  -- where things appear for players without a seat: the strip left of the board
-- Which team stand each seat uses: the near (south, z < 0) or far (north) long side of the table.
SEAT_SIDE = { White = "south", Brown = "south", Red = "south", Orange = "south", Pink = "south",
  Green = "north", Teal = "north", Blue = "north", Yellow = "north", Purple = "north" }
-- Team stand geometry, in the stand's own frame (from tools/build_props.py, props/stand-v1.json): six columns,
-- each a pedestal on top with an item card, a warrior skill card and an ability card below it on the slope.
STAND = {
  x = { -17.625, -10.575, -3.525, 3.525, 10.575, 17.625 },
  pedestal = { y = 2.6, z = -1.6 },
  cards = { items = { y = 2.2198, z = -4.5856 },
            skills = { y = 1.5272, z = -6.9252 },
            abilities = { y = 0.8345, z = -9.2648 } },
  tilt = 16.492, length = 42.3,
  -- The card's scale. TTS shapes a one-card custom deck to its image, and the card images are 400 x 840 (narrower
  -- than TTS's standard card), so at scale 1 a card is 1.46 x 3.06: scaled evenly by 1.5 it's 2.19 x 4.59, short
  -- enough for three rows. (Scaling (1.0, 1.5) stretched the art 1.5x along the card.)
  cardScale = { 1.5, 1.5 },
  snapLift = 0.55,  -- card snap points float this far off the slope, so a card held flat clears the rising slope
}
-- The pedestal columns along a stand (its frame): a whole team of 9 packed close (the cards in their columns
-- almost touch), or the 6 that play at the stand's first spacing.
SLOTS = { [9] = { -18.8, -14.1, -9.4, -4.7, 0, 4.7, 9.4, 14.1, 18.8 }, [6] = STAND.x }
BENCH_SIZE = 3       -- how many of a team of 9 sit out
CARD_YAW = 270  -- cards lie landscape: turned a quarter so the name reads left-to-right for the stand's player
PEDESTAL_TOP = 0.25  -- a pedestal's height above the stand top
COLORS = { "White", "Brown", "Red", "Orange", "Yellow", "Green", "Teal", "Blue", "Purple", "Pink", "Grey", "Black" }

catalog = {}         -- kind -> { index = name -> data, list = sorted search entries, keys = name -> deck id }
for _, k in ipairs(SEARCH_KINDS) do catalog[k] = { index = {}, list = {}, keys = {} } end
roster = catalog.dex.index
cardBacks = {}       -- kind -> back image path
stats = {}           -- Pokémon name -> { hp, atk, def, spd, rng, types } (data/pokemon.json)
arenas = {}          -- arena name -> { mesh, texture, table, depth, snaps, pieces } (arenas/index.json)
openPanel, searchHits, mapRows, spawnCount = {}, {}, {}, {}
armed = {}           -- [colour] = status key waiting for that player to pick up a Pokémon
queries = {}         -- [colour .. kind] = what that player last typed in that search box
listViewers = { items = {}, skills = {}, abilities = {} }  -- [kind][colour] = true while that player sees the full list
listNames, builtLists = {}, {}             -- names in each full list as built, and a signature of them

----------------------------------------------------------------------------------------------------
-- Save / load
----------------------------------------------------------------------------------------------------
-- The downloads (roster, cards, stats, arenas) are kept as the text that came in and saved as that text: TTS saves
-- the game every few seconds for rewind, and turning these tables back into JSON took over a second each time
-- (the stutter). Each is read once per load: the fresh download, or the saved copy if the site can't be reached.
-- They come as plain text, one record per line (tools/fast_data.py): TTS's Lua decodes JSON at about 7 KB a
-- second, so the JSON versions froze every load and rewind for close to a minute.
DATA = {
  { key = "roster", url = ROSTER_URL, use = function(t) setCatalog("dex", t) end },
  { key = "cards", url = CARDS_URL, use = function(t) setCards(t) end },
  { key = "stats", url = STATS_URL, use = function(t) stats = t; refreshPedestals() end },
  { key = "arenas", url = ARENAS_URL, use = function(t) arenas = t; Wait.time(fitTableToBoard, 1) end },
}
STATE_MARK, STATE_SEP = "PCTTS-STATE-1", "\n\30\n"   -- a raw \30 (record separator) can't appear in JSON text
rawData, savedState = {}, ""

local function rememberData(key, text)
  rawData[key] = text
  local parts = { STATE_MARK }
  for _, d in ipairs(DATA) do parts[#parts + 1] = d.key .. "=" .. (rawData[d.key] or "") end
  savedState = table.concat(parts, STATE_SEP)
end

local function readSavedState(saved)
  local texts = {}
  if saved and saved:sub(1, #STATE_MARK) == STATE_MARK then
    -- split with plain find/sub: TTS's Lua gives up on patterns over text this size ("pattern too complex")
    local pos = #STATE_MARK + 1
    while pos <= #saved do
      local s, e = saved:find(STATE_SEP, pos, true)
      local part = saved:sub(pos, (s or #saved + 1) - 1)
      local eq = part:find("=", 1, true)
      if eq and eq > 1 and eq < #part then texts[part:sub(1, eq - 1)] = part:sub(eq + 1) end
      if not s then break end
      pos = e + 1
    end
  elseif saved and saved:sub(1, 1) == "{" then   -- an older save: decoded tables (slow, but only once)
    local ok, old = pcall(JSON.decode, saved)
    if ok and type(old) == "table" then texts.legacy = old end
  end
  return texts
end

-- Plain-text data (tools/fast_data.py): split with plain find/sub only (no Lua patterns on big text).
local function splitPlain(s, sep)
  local out, i = {}, 1
  while true do
    local j = s:find(sep, i, true)
    if not j then
      out[#out + 1] = s:sub(i)
      return out
    end
    out[#out + 1] = s:sub(i, j - 1)
    i = j + #sep
  end
end

local function orNil(s) return s ~= "" and s or nil end

local function numbers(s, sep)
  local out = {}
  for i, v in ipairs(splitPlain(s, sep or ",")) do out[i] = tonumber(v) end
  return out
end

DATA_HEAD = "PCTTS-DATA-1 "
READERS = {
  roster = function(rows)
    local t = {}
    for _, f in ipairs(rows) do
      t[f[1]] = { front = orNil(f[2]), back = orNil(f[3]), standee = orNil(f[4]), source = orNil(f[5]) }
    end
    return t
  end,
  cards = function(rows)
    local t = { backs = {}, abilities = {}, items = {}, skills = {} }
    for _, f in ipairs(rows) do
      if f[1] == "back" then
        t.backs[f[2]] = f[3]
      elseif f[1] == "card" and t[f[2]] then
        t[f[2]][f[3]] = { class = orNil(f[4]), group = orNil(f[5]), face = orNil(f[6]), effect = orNil(f[7]) }
      end
    end
    return t
  end,
  stats = function(rows)
    local t = {}
    for _, f in ipairs(rows) do
      t[f[1]] = { hp = tonumber(f[2]), atk = tonumber(f[3]), def = tonumber(f[4]), spd = tonumber(f[5]),
        rng = tonumber(f[6]), types = splitPlain(f[7] or "", ",") }
    end
    return t
  end,
  arenas = function(rows)
    local t, cur = {}, nil
    local NUM = { yaw = true, material = true, pair = true, tile = true, tiles = true, gate = true, branch = true,
      gear = true, size = true, door = true, sx = true, sy = true, sz = true, group = true, hy = true }
    for _, f in ipairs(rows) do
      if f[1] == "arena" then
        cur = { mesh = f[3], texture = f[4], table = f[5] or "", depth = tonumber(f[6] or ""), turns = tonumber(f[7] or ""),
          snaps = {}, pieces = {} }
        t[f[2]] = cur
      elseif f[1] == "snaps" and cur and (f[2] or "") ~= "" then
        for i, p in ipairs(splitPlain(f[2], ";")) do cur.snaps[i] = numbers(p) end
      elseif f[1] == "piece" and cur then
        local p = {}
        for k = 2, #f do
          local eq = f[k]:find("=", 1, true)
          local key, v = f[k]:sub(1, eq - 1), f[k]:sub(eq + 1)
          if key == "pos" then p.pos = numbers(v)
          elseif v == "true" or v == "false" then p[key] = (v == "true")
          elseif NUM[key] then p[key] = tonumber(v)
          else p[key] = v end
        end
        cur.pieces[#cur.pieces + 1] = p
      end
    end
    return t
  end,
}

-- A download (or its saved copy) as a table: the plain-text format, or JSON (an older saved copy; slow).
function readData(key, text)
  if text:sub(1, #DATA_HEAD) ~= DATA_HEAD then return JSON.decode(text) end
  local rows = {}
  for i, line in ipairs(splitPlain(text, "\n")) do
    if i > 1 and line ~= "" then rows[#rows + 1] = splitPlain(line, "\t") end
  end
  return READERS[key](rows)
end

function onLoad(saved)
  local ok, texts = pcall(readSavedState, saved)
  if not ok then texts = {} end   -- a bad saved copy must never stop the load: the downloads still come in
  for key, text in pairs(texts) do
    if key ~= "legacy" then rememberData(key, text) end
  end
  for _, d in ipairs(DATA) do
    WebRequest.get(d.url, function(req)
      local text = (not req.is_error and req.text and req.text ~= "") and req.text or nil
      local fresh = text ~= nil
      if not fresh then text = rawData[d.key] end   -- offline: the saved copy
      local ok, data = false, nil
      if text then ok, data = pcall(readData, d.key, text) end
      if ok and type(data) == "table" and next(data) then
        if fresh then rememberData(d.key, text) end
        d.use(data)
      elseif texts.legacy and texts.legacy[d.key] then
        d.use(texts.legacy[d.key])
      end
      if d.key == "cards" then buildUI() end   -- once, as soon as the card lists can go in it
    end)
  end
  math.randomseed(os.time())
  for _, obj in ipairs(getAllObjects()) do pieceSetup(obj) end   -- context menus aren't saved with the game
  -- once the objects have finished loading (their own saved UI can replace ours): stands' signs, plain standees,
  -- the buttons on portals and bridges
  Wait.time(function()
    for _, obj in ipairs(getAllObjects()) do
      if obj.hasTag("Stand") then
        setupStand(obj)
      elseif obj.hasTag("Pokemon") then
        plainStandee(obj)
      elseif obj.hasTag("Portal") or obj.hasTag("Bridge") or obj.hasTag("Zone") or obj.hasTag("Trap")
        or obj.hasTag("GateFrame") or obj.hasTag("Gate") or obj.hasTag("Water") or obj.hasTag("Gear") or obj.hasTag("Door")
        or obj.hasTag("Flower") or obj.hasTag("Pedestal") or obj.hasTag("SpectatorStand") or obj.hasTag("TurnTrack")
        or obj.hasTag("Platform") or obj.hasTag("ArenaBackdrop") or obj.hasTag("Board3D") or obj.hasTag("Pillar") then
        pieceSetup(obj)
      elseif obj.type == "Card" and (obj.hasTag("Item") or obj.hasTag("WarriorSkill") or obj.hasTag("Ability")) then
        unstretchCard(obj)
      end
    end
    ensureSpectators()
    pedestalUI = {}      -- the pedestals' saved UI may have replaced ours
    refreshPedestals()
    ensureHandZones()
  end, 2)
end

-- A card spawned before the fix (scaled 1.0 across, 1.5 along: the art stretched) gets the even scale.
function unstretchCard(card)
  local s = card.getScale()
  if math.abs(s.x - STAND.cardScale[1]) > 0.01 and math.abs(s.z - STAND.cardScale[2]) < 0.01 then
    card.setScale({ STAND.cardScale[1], s.y, STAND.cardScale[2] })
    return true
  end
  return false
end

-- The board, its backdrop and the pillars aren't interactive at all (pieceSetup). The team stands and the map's fixed
-- pieces still need clicks (HP signs, flags, buttons), so players just can't delete or cut them; the map picker
-- replaces them by script, which isn't a player action.
PROTECTED_TAGS = { "Stand", "Flag", "Portal", "Bridge", "Zone", "Bell", "BellStand", "GateFrame", "Gate", "Water",
  "Fountain", "Statue", "Gear", "Door", "Flower", "Pedestal", "SpectatorStand", "TurnTrack", "Platform" }

function onPlayerAction(player, action, targets)
  if action == Player.Action.Select or action == Player.Action.PickUp then
    -- a left-click on a (locked) flag arrives as a selection (or a pick-up): it makes the flag neutral instead
    local obj = targets and #targets == 1 and targets[1]
    if obj and obj.hasTag("Flag") then
      flagClicked(obj, player)
      return false
    end
    return true
  end
  if action ~= Player.Action.Delete and action ~= Player.Action.Cut then return true end
  for _, obj in ipairs(targets or {}) do
    for _, tag in ipairs(PROTECTED_TAGS) do
      if obj.hasTag(tag) then return false end
    end
  end
  return true
end

-- Hand zones: eight tiny ones just past the table's edge (so cards on the team stands never fall into a hand, and
-- pieces dragged near the edge don't catch on them), one pair on each side; they are kept only because they set each
-- seat's spacebar camera (from where they stand: "out" past the edge, at height y). A save or reload can bring back
-- TTS's default zones (which reach over the stands), so the layout is checked on every load and put back if it differs.
HAND_SIZE = { w = 0.1, h = 0.1, d = 0.1, y = 2.85, out = 2.28 }
HAND_LAYOUT = {   -- side: near (-z), far (+z), left (-x), right (+x); at: offset along that side
  { c = "Red", side = "near", at = -9.48 }, { c = "White", side = "near", at = 9.48 },
  { c = "Blue", side = "far", at = -9.48 }, { c = "Green", side = "far", at = 9.48 },
  { c = "Orange", side = "left", at = -9.48 }, { c = "Yellow", side = "left", at = 9.48 },
  { c = "Pink", side = "right", at = -9.48 }, { c = "Purple", side = "right", at = 9.48 },
}

-- Where each hand zone goes: { c, x, z, yaw }, from the table's size.
function handTargets()
  local ok, b = pcall(function() return Tables.getTableObject().getBounds() end)
  if not ok or not b then return nil end
  local hx, hz, out = b.size.x / 2, b.size.z / 2, {}
  local off = HAND_SIZE.out
  for _, h in ipairs(HAND_LAYOUT) do
    local t = { c = h.c }
    if h.side == "near" then t.x, t.z, t.yaw = h.at, -(hz + off), 0
    elseif h.side == "far" then t.x, t.z, t.yaw = h.at, hz + off, 180
    elseif h.side == "left" then t.x, t.z, t.yaw = -(hx + off), h.at, 90
    else t.x, t.z, t.yaw = hx + off, h.at, 270 end
    out[#out + 1] = t
  end
  return out
end

-- Put the hand zones back to the layout if they differ from it (returns true if it changed them).
function ensureHandZones()
  if not (Hands and Hands.getHands) then return false end
  local targets = handTargets()
  if not targets then return false end
  local hands, byColor = Hands.getHands(), {}
  for _, h in ipairs(hands) do byColor[h.getValue() or ""] = h end
  local same = #hands == #targets
  for _, t in ipairs(targets) do
    local h = byColor[t.c]
    if not h then
      same = false
    else
      local p, s = h.getPosition(), h.getScale()
      if math.abs(p.x - t.x) > 0.1 or math.abs(p.z - t.z) > 0.1 or math.abs(s.x - HAND_SIZE.w) > 0.01
        or math.abs(s.y - HAND_SIZE.h) > 0.01 or math.abs(s.z - HAND_SIZE.d) > 0.01 then same = false end
    end
  end
  if same then return false end
  -- a zone that moves drops what it holds: note each player's cards first and give them back after
  local held, wanted = {}, {}
  for _, t in ipairs(targets) do
    wanted[t.c] = true
    local ok, objs = pcall(function() return Player[t.c].getHandObjects() end)
    held[t.c] = ok and objs or {}
  end
  for _, h in ipairs(hands) do
    if not wanted[h.getValue() or ""] then h.destruct() end   -- seats without a zone in the layout (Brown, Teal)
  end
  for _, t in ipairs(targets) do
    local h = byColor[t.c]
    if h then
      h.setPosition({ t.x, HAND_SIZE.y, t.z })
      h.setRotation({ 0, t.yaw, 0 })
      h.setScale({ HAND_SIZE.w, HAND_SIZE.h, HAND_SIZE.d })
    else
      local col = Color.fromString(t.c)
      spawnObjectData({ data = {
        Name = "HandTrigger", FogColor = t.c, Locked = true,
        ColorDiffuse = { r = col.r, g = col.g, b = col.b, a = 0 },
        Transform = { posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0,
          scaleX = HAND_SIZE.w, scaleY = HAND_SIZE.h, scaleZ = HAND_SIZE.d },
      }, position = { t.x, HAND_SIZE.y, t.z }, rotation = { 0, t.yaw, 0 } })
    end
  end
  Wait.frames(function()   -- into the hand's new place: a card dropped in a hand zone joins that hand
    for _, t in ipairs(targets) do
      for _, obj in ipairs(held[t.c]) do
        obj.setPosition({ t.x, HAND_SIZE.y, t.z })   -- the zone's centre: it's too small to spread them out
      end
    end
  end, 10)
  return true
end

function onSave()
  return savedState
end

----------------------------------------------------------------------------------------------------
-- Catalogues and search
----------------------------------------------------------------------------------------------------
local function norm(s)
  s = s:lower():gsub("é", "e"):gsub("♀", "f"):gsub("♂", "m")
  return (s:gsub("[^%w]", ""))
end

function setCatalog(kind, index)
  local list, keys = {}, {}
  for name in pairs(index) do
    local words = {}
    for w in name:gmatch("[^%s%-%(%)]+") do words[#words + 1] = norm(w) end
    list[#list + 1] = { name = name, key = norm(name), words = words }
  end
  table.sort(list, function(a, b) return a.name < b.name end)
  for i, e in ipairs(list) do keys[e.name] = (CATALOGS[kind].deckBase or 0) + i end
  catalog[kind] = { index = index, list = list, keys = keys }
  if kind == "dex" then roster = index end
  -- the scrolling lists are part of the UI: rebuild it if this catalogue's names changed since it was built
  if LIST_KINDS[kind] and builtLists[kind] and builtLists[kind] ~= listSignature(kind) then buildUI() end
end

function listSignature(kind)
  local names = {}
  for i, e in ipairs(catalog[kind].list) do names[i] = e.name end
  return table.concat(names, "\n")
end

function setCards(data)
  cardBacks = data.backs or {}
  if data.items then setCatalog("items", data.items) end
  if data.skills then setCatalog("skills", data.skills) end
  if data.abilities then setCatalog("abilities", data.abilities) end
end

-- Best matches for a typed query: whole-name prefix first, then a word prefix, then anywhere; shorter names first.
function search(kind, query, limit)
  local q = norm(query or "")
  if q == "" then return {}, {} end
  local hits = {}
  for _, e in ipairs(catalog[kind].list) do
    local score = false  -- must be initialised: TTS's Lua (MoonSharp) can leave a bare `local x` holding a stale value
    if e.key:sub(1, #q) == q then
      score = 0
    else
      for _, w in ipairs(e.words) do
        if w:sub(1, #q) == q then score = 1; break end
      end
      if not score and e.key:find(q, 1, true) then score = 2 end
    end
    if score then hits[#hits + 1] = { score = score, name = e.name, exact = (e.key == q) } end
  end
  table.sort(hits, function(a, b)
    if a.exact ~= b.exact then return a.exact end
    if a.score ~= b.score then return a.score < b.score end
    if #a.name ~= #b.name then return #a.name < #b.name end
    return a.name < b.name
  end)
  local names = {}
  for i = 1, math.min(limit, #hits) do names[i] = hits[i].name end
  return names, hits
end

function searchRoster(query, limit)
  return search("dex", query, limit)
end

----------------------------------------------------------------------------------------------------
-- Spawning
----------------------------------------------------------------------------------------------------
-- The team stand on this player's side (tagged "Stand"; the near one has z < 0), or nil.
function standFor(color)
  local side = SEAT_SIDE[color]
  if not side then return nil end
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("Stand") and ((o.getPosition().z < 0) == (side == "south")) then return o end
  end
end

local function near(a, b, r)
  return (a.x - b.x) ^ 2 + (a.z - b.z) ^ 2 < r * r
end

-- Is anything of this sort already sitting on the given spot?
local function taken(spot, isCard)
  for _, o in ipairs(getAllObjects()) do
    local wanted = false
    if isCard then wanted = o.type == "Card" else wanted = o.hasTag("Pokemon") or o.type == "Figurine" end
    if wanted and near(o.getPosition(), spot, 1.0) then return true end
  end
  return false
end

-- How far "off the slope" is, in the stand's frame: the slope's normal (it rises toward the board, +z).
local function slopeLift(d)
  local a = math.rad(STAND.tilt)
  return d * math.cos(a), -d * math.sin(a)  -- (y, z)
end

-- The stand's card snap points (one per card slot, n columns), a little above the slope, rotation snapping to the slope.
function standSnapPoints(n)
  local dy, dz = slopeLift(STAND.snapLift)
  local tilt = STAND.tilt * (CARD_YAW == 270 and 1 or -1)
  local snaps = {}
  for _, x in ipairs(SLOTS[n or 6]) do
    for _, kind in ipairs(CARD_KINDS) do
      local c = STAND.cards[kind]
      snaps[#snaps + 1] = { position = { x, c.y + dy, c.z + dz }, rotation = { 0, CARD_YAW, tilt }, rotation_snap = true }
    end
  end
  return snaps
end

-- Card rotation on the slope: a quarter turn (landscape), tilted to the slope's angle.
function cardRotation(stand)
  local tilt = STAND.tilt * (CARD_YAW == 270 and 1 or -1)
  return Vector(0, stand.getRotation().y + CARD_YAW, tilt)
end

-- First free spot on the player's stand, columns from the player's left. kind: "dex" (a pedestal with no Pokémon of
-- its own, not sat out) or a card kind (not in a sat-out column).
function freeSpot(color, kind)
  local stand = standFor(color)
  if not stand then return nil end
  local peds = standPedestals(stand)
  if kind == "dex" then
    for _, p in ipairs(peds) do
      local st = pedestalState(p.obj)
      local spot = p.obj.getPosition() + Vector(0, PEDESTAL_TOP, 0)
      if not st.benched and not pedestalMon(p.obj, st) and not taken(spot, false) then return spot, stand end
    end
  else
    local benched = {}
    for i, p in ipairs(peds) do benched[i] = pedestalState(p.obj).benched end
    for i, x in ipairs(SLOTS[standSlots(stand)]) do
      local spot = stand.positionToWorld(Vector(x, STAND.cards[kind].y, STAND.cards[kind].z))
      if not benched[i] and not taken(spot, true) then return spot, stand end
    end
  end
  -- all full: past the stand's right-hand end (from its player's side)
  return stand.positionToWorld(Vector(STAND.length / 2 + 3, 3, -5)), stand, true
end

function spawnPokemon(name, color)
  local files = roster[name]
  if not files then return nil end
  local spot, stand = freeSpot(color or "Grey", "dex")
  local pos = spot and Vector(spot.x, spot.y + 0.5, spot.z) or Vector(NO_SEAT_SPOT[1], NO_SEAT_SPOT[2], NO_SEAT_SPOT[3])
  local yaw = (stand and stand.getRotation().y or 0) + FRONT_YAW  -- front faces the stand's player
  local data = {
    Transform = { posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = 1, scaleY = 1, scaleZ = 1 },
    Nickname = name,
    Tags = { "Pokemon" },
    Memo = JSON.encode({ pokemon = name, hp = maxHp(name), maxHp = maxHp(name), owner = teamColor(color) }),
  }
  if files.standee then
    -- the standee: the art on a round base whose arrow points the way the Pokémon faces (the art's left);
    -- a tint (statuses) recolours all of it
    data.Name = "Custom_Model"
    data.ColorDiffuse = { r = 1, g = 1, b = 1 }
    data.CustomMesh = { MeshURL = BASE_URL .. STANDEE_MESH, DiffuseURL = BASE_URL .. files.standee, NormalURL = "",
      ColliderURL = BASE_URL .. STANDEE_MESH, Convex = true, MaterialIndex = 3, TypeIndex = 1, CastShadows = true }  -- matte (cardboard): plastic glare washed out the base
  else
    -- an older roster without standees: the flat two-sided figurine
    pos = Vector(pos.x, pos.y + 1, pos.z)
    data.Name = "Figurine_Custom"
    data.CustomImage = { ImageURL = BASE_URL .. files.front, ImageSecondaryURL = BASE_URL .. files.back,
      ImageScalar = FIGURE_SCALE, WidthScale = 0 }
  end
  return spawnObjectData({ data = data, position = pos, rotation = Vector(0, yaw, 0) })
end

-- A single landscape card (its own one-card deck sheet) on the next free slot of the player's stand:
-- items in the top row, warrior skills in the middle, abilities at the bottom. The effect is its hover description.
function spawnCard(kind, name, color)
  local card, key = catalog[kind].index[name], catalog[kind].keys[name]
  if not (card and key and cardBacks[kind]) then return nil end
  local deck = {}
  deck[tostring(key)] = { FaceURL = BASE_URL .. card.face, BackURL = BASE_URL .. cardBacks[kind], NumWidth = 1, NumHeight = 1,
    BackIsHidden = true, UniqueBack = false, Type = 0 }
  local spot, stand, full = freeSpot(color or "Grey", kind)
  local pos, rot
  if spot and not full then
    local dy, dz = slopeLift(0.15)
    pos, rot = stand.positionToWorld(stand.positionToLocal(spot) + Vector(0, dy, dz)), cardRotation(stand)
  else
    pos = spot and Vector(spot.x, spot.y + 1, spot.z) or Vector(NO_SEAT_SPOT[1], NO_SEAT_SPOT[2], NO_SEAT_SPOT[3])
    rot = Vector(0, (stand and stand.getRotation().y or 0) + CARD_YAW, 0)
  end
  local kx, kz = STAND.cardScale[1], STAND.cardScale[2]
  return spawnObjectData({
    data = {
      Name = "CardCustom",
      Transform = { posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = kx, scaleY = 1, scaleZ = kz },
      Nickname = name,
      Description = card.effect or "",
      Tags = { CATALOGS[kind].tag },
      CardID = key * 100,
      CustomDeck = deck,
      SidewaysCard = true,
    },
    position = pos,
    rotation = rot,
  })
end

function spawnFrom(kind, name, color)
  if kind == "dex" then return spawnPokemon(name, color) end
  return spawnCard(kind, name, color)
end

----------------------------------------------------------------------------------------------------
-- Maps: the arenas in arenas/index.json (tools/build_arena_index.py), each a 3D board (tag "Board3D") with a
-- snap point over every tile (position only), its pieces (flags…) and the table image around it.
----------------------------------------------------------------------------------------------------
BOARD_SPOT = { 0.01, 0.961, -0.01 }   -- where a board sits: on the table, no rotation
-- An arena's surroundings are shown on a flat panel over the table's play area (props/backdrop-v1.obj), not as the
-- table's own image: changing that reloads the table, and TTS then puts back its default hand zones, which reach over
-- the team stands and pull in the cards on them.
BACKDROP = { mesh = "props/backdrop-v1.obj", pos = { 0.0092, 0.9615, -0.0071 } }
BOARD_SHADER = { SpecularColor = { r = 1, g = 1, b = 1 }, SpecularIntensity = 0, SpecularSharpness = 2, FresnelStrength = 0 }

function currentBoard()
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("Board3D") then return o end
  end
end

-- { {name="Pugilis", current=true}, ... } sorted by name
function mapList()
  local board, list = currentBoard(), {}
  for name in pairs(arenas) do
    list[#list + 1] = { name = name, current = board ~= nil and board.getName() == name }
  end
  table.sort(list, function(a, b) return a.name < b.name end)
  return list
end

-- Put an arena on the table: the old board and its pieces go, the new board comes with its snap points and
-- pieces, and the table gets the arena's image. (entry and base: a preview from local files, tools only.)
function loadArena(name, entry, base)
  local a = entry or arenas[name]
  if not a then return false end
  base = base or BASE_URL
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("Board3D") or o.hasTag("ArenaPiece") then o.destruct() end
  end
  local snaps = {}
  for i, p in ipairs(a.snaps) do
    snaps[i] = { position = { p[1], p[2], p[3] }, rotation = { 0, 0, 0 }, rotation_snap = false }
  end
  local spot = Vector(BOARD_SPOT[1], BOARD_SPOT[2], BOARD_SPOT[3])
  spawnObjectData({
    data = {
      Name = "Custom_Model", Nickname = name, Tags = { "Board3D" }, Locked = true,
      Transform = { posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = 1, scaleY = 1, scaleZ = 1 },
      CustomMesh = { MeshURL = base .. a.mesh, DiffuseURL = base .. a.texture, NormalURL = "",
        ColliderURL = base .. a.mesh, Convex = false, MaterialIndex = 3, TypeIndex = 0, CastShadows = true,
        CustomShader = BOARD_SHADER },
    },
    position = spot, rotation = { 0, 0, 0 },
    callback_function = function(board)
      board.setSnapPoints(snaps)
      board.interactable = false
    end,
  })
  for _, p in ipairs(a.pieces or {}) do spawnArenaPiece(p, spot, base) end
  if a.table and a.table ~= "" then setBackdrop(base .. a.table, base, tableLayout(a.depth)) end
  setTableDepth(a.depth)
  setTurnTrack(a.turns)
  return true
end

function currentBackdrop()
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("ArenaBackdrop") then return o end
  end
end

----------------------------------------------------------------------------------------------------
-- The table follows the board's depth. A board deeper than the usual play area (Snow: 18 tiles) gets the table
-- stretched front to back just enough that its near and far trims stay their usual width outside the board: the
-- map's picture is stretched to the board's depth and lies over the trim's inner part (a hair higher: the trim
-- sits a little above the play area), and the team stands move back to the usual gap from the board, with
-- everything resting on them (Pokémon, cards, the pedestal discs). Any other board puts the table and stands back.
-- A table's scale may not be kept in a save, so it's applied again once the arena list has loaded.
----------------------------------------------------------------------------------------------------
TABLE_DEPTH = 75.246      -- the custom table front to back at scale 1 (measured in TTS)
PLAY_DEPTH = 51.981       -- its play area front to back (= the backdrop panel at scale 1, and 16 tiles)
STAND_GAP = 0.4095        -- a team stand's inner edge sits this far outside the play area (z 26.4)
STAND_DEPTH = 10.8        -- a team stand front to back
BACKDROP_LIFT = 0.9625    -- the panel's height when it lies over part of the trim (the trim's top is 0.9612)

-- The table's stretch, the panel's and the stands' distance from the middle for a board `depth` deep.
function tableLayout(depth)
  local d = math.max(depth or PLAY_DEPTH, PLAY_DEPTH)
  return { scale = (d + TABLE_DEPTH - PLAY_DEPTH) / TABLE_DEPTH, panel = d / PLAY_DEPTH, stand = d / 2 + STAND_GAP }
end

local function backdropY(lay)
  return lay.panel > 1.0001 and BACKDROP_LIFT or BACKDROP.pos[2]
end

local function fitBackdrop(panel, lay)
  if math.abs(panel.getScale().z - lay.panel) > 1e-4 then panel.setScale({ 1, 1, lay.panel }) end
  local p = panel.getPosition()
  if math.abs(p.y - backdropY(lay)) > 1e-5 then panel.setPosition({ p.x, backdropY(lay), p.z }) end
end

-- What rests on a team stand: anything over its footprint, except what's in a hand and the fixed pieces.
local function standRiders(stand)
  local p, out = stand.getPosition(), {}
  local sgn = p.z < 0 and -1 or 1
  for _, o in ipairs(getAllObjects()) do
    if o ~= stand and not o.held_by_color and not (o.hasTag("Stand") or o.hasTag("Board3D") or o.hasTag("ArenaPiece")
        or o.hasTag("ArenaBackdrop") or o.hasTag("Pillar")) then
      local q = o.getPosition()
      local into = (q.z - p.z) * sgn   -- how far in behind the stand's inner edge
      if math.abs(q.x - p.x) <= STAND.length / 2 + 0.2 and into >= -0.1 and into <= STAND_DEPTH + 0.1 and q.y > p.y - 0.5 then
        out[#out + 1] = o
      end
    end
  end
  return out
end

-- Stretch (or restore) the table for a board `depth` deep, move the stands (and what's on them) to suit, fit the
-- backdrop panel, and put the hand zones at the table's new edges.
function setTableDepth(depth)
  local lay = tableLayout(depth)
  local ok, tbl = pcall(function() return Tables.getTableObject() end)
  if ok and tbl and tbl.setScale and math.abs(tbl.getScale().z - lay.scale) > 1e-4 then tbl.setScale({ 1, 1, lay.scale }) end
  for _, stand in ipairs(getAllObjects()) do
    if stand.hasTag("Stand") then
      local p = stand.getPosition()
      local dz = (p.z < 0 and -lay.stand or lay.stand) - p.z
      if math.abs(dz) > 0.005 then
        for _, o in ipairs(standRiders(stand)) do
          local q = o.getPosition()
          o.setPosition({ q.x, q.y, q.z + dz })
        end
        stand.setPosition({ p.x, p.y, p.z + dz })
      end
    end
  end
  local panel = currentBackdrop()
  if panel then fitBackdrop(panel, lay) end
  Wait.frames(ensureHandZones, 2)   -- once the table's new size shows in its bounds
end

-- After a load: the table's stretch for the board on it.
function fitTableToBoard()
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("Board3D") then
      local a = arenas[o.getName()]
      if a then
        setTableDepth(a.depth)
        ensureTurnTrack(a.turns)
      end
      return
    end
  end
end

-- Show an image round the board on the backdrop panel (kept if it already shows it), sized for the board (lay:
-- tableLayout). Locked and not clickable.
function setBackdrop(image, base, lay)
  lay = lay or tableLayout()
  local old = currentBackdrop()
  if old then
    if (old.getCustomObject() or {}).diffuse == image then
      fitBackdrop(old, lay)
      return old
    end
    old.destruct()
  end
  return spawnObjectData({
    data = {
      Name = "Custom_Model", Nickname = "", Tags = { "ArenaBackdrop" }, Locked = true,
      Transform = { posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = 1, scaleY = 1, scaleZ = lay.panel },
      CustomMesh = { MeshURL = base .. BACKDROP.mesh, DiffuseURL = image, NormalURL = "", ColliderURL = base .. BACKDROP.mesh,
        Convex = false, MaterialIndex = 3, TypeIndex = 0, CastShadows = false, CustomShader = BOARD_SHADER },
    },
    position = { BACKDROP.pos[1], backdropY(lay), BACKDROP.pos[3] }, rotation = { 0, 0, 0 },
    callback_function = function(obj) obj.interactable = false end,
  })
end

-- One arena piece from the index (pos: in the board's frame; origin: where the board sits), locked.
-- Flags start neutral, portals in their starting pair's colour, bridges dropped (closed); pieceSetup gives
-- them their buttons and menus.
function spawnArenaPiece(p, origin, base)
  local data = {
    Name = "Custom_Model", Nickname = p.name, Description = p.desc or "", Tags = { p.kind, "ArenaPiece" },
    Locked = not p.free, ColorDiffuse = { r = 1, g = 1, b = 1 }, Memo = "",   -- free pieces (trees, gifts): players move them
    Transform = { posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = 1, scaleY = 1, scaleZ = 1 },
    CustomMesh = { MeshURL = base .. p.mesh, DiffuseURL = base .. p.diffuse, NormalURL = "",
      ColliderURL = base .. p.collider, Convex = p.convex, MaterialIndex = p.material, TypeIndex = 0,
      CastShadows = true },
  }
  local pos = origin + Vector(p.pos[1], p.pos[2], p.pos[3])
  if p.kind == "Flag" then
    data.ColorDiffuse, data.Description = NEUTRAL, FLAG_DESC
  elseif p.kind == "Portal" then
    data.ColorDiffuse, data.Memo = portalTint(p.pair or 1), JSON.encode({ pair = p.pair or 1 })
  elseif p.kind == "Zone" then
    data.ColorDiffuse, data.Memo = NEUTRAL, JSON.encode({ tiles = p.tiles or 2, tile = p.tile or BOARD_TILE })
  elseif p.kind == "Bridge" and (p.sx or p.sz) then   -- a grass half starts closed, inside its hedge
    data.Memo = JSON.encode({ up = false, x = pos.x, y = pos.y, z = pos.z, sx = p.sx or 0, sz = p.sz or 0,
      tiles = p.tiles or 1, tile = p.tile or BOARD_TILE, group = p.group, lead = p.lead, hy = p.hy })
    pos = Vector(pos.x + (p.sx or 0), pos.y, pos.z + (p.sz or 0))
  elseif p.kind == "Bridge" then   -- rope bridges start dropped, hanging below the islands
    data.Memo = JSON.encode({ up = false, y = pos.y, tiles = p.tiles or 1, tile = p.tile or BOARD_TILE })
    pos = Vector(pos.x, pos.y - BRIDGE_DROP, pos.z)
  elseif p.kind == "Flower" then   -- its spots: "dx,dy,dz;..." from its tile top to theirs
    local targets = {}
    for _, s in ipairs(splitPlain(p.targets or "", ";")) do
      if s ~= "" then targets[#targets + 1] = numbers(s) end
    end
    data.Memo = JSON.encode({ targets = targets, tile = p.tile or BOARD_TILE })
  elseif p.kind == "Platform" then   -- starts on its first tile; its route: "dx,dy,dz;..." from there to the others
    local route = {}
    for _, s in ipairs(splitPlain(p.route or "", ";")) do
      if s ~= "" then route[#route + 1] = numbers(s) end
    end
    data.Memo = JSON.encode({ route = route, at = 1, x = pos.x, y = pos.y, z = pos.z, tile = p.tile or BOARD_TILE,
      arms = p.arms })
  elseif p.kind == "Gate" then   -- gates start open: the sluice block sunk into the river bed
    data.Memo = JSON.encode({ gate = p.gate, branch = p.branch, part = p.part, open = true, y = pos.y })
    pos = Vector(pos.x, pos.y - GATE_DROP, pos.z)
  elseif p.kind == "GateFrame" then
    data.Memo, data.Description = JSON.encode({ gate = p.gate, branch = p.branch, part = p.part }), GATE_DESC
  elseif p.kind == "Water" then
    data.Memo = JSON.encode({ branch = p.branch, part = p.part, y = pos.y })
    data.CustomMesh.CastShadows = false
  elseif p.kind == "Gear" then
    data.Memo = JSON.encode({ gear = p.gear or 0, size = p.size or 4, turn = p.turn or "ccw", tile = p.tile or BOARD_TILE })
  elseif p.kind == "Door" then   -- blockers start closed, filling their tile; the memo keeps that spot
    data.Memo = JSON.encode({ door = p.door, open = false, x = pos.x, y = pos.y, z = pos.z,
      sx = p.sx or 0, sy = p.sy or 0, sz = p.sz or 0 })
  end
  return spawnObjectData({ data = data, position = pos, rotation = { 0, p.yaw, 0 },
    callback_function = function(obj) pieceSetup(obj) end })
end

----------------------------------------------------------------------------------------------------
-- Interface: toolbar on the right, one panel per player colour (each visible only to that colour)
----------------------------------------------------------------------------------------------------
local function barSize()
  return BAR_ICON + 2 * BAR_MARGIN, #TOOLS * BAR_ICON + (#TOOLS - 1) * BAR_GAP + 2 * BAR_MARGIN
end

-- Each tool: an invisible button (hover highlight, click) with the icon on top, placed by hand so the
-- border around the icons is exactly BAR_MARGIN (TTS pads icons inside buttons).
local function toolbarXml()
  local w, h = barSize()
  local items = {}
  for i, t in ipairs(TOOLS) do
    local y = -(BAR_MARGIN + (i - 1) * (BAR_ICON + BAR_GAP))
    local place = string.format('rectAlignment="UpperCenter" offsetXY="0 %d" width="%d" height="%d" onClick="toolClick"',
      y, BAR_ICON, BAR_ICON)
    items[#items + 1] = string.format('<Button id="tool_%s" class="bar" %s/>', t.kind, place)
    items[#items + 1] = string.format('<Image id="toolIcon_%s" class="barIcon" image="%s" %s/>', t.kind, t.icon, place)
  end
  return string.format('<Panel id="toolbar" rectAlignment="MiddleRight" width="%d" height="%d" color="#000000E6" '
    .. 'outline="#303030" outlineSize="1 1">\n  %s\n</Panel>\n', w, h, table.concat(items, "\n  "))
end

PANEL_W, PANEL_PAD = 290, 8
LIST_TOP = 78   -- a search panel's first result row, below its top: padding, title, search box and gaps
LIST_BAR = 20   -- room at a full list's right for its scrollbar, which lies over the list
LIST_HBAR = 20  -- TTS always gives a scroll list a sideways scrollbar along its bottom, even with nothing to scroll:
                -- the list is this much taller and a strip in the panel's colour covers the bar

-- Panels hang from a "dock": an empty box the toolbar's height, just left of it. Each panel is anchored to the
-- dock's top-right corner (rectAlignment UpperRight), so it grows downward and its top stays level with the
-- toolbar's whatever its height. (A panel centred on the toolbar with pivot "1 1" jumped when its height changed:
-- TTS re-applies the alignment's own pivot.)
local function dockXml()
  local w, h = barSize()
  return string.format('<Panel id="dock" rectAlignment="MiddleRight" offsetXY="%d 0" width="%d" height="%d" '
    .. 'color="#00000000" raycastTarget="false">\n', -(w + 4), PANEL_W, h)
end

local function panelXml(kind, c, title, height, body)
  return string.format([[
<VerticalLayout id="%s_%s" visibility="%s" active="false" rectAlignment="UpperRight" width="%d" height="%d"
       color="#141414F2" outline="#303030" outlineSize="1 1" padding="%d %d %d %d" spacing="4"
       childForceExpandHeight="false" childForceExpandWidth="true">
  <HorizontalLayout preferredHeight="28" flexibleHeight="0" childForceExpandWidth="false" spacing="4">
    <Text class="title" flexibleWidth="1">%s</Text>
    %s
  </HorizontalLayout>
  %s
  <Panel flexibleHeight="1"/>
</VerticalLayout>
]], kind, c, c, PANEL_W, height, PANEL_PAD, PANEL_PAD, PANEL_PAD, PANEL_PAD, title,
    '<Button class="close" preferredWidth="28" onClick="closePanel" text="X"/>', body)
end

local function xmlText(s)
  return (s:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"):gsub('"', "&quot;"))
end

-- Every name of a card kind in one scrolling list, built once and shown (via its visibility) to the players
-- whose panel for that kind is open with an empty search box. It sits where those panels' result rows go.
local function listXml(kind)
  local names, rows = {}, {}
  for i, e in ipairs(catalog[kind].list) do
    names[i] = e.name
    rows[i] = string.format('<Button id="%sAll_%d" class="row" onClick="listPick" text="%s"/>', kind, i, xmlText(e.name))
  end
  listNames[kind], builtLists[kind] = names, listSignature(kind)
  local height = LIST_ROWS * ROW_STEP - 4 + LIST_HBAR
  return string.format([[
<VerticalScrollView id="%sList" active="false" rectAlignment="UpperRight" offsetXY="%d %d" width="%d" height="%d"
       color="#00000000" scrollSensitivity="%d" movementType="Clamped" horizontal="false" vertical="true"
       horizontalScrollbarVisibility="AutoHide" verticalScrollbarVisibility="AutoHide"
       scrollbarBackgroundColor="#00000060" scrollbarColors="#5A5A5A|#7A7A7A|#9A9A9A|#5A5A5A">
  <VerticalLayout id="%sListBody" height="%d" spacing="4" padding="0 %d 0 0"
       childForceExpandHeight="false" childForceExpandWidth="true">
  %s
  </VerticalLayout>
</VerticalScrollView>
<Panel id="%sListCover" active="false" rectAlignment="UpperRight" offsetXY="%d %d" width="%d" height="%d"
       color="#181818"/>  <!-- the panel's colour as it shows on screen -->
]], kind, -PANEL_PAD, -LIST_TOP, PANEL_W - 2 * PANEL_PAD, height, ROW_STEP * 2,
    kind, math.max(1, #rows * ROW_STEP - 4), LIST_BAR, table.concat(rows, "\n  "),
    kind, -PANEL_PAD + 1, -(LIST_TOP + height - LIST_HBAR), PANEL_W - 2 * PANEL_PAD + 2, LIST_HBAR)
end

function buildUI()
  local assets = {}
  for name, path in pairs(ICONS) do assets[#assets + 1] = { name = name, url = BASE_URL .. path } end
  UI.setCustomAssets(assets)
  openPanel, armed, queries = {}, {}, {}
  listViewers = { items = {}, skills = {}, abilities = {} }

  local xml = { [[
<Defaults>
  <Button class="bar" colors="#00000000|#FFFFFF26|#FFFFFF4D|#00000000"/>
  <Image class="barIcon" raycastTarget="false" preserveAspect="true"/>
  <Button class="row" fontSize="15" textAlignment="MiddleLeft" padding="10 0 0 0" textColor="#111111"
          colors="#E4E4E4|#B3D1FF|#8DB8F7|#E4E4E4" preferredHeight="28" flexibleHeight="0"/>
  <Button class="close" fontSize="14" textColor="#FFFFFF" colors="#2a2a2a|#c0392b|#962d22|#2a2a2a"/>
  <Text class="title" fontSize="16" fontStyle="Bold" color="#FFFFFF" alignment="MiddleLeft"/>
  <InputField class="search" fontSize="16" preferredHeight="34" flexibleHeight="0" characterLimit="40"/>
</Defaults>
]], string.format('<Panel id="hud" rectAlignment="UpperRight" width="100%%" height="%s" color="#00000000" raycastTarget="false">\n',
    HUD_HEIGHT), toolbarXml(), dockXml() }
  for _, c in ipairs(COLORS) do
    for _, kind in ipairs(SEARCH_KINDS) do
      local cat = CATALOGS[kind]
      local rows = {
        string.format('<InputField id="%sIn_%s" class="search" placeholder="Type part of a name..." onValueChanged="searchChanged"/>', kind, c),
      }
      for i = 1, RESULTS do
        rows[#rows + 1] = string.format('<Button id="%sRes_%s_%d" class="row" active="false" onClick="searchPick" text=" "/>', kind, c, i)
      end
      xml[#xml + 1] = panelXml(kind, c, cat.title, panelHeight(kind, 0), table.concat(rows, "\n  "))
    end

    local rows = {}
    for i = 1, MAX_MAPS do
      rows[#rows + 1] = string.format('<Button id="mapRes_%s_%d" class="row" active="false" onClick="mapPick" text=" "/>', c, i)
    end
    xml[#xml + 1] = panelXml("maps", c, "Choose the map", MAPS_BASE, table.concat(rows, "\n  "))

    -- statuses: a square in the status's colour, then the row (the clear row gets an empty square's space)
    rows = {}
    for _, s in ipairs(STATUS_ROWS) do
      local swatch = s.key == "clear" and "#00000000" or s.color
      rows[#rows + 1] = string.format('<HorizontalLayout preferredHeight="28" flexibleHeight="0" spacing="6" childForceExpandWidth="false">'
        .. '<Panel id="statusSwatch_%s_%s" preferredWidth="28" flexibleWidth="0" color="%s"/>'
        .. '<Button id="statusRes_%s_%s" class="row" flexibleWidth="1" onClick="statusPick" text="%s" colors="%s"/></HorizontalLayout>',
        c, s.key, swatch, c, s.key, s.label, statusRowColors(s.color, false))
    end
    xml[#xml + 1] = panelXml("status", c, "Give a status", MAPS_BASE + #STATUS_ROWS * ROW_STEP, table.concat(rows, "\n  "))
  end
  for _, kind in ipairs(SEARCH_KINDS) do
    if LIST_KINDS[kind] then xml[#xml + 1] = listXml(kind) end   -- after the panels, so drawn on top of them
  end
  xml[#xml + 1] = "</Panel>\n</Panel>\n"   -- closes the dock, then the frame
  UI.setXml(table.concat(xml))
end

-- A search panel's height with n result rows. Panels with a full list stay one size: the list's.
function panelHeight(kind, n)
  if LIST_KINDS[kind] then return SEARCH_BASE + LIST_ROWS * ROW_STEP + LIST_HBAR end
  return SEARCH_BASE + n * ROW_STEP
end

-- Show or hide a card kind's full list for one player (it's one list, made visible to each player who needs it).
function setListShown(c, kind, on)
  if not LIST_KINDS[kind] or (listViewers[kind][c] or false) == on then return end
  listViewers[kind][c] = on or nil
  local viewers = {}
  for _, col in ipairs(COLORS) do
    if listViewers[kind][col] then viewers[#viewers + 1] = col end
  end
  for _, id in ipairs({ kind .. "List", kind .. "ListCover" }) do
    if #viewers > 0 then UI.setAttribute(id, "visibility", table.concat(viewers, "|")) end
    UI.setAttribute(id, "active", #viewers > 0 and "true" or "false")
  end
end

local function show(c, kind)
  for _, t in ipairs(TOOLS) do
    UI.setAttribute(t.kind .. "_" .. c, "active", (t.kind == kind) and "true" or "false")
  end
  for lk in pairs(LIST_KINDS) do   -- the full list shows while its panel is open and nothing is typed
    setListShown(c, lk, lk == kind and (queries[c .. lk] or "") == "")
  end
  openPanel[c] = kind
  if kind ~= "status" and armed[c] then  -- closing the status panel cancels a waiting status
    armed[c] = nil
    refreshStatus(c)
  end
end

function closePanel(player)
  show(player.color, nil)
end

-- Every toolbar icon calls this; the element id says which tool ("tool_items", "toolIcon_items", ...).
function toolClick(player, _, id)
  local c, kind = player.color, id:match("^tool%a*_(%a+)$")
  if openPanel[c] == kind then return show(c, nil) end
  if kind == "maps" then refreshMaps(c) end
  show(c, kind)
  if kind == "status" then refreshStatus(c) end
end

function searchChanged(player, value, id)
  local c, kind = player.color, id:match("^(%a+)In_")
  value = value or ""
  queries[c .. kind] = value
  local names = search(kind, value, RESULTS)
  searchHits[c] = { kind = kind, names = names }
  for i = 1, RESULTS do
    local rid = kind .. "Res_" .. c .. "_" .. i
    if names[i] then
      UI.setAttribute(rid, "text", names[i])
      UI.setAttribute(rid, "textColor", ROW_TEXT)
    end
    UI.setAttribute(rid, "active", names[i] and "true" or "false")
  end
  UI.setAttribute(kind .. "_" .. c, "height", panelHeight(kind, #names))
  setListShown(c, kind, value == "" and openPanel[c] == kind)
end

local function placed(kind, c, name)
  if name then spawnFrom(kind, name, c) end
end

function searchPick(player, _, id)
  local c = player.color
  local kind, i = id:match("^(%a+)Res_%a+_(%d+)$")
  local hits = searchHits[c]
  placed(kind, c, hits and hits.kind == kind and hits.names[tonumber(i)])
end

-- A row of a full list ("itemsAll_12"): the 12th name of the list as it was built.
function listPick(player, _, id)
  local kind, i = id:match("^(%a+)All_(%d+)$")
  placed(kind, player.color, listNames[kind] and listNames[kind][tonumber(i)])
end

function refreshMaps(c)
  local list = mapList()
  mapRows[c] = list
  for i = 1, MAX_MAPS do
    local id, m = "mapRes_" .. c .. "_" .. i, list[i]
    if m then
      UI.setAttribute(id, "text", m.name)
      UI.setAttribute(id, "textColor", ROW_TEXT)
      UI.setAttribute(id, "colors", m.current and "#8DB8F7|#8DB8F7|#6FA3F0|#8DB8F7" or "#E4E4E4|#B3D1FF|#8DB8F7|#E4E4E4")
    end
    UI.setAttribute(id, "active", m and "true" or "false")
  end
  UI.setAttribute("maps_" .. c, "height", MAPS_BASE + math.min(#list, MAX_MAPS) * ROW_STEP)
end

function mapPick(player, _, id)
  local c = player.color
  local m = mapRows[c] and mapRows[c][tonumber(id:match("_(%d+)$"))]
  if not m or m.current then return end
  if not loadArena(m.name) then return end
  resetStands()
  Wait.frames(function()
    for _, other in ipairs(COLORS) do
      if openPanel[other] == "maps" then refreshMaps(other) end
    end
  end, 5)
end

----------------------------------------------------------------------------------------------------
-- Statuses: pick one in the panel, then pick up a Pokémon. Stored in the figure's memo, shown as a tint.
----------------------------------------------------------------------------------------------------
local function hexRGB(hex)
  return tonumber(hex:sub(2, 3), 16) / 255, tonumber(hex:sub(4, 5), 16) / 255, tonumber(hex:sub(6, 7), 16) / 255
end

-- Colour `t` of the way from hex a to hex b.
local function mixHex(a, b, t)
  local r1, g1, b1 = hexRGB(a)
  local r2, g2, b2 = hexRGB(b)
  local function ch(x, y) return math.floor((x + (y - x) * t) * 255 + 0.5) end
  return string.format("#%02X%02X%02X", ch(r1, r2), ch(g1, g2), ch(b1, b2))
end

-- Row colours (normal|hover|pressed|disabled): pale type colour; strong when armed.
function statusRowColors(hex, isArmed)
  if isArmed then
    local s = mixHex("#F0F0F0", hex, 0.75)
    return table.concat({ s, s, s, s }, "|")
  end
  return table.concat({ mixHex("#F0F0F0", hex, 0.3), mixHex("#F0F0F0", hex, 0.5), mixHex("#F0F0F0", hex, 0.65),
    mixHex("#F0F0F0", hex, 0.3) }, "|")
end

function refreshStatus(c)
  for _, s in ipairs(STATUS_ROWS) do
    UI.setAttribute("statusRes_" .. c .. "_" .. s.key, "colors", statusRowColors(s.color, armed[c] == s.key))
  end
end

function statusPick(player, _, id)
  local c = player.color
  local key = id:match("^statusRes_%a+_(%a+)$")
  armed[c] = (armed[c] ~= key) and key or nil
  refreshStatus(c)
  if armed[c] then
    local what = key == "clear" and "return it to normal" or ("make it " .. STATUS_BY_KEY[key].label:lower())
    player.broadcast("Pick up a Pokémon to " .. what .. ".", { 0.9, 0.9, 0.9 })
  end
end

local function isFigure(obj)
  if not obj or obj.getLock() then return false end
  return obj.hasTag("Pokemon") or obj.type == "Figurine" or (obj.name or ""):find("Figurine_Custom", 1, true) ~= nil
end

-- Per-figure state lives in its memo as JSON: { pokemon = name, status = key|nil, confused = true|nil, flinched = true|nil }
function figureState(obj)
  local ok, st = pcall(JSON.decode, obj.memo or "")
  if not ok or type(st) ~= "table" then st = {} end
  st.pokemon = st.pokemon or obj.getName()
  return st
end

function paintFigure(obj, st)
  local key = st.status or (st.confused and "confused") or (st.flinched and "flinched") or nil
  local def = key and STATUS_BY_KEY[key]
  local r, g, b = 1, 1, 1
  if def then r, g, b = hexRGB(mixHex("#FFFFFF", def.color, def.strength or STATUS_TINT)) end
  obj.setColorTint({ r = r, g = g, b = b })
  local labels = {}
  if st.status then labels[#labels + 1] = STATUS_BY_KEY[st.status].label end
  if st.confused then labels[#labels + 1] = "Confused" end
  if st.flinched then labels[#labels + 1] = "Flinched" end
  obj.setDescription(#labels > 0 and ("Status: " .. table.concat(labels, ", ")) or "")
end

function applyStatus(obj, key)
  local st, def = figureState(obj), STATUS_BY_KEY[key]
  if key == "clear" then
    st.status, st.confused, st.flinched = nil, nil, nil
  elseif def.volatile then
    st[key] = (not st[key]) or nil   -- toggles
  else
    st.status = (st.status ~= key) and key or nil  -- replaces the main status, or removes it if it's the same
  end
  obj.memo = JSON.encode(st)
  paintFigure(obj, st)
end

function onObjectPickUp(color, obj)
  if obj.hasTag("Pokemon") then   -- lifted off its pedestal or out of a zone: the sign empties, the zone recounts
    Wait.time(refreshPedestals, 0.3)
    Wait.time(refreshZones, 0.3)
  end
  local key = armed[color]
  if not key or not isFigure(obj) then return end
  armed[color] = nil
  applyStatus(obj, key)
  refreshStatus(color)
end

----------------------------------------------------------------------------------------------------
-- Arena pieces (tools/place_pieces.py puts them on the board): bells, and flags that show who holds them.
-- A flag takes the colour of the last Pokémon put down on its tile (its owner's seat colour) and keeps it until
-- another one is put down there; a left-click makes it neutral again. Its cloth is white, so its tint is the
-- holder's colour; its memo keeps the holder's seat colour.
----------------------------------------------------------------------------------------------------
local function piecesTagged(tag)
  local list = {}
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag(tag) then list[#list + 1] = o end
  end
  table.sort(list, function(a, b) return a.guid < b.guid end)
  return list
end

NEUTRAL = { r = 0.6, g = 0.58, b = 0.54 }   -- an unclaimed flag or capture zone
FLAG_DESC = "Flag. It takes the colour of the last Pokémon put down on its tile; left-click it to make it neutral."
FLAG_INSET = 0.38   -- tools/place_pieces.py: a flag's pole stands this far from the two edges of its tile's corner

-- color = the seat colour that now holds the flag (nil = neutral)
function setFlagHolder(obj, color)
  obj.setColorTint(color and Color.fromString(color) or NEUTRAL)
  obj.memo = color or ""
end

-- The flag whose tile a position is on, if any. A flag stands in the corner of its tile farthest from the board's
-- centre, so its tile's centre is half a tile (less the inset) back toward the centre.
function flagAt(pos)
  local back = BOARD_TILE / 2 - FLAG_INSET
  for _, flag in ipairs(piecesTagged("Flag")) do
    local f = flag.getPosition()
    local cx = f.x - (f.x >= BOARD_SPOT[1] and back or -back)
    local cz = f.z - (f.z >= BOARD_SPOT[3] and back or -back)
    if math.abs(pos.x - cx) < BOARD_TILE / 2 and math.abs(pos.z - cz) < BOARD_TILE / 2 and math.abs(pos.y - f.y) < 3 then
      return flag
    end
  end
end

-- A Pokémon put down: the flag on its tile (if any) takes its owner's colour.
function flagTaken(obj)
  local flag = obj and flagAt(obj.getPosition())
  local owner = flag and figureState(obj).owner
  if owner then setFlagHolder(flag, owner) end
end

local lastClear = {}   -- flag guid -> when it was last cleared (one click can arrive as a selection and a pick-up)
function flagClicked(flag, player)
  local hover = player and player.getHoverObject and player.getHoverObject()
  if hover and hover ~= flag then return end   -- a box selection, not a click on it
  local now = os.clock()
  if lastClear[flag.guid] and now - lastClear[flag.guid] < 0.4 then return end
  lastClear[flag.guid] = now
  setFlagHolder(flag, nil)
end

local function memoTable(obj)
  local ok, t = pcall(JSON.decode, obj.memo or "")
  return (ok and type(t) == "table") and t or {}
end

-- A clear button lying on a piece (object UI: 100 units = 1 world unit, canvas y = the object's z, -z = up),
-- with an icon that reads the same from either side of the table. No hover text on buttons (the user's call).
local function pieceButtonXml(id, x, z, y, onClick, icon)
  return string.format([[
<Button id="%s" position="%d %d %d" width="56" height="56" onClick="Global/%s"
  colors="#00000040|#FFFFFF66|#FFFFFF99|#00000040"/>
<Image image="%s" position="%d %d %d" width="46" height="46" raycastTarget="false" color="#FFFFFFE0" preserveAspect="true"/>
]], id, math.floor(x * 100 + 0.5), math.floor(z * 100 + 0.5), math.floor(-y * 100 + 0.5), onClick,
    icon, math.floor(x * 100 + 0.5), math.floor(z * 100 + 0.5), math.floor(-y * 100 - 0.5))
end

----------------------------------------------------------------------------------------------------
-- Portals (Illusio): round tiles in pairs, each pair one colour. The die on any portal shuffles them: every
-- portal gets a new partner at random (any two can end up paired) and the colours show the new pairs.
----------------------------------------------------------------------------------------------------
PORTAL_COLORS = { { name = "magenta", hex = "#E94FF0" }, { name = "cyan", hex = "#2BD3F2" }, { name = "gold", hex = "#FFC22E" } }
PORTAL_BUTTON = { x = 0.74, z = -0.74, y = 0.06 }   -- off the middle, where a Pokémon's base doesn't cover it

function portalTint(pair)
  local r, g, b = hexRGB(PORTAL_COLORS[pair].hex)
  return { r = r, g = g, b = b }
end

function setPortalPair(obj, pair)
  obj.memo = JSON.encode({ pair = pair })
  obj.setColorTint(portalTint(pair))
  obj.setDescription("A " .. PORTAL_COLORS[pair].name .. " portal. A Pokémon that ends its turn here comes out next to "
    .. "the other " .. PORTAL_COLORS[pair].name .. " portal (unless a Pokémon is on it). Click the die to shuffle "
    .. "the portals.")
end

function shufflePortals()
  local portals = piecesTagged("Portal")
  if #portals < 2 then return end
  local order = {}
  for i = 1, #portals do order[i] = i end
  for i = #order, 2, -1 do
    local j = math.random(i)
    order[i], order[j] = order[j], order[i]
  end
  for k, i in ipairs(order) do setPortalPair(portals[i], math.floor((k + 1) / 2)) end
end

function portalClicked()
  shufflePortals()
end

----------------------------------------------------------------------------------------------------
-- Rope bridges (Illusio): flat plank decks over the sky between islands, carrying their own snap points. Up =
-- level with the islands (crossable); dropped = hanging below them (closed). They start dropped. The arrows on
-- any bridge raise them all, or drop them all, except that a bridge with a Pokémon on it stays up (the rules:
-- it doesn't close until the next time they all do). Right-click a bridge to raise or drop just that one.
-- Greenleaf's grass bridge goes by the same rule. It's two halves (a "group"), a mat of grass along each hedge
-- beside the creek: open, they've grown out of their hedges over the water to meet in the middle; closed, they're
-- drawn back inside the hedges. They start closed and move together, slowly (seen growing); a Pokémon on either
-- half keeps both open. The first half ("lead") carries the arrows, on top of its hedge, where they stay put
-- (a closed half is hidden in its hedge, so nothing on the half itself could be clicked); snap points only while
-- open (none hidden in the hedge).
-- Memo: rope { up, y = its height when up, tiles, tile }; grass half { up, x, y, z (where it lies open), sx, sz
-- (the move from there into its hedge), tiles, tile, group, lead, hy (the hedge's top above the mat's) }.
----------------------------------------------------------------------------------------------------
BOARD_TILE = 3.24875
BRIDGE_DROP = 1.6
BRIDGE_BUTTON = { z = 1.0, y = 0.02 }   -- beside the middle of the deck, clear of a Pokémon's base
GRASS_GROW_TIME, GRASS_GROW_FRAMES = 2.0, 120   -- a grass half grows out or draws back this slowly (game clock;
                                                -- frames without one, in the offline tests)
movingBridges = {}   -- grass half guid -> the move under way (a newer one takes over)

function bridgeState(obj)
  local st = memoTable(obj)
  st.tiles, st.tile = st.tiles or 1, st.tile or BOARD_TILE
  return st
end

local function grassBridge(st)
  return st.sx ~= nil or st.sz ~= nil
end

function bridgeSnaps(st)
  local snaps = {}
  for i = 1, st.tiles do
    snaps[i] = { position = { (i - (st.tiles + 1) / 2) * st.tile, 0.02, 0 }, rotation = { 0, 0, 0 }, rotation_snap = false }
  end
  return snaps
end

-- The Pokémon standing on a bridge, or nil.
function pokemonOnBridge(bridge)
  local st = bridgeState(bridge)
  local half = st.tiles * st.tile / 2
  for _, obj in ipairs(getAllObjects()) do
    if obj.hasTag("Pokemon") then
      local p = bridge.positionToLocal(obj.getPosition())
      if math.abs(p.x) <= half + 0.2 and math.abs(p.z) <= 1.6 and p.y > -0.5 and p.y < 3 then return obj end
    end
  end
end

function bridgeDescription(up, st)
  if st and grassBridge(st) then
    return (up and "Open: grown over the creek; Pokémon can cross it." or "Closed.") .. " It opens or closes every "
      .. "second turn: click the arrows on the hedge beside it. With a Pokémon on it, it stays open until the next time."
  end
  return (up and "Up: Pokémon can cross it." or "Dropped: closed.") .. " The bridges go up or down together every "
    .. "second turn: click the arrows on any bridge. One with a Pokémon on it stays up until the next time. "
    .. "Right-click it to raise or drop just this one."
end

-- A grass half's snap points (open only), description, and on the lead half the arrows on top of its hedge: the
-- same spot open or closed (the lead is never turned, so its own frame is the world's).
function grassBridgeUI(obj, st)
  st = st or bridgeState(obj)
  obj.setSnapPoints(st.up and bridgeSnaps(st) or {})
  obj.setDescription(bridgeDescription(st.up, st))
  if st.lead then
    local bx, bz = st.up and (st.sx or 0) or 0, st.up and (st.sz or 0) or 0
    obj.UI.setCustomAssets({ { name = "updown", url = BASE_URL .. PIECE_ICONS.updown } })
    obj.UI.setXml(pieceButtonXml("bridgeArrows", bx, bz, (st.hy or 0) + 0.02, "bridgeClicked",
      "updown"))
  end
end

-- Move a grass half to `to` a little each frame, eased, so it's seen growing out of its hedge or drawing back;
-- then `done`.
local function growGrass(obj, to, done)
  local p0, token = obj.getPosition(), {}
  movingBridges[obj.guid] = token
  local clock = Time and Time.time and function() return Time.time end
  local k, t0 = 0, clock and clock()
  local function step()
    if obj == nil or movingBridges[obj.guid] ~= token then return end   -- gone (map changed), or moving again
    k = k + 1
    local t = math.min(1, clock and (clock() - t0) / GRASS_GROW_TIME or k / GRASS_GROW_FRAMES)
    local e = t * t * (3 - 2 * t)
    obj.setPosition({ p0.x + (to.x - p0.x) * e, p0.y + (to.y - p0.y) * e, p0.z + (to.z - p0.z) * e })
    if t < 1 then
      Wait.frames(step, 1)
    else
      movingBridges[obj.guid] = nil
      if done then done() end
    end
  end
  step()
end

function setBridgeUp(obj, up)
  local st = bridgeState(obj)
  if (st.up and true or false) == up then return false end
  st.up = up
  obj.memo = JSON.encode(st)
  if grassBridge(st) and st.x then
    if st.lead then obj.UI.setXml("") end   -- the arrows come back on the hedge once it has moved
    obj.setSnapPoints({})
    local to = up and Vector(st.x, st.y, st.z) or Vector(st.x + (st.sx or 0), st.y, st.z + (st.sz or 0))
    growGrass(obj, to, function() grassBridgeUI(obj) end)
    return true
  end
  local p = obj.getPosition()
  if st.y then obj.setPositionSmooth(Vector(p.x, up and st.y or st.y - BRIDGE_DROP, p.z), false, false) end
  obj.setDescription(bridgeDescription(up, st))
  return true
end

-- Raise them all if any is down; otherwise drop them all except the ones with a Pokémon on them (a grass bridge:
-- both halves stay if either has one).
function toggleBridges()
  local bridges, anyDown, held = piecesTagged("Bridge"), false, {}
  if #bridges == 0 then return end
  for _, b in ipairs(bridges) do
    local st = bridgeState(b)
    if not st.up then anyDown = true end
    if not anyDown and pokemonOnBridge(b) then held[st.group or b.guid] = true end
  end
  for _, b in ipairs(bridges) do
    if anyDown or not held[bridgeState(b).group or b.guid] then setBridgeUp(b, anyDown) end
  end
end

-- Open or close a grass bridge (both halves) from either half's menu.
function setBridgeGroupUp(obj, up)
  local g = bridgeState(obj).group
  for _, b in ipairs(piecesTagged("Bridge")) do
    if b == obj or (g and bridgeState(b).group == g) then setBridgeUp(b, up) end
  end
end

function bridgeClicked()
  toggleBridges()
end

----------------------------------------------------------------------------------------------------
-- Capture zones (Ingis): a frame around each zone takes the colour of the player with more Pokémon inside it
-- (fainted ones don't count); a tie or an empty zone is neutral. It updates whenever a Pokémon is put down,
-- picked up, removed or faints, so at the end of a turn it shows who captures the zone.
-- A Pokémon belongs to the player whose toolbar spawned it, or else the first seated player to put it down
-- (its memo's owner).
----------------------------------------------------------------------------------------------------
ZONE_DESC = "Capture zone. At the end of each turn the player with more Pokémon in it captures it (a tie: neither). "
  .. "The frame shows who that is right now."

-- The team a seat colour plays for (nil for spectators and the game master).
function teamColor(color)
  if not color or color == "Grey" or color == "Black" then return nil end
  for _, c in ipairs(COLORS) do
    if c == color then return color end
  end
end

-- Give an ownerless Pokémon to the seated player putting it down.
function claimPokemon(obj, color)
  local team = teamColor(color)
  if not team then return end
  local st = figureState(obj)
  if st.owner then return end
  st.owner = team
  obj.memo = JSON.encode(st)
end

-- The owner with the most Pokémon (not fainted) inside a zone, or nil on a tie / none.
function zoneLeader(zone)
  local st = memoTable(zone)
  local half = (st.tiles or 2) * (st.tile or BOARD_TILE) / 2
  local counts = {}
  for _, obj in ipairs(getAllObjects()) do
    if obj.hasTag("Pokemon") then
      local p = zone.positionToLocal(obj.getPosition())
      if math.abs(p.x) < half and math.abs(p.z) < half and p.y > -0.5 and p.y < 3 then
        local f = figureState(obj)
        if f.owner and (f.hp == nil or f.hp > 0) then counts[f.owner] = (counts[f.owner] or 0) + 1 end
      end
    end
  end
  local best, n, tie = nil, 0, false
  for owner, k in pairs(counts) do
    if k > n then best, n, tie = owner, k, false elseif k == n then tie = true end
  end
  if tie then return nil end
  return best
end

function refreshZones()
  for _, zone in ipairs(piecesTagged("Zone")) do
    local st = memoTable(zone)
    local leader = zoneLeader(zone)
    if leader ~= st.holder then
      st.holder = leader
      zone.memo = JSON.encode(st)
    end
    zone.setColorTint(leader and Color.fromString(leader) or NEUTRAL)
  end
end

----------------------------------------------------------------------------------------------------
-- Water gates (Fontaine): a river runs in from each corner past an edge gate, on past an inner gate, and into
-- the middle, where the four branches meet round the island. A gate is four stone posts (GateFrame: its button
-- and menu) and a sluice block (Gate) that rises between them to close it. Closing an edge gate drains its whole
-- branch (with that branch's quarter of the middle); closing an inner gate drains the river past it. Each river
-- tile's water is a slab (Water), sunk out of sight while dry. Gates start open. Memos: { gate, branch, part,
-- open (Gate), y = its height when up (Gate, Water) }.
----------------------------------------------------------------------------------------------------
GATE_DROP = 1.16        -- an open gate's block sinks this far: below the river bed
WATER_DROP = 0.75       -- dry water sinks this far: below the river bed
GATE_BUTTON = { x = 1.29, z = -1.29, y = 1.57 }   -- on top of a corner post
GATE_DESC = "Water gate. Click the arrows (or right-click) to open or close it; closing it drains the river past it."

-- Every Water tile up (wet) or sunk (dry): wet while the gates upstream of it are open.
function refreshWater()
  local open = {}   -- branch -> part -> open
  for _, gate in ipairs(piecesTagged("Gate")) do
    local st = memoTable(gate)
    if st.branch then
      open[st.branch] = open[st.branch] or {}
      open[st.branch][st.part] = st.open ~= false
    end
  end
  for _, water in ipairs(piecesTagged("Water")) do
    local st = memoTable(water)
    local branch = open[st.branch] or {}
    local wet = branch.edge ~= false and (st.part == "edge" or branch.inner ~= false)
    if st.y then
      local p = water.getPosition()
      local y = wet and st.y or st.y - WATER_DROP
      if math.abs(p.y - y) > 0.01 then water.setPositionSmooth(Vector(p.x, y, p.z), false, false) end
    end
  end
end

function setGateOpen(n, open)
  for _, gate in ipairs(piecesTagged("Gate")) do
    local st = memoTable(gate)
    if st.gate == n and (st.open ~= false) ~= open then
      st.open = open
      gate.memo = JSON.encode(st)
      local p = gate.getPosition()
      if st.y then gate.setPositionSmooth(Vector(p.x, open and st.y - GATE_DROP or st.y, p.z), false, false) end
    end
  end
  refreshWater()
end

function toggleGate(n)
  for _, gate in ipairs(piecesTagged("Gate")) do
    local st = memoTable(gate)
    if st.gate == n then return setGateOpen(n, st.open == false) end
  end
end

-- The arrows on a gate's post: its id is "gate_<number>".
function gateClicked(_, _, id)
  local n = tonumber(tostring(id or ""):sub(6))
  if n then toggleGate(n) end
end

----------------------------------------------------------------------------------------------------
-- Gears and blockers (Valora). A gear is a steel plate (Gear) lying on its tiles: its button (or right-click > Turn
-- gear) turns it 270 degrees the way its arrows point, carrying whatever stands on it round with it (Pokémon keep
-- the way they face; nothing is teleported: the plate and its riders sweep round together). A numbered gear (1-3)
-- also has a doors button that opens or closes its blockers (Door): steel blocks that slide into the wall beside
-- them, or sink into the floor where there's no wall. Blockers start closed.
-- Memos: Gear { gear (0: unnumbered), size, turn ("ccw"/"cw" seen from above), tile }; Door { door, open,
-- x, y, z (where it stands closed), sx, sy, sz (the move that opens it) }.
----------------------------------------------------------------------------------------------------
GEAR_TURN_TIME = 2.5     -- seconds a turn takes (timed by the game clock: the frame rate varies a lot)
GEAR_TURN_FRAMES = 150   -- without a game clock (offline tests), this many frames instead
GEAR_T = 0.05            -- tools/build_pieces.py: a gear plate's thickness
GEAR_BUTTON_IN = 0.55    -- its buttons sit this far in from two of its edges, in opposite corner tiles
turningGears = {}        -- gear guid -> true while it turns

function gearState(obj)
  local st = memoTable(obj)
  st.size, st.tile, st.turn, st.gear = st.size or 4, st.tile or BOARD_TILE, st.turn or "ccw", st.gear or 0
  return st
end

-- A snap point on every tile of the plate (the board has none under it).
function gearSnaps(st)
  local snaps, h = {}, (st.size - 1) / 2
  for i = 0, st.size - 1 do
    for j = 0, st.size - 1 do
      snaps[#snaps + 1] = { position = { (i - h) * st.tile, GEAR_T + 0.02, (j - h) * st.tile }, rotation = { 0, 0, 0 },
        rotation_snap = false }
    end
  end
  return snaps
end

-- What rides on a gear: anything loose (Pokémon, gift boxes) resting over its tiles and not in someone's hand.
function gearRiders(plate, st)
  local c, half, riders = plate.getPosition(), st.size * st.tile / 2, {}
  for _, o in ipairs(getAllObjects()) do
    if o ~= plate and not o.getLock() and not o.held_by_color then
      local p = o.getPosition()
      if math.abs(p.x - c.x) < half and math.abs(p.z - c.z) < half and p.y > c.y - 0.5 and p.y < c.y + 5 then
        riders[#riders + 1] = { obj = o, dx = p.x - c.x, dz = p.z - c.z, y = p.y }
      end
    end
  end
  return riders
end

-- Turn a gear 270 degrees the way its arrows point, a little each frame, its riders swept round with it (held still
-- meanwhile: locked, so physics doesn't drop them, and unlocked again at the end). Seen from above with player 1's
-- side at the bottom, "ccw" is counter-clockwise; in TTS a positive yaw turns clockwise.
function turnGear(plate)
  if not plate or turningGears[plate.guid] then return false end
  local st = gearState(plate)
  local c, riders, yaw0 = plate.getPosition(), gearRiders(plate, st), plate.getRotation().y
  local sign = st.turn == "cw" and -1 or 1
  turningGears[plate.guid] = true
  for _, r in ipairs(riders) do r.obj.setLock(true) end
  local clock = Time and Time.time and function() return Time.time end
  local k, t0 = 0, clock and clock()
  local function step()
    k = k + 1
    local t = math.min(1, clock and (clock() - t0) / GEAR_TURN_TIME or k / GEAR_TURN_FRAMES)
    local a = sign * math.rad(270) * t * t * (3 - 2 * t)   -- eased in and out
    local ca, sa = math.cos(a), math.sin(a)
    plate.setRotation({ 0, (yaw0 - math.deg(a)) % 360, 0 })
    for _, r in ipairs(riders) do
      r.obj.setPosition({ c.x + r.dx * ca - r.dz * sa, r.y, c.z + r.dx * sa + r.dz * ca })
    end
    if t < 1 then
      Wait.frames(step, 1)
    else
      for _, r in ipairs(riders) do r.obj.setLock(false) end
      turningGears[plate.guid] = nil
    end
  end
  step()
  return true
end

function setDoorsOpen(n, open)
  for _, door in ipairs(piecesTagged("Door")) do
    local st = memoTable(door)
    if st.door == n and (st.open == true) ~= open then
      st.open = open
      door.memo = JSON.encode(st)
      if st.x then
        local to = Vector(st.x, st.y, st.z)
        if open then to = Vector(st.x + (st.sx or 0), st.y + (st.sy or 0), st.z + (st.sz or 0)) end
        door.setPositionSmooth(to, false, false)
      end
    end
  end
end

function toggleDoors(n)
  for _, door in ipairs(piecesTagged("Door")) do
    local st = memoTable(door)
    if st.door == n then return setDoorsOpen(n, st.open ~= true) end
  end
end

-- A gear's buttons: "gear_<its guid>" turns it, "doors_<number>" opens or closes that number's blockers.
function gearClicked(_, _, id)
  local plate = getObjectFromGUID(tostring(id or ""):sub(6))
  if plate then turnGear(plate) end
end

function doorsClicked(_, _, id)
  local n = tonumber(tostring(id or ""):sub(7))
  if n then toggleDoors(n) end
end

----------------------------------------------------------------------------------------------------
-- Flowers (Greenleaf): a flat bloom lying on its tile. Its button (or right-click > Fling Pokémon) throws the Pokémon
-- standing on it to one of the flower's numbered spots at random, in an arc you can watch (it keeps the way it
-- faces). A spot something stands on is left out; with all of them taken nothing happens (the rules).
-- Its memo: { targets = { {dx, dy, dz}, ... } (from its tile top to each spot's), tile }.
----------------------------------------------------------------------------------------------------
FLOWER_T = 0.06                         -- tools/build_pieces.py: the bloom's thickness
FLOWER_BUTTON = { x = 0.86, z = -0.86 }   -- on a petal, clear of a Pokémon's base
FLING_TIME, FLING_FRAMES = 1.2, 72      -- seconds a throw takes (game clock); frames without one (offline tests)
FLING_PEAK = 3.5                        -- how high the arc goes (plus a quarter of the distance)
FLOWER_DESC = "Flower. A Pokémon that ends its turn here is flung to one of its three numbered spots at random (not "
  .. "one that's taken), keeping its facing. Click the arrows on it to fling."
flinging = {}                           -- flower guid -> true while it throws

function flowerState(obj)
  local st = memoTable(obj)
  st.targets, st.tile = st.targets or {}, st.tile or BOARD_TILE
  return st
end

local function overTile(o, x, y, z, half)
  local p = o.getPosition()
  return math.abs(p.x - x) < half and math.abs(p.z - z) < half and p.y > y - 0.5 and p.y < y + 5
end

-- The Pokémon standing on a flower (not one in someone's hand), or nil.
function pokemonOnFlower(flower)
  local c, half = flower.getPosition(), flowerState(flower).tile / 2
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("Pokemon") and not o.held_by_color and overTile(o, c.x, c.y, c.z, half) then return o end
  end
end

-- A flower's spots with nothing on them (a Pokémon, or anything loose), as the tops of their tiles.
function freeFlowerSpots(flower, thrown)
  local c, st = flower.getPosition(), flowerState(flower)
  local half, free = st.tile / 2 - 0.05, {}
  for _, t in ipairs(st.targets) do
    local x, y, z = c.x + (t[1] or 0), c.y + (t[2] or 0), c.z + (t[3] or 0)
    local taken = false
    for _, o in ipairs(getAllObjects()) do
      if o ~= thrown and o ~= flower and (o.hasTag("Pokemon") or not o.getLock()) and overTile(o, x, y, z, half) then
        taken = true
      end
    end
    if not taken then free[#free + 1] = Vector(x, y, z) end
  end
  return free
end

-- Throw the Pokémon on a flower to one of its free spots: along an arc, a little each frame (locked meanwhile so
-- physics leaves it alone), landing at the same height above the ground as it stood on the flower.
function flingFromFlower(flower)
  if not flower or flinging[flower.guid] then return false end
  local mon = pokemonOnFlower(flower)
  if not mon then return false end
  local spots = freeFlowerSpots(flower, mon)
  if #spots == 0 then return false end
  local to = spots[math.random(#spots)]
  local from = mon.getPosition()
  local lift = math.max(0, from.y - (flower.getPosition().y + FLOWER_T))
  local dest = Vector(to.x, to.y + lift, to.z)
  local dx, dz = dest.x - from.x, dest.z - from.z
  local peak = FLING_PEAK + 0.25 * math.sqrt(dx * dx + dz * dz)
  local wasLocked = mon.getLock()
  flinging[flower.guid] = true
  mon.setLock(true)
  local clock = Time and Time.time and function() return Time.time end
  local k, t0 = 0, clock and clock()
  local function step()
    k = k + 1
    local t = math.min(1, clock and (clock() - t0) / FLING_TIME or k / FLING_FRAMES)
    mon.setPosition({ from.x + dx * t, from.y + (dest.y - from.y) * t + 4 * peak * t * (1 - t), from.z + dz * t })
    if t < 1 then
      Wait.frames(step, 1)
    else
      mon.setLock(wasLocked)
      flinging[flower.guid] = nil
      flagTaken(mon)
    end
  end
  step()
  return true
end

-- A flower's button: its id is "fling_<its guid>".
function flowerClicked(_, _, id)
  local flower = getObjectFromGUID(tostring(id or ""):sub(7))
  if flower then flingFromFlower(flower) end
end

----------------------------------------------------------------------------------------------------
-- Floating platforms (Avia): a wooden deck in the sky, level with the land, moving along an L. Its button (an L arrow
-- the shape of its track) or right-click > Move platform glides it along its track, round the bend, to the other
-- end, carrying whatever stands on it (Pokémon keep the way they face); the next time it goes back. Its memo:
-- { route = { {dx, dy, dz}, ... } (the bend and the far end, from its first tile), x, y, z (its first tile),
-- at = 1 (there) or #route + 1 (at the far end), tile, arms (its L's arms from the bend, "ne" ...: the icon) }.
----------------------------------------------------------------------------------------------------
PLATFORM_GLIDE_TIME, PLATFORM_GLIDE_FRAMES = 2.0, 120   -- seconds a move takes (game clock); frames without one
PLATFORM_BUTTON = { x = 1.12, z = -1.12, y = 0.01 }      -- in a corner of the deck, clear of a Pokémon's base
PLATFORM_DESC = "Floating platform. When a Pokémon ends its move on it, it glides along its track to the other end, "
  .. "taking the Pokémon with it. Click the arrow on it to move it."
gliding = {}                                            -- platform guid -> true while it moves

function platformState(obj)
  local st = memoTable(obj)
  st.route, st.tile, st.at = st.route or {}, st.tile or BOARD_TILE, st.at or 1
  return st
end

-- Its stops in order: its first tile, then the route's (world positions of the deck's top).
function platformStops(st)
  local stops = { Vector(st.x, st.y, st.z) }
  for _, r in ipairs(st.route) do
    stops[#stops + 1] = Vector(st.x + (r[1] or 0), st.y + (r[2] or 0), st.z + (r[3] or 0))
  end
  return stops
end

-- What rides on a platform: anything loose (Pokémon, gift boxes) over its deck and not in someone's hand.
function platformRiders(plat, st)
  local c, half, riders = plat.getPosition(), st.tile / 2, {}
  for _, o in ipairs(getAllObjects()) do
    if o ~= plat and not o.getLock() and not o.held_by_color then
      local p = o.getPosition()
      if math.abs(p.x - c.x) < half and math.abs(p.z - c.z) < half and p.y > c.y - 0.5 and p.y < c.y + 5 then
        riders[#riders + 1] = { obj = o, dx = p.x - c.x, dy = p.y - c.y, dz = p.z - c.z }
      end
    end
  end
  return riders
end

-- Glide a platform to the other end of its route, a little each frame (eased in and out over the whole way, round
-- the bend), its riders with it (locked meanwhile so physics doesn't drop them, unlocked at the end).
function movePlatform(plat)
  if not plat or gliding[plat.guid] then return false end
  local st = platformState(plat)
  if not st.x or #st.route == 0 then return false end
  local stops, path = platformStops(st), {}
  local back = st.at > 1
  for i = 1, #stops do path[i] = stops[back and #stops + 1 - i or i] end
  path[1] = plat.getPosition()   -- from where it actually is
  local legs, total = {}, 0
  for i = 2, #path do
    local a, b = path[i - 1], path[i]
    legs[i] = math.sqrt((b.x - a.x) ^ 2 + (b.y - a.y) ^ 2 + (b.z - a.z) ^ 2)
    total = total + legs[i]
  end
  local riders = platformRiders(plat, st)
  gliding[plat.guid] = true
  for _, r in ipairs(riders) do r.obj.setLock(true) end
  local clock = Time and Time.time and function() return Time.time end
  local k, t0 = 0, clock and clock()
  local function finish()
    for _, r in ipairs(riders) do
      if r.obj ~= nil then r.obj.setLock(false) end
    end
    gliding[plat.guid] = nil
  end
  local function step()
    if plat == nil then   -- gone (the map changed)
      finish()
      return
    end
    k = k + 1
    local t = math.min(1, clock and (clock() - t0) / PLATFORM_GLIDE_TIME or k / PLATFORM_GLIDE_FRAMES)
    local s = total * t * t * (3 - 2 * t)
    local i = 2
    while i < #path and s > legs[i] do
      s = s - legs[i]
      i = i + 1
    end
    local a, b = path[i - 1], path[i]
    local f = legs[i] > 0 and math.min(1, s / legs[i]) or 1
    local x, y, z = a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f, a.z + (b.z - a.z) * f
    plat.setPosition({ x, y, z })
    for _, r in ipairs(riders) do
      if r.obj ~= nil then r.obj.setPosition({ x + r.dx, y + r.dy, z + r.dz }) end
    end
    if t < 1 then
      Wait.frames(step, 1)
    else
      st.at = back and 1 or #stops
      plat.memo = JSON.encode(st)
      finish()
    end
  end
  step()
  return true
end

-- A platform's button: its id is "glide_<its guid>".
function platformClicked(_, _, id)
  local plat = getObjectFromGUID(tostring(id or ""):sub(7))
  if plat then movePlatform(plat) end
end

----------------------------------------------------------------------------------------------------
-- Traps (Chrysalia): a trap piece on its tile; once it has caught a Pokémon, right-click > Spring trap removes it.
----------------------------------------------------------------------------------------------------
TRAP_DESC = "Trap. A Pokémon that ends its turn here finishes its activation and skips its next one; then the trap "
  .. "is used up (right-click > Spring trap removes it)."

-- Buttons, menus and snap points for an arena piece (after it spawns, and again on load: none of it is reliably
-- kept by a save).
function pieceSetup(obj)
  if not obj then return end
  if obj.hasTag("ArenaBackdrop") or obj.hasTag("Board3D") or obj.hasTag("Pillar") then   -- unselectable
    obj.interactable = false
    return
  end
  if obj.hasTag("SpectatorStand") then   -- the turn track's slots (the token snaps to them) and its gold last turn
    if #(obj.getSnapPoints() or {}) ~= TURN_TRACK.turns then obj.setSnapPoints(turnSnaps()) end
    showLastTurn(obj)
    return
  end
  if obj.hasTag("Pedestal") then   -- a Pokémon dropped near snaps onto its middle
    if #(obj.getSnapPoints() or {}) ~= 1 then obj.setSnapPoints({ { position = { 0, PEDESTAL_TOP, 0 }, rotation_snap = false } }) end
    return
  end
  if obj.hasTag("TurnTrack") then  -- the separate track of an older layout: the spectator stand has it now
    obj.destruct()
    return
  end
  if obj.hasTag("Flag") then
    obj.setDescription(FLAG_DESC)
  elseif obj.hasTag("Portal") then
    local pair = memoTable(obj).pair or 1
    setPortalPair(obj, PORTAL_COLORS[pair] and pair or 1)
    obj.UI.setCustomAssets({ { name = "die", url = BASE_URL .. PIECE_ICONS.die } })
    obj.UI.setXml(pieceButtonXml("portalDie", PORTAL_BUTTON.x, PORTAL_BUTTON.z, PORTAL_BUTTON.y, "portalClicked",
      "die"))
    obj.clearContextMenu()
    obj.addContextMenuItem("Shuffle portals", function(color) shufflePortals(color) end)
  elseif obj.hasTag("Trap") then
    obj.setDescription(TRAP_DESC)
    obj.clearContextMenu()
    obj.addContextMenuItem("Spring trap", function() obj.destruct() end)
  elseif obj.hasTag("Zone") then
    obj.setDescription(ZONE_DESC)
    Wait.frames(refreshZones, 1)
  elseif obj.hasTag("Bridge") then
    local st = bridgeState(obj)
    obj.clearContextMenu()
    if grassBridge(st) then   -- a grass half (only seen, and so right-clicked, while it's open)
      grassBridgeUI(obj, st)
      obj.addContextMenuItem("Open the bridge", function() setBridgeGroupUp(obj, true) end)
      obj.addContextMenuItem("Close the bridge", function() setBridgeGroupUp(obj, false) end)
    else
      if #(obj.getSnapPoints() or {}) ~= st.tiles then obj.setSnapPoints(bridgeSnaps(st)) end
      obj.setDescription(bridgeDescription(st.up))
      obj.UI.setCustomAssets({ { name = "updown", url = BASE_URL .. PIECE_ICONS.updown } })
      obj.UI.setXml(pieceButtonXml("bridgeArrows", 0, BRIDGE_BUTTON.z, BRIDGE_BUTTON.y, "bridgeClicked",
        "updown"))
      obj.addContextMenuItem("Raise this bridge", function() setBridgeUp(obj, true) end)
      obj.addContextMenuItem("Drop this bridge", function() setBridgeUp(obj, false) end)
    end
  elseif obj.hasTag("GateFrame") then
    local n = memoTable(obj).gate or 0
    obj.setDescription(GATE_DESC)
    obj.UI.setCustomAssets({ { name = "updown", url = BASE_URL .. PIECE_ICONS.updown } })
    obj.UI.setXml(pieceButtonXml("gate_" .. n, GATE_BUTTON.x, GATE_BUTTON.z, GATE_BUTTON.y, "gateClicked",
      "updown"))
    obj.clearContextMenu()
    obj.addContextMenuItem("Open gate", function() setGateOpen(n, true) end)
    obj.addContextMenuItem("Close gate", function() setGateOpen(n, false) end)
  elseif obj.hasTag("Gate") then
    obj.interactable = false   -- opened and closed through its posts
  elseif obj.hasTag("Gear") then
    local st = gearState(obj)
    if #(obj.getSnapPoints() or {}) ~= st.size * st.size then obj.setSnapPoints(gearSnaps(st)) end
    local icon, h = st.turn == "cw" and "turncw" or "turnccw", st.size * st.tile / 2 - GEAR_BUTTON_IN
    local assets = { { name = icon, url = BASE_URL .. PIECE_ICONS[icon] } }
    local xml = pieceButtonXml("gear_" .. obj.guid, h, -h, GEAR_T + 0.01, "gearClicked", icon)
    obj.clearContextMenu()
    obj.addContextMenuItem("Turn gear", function() turnGear(obj) end)
    if st.gear > 0 then
      assets[2] = { name = "doors", url = BASE_URL .. PIECE_ICONS.doors }
      xml = xml .. pieceButtonXml("doors_" .. st.gear, -h, h, GEAR_T + 0.01, "doorsClicked",
        "doors")
      obj.addContextMenuItem("Blockers " .. st.gear .. " open/close", function() toggleDoors(st.gear) end)
    end
    obj.UI.setCustomAssets(assets)
    obj.UI.setXml(xml)
  elseif obj.hasTag("Flower") then
    if #(obj.getSnapPoints() or {}) ~= 1 then   -- the tile's snap point, on the bloom
      obj.setSnapPoints({ { position = { 0, FLOWER_T + 0.02, 0 }, rotation = { 0, 0, 0 }, rotation_snap = false } })
    end
    obj.setDescription(FLOWER_DESC)
    obj.UI.setCustomAssets({ { name = "fling", url = BASE_URL .. PIECE_ICONS.fling } })
    obj.UI.setXml(pieceButtonXml("fling_" .. obj.guid, FLOWER_BUTTON.x, FLOWER_BUTTON.z, FLOWER_T + 0.01, "flowerClicked",
      "fling"))
    obj.clearContextMenu()
    obj.addContextMenuItem("Fling Pokémon", function() flingFromFlower(obj) end)
  elseif obj.hasTag("Platform") then
    if #(obj.getSnapPoints() or {}) ~= 1 then   -- its tile's snap point, on the deck
      obj.setSnapPoints({ { position = { 0, 0.02, 0 }, rotation = { 0, 0, 0 }, rotation_snap = false } })
    end
    obj.setDescription(PLATFORM_DESC)
    local icon = "glide-" .. (platformState(obj).arms or "ne")
    if not PIECE_ICONS[icon] then icon = "glide-ne" end
    obj.UI.setCustomAssets({ { name = icon, url = BASE_URL .. PIECE_ICONS[icon] } })
    obj.UI.setXml(pieceButtonXml("glide_" .. obj.guid, PLATFORM_BUTTON.x, PLATFORM_BUTTON.z, PLATFORM_BUTTON.y,
      "platformClicked", icon))
    obj.clearContextMenu()
    obj.addContextMenuItem("Move platform", function() movePlatform(obj) end)
  elseif obj.hasTag("Door") then
    obj.interactable = false   -- opened and closed from its gear
  elseif obj.hasTag("Water") then
    obj.interactable = false   -- part of the board; a Pokémon can stand on it
    if #(obj.getSnapPoints() or {}) ~= 1 then
      obj.setSnapPoints({ { position = { 0, 0, 0 }, rotation_snap = false } })
    end
  end
end

function onObjectSpawn(obj)
  pieceSetup(obj)
  if obj.hasTag("Stand") then
    Wait.time(function() setupStand(obj) end, 0.5)
  elseif obj.hasTag("Pokemon") then
    plainStandee(obj)
    Wait.time(refreshPedestals, 1.5)   -- once it has landed
  elseif obj.hasTag("Pedestal") then
    Wait.time(refreshPedestals, 0.5)
  end
end

----------------------------------------------------------------------------------------------------
-- Pedestals and HP signs. A team stand's pedestals are objects of their own (tag "Pedestal", props/pedestal-v1.obj: a
-- round pedestal with a black sign floating above it), so a stand can hold a whole team of 9 and then slide to 6
-- (below). A Pokémon put on a pedestal becomes that pedestal's (the pedestal's memo keeps its guid): taken off to
-- the board, it leaves a phantom behind, its picture faintly on the pedestal (object UI: nothing to bump into), and
-- the sign keeps showing its HP; put back, the phantom goes. Another Pokémon put on the pedestal takes it over.
-- The sign shows "Y/X" on each face: TTS draws an object's UI in a fixed order regardless of which part is nearer,
-- but solid geometry hides UI behind it, so each side of the table reads its own label the right way round.
-- Click the number and type 120 to set it, -35 to take damage or +20 to heal (kept between 0 and its max).
-- Current and max HP live in the Pokémon's memo (it keeps them when it moves); the max comes from the sheet.
----------------------------------------------------------------------------------------------------
STAND_MESH, STAND_TEX = "props/stand-v2.obj", "props/stand-wood-v2.jpg"   -- the plain stand: the signs are on the pedestals
PEDESTAL = { mesh = "props/pedestal-v1.obj", plain = "props/pedestal-plain-v1.obj",
  collider = "props/pedestal-collider-v1.obj", tex = "props/pedestal-v1.jpg" }
SIGN = { y = 2.8, face = 0.03 }   -- a pedestal's sign: its centre above the pedestal's bottom (build_props.py PED_SIGN_Y)
PHANTOM = { y = 1.38, size = 200, color = "#FFFFFF8C" }   -- the picture: its centre above the pedestal's bottom, its size
BENCH_BUTTON = { x = 1.2, size = 50 }   -- beside the sign (on its player's side), level with it
HP_COLOR, HP_FAINTED = "#FFFFFF", "#FF6B6B"
PEDESTAL_REACH = 1.5 -- a Pokémon this close (sideways) to a pedestal's centre, and resting on it, counts as on it
pedestalUI = {}      -- pedestal guid -> { assets, xml } it shows (set again only when they change)
flying = {}          -- Pokémon guid -> true while it flies to or from the spectator stand
seatTaken = {}       -- spectator pedestal guid -> true while a Pokémon flies to it
sliding = {}         -- team stand guid -> true while its pedestals slide

function maxHp(name)
  local s = stats[name]
  return s and tonumber(s.hp) and math.floor(tonumber(s.hp)) or nil
end

-- A Pokémon's state with hp/maxHp filled in (and saved to its memo if they were missing or out of range).
function hpState(obj)
  local st = figureState(obj)
  local max = maxHp(st.pokemon) or (st.maxHp and math.floor(st.maxHp))
  if not max then return st end
  local hp = math.max(0, math.min(max, math.floor(st.hp or max)))
  if st.hp ~= hp or st.maxHp ~= max then
    st.hp, st.maxHp = hp, max
    obj.memo = JSON.encode(st)
  end
  return st
end

local function teamStands()
  local out = {}
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("Stand") then out[#out + 1] = o end
  end
  return out
end

-- Is this position on a stand's top where its pedestals stand? (and where, in the stand's frame)
local function onStandTop(stand, pos)
  local lp = stand.positionToLocal(pos)
  return math.abs(lp.x) <= STAND.length / 2 and math.abs(lp.z - STAND.pedestal.z) < 1
    and math.abs(lp.y - STAND.pedestal.y) < 0.6, lp
end

-- A team stand's pedestals from its player's left: { { obj = pedestal, x = along the stand (its frame) } }.
function standPedestals(stand)
  local out = {}
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("Pedestal") then
      local on, lp = onStandTop(stand, o.getPosition())
      if on then out[#out + 1] = { obj = o, x = lp.x } end
    end
  end
  table.sort(out, function(a, b) return a.x < b.x end)
  return out
end

-- (Each lookup below ends with an explicit "return nil": in TTS's Lua a function that just ends returns a "void"
-- that breaks when stored in a table.)
function pedestalStand(ped)
  for _, s in ipairs(teamStands()) do
    if onStandTop(s, ped.getPosition()) then return s end
  end
  return nil
end

-- How many pedestals a team stand has: 9 (a whole team) or 6 (the ones that play).
function standSlots(stand)
  local n = memoTable(stand).slots
  return (n == 9 or n == 6) and n or 6
end

-- The Pokémon resting on a pedestal (not in a hand, not flying), or nil.
function restingOn(ped, mons)
  local top = ped.getPosition() + Vector(0, PEDESTAL_TOP, 0)
  for _, o in ipairs(mons or getAllObjects()) do
    if o.hasTag("Pokemon") and not o.held_by_color and not flying[o.guid] then
      local p = o.getPosition()
      if near(p, top, PEDESTAL_REACH) and math.abs(p.y - top.y) < 1 then return o end
    end
  end
  return nil
end

-- A pedestal's memo: { mon = its Pokémon's guid, benched = sat out (a team stand's), spect = the spectator stand's }.
function pedestalState(ped)
  return memoTable(ped)
end

-- The Pokémon a pedestal belongs to, wherever it is now, or nil.
function pedestalMon(ped, st)
  st = st or memoTable(ped)
  local mon = st.mon and getObjectFromGUID(st.mon)
  if mon and mon.hasTag("Pokemon") then return mon end
  return nil
end

-- One face's label (an input box under 50 high hides its text). Object UI: 100 units = 1 world unit, x = x (not
-- mirrored), the UI's +y is the object's +z and -z is up.
local function signLabelXml(ped, side, rotation, z, st)
  local hp, max = st and st.hp, st and st.maxHp
  return string.format([[
<Panel position="0 %d %d" rotation="%s" width="170" height="50" color="#000000C8" active="%s">
  <InputField id="hpIn_%s_%s" onEndEdit="Global/hpEdited" text="%d" rectAlignment="MiddleLeft" offsetXY="9 0" width="84" height="50"
    fontSize="26" textColor="%s" textAlignment="MiddleRight" characterLimit="8"
    colors="#00000000|#FFFFFF22|#FFFFFF33|#00000000"/>
  <Text rectAlignment="MiddleRight" width="85" height="50" fontSize="26" color="#FFFFFF" alignment="MiddleLeft">/%d</Text>
</Panel>
]], math.floor(z * 100 + 0.5), math.floor(-SIGN.y * 100 + 0.5), rotation, hp and "true" or "false", ped.guid, side,
    hp or 0, (hp or 1) > 0 and HP_COLOR or HP_FAINTED, max or 0)
end

-- The phantom: the Pokémon's picture standing on the pedestal, see-through, facing the pedestal's player (seen
-- mirrored from behind, like a standee).
local function phantomXml()
  return string.format([[<Image image="phantom" position="0 0 %d" rotation="-90 0 0" width="%d" height="%d" color="%s" raycastTarget="false"/>
]], math.floor(-PHANTOM.y * 100 + 0.5), PHANTOM.size, PHANTOM.size, PHANTOM.color)
end

-- The bench button: standing beside the sign, facing the pedestal's player.
local function benchButtonXml(ped)
  local s, x, y = BENCH_BUTTON.size, math.floor(BENCH_BUTTON.x * 100 + 0.5), math.floor(-SIGN.y * 100 + 0.5)
  local z = math.floor(-SIGN.face * 100 + 0.5) - 1
  return string.format([[
<Button id="bench_%s" position="%d %d %d" rotation="-90 0 0" width="%d" height="%d" onClick="Global/benchClicked"
  colors="#000000B0|#FFFFFF66|#FFFFFF99|#000000B0"/>
<Image image="bench" position="%d %d %d" rotation="-90 0 0" width="%d" height="%d" raycastTarget="false" color="#FFFFFFE0" preserveAspect="true"/>
]], ped.guid, x, z, y, s, s, x, z - 1, y, s - 10, s - 10)
end

-- A team pedestal's UI: the sign, the phantom while its Pokémon is away, the bench button while its stand holds 9.
function updatePedestal(ped, st, mon, resting, stand)
  local hp = mon and hpState(mon)
  if hp and not hp.maxHp then hp = nil end
  local parts = { signLabelXml(ped, "F", "-90 0 0", -SIGN.face, hp), signLabelXml(ped, "B", "90 0 180", SIGN.face, hp) }
  local link
  if mon and resting ~= mon then
    local files = roster[figureState(mon).pokemon] or roster[mon.getName()]
    if files and files.front then
      link = BASE_URL .. files.front
      parts[#parts + 1] = phantomXml()
    end
  end
  local bench = stand ~= nil and standSlots(stand) == 9 and not st.benched and not sliding[stand.guid]
  if bench then parts[#parts + 1] = benchButtonXml(ped) end
  local ui, xml, assets = pedestalUI[ped.guid] or {}, table.concat(parts), (bench and "bench" or "") .. "|" .. (link or "")
  local fresh = ui.assets ~= assets
  if fresh then
    local list = {}
    if bench then list[#list + 1] = { name = "bench", url = BASE_URL .. PIECE_ICONS.bench } end
    if link then list[#list + 1] = { name = "phantom", url = link } end
    ped.UI.setCustomAssets(list)
    ui.assets, ui.xml = assets, nil
  end
  if ui.xml ~= xml then
    ped.UI.setXml(xml)
    ui.xml = xml
  end
  pedestalUI[ped.guid] = ui
  if fresh then   -- an image that was still downloading shows blank until the UI is set again
    for _, delay in ipairs({ 1, 3 }) do
      Wait.time(function()
        if ped ~= nil and pedestalUI[ped.guid] == ui and ui.xml == xml then ped.UI.setXml(xml) end
      end, delay)
    end
  end
end

-- Who belongs to which pedestal, and every team pedestal's sign, phantom and button. A Pokémon resting on a pedestal
-- is that pedestal's (and no other's); a pedestal whose Pokémon is gone is empty again.
function refreshPedestals()
  local peds, mons, stands = {}, {}, teamStands()
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("Pedestal") then
      if not memoTable(o).spect then peds[#peds + 1] = o end
    elseif o.hasTag("Pokemon") then
      mons[#mons + 1] = o
    end
  end
  local states, rest, dirty = {}, {}, {}
  for i, ped in ipairs(peds) do
    states[i], rest[i] = memoTable(ped), restingOn(ped, mons)
  end
  for i in ipairs(peds) do
    local mon = rest[i]
    if mon and states[i].mon ~= mon.guid then
      for j in ipairs(peds) do
        if j ~= i and states[j].mon == mon.guid then states[j].mon, dirty[j] = nil, true end
      end
      states[i].mon, states[i].benched, dirty[i] = mon.guid, nil, true   -- put back on a sat-out pedestal: it plays again
    end
  end
  for i, ped in ipairs(peds) do
    local st = states[i]
    local mon = pedestalMon(ped, st)
    if st.mon and not mon then st.mon, dirty[i] = nil, true end
    if dirty[i] then ped.memo = JSON.encode(st) end
    local stand
    for _, s in ipairs(stands) do
      if onStandTop(s, ped.getPosition()) then stand = s end
    end
    if stand and rest[i] then restoreCards(rest[i], ped, stand) end
    updatePedestal(ped, st, mon, rest[i], stand)
  end
end

-- A new pedestal (a team stand's with its sign, or a plain one for the spectator stand), locked.
function spawnPedestal(pos, yaw, plain, memo)
  return spawnObjectData({
    data = {
      Name = "Custom_Model", Nickname = "", Tags = { "Pedestal" }, Locked = true, Memo = memo or "",
      Transform = { posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = 1, scaleY = 1, scaleZ = 1 },
      CustomMesh = { MeshURL = BASE_URL .. (plain and PEDESTAL.plain or PEDESTAL.mesh), DiffuseURL = BASE_URL .. PEDESTAL.tex,
        NormalURL = "", ColliderURL = BASE_URL .. PEDESTAL.collider, Convex = true, MaterialIndex = 3, TypeIndex = 0,
        CastShadows = true },
    },
    position = pos, rotation = { 0, yaw, 0 },
  })
end

local function slotSpot(stand, x)
  return stand.positionToWorld(Vector(x, STAND.pedestal.y, STAND.pedestal.z))
end

-- Cards on a stand's slope in the column around x (the stand's frame), within `half` of it.
function columnCards(stand, x, half)
  local out = {}
  for _, o in ipairs(getAllObjects()) do
    if o.type == "Card" and not o.held_by_color and not flying[o.guid] then
      local lp = stand.positionToLocal(o.getPosition())
      if math.abs(lp.x - x) < half and lp.z < STAND.pedestal.z - 1.2 and lp.z > -STAND_DEPTH - 0.5 and lp.y > -0.5
          and lp.y < STAND.pedestal.y + 1 then
        out[#out + 1] = o
      end
    end
  end
  return out
end

-- A stand gets the plain model (reloading it; it comes back through onObjectSpawn), then its own pedestals: the old
-- fixed ones (backgammon discs) give way to 9 for a whole team, or 6 if a team is already on it. Then its card
-- snap points and the pedestals' signs.
function setupStand(stand)
  if not (stand and stand.hasTag("Stand")) then return end
  local mesh = (stand.getCustomObject() or {}).mesh or ""
  if mesh ~= "" and not mesh:find(STAND_MESH, 1, true) then
    stand.setCustomObject({ mesh = BASE_URL .. STAND_MESH, diffuse = BASE_URL .. STAND_TEX })
    stand.reload()
    return
  end
  local st = memoTable(stand)
  local count = #standPedestals(stand)
  if count == 0 then
    local busy = #columnCards(stand, 0, STAND.length / 2 + 1) > 0
    for _, o in ipairs(getAllObjects()) do
      if o ~= stand and onStandTop(stand, o.getPosition()) then
        if (o.name or ""):find("backgammon_piece", 1, true) then
          o.destruct()
        elseif o.hasTag("Pokemon") then   -- lifted a little: the new pedestal is a hair taller
          busy = true
          local p = o.getPosition()
          o.setPosition({ p.x, p.y + 0.2, p.z })
        end
      end
    end
    st.slots = busy and 6 or 9
    stand.memo = JSON.encode(st)
    for _, x in ipairs(SLOTS[st.slots]) do spawnPedestal(slotSpot(stand, x), stand.getRotation().y) end
  elseif st.slots ~= 9 and st.slots ~= 6 then
    st.slots = count >= 9 and 9 or 6
    stand.memo = JSON.encode(st)
  end
  local n = standSlots(stand)
  if #(stand.getSnapPoints() or {}) ~= #SLOTS[n] * #CARD_KINDS then stand.setSnapPoints(standSnapPoints(n)) end   -- card slots
  refreshPedestals()
end

----------------------------------------------------------------------------------------------------
-- The spectator stand (tag "SpectatorStand", props/spectators-v3) at the table's right end, clear of every board
-- (between Yaksha's gift boxes), as tall as the team stands: along its board side the turn track (below), along its
-- middle 6 plain pedestals evenly spaced, each player's 3 on their own half, and beside each (the outer side) its
-- Pokémon's cards, stacked. A team of 9
-- sends 3 there with the bench buttons, each with the cards from its column; a Pokémon put back on its sat-out
-- pedestal plays again (its cards follow). Once 3 have been sent, the stand's other 6 pedestals slide to the usual
-- spacing, taking their Pokémon and cards (an empty pedestal sat out goes with any cards left in its column).
-- Picking a map makes it 9 again just as it was: the 6 slide back to their own slots (each pedestal remembers its
-- slot of the 9, memo "home"), the sat-out pedestals come back where they were, and everyone comes home with their
-- cards, the benched to the slot they left (the Pokémon's memo "home"), so the team's order is as before.
----------------------------------------------------------------------------------------------------
SPECTATORS = { mesh = "props/spectators-v3.obj", tex = "props/spectators-v3.jpg", pos = { 37.0, 0.961, 0 }, yaw = 180,
  top = 2.6,
  z = { 12.5, 7.5, 2.5 },    -- seat i: z = -z[i] on the near half, +z[i] on the far half (each player's end first)
  seatX = 0.1, cardX = 2.65, -- across the stand (from its middle, toward the table's end): the pedestals, the card stacks
  cardYaw = 0 }               -- the stacked cards lie along the stand, reading from the board side
SLIDE_TIME, SLIDE_FRAMES = 1.0, 60
ARC_TIME, ARC_FRAMES, ARC_PEAK = 1.2, 72, 3.0

function spectatorStand()
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("SpectatorStand") then return o end
  end
  return nil
end

-- The spectator stand and its 6 pedestals, if any are missing. An older stand (another model: the earlier ones had
-- no turn track) gives way to the current one, and each half's pedestals go to their seats with the Pokémon on them.
local function spawnSpectatorStand()
  local turns = 10
  local board = currentBoard()
  local a = board and arenas[board.getName()]
  if a and a.turns then turns = a.turns end
  local stand = spawnObjectData({
    data = {
      Name = "Custom_Model", Nickname = "Spectator stand", Tags = { "SpectatorStand" }, Locked = true,
      Memo = JSON.encode({ turns = turns }),
      Transform = { posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = 1, scaleY = 1, scaleZ = 1 },
      CustomMesh = { MeshURL = BASE_URL .. SPECTATORS.mesh, DiffuseURL = BASE_URL .. SPECTATORS.tex, NormalURL = "",
        ColliderURL = BASE_URL .. SPECTATORS.mesh, Convex = true, MaterialIndex = 3, TypeIndex = 0, CastShadows = true },
    },
    position = SPECTATORS.pos, rotation = { 0, SPECTATORS.yaw, 0 },
  })
  if stand then pieceSetup(stand) end   -- (again once it has loaded: onObjectSpawn)
end

function ensureSpectators()
  local stand = spectatorStand()
  local want = Vector(SPECTATORS.pos[1], SPECTATORS.pos[2], SPECTATORS.pos[3])
  if stand and not ((stand.getCustomObject() or {}).mesh or ""):find(SPECTATORS.mesh, 1, true) then
    stand.destruct()
    stand = nil
  end
  if not stand then
    spawnSpectatorStand()
  else
    local at = stand.getPosition()
    if math.abs(at.x - want.x) + math.abs(at.z - want.z) > 0.01 then stand.setPosition(want) end
  end
  for _, near_ in ipairs({ true, false }) do
    local have = {}
    for _, o in ipairs(getAllObjects()) do
      if o.hasTag("Pedestal") and memoTable(o).spect and (o.getPosition().z < 0) == near_ then have[#have + 1] = o end
    end
    table.sort(have, function(a, b) return math.abs(a.getPosition().z) > math.abs(b.getPosition().z) end)
    for i, z in ipairs(SPECTATORS.z) do
      local spot = Vector(want.x + SPECTATORS.seatX, want.y + SPECTATORS.top, want.z + (near_ and -z or z))
      local ped = have[i]
      if not ped then
        spawnPedestal(spot, near_ and 0 or 180, true, JSON.encode({ spect = true }))
      else
        local p = ped.getPosition()
        local d = spot - p
        if math.abs(d.x) + math.abs(d.y) + math.abs(d.z) > 0.01 then
          local mon = restingOn(ped)
          ped.setPosition(spot)
          if mon then
            local q = mon.getPosition()
            mon.setPosition({ q.x + d.x, q.y + d.y, q.z + d.z })
          end
        end
      end
    end
  end
end

-- Where a spectator seat's cards stack: beside its pedestal, on the stand's outer side (i = 0 at the bottom).
function seatCardSpot(seat, i)
  local p = seat.getPosition()
  return Vector(p.x + SPECTATORS.cardX - SPECTATORS.seatX, p.y + 0.02 + 0.03 * i, p.z)
end

-- The spectator pedestals on a team stand's half, its player's end first.
function spectatorSeats(stand)
  local near_ = stand.getPosition().z < 0
  local out = {}
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("Pedestal") and memoTable(o).spect and (o.getPosition().z < 0) == near_ then out[#out + 1] = o end
  end
  table.sort(out, function(a, b) return math.abs(a.getPosition().z) > math.abs(b.getPosition().z) end)
  return out
end

-- Move objects together to where they're going over SLIDE_TIME (locked meanwhile), then done().
-- moves: { { obj, from = Vector, to = Vector } }
local function slideAll(moves, done)
  for _, m in ipairs(moves) do
    m.locked = m.obj.getLock()
    m.obj.setLock(true)
  end
  local clock = Time and Time.time and function() return Time.time end
  local k, t0 = 0, clock and clock()
  local function step()
    k = k + 1
    local t = math.min(1, clock and (clock() - t0) / SLIDE_TIME or k / SLIDE_FRAMES)
    local e = t * t * (3 - 2 * t)
    for _, m in ipairs(moves) do
      if m.obj ~= nil then m.obj.setPosition(m.from + (m.to - m.from) * e) end
    end
    if t < 1 then
      Wait.frames(step, 1)
    else
      for _, m in ipairs(moves) do
        if m.obj ~= nil then m.obj.setLock(m.locked) end
      end
      if done then done() end
    end
  end
  step()
end

-- Fly a Pokémon (or a card) along an arc to dest (locked meanwhile, turned to rot if given), then done().
local function arcTo(obj, dest, rot, done)
  local from = obj.getPosition()
  local dx, dy, dz = dest.x - from.x, dest.y - from.y, dest.z - from.z
  local peak = ARC_PEAK + 0.1 * math.sqrt(dx * dx + dz * dz)
  local wasLocked = obj.getLock()
  flying[obj.guid] = true
  obj.setLock(true)
  if rot then obj.setRotation(rot) end
  local clock = Time and Time.time and function() return Time.time end
  local k, t0 = 0, clock and clock()
  local function step()
    if obj == nil then return end
    k = k + 1
    local t = math.min(1, clock and (clock() - t0) / ARC_TIME or k / ARC_FRAMES)
    obj.setPosition({ from.x + dx * t, from.y + dy * t + 4 * peak * t * (1 - t), from.z + dz * t })
    if t < 1 then
      Wait.frames(step, 1)
    else
      obj.setLock(wasLocked)
      flying[obj.guid] = nil
      if done then done() end
    end
  end
  step()
end

-- Each pedestal of a stand with what rides along when it slides: the Pokémon resting on it, the cards in its column.
local function slideMoves(stand, peds, xs, half)
  local moves = {}
  for i, p in ipairs(peds) do
    local x = xs[i]
    if x then
      local d = stand.positionToWorld(Vector(x, 0, 0)) - stand.positionToWorld(Vector(p.x, 0, 0))
      local riders = columnCards(stand, p.x, half)
      riders[#riders + 1] = p.obj
      riders[#riders + 1] = restingOn(p.obj)
      for _, o in ipairs(riders) do
        local from = o.getPosition()
        moves[#moves + 1] = { obj = o, from = from, to = from + d }
      end
    end
  end
  return moves
end

-- Which slot (1-9) of a stand's 9 a pedestal stands in (the nearest).
function slotIndex(stand, ped)
  local x = stand.positionToLocal(ped.getPosition()).x
  local best, bd = 1, nil
  for i, sx in ipairs(SLOTS[9]) do
    if not bd or math.abs(sx - x) < bd then best, bd = i, math.abs(sx - x) end
  end
  return best
end

function benchedCount(stand)
  local n = 0
  for _, p in ipairs(standPedestals(stand)) do
    if memoTable(p.obj).benched then n = n + 1 end
  end
  return n
end

-- Once 3 of a team of 9 are sat out: their pedestals and cards go, the other 6 slide to the usual spacing.
function compactStand(stand)
  if sliding[stand.guid] or standSlots(stand) ~= 9 then return false end
  local peds, keep, out = standPedestals(stand), {}, {}
  for _, p in ipairs(peds) do
    if memoTable(p.obj).benched then out[#out + 1] = p else keep[#keep + 1] = p end
  end
  if #out < BENCH_SIZE or #keep ~= #SLOTS[6] then return false end
  local half = (SLOTS[9][2] - SLOTS[9][1]) / 2
  for _, p in ipairs(keep) do   -- each remembers its slot of the 9, to go back to it
    local ps = memoTable(p.obj)
    ps.home = slotIndex(stand, p.obj)
    p.obj.memo = JSON.encode(ps)
  end
  for _, p in ipairs(out) do
    for _, c in ipairs(columnCards(stand, p.x, half)) do c.destruct() end
    p.obj.destruct()
  end
  local st = memoTable(stand)
  st.slots = 6
  stand.memo = JSON.encode(st)
  sliding[stand.guid] = true
  refreshPedestals()   -- the bench buttons go
  slideAll(slideMoves(stand, keep, SLOTS[6], half), function()
    stand.setSnapPoints(standSnapPoints(6))
    sliding[stand.guid] = nil
    refreshPedestals()
  end)
  return true
end

-- Send a pedestal's Pokémon to its player's half of the spectator stand (an empty pedestal is just sat out).
function benchFrom(ped)
  local stand = ped and pedestalStand(ped)
  if not stand or standSlots(stand) ~= 9 or sliding[stand.guid] then return false end
  local st = memoTable(ped)
  if st.benched then return false end
  local mon = pedestalMon(ped, st) or restingOn(ped)
  local seat
  if mon then
    for _, s in ipairs(spectatorSeats(stand)) do
      if not seat and not seatTaken[s.guid] and not restingOn(s) then seat = s end
    end
    if not seat then return false end
  end
  st.benched, st.mon = true, nil
  ped.memo = JSON.encode(st)
  local function after()
    if benchedCount(stand) >= BENCH_SIZE then compactStand(stand) else refreshPedestals() end
  end
  if mon then
    seatTaken[seat.guid] = true
    local x = stand.positionToLocal(ped.getPosition()).x
    local cards = columnCards(stand, x, (SLOTS[9][2] - SLOTS[9][1]) / 2)
    table.sort(cards, function(a, b) return stand.positionToLocal(a.getPosition()).y < stand.positionToLocal(b.getPosition()).y end)
    local fst, guids = figureState(mon), {}
    for i, c in ipairs(cards) do   -- the bottom row's card at the bottom of the stack, the item on top
      guids[i] = c.guid
      arcTo(c, seatCardSpot(seat, i - 1), { 0, SPECTATORS.cardYaw, 0 })
    end
    fst.cards = #guids > 0 and guids or nil
    fst.home = slotIndex(stand, ped)
    mon.memo = JSON.encode(fst)
    arcTo(mon, seat.getPosition() + Vector(0, PEDESTAL_TOP + 0.02, 0), { 0, stand.getRotation().y + FRONT_YAW, 0 }, function()
      seatTaken[seat.guid] = nil
      after()
    end)
    refreshPedestals()
  else
    after()
  end
  return true
end

-- A pedestal's bench button: its id is "bench_<pedestal guid>".
function benchClicked(_, _, id)
  local ped = getObjectFromGUID(tostring(id or ""):sub(7))
  if ped then benchFrom(ped) end
end

-- A stand back to 9 pedestals (sliding its 6 along and adding 3), then done(); with 9 already, nobody is sat out.
function expandStand(stand, done)
  if sliding[stand.guid] then return false end
  local peds = standPedestals(stand)
  if standSlots(stand) == 9 then
    for _, p in ipairs(peds) do
      local ps = memoTable(p.obj)
      if ps.benched then
        ps.benched = nil
        p.obj.memo = JSON.encode(ps)
      end
    end
    if done then done() end
    return true
  end
  local st = memoTable(stand)
  st.slots = 9
  stand.memo = JSON.encode(st)
  local homes, used, xs = {}, {}, {}
  for i, p in ipairs(peds) do
    local h = memoTable(p.obj).home
    if h and SLOTS[9][h] and not used[h] then homes[i], used[h] = h, true end
  end
  local nextSlot = 1
  for i in ipairs(peds) do   -- (a pedestal that doesn't know its slot: the first free one)
    if not homes[i] then
      while used[nextSlot] do nextSlot = nextSlot + 1 end
      homes[i], used[nextSlot] = nextSlot, true
    end
    xs[i] = SLOTS[9][homes[i]]
  end
  sliding[stand.guid] = true
  slideAll(slideMoves(stand, peds, xs, (SLOTS[6][2] - SLOTS[6][1]) / 2), function()
    for i, x in ipairs(SLOTS[9]) do
      if not used[i] then spawnPedestal(slotSpot(stand, x), stand.getRotation().y) end
    end
    for _, p in ipairs(peds) do
      local ps = memoTable(p.obj)
      if ps.home then
        ps.home = nil
        p.obj.memo = JSON.encode(ps)
      end
    end
    stand.setSnapPoints(standSnapPoints(9))
    sliding[stand.guid] = nil
    refreshPedestals()
    if done then done() end
  end)
  return true
end

-- Everyone back to a stand: each Pokémon to its own pedestal, then the ones on its player's half of the spectator
-- stand to the slot they left (or, if that's taken, the first free one).
function returnTeam(stand)
  local free, rot = {}, { 0, stand.getRotation().y + FRONT_YAW, 0 }
  for _, p in ipairs(standPedestals(stand)) do
    local st = memoTable(p.obj)
    local mon, resting = pedestalMon(p.obj, st), restingOn(p.obj)
    if mon and resting ~= mon and not flying[mon.guid] then
      arcTo(mon, p.obj.getPosition() + Vector(0, PEDESTAL_TOP + 0.02, 0), rot, refreshPedestals)
    elseif not mon and not resting then
      free[#free + 1] = p.obj
    end
  end
  local taken = {}
  for _, seat in ipairs(spectatorSeats(stand)) do
    local mon = restingOn(seat)
    if mon then
      local home, to = figureState(mon).home, nil
      for _, f in ipairs(free) do
        if not to and not taken[f.guid] and home and slotIndex(stand, f) == home then to = f end
      end
      for _, f in ipairs(free) do
        if not to and not taken[f.guid] then to = f end
      end
      if to then
        taken[to.guid] = true
        arcTo(mon, to.getPosition() + Vector(0, PEDESTAL_TOP + 0.02, 0), rot, refreshPedestals)
      end
    end
  end
end

-- A Pokémon that went to the spectator stand with its cards, now back on a team pedestal: its cards fly back to
-- that pedestal's column, each to its own row.
function restoreCards(mon, ped, stand)
  local st = figureState(mon)
  if type(st.cards) ~= "table" and not st.home then return end
  local guids = type(st.cards) == "table" and st.cards or {}
  st.cards, st.home = nil, nil
  mon.memo = JSON.encode(st)
  local x, rot = stand.positionToLocal(ped.getPosition()).x, cardRotation(stand)
  local dy, dz = slopeLift(0.15)
  for _, g in ipairs(guids) do
    local c = getObjectFromGUID(g)
    if c and c.type == "Card" then
      local kind
      for _, k in ipairs(CARD_KINDS) do
        if c.hasTag(CATALOGS[k].tag) then kind = k end
      end
      if kind then
        arcTo(c, stand.positionToWorld(Vector(x, STAND.cards[kind].y + dy, STAND.cards[kind].z + dz)), rot)
      end
    end
  end
end

-- A new map: both stands back to 9 with their whole teams.
function resetStands()
  for _, stand in ipairs(teamStands()) do
    expandStand(stand, function() returnTeam(stand) end)
  end
end

----------------------------------------------------------------------------------------------------
-- The turn track along the spectator stand's board side: slots 1-15 (1 at the far end: the left, seen from the
-- board), the arena's last turn in gold (object UI over its slot, its number on it; the stand's memo keeps the
-- arena's turn count),
-- and a token (tag "TurnToken", a Poké Ball, its white half toward the board) that snaps to the slots. A new map
-- tints its last turn and puts the token back on 1.
----------------------------------------------------------------------------------------------------
TURN_TRACK = { x = 2.7, slot = 2.0, turns = 15,   -- the slots in the stand's own frame: across at x, 1 at -z
  token = "props/turntoken-v2.obj", tokenTex = "props/turntoken-v2.jpg",
  gold = "#E8C462", goldSize = 156, ink = "#3A2212" }   -- the last turn's slot: gold, its size (UI units), the number's colour

-- A slot's middle along the stand (its own frame).
local function slotZ(i)
  return (2 * i - TURN_TRACK.turns - 1) * TURN_TRACK.slot / 2
end

function turnSnaps()
  local snaps = {}
  for i = 1, TURN_TRACK.turns do
    snaps[i] = { position = { TURN_TRACK.x, SPECTATORS.top, slotZ(i) }, rotation = { 0, 0, 0 }, rotation_snap = false }
  end
  return snaps
end

-- The arena's last turn (the stand's memo's turn count) in gold: a gold square over its slot with its number, turned
-- to read from the board side like the slots' own numbers.
function showLastTurn(stand)
  local n = math.max(1, math.min(TURN_TRACK.turns, math.floor(memoTable(stand).turns or 10)))
  stand.UI.setXml(string.format([[<Panel position="%d %d %d" width="%d" height="%d" color="%s" raycastTarget="false">
  <Text rotation="0 0 90" fontSize="100" fontStyle="Bold" color="%s">%d</Text>
</Panel>]], math.floor(TURN_TRACK.x * 100 + 0.5), math.floor(slotZ(n) * 100 + 0.5),
    math.floor(-(SPECTATORS.top + 0.01) * 100 + 0.5), TURN_TRACK.goldSize, TURN_TRACK.goldSize, TURN_TRACK.gold, TURN_TRACK.ink, n))
end

-- Where the token sits on turn 1 (in the world: the stand is turned round).
local function firstTurnSpot()
  local c, k = SPECTATORS.pos, SPECTATORS.yaw == 180 and -1 or 1
  return Vector(c[1] + k * TURN_TRACK.x, c[2] + SPECTATORS.top + 0.1, c[3] + k * slotZ(1))
end

local function spawnToken()
  spawnObjectData({
    data = {
      Name = "Custom_Model", Nickname = "Turn", Tags = { "TurnToken" },
      Transform = { posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = 1, scaleY = 1, scaleZ = 1 },
      CustomMesh = { MeshURL = BASE_URL .. TURN_TRACK.token, DiffuseURL = BASE_URL .. TURN_TRACK.tokenTex, NormalURL = "",
        ColliderURL = BASE_URL .. TURN_TRACK.token, Convex = true, MaterialIndex = 3, TypeIndex = 0, CastShadows = true },
    },
    position = firstTurnSpot(), rotation = { 0, 0, 0 },
  })
end

-- A new map: its last turn in gold, the token back on 1 (a new one if it's gone). (The separate track of an older
-- layout goes.)
function setTurnTrack(turns)
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("TurnTrack") then o.destruct() end
  end
  local stand = spectatorStand()
  if stand then
    local st = memoTable(stand)
    st.turns = turns or 10
    stand.memo = JSON.encode(st)
    showLastTurn(stand)
  end
  local token
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("TurnToken") then
      if token then o.destruct() else token = o end
    end
  end
  if token then
    token.setPosition(firstTurnSpot())
    token.setRotation({ 0, 0, 0 })
  else
    spawnToken()
  end
end

-- Is the token on the track? (on the stand's slots row)
local function onTrack(token)
  local p, first = token.getPosition(), firstTurnSpot()
  return math.abs(p.x - first.x) < 1.5 and math.abs(p.z - SPECTATORS.pos[3]) < TURN_TRACK.turns * TURN_TRACK.slot / 2 + 0.5
    and p.y > first.y - 0.6
end

-- After a load: the stand shows the last turn of the arena on the table, and there's a token (left where it is, if
-- it's on the track: one from an older layout goes back to 1).
function ensureTurnTrack(turns)
  local stand = spectatorStand()
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("TurnTrack") then o.destruct() end
  end
  if stand and memoTable(stand).turns ~= (turns or 10) then
    local st = memoTable(stand)
    st.turns = turns or 10
    stand.memo = JSON.encode(st)
    showLastTurn(stand)
  end
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag("TurnToken") then
      if not onTrack(o) and not o.held_by_color then
        o.setPosition(firstTurnSpot())
        o.setRotation({ 0, 0, 0 })
      end
      return
    end
  end
  spawnToken()
end

-- Pokémon use the plain standee (no sign of their own) and no labels of their own.
function plainStandee(obj)
  local custom = obj.name == "Custom_Model" and (obj.getCustomObject() or {}) or {}
  local mesh = custom.mesh or ""
  if mesh:find("models/standee-", 1, true) and not mesh:find(STANDEE_MESH, 1, true) then
    obj.setCustomObject({ mesh = BASE_URL .. STANDEE_MESH, collider = BASE_URL .. STANDEE_MESH })
    obj.reload()
  elseif (obj.UI.getXml() or "") ~= "" then
    obj.UI.setXml("")
  end
end

-- Pokémon put down, picked up or removed: the signs, zones and flags follow (after it has settled or left).
function onObjectDrop(color, obj)
  if obj.hasTag("Pokemon") then
    claimPokemon(obj, color)
    Wait.time(refreshPedestals, 0.5)
    Wait.time(refreshZones, 0.5)
    Wait.time(function() flagTaken(obj) end, 0.5)
  end
end

function onObjectDestroy(obj)
  if obj.hasTag("Pokemon") then
    Wait.frames(refreshPedestals, 2)
    Wait.frames(refreshZones, 2)
  end
end

-- What a typed entry makes the HP: "120" sets it, "-35" / "+20" change it; nil if it isn't a number.
function parseHp(text, current, max)
  local s = (text or ""):gsub("%s", ""):gsub("/.*$", "")
  local sign, n = s:match("^([%+%-]?)(%d+)$")
  if not n then return nil end
  local v = tonumber(n)
  if sign == "-" then v = current - v elseif sign == "+" then v = current + v end
  return math.max(0, math.min(max, v))
end

-- A sign's number was edited ("hpIn_<pedestal guid>_<side>"): change the HP of that pedestal's Pokémon.
function hpEdited(player, value, id)
  local guid = id:match("^hpIn_(%w+)_%a$")
  local ped = guid and getObjectFromGUID(guid)
  if not ped then return end
  local mon = pedestalMon(ped)
  if mon then
    local st = hpState(mon)
    if st.maxHp then
      local old = st.hp
      local new = parseHp(value, old, st.maxHp)
      if new and new ~= old then
        st.hp = new
        mon.memo = JSON.encode(st)
      end
    end
  end
  pedestalUI[ped.guid] = nil   -- shows the result, or puts back the number if the entry wasn't one
  refreshPedestals()
  refreshZones()               -- a fainted Pokémon no longer holds a zone
end
