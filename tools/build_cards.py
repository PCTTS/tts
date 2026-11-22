"""Build card images for items and warrior skills from the spreadsheet (original card design).

Front (design "Y2"): landscape, in the kind's colour (items green, warrior skills red). A darker band on the left
with diagonal stripes and the white icon, a thin white divider, then the name in white (Bahnschrift Bold) over a
hairline triangle grid that fades in toward the right edge. Every card uses the same name size: the largest at
which every name fits in at most two lines. The effect text is not printed; it is the card's hover description.
Back: the kind's colour with stripes and a large icon.

Usage:  python -I tools/build_cards.py <spreadsheet.xlsx> [--prune]   (sheets "items", "warriorSkills", "abilitiesDB")
Writes cards/items/<name>-<hash>.jpg, cards/skills/<name>-<hash>.jpg, the two card backs, and
cards/index.json (kind -> name -> card file + text). The hash covers everything drawn on the card (design,
text, name size), so a card that looks different gets a new file name (TTS caches images by their link) and
unchanged cards keep theirs. Old card files the index no longer uses are kept (saved games may still use them)
unless --prune. Uses every CPU core. Three kinds: items (green), warrior skills (red), Pokemon abilities (blue).
"""
import hashlib, json, math, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fast_data  # noqa: E402
import draw_icons  # noqa: E402
from build_figures import file_name  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "cards"
DESIGN = "6"            # front design version (6 = "Y2" on the thinner card); bump to rebuild every front after a change
BACK_DESIGN = "5"       # back design version (5 = thinner card)
# Cards are thinner than TTS's standard card so three rows (items, warrior skills, abilities) fit on a stand's
# slope: spawned at scale 1.0 across (2.19) and 1.5 along (4.59), a 2.1 : 1 landscape card.
W, H, SS = 400, 840, 2  # card image size (portrait, as TTS maps it), supersampling
LW, LH = H, W           # the design is drawn landscape (840 x 400) and turned onto the portrait card
CORE = {"items": "#2E8B57", "skills": "#B83A30", "abilities": "#3B6FB6"}  # each kind's colour (green, red, blue)
ICON = {"items": "item", "skills": "skill", "abilities": "ability"}
ICON_SIZE = 100
BAND = 200                         # right edge of the icon band (landscape design units)
NAME_X, NAME_W = 232, LW - 290     # where the name sits, and how wide a line may be
TRI_SIZE, TRI_LINE, TRI_TONE = 48, 1.0, 1.10   # triangle grid: side, line width, brightness vs the card colour
FADE_FROM, FADE_TO = 380, 740      # the grid is invisible left of FADE_FROM and full strength right of FADE_TO


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def shade(c, k):
    return tuple(max(0, min(255, round(v * k))) for v in c)


def name_font(size):
    """Bahnschrift Bold (a variable font); Arial Bold elsewhere."""
    path = Path("C:/Windows/Fonts/bahnschrift.ttf")
    if path.exists():
        f = ImageFont.truetype(str(path), size)
        f.set_variation_by_name("Bold")
        return f
    for d in (Path("/usr/share/fonts/truetype/msttcorefonts"), Path("/Library/Fonts")):
        if (d / "arialbd.ttf").exists():
            return ImageFont.truetype(str(d / "arialbd.ttf"), size)
    return ImageFont.load_default(size)


def wrap(text, f, width):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if f.getlength(trial) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def standard_name_size(names):
    """The largest name size (design px) at which every name fits in at most two lines of NAME_W."""
    for size in range(120, 30, -2):
        f = name_font(size * SS)
        if all(len(ls := wrap(n, f, NAME_W * SS)) <= 2 and all(f.getlength(l) <= NAME_W * SS for l in ls) for n in names):
            return size
    return 30


def landscape_to_card(img):
    """Cards lie landscape on the stand slope: the art is drawn landscape, then turned a quarter (counter-
    clockwise) onto the portrait card image, so it reads left-to-right once the card is turned on its side."""
    return img.rotate(90, expand=True)


def P(*v):
    return [x * SS for x in v]


def stripes(size, colour, spacing=46, width=10):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(-LH, LW, spacing):
        d.line(P(i, LH, i + LH, 0), fill=colour, width=width * SS)
    return layer


def triangle_grid(size, colour):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    h = TRI_SIZE * math.sqrt(3) / 2
    for j in range(-1, int(LH / h) + 2):
        for i in range(-1, int(LW / TRI_SIZE) + 3):
            x0, y0 = i * TRI_SIZE + (TRI_SIZE / 2 if j % 2 else 0), j * h
            d.polygon(P(x0, y0 + h, x0 + TRI_SIZE / 2, y0, x0 + TRI_SIZE, y0 + h), outline=colour, width=max(1, round(TRI_LINE * SS)))
    fade = Image.new("L", size, 0)
    ramp = Image.linear_gradient("L").rotate(90, expand=True)          # dark on the left -> light on the right
    fade.paste(ramp.resize(((FADE_TO - FADE_FROM) * SS, size[1])), (FADE_FROM * SS, 0))
    fade.paste(255, (FADE_TO * SS, 0, size[0], size[1]))
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), fade))
    return layer


def overlay(img, mask, layer):
    img.paste(layer.convert("RGB"), (0, 0), ImageChops.multiply(layer.getchannel("A"), mask))


