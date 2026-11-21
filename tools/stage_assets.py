"""Copy every image/model a TTS save uses out of the local TTS cache into this repo, with readable names.

Usage:  python -I tools/stage_assets.py "<save name or file>" [more saves or Saved Objects .json ...]

Writes:
  pokemon/<name>-front.png / -back.png, maps/<arena>.jpg, misc/...   (files to publish)
  .local/url-map.json   old URL -> repo path (kept out of git; used by rewrite_save.py)
Nothing outside this repo is modified.
"""
import hashlib, json, re, shutil, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TTS = Path.home() / "Documents" / "My Games" / "Tabletop Simulator"
CACHE_DIRS = [TTS / "Mods" / d for d in ("Images", "Models", "Images Raw", "PDF")]
MAP_FILE = REPO / ".local" / "url-map.json"

# Readable names for maps and other non-Pokemon pieces, keyed by old link or Drive file id.
# Kept in .local/ (not published): Drive ids would show who owns the original files.
_names_file = REPO / ".local" / "names.json"
_names = json.loads(_names_file.read_text(encoding="utf-8")) if _names_file.exists() else {}
ARENA_BY_DRIVE_ID = _names.get("maps", {})  # Drive id -> arena name, e.g. "pugilis"
FIXED_NAMES = _names.get("fixed", {})  # link or Drive id -> repo path without extension


def cache_file(url):
    """TTS names cache files after the URL with every non-alphanumeric character removed."""
    stem = re.sub(r"[^A-Za-z0-9]", "", url)
    for d in CACHE_DIRS:
        for f in d.glob(stem + ".*"):
            return f
    return None


def kind(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:2] == b"\xff\xd8":
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:3] == b"GIF":
        return ".gif"
    if data[:5] == b"%PDF-":
        return ".pdf"
    return ".obj"  # TTS meshes are plain-text .obj


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "unnamed"


def walk(objs):
    for o in objs or []:
        yield o
        yield from walk(o.get("ContainedObjects"))
        yield from walk(list((o.get("States") or {}).values()))


def resolve_save(arg):
    p = Path(arg)
    if p.is_file():
        return p
    saves = TTS / "Saves"
    for info in json.loads((saves / "SaveFileInfos.json").read_text(encoding="utf-8")):
        if re.sub(r"^\d+ - | - [\d/]+ [\d:]+ [AP]M$", "", info["Name"]) == arg:
            return Path(info["Directory"].replace("//", "/"))
    sys.exit(f"Save not found: {arg}")


def main(args):
    url_map = json.loads(MAP_FILE.read_text(encoding="utf-8")) if MAP_FILE.exists() else {}
    by_hash = {}  # content hash -> repo path, so identical images are stored once
    for path in url_map.values():
        f = REPO / path
        if f.exists():
            by_hash.setdefault(hashlib.sha256(f.read_bytes()).hexdigest(), path)
    taken = set(url_map.values())
    missing, new = [], 0

    def place(url, base):
        nonlocal new
        if url in url_map:
            return
        src = cache_file(url)
        if not src:
            missing.append((base, url))
            return
        data = src.read_bytes()
        h = hashlib.sha256(data).hexdigest()
        if h in by_hash:
            url_map[url] = by_hash[h]
            return
        path, n = base + kind(data), 2
        while path in taken:
            path, n = f"{base}-{n}{kind(data)}", n + 1
        (REPO / path).parent.mkdir(parents=True, exist_ok=True)
        (REPO / path).write_bytes(data)
        url_map[url] = by_hash[h] = path
        taken.add(path)
        new += 1

    for arg in args:
        save = resolve_save(arg)
        d = json.loads(save.read_text(encoding="utf-8"))
        if d.get("TableURL"):
            place(d["TableURL"], "misc/table")
        figurines = [o for o in walk(d.get("ObjectStates")) if o.get("Name") == "Figurine_Custom"]
        # A Saved Object holding one unnamed Pokemon is named only by its file ("Archeops2.json").
        fallback = re.sub(r"\d+$", "", save.stem).strip() if len(figurines) == 1 else "unnamed"
        for o in walk(d.get("ObjectStates")):
            for key in ("CustomImage", "CustomMesh"):
                for field, url in (o.get(key) or {}).items():
                    if not (isinstance(url, str) and url.startswith("http")):
                        continue
                    drive_id = url.split("id=")[-1] if "drive.google" in url else None
                    if drive_id in ARENA_BY_DRIVE_ID:
                        base = "maps/" + ARENA_BY_DRIVE_ID[drive_id]
                    elif url in FIXED_NAMES or drive_id in FIXED_NAMES:
                        base = FIXED_NAMES.get(url) or FIXED_NAMES[drive_id]
                        base += "-mesh" if field == "MeshURL" else ""
                    elif o.get("Name") == "Figurine_Custom":
                        side = "back" if field == "ImageSecondaryURL" else "front"
                        base = f"pokemon/{slug(o.get('Nickname') or fallback)}-{side}"
                    else:
                        base = f"misc/{slug(o.get('Nickname') or o.get('Name'))}-{slug(field)}"
                    place(url, base)

    MAP_FILE.parent.mkdir(exist_ok=True)
    MAP_FILE.write_text(json.dumps(url_map, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{new} new files; {len(url_map)} URLs mapped; {len(set(url_map.values()))} distinct files")
    for base, url in missing:
        print("NOT IN CACHE:", base, url)


if __name__ == "__main__":
    main(sys.argv[1:])
