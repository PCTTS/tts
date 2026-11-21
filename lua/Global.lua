--[[ PCTTS_MOD — Global script for the Pokemon Conquest tabletop mod.
Source: https://github.com/PCTTS/tts (lua/Global.lua). Edit there, not in TTS.

Toolbar (right edge, a third of the way down the screen), one panel open at a time, each player gets their own:
  * Pokéball: search the roster, click a result and that figure goes on your next free pedestal.
  * Potion:   scroll through (or search) the item cards, click one and it goes in the next free item slot.
  * Swords:   scroll through (or search) the warrior skill cards, click one and it goes in the next free skill slot.
  * Sparkle:  the same for Pokémon ability cards (the bottom row of the stand).
Team stands (tagged "Stand") sit on the two long sides: six pedestals on top, an item card and a warrior skill
card on the slope under each. Which stand is yours depends on your seat colour (SEAT_SIDE).
  * Swirl:    pick a status, then pick up a Pokémon to give it that status (it's tinted in the status's
              type colour). One main status at a time; Confused and Flinched can stack on top.
              "Clear status" returns a Pokémon to normal.
  * Map:      pick which arena goes on the table (3D boards from arenas/index.json, with snap points and pieces).
Flags on the board: right-click > Capture tints a flag to your seat colour; "Make neutral" resets it.
HP: the sign above each pedestal shows "current/max" HP of the Pokémon on it; click the number and type 120 (set), -35 or +20.
Chat:  !spawn garchomp   !item sitrus   !skill belief   !ability levitate   spawn the best match (or list close alternatives).

The roster (figures/index.json) and the cards (cards/index.json) are downloaded from the PCTTS site when the
game loads, so new Pokémon and changed cards appear without editing the mod. The last copies are kept in the
save, so everything still works if the site can't be reached.
--]]

BASE_URL = "https://pctts.github.io/tts/"
ICONS = {
  pokeball = "ui/icons/pokeball-v3.png", map = "ui/icons/map-v3.png", status = "ui/icons/status-v3.png",
  item = "ui/icons/item-v3.png", skill = "ui/icons/skill-v3.png", ability = "ui/icons/ability-v3.png",
}
PIECE_ICONS = { die = "ui/icons/die-v3.png", updown = "ui/icons/updown-v3.png" }   -- buttons on arena pieces
-- Toolbar geometry in UI units. Icons are drawn at 64 px, close to their on-screen size: TTS doesn't smooth
-- UI images it shrinks, so a much larger image looks jagged.
BAR_ICON, BAR_MARGIN, BAR_GAP = 32, 3, 6
TOOLS = {
  { kind = "dex", icon = "pokeball", tip = "Spawn a Pokémon" },
  { kind = "items", icon = "item", tip = "Item cards" },
  { kind = "skills", icon = "skill", tip = "Warrior skill cards" },
  { kind = "abilities", icon = "ability", tip = "Pokémon ability cards" },
  { kind = "status", icon = "status", tip = "Give a status" },
  { kind = "maps", icon = "map", tip = "Choose the map" },
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
  dex = { title = "Spawn a Pokémon", noun = "Pokémon", hint = "Click a result to put it on your next free pedestal." },
  items = { title = "Item cards", noun = "item", hint = "Click a card to place it, or type to search.",
    deckBase = 1000, tag = "Item" },
  skills = { title = "Warrior skill cards", noun = "warrior skill", hint = "Click a card to place it, or type to search.",
    deckBase = 3000, tag = "WarriorSkill" },
  abilities = { title = "Pokémon ability cards", noun = "ability", hint = "Click a card to place it, or type to search.",
    deckBase = 5000, tag = "Ability" },
}
ROSTER_URL = BASE_URL .. "figures/index.json"
CARDS_URL = BASE_URL .. "cards/index.json"
STATS_URL = BASE_URL .. "data/pokemon.json"   -- every Pokémon's stats from the sheet (tools/build_stats.py)
ARENAS_URL = BASE_URL .. "arenas/index.json"   -- the map picker's arenas (tools/build_arena_index.py)

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
STATUS_HINT = "Pick a status, then pick up a Pokémon."

