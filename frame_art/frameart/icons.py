"""Weather icons for the morning picture: thin line drawings in the picture's own ink, made with PIL so there's no icon
font to ship. Each is drawn four times too big on a square and scaled down, for smooth edges on a 4K wall.
"""
import math

from PIL import Image, ImageChops, ImageDraw

SCALE = 4

# Home Assistant's conditions -> what's drawn: (sky, below). sky: sun, moon, cloud, sun_cloud, moon_cloud, fog or
# wind; below the cloud: rain, pour, snow, sleet, hail, bolt, bolt_rain or None
DRAWINGS = {
    "sunny": ("sun", None), "clear-night": ("moon", None), "partlycloudy": ("sun_cloud", None),
    "cloudy": ("cloud", None), "fog": ("fog", None), "rainy": ("cloud", "rain"), "pouring": ("cloud", "pour"),
    "snowy": ("cloud", "snow"), "snowy-rainy": ("cloud", "sleet"), "hail": ("cloud", "hail"),
    "lightning": ("cloud", "bolt"), "lightning-rainy": ("cloud", "bolt_rain"), "windy": ("wind", None),
    "windy-variant": ("cloud_wind", None), "exceptional": ("cloud", None),
}
NIGHT = {"sun": "moon", "sun_cloud": "moon_cloud"}


def icon(condition, size, colour, night=False):
    """An RGBA picture, size by size, of Home Assistant's condition ("rainy"), in colour; the moon for the sun at
    night."""
    sky, below = DRAWINGS.get(condition, ("cloud", None))
    if night:
        sky = NIGHT.get(sky, sky)
    s = size * SCALE
    w = max(2, round(s * 0.055))  # the line
    mask = Image.new("L", (s, s), 0)
    cloud_low = below is not None  # a cloud with something under it sits higher
    if sky in ("sun", "moon"):
        _sun(mask, s, w) if sky == "sun" else _moon(mask, s, w, (0.5, 0.5), 0.3)
    elif sky in ("sun_cloud", "moon_cloud"):
        part = Image.new("L", (s, s), 0)
        if sky == "sun_cloud":
            _sun(part, s, w, centre=(0.38, 0.38), r=0.13, rays=0.085)
        else:
            _moon(part, s, w, (0.36, 0.32), 0.19)
        cloud = _cloud_circles(0.12, 0.26, 0.94)
        part = ImageChops.subtract(part, _shape(s, cloud, grow=w * 1.6))  # a gap round the cloud
        mask = ImageChops.lighter(part, _outline(s, cloud, w))
    elif sky == "fog":
        d = ImageDraw.Draw(mask)
        for i, (a, b) in enumerate(((0.16, 0.84), (0.1, 0.72), (0.24, 0.9), (0.16, 0.66))):
            y = s * (0.3 + i * 0.14)
            _line(d, (s * a, y), (s * b, y), w)
    elif sky == "wind":
        _wind(ImageDraw.Draw(mask), s, w, 0.5)
    else:  # cloud, cloud_wind
        top = -0.22 if sky == "cloud_wind" else -0.1 if cloud_low else 0.02
        cloud = _cloud_circles(top, 0.12, 0.88)
        mask = _outline(s, cloud, w)
        if sky == "cloud_wind":
            _wind(ImageDraw.Draw(mask), s, w, 0.7, short=True)
    if below:
        _below(ImageDraw.Draw(mask), s, w, below)
    mask = mask.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), tuple(colour) + (0,))
    out.putalpha(mask)
    return out


def paste(img, condition, xy, size, colour, night=False):
    """The icon on img with its top left at xy."""
    i = icon(condition, size, colour, night)
    img.paste(i, (round(xy[0]), round(xy[1])), i)


# MARK: - The parts

def _line(d, a, b, w):
    d.line((a, b), fill=255, width=w)
    for x, y in (a, b):  # round ends
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=255)


def _sun(mask, s, w, centre=(0.5, 0.5), r=0.18, rays=0.13):
    d = ImageDraw.Draw(mask)
    cx, cy = centre[0] * s, centre[1] * s
    R = r * s
    d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=255, width=w)
    for n in range(8):
        a = n * math.pi / 4
        start, end = R + w * 2.2, R + w * 2.2 + rays * s
        _line(d, (cx + math.cos(a) * start, cy + math.sin(a) * start),
              (cx + math.cos(a) * end, cy + math.sin(a) * end), w)


