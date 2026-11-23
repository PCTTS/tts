"""Try images on the sides of an arena's walls (map.json textures "walls:<surface>", e.g. the sides of Pugilis's
steps) quickly: preview each on the board in the open TTS game from a file on this computer (a few seconds,
nothing pushed), then publish the one to keep.

  python -I tools/wall_texture.py <image>             preview it (the repo isn't touched)
  python -I tools/wall_texture.py <image> --watch     preview again every time the image is saved (Ctrl+C stops)
  python -I tools/wall_texture.py --reset             put the published board back (after previews you don't keep)
  python -I tools/wall_texture.py <image> --publish   keep it: copy it into the arena's textures/, build a new board
                                                      texture version (the mesh is reused when it's unchanged),
                                                      arena index, offline tests, commit + push, wait for GitHub
                                                      Pages, then put the published board on the table
  options:  --arena pugilis   --surface stairs (whose inner walls; several: floor,stairs)   --levels LO HI (fit the
            image from level LO's top to level HI's top on every wall, so its layers line up; default: one level
            from each tile's top)   --across N (copies across a tile; default: the whole number nearest the image's
            own shape). Settings already in map.json are kept unless given.

A previewed board points at a file on this computer that the other players don't have: publish or --reset before
saving the game.
"""
import argparse, json, re, shutil, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import build_board as bb  # noqa: E402
from tts import exec_lua, report  # noqa: E402

SITE = "https://pctts.github.io/tts/"
PREVIEWS = Path(tempfile.gettempdir()) / "pctts-preview"   # outside the repo; TTS caches by link, so each is new

# Swap the board's images in place (its pieces stay put); if that arena isn't on the table, put it there first.
SWAP = """
local name, mesh, diffuse = %s, %s, %s
local function swap()
  for _, o in ipairs(getObjectsWithTag("Board3D")) do
    if o.getName() == name then
      local d = o.getData()
      if mesh ~= "" then d.CustomMesh.MeshURL = mesh d.CustomMesh.ColliderURL = mesh end
      d.CustomMesh.DiffuseURL = diffuse
      local pos, rot = o.getPosition(), o.getRotation()
      o.destruct()
      spawnObjectData({ data = d, position = pos, rotation = rot,
        callback_function = function(b) b.interactable = false end })
      return true
    end
  end
  return false
end
if swap() then return "swapped onto the board" end
if not loadArena(name) then return "no arena called " .. name end
Wait.time(swap, 1)
return "put " .. name .. " on the table and swapped onto its board"
"""


def read_map(folder):
    raw = (folder / "map.json").read_bytes()
    return raw.decode("utf-8").replace("\r\n", "\n"), b"\r\n" in raw


def write_map(folder, text, crlf):
    (folder / "map.json").write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def object_span(text, key):
    """Where `"key": {...}` sits in a JSON text: (start of the key, end of its object), or None."""
    m = re.search(r'"%s"\s*:\s*\{' % re.escape(key), text)
    if not m:
        return None
    depth, i, in_str = 0, m.end() - 1, False
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 1
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return m.start(), i + 1
        i += 1
    sys.exit(f"unbalanced map.json near {key}")


def indent_of(text, pos):
    line = text[text.rfind("\n", 0, pos) + 1:pos]
    return line[:len(line) - len(line.lstrip())]


def set_object(text, key, value, parent):
    """Set `"key": value` inside the object `parent` of a map.json text, keeping the rest of its layout."""
    span = object_span(text, key)
    if span:
        pad = indent_of(text, span[0])
        dumped = json.dumps(value, indent=2, ensure_ascii=False).replace("\n", "\n" + pad)
        return text[:span[0]] + f'"{key}": ' + dumped + text[span[1]:]
    outer = object_span(text, parent)
    if not outer:
        sys.exit(f'map.json has no "{parent}" entry to put "{key}" in')
    brace = text.index("{", outer[0])
    pad = indent_of(text, outer[0]) + "  "
    dumped = json.dumps(value, indent=2, ensure_ascii=False).replace("\n", "\n" + pad)
    return text[:brace + 1] + f'\n{pad}"{key}": ' + dumped + "," + text[brace + 1:]