STANDEE_MESH = "models/standee-v1.obj"  -- a Pokémon: art on a round base with a facing arrow (build_standee.py)
FIGURE_SCALE = 1.5   -- ImageScalar for the old flat figurines (only used if the roster has no standees)
FRONT_YAW = 0        -- added to the seat's rotation so the figure's front faces its player
RESULTS = 8          -- search results shown at once
MAX_MAPS = 16        -- rows in the map panel
ROW_TEXT = "#111111" -- result rows: dark text on light grey (TTS can reset text colour when a row's text changes)
ROW_STEP = 32        -- height of one result row plus spacing
SEARCH_BASE = 108    -- search panel height with no results (title, search box, hint)
MAPS_BASE = 70       -- map panel height with no rows (title, hint)
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
  cardScale = { 1.0, 1.5 },  -- (across, along) the card: shorter than TTS's standard card so three rows fit
  snapLift = 0.55,  -- card snap points float this far off the slope, so a card held flat clears the rising slope
}
CARD_YAW = 270  -- cards lie landscape: turned a quarter so the name reads left-to-right for the stand's player
PEDESTAL_TOP = 0.25  -- a pedestal's height above the stand top
COLORS = { "White", "Brown", "Red", "Orange", "Yellow", "Green", "Teal", "Blue", "Purple", "Pink", "Grey", "Black" }

catalog = {}         -- kind -> { index = name -> data, list = sorted search entries, keys = name -> deck id }
for _, k in ipairs(SEARCH_KINDS) do catalog[k] = { index = {}, list = {}, keys = {} } end
roster = catalog.dex.index
cardBacks = {}       -- kind -> back image path
stats = {}           -- Pokémon name -> { hp, atk, def, spd, rng, types } (data/pokemon.json)
arenas = {}          -- arena name -> { mesh, texture, table, snaps, pieces } (arenas/index.json)
openPanel, searchHits, mapRows, spawnCount = {}, {}, {}, {}
armed = {}           -- [colour] = status key waiting for that player to pick up a Pokémon
queries = {}         -- [colour .. kind] = what that player last typed in that search box
listViewers = { items = {}, skills = {}, abilities = {} }  -- [kind][colour] = true while that player sees the full list
listNames, builtLists = {}, {}             -- names in each full list as built, and a signature of them

----------------------------------------------------------------------------------------------------
-- Save / load
----------------------------------------------------------------------------------------------------
-- The downloads (roster, cards, stats) are kept as the text that came in and saved as that text: TTS saves the
-- game every few seconds for rewind, and turning these tables back into JSON took over a second each time
-- (the stutter). Each is decoded once per load: the fresh download, or the saved copy if the site can't be reached.
DATA = {
  { key = "roster", url = ROSTER_URL, use = function(t) setCatalog("dex", t, "downloaded") end },
  { key = "cards", url = CARDS_URL, use = function(t) setCards(t, "downloaded") end },
  { key = "stats", url = STATS_URL, use = function(t) stats = t; refreshPedestals() end },
  { key = "arenas", url = ARENAS_URL, use = function(t) arenas = t end },
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

function onLoad(saved)
  local ok, texts = pcall(readSavedState, saved)
  if not ok then   -- a bad saved copy must never stop the load: the downloads still come in
    log("Couldn't read the saved copies (" .. tostring(texts) .. "); downloading fresh ones.")
    texts = {}
  end
  for key, text in pairs(texts) do
    if key ~= "legacy" then rememberData(key, text) end
  end
  for _, d in ipairs(DATA) do
    WebRequest.get(d.url, function(req)
      local text = (not req.is_error and req.text and req.text ~= "") and req.text or nil
      local from = "downloaded"
      if not text then
        log("Couldn't download the " .. d.key .. " (" .. tostring(req.error) .. "); using the saved copy.")
        text, from = rawData[d.key], "saved copy"
      end
      local ok, data = false, nil
      if text then ok, data = pcall(JSON.decode, text) end
      if ok and type(data) == "table" and next(data) then
        if from == "downloaded" then rememberData(d.key, text) end
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
      elseif obj.hasTag("Portal") or obj.hasTag("Bridge") then
        pieceSetup(obj)
      end
    end
  end, 2)
end

function onSave()
  return savedState
end

function log(msg)
  print("[PCTTS] " .. msg)
end

----------------------------------------------------------------------------------------------------
-- Catalogues and search
----------------------------------------------------------------------------------------------------
local function norm(s)
  s = s:lower():gsub("é", "e"):gsub("♀", "f"):gsub("♂", "m")
  return (s:gsub("[^%w]", ""))
end

function setCatalog(kind, index, from)
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
  log(CATALOGS[kind].title .. ": " .. #list .. " (" .. from .. ")")
  -- the scrolling lists are part of the UI: rebuild it if this catalogue's names changed since it was built
  if LIST_KINDS[kind] and builtLists[kind] and builtLists[kind] ~= listSignature(kind) then buildUI() end
end

function listSignature(kind)
  local names = {}
  for i, e in ipairs(catalog[kind].list) do names[i] = e.name end
  return table.concat(names, "\n")
end

function setCards(data, from)
  cardBacks = data.backs or {}
  if data.items then setCatalog("items", data.items, from) end
  if data.skills then setCatalog("skills", data.skills, from) end
  if data.abilities then setCatalog("abilities", data.abilities, from) end
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

-- The stand's card snap points (one per card slot), a little above the slope, rotation snapping to the slope.
function standSnapPoints()
  local dy, dz = slopeLift(STAND.snapLift)
  local tilt = STAND.tilt * (CARD_YAW == 270 and 1 or -1)
  local snaps = {}
  for _, x in ipairs(STAND.x) do
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

-- First free spot on the player's stand, columns from the player's left. kind: "dex" (pedestal) or a card kind.
function freeSpot(color, kind)
  local stand = standFor(color)
  if not stand then return nil end
  for _, x in ipairs(STAND.x) do
    local spot
    if kind == "dex" then
      spot = stand.positionToWorld(Vector(x, STAND.pedestal.y + PEDESTAL_TOP, STAND.pedestal.z))
    else
      spot = stand.positionToWorld(Vector(x, STAND.cards[kind].y, STAND.cards[kind].z))
    end
    if not taken(spot, kind ~= "dex") then return spot, stand end
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
    Memo = JSON.encode({ pokemon = name, hp = maxHp(name), maxHp = maxHp(name) }),
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
    callback_function = function(board) board.setSnapPoints(snaps) end,
  })
  for _, p in ipairs(a.pieces or {}) do spawnArenaPiece(p, spot, base) end
  if a.table and a.table ~= "" and Tables.getCustomURL() ~= base .. a.table then
    Tables.setCustomURL(base .. a.table)
  end
  return true
