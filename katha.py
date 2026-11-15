import asyncio
import base64
from datetime import datetime, timedelta, timezone
import glob
import json
import math
import os
import random
import re
import time
import numpy as np
import requests
import edge_tts
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    concatenate_audioclips,
    vfx,
)

ANTON_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf"
FALLBACK_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def get_font():
    for pattern in ("fonts/*.ttf", "*.ttf"):
        found = glob.glob(pattern)
        if found:
            return found[0]
    tmp_font = "/tmp/Anton-Regular.ttf"
    if os.path.exists(tmp_font):
        return tmp_font
    try:
        r = requests.get(ANTON_FONT_URL, timeout=20)
        if r.ok and len(r.content) > 10000:
            with open(tmp_font, "wb") as f:
                f.write(r.content)
            return tmp_font
    except Exception:
        pass
    return FALLBACK_FONT


def clean_ascii_caps(txt):
    cleaned = re.sub(r"[^\x20-\x7E]", "", str(txt)).strip().upper()
    return cleaned or "BHAKTI KATHA"


# 1. INDIA TIME (IST) KE HISAAB SE DIN KE BHAGWAN KI KATHA
def get_today_bhagwan_topic():
    ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    day_idx = ist_now.weekday()  # 0=Monday ... 6=Sunday

    day_topics = {
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
    day_label, options = day_topics[day_idx]
    return day_label, random.choice(options)


def generate_katha():
    api_key = os.environ["GEMINI_API_KEY"].strip()
    client = genai.Client(api_key=api_key)
    day_label, chosen_topic = get_today_bhagwan_topic()
    print(f"Today's Schedule ({day_label}): {chosen_topic}")

    prompt = f"""
    Today is {day_label}. Create a heart-touching, gripping 19-second Indian Mythological Katha YouTube Short on: "{chosen_topic}".
    Rules:
    - Start immediately with an emotional or curiosity 1-line hook (NO "Namaste dosto", NO intro).
    - Keep total voiceover 38-45 words in emotional Hindi (Devanagari script).
    - Last segment MUST ask viewers to comment (e.g., "Har Har Mahadev", "Jai Shri Ram", "Jai Hanuman", matching today's deity).
    - IMPORTANT: "screen_text" and every "caption" MUST be ONLY English/Hinglish ASCII letters (A-Z, 0-9, ?, !), NO Hindi script, NO emojis.
    - Keep character appearance IDENTICAL across all 6 "scene_prompts" (repeat exact clothing, skin tone, crown/ornaments in every prompt).
    - Every scene_prompt MUST include: "cute 2D chibi cartoon illustration, Indian mythological folk art style, warm golden glowing colors, clean dark outlines, expressive cute faces, no text, no watermark".
    - Return ONLY valid JSON with these exact keys:
    {{
      "title": "Catchy Hindi/Hinglish title under 58 chars with #shorts #katha #bhakti",
      "description": "2 lines devotional story description with #katha #hindikahani #bhakti #shorts",
      "tags": ["katha", "bhakti", "hindikahani", "mythology", "shorts"],
      "screen_text": "3 TO 5 WORDS CAPS HOOK",
      "segments": [
        {{"voice": "Hindi sentence 1 (6-8 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 2 (6-8 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 3 (6-8 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 4 (6-8 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 5 (6-8 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 6 (5-7 words)", "caption": "COMMENT DEITY NAME"}}
      ],
      "scene_prompts": [
        "Detailed scene 1...",
        "Detailed scene 2...",
        "Detailed scene 3...",
        "Detailed scene 4...",
        "Detailed scene 5...",
        "Detailed scene 6..."
      ]
    }}
    """

    last_err = None
    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.strip("`").replace("json", "", 1).strip()
            data = json.loads(text)
            if data.get("segments") and data.get("scene_prompts"):
                return data
        except Exception as e:
            last_err = e
            print(f"Attempt {attempt + 1} info: {e}")
            time.sleep(10)
    raise last_err


# 2. CLOUDFLARE SE 6 FAST CARTOON SCENES BANANA
def make_cartoon_images(scene_prompts):
    cf_account = os.environ["CF_ACCOUNT_ID"].strip()
    cf_token = os.environ["CF_API_TOKEN"].strip()
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    headers = {"Authorization": f"Bearer {cf_token}"}

    img_paths = []
    for i, scene_prompt in enumerate(scene_prompts[:6]):
        filename = f"scene_{i}.jpg"
        saved = False
        for attempt in range(2):
            try:
                res = requests.post(
                    url,
                    headers=headers,
                    json={"prompt": scene_prompt, "steps": 4},
                    timeout=60,
                )
                if res.status_code == 200:
                    ctype = res.headers.get("content-type", "")
                    if "image/" in ctype:
                        img_bytes = res.content
                    else:
                        b64_data = res.json()["result"]["image"]
                        img_bytes = base64.b64decode(b64_data)
                    with open(filename, "wb") as f:
                        f.write(img_bytes)
                    img_paths.append(filename)
                    print(f"Generated cartoon scene {i + 1}")
                    saved = True
                    break
                else:
                    print(f"Cloudflare error ({res.status_code}): {res.text[:200]}")
            except Exception as e:
                print(f"Image attempt {attempt + 1} error: {e}")
            time.sleep(2)
        if not saved and img_paths:
            img_paths.append(img_paths[-1])

    if not img_paths:
        raise RuntimeError("No cartoon images could be generated from Cloudflare.")
    return img_paths


# 3. NATURAL HINDI STORYTELLING VOICEOVER
async def make_voice(text, filename="katha_voice.mp3"):
    use_eleven = os.environ.get("USE_ELEVENLABS_KATHA", "false").lower() == "true"
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "nPczCjzI2devNBz1zQrb")

    if use_eleven and eleven_key:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
            res = requests.post(
                url,
                headers={"xi-api-key": eleven_key, "Content-Type": "application/json"},
                json={
                    "text": text,
                    "model_id": "eleven_flash_v2_5",
                    "voice_settings": {"stability": 0.50, "similarity_boost": 0.75, "speed": 1.05},
                },
                timeout=30,
            )
            if res.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(res.content)
                print("Voice generated via ElevenLabs!")
                return
        except Exception as e:
            print(f"ElevenLabs fallback triggered: {e}")

    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="+8%")
    await communicate.save(filename)
    print("Voice generated via Indian Edge-TTS (+8%)!")


