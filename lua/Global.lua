--[[ PCTTS_MOD — Global script for the Pokemon Conquest tabletop mod.
Source: https://github.com/PCTTS/tts (lua/Global.lua). Edit there, not in TTS.

Toolbar (right edge, a third of the way down the screen), one panel open at a time, each player gets their own:
  * Pokéball: search the roster, click a result and that figure goes on your next free pedestal.
  * Potion:   scroll through (or search) the item cards, click one and it goes in the next free item slot.
  * Swords:   scroll through (or search) the warrior skill cards, click one and it goes in the next free skill slot.
Team stands (tagged "Stand") sit on the two long sides: six pedestals on top, an item card and a warrior skill
card on the slope under each. Which stand is yours depends on your seat colour (SEAT_SIDE).
  * Swirl:    pick a status, then pick up a Pokémon to give it that status (it's tinted in the status's
              type colour). One main status at a time; Confused and Flinched can stack on top.
              "Clear status" returns a Pokémon to normal.
  * Map:      pick which arena the board shows.
Flags on the board: right-click > Capture tints a flag to your seat colour; "Make neutral" resets it.
HP: each Pokémon shows "current/max" HP over its head; click the number and type 120 (set), -35 or +20.
Chat:  !spawn garchomp   !item sitrus   !skill belief   spawn the best match (or list close alternatives).

The roster (figures/index.json) and the cards (cards/index.json) are downloaded from the PCTTS site when the
game loads, so new Pokémon and changed cards appear without editing the mod. The last copies are kept in the
save, so everything still works if the site can't be reached.
--]]

BASE_URL = "https://pctts.github.io/tts/"
ICONS = {
  pokeball = "ui/icons/pokeball-v3.png", map = "ui/icons/map-v3.png", status = "ui/icons/status-v3.png",
  item = "ui/icons/item-v3.png", skill = "ui/icons/skill-v3.png",
}
-- Toolbar geometry in UI units. Icons are drawn at 64 px, close to their on-screen size: TTS doesn't smooth
-- UI images it shrinks, so a much larger image looks jagged.
BAR_ICON, BAR_MARGIN, BAR_GAP = 32, 3, 6
TOOLS = {
  { kind = "dex", icon = "pokeball", tip = "Spawn a Pokémon" },
  { kind = "items", icon = "item", tip = "Item cards" },
  { kind = "skills", icon = "skill", tip = "Warrior skill cards" },
  { kind = "status", icon = "status", tip = "Give a status" },
  { kind = "maps", icon = "map", tip = "Choose the map" },
}
-- The toolbar and its panels sit in a frame covering the top two-thirds of the screen, the toolbar at the frame's
-- middle: a third of the way down the screen at any resolution. A panel's top stays level with the toolbar's.
HUD_HEIGHT = "66.667%"
-- Searchable catalogues behind the search panels.
SEARCH_KINDS = { "dex", "items", "skills" }
-- Panels that also list every name to scroll through (shown while the search box is empty), LIST_ROWS rows tall.
LIST_KINDS = { items = true, skills = true }
LIST_ROWS = 10
CATALOGS = {
  dex = { title = "Spawn a Pokémon", noun = "Pokémon", hint = "Click a result to put it on your next free pedestal." },
  items = { title = "Item cards", noun = "item", hint = "Click a card to place it, or type to search.",
    deckBase = 1000, tag = "Item" },
  skills = { title = "Warrior skill cards", noun = "warrior skill", hint = "Click a card to place it, or type to search.",
    deckBase = 3000, tag = "WarriorSkill" },
}
ROSTER_URL = BASE_URL .. "figures/index.json"
CARDS_URL = BASE_URL .. "cards/index.json"
STATS_URL = BASE_URL .. "data/pokemon.json"   -- every Pokémon's stats from the sheet (tools/build_stats.py)

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