def set_board(text, files):
    """Point map.json's "board" entry at new published files ({"mesh"/"texture"/"geometry": name})."""
    start, end = object_span(text, "board")
    block = text[start:end]
    for kind, name in files.items():
        block, n = re.subn(r'("%s"\s*:\s*")[^"]*(")' % kind, lambda m: m.group(1) + name + m.group(2), block)
        if n != 1:
            sys.exit(f'map.json\'s "board" has no "{kind}"')
    return text[:start] + block + text[end:]


def wall_spec(data, surface, image, across, levels):
    """The "walls:<surface>" texture spec with a new image (keeping its other settings; mirrored copies if new)."""
    spec = dict((data.get("textures") or {}).get(f"walls:{surface}") or {"vary": "mirror"})
    spec.pop("images", None)
    spec["image"] = image
    if across:
        spec["across"] = across
    if levels:
        spec["levels"] = levels
    return spec


def arena(folder):
    """The arena, with the builder set to its published board's tile size."""
    _, board = published(folder)
    bb.set_tile(json.loads((folder / board["geometry"]).read_text(encoding="utf-8"))["tile"])
    return bb.Arena(folder)


def published(folder):
    data = json.loads(read_map(folder)[0])
    return data, data["board"]


def mesh_changed(a, folder, board, scratch):
    """Build the mesh to `scratch`; True if it differs from the published one."""
    bb.build_mesh(a).write(scratch)
    return scratch.read_bytes() != (folder / board["mesh"]).read_bytes()


def to_tts(name, mesh, diffuse):
    try:
        report(exec_lua(SWAP % (json.dumps(name), json.dumps(mesh), json.dumps(diffuse)), wait=5))
    except OSError:
        print("TTS isn't answering (it only does while a game is loaded)")


def preview(folder, image, surfaces, across, levels):
    t0 = time.time()
    a = arena(folder)
    data, board = published(folder)
    for surface in surfaces:
        a.data.setdefault("textures", {})[f"walls:{surface}"] = wall_spec(data, surface, str(image.resolve()), across,
                                                                          levels)
    PREVIEWS.mkdir(exist_ok=True)
    for old in sorted(PREVIEWS.glob(f"{folder.name}-*"))[:-4]:   # keep just the last few
        old.unlink(missing_ok=True)
    stamp = f"{folder.name}-{time.time_ns()}"
    mesh = PREVIEWS / f"{stamp}.obj"
    mesh_url = mesh.as_uri() if mesh_changed(a, folder, board, mesh) else ""   # new wall slices: a new mesh too
    if not mesh_url:
        mesh.unlink()
    jpg = PREVIEWS / f"{stamp}.jpg"
    bb.draw_texture(a).save(jpg, quality=95)
    print(f"built {jpg} in {time.time() - t0:.1f} s" + (" (with a new mesh)" if mesh_url else ""))
    to_tts(data["name"], mesh_url, jpg.as_uri())


def watch(folder, image, surfaces, across, levels):
    seen = None
    print(f"watching {image} (Ctrl+C stops)")
    try:
        while True:
            try:
                stamp = image.stat().st_mtime_ns
            except FileNotFoundError:
                stamp = None
            if stamp and stamp != seen:
                time.sleep(0.5)   # let the paint program finish writing it
                seen = image.stat().st_mtime_ns
                try:
                    preview(folder, image, surfaces, across, levels)
                except Exception as e:   # a half-written image: try again on the next save
                    print("couldn't build:", e)
            time.sleep(1)
    except KeyboardInterrupt:
        print("stopped")


def run(*cmd):
    print(">", " ".join(cmd))
    return subprocess.run(cmd, cwd=REPO, check=True, capture_output=True, text=True).stdout


def wait_for_pages(paths, minutes=6):
    """Until GitHub Pages serves every path (and the arena index names the first)."""
    end = time.time() + minutes * 60
    while time.time() < end:
        try:
            index = urllib.request.urlopen(f"{SITE}arenas/index.txt?t={time.time_ns()}", timeout=20).read().decode()
            if paths[0] in index and all(urllib.request.urlopen(SITE + p, timeout=20).status == 200 for p in paths):
                return True
        except OSError:
            pass
        time.sleep(8)
    return False


