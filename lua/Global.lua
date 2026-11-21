--[[ PCTTS_MOD — Global script for the Pokemon Conquest tabletop mod.
Source: https://github.com/PCTTS/tts (lua/Global.lua). Edit there, not in TTS.

Toolbar (right edge of the screen), one panel open at a time, each player gets their own:
  * Pokéball: search the roster, click a result and that figure appears in front of your seat.
  * Map:      pick which arena the board shows.
Chat:  !spawn garchomp   spawns the best match (and lists close alternatives if unsure).

The roster comes from figures/index.json on the PCTTS site, so new Pokemon appear without editing the mod.
The last roster loaded is kept in the save, so the spawner still works if the site can't be reached.
--]]

BASE_URL = "https://pctts.github.io/tts/"
ROSTER_URL = BASE_URL .. "figures/index.json"
ICONS = { pokeball = "ui/icons/pokeball.png", map = "ui/icons/map.png" }
FIGURE_SCALE = 1.5   -- figurine ImageScalar; the old sprite figurines used 1.5
FRONT_YAW = 0        -- added to the seat's rotation so the figure's front faces its player
RESULTS = 8          -- search results shown at once
MAX_MAPS = 16        -- rows in the map panel
COLORS = { "White", "Brown", "Red", "Orange", "Yellow", "Green", "Teal", "Blue", "Purple", "Pink", "Grey", "Black" }

roster = {}          -- name -> { front = "...", back = "..." } (paths relative to BASE_URL)
rosterList = {}      -- sorted { name, key, words } for searching
openPanel, dexHits, mapRows, spawnCount = {}, {}, {}, {}

----------------------------------------------------------------------------------------------------
-- Save / load
----------------------------------------------------------------------------------------------------
function onLoad(saved)
  local state = (saved and saved ~= "") and JSON.decode(saved) or {}
  if state.roster then setRoster(state.roster, "saved copy") end
  buildUI()
  fetchRoster()
end

function onSave()
  return JSON.encode({ roster = roster })
end

function log(msg)
  print("[PCTTS] " .. msg)
end

----------------------------------------------------------------------------------------------------
-- Roster and search
----------------------------------------------------------------------------------------------------
local function norm(s)
  s = s:lower():gsub("é", "e"):gsub("♀", "f"):gsub("♂", "m")
  return (s:gsub("[^%w]", ""))
end

