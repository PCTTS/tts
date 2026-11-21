"""Build card images for items and warrior skills from the spreadsheet (original card design: the name only,
landscape, on a frame coloured by kind and class; the effect text goes in the card's hover description).

Usage:  python -I tools/build_cards.py <spreadsheet.xlsx>     (sheets "items" and "warriorSkills")
Writes cards/items/<name>-<hash>.jpg, cards/skills/<name>-<hash>.jpg, the two card backs, and
cards/index.json (kind -> name -> card file + text). The hash comes from the card's content, so a card
whose text changes gets a new file name (TTS caches images by their link) — and unchanged cards keep theirs.
Old card files that the index no longer uses are deleted. Uses every CPU core.
"""
import hashlib, json, os, re, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import draw_icons  # noqa: E402
from build_figures import file_name  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "cards"
DESIGN = "3"            # bump to rebuild every card after a design change (3: landscape, name only, one line)
W, H, SS = 600, 840, 2  # card image size (portrait, as TTS maps it), supersampling
CREAM, INK, MUTED = (247, 241, 228), (38, 32, 26), (120, 108, 94)
ONE_LINE_MIN = 70       # names go on one line across the card unless that would make the text smaller than this
COLOURS = {  # header/frame colour by kind and class (groups override classes)
    "items": {"Consumable": "#2F8F83", "Active": "#4C63B6", "Mega Stone": "#8E44AD", "Berry": "#3E8E41", None: "#7A7A7A"},
    "skills": {"Hero": "#C08A25", "Recovery": "#3A9D5D", "Normal": "#4F6D8F", None: "#7A7A7A"},
}
LABEL = {"items": "Item", "skills": "Warrior skill"}
ICON = {"items": "item", "skills": "skill"}


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def font(size, names):
    for n in names:
        for d in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/msttcorefonts"), Path("/Library/Fonts")):
            if (d / n).exists():
                return ImageFont.truetype(str(d / n), size)
    return ImageFont.load_default(size)


BOLD, REGULAR, SEMI = ("segoeuib.ttf", "arialbd.ttf"), ("segoeui.ttf", "arial.ttf"), ("seguisb.ttf", "arialbd.ttf")


def wrap(text, f, width):
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            trial = (line + " " + word).strip()
            if f.getlength(trial) <= width or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def fit_text(text, names, width, height, start, smallest, spacing=1.25):
    """Largest font size (from start down) whose wrapped text fits the box (no line wider than it)."""
    for size in range(start, smallest - 1, -1):
        f = font(size * SS, names)
        lines = wrap(text, f, width * SS)
        if len(lines) * size * spacing <= height and all(f.getlength(l) <= width * SS for l in lines):
            return f, lines, size
    f = font(smallest * SS, names)
    return f, wrap(text, f, width * SS), smallest


def colour_for(kind, card):
    table = COLOURS[kind]
    group = (card.get("group") or "")
    for g in group.split(","):
        if g.strip() in table:
            return hex_rgb(table[g.strip()])
    return hex_rgb(table.get(card.get("class"), table[None]))


def landscape_to_card(img):
    """Cards lie landscape on the stand slope: the art is drawn landscape, then turned a quarter (counter-
    clockwise) onto the portrait card image, so it reads left-to-right once the card is turned on its side."""
    return img.rotate(90, expand=True)


def draw_face(kind, card):
    """Just the name, big, across the card, on a frame in the kind/class colour."""
    s, w, h = SS, H, W  # landscape: H wide, W tall
    col = colour_for(kind, card)
    img = Image.new("RGB", (w * s, h * s), col)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([22 * s, 22 * s, (w - 22) * s, (h - 22) * s], radius=24 * s, fill=CREAM)
    d.rounded_rectangle([34 * s, 34 * s, (w - 34) * s, (h - 34) * s], radius=18 * s, outline=col, width=4 * s)
    # one line across the card if it can be big enough; otherwise wrap
    name_font, lines, size = fit_text(card["name"], BOLD, w - 120, 150, 150, 40, spacing=1.08)
    if len(lines) > 1 or size < ONE_LINE_MIN:
        name_font, lines, size = fit_text(card["name"], BOLD, w - 120, h - 140, 150, 40, spacing=1.08)
    y = h / 2 * s - (len(lines) - 1) * size * 1.08 * s / 2
    for line in lines:
        d.text((w / 2 * s, y), line, font=name_font, fill=INK, anchor="mm")
        y += size * 1.08 * s
    return landscape_to_card(img.resize((w, h), Image.LANCZOS))


