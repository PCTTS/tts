# PCTTS

Assets and scripts for a Tabletop Simulator tabletop adaptation of Pokemon Conquest.

- `pokemon/` figurine images (front and back)
- `maps/` arena boards (the old flat map images)
- `arenas/` 3D arenas: each arena's map data, board model and textures, and `index.json` for the in-game map picker
- `props/` 3D pieces: team stands, flags, portals, rope bridges, capture zone frames, Pokimari balls, traps, trees, gift boxes, water gates, fountains, statues, gear plates, blockers
- `rules/` rulebooks as PDFs (dated; a new date means a new version)
- `misc/` table, bags and other pieces
- `tools/` scripts that move a TTS save's images here and rewrite its links

Files are served from GitHub Pages at `https://pctts.github.io/tts/<path>`.
A changed file gets a new name, because Tabletop Simulator caches images by their link.
