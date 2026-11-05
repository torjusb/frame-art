"""Weather icons for the morning picture: Yr's (github.com/metno/weathericons, MIT, © Yr), made for met.no's forecast,
which is what Home Assistant's weather.forecast_home has. They're in weathericons/ as 512 px PNGs, made from the SVGs
by scripts/weathericons.py.
"""
import functools
import os

from PIL import Image

DIR = os.path.join(os.path.dirname(__file__), "weathericons")

# Home Assistant's conditions -> Yr's symbols: (day, night). Home Assistant keeps less than met.no's own symbol, so
# it's the middle one of each kind: rain, not light rain or showers. There's no thunder without rain, nor hail.
SYMBOLS = {
    "sunny": ("clearsky_day", "clearsky_night"),
    "clear-night": ("clearsky_night", "clearsky_night"),
    "partlycloudy": ("partlycloudy_day", "partlycloudy_night"),
    "cloudy": ("cloudy", "cloudy"),
    "fog": ("fog", "fog"),
    "rainy": ("rain", "rain"),
    "pouring": ("heavyrain", "heavyrain"),
    "snowy": ("snow", "snow"),
    "snowy-rainy": ("sleet", "sleet"),
    "hail": ("heavysleet", "heavysleet"),
    "lightning": ("lightrainandthunder", "lightrainandthunder"),
    "lightning-rainy": ("rainandthunder", "rainandthunder"),
    "windy": ("cloudy", "cloudy"),
    "windy-variant": ("partlycloudy_day", "partlycloudy_night"),
    "exceptional": ("cloudy", "cloudy"),
}


@functools.lru_cache(maxsize=64)
def icon(condition, size, night=False):
    """An RGBA picture, size by size, of Home Assistant's condition ("rainy"); the night's (a moon, not a sun) at
    night. Clouds when the condition isn't known."""
    day_name, night_name = SYMBOLS.get(condition, SYMBOLS["cloudy"])
    with Image.open(os.path.join(DIR, (night_name if night else day_name) + ".png")) as i:
        return i.convert("RGBA").resize((size, size), Image.LANCZOS)


def paste(img, condition, xy, size, night=False):
    """The icon on img with its top left at xy."""
    i = icon(condition, size, night)
    img.paste(i, (round(xy[0]), round(xy[1])), i)
