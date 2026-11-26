"""Katha ki tasveer ka backup: sirf tab jab Cloudflare fail ho. Kabhi exception nahi; na bane to False."""
import io, os, time, urllib.parse
import requests
from PIL import Image

SAFE = ", family friendly devotional art, fully clothed, correct human hands with five fingers, no text, no watermark"
_OFF = set()                       # is run mein jis raaste ne saaf mana kiya, dobara nahi
BUDGET = 12 * 60                   # sab backup milakar itne second se zyada nahi (job 30 minute ki hai)
_spent = [0.0]
POLL_GAP = 47                      # Pollinations bina chaabi: 45 second mein 1 tasveer
_last = [0.0]


def _save(raw, fn):
    im = Image.open(io.BytesIO(raw)); im.load()
    if min(im.size) < 500:
        raise ValueError(f"tasveer chhoti {im.size}")
    im.convert("RGB").save(fn, "JPEG", quality=92)


def gemini_image(prompt, fn):
    if "gemini" in _OFF or not os.environ.get("GEMINI_API_KEY", "").strip():
        return False
    try:
        from google import genai
        from google.genai import types
        c = genai.Client(api_key=os.environ["GEMINI_API_KEY"].strip(), http_options=types.HttpOptions(timeout=60000))
        names = [m.name.split("/")[-1] for m in c.models.list()]
        names = sorted((n for n in names if "image" in n and "gemini" in n), key=lambda n: ("pro" in n, n))[:3]
        for n in names:
            try:
                res = c.models.generate_content(model=n, contents=prompt + SAFE + ", square 1:1",
                                                config=types.GenerateContentConfig(response_modalities=["IMAGE"]))
                for part in res.candidates[0].content.parts:
                    if getattr(part, "inline_data", None) and part.inline_data.data:
                        _save(part.inline_data.data, fn)
                        print("Tasveer backup: Gemini", n)
                        return True
            except Exception as e:
                print(f"Gemini image {n}: {str(e)[:150]}")
    except Exception as e:
        print("Gemini image:", str(e)[:150])
    _OFF.add("gemini")
    return False


def pollinations(prompt, fn, seed=7):
    if "pollinations" in _OFF:
        return False
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote((prompt[:900] + SAFE), safe="") +
           f"?width=1024&height=1024&model=flux&nologo=true&safe=true&private=true&seed={seed}")
    for att in range(3):
        time.sleep(max(0, _last[0] + POLL_GAP - time.time()))
        _last[0] = time.time()
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
                _save(r.content, fn)
                print("Tasveer backup: Pollinations")
                return True
            print(f"Pollinations error ({r.status_code}): {r.text[:150]}")
            if r.status_code in (401, 402, 403):
                break
        except Exception as e:
            print("Pollinations:", str(e)[:150])
    _OFF.add("pollinations")
    return False


def backup_image(prompt, fn):
    for route in (gemini_image, pollinations):
        if _spent[0] > BUDGET:
            return False
        t = time.time()
        ok = route(prompt, fn)
        _spent[0] += time.time() - t
        if ok:
            return True
    return False
