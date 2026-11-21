"""Build a figurine image (front + mirrored back) for every Pokemon on the roster.

Usage:  python -I tools/build_figures.py <roster.xlsx (sheet pokemonDB, column A) | roster.txt (one name per line)>
                                         [--only "Name" ["Name" ...]]   rebuild just these, keep the rest

Art comes from PokeAPI's official artwork (the same art as the official Pokedex), pinned to one commit so
rebuilds are identical. Each image is trimmed, fitted onto a square canvas with the feet at the bottom,
and saved as WebP. Names PokeAPI spells differently, placeholders and custom art are in roster-aliases.json.

Writes figures/<name>.webp, figures/<name>-back.webp (the old flat figurines), standees/v2/<name>.webp (the 3D
standee's texture: the art plus its base strip, lossless; mesh models/standee-v1.obj from build_standee.py) and
figures/index.json (roster name -> files).
Downloads are kept in .local/source/ (not published).
"""
import io, json, os, re, sys, time, unicodedata, urllib.error, urllib.request
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_standee import standee_texture  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
SRC = REPO / ".local" / "source"
OUT = REPO / "figures"
STANDEES = REPO / "standees" / "v2"
PIN = "c0542f7c51215d9672439012838c99f520596cbd"  # PokeAPI/sprites commit, 2026-11-13
ART_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/{pin}/sprites/pokemon/other/official-artwork/{id}.png"
CANVAS, MARGIN = 512, 8
TYPE_COLOURS = {  # standard type colours, used for placeholder recolours
    "Normal": "#A8A77A", "Fire": "#EE8130", "Water": "#6390F0", "Electric": "#F7D02C", "Grass": "#7AC74C",
    "Ice": "#96D9D6", "Fighting": "#C22E28", "Poison": "#A33EA1", "Ground": "#E2BF65", "Flying": "#A98FF3",
    "Psychic": "#F95587", "Bug": "#A6B91A", "Rock": "#B6A136", "Ghost": "#735797", "Dragon": "#6F35FC",
    "Dark": "#705746", "Steel": "#B7B7CE", "Fairy": "#D685AD",
}


def fetch(url, tries=6):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pctts-figure-builder"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == tries - 1:
                raise
        except urllib.error.URLError:
            if attempt == tries - 1:
                raise
        time.sleep(2 ** attempt)


def roster_names(path):
    p = Path(path)
    if p.suffix.lower() == ".xlsx":
        import openpyxl
        ws = openpyxl.load_workbook(p, read_only=True)["pokemonDB"]
        return [str(r[0]).strip() for r in ws.iter_rows(min_row=2, values_only=True) if r and r[0]]
    return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def ascii_lower(name):
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()


def file_name(name):
    """Roster name -> file name: 'Sirfetch'd' -> 'sirfetchd', 'Zygarde 10%' -> 'zygarde-10'."""
    s = re.sub(r"['.%]", "", ascii_lower(name))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def pokeapi_key(name):
    """Roster name -> PokeAPI-style name: 'Charizard X Mega' -> 'charizard-mega-x'."""
    toks = re.sub(r"[^a-z0-9 -]", "", ascii_lower(name).replace("%", "")).replace("-", " ").split()
    if "mega" in toks:
        xy = [t for t in toks if t in ("x", "y", "z")]
        toks = [t for t in toks if t not in ("mega", "x", "y", "z")] + ["mega"] + xy
    return "-".join(toks)


def resolve(name, aliases, api):
    """Return ('pokeapi', id, apiname) | ('recolor', id, type) | ('file', filename) | None."""
    a = aliases.get(name)
    if a and "pokeapi" in a:
        return ("pokeapi", api[a["pokeapi"]], a["pokeapi"])
    if a and "recolor" in a:
        return ("recolor", api[a["recolor"]], a["type"])
    if a and "file" in a:
        return ("file", a["file"])
    k = pokeapi_key(name)
    if k in api:
        return ("pokeapi", api[k], k)
    forms = sorted((i, n) for n, i in api.items() if n.startswith(k + "-"))  # default form has the lowest id
    return ("pokeapi", forms[0][0], forms[0][1]) if forms else None