end

-- One arena piece from the index (pos: in the board's frame; origin: where the board sits), locked.
-- Flags start neutral, portals in their starting pair's colour, bridges dropped (closed); pieceSetup gives
-- them their buttons and menus.
function spawnArenaPiece(p, origin, base)
  local data = {
    Name = "Custom_Model", Nickname = p.name, Description = p.desc or "", Tags = { p.kind, "ArenaPiece" },
    Locked = true, ColorDiffuse = { r = 1, g = 1, b = 1 }, Memo = "",
    Transform = { posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = 1, scaleY = 1, scaleZ = 1 },
    CustomMesh = { MeshURL = base .. p.mesh, DiffuseURL = base .. p.diffuse, NormalURL = "",
      ColliderURL = base .. p.collider, Convex = p.convex, MaterialIndex = p.material, TypeIndex = 0,
      CastShadows = true },
  }
  local pos = origin + Vector(p.pos[1], p.pos[2], p.pos[3])
  if p.kind == "Flag" then
    data.ColorDiffuse, data.Description = FLAG_NEUTRAL, flagDescription(nil)
  elseif p.kind == "Portal" then
    data.ColorDiffuse, data.Memo = portalTint(p.pair or 1), JSON.encode({ pair = p.pair or 1 })
  elseif p.kind == "Bridge" then
    data.Memo = JSON.encode({ up = false, y = pos.y, tiles = p.tiles or 1, tile = p.tile or BOARD_TILE })
    pos = Vector(pos.x, pos.y - BRIDGE_DROP, pos.z)
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
    local place = string.format('rectAlignment="UpperCenter" offsetXY="0 %d" width="%d" height="%d" tooltip="%s" onClick="toolClick"',
      y, BAR_ICON, BAR_ICON, t.tip)
    items[#items + 1] = string.format('<Button id="tool_%s" class="bar" %s/>', t.kind, place)
    items[#items + 1] = string.format('<Image id="toolIcon_%s" class="barIcon" image="%s" %s/>', t.kind, t.icon, place)
  end
  return string.format('<Panel id="toolbar" rectAlignment="MiddleRight" width="%d" height="%d" color="#000000E6" '
    .. 'outline="#303030" outlineSize="1 1">\n  %s\n</Panel>\n', w, h, table.concat(items, "\n  "))
end

PANEL_W, PANEL_PAD = 290, 8
LIST_TOP = 100  -- a search panel's first result row, below its top: padding, title, search box, hint and gaps
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
    <Button class="close" preferredWidth="28" onClick="closePanel" text="X"/>
  </HorizontalLayout>
  %s
  <Panel flexibleHeight="1"/>
</VerticalLayout>
]], kind, c, c, PANEL_W, height, PANEL_PAD, PANEL_PAD, PANEL_PAD, PANEL_PAD, title, body)
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
  <Button class="bar" colors="#00000000|#FFFFFF26|#FFFFFF4D|#00000000" tooltipPosition="Left"/>
  <Image class="barIcon" raycastTarget="false" preserveAspect="true" tooltipPosition="Left"/>
  <Button class="row" fontSize="15" textAlignment="MiddleLeft" padding="10 0 0 0" textColor="#111111"
          colors="#E4E4E4|#B3D1FF|#8DB8F7|#E4E4E4" preferredHeight="28" flexibleHeight="0"/>
  <Button class="close" fontSize="14" textColor="#FFFFFF" colors="#2a2a2a|#c0392b|#962d22|#2a2a2a"/>
  <Text class="title" fontSize="16" fontStyle="Bold" color="#FFFFFF" alignment="MiddleLeft"/>
  <Text class="hint" fontSize="12" color="#AAAAAA" alignment="MiddleLeft" preferredHeight="18" flexibleHeight="0"/>
  <InputField class="search" fontSize="16" preferredHeight="34" flexibleHeight="0" characterLimit="40"/>
