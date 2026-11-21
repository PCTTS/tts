"""Write every Pokemon's stats from the spreadsheet to data/pokemon.json (the TTS mod downloads it).

Usage:  python -I tools/build_stats.py <spreadsheet.xlsx>     (sheet "pokemonDB")
data/pokemon.json: name -> {hp, atk, def, spd, rng, types: [primary, secondary?]}, names exactly as the
roster (figures/index.json) spells them. The mod shows each Pokemon's HP over its standee from "hp".
"""
import json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "pokemon.json"


def number(v):
    if v is None or v == "":
        return None
    f = float(v)
    return int(f) if f == int(f) else f


def main(argv):
    if not argv:
        sys.exit(__doc__)
    import openpyxl
    ws = openpyxl.load_workbook(argv[0], read_only=True, data_only=True)["pokemonDB"]
    rows = ws.iter_rows(values_only=True)
    head = [str(h).strip() if h else "" for h in next(rows)]
    col = {h: i for i, h in enumerate(head)}
    stats, missing = {}, []
    for r in rows:
        if not r or not r[0]:
            continue
        name = str(r[0]).strip()
        entry = {"hp": number(r[col["HP"]]), "atk": number(r[col["ATK"]]), "def": number(r[col["DEF"]]),
                 "spd": number(r[col["SPD"]]), "rng": number(r[col["RNG"]]),
                 "types": [t for t in (r[col["P Type"]], r[col["S Type"]]) if t]}
        if entry["hp"] is None:
            missing.append(name)
        stats[name] = entry
    roster = json.loads((REPO / "figures" / "index.json").read_text(encoding="utf-8"))
    no_stats = sorted(n for n in roster if n not in stats or stats[n]["hp"] is None)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(dict(sorted(stats.items())), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(stats)} Pokemon -> {OUT.relative_to(REPO)}; roster names without HP: {no_stats or 'none'}")


if __name__ == "__main__":
    main(sys.argv[1:])