def fit(im):
    """Trim empty space, then fit onto the canvas, centred, standing on the bottom edge."""
    im = im.convert("RGBA")
    box = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    im = im.crop(box)
    scale = min((CANVAS - 2 * MARGIN) / im.width, (CANVAS - 2 * MARGIN) / im.height)
    im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
    out = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    out.alpha_composite(im, ((CANVAS - im.width) // 2, CANVAS - MARGIN - im.height))
    return out


def recolor(im, type_name):
    """Placeholder look: the original shading, tinted in one type colour."""
    im = im.convert("RGBA")
    tinted = ImageOps.colorize(ImageOps.grayscale(im), black="#101010", mid=TYPE_COLOURS[type_name], white="#FFFFFF")
    tinted.putalpha(im.getchannel("A"))
    return tinted


def make_figure(job):
    """Build one roster entry's front and back images; returns its index entry. Runs in a worker process."""
    n, r = job
    if r[0] == "file":
        art, source = Image.open(TOOLS / "custom" / r[1]), "custom"
    else:
        art = Image.open(io.BytesIO((SRC / f"{r[1]}.png").read_bytes()))
        art, source = (recolor(art, r[2]), f"placeholder: {r[2]}-tinted") if r[0] == "recolor" else (art, r[2])
    front = fit(art)
    f = file_name(n)
    front.save(OUT / f"{f}.webp", "WEBP", quality=90, method=6)
    ImageOps.mirror(front).save(OUT / f"{f}-back.webp", "WEBP", quality=90, method=6)
    standee_texture(front).save(STANDEES / f"{f}.webp", "WEBP", lossless=True, method=6)
    return {"front": f"figures/{f}.webp", "back": f"figures/{f}-back.webp", "standee": f"standees/v2/{f}.webp",
            "source": source}


def main(args):
    if not args:
        sys.exit(__doc__)
    names = roster_names(args[0])
    only = set(args[args.index("--only") + 1:]) if "--only" in args else None
    if only and only - set(names):
        sys.exit(f"Not on the roster: {sorted(only - set(names))}")
    aliases = {k: v for k, v in json.loads((TOOLS / "roster-aliases.json").read_text(encoding="utf-8")).items()
               if not k.startswith("_")}
    SRC.mkdir(parents=True, exist_ok=True)
    api_file = SRC / "pokeapi-list.json"
    if not api_file.exists():
        api_file.write_bytes(fetch("https://pokeapi.co/api/v2/pokemon?limit=5000"))
    api = {e["name"]: int(e["url"].rstrip("/").split("/")[-1])
           for e in json.loads(api_file.read_text(encoding="utf-8"))["results"]}

    plan, unresolved = {}, []
    for n in names:
        r = resolve(n, aliases, api)
        (plan.__setitem__(n, r) if r else unresolved.append(n))
    clashes = {}
    for n in plan:
        clashes.setdefault(file_name(n), []).append(n)
    clashes = {k: v for k, v in clashes.items() if len(v) > 1}
    if clashes:
        sys.exit(f"Different roster names give the same file name: {clashes}")

    ids = sorted({r[1] for r in plan.values() if r[0] in ("pokeapi", "recolor")})
    todo = [i for i in ids if not (SRC / f"{i}.png").exists()]
    print(f"{len(names)} on roster, {len(plan)} resolved; downloading {len(todo)} of {len(ids)} artworks")

    def download(i):
        (SRC / f"{i}.png").write_bytes(fetch(ART_URL.format(pin=PIN, id=i)))

    with ThreadPoolExecutor(4) as pool:
        list(pool.map(download, todo))

    OUT.mkdir(exist_ok=True)
    STANDEES.mkdir(parents=True, exist_ok=True)
    index_file = OUT / "index.json"
    index = json.loads(index_file.read_text(encoding="utf-8")) if only and index_file.exists() else {}
    jobs = [(n, r) for n, r in sorted(plan.items()) if not only or n in only]
    with ProcessPoolExecutor(os.cpu_count()) as pool:  # one figure per core
        for n, entry in zip((n for n, _ in jobs), pool.map(make_figure, jobs, chunksize=4)):
            index[n] = entry
    index_file.write_text(json.dumps(dict(sorted(index.items())), indent=1, ensure_ascii=False), encoding="utf-8")
    size = sum(p.stat().st_size for p in OUT.glob("*.webp"))
    print(f"wrote {len(index) * 2} images ({size / 1e6:.1f} MB) + figures/index.json")
    for n in unresolved:
        print("NO ART FOUND:", n)


if __name__ == "__main__":
    main(sys.argv[1:])
