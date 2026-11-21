"""Write a copy of a TTS save (or Saved Object) whose asset links point at this repo's GitHub Pages site.

Usage:  python -I tools/rewrite_save.py "<save name or file>" [...]   [--base URL] [--no-check]

Each input is left untouched. Copies go to  Saves/PCTTS/  (saves) or  Saves/Saved Objects/PCTTS/  (objects).
Before writing, every new link is fetched once to confirm it is live (skip with --no-check).
"""
import json, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage_assets import MAP_FILE, TTS, resolve_save  # noqa: E402

DEFAULT_BASE = "https://pctts.github.io/tts/"


def rewrite(node, url_map, base, unmapped):
    if isinstance(node, dict):
        return {k: rewrite(v, url_map, base, unmapped) for k, v in node.items()}
    if isinstance(node, list):
        return [rewrite(v, url_map, base, unmapped) for v in node]
    if isinstance(node, str) and node.startswith("http"):
        if node in url_map:
            return base + url_map[node]
        if not node.startswith(base):
            unmapped.add(node)
    return node


def live(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=20) as r:
            return r.status == 200
    except Exception:
        return False


def main(argv):
    base, check, args = DEFAULT_BASE, True, []
    it = iter(argv)
    for a in it:
        if a == "--base":
            base = next(it).rstrip("/") + "/"
        elif a == "--no-check":
            check = False
        else:
            args.append(a)
    url_map = json.loads(MAP_FILE.read_text(encoding="utf-8"))

    if check:
        urls = sorted({base + p for p in url_map.values()})
        with ThreadPoolExecutor(16) as pool:
            dead = [u for u, ok in zip(urls, pool.map(live, urls)) if not ok]
        if dead:
            print(f"{len(dead)} of {len(urls)} links are not live yet, nothing written. First few:")
            print("\n".join(dead[:10]))
            sys.exit(1)
        print(f"All {len(urls)} links are live.")

    for arg in args:
        src = resolve_save(arg)
        data = json.loads(src.read_text(encoding="utf-8"))
        unmapped = set()
        out = rewrite(data, url_map, base, unmapped)
        is_object = "Saved Objects" in src.parts
        dest_dir = TTS / "Saves" / ("Saved Objects" if is_object else "") / "PCTTS"
        dest_dir.mkdir(parents=True, exist_ok=True)
        if not is_object:
            out["SaveName"] = (data.get("SaveName") or src.stem) + " (GitHub)"
        dest = dest_dir / (src.stem + ".json" if is_object else out["SaveName"] + ".json")
        dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        thumb = src.with_suffix(".png")
        if thumb.exists():
            (dest.with_suffix(".png")).write_bytes(thumb.read_bytes())
        note = f"  ({len(unmapped)} links left as they were: {sorted(unmapped)[:3]})" if unmapped else ""
        print(f"wrote {dest.relative_to(TTS)}{note}")


if __name__ == "__main__":
    main(sys.argv[1:])