# 4. ANIMATED FLOATING GOLDEN SPARKS FILTER
def make_sparkle_transform(seed=42):
    rng = random.Random(seed)
    r = 5
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    glow_mask = np.maximum(0.0, 1.0 - np.sqrt(xx * xx + yy * yy) / (r + 0.5))
    glow_mask = glow_mask[:, :, None]  # shape (11, 11, 1)
    spark_rgb = np.array([[[255.0, 210.0, 80.0]]])

    sparks = [
        (
            rng.uniform(0, 1060),   # x0
            rng.uniform(0, 1060),   # y0
            rng.uniform(45, 115),   # upward speed
            rng.uniform(0, 6.28),   # phase
        )
        for _ in range(22)
    ]

    def apply_sparks(get_frame, t):
        frame = np.array(get_frame(t), copy=True)
        fh, fw, _ = frame.shape
        if fh <= 2 * r or fw <= 2 * r:
            return frame
        for x0, y0, speed, phase in sparks:
            cy = r + int((y0 - t * speed) % (fh - 2 * r))
            cx = r + int((x0 + math.sin(t * 2.2 + phase) * 20) % (fw - 2 * r))
            twinkle = 0.35 + 0.55 * (0.5 + 0.5 * math.sin(t * 5.0 + phase))
            patch = frame[cy - r:cy + r + 1, cx - r:cx + r + 1].astype(np.float32)
            patch += glow_mask * spark_rgb * twinkle
            frame[cy - r:cy + r + 1, cx - r:cx + r + 1] = np.clip(patch, 0, 255).astype(np.uint8)
        return frame

    return apply_sparks