function setRoster(index, from)
  local list = {}
  for name in pairs(index) do
    local words = {}
    for w in name:gmatch("[^%s%-%(%)]+") do words[#words + 1] = norm(w) end
    list[#list + 1] = { name = name, key = norm(name), words = words }
  end
  table.sort(list, function(a, b) return a.name < b.name end)
  roster, rosterList = index, list
  log("Pokémon roster: " .. #list .. " (" .. from .. ")")
end

function fetchRoster()
  WebRequest.get(ROSTER_URL, function(req)
    if req.is_error or not req.text or req.text == "" then
      log("Couldn't download the roster (" .. tostring(req.error) .. "); using the saved copy.")
      return
    end
    local ok, index = pcall(JSON.decode, req.text)
    if ok and type(index) == "table" and next(index) then setRoster(index, "downloaded") end
  end)
end

-- Best matches for a typed query: whole-name prefix first, then a word prefix, then anywhere; shorter names first.
function searchRoster(query, limit)
  local q = norm(query or "")
  if q == "" then return {}, {} end
  local hits = {}
  for _, e in ipairs(rosterList) do
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

----------------------------------------------------------------------------------------------------
-- Spawning
----------------------------------------------------------------------------------------------------
-- In front of the player's seat, in a row of six so repeated spawns don't land on each other.
local function spawnSpot(color)
  local n = spawnCount[color] or 0
  spawnCount[color] = n + 1
  local slot = (n % 6) - 2.5
  local ok, hand = pcall(function() return Player[color].getHandTransform() end)
  if ok and hand then
    local fwd = Vector(hand.forward.x, 0, hand.forward.z):normalized()
    local right = Vector(fwd.z, 0, -fwd.x)
    local pos = hand.position + fwd * 5 + right * (slot * 2.6)
    return Vector(pos.x, 4, pos.z), Vector(0, hand.rotation.y + FRONT_YAW, 0)
  end
  return Vector(slot * 2.6, 4, 0), Vector(0, FRONT_YAW, 0)  -- no seat (spectator): middle of the table
end

function spawnPokemon(name, color)
  local files = roster[name]
  if not files then return nil end
  local pos, rot = spawnSpot(color or "Grey")
  return spawnObjectData({
    data = {
      Name = "Figurine_Custom",
      Transform = { posX = 0, posY = 0, posZ = 0, rotX = 0, rotY = 0, rotZ = 0, scaleX = 1, scaleY = 1, scaleZ = 1 },
      Nickname = name,
      Tags = { "Pokemon" },
      Memo = JSON.encode({ pokemon = name }),
      CustomImage = {
        ImageURL = BASE_URL .. files.front,
        ImageSecondaryURL = BASE_URL .. files.back,
        ImageScalar = FIGURE_SCALE,
        WidthScale = 0,
      },
    },
    position = pos,
    rotation = rot,
  })
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
local function panelXml(kind, c, title, height, body)
  return string.format([[
<VerticalLayout id="%s_%s" visibility="%s" active="false" rectAlignment="MiddleRight" offsetXY="-56 0" width="290" height="%d"
       color="#141414F2" outline="#303030" outlineSize="1 1" padding="8 8 8 8" spacing="4"
       childForceExpandHeight="false" childForceExpandWidth="true">
  <HorizontalLayout preferredHeight="28" flexibleHeight="0" childForceExpandWidth="false" spacing="4">
    <Text class="title" flexibleWidth="1">%s</Text>
    <Button class="close" preferredWidth="28" onClick="closePanel" text="X"/>
  </HorizontalLayout>
  %s
  <Panel flexibleHeight="1"/>
</VerticalLayout>
]], kind, c, c, height, title, body)
end

function buildUI()
  local assets = {}
  for name, path in pairs(ICONS) do assets[#assets + 1] = { name = name, url = BASE_URL .. path } end
  UI.setCustomAssets(assets)

  local xml = { [[
<Defaults>
  <Button class="bar" colors="#00000000|#FFFFFF33|#FFFFFF66|#00000000" tooltipPosition="Left" preferredHeight="44" flexibleHeight="0"/>
  <Button class="row" fontSize="15" textAlignment="MiddleLeft" padding="10 0 0 0" textColor="#FFFFFF"
          colors="#2a2a2a|#3d6fb8|#24477a|#2a2a2a" preferredHeight="28" flexibleHeight="0"/>
  <Button class="close" fontSize="14" textColor="#FFFFFF" colors="#2a2a2a|#c0392b|#962d22|#2a2a2a"/>
  <Text class="title" fontSize="16" fontStyle="Bold" color="#FFFFFF" alignment="MiddleLeft"/>
  <Text class="hint" fontSize="12" color="#AAAAAA" alignment="MiddleLeft" preferredHeight="18" flexibleHeight="0"/>
  <InputField class="search" fontSize="16" preferredHeight="34" flexibleHeight="0" characterLimit="40"/>
</Defaults>
<VerticalLayout id="toolbar" rectAlignment="MiddleRight" width="52" height="104" padding="4 4 4 4" spacing="4"
                color="#000000E6" outline="#303030" outlineSize="1 1" childForceExpandHeight="false">
  <Button class="bar" icon="pokeball" tooltip="Spawn a Pokémon" onClick="toggleDex"/>
  <Button class="bar" icon="map" tooltip="Choose the map" onClick="toggleMaps"/>
</VerticalLayout>
]] }
  for _, c in ipairs(COLORS) do
    local rows = {}
    rows[1] = string.format('<InputField id="dexIn_%s" class="search" placeholder="Type part of a name..." onValueChanged="dexSearch"/>', c)
    rows[2] = string.format('<Text id="dexMsg_%s" class="hint">Click a result to place it in front of you.</Text>', c)
    for i = 1, RESULTS do
      rows[#rows + 1] = string.format('<Button id="dexRes_%s_%d" class="row" active="false" onClick="dexPick" text=" "/>', c, i)
    end
    xml[#xml + 1] = panelXml("dex", c, "Spawn a Pokémon", 104 + RESULTS * 32, table.concat(rows, "\n  "))

    rows = { string.format('<Text id="mapMsg_%s" class="hint">Click a map to put it on the board.</Text>', c) }
    for i = 1, MAX_MAPS do
      rows[#rows + 1] = string.format('<Button id="mapRes_%s_%d" class="row" active="false" onClick="mapPick" text=" "/>', c, i)
    end
    xml[#xml + 1] = panelXml("maps", c, "Choose the map", 70 + MAX_MAPS * 32, table.concat(rows, "\n  "))
  end
  UI.setXml(table.concat(xml))
end

local function show(c, kind)
  for _, k in ipairs({ "dex", "maps" }) do
    UI.setAttribute(k .. "_" .. c, "active", (k == kind) and "true" or "false")
  end
  openPanel[c] = kind
end

function closePanel(player)
  show(player.color, nil)
end

function toggleDex(player)
  local c = player.color
  show(c, openPanel[c] ~= "dex" and "dex" or nil)
end

function toggleMaps(player)
  local c = player.color
  if openPanel[c] == "maps" then return show(c, nil) end
  refreshMaps(c)
  show(c, "maps")
end

function dexSearch(player, value)
  local c = player.color
  local names, hits = searchRoster(value, RESULTS)
  dexHits[c] = names
  for i = 1, RESULTS do
    local id = "dexRes_" .. c .. "_" .. i
    if names[i] then UI.setAttribute(id, "text", names[i]) end
    UI.setAttribute(id, "active", names[i] and "true" or "false")
  end
  local msg
  if (value or "") == "" then
    msg = "Click a result to place it in front of you."
  elseif #names == 0 then
    msg = "No Pokémon matches \"" .. value .. "\"."
  elseif #hits > RESULTS then
    msg = #hits .. " matches, showing the best " .. RESULTS .. "."
  else
    msg = #hits .. (#hits == 1 and " match." or " matches.")
  end
  UI.setValue("dexMsg_" .. c, msg)
end

function dexPick(player, _, id)
  local c = player.color
  local name = dexHits[c] and dexHits[c][tonumber(id:match("_(%d+)$"))]
  if name and spawnPokemon(name, c) then UI.setValue("dexMsg_" .. c, "Placed " .. name .. ".") end
end

function refreshMaps(c)
  local list = mapList()
  mapRows[c] = list
  for i = 1, MAX_MAPS do
    local id, m = "mapRes_" .. c .. "_" .. i, list[i]
    if m then
      UI.setAttribute(id, "text", m.current and (m.name .. "   (on the board)") or m.name)
      UI.setAttribute(id, "colors", m.current and "#3d6fb8|#3d6fb8|#24477a|#3d6fb8" or "#2a2a2a|#3d6fb8|#24477a|#2a2a2a")
    end
    UI.setAttribute(id, "active", m and "true" or "false")
  end
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
-- Chat command
----------------------------------------------------------------------------------------------------
function onChat(message, player)
  local query = message:match("^!spawn%s+(.+)$")
  if not query then return true end
  local names, hits = searchRoster(query, 5)
  if #names == 0 then
    player.broadcast("No Pokémon matches \"" .. query .. "\".", { 1, 0.5, 0.5 })
  elseif hits[1].exact or #hits == 1 or hits[1].score < (hits[2] and hits[2].score or 3) then
    spawnPokemon(names[1], player.color)
  else
    player.broadcast("Which one? " .. table.concat(names, ", "), { 1, 1, 0.6 })
  end
  return false  -- keep the command out of the chat log
end
