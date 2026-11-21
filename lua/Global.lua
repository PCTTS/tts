--[[ PCTTS_MOD — Global script for the Pokemon Conquest tabletop mod.
Source: https://github.com/PCTTS/tts (lua/Global.lua). Edit there, not in TTS.

Pokemon spawner
  * "Pokémon" button (left edge) opens a search panel for the player who clicks it; each player has their own.
  * Type part of a name, click a result: that figure appears in front of your seat.
  * Chat:  !spawn garchomp   spawns the best match (and lists close alternatives if unsure).
The roster comes from figures/index.json on the PCTTS site, so new Pokemon appear without editing the mod.
The last roster loaded is kept in the save, so the spawner still works if the site can't be reached.
--]]

BASE_URL = "https://pctts.github.io/tts/"
ROSTER_URL = BASE_URL .. "figures/index.json"
FIGURE_SCALE = 1.5   -- figurine ImageScalar; the old sprite figurines used 1.5
FRONT_YAW = 0        -- added to the seat's rotation so the figure's front faces its player
RESULTS = 8          -- search results shown at once
COLORS = { "White", "Brown", "Red", "Orange", "Yellow", "Green", "Teal", "Blue", "Purple", "Pink", "Grey", "Black" }

roster = {}          -- name -> { front = "...", back = "..." } (paths relative to BASE_URL)
rosterList = {}      -- sorted { name, key, words } for searching
dexOpen, dexHits, spawnCount = {}, {}, {}

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

----------------------------------------------------------------------------------------------------
-- Roster
----------------------------------------------------------------------------------------------------
local function norm(s)
  s = s:lower():gsub("é", "e"):gsub("♀", "f"):gsub("♂", "m")
  return (s:gsub("[^%w]", ""))
end

function setRoster(index, from)
  local list = {}
  for name, files in pairs(index) do
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
  if q == "" then return {} end
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
-- Search panel (one per player colour, each visible only to that colour)
----------------------------------------------------------------------------------------------------
function buildUI()
  local xml = {
    [[<Defaults>
  <Button class="dexResult" fontSize="15" alignment="MiddleLeft" textAlignment="MiddleLeft" padding="10 0 0 0"
          colors="#2a2a2a|#3d6fb8|#24477a|#2a2a2a" textColor="#FFFFFF" preferredHeight="28"/>
  <Button class="dexIcon" fontSize="14" colors="#2a2a2a|#c0392b|#962d22|#2a2a2a" textColor="#FFFFFF"/>
  <Text class="dexTitle" fontSize="16" fontStyle="Bold" color="#FFFFFF" alignment="MiddleLeft"/>
  <Text class="dexHint" fontSize="12" color="#AAAAAA" alignment="MiddleLeft"/>
</Defaults>
<Button id="dexToggle" onClick="dexToggle" rectAlignment="MiddleLeft" offsetXY="68 0" width="110" height="36"
        fontSize="16" fontStyle="Bold" colors="#c0392b|#e74c3c|#962d22|#c0392b" textColor="#FFFFFF">Pokémon</Button>
]] }
  for _, c in ipairs(COLORS) do
    local results = {}
    for i = 1, RESULTS do
      results[i] = string.format('<Button id="dexRes_%s_%d" class="dexResult" active="false" onClick="dexPick"></Button>', c, i)
    end
    xml[#xml + 1] = string.format([[
<Panel id="dex_%s" visibility="%s" active="false" rectAlignment="MiddleLeft" offsetXY="186 0" width="290" height="%d"
       color="#161616F2" padding="8 8 8 8">
  <VerticalLayout spacing="4" childForceExpandHeight="false" childAlignment="UpperCenter">
    <HorizontalLayout preferredHeight="28" childForceExpandWidth="false" spacing="4">
      <Text class="dexTitle" flexibleWidth="1">Spawn a Pokémon</Text>
      <Button class="dexIcon" onClick="dexToggle" preferredWidth="28">X</Button>
    </HorizontalLayout>
    <InputField id="dexIn_%s" preferredHeight="34" fontSize="16" placeholder="Type part of a name..."
                onValueChanged="dexSearch" characterLimit="40"/>
    <Text id="dexMsg_%s" class="dexHint" preferredHeight="18">Click a result to place it in front of you.</Text>
    %s
  </VerticalLayout>
</Panel>
]], c, c, 104 + RESULTS * 32, c, c, table.concat(results, "\n    "))
  end
  UI.setXml(table.concat(xml))
end

function dexToggle(player)
  local c = player.color
  dexOpen[c] = not dexOpen[c]
  UI.setAttribute("dex_" .. c, "active", dexOpen[c] and "true" or "false")
end

function dexSearch(player, value)
  local c = player.color
  local names, hits = searchRoster(value, RESULTS)
  dexHits[c] = names
  for i = 1, RESULTS do
    local id = "dexRes_" .. c .. "_" .. i
    if names[i] then
      UI.setValue(id, names[i])
      UI.setAttribute(id, "active", "true")
    else
      UI.setAttribute(id, "active", "false")
    end
  end
  local msg
  if (value or "") == "" then
    msg = "Click a result to place it in front of you."
  elseif #names == 0 then
    msg = "No Pokémon matches \"" .. value .. "\"."
  else
    msg = #hits > RESULTS and (#hits .. " matches, showing the best " .. RESULTS) or (#hits .. " match" .. (#hits == 1 and "" or "es"))
  end
  UI.setValue("dexMsg_" .. c, msg)
end

function dexPick(player, _, id)
  local c = player.color
  local i = tonumber(id:match("_(%d+)$"))
  local name = dexHits[c] and dexHits[c][i]
  if name and spawnPokemon(name, c) then
    UI.setValue("dexMsg_" .. c, "Placed " .. name .. ".")
  end
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

function log(msg)
  print("[PCTTS] " .. msg)
end