</Defaults>
]], string.format('<Panel id="hud" rectAlignment="UpperRight" width="100%%" height="%s" color="#00000000" raycastTarget="false">\n',
    HUD_HEIGHT), toolbarXml(), dockXml() }
  for _, c in ipairs(COLORS) do
    for _, kind in ipairs(SEARCH_KINDS) do
      local cat = CATALOGS[kind]
      local rows = {
        string.format('<InputField id="%sIn_%s" class="search" placeholder="Type part of a name..." onValueChanged="searchChanged"/>', kind, c),
        string.format('<Text id="%sMsg_%s" class="hint">%s</Text>', kind, c, cat.hint),
      }
      for i = 1, RESULTS do
        rows[#rows + 1] = string.format('<Button id="%sRes_%s_%d" class="row" active="false" onClick="searchPick" text=" "/>', kind, c, i)
      end
      xml[#xml + 1] = panelXml(kind, c, cat.title, panelHeight(kind, 0), table.concat(rows, "\n  "))
    end

    local rows = { string.format('<Text id="mapMsg_%s" class="hint">Click a map to put it on the table.</Text>', c) }
    for i = 1, MAX_MAPS do
      rows[#rows + 1] = string.format('<Button id="mapRes_%s_%d" class="row" active="false" onClick="mapPick" text=" "/>', c, i)
    end
    xml[#xml + 1] = panelXml("maps", c, "Choose the map", MAPS_BASE, table.concat(rows, "\n  "))

    -- statuses: a square in the status's colour, then the row (the clear row gets an empty square's space)
    rows = { string.format('<Text id="statusMsg_%s" class="hint">%s</Text>', c, STATUS_HINT) }
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
  local names, hits = search(kind, value, RESULTS)
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
  local msg
  if value == "" then
    msg = CATALOGS[kind].hint
  elseif #names == 0 then
    msg = "No " .. CATALOGS[kind].noun .. " matches \"" .. value .. "\"."
  elseif #hits > RESULTS then
    msg = #hits .. " matches, showing the best " .. RESULTS .. "."
  else
    msg = #hits .. (#hits == 1 and " match." or " matches.")
  end
  UI.setValue(kind .. "Msg_" .. c, msg)
end

local function placed(kind, c, name)
  if name and spawnFrom(kind, name, c) then
    UI.setValue(kind .. "Msg_" .. c, "Placed " .. name .. ".")
  end
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
      UI.setAttribute(id, "text", m.current and (m.name .. "   (on the board)") or m.name)
      UI.setAttribute(id, "textColor", ROW_TEXT)
      UI.setAttribute(id, "colors", m.current and "#8DB8F7|#8DB8F7|#6FA3F0|#8DB8F7" or "#E4E4E4|#B3D1FF|#8DB8F7|#E4E4E4")
    end
    UI.setAttribute(id, "active", m and "true" or "false")
  end
  UI.setAttribute("maps_" .. c, "height", MAPS_BASE + math.min(#list, MAX_MAPS) * ROW_STEP)
  UI.setValue("mapMsg_" .. c, #list > 0 and "Click a map to put it on the table." or "The map list hasn't downloaded yet.")
end

function mapPick(player, _, id)
  local c = player.color
  local m = mapRows[c] and mapRows[c][tonumber(id:match("_(%d+)$"))]
  if not m or m.current then return end
  if not loadArena(m.name) then return end
  printToAll((player.steam_name or c) .. " put " .. m.name .. " on the table.", { 0.8, 0.9, 1 })
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
  UI.setValue("statusMsg_" .. c, armed[c] and "Now pick up a Pokémon (click the status again to cancel)." or STATUS_HINT)
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
  local name, now = (st.pokemon ~= "" and st.pokemon) or "That Pokémon", false
  if key == "clear" then
    st.status, st.confused, st.flinched = nil, nil, nil
  elseif def.volatile then
    st[key] = (not st[key]) or nil   -- toggles
    now = st[key]
  else
    st.status = (st.status ~= key) and key or nil  -- replaces the main status, or removes it if it's the same
    now = st.status ~= nil
  end
  obj.memo = JSON.encode(st)
  paintFigure(obj, st)
  local msg = key == "clear" and (name .. " is back to normal.")
    or (name .. (now and " is now " or " is no longer ") .. def.label:lower() .. ".")
  printToAll(msg, { 0.95, 0.88, 0.75 })
end

function onObjectPickUp(color, obj)
  if obj.hasTag("Pokemon") then Wait.time(refreshPedestals, 0.3) end   -- lifted off its pedestal: its sign empties
  local key = armed[color]
  if not key or not isFigure(obj) then return end
  armed[color] = nil
  applyStatus(obj, key)
  refreshStatus(color)
end

----------------------------------------------------------------------------------------------------
-- Arena pieces (tools/place_pieces.py puts them on the board): bells, and flags that show who holds them.
-- A flag's cloth is white, so its tint is the holder's colour; its memo keeps the holder's seat colour.
----------------------------------------------------------------------------------------------------
FLAG_NEUTRAL = { r = 0.6, g = 0.58, b = 0.54 }   -- an unclaimed flag

function flagDescription(color)
  return (color and ("Held by " .. color .. ".") or "Neutral.") .. " Right-click it to capture it for your colour."
end

-- color = the seat colour that now holds the flag (nil = neutral); by = the player who changed it
function setFlagHolder(obj, color, by)
  local was = obj.memo
  if was == "" then was = nil end
  if color then obj.setColorTint(Color.fromString(color)) else obj.setColorTint(FLAG_NEUTRAL) end
  obj.memo = color or ""
  obj.setDescription(flagDescription(color))
  if by and color ~= was then
    local who = Player[by].steam_name or by
    if color then
      printToAll(who .. " captured a flag.", Color.fromString(color))
    else
      printToAll(who .. " made a flag neutral.", { 0.9, 0.9, 0.9 })
    end
  end
end

function flagMenu(obj)
  if not (obj and obj.hasTag("Flag")) then return end
  obj.clearContextMenu()
  obj.addContextMenuItem("Capture", function(color)
    if color == "Grey" then
      Player[color].broadcast("Take a seat to capture flags.", { 1, 0.6, 0.6 })
    else
      setFlagHolder(obj, color, color)
    end
  end)
  obj.addContextMenuItem("Make neutral", function(color) setFlagHolder(obj, nil, color) end)
end

local function playerName(color)
  return (color and Player[color] and Player[color].steam_name) or color or "Someone"
end

local function piecesTagged(tag)
  local list = {}
  for _, o in ipairs(getAllObjects()) do
    if o.hasTag(tag) then list[#list + 1] = o end
  end
  table.sort(list, function(a, b) return a.guid < b.guid end)
  return list
end

local function memoTable(obj)
  local ok, t = pcall(JSON.decode, obj.memo or "")
  return (ok and type(t) == "table") and t or {}
end

-- A clear button lying on a piece (object UI: 100 units = 1 world unit, canvas y = the object's z, -z = up),
-- with an icon that reads the same from either side of the table.
local function pieceButtonXml(id, x, z, y, onClick, tip, icon)
  return string.format([[
<Button id="%s" position="%d %d %d" width="56" height="56" onClick="Global/%s" tooltip="%s" tooltipPosition="Above"
  colors="#00000040|#FFFFFF66|#FFFFFF99|#00000040"/>
<Image image="%s" position="%d %d %d" width="46" height="46" raycastTarget="false" color="#FFFFFFE0" preserveAspect="true"/>
]], id, math.floor(x * 100 + 0.5), math.floor(z * 100 + 0.5), math.floor(-y * 100 + 0.5), onClick, tip,
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

function shufflePortals(color)
  local portals = piecesTagged("Portal")
  if #portals < 2 then return end
  local order = {}
  for i = 1, #portals do order[i] = i end
  for i = #order, 2, -1 do
    local j = math.random(i)
    order[i], order[j] = order[j], order[i]
  end
  for k, i in ipairs(order) do setPortalPair(portals[i], math.floor((k + 1) / 2)) end
  printToAll(playerName(color) .. " shuffled the portals.", { 0.85, 0.7, 1 })
end

function portalClicked(player)
  shufflePortals(player and player.color)
end

----------------------------------------------------------------------------------------------------
-- Rope bridges (Illusio): flat plank decks over the sky between islands, carrying their own snap points. Up =
-- level with the islands (crossable); dropped = hanging below them (closed). They start dropped. The arrows on
-- any bridge raise them all, or drop them all, except that a bridge with a Pokémon on it stays up (the rules:
-- it doesn't close until the next time they all do). Right-click a bridge to raise or drop just that one.
-- Its memo: { up, y = its height when up, tiles, tile }.
----------------------------------------------------------------------------------------------------
BOARD_TILE = 3.24875
BRIDGE_DROP = 1.6
BRIDGE_BUTTON = { z = 1.0, y = 0.02 }   -- beside the middle of the deck, clear of a Pokémon's base

function bridgeState(obj)
  local st = memoTable(obj)
  st.tiles, st.tile = st.tiles or 1, st.tile or BOARD_TILE
  return st
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

function bridgeDescription(up)
  return (up and "Up: Pokémon can cross it." or "Dropped: closed.") .. " The bridges go up or down together every "
    .. "second turn: click the arrows on any bridge. One with a Pokémon on it stays up until the next time. "
    .. "Right-click it to raise or drop just this one."
end

function setBridgeUp(obj, up)
  local st = bridgeState(obj)
  if (st.up and true or false) == up then return false end
  st.up = up
  obj.memo = JSON.encode(st)
  local p = obj.getPosition()
  if st.y then obj.setPositionSmooth(Vector(p.x, up and st.y or st.y - BRIDGE_DROP, p.z), false, false) end
  obj.setDescription(bridgeDescription(up))
  return true
end

-- Raise them all if any is down; otherwise drop them all except the ones with a Pokémon on them.
function toggleBridges(color)
  local bridges, anyDown = piecesTagged("Bridge"), false
  for _, b in ipairs(bridges) do
    if not bridgeState(b).up then anyDown = true end
  end
  if #bridges == 0 then return end
  if anyDown then
    for _, b in ipairs(bridges) do setBridgeUp(b, true) end
    printToAll(playerName(color) .. " raised the bridges.", { 0.9, 0.8, 0.6 })
    return
  end
  local stay = {}
  for _, b in ipairs(bridges) do
    local mon = pokemonOnBridge(b)
    if mon then stay[#stay + 1] = figureState(mon).pokemon else setBridgeUp(b, false) end
  end
  local msg = playerName(color) .. " dropped the bridges."
  if #stay == 1 then
    msg = msg .. " The one under " .. stay[1] .. " stays up."
  elseif #stay > 1 then
    msg = msg .. " The ones under " .. table.concat(stay, ", ") .. " stay up."
  end
  printToAll(msg, { 0.9, 0.8, 0.6 })
end

function bridgeClicked(player)
  toggleBridges(player and player.color)
end

-- Buttons, menus and snap points for an arena piece (after it spawns, and again on load: none of it is reliably
-- kept by a save).
function pieceSetup(obj)
  if not obj then return end
  flagMenu(obj)
  if obj.hasTag("Portal") then
    local pair = memoTable(obj).pair or 1
    setPortalPair(obj, PORTAL_COLORS[pair] and pair or 1)
    obj.UI.setCustomAssets({ { name = "die", url = BASE_URL .. PIECE_ICONS.die } })
    obj.UI.setXml(pieceButtonXml("portalDie", PORTAL_BUTTON.x, PORTAL_BUTTON.z, PORTAL_BUTTON.y, "portalClicked",
      "Shuffle the portals", "die"))
    obj.clearContextMenu()
    obj.addContextMenuItem("Shuffle portals", function(color) shufflePortals(color) end)
  elseif obj.hasTag("Bridge") then
    local st = bridgeState(obj)
    if #(obj.getSnapPoints() or {}) ~= st.tiles then obj.setSnapPoints(bridgeSnaps(st)) end
    obj.setDescription(bridgeDescription(st.up))
    obj.UI.setCustomAssets({ { name = "updown", url = BASE_URL .. PIECE_ICONS.updown } })
    obj.UI.setXml(pieceButtonXml("bridgeArrows", 0, BRIDGE_BUTTON.z, BRIDGE_BUTTON.y, "bridgeClicked",
      "Raise or drop the bridges", "updown"))
    obj.clearContextMenu()
    obj.addContextMenuItem("Raise this bridge", function(color)
      if setBridgeUp(obj, true) then printToAll(playerName(color) .. " raised a bridge.", { 0.9, 0.8, 0.6 }) end
    end)
    obj.addContextMenuItem("Drop this bridge", function(color)
      if setBridgeUp(obj, false) then printToAll(playerName(color) .. " dropped a bridge.", { 0.9, 0.8, 0.6 }) end
    end)
  end
end

function onObjectSpawn(obj)
  pieceSetup(obj)
  if obj.hasTag("Stand") then
    Wait.time(function() setupStand(obj) end, 0.5)
  elseif obj.hasTag("Pokemon") then
    plainStandee(obj)
    Wait.time(refreshPedestals, 1.5)   -- once it has landed
  end
end

----------------------------------------------------------------------------------------------------
-- HP signs: each team stand (props/stand-v3.obj) has a sign board above each pedestal, showing "Y/X" for the
-- Pokémon standing on that pedestal (blank when it's empty). One label on each face of the board: TTS draws an
-- object's UI in a fixed order regardless of which part is nearer, but solid geometry hides UI behind it, so
-- each side of the table reads its own label the right way round.
-- Click the number and type 120 to set it, -35 to take damage or +20 to heal (kept between 0 and its max).
-- Current and max HP live in the Pokémon's memo (it keeps them when it moves); the max comes from the sheet.
----------------------------------------------------------------------------------------------------
STAND_MESH, STAND_TEX = "props/stand-v4.obj", "props/stand-wood-v2.jpg"   -- black signs floating above the pedestals
SIGN = { y = 5.4, z = -1.6, face = 0.03 }   -- a sign's centre in the stand's frame (build_props.py SIGN_*)
HP_COLOR, HP_FAINTED = "#FFFFFF", "#FF6B6B"
PEDESTAL_REACH = 1.5 -- a Pokémon this close (sideways) to a pedestal's centre, and resting on it, counts as on it

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

-- The Pokémon resting on a stand's pedestal (column 1..6), or nil.
function pokemonOn(stand, col)
  local top = stand.positionToWorld(Vector(STAND.x[col], STAND.pedestal.y + PEDESTAL_TOP, STAND.pedestal.z))
  for _, obj in ipairs(getAllObjects()) do
    if obj.hasTag("Pokemon") then
      local p = obj.getPosition()
      if near(p, top, PEDESTAL_REACH) and math.abs(p.y - top.y) < 1 then return obj end
    end
  end
end

-- One face's label (an input box under 50 high hides its text). Object UI: 100 units = 1 world unit, x = x (not mirrored), the UI's
-- +y is the object's +z and -z is up.
local function signLabelXml(stand, col, side, rotation, z, st)
  local hp, max = st and st.hp, st and st.maxHp
  return string.format([[
<Panel position="%d %d %d" rotation="%s" width="170" height="50" color="#000000C8" active="%s">
  <InputField id="hpIn_%s_%d_%s" onEndEdit="Global/hpEdited" text="%d" rectAlignment="MiddleLeft" offsetXY="9 0" width="84" height="50"
    fontSize="26" textColor="%s" textAlignment="MiddleRight" characterLimit="8"
    colors="#00000000|#FFFFFF22|#FFFFFF33|#00000000"/>
  <Text rectAlignment="MiddleRight" width="85" height="50" fontSize="26" color="#FFFFFF" alignment="MiddleLeft">/%d</Text>
</Panel>
]], math.floor(STAND.x[col] * 100 + 0.5), math.floor(z * 100 + 0.5), math.floor(-SIGN.y * 100 + 0.5), rotation,
    hp and "true" or "false", stand.guid, col, side, hp or 0, (hp or 1) > 0 and HP_COLOR or HP_FAINTED, max or 0)
end

-- Rewrite a stand's signs from the Pokémon now on its pedestals.
function refreshStand(stand)
  local parts = {}
  for col = 1, #STAND.x do
    local mon = pokemonOn(stand, col)
    local st = mon and hpState(mon)
    if st and not st.maxHp then st = nil end
    parts[#parts + 1] = signLabelXml(stand, col, "F", "-90 0 0", SIGN.z - SIGN.face, st)
    parts[#parts + 1] = signLabelXml(stand, col, "B", "90 0 180", SIGN.z + SIGN.face, st)
  end
  stand.UI.setXml(table.concat(parts))
end

function refreshPedestals()
  for _, obj in ipairs(getAllObjects()) do
    if obj.hasTag("Stand") then refreshStand(obj) end
  end
end

-- A stand gets the model with the signs (reloading it; it comes back through onObjectSpawn with its card snap
-- points put back if the reload dropped them), then its labels.
function setupStand(stand)
  if not (stand and stand.hasTag("Stand")) then return end
  local mesh = (stand.getCustomObject() or {}).mesh or ""
  if mesh ~= "" and not mesh:find(STAND_MESH, 1, true) then
    stand.setCustomObject({ mesh = BASE_URL .. STAND_MESH, diffuse = BASE_URL .. STAND_TEX })
    stand.reload()
    return
  end
  if #(stand.getSnapPoints() or {}) ~= #STAND.x * #CARD_KINDS then stand.setSnapPoints(standSnapPoints()) end   -- card slots: one per row per column
  refreshStand(stand)
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

-- Pokémon put down, picked up or removed: the signs follow (after it has settled or left).
function onObjectDrop(_, obj)
  if obj.hasTag("Pokemon") then Wait.time(refreshPedestals, 0.5) end
end

function onObjectDestroy(obj)
  if obj.hasTag("Pokemon") then Wait.frames(refreshPedestals, 2) end
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

-- A sign's number was edited ("hpIn_<stand guid>_<column>_<side>"): change the HP of the Pokémon on it.
function hpEdited(player, value, id)
  local guid, col = id:match("^hpIn_(%w+)_(%d+)_%a$")
  local stand = guid and getObjectFromGUID(guid)
  if not stand then return end
  local mon = pokemonOn(stand, tonumber(col))
  if mon then
    local st = hpState(mon)
    if st.maxHp then
      local old = st.hp
      local new = parseHp(value, old, st.maxHp)
      if new and new ~= old then
        st.hp = new
        mon.memo = JSON.encode(st)
        local name = st.pokemon ~= "" and st.pokemon or "That Pokémon"
        local change = new - old
        printToAll(string.format("%s: %d → %d HP (%s%d)%s", name, old, new, change > 0 and "+" or "", change,
          new == 0 and (". " .. name .. " fainted!") or ""), new == 0 and { 1, 0.45, 0.45 } or { 0.85, 0.85, 0.85 })
      end
    end
  end
  refreshStand(stand)   -- shows the result, or puts back the number if the entry wasn't one
end

----------------------------------------------------------------------------------------------------
-- Chat commands: !spawn <pokemon>, !item <item>, !skill <warrior skill>, !ability <ability>
----------------------------------------------------------------------------------------------------
CHAT_KINDS = { spawn = "dex", item = "items", skill = "skills", ability = "abilities" }

function onChat(message, player)
  local cmd, query = message:match("^!(%a+)%s+(.+)$")
  local kind = cmd and CHAT_KINDS[cmd:lower()]
  if not kind then return true end
  local names, hits = search(kind, query, 5)
  if #names == 0 then
    player.broadcast("No " .. CATALOGS[kind].noun .. " matches \"" .. query .. "\".", { 1, 0.5, 0.5 })
  elseif hits[1].exact or #hits == 1 or hits[1].score < (hits[2] and hits[2].score or 3) then
    spawnFrom(kind, names[1], player.color)
  else
    player.broadcast("Which one? " .. table.concat(names, ", "), { 1, 1, 0.6 })
  end
  return false  -- keep the command out of the chat log
end
