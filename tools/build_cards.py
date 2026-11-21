"""Build card images for items and warrior skills from the spreadsheet (original card design).

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
DESIGN = "1"            # bump to rebuild every card after a design change
W, H, SS = 600, 840, 2  # card size (poker proportions), supersampling
CREAM, INK, MUTED = (247, 241, 228), (38, 32, 26), (120, 108, 94)
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
    """Largest font size (from start down) whose wrapped text fits the box."""
    for size in range(start, smallest - 1, -1):
        f = font(size * SS, names)
        lines = wrap(text, f, width * SS)
        if len(lines) * size * spacing <= height:
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


def draw_face(kind, card):
    s = SS
    col = colour_for(kind, card)
    img = Image.new("RGB", (W * s, H * s), col)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([18 * s, 18 * s, (W - 18) * s, (H - 18) * s], radius=20 * s, fill=CREAM)
    d.rounded_rectangle([18 * s, 18 * s, (W - 18) * s, 176 * s], radius=20 * s, fill=col)
    d.rectangle([18 * s, 150 * s, (W - 18) * s, 176 * s], fill=col)
    # icon badge
    icon = draw_icons.white(draw_icons.render(draw_icons.SHAPES[ICON[kind]], 76 * s, 4))
    img.paste(icon, ((W - 112) * s, 50 * s), icon)
    # name, shrunk to fit the header
    name_font, name_lines, _ = fit_text(card["name"], BOLD, W - 170, 110, 52, 26, spacing=1.1)
    y = 97 * s - len(name_lines) * name_font.size * 0.55
    for line in name_lines:
        d.text((48 * s, y), line, font=name_font, fill=(255, 255, 255), anchor="lm")
        y += name_font.size * 1.1
    # subtitle: kind, class, group
    bits = [LABEL[kind]] + [b for b in (card.get("class"), card.get("group")) if b]
    d.text((48 * s, 208 * s), "  ·  ".join(bits).upper(), font=font(19 * s, SEMI), fill=col, anchor="lm")
    d.line([48 * s, 232 * s, (W - 48) * s, 232 * s], fill=col + (0,), width=2 * s)
    # effect text
    effect = card.get("effect") or ""
    effect = effect[:1].upper() + effect[1:]
    bottom = 740 if card.get("mega") else 790
    body_font, body_lines, size = fit_text(effect, REGULAR, W - 96, bottom - 256, 36, 18)
    y = 256 * s
    for line in body_lines:
        d.text((48 * s, y), line, font=body_font, fill=INK)
        y += size * 1.25 * s
    if card.get("mega"):
        d.rounded_rectangle([40 * s, 752 * s, (W - 40) * s, 800 * s], radius=14 * s, fill=col)
        d.text((W / 2 * s, 776 * s), card["mega"], font=font(21 * s, SEMI), fill=(255, 255, 255), anchor="mm")
    return img.resize((W, H), Image.LANCZOS)


def draw_back(kind):
    s = SS
    col = hex_rgb({"items": "#3E4F86", "skills": "#7A4E1E"}[kind])
    dark = tuple(round(v * 0.72) for v in col)
    img = Image.new("RGB", (W * s, H * s), dark)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([18 * s, 18 * s, (W - 18) * s, (H - 18) * s], radius=20 * s, fill=col)
    d.rounded_rectangle([40 * s, 40 * s, (W - 40) * s, (H - 40) * s], radius=14 * s, outline=(255, 255, 255), width=3 * s)
    for i in range(-H, W, 46):  # faint diagonal stripes
        d.line([(i * s, H * s), ((i + H) * s, 0)], fill=tuple(min(255, v + 10) for v in col), width=10 * s)
    d.rounded_rectangle([40 * s, 40 * s, (W - 40) * s, (H - 40) * s], radius=14 * s, outline=(255, 255, 255), width=3 * s)
    icon = draw_icons.white(draw_icons.render(draw_icons.SHAPES[ICON[kind]], 260 * s, 4))
    img.paste(icon, ((W - 260) // 2 * s, 230 * s), icon)
    d.text((W / 2 * s, 600 * s), LABEL[kind].upper(), font=font(48 * s, BOLD), fill=(255, 255, 255), anchor="mm")
    return img.resize((W, H), Image.LANCZOS)


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