def draw_back(kind):
    s, w, h = SS, H, W
    col = hex_rgb({"items": "#3E4F86", "skills": "#7A4E1E"}[kind])
    img = Image.new("RGB", (w * s, h * s), tuple(round(v * 0.72) for v in col))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([18 * s, 18 * s, (w - 18) * s, (h - 18) * s], radius=20 * s, fill=col)
    for i in range(-h, w, 46):  # faint diagonal stripes
        d.line([(i * s, h * s), ((i + h) * s, 0)], fill=tuple(min(255, v + 10) for v in col), width=10 * s)
    d.rounded_rectangle([40 * s, 40 * s, (w - 40) * s, (h - 40) * s], radius=14 * s, outline=(255, 255, 255), width=3 * s)
    icon = draw_icons.white(draw_icons.render(draw_icons.SHAPES[ICON[kind]], 230 * s, 4))
    img.paste(icon, ((w - 230) // 2 * s, (h - 230) // 2 * s), icon)
    return landscape_to_card(img.resize((w, h), Image.LANCZOS))


def read_sheet(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    cards = {"items": [], "skills": []}
    for r in list(wb["items"].iter_rows(min_row=2, values_only=True)):
        if not r or not r[0]:
            continue
        mega = None
        if r[2] and "Mega Stone" in str(r[2]) and r[6]:
            mega = f"Mega form: {r[6]}" + (f"  ·  lasts {int(r[4])} turns" if isinstance(r[4], (int, float)) else "")
        cards["items"].append({"name": str(r[0]).strip(), "class": r[1], "group": r[2], "effect": str(r[3] or "").strip(), "mega": mega})
    for r in list(wb["warriorSkills"].iter_rows(min_row=2, values_only=True)):
        if r and r[0]:
            cards["skills"].append({"name": str(r[0]).strip(), "class": r[1], "group": r[2], "effect": str(r[3] or "").strip()})
    return cards


def card_path(kind, card):
    h = hashlib.sha1(json.dumps([DESIGN, card], sort_keys=True, default=str).encode()).hexdigest()[:8]
    return f"cards/{kind}/{file_name(card['name'])}-{h}.jpg"


def render_job(job):
    kind, card, rel = job
    path = REPO / rel
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        draw_face(kind, card).save(path, quality=93)
        return 1
    return 0


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cards = read_sheet(argv[0])
    index, jobs = {"backs": {}}, []
    for kind, lst in cards.items():
        index[kind] = {}
        for card in lst:
            rel = card_path(kind, card)
            index[kind][card["name"]] = {"face": rel, "class": card["class"], "group": card["group"], "effect": card["effect"]}
            jobs.append((kind, card, rel))
        back = f"cards/back-{kind}-v{DESIGN}.jpg"
        if not (REPO / back).exists():
            (REPO / back).parent.mkdir(parents=True, exist_ok=True)
            draw_back(kind).save(REPO / back, quality=93)
        index["backs"][kind] = back
    with ProcessPoolExecutor(os.cpu_count()) as pool:
        made = sum(pool.map(render_job, jobs, chunksize=4))
    used = {j[2] for j in jobs}
    stale = [p for kind in cards for p in (OUT / kind).glob("*.jpg") if f"cards/{kind}/{p.name}" not in used]
    for p in stale:
        p.unlink()
    (OUT / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(f"{len(jobs)} cards ({made} new, {len(stale)} removed) + backs + cards/index.json")


if __name__ == "__main__":
    main(sys.argv[1:])