def publish(folder, image, surfaces, across, levels):
    stem = re.sub(r"[^a-z0-9]+", "-", image.stem.lower()).strip("-").removeprefix(folder.name + "-")
    dest = folder / "textures" / f"{stem}{image.suffix.lower()}"   # Pugilis_Cliff2.png -> textures/cliff2.png
    dest.parent.mkdir(exist_ok=True)
    if image.resolve() != dest.resolve():
        shutil.copy2(image, dest)
    text, crlf = read_map(folder)
    data = json.loads(text)
    for surface in surfaces:
        text = set_object(text, f"walls:{surface}", wall_spec(data, surface, f"textures/{dest.name}", across, levels),
                          "textures")
    write_map(folder, text, crlf)

    a = arena(folder)
    _, board = published(folder)
    n = 1 + max(int(m.group(1)) for f in folder.iterdir() if (m := re.match(r"board-v(\d+)\.", f.name)))
    tag = f"v{n}"
    scratch = folder / f"board-{tag}.obj"
    if mesh_changed(a, folder, board, scratch):   # its own new wall slices: a new mesh (and geometry) too
        bb.main([str(folder), "--tag", tag, "--tile", str(bb.TILE)])
        files = {"mesh": f"board-{tag}.obj", "texture": f"board-{tag}.jpg", "geometry": f"board-{tag}.json"}
    else:
        scratch.unlink()
        bb.draw_texture(a).save(folder / f"board-{tag}.jpg", quality=95)
        files = {"texture": f"board-{tag}.jpg"}
    text, crlf = read_map(folder)
    write_map(folder, set_board(text, files), crlf)
    print(f"{data['name']}: {', '.join(files.values())}")

    run(sys.executable, "-I", "tools/build_arena_index.py")
    tests = subprocess.run([sys.executable, "-I", "tools/test_global.py"], cwd=REPO, capture_output=True, text=True)
    if "all checks passed" not in tests.stdout:
        print(tests.stdout[-2000:], tests.stderr[-2000:])
        sys.exit("tests failed: nothing committed")
    rel = lambda p: p.relative_to(REPO).as_posix()   # noqa: E731
    paths = [rel(folder / "map.json"), rel(dest), "arenas/index.json", "arenas/index.txt"] + \
            [rel(folder / f) for f in files.values()]
    run("git", "add", "--", *paths)
    message = (f"{data['name']} texture {tag}: {image.name} on the inner walls of {', '.join(surfaces)}\n\n"
               "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n")
    subprocess.run(["git", "commit", "-q", "-F", "-", "--", *paths], cwd=REPO, check=True, input=message, text=True)
    run("git", "push", "-q")
    print("pushed; waiting for GitHub Pages ...")
    site = [rel(folder / files["texture"])] + ([rel(folder / files["mesh"])] if "mesh" in files else [])
    if not wait_for_pages(site):
        sys.exit("GitHub Pages hasn't caught up yet: pick the map again in a minute")
    _, board = published(folder)
    try:   # the map picker's list too, so picking the map again gets the new board
        exec_lua('WebRequest.get(ARENAS_URL .. "?t=" .. os.time(), function(r) arenas = readData("arenas", r.text) end)')
    except OSError:
        pass
    to_tts(data["name"], SITE + rel(folder / board["mesh"]), SITE + rel(folder / board["texture"]))


def reset(folder):
    data, board = published(folder)
    rel = folder.relative_to(REPO).as_posix()
    to_tts(data["name"], f"{SITE}{rel}/{board['mesh']}", f"{SITE}{rel}/{board['texture']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", type=Path, nargs="?")
    ap.add_argument("--arena", default="pugilis")
    ap.add_argument("--surface", default="stairs")
    ap.add_argument("--across", type=int)
    ap.add_argument("--levels", type=int, nargs=2)
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()
    folder = REPO / "arenas" / args.arena.lower()
    if args.reset:
        return reset(folder)
    if not args.image or not args.image.exists():
        sys.exit(f"no image at {args.image}")
    job = (folder, args.image, args.surface.split(","), args.across, args.levels)
    if args.publish:
        publish(*job)
    elif args.watch:
        watch(*job)
    else:
        preview(*job)


if __name__ == "__main__":
    main()
