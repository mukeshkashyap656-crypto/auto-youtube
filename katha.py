import asyncio
import base64
import glob
import json
import math
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import edge_tts
import numpy as np
import requests
from google import genai
from google.auth.transport.requests import Request
from google.genai import types
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_audioclips,
    concatenate_videoclips,
    vfx,
)
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

RESAMPLE_BILINEAR = getattr(Image, "Resampling", Image).BILINEAR
ANTON_FONT_URL = "https://githubusercontent.com"
FALLBACK_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def get_font():
    for p in ("fonts/*.ttf", "*.ttf"):
        found = glob.glob(p)
        if found:
            return found[0]
    tmp = "/tmp/Anton-Regular.ttf"
    if os.path.exists(tmp):
        return tmp
    try:
        r = requests.get(ANTON_FONT_URL, timeout=20)
        if r.ok and len(r.content) > 10000:
            with open(tmp, "wb") as f:
                f.write(r.content)
            return tmp
    except Exception:
        pass
    return FALLBACK_FONT


def clean_ascii_caps(txt):
    return re.sub(r"[^\x20-\x7E]", "", str(txt)).strip().upper() or "BHAKTI KATHA"


def get_today_bhagwan_topic():
    ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    topics = {
        0: ("Somwar Special - Bhagwan Shiv", [
            "Samudra Manthan mein Bhagwan Shiv ka vish peena (Neelkanth)",
            "Bhagwan Shiv ki jataon mein Maa Ganga ke samane ki katha",
            "Bholenath ki kripa aur Markandeya Rishi ko amar vardaan",
            "Maa Parvati ki tapashya aur Shiv-Parvati vivah rahasya",
        ]),
        1: ("Mangalwar Special - Hanuman Ji", [
            "Nanhe Hanuman ji ka Surya ko fal samajh kar nigalna",
            "Hanuman ji ka Lanka Dahan aur Shri Ram bhakti",
            "Sanjeevani booti laane ke liye Hanuman ji ka Dronagiri parvat uthana",
            "Kalyug mein Hanuman ji ka aaj bhi dharti par rehna",
        ]),
        2: ("Budhwar Special - Ganesh Ji", [
            "Ganesh ji ne Mata-Pita ki parikrama karke brahmand jeeta",
            "Bhagwan Ganesh ji ke Ekdant banne ki adbhut kahani",
            "Ganesh ji ne bina ruke poori Mahabharat kaise likhi",
            "Kuber ka ghamand aur Bal Ganesh ji ki leela",
        ]),
        3: ("Guruwar Special - Bhagwan Vishnu & Shri Krishna", [
            "Bhakt Prahlad ki bhakti aur Bhagwan Narsingh Avtar",
            "Shri Krishna aur Sudama ki sacchi dosti",
            "Shri Krishna ka Govardhan Parvat chhoti ungli par uthana",
            "Gajendra Moksha: Jab Bhagwan Vishnu nange pair daud pade",
        ]),
        4: ("Shukrawar Special - Maa Durga & Maa Lakshmi", [
            "Maa Durga ka Mahishasura par vijay aur Navdurga shakti",
            "Samudra Manthan se Maa Lakshmi ke prakat hone ki katha",
            "Maa Lakshmi ke 8 swaroop aur ghar mein sukh-shanti ka rahasya",
            "Maa Santoshi aur sacche bhakt ki pariksha",
        ]),
        5: ("Shaniwar Special - Shani Dev & Hanuman Ji", [
            "Shani Dev aur Hanuman ji ki mitrata aur adbhut vachan",
            "Shani Dev kaise bane teeno lokon ke sabse bade Nyayadhish",
            "Raja Dashrath ki stuti aur Shani Dev ka vardaan",
            "Shaniwar ko Pipal ke ped ki puja ka pauranik rahasya",
        ]),
        6: ("Ravivar Special - Shri Ram & Surya Dev", [
            "Shabri ke jhoothe ber aur Shri Ram ka atoot prem",
            "Ram Setu mein choti gilhari ki bhakti aur seva",
            "Jatayu ka Sita Mata ko bachane ke liye mahan balidaan",
            "Surya Dev ke saat ghodon wale rath ka adbhut rahasya",
        ]),
    }
    lbl, opts = topics[ist.weekday()]
    return lbl, random.choice(opts)


