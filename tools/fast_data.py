"""Write the data the game downloads at every load as plain text the TTS script can read fast.

Usage:  python -I tools/fast_data.py      (the build tools also run it after writing their JSON)
Reads figures/index.json, cards/index.json, data/pokemon.json and arenas/index.json; writes figures/index.txt,
cards/index.txt, data/pokemon.txt and arenas/index.txt.

Why: TTS's Lua (MoonSharp) decodes JSON at about 7 KB a second, so the ~470 KB of JSON froze the game for close
to a minute on every load and rewind. These files hold the same tables as one record per line, fields split by
tabs, which Global.lua splits with plain text search in a fraction of a second (readData). Formats (first line
"PCTTS-DATA-1 <kind>"; an empty field is nil):
  roster  name, front, back, standee, source
  cards   "back", kind, image  |  "card", kind, name, class, group, face, effect
  stats   name, hp, atk, def, spd, rng, types (comma-separated)
  arenas  "arena", name, mesh, texture, table, depth, turns  |  "snaps", x,y,z;x,y,z;...  |  "piece", key=value, ...
          (pos = x,y,z; convex/free = true/false; yaw/material/pair/tile/tiles = numbers)
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HEAD = "PCTTS-DATA-1 "
FILES = {"roster": "figures/index", "cards": "cards/index", "stats": "data/pokemon", "arenas": "arenas/index"}


def field(v):
    if v is None:
        return ""
    s = str(v)
    if any(ch in s for ch in "\t\n\r"):
        raise ValueError(f"tab or newline in {s!r}")
    return s


def num(v):
    return f"{v:.4f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def roster(d):
    return [[n, e.get("front"), e.get("back"), e.get("standee"), e.get("source")] for n, e in d.items()]


def cards(d):
    rows = [["back", kind, path] for kind, path in d["backs"].items()]
    for kind in ("abilities", "items", "skills"):
        rows += [["card", kind, n, e.get("class"), e.get("group"), e.get("face"), e.get("effect")] for n, e in d[kind].items()]
    return rows


def stats(d):
    return [[n, e["hp"], e["atk"], e["def"], e["spd"], e["rng"], ",".join(e["types"])] for n, e in d.items()]


def arenas(d):
    rows = []
    for name, e in d.items():
        rows.append(["arena", name, e["mesh"], e["texture"], e.get("table", ""), num(e["depth"]) if "depth" in e else "",
                     str(e.get("turns", ""))])
        rows.append(["snaps", ";".join(",".join(num(v) for v in p) for p in e["snaps"])])
        for p in e["pieces"]:
            kv = []
            for k, v in p.items():
                if k == "pos":
                    v = ",".join(num(x) for x in v)
                elif isinstance(v, bool):
                    v = "true" if v else "false"
                elif isinstance(v, (int, float)):
                    v = num(v)
                kv.append(f"{k}={field(v)}")
            rows.append(["piece"] + kv)
    return rows


def main():
    for kind, stem in FILES.items():
        data = json.loads((REPO / f"{stem}.json").read_text(encoding="utf-8"))
        rows = globals()[kind](data)
        text = HEAD + kind + "\n" + "\n".join("\t".join(field(v) for v in row) for row in rows) + "\n"
        out = REPO / f"{stem}.txt"
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            out.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {stem}.txt ({len(text) // 1024} KB, {len(rows)} lines)")


if __name__ == "__main__":
    main()
