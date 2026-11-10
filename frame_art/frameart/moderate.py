"""The content filter: before a picture from the sources goes on the wall, TypeSafe's Jev looks at it (and its title)
and says how likely it is to show gore, violence or extremism. One over the threshold is never drawn again.

Jev is a "System One" model: it answers yes/no questions (Nouls) with a probability, fast and cheaply. Images are in early access with TypeSafe, behind the TypeSafe-Danger-Zone-Images header; see
https://docs.typesafe.ai/images.md. The key is typesafe_api_key in the options; without one there's no filter.

The picture is checked as it will be on the wall (cropped to 16:9), scaled down to Jev's limit of 1568 pixels.
"""
import base64
import json
import logging
import urllib.error
import uuid

from PIL import Image

from . import image, net

log = logging.getLogger(__name__)

API = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
MAX_SIDE = 1568  # Jev's limit for each side
THRESHOLD = 0.5
TIMEOUT = 30

# The yes/no questions, by the name in the log. `picture` and `title` are fields in the state.
QUESTIONS = {
    "gore": "Does `picture` show gore: blood, open wounds, mutilation, severed body parts, dead or decaying bodies, "
            "or a surgical or anatomical dissection?",
    "violence": "Is violence or cruelty the main subject of `picture`: killing, torture, an execution, or a battle "
                "with the dead and wounded in view?",
    "extremism": "Does `picture` show extremist or hate content: Nazi, fascist, white-supremacist or other hate "
                 "symbols (such as the swastika or SS runes) used as political emblems, or propaganda for such "
                 "movements? Use `title` too.",
}


class Verdict:
    def __init__(self, scores, threshold):
        self.scores = scores
        self.flagged = [k for k, v in scores.items() if v >= threshold]

    @property
    def reason(self):
        return ", ".join("%s %.2f" % (k, self.scores[k]) for k in self.flagged)

    def __str__(self):
        return ", ".join("%s %.2f" % kv for kv in self.scores.items())


class Moderator:
    def __init__(self, api_key, threshold=THRESHOLD):
        self.api_key = api_key
        self.threshold = threshold

    @classmethod
    def from_config(cls, cfg):
        """A moderator, or None when there's no key."""
        key = (cfg.get("typesafe_api_key") or "").strip()
        if not key:
            return None
        try:
            threshold = float(cfg.get("content_filter_threshold") or THRESHOLD)
        except (TypeError, ValueError):
            threshold = THRESHOLD
        return cls(key, min(max(threshold, 0.01), 1.0))

    def check(self, img, title):
        """A Verdict for a PIL image as it will be on the wall; raises RuntimeError when Jev can't be asked, so the
        picture is neither shown nor left out for good."""
        small = img.copy()
        small.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        ref = "img-" + uuid.uuid4().hex  # matched as plain text in the request: one that can't occur by accident
        body = {
            "model": MODEL,
            "state": {"picture": ref, "title": title or ""},
            "assets": {ref: {"type": "image", "format": "jpg",
                             "data_base64": base64.b64encode(image.to_jpeg(small.convert("RGB"), 85)).decode()}},
            "questions": {k: {"type": "noul", "instructions": q} for k, q in QUESTIONS.items()},
        }
        headers = {"Authorization": "Bearer " + self.api_key, "TypeSafe-Danger-Zone-Images": "true"}
        try:
            r = net.post_json(API, body, headers=headers, timeout=TIMEOUT)
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            raise RuntimeError("content filter: HTTP %s from TypeSafe %s" % (e.code, detail)) from None
        except (OSError, ValueError) as e:
            raise RuntimeError("content filter: couldn't ask TypeSafe (%s)" % e) from None
        answers = r.get("answers") or {}
        try:
            scores = {k: float(answers[k]["noul"]) for k in QUESTIONS}
        except (KeyError, TypeError, ValueError):
            raise RuntimeError("content filter: an answer TypeSafe didn't explain: %s" % json.dumps(r)[:300]) from None
        return Verdict(scores, self.threshold)