# 5. MULTI-DIRECTION MOTION + CROSSFADE + GOLDEN SPARKS + CAPTIONS
def build_video(data, img_paths, output_file="katha_output.mp4"):
    font_path = get_font()
    voice = AudioFileClip("katha_voice.mp3").with_volume_scaled(1.25)
    duration = voice.duration

    audio_layers = [voice]
    opened_audio = [voice]

    music_files = []
    for folder in ("katha_music", "music", "sfx"):
        for ext in ("*.mp3", "*.wav", "*.m4a"):
            for fpath in glob.glob(os.path.join(folder, "**", ext), recursive=True):
                try:
                    probe = AudioFileClip(fpath)
                    if probe.duration >= 8.0:
                        music_files.append(fpath)
                    probe.close()
                except Exception:
                    pass

    if music_files:
        chosen_bgm = random.choice(music_files)
        print("Using Katha BGM:", chosen_bgm)
        bgm_raw = AudioFileClip(chosen_bgm)
        opened_audio.append(bgm_raw)
        if bgm_raw.duration < duration:
            loops = int(duration // bgm_raw.duration) + 1
            bgm = concatenate_audioclips([bgm_raw] * loops)
        else:
            bgm = bgm_raw
        bgm = bgm.subclipped(0, min(duration, bgm.duration)).with_volume_scaled(0.14)
        audio_layers.append(bgm)

    video_layers = []
    n_scenes = len(img_paths)
    scene_dur = duration / n_scenes
    fade_t = min(0.35, scene_dur * 0.25)

    for i, img_path in enumerate(img_paths):
        start_t = i * scene_dur
        seg_d = scene_dur + (fade_t if i < n_scenes - 1 else 0.0)
        bg_full = ImageClip(img_path).resized(height=1920)
        bg_full = bg_full.cropped(x_center=bg_full.w / 2, y_center=bg_full.h / 2, width=1080, height=1920)
        bg_layer = bg_full.with_duration(seg_d).with_start(start_t)
        if i > 0:
            bg_layer = bg_layer.with_effects([vfx.CrossFadeIn(fade_t)])
        video_layers.append(bg_layer)

    dark_veil = ColorClip(size=(1080, 1920), color=(14, 8, 26)).with_opacity(0.68).with_duration(duration)
    video_layers.append(dark_veil)

    gold_frame = ColorClip(size=(1080, 1104), color=(217, 119, 6)).with_duration(duration).with_position(("center", 348))
    video_layers.append(gold_frame)

    sparkle_fn = make_sparkle_transform()

    for i, img_path in enumerate(img_paths):
        start_t = i * scene_dur
        seg_d = scene_dur + (fade_t if i < n_scenes - 1 else 0.0)
        base_img = ImageClip(img_path).with_duration(seg_d).resized(width=1240)
        motion_type = i % 4

        if motion_type == 0:
            # Zoom-In
            moving = base_img.resized(lambda t, d=seg_d: 0.88 + 0.12 * (t / max(d, 0.1))).with_position("center")
        elif motion_type == 1:
            # Smooth Pan Left -> Right
            moving = base_img.with_position(lambda t, d=seg_d: (int(-160 * (1.0 - t / max(d, 0.1))), -80))
        elif motion_type == 2:
            # Zoom-Out
            moving = base_img.resized(lambda t, d=seg_d: 1.0 - 0.12 * (t / max(d, 0.1))).with_position("center")
        else:
            # Smooth Pan Right -> Left
            moving = base_img.with_position(lambda t, d=seg_d: (int(-160 * (t / max(d, 0.1))), -80))

        framed = CompositeVideoClip([moving], size=(1080, 1080)).with_duration(seg_d)
        framed = framed.transform(sparkle_fn)
        framed = framed.with_start(start_t).with_position(("center", 360))
        if i > 0:
            framed = framed.with_effects([vfx.CrossFadeIn(fade_t)])
        video_layers.append(framed)

    # Top Saffron Hook Banner
    banner_bg = (
        ColorClip(size=(960, 128), color=(180, 83, 9))
        .with_opacity(0.92)
        .with_duration(duration)
        .with_position(("center", 130))
    )
    video_layers.append(banner_bg)

    title_txt = (
        TextClip(
            font=font_path,
            text=clean_ascii_caps(data["screen_text"]),
            font_size=54,
            color="white",
            stroke_color="black",
            stroke_width=4,
            method="caption",
            size=(900, None),
            margin=(0, 10),
        )
        .with_duration(duration)
        .with_position(("center", 150))
    )
    video_layers.append(title_txt)

    # Synced Captions
    seg_list = data["segments"]
    total_chars = max(1, sum(len(s["voice"]) for s in seg_list))
    cur_t = 0.0

    for i, item in enumerate(seg_list):
        seg_dur = (len(item["voice"]) / total_chars) * duration
        cap_text = clean_ascii_caps(item["caption"])
        cap_color = "yellow" if i % 2 == 0 else "white"

        c_clip = (
            TextClip(
                font=font_path,
                text=cap_text,
                font_size=68,
                color=cap_color,
                stroke_color="black",
                stroke_width=6,
                method="caption",
                size=(920, None),
                margin=(0, 14),
            )
            .with_start(cur_t)
            .with_duration(seg_dur)
            .with_position(("center", 1500))
        )
        video_layers.append(c_clip)
        cur_t += seg_dur

    final_audio = CompositeAudioClip(audio_layers).with_duration(duration)
    final = CompositeVideoClip(video_layers, size=(1080, 1920)).with_duration(duration).with_audio(final_audio)
    final.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)

    for a in opened_audio:
        a.close()
    final.close()


# 6. UPLOAD TO KATHA CHANNEL
def upload_video(video_file, data):
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN_KATHA"].strip(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"].strip(),
        client_secret=os.environ["YT_CLIENT_SECRET"].strip(),
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    creds.refresh(Request())

    youtube = build("youtube", "v3", credentials=creds)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": data["title"][:95],
                "description": data["description"],
                "tags": data.get("tags", ["katha", "bhakti", "shorts"]),
                "categoryId": "24",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True),
    )
    response = request.execute()
    print("SUCCESS! Katha Video Uploaded. ID:", response["id"])


if __name__ == "__main__":
    data = generate_katha()
    print("Generated Title:", data["title"])
    img_paths = make_cartoon_images(data["scene_prompts"])
    full_voice = " ".join(s["voice"] for s in data["segments"])
    asyncio.run(make_voice(full_voice))
    build_video(data, img_paths)
    upload_video("katha_output.mp4", data)