def draw_face(kind, card, size):
    col = hex_rgb(CORE[kind])
    img = Image.new("RGB", (LW * SS, LH * SS), shade(col, 0.6))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(P(18, 18, LW - 18, LH - 18), radius=22 * SS, fill=col)
    body = Image.new("L", img.size, 0)
    ImageDraw.Draw(body).rounded_rectangle(P(18, 18, LW - 18, LH - 18), radius=22 * SS, fill=255)
    band = Image.new("L", img.size, 0)
    ImageDraw.Draw(band).rounded_rectangle(P(18, 18, BAND, LH - 18), radius=22 * SS, fill=255)
    ImageDraw.Draw(band).rectangle(P(BAND - 40, 18, BAND, LH - 18), fill=255)
    main = ImageChops.subtract(body, band)
    img.paste(shade(col, 0.7), (0, 0), band)
    overlay(img, band, stripes(img.size, shade(col, 0.8) + (255,)))
    overlay(img, main, triangle_grid(img.size, shade(col, TRI_TONE) + (255,)))
    d.line(P(BAND, 40, BAND, LH - 40), fill=(255, 255, 255), width=3 * SS)
    icon = draw_icons.white(draw_icons.render(draw_icons.SHAPES[ICON[kind]], ICON_SIZE * SS, 4))
    img.paste(icon, (round((18 + BAND) / 2 - ICON_SIZE / 2) * SS, round((LH - ICON_SIZE) / 2) * SS), icon)
    f = name_font(size * SS)
    lines = wrap(card["name"], f, NAME_W * SS)
    step = size * 1.12 * SS
    y = LH / 2 * SS - (len(lines) - 1) * step / 2
    for line in lines:
        d.text((NAME_X * SS, y), line, font=f, fill=(255, 255, 255), anchor="lm")
        y += step
    return landscape_to_card(img.resize((LW, LH), Image.LANCZOS))


def draw_back(kind):
    s, w, h = SS, LW, LH
    col = hex_rgb(CORE[kind])
    img = Image.new("RGB", (w * s, h * s), shade(col, 0.72))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([18 * s, 18 * s, (w - 18) * s, (h - 18) * s], radius=20 * s, fill=col)
    for i in range(-h, w, 46):  # faint diagonal stripes
        d.line([(i * s, h * s), ((i + h) * s, 0)], fill=tuple(min(255, v + 10) for v in col), width=10 * s)
    d.rounded_rectangle([40 * s, 40 * s, (w - 40) * s, (h - 40) * s], radius=14 * s, outline=(255, 255, 255), width=3 * s)
    big = 200
    icon = draw_icons.white(draw_icons.render(draw_icons.SHAPES[ICON[kind]], big * s, 4))
    img.paste(icon, ((w - big) // 2 * s, (h - big) // 2 * s), icon)
    return landscape_to_card(img.resize((w, h), Image.LANCZOS))


def read_sheet(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    cards = {"items": [], "skills": [], "abilities": []}
    for r in list(wb["items"].iter_rows(min_row=2, values_only=True)):
        if r and r[0]:
            cards["items"].append({"name": str(r[0]).strip(), "class": r[1], "group": r[2], "effect": str(r[3] or "").strip()})
    for r in list(wb["warriorSkills"].iter_rows(min_row=2, values_only=True)):
        if r and r[0]:
            cards["skills"].append({"name": str(r[0]).strip(), "class": r[1], "group": r[2], "effect": str(r[3] or "").strip()})
    for r in list(wb["abilitiesDB"].iter_rows(min_row=2, values_only=True)):
        if r and r[0]:
            effect = r[1] if len(r) > 1 else ""
            cards["abilities"].append({"name": str(r[0]).strip(), "class": None, "group": None, "effect": str(effect or "").strip()})
    return cards


def card_path(kind, card, size):
    drawn = [DESIGN, kind, card["name"], size]   # everything that appears on the front
    h = hashlib.sha1(json.dumps(drawn).encode()).hexdigest()[:8]
    return f"cards/{kind}/{file_name(card['name'])}-{h}.jpg"


def render_job(job):
    kind, card, rel, size = job
    path = REPO / rel
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        draw_face(kind, card, size).save(path, quality=93)
        return 1
    return 0


def main(argv):
    if not argv:
        sys.exit(__doc__)
    cards = read_sheet(argv[0])
    size = standard_name_size([c["name"] for lst in cards.values() for c in lst])
    index, jobs = {"backs": {}}, []
    for kind, lst in cards.items():
        index[kind] = {}
        for card in lst:
            rel = card_path(kind, card, size)
            index[kind][card["name"]] = {"face": rel, "class": card["class"], "group": card["group"], "effect": card["effect"]}
            jobs.append((kind, card, rel, size))
        back = f"cards/back-{kind}-v{BACK_DESIGN}.jpg"
        if not (REPO / back).exists():
            (REPO / back).parent.mkdir(parents=True, exist_ok=True)
            draw_back(kind).save(REPO / back, quality=93)
        index["backs"][kind] = back
    with ProcessPoolExecutor(os.cpu_count()) as pool:
        made = sum(pool.map(render_job, jobs, chunksize=4))
    used = {j[2] for j in jobs}
    stale = [p for kind in cards for p in (OUT / kind).glob("*.jpg") if f"cards/{kind}/{p.name}" not in used]
    if "--prune" in argv:   # only once saved games no longer use them (TTS loads cards by their link)
        for p in stale:
            p.unlink()
    (OUT / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    fast_data.main()   # the plain-text copy the game reads (JSON is far too slow in TTS)
    print(f"{len(jobs)} cards, name size {size}px ({made} new, {len(stale)} old ones {'removed' if '--prune' in argv else 'kept (--prune removes them)'}) + backs + cards/index.json")


if __name__ == "__main__":
    main(sys.argv[1:])
