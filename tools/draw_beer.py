"""Draw the 'Beer' figure: a cartoon pint mug of McKenna, a made-up lager (original art). Writes tools/custom/beer.png."""
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

S = 4  # draw at 4x, then shrink for smooth edges
W, H = 600 * S, 640 * S
INK = (62, 36, 18, 255)  # dark brown outline
GLASS, GLASS_SHADE = (228, 236, 216, 255), (198, 210, 186, 255)
BEER, BEER_DEEP, BEER_LIGHT = (250, 196, 30, 255), (232, 150, 20, 255), (255, 228, 110, 255)
FOAM, FOAM_SHADE = (255, 255, 255, 255), (222, 226, 232, 255)
LINE = 6 * S


def P(*xy):
    return [v * S for v in xy]


def font(size, names):
    for n in names:
        for d in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/msttcorefonts"), Path("/Library/Fonts")):
            if (d / n).exists():
                return ImageFont.truetype(str(d / n), size)
    return ImageFont.load_default(size)


def mask(draw_fn):
    m = Image.new("L", (W, H), 0)
    draw_fn(ImageDraw.Draw(m))
    return m


def fill(img, m, colour):
    layer = Image.new("RGBA", (W, H), colour)
    img.paste(layer, (0, 0), m)


def outline_of(m, width):
    """A ring of the given width just inside the edge of mask m."""
    inner = m.filter(ImageFilter.MinFilter(width * 2 + 1))
    return ImageChops.subtract(m, inner)


def main():
    rnd = random.Random(7)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # glass body: slightly tapered, with a thick base
    body = P(120, 190, 400, 190, 388, 560, 132, 560)
    body_m = mask(lambda d: (d.polygon(body, fill=255), d.rounded_rectangle(P(130, 470, 390, 585), radius=28 * S, fill=255)))
    # handle: a rounded loop on the right
    handle_outer = mask(lambda d: d.rounded_rectangle(P(330, 250, 535, 500), radius=60 * S, fill=255))
    handle_inner = mask(lambda d: d.rounded_rectangle(P(395, 305, 482, 445), radius=34 * S, fill=255))
    handle_m = ImageChops.subtract(handle_outer, handle_inner)
    fill(img, handle_m, GLASS)
    fill(img, mask(lambda d: d.rounded_rectangle(P(470, 280, 520, 470), radius=24 * S, fill=255)).point(lambda v: v // 3), GLASS_SHADE)
    img.putalpha(ImageChops.lighter(img.getchannel("A"), handle_m))
    fill(img, body_m, GLASS)

    # beer inside the glass walls
    beer_m = mask(lambda d: (d.polygon(P(142, 200, 378, 200, 368, 520, 152, 520), fill=255),
                             d.rounded_rectangle(P(152, 470, 368, 540), radius=26 * S, fill=255)))
    fill(img, beer_m, BEER)
    deep = mask(lambda d: d.polygon(P(300, 200, 378, 200, 368, 540, 290, 540), fill=255)).filter(ImageFilter.GaussianBlur(24 * S))
    fill(img, ImageChops.multiply(deep, beer_m), BEER_DEEP)
    light = mask(lambda d: d.rounded_rectangle(P(172, 230, 200, 500), radius=14 * S, fill=255)).filter(ImageFilter.GaussianBlur(6 * S))
    fill(img, ImageChops.multiply(light, beer_m), BEER_LIGHT)
    d = ImageDraw.Draw(img)
    for _ in range(46):  # bubbles
        x, y, r = rnd.uniform(160, 360), rnd.uniform(240, 520), rnd.choice((3, 4, 5, 7))
        if beer_m.getpixel((int(x * S), int(y * S))):
            d.ellipse(P(x - r, y - r, x + r, y + r), fill=BEER_LIGHT)
    # glass base and rim shading
    fill(img, ImageChops.multiply(body_m, mask(lambda d: d.rectangle(P(0, 540, 600, 600), fill=255))), GLASS_SHADE)
    d.arc(P(150, 500, 370, 560), 20, 160, fill=INK, width=3 * S)

    # foam: a cloud overflowing the rim, with drips down the front
    blobs = [(130, 190, 46), (175, 160, 52), (230, 140, 58), (290, 138, 56), (345, 155, 52), (392, 188, 44),
             (160, 205, 40), (365, 210, 38), (260, 190, 50)]
    drips = [(146, 200, 176, 310), (226, 205, 254, 272), (310, 205, 340, 336)]
    foam_m = mask(lambda d: ([d.ellipse(P(x - r, y - r, x + r, y + r), fill=255) for x, y, r in blobs],
                             [d.rounded_rectangle(P(x0, y0, x1, y1), radius=9 * S, fill=255) for x0, y0, x1, y1 in drips],
                             [d.ellipse(P(x0 - 3, y1 - 12, x1 + 3, y1 + 6), fill=255) for x0, y0, x1, y1 in drips]))
    fill(img, foam_m, FOAM)
    under = mask(lambda d: d.rectangle(P(0, 196, 600, 340), fill=255)).filter(ImageFilter.GaussianBlur(10 * S))
    fill(img, ImageChops.multiply(under, foam_m), FOAM_SHADE)
    for _ in range(26):  # foam bubbles
        x, y, r = rnd.uniform(110, 410), rnd.uniform(110, 240), rnd.choice((3, 4, 6))
        if foam_m.getpixel((int(x * S), int(y * S))):
            d.ellipse(P(x - r, y - r, x + r, y + r), fill=FOAM_SHADE)
    for x0, y0 in ((190, 150), (285, 120), (330, 185)):  # little curl lines in the foam
        d.arc(P(x0, y0, x0 + 34, y0 + 20), 200, 340, fill=INK, width=3 * S)
        d.arc(P(x0 + 26, y0, x0 + 60, y0 + 20), 200, 340, fill=INK, width=3 * S)

    # the brand, written on the side of the glass
    brand = font(40 * S, ("segoescb.ttf", "BRUSHSCI.TTF", "comicbd.ttf", "arialbd.ttf"))
    d.text(P(262, 410), "McKenna", font=brand, anchor="mm", fill=(255, 250, 235, 255), stroke_width=4 * S, stroke_fill=INK)

    # ink outlines: around the whole shape, and where foam and handle meet the glass
    silhouette = img.getchannel("A").point(lambda v: 255 if v > 0 else 0)
    ink = Image.new("RGBA", (W, H), INK)
    not_foam = ImageChops.invert(foam_m)
    hole_ring = ImageChops.subtract(handle_inner.filter(ImageFilter.MaxFilter(LINE * 2 + 1)), handle_inner)
    for m in (hole_ring, outline_of(foam_m, LINE // 2), ImageChops.multiply(outline_of(body_m, LINE // 2), not_foam)):
        img.paste(ink, (0, 0), ImageChops.multiply(m, silhouette))
    ring = ImageChops.subtract(silhouette.filter(ImageFilter.MaxFilter(LINE * 2 + 1)), silhouette)
    img.paste(ink, (0, 0), ring)
    img.putalpha(ImageChops.lighter(img.getchannel("A"), ring))
    # cut the hole in the handle back out
    img.putalpha(ImageChops.subtract(img.getchannel("A"), handle_inner))

    img = img.rotate(-5, resample=Image.BICUBIC, expand=True)
    out = Path(__file__).resolve().parent / "custom" / "beer.png"
    out.parent.mkdir(exist_ok=True)
    img.resize((img.width // S, img.height // S), Image.LANCZOS).save(out)
    print("wrote", out.relative_to(out.parent.parent.parent))


if __name__ == "__main__":
    main()