STANDEE_MESH = "models/standee-v1.obj"  -- a Pokémon: art quad on a round base with a facing arrow (build_standee.py)
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
-- each a pedestal on top with an item card and a warrior skill card below it on the slope.
STAND = {
  x = { -17.625, -10.575, -3.525, 3.525, 10.575, 17.625 },
  pedestal = { y = 2.6, z = -1.6 },
  cards = { items = { y = 2.0644, z = -5.1105 },
            skills = { y = 1.0467, z = -8.5481 } },
  tilt = 16.492, cardScale = 1.5, length = 42.3,
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
openPanel, searchHits, mapRows, spawnCount = {}, {}, {}, {}
armed = {}           -- [colour] = status key waiting for that player to pick up a Pokémon
queries = {}         -- [colour .. kind] = what that player last typed in that search box
listViewers = { items = {}, skills = {} }  -- [kind][colour] = true while that player sees the full list
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
  { key = "stats", url = STATS_URL, use = function(t) stats = t; refreshAllHp() end },
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
    for part in (saved .. STATE_SEP):gmatch("(.-)" .. STATE_SEP) do
      local key, text = part:match("^(%a+)=(.*)$")
      if key and text ~= "" then texts[key] = text end
    end
  elseif saved and saved:sub(1, 1) == "{" then   -- an older save: decoded tables (slow, but only once)
    local ok, old = pcall(JSON.decode, saved)
    if ok and type(old) == "table" then texts.legacy = old end
  end
  return texts
end

function onLoad(saved)
  local texts = readSavedState(saved)
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
  for _, obj in ipairs(getAllObjects()) do flagMenu(obj) end   -- context menus aren't saved with the game
  refreshAllHp()
  Wait.time(refreshAllHp, 2)   -- again once the objects have finished loading (their own saved UI can replace ours)
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
    for _, kind in ipairs({ "items", "skills" }) do
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
      ColliderURL = "", Convex = true, MaterialIndex = 3, TypeIndex = 1, CastShadows = true }  -- matte (cardboard): plastic glare washed out the base
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
-- items in the upper row, warrior skills in the lower. The effect is its hover description.
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
  local k = STAND.cardScale
  return spawnObjectData({
    data = {
      Name = "CardCustom",
      Transform = { posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = k, scaleY = 1, scaleZ = k },
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
-- Maps (for now: the states of the locked map board; later the data-driven map system)
----------------------------------------------------------------------------------------------------
local function titleCase(s)
  return (s:gsub("%-", " "):gsub("(%a)(%w*)", function(a, b) return a:upper() .. b end))
end

function findMapBoard()
  for _, o in ipairs(getAllObjects()) do
    local states = o.getStates()
    if states and #states > 0 and (o.getCustomObject() or {}).image then return o end
  end
end

-- { {id=stateId, name="Pugilis", current=true}, ... } sorted by name
function mapList()
  local board = findMapBoard()
  if not board then return {} end
  local data, list = board.getData(), {}
  local function add(id, image, current)
    local file = (image or ""):match("/maps/([%w%-]+)%.%a+$")
    list[#list + 1] = { id = id, name = file and titleCase(file) or ("Map " .. id), current = current }
  end
  add(board.getStateId(), data.CustomImage and data.CustomImage.ImageURL, true)
  for id, st in pairs(data.States or {}) do
    add(tonumber(id), st.CustomImage and st.CustomImage.ImageURL, false)
  end
  table.sort(list, function(a, b) return a.name < b.name end)
  return list
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
  listViewers = { items = {}, skills = {} }

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

    local rows = { string.format('<Text id="mapMsg_%s" class="hint">Click a map to put it on the board.</Text>', c) }
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
  UI.setValue("mapMsg_" .. c, #list > 0 and "Click a map to put it on the board." or "No map board found on the table.")
end

function mapPick(player, _, id)
  local c = player.color
  local m = mapRows[c] and mapRows[c][tonumber(id:match("_(%d+)$"))]
  local board = findMapBoard()
  if not (m and board) or m.current then return end
  board.setState(m.id)
  printToAll(player.steam_name .. " put " .. m.name .. " on the board.", { 0.8, 0.9, 1 })
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

function onObjectSpawn(obj)
  flagMenu(obj)
  showHp(obj)
end

----------------------------------------------------------------------------------------------------
-- HP over each Pokémon's head: "Y/X", on two labels back to back so both sides of the table can read it.
-- Click the number and type 120 to set it, -35 to take damage or +20 to heal (kept between 0 and its max).
-- Current and max HP live in the figure's memo; the max comes from the sheet (data/pokemon.json).
----------------------------------------------------------------------------------------------------
HP_HEIGHT = -255        -- object UI units (100 = one world unit; up is -z): just above a standee's art
HP_LEAN = "-40 0 0"     -- a label's tilt: "-90 0 0" stands it up facing the player, "-40 0 0" leans it back 50 degrees
HP_COLOR, HP_FAINTED = "#FFFFFF", "#FF6B6B"

function maxHp(name)
  local s = stats[name]
  return s and tonumber(s.hp) and math.floor(tonumber(s.hp)) or nil
end

-- Who sees which label: each side of the table gets the one facing it (spectators and the GM: the near side).
-- Labels drawn on one object ignore depth (the later one always shows on top, mirrored from behind), so each
-- player is shown just one.
local function seatsOn(side, extra)
  local list = {}
  for _, c in ipairs(COLORS) do
    if SEAT_SIDE[c] == side then list[#list + 1] = c end
  end
  for _, c in ipairs(extra or {}) do list[#list + 1] = c end
  return table.concat(list, "|")
end

local function hpLabelXml(guid, side, rotation, seats, hp, max)
  return string.format([[
  <Panel id="hp%s" visibility="%s" rotation="%s" width="170" height="50" color="#000000C8">
    <InputField id="hpIn_%s_%s" onEndEdit="Global/hpEdited" text="%d" rectAlignment="MiddleLeft" width="84" height="50"
      fontSize="26" textColor="%s" textAlignment="MiddleRight" characterLimit="8"
      colors="#00000000|#FFFFFF22|#FFFFFF33|#00000000"/>
    <Text rectAlignment="MiddleRight" offsetXY="-9 0" width="84" height="50" fontSize="26" color="#FFFFFF" alignment="MiddleLeft">/%d</Text>
  </Panel>
]], side, seats, rotation, guid, side, hp, hp > 0 and HP_COLOR or HP_FAINTED, max)
end

-- The labels hang from a "spinner" turned by the figure's own yaw, so they keep facing the two long sides of the
-- table whichever way the Pokémon faces (an input box under 50 high hides its text).
local function spinXml(id, yaw)
  return string.format('<Panel id="%s" position="0 0 %d" rotation="0 0 %d" width="10" height="10" color="#00000000">\n',
    id, HP_HEIGHT, yaw)
end

-- Each label is leaned back toward the sky (HP_LEAN), so from anywhere above the table you see its front:
-- from the ends of the table it reads turned on its side, but never mirrored. The far side's label is the
-- same label on a second spinner turned 180 degrees.
local function hpXml(obj, hp, max)
  local yaw = math.floor(obj.getRotation().y + 0.5)
  return spinXml("hpSpin", yaw) .. hpLabelXml(obj.guid, "F", HP_LEAN, seatsOn("south", { "Grey", "Black" }), hp, max)
    .. "</Panel>\n" .. spinXml("hpSpinB", yaw + 180) .. hpLabelXml(obj.guid, "B", HP_LEAN, seatsOn("north"), hp, max)
    .. "</Panel>\n"
end

-- Give a Pokémon its HP labels (or bring them up to date). Its memo gets hp/maxHp if it had none.
function showHp(obj)
  if not (obj and obj.hasTag("Pokemon")) then return end
  local st = figureState(obj)
  local max = maxHp(st.pokemon) or (st.maxHp and math.floor(st.maxHp))
  if not max then return end
  local hp = math.max(0, math.min(max, math.floor(st.hp or max)))
  if st.hp ~= hp or st.maxHp ~= max then
    st.hp, st.maxHp = hp, max
    obj.memo = JSON.encode(st)
  end
  obj.UI.setXml(hpXml(obj, hp, max))
end

-- Keep a Pokémon's labels facing the table's sides after it's turned or put down.
function turnHp(obj, yaw)
  if obj and obj.hasTag("Pokemon") then
    local y = math.floor((yaw or obj.getRotation().y) + 0.5)
    obj.UI.setAttribute("hpSpin", "rotation", "0 0 " .. y)
    obj.UI.setAttribute("hpSpinB", "rotation", "0 0 " .. (y + 180))
  end
end

function onObjectRotate(obj, spin)
  turnHp(obj, spin)
end

function onObjectDrop(_, obj)
  turnHp(obj)
end

function refreshAllHp()
  for _, obj in ipairs(getAllObjects()) do showHp(obj) end
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

function hpEdited(player, value, id)
  local guid = id:match("^hpIn_(%w+)_%a$")
  local obj = guid and getObjectFromGUID(guid)
  if not obj then return end
  local st = figureState(obj)
  if not st.maxHp then return end
  local old = math.floor(st.hp or st.maxHp)
  local new = parseHp(value, old, st.maxHp)
  if new and new ~= old then
    st.hp = new
    obj.memo = JSON.encode(st)
    local name = st.pokemon ~= "" and st.pokemon or "That Pokémon"
    local change = new - old
    printToAll(string.format("%s: %d → %d HP (%s%d)%s", name, old, new, change > 0 and "+" or "", change,
      new == 0 and (". " .. name .. " fainted!") or ""), new == 0 and { 1, 0.45, 0.45 } or { 0.85, 0.85, 0.85 })
  end
  local shown = math.floor(st.hp or st.maxHp)
  for _, side in ipairs({ "F", "B" }) do   -- show the result (or put back the number if the entry wasn't one)
    obj.UI.setAttribute("hpIn_" .. guid .. "_" .. side, "text", tostring(shown))
    obj.UI.setAttribute("hpIn_" .. guid .. "_" .. side, "textColor", shown > 0 and HP_COLOR or HP_FAINTED)
  end
end

----------------------------------------------------------------------------------------------------
-- Chat commands: !spawn <pokemon>, !item <item>, !skill <warrior skill>
----------------------------------------------------------------------------------------------------
CHAT_KINDS = { spawn = "dex", item = "items", skill = "skills" }

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
