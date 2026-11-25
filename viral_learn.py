"""Roz video banane se pehle free jagah se viral seekh (MK Gaming = "ff", MK Car Rider = "car").

Kabhi video nahi rokta: har raaste ko try/except mein rakha hai. Sab fail ho toh khaali text deta hai
aur purana random topic chalta hai.

Raaste (ek fail ho toh agla):
 1. YouTube search (agar YOUTUBE_API_KEY ho): is hafte ke sabse zyada chale Hindi/India Shorts.
 2. Apne channel ke asli views (public API): kya chala, kya nahi.
 3. YouTube autocomplete (koi key nahi): log abhi kya search kar rahe hain.
 4. Gemini + Google Search (free): aaj ka trend (GEMINI_API_KEY).
 5. Kuch bhi na mile: "" (purana tareeka).
Sirf dhang seekha jaata hai. Kisi ka video, awaaz ya title copy nahi hota.
"""
import datetime
import json
import os
import re

import requests

CHANNELS = {
    "ff": {
        "niche": "Free Fire India gaming Shorts",
        "seeds": ["free fire", "free fire india", "free fire sensitivity", "free fire headshot",
                  "free fire new update", "free fire cs rank", "free fire lag fix"],
        "handle": "@m.k.gaming-y2w",
    },
    "car": {
        "niche": "car gaming aur supercar Shorts (Hindi)",
        "seeds": ["supercar", "car gaming", "asphalt 9", "car race", "drag race",
                  "thar fortuner", "bugatti", "car stunt"],
        "handle": "@mkcarrider",
    },
}
YT = "https://www.googleapis.com/youtube/v3"
LEARN_FILE = "history_learn_{ch}.json"   # workflow ka "git add history_*.json" ise apne aap save kar deta hai


def _key():
    return (os.environ.get("YOUTUBE_API_KEY") or "").strip()


def _get(url, **kw):
    r = requests.get(url, timeout=25, **kw)
    r.raise_for_status()
    return r.json()


def _duration_sec(iso):
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 9999
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


def _viral_shorts(cfg):
    """Is hafte ke sabse chale chhote videos (title + views)."""
    key = _key()
    if not key:
        return []
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids = []
    for seed in cfg["seeds"][:4]:
        try:
            js = _get(f"{YT}/search", params={"key": key, "part": "snippet", "q": seed, "type": "video",
                                              "videoDuration": "short", "order": "viewCount", "regionCode": "IN",
                                              "relevanceLanguage": "hi", "publishedAfter": since, "maxResults": 10})
            ids += [i["id"]["videoId"] for i in js.get("items", [])]
        except Exception as e:
            print("viral_learn: search chala nahi:", str(e)[:120])
    ids = list(dict.fromkeys(ids))[:40]
    if not ids:
        return []
    out = []
    try:
        js = _get(f"{YT}/videos", params={"key": key, "part": "snippet,statistics,contentDetails", "id": ",".join(ids)})
        for v in js.get("items", []):
            if _duration_sec(v["contentDetails"].get("duration")) > 75:
                continue
            out.append((int(v["statistics"].get("viewCount", 0)), v["snippet"]["title"]))
    except Exception as e:
        print("viral_learn: video detail chala nahi:", str(e)[:120])
    out.sort(reverse=True)
    return out[:8]


def _own_results(cfg):
    """Apne channel ke videos: kaunse chale, kaunse nahi (2 din se purane)."""
    key = _key()
    if not key:
        return [], []
    try:
        ch = _get(f"{YT}/channels", params={"key": key, "part": "contentDetails", "forHandle": cfg["handle"]})
        pl = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        items = _get(f"{YT}/playlistItems", params={"key": key, "part": "contentDetails", "playlistId": pl, "maxResults": 40})["items"]
        ids = [i["contentDetails"]["videoId"] for i in items]
        vids = _get(f"{YT}/videos", params={"key": key, "part": "snippet,statistics", "id": ",".join(ids)})["items"]
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=2)
        rows = []
        for v in vids:
            pub = datetime.datetime.strptime(v["snippet"]["publishedAt"][:19], "%Y-%m-%dT%H:%M:%S")
            if pub < cutoff:
                rows.append((int(v["statistics"].get("viewCount", 0)), v["snippet"]["title"]))
        rows.sort(reverse=True)
        return rows[:4], rows[-3:] if len(rows) > 6 else []
    except Exception as e:
        print("viral_learn: apne channel ka data nahi mila:", str(e)[:120])
        return [], []


