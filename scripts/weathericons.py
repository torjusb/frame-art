"""Makes frame_art/frameart/weathericons/ from Yr's weather icons (github.com/metno/weathericons, MIT): the SVGs the
morning picture uses, as 512 px PNGs, so the add-on needs no SVG renderer. Run it again after a new version:

git clone --depth 1 https://github.com/metno/weathericons /tmp/weathericons
pip install pillow resvg-py
python3 scripts/weathericons.py /tmp/weathericons frame_art/frameart/weathericons
"""
import io
import os
import shutil
import sys

import resvg_py
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "frame_art"))
from frameart.icons import SYMBOLS  # noqa: E402

SIZE = 512
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
names = {n for day, night in SYMBOLS.values() for n in (day, night)}
for name in sorted(names):
    png = bytes(resvg_py.svg_to_bytes(svg_path=os.path.join(src, "weather", "svg", name + ".svg"),
                                      width=SIZE, height=SIZE))
    Image.open(io.BytesIO(png)).save(os.path.join(out, name + ".png"), optimize=True)
    print(name)
shutil.copy(os.path.join(src, "LICENSE"), os.path.join(out, "LICENSE"))