def _moon(mask, s, w, centre, r):
    """A crescent: a disc less another, a little up and to the right."""
    cx, cy = centre
    shape = [("disc", cx, cy, r)]
    cut = [("disc", cx + r * 0.55, cy - r * 0.35, r * 0.82)]
    outer = ImageChops.subtract(_shape(s, shape), _shape(s, cut))
    inner = ImageChops.subtract(_shape(s, shape, grow=-w), _shape(s, cut, grow=w))
    mask.paste(ImageChops.lighter(mask, ImageChops.subtract(outer, inner)))


def _cloud_circles(top, left, right):
    """A cloud between left and right (fractions of the square), moved down by top: three bumps on a flat bottom."""
    span = right - left

    def x(f):
        return left + span * f
    bottom = 0.68 + top
    return [("disc", x(0.24), bottom - 0.13, 0.13), ("disc", x(0.55), bottom - 0.2, 0.2),
            ("disc", x(0.8), bottom - 0.12, 0.12), ("box", x(0.24), bottom - 0.13, x(0.8), bottom)]


def _shape(s, parts, grow=0):
    """The filled shape of discs ("disc", cx, cy, r) and boxes ("box", x0, y0, x1, y1) with rounded corners for the
    grown ones; grow (in pixels) makes it bigger, or smaller when it's negative."""
    m = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(m)
    for p in parts:
        if p[0] == "disc":
            _, cx, cy, r = p
            R = r * s + grow
            if R > 0:
                d.ellipse((cx * s - R, cy * s - R, cx * s + R, cy * s + R), fill=255)
        else:
            _, x0, y0, x1, y1 = p
            box = (x0 * s - grow, y0 * s - grow, x1 * s + grow, y1 * s + grow)
            if box[2] > box[0] and box[3] > box[1]:
                d.rounded_rectangle(box, radius=max(0, grow), fill=255)
    return m


def _outline(s, parts, w):
    return ImageChops.subtract(_shape(s, parts, grow=w / 2), _shape(s, parts, grow=-w / 2))


def _wind(d, s, w, y, short=False):
    """Two lines of wind, the upper with a curl at the end."""
    x0 = 0.12 * s
    for i, (length, dy) in enumerate(((0.62, -0.09), (0.46, 0.09))):
        length = length * (0.75 if short else 1)
        yy, end = (y + dy) * s, x0 + length * s
        _line(d, (x0, yy), (end, yy), w)
        r = 0.07 * s
        box = (end - r, yy - 2 * r, end + r, yy) if i == 0 else (end - r, yy, end + r, yy + 2 * r)
        d.arc(box, start=-90, end=90, fill=255, width=w)


def _below(d, s, w, kind):
    """What falls from the cloud, under it."""
    top, xs = 0.62, (0.3, 0.5, 0.7)
    if kind in ("rain", "pour", "bolt_rain", "sleet"):
        n = 4 if kind == "pour" else 3
        spots = [0.25 + i * 0.5 / (n - 1) for i in range(n)]
        for i, x in enumerate(spots):
            if kind == "bolt_rain" and i == 1:
                continue
            if kind == "sleet" and i % 2:
                _flake(d, x * s, (top + 0.12) * s, 0.06 * s, w)
                continue
            length = 0.17 if kind == "pour" else 0.13
            _line(d, (x * s + 0.03 * s, (top + 0.04) * s), (x * s - 0.03 * s, (top + 0.04 + length) * s), w)
    if kind == "snow":
        for i, x in enumerate(xs):
            _flake(d, x * s, (top + 0.1 + (0.06 if i % 2 else 0)) * s, 0.065 * s, w)
    if kind == "hail":
        for i, x in enumerate(xs):
            y, r = (top + 0.1 + (0.07 if i % 2 else 0)) * s, w * 0.9
            d.ellipse((x * s - r, y - r, x * s + r, y + r), fill=255)
    if kind in ("bolt", "bolt_rain"):
        cx = 0.5 * s
        pts = [(cx + 0.02 * s, (top + 0.0) * s), (cx - 0.1 * s, (top + 0.18) * s), (cx + 0.0 * s, (top + 0.18) * s),
               (cx - 0.06 * s, (top + 0.36) * s), (cx + 0.12 * s, (top + 0.12) * s), (cx + 0.02 * s, (top + 0.12) * s),
               (cx + 0.08 * s, (top + 0.0) * s)]
        d.polygon(pts, fill=255)


def _flake(d, x, y, r, w):
    for n in range(3):
        a = n * math.pi / 3 + math.pi / 2
        _line(d, (x - math.cos(a) * r, y - math.sin(a) * r), (x + math.cos(a) * r, y + math.sin(a) * r),
              max(1, round(w * 0.7)))