def generate_katha():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"].strip())
    day_label, chosen_topic = get_today_bhagwan_topic()
    print(f"Today's Schedule ({day_label}): {chosen_topic}")

    prompt = f"""Today is {day_label}. Create a gripping 19-second Indian Mythological Katha YouTube Short on: "{chosen_topic}".
Rules:
- Start immediately with an emotional/curiosity hook (NO "Namaste doston", NO intro).
- Keep total voiceover 38-45 words in emotional Hindi (Devanagari script).
- Last segment MUST ask viewers to comment (e.g., "Har Har Mahadev", "Jai Shri Ram", matching today's deity).
- "screen_text" and every "caption" MUST be ONLY English/Hinglish ASCII letters (A-Z, 0-9, ?, !), NO Hindi script, NO emojis.
- Keep character appearance IDENTICAL across all 6 "scene_prompts" (repeat exact clothing, skin tone, crown/ornaments).
- Every scene_prompt MUST include: "cute 2D chibi cartoon illustration, Indian mythological folk art style, warm golden glowing colors, clean dark outlines, expressive cute faces, no text, no watermark".
- Return ONLY valid JSON:
{{"title":"Catchy title under 58 chars with #shorts #katha #bhakti","description":"2 lines devotional description with #katha #hindikahani #bhakti #shorts","tags":["katha","bhakti","hindikahani","mythology","shorts"],"screen_text":"3 TO 5 WORDS CAPS HOOK","segments":[{{"voice":"Hindi sentence 1 (6-8 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi sentence 2 (6-8 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi sentence 3 (6-8 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi sentence 4 (6-8 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi sentence 5 (6-8 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi sentence 6 (5-7 words)","caption":"COMMENT DEITY NAME"}}],"scene_prompts":["Scene 1...","Scene 2...","Scene 3...","Scene 4...","Scene 5...","Scene 6..."]}}"""

    models = [
        "gemini-4-hydrogen",
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
        "gemini-4-argon",
    ]
    last_err = None

    for attempt in range(8):
        m = models[attempt % len(models)]
        try:
            res = client.models.generate_content(
                model=m,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            txt = res.text.strip()
            match = re.search(r"\{.*\}", txt, re.DOTALL)
            if match:
                txt = match.group(0)
            data = json.loads(txt)
            if data.get("segments") and data.get("scene_prompts"):
                print("Script generated using:", m)
                return data
        except Exception as e:
            last_err = e
            wait_sec = min(60, 10 * (attempt + 1))
            print(f"Attempt {attempt + 1} ({m}) failed: {e}. Retrying in {wait_sec}s...")
            time.sleep(wait_sec)

    raise last_err


def fetch_pixabay_bg_video(filename="katha_bg_motion.mp4"):
    local = [
        f
        for ext in ("*.mp4", "*.mov", "*.mkv")
        for f in glob.glob(os.path.join("katha_clips", ext))
    ]
    if local:
        return random.choice(local)

    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        return None

    queries = [
        "golden clouds sky",
        "temple candle diya",
        "sunrise clouds nature",
        "golden particles dark",
    ]
    random.shuffle(queries)

    for q in queries:
        try:
            hits = (
                requests.get(
                    "https://pixabay.com",
                    params={"key": key, "q": q, "per_page": 8},
                    timeout=25,
                )
                .json()
                .get("hits", [])
            )
            if hits:
                vids = random.choice(hits).get("videos", {})
                for qual in ("small", "tiny", "medium"):
                    url = vids.get(qual, {}).get("url")
                    if url:
                        print(f"Downloading Pixabay backdrop ({q}, {qual})...")
                        content = requests.get(url, timeout=45).content
                        with open(filename, "wb") as f:
                            f.write(content)
                        return filename
        except Exception as e:
            print(f"Pixabay '{q}' skipped:", e)
    return None


def make_cartoon_images(scene_prompts):
    url = f"https://cloudflare.com{os.environ['CF_ACCOUNT_ID'].strip()}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    headers = {"Authorization": f"Bearer {os.environ['CF_API_TOKEN'].strip()}"}
    paths = []

    for i, sp in enumerate(scene_prompts[:6]):
        fn, saved = f"scene_{i}.jpg", False
        for att in range(3):
            try:
                r = requests.post(
                    url, headers=headers, json={"prompt": sp, "steps": 4}, timeout=60
                )
                if r.status_code == 200:
                    img_b = (
                        r.content
                        if "image/" in r.headers.get("content-type", "")
                        else base64.b64decode(r.json()["result"]["image"])
                    )
                    with open(fn, "wb") as f:
                        f.write(img_b)
                    paths.append(fn)
                    print(f"Generated cartoon scene {i + 1}")
                    saved = True
                    break
                print(f"Cloudflare error ({r.status_code}): {r.text[:200]}")
            except Exception as e:
                print(f"Image attempt {att + 1} error: {e}")
            time.sleep(3 * (att + 1))

        if not saved and paths:
        