def _autocomplete(cfg):
    """YouTube par log abhi kya dhoondh rahe hain (koi key nahi chahiye)."""
    seen = []
    for seed in cfg["seeds"]:
        try:
            r = requests.get("https://suggestqueries.google.com/complete/search", timeout=15,
                             params={"client": "firefox", "ds": "yt", "hl": "hi", "gl": "IN", "q": seed})
            for s in r.json()[1][:6]:
                if s not in seen:
                    seen.append(s)
        except Exception as e:
            print("viral_learn: autocomplete chala nahi:", str(e)[:100])
            break
    return seen[:25]


def _gemini_trends(cfg):
    """Gemini + Google Search (free): aaj India mein is niche mein kya trend kar raha hai."""
    k = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not k:
        return ""
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=k)
        prompt = (f"Aaj ({datetime.date.today():%d %B %Y}) India mein '{cfg['niche']}' mein kaunse 5 topic sabse zyada trend "
                  "ya viral ho rahe hain (naya update, naya event, naya game/car launch, viral challenge)? "
                  "Har topic ek line mein, sirf asli aur abhi ki baat. Koi purani ya banayi hui cheez nahi.")
        for model in ("gemini-2.5-flash", "gemini-3.6-flash"):
            try:
                resp = client.models.generate_content(
                    model=model, contents=prompt,
                    config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
                if (resp.text or "").strip():
                    return resp.text.strip()[:900]
            except Exception as e:
                print(f"viral_learn: gemini {model} search nahi chala:", str(e)[:100])
    except Exception as e:
        print("viral_learn: gemini search nahi chala:", str(e)[:100])
    return ""


def get_brief(channel):
    """Prompt mein jodne layak chhota text. Kuch na mile toh ''."""
    cfg = CHANNELS[channel]
    parts = []
    try:
        viral = _viral_shorts(cfg)
        if viral:
            parts.append("Is hafte ke sabse chale Shorts (sirf dhang seekho, copy mat karo):\n" +
                         "\n".join(f"- {t} ({v} views)" for v, t in viral))
        best, worst = _own_results(cfg)
        if best:
            parts.append("Hamare channel par sabse zyada chale (inka dhang dohrao):\n" +
                         "\n".join(f"- {t} ({v} views)" for v, t in best))
        if worst:
            parts.append("Hamare channel par kam chale (inka dhang mat dohrao):\n" +
                         "\n".join(f"- {t} ({v} views)" for v, t in worst))
        ac = _autocomplete(cfg)
        if ac:
            parts.append("Log YouTube par abhi ye search kar rahe hain: " + " | ".join(ac))
        tr = _gemini_trends(cfg)
        if tr:
            parts.append("Aaj ke trend (Google Search se):\n" + tr)
    except Exception as e:
        print("viral_learn: seekh adhuri rahi:", str(e)[:120])
    brief = "\n\n".join(parts)[:3500]
    try:
        with open(LEARN_FILE.format(ch=channel), "w", encoding="utf-8") as f:
            json.dump({"date": datetime.date.today().isoformat(), "raaste_chale": len(parts), "brief": brief},
                      f, ensure_ascii=False, indent=1)
    except Exception:
        pass
    print(f"viral_learn[{channel}]: {len(parts)} raaste se seekh mili")
    return brief


def prompt_block(channel):
    """Script ke prompt mein lagane wala poora hissa ('' agar kuch na mila)."""
    brief = get_brief(channel)
    if not brief:
        return ""
    return ("TRENDING AUR SEEKH (aaj ke asli signals): agar neeche ka koi trend is channel ke liye fit baithta hai, "
            "toh default topic ki jagah usi trend par Short banao, par apne tareeke se, bilkul original. "
            "Kisi ka title, awaaz ya video copy mat karo. Fit na baithe toh default topic hi rakho.\n"
            f"{brief}\n")
