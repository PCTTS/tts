# Pugilis — the original look (before the sand textures)

Keep these files: they are the board as it was before any image textures were added.

- **Published files:** `board-v1.obj` + `board-v1.jpg` (+ `board-v1.json`), built at tile size 3.24875.
  In TTS: mesh and collider `arenas/pugilis/board-v1.obj`, texture `arenas/pugilis/board-v1.jpg`.
- **Map data:** `map.json` as of commit `6e0f55c` — no `"textures"` entry
  (`git show 6e0f55c:arenas/pugilis/map.json`).
- **Builder:** `tools/build_board.py` as of commit `6e0f55c`.

What it looked like:

- Every tile a flat colour from the palette, with a slight random brightness per tile, a light/dark slab bevel,
  a thin grout line, and fine grain over everything:
  floor `#D9BC8E`, stairs `#C8A676`, pit `#A9845A`.
- Stairs: three step lines per tile (dark `(60, 40, 25)` at alpha 150, light `(255, 245, 225)` at alpha 90),
  nested L's on the corner staircases, straight lines in the alcoves.
- All walls (inner and the board's outer edge): rock in `#8E6C48`, darker toward the bottom, with wavy
  horizontal strata lines.
- Markers, all drawn upright: red fall edges `#D2392C`, spawn rings (blue 1 / red 2), flags, ATK/DEF bells.

To rebuild it from today's builder: remove `"textures"` from `map.json`, remove `"paint"` and `"orient"` from the
`F`, `A` and `D` legend entries (the original painted the flags, and drew every symbol upright), and set the stair
line alphas in `draw_steps` back to 150 / 90, then build with `--tile 3.24875`.

What changed afterwards (see `git log -- arenas/pugilis`): dirt textures on the floor, stairs and pit
(user's art `Pugilis_Dirt2/5`, random turns and mirrors, stairs/pit darkened to their palette colours),
much fainter stair lines, sand on the inner and outer walls darkened to the pit colour, and (with the 3D bells
and flags) the painted flags dropped and the bell symbols turned to face away from the pit.
