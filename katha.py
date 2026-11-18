import asyncio, base64, glob, json, math, os, random, re, sys, time
from datetime import datetime, timedelta, timezone
import numpy as np
from PIL import Image
import requests
import edge_tts
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy import (
    AudioFileClip, ColorClip, CompositeAudioClip, CompositeVideoClip,
    ImageClip, TextClip, VideoFileClip, concatenate_audioclips,
    concatenate_videoclips, vfx,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

RESAMPLE_BILINEAR = getattr(Image, "Resampling", Image).BILINEAR
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


def get_today_bhagwan_topic():
    ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
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
    day_label, options = day_topics[ist_now.weekday()]
    return day_label, random.choice(options)


def generate_katha():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"].strip())
    day_label, chosen_topic = get_today_bhagwan_topic()
    print(f"Today's Schedule ({day_label}): {chosen_topic}")
    prompt = f"""
    Today is {day_label}. Create a gripping 19-second Indian Mythological Katha YouTube Short on: "{chosen_topic}".
    Rules:
    - Start immediately with an emotional/curiosity hook (NO "Namaste doston", NO intro).
    - Keep total voiceover 38-45 words in emotional Hindi (Devanagari script).
    - Last segment MUST ask viewers to comment (e.g., "Har Har Mahadev", "Jai Shri Ram", matching today's deity).
    - "screen_text" and every "caption" MUST be ONLY English/Hinglish ASCII letters (A-Z, 0-9, ?, !), NO Hindi script, NO emojis.
    - Keep character appearance IDENTICAL across all 6 "scene_prompts" (repeat exact clothing, skin tone, crown/ornaments).
    - Every scene_prompt MUST include: "cute 2D chibi cartoon illustration, Indian mythological folk art style, warm golden glowing colors, clean dark outlines, expressive cute faces, no text, no watermark".
    - Return ONLY valid JSON:
    {{
      "title": "Catchy title under 58 chars with #shorts #katha #bhakti",
      "description": "2 lines devotional description with #katha #hindikahani #bhakti #shorts",
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
      "scene_prompts": ["Scene 1...", "Scene 2...", "Scene 3...", "Scene 4...", "Scene 5...", "Scene 6..."]
    }}
    """
    models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash"]
    last_err = None
    for attempt in range(4):
        model_name = models_to_try[attempt % len(models_to_try)]
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.strip("`").replace("json", "", 1).strip()
            data = json.loads(text)
            if data.get("segments") and data.get("scene_prompts"):
                print("Script generated using:", model_name)
                return data
        except Exception as e:
            last_err = e
            print(f"Attempt {attempt + 1} ({model_name}) info: {e}")
            time.sleep(5)
    raise last_err


def fetch_pixabay_bg_video(filename="katha_bg_motion.mp4"):
    local_clips = []
    for ext in ("*.mp4", "*.mov", "*.mkv"):
        local_clips.extend(glob.glob(os.path.join("katha_clips", ext)))
    if local_clips:
        return random.choice(local_clips)
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not pixabay_key:
        return None
    queries = ["golden clouds sky", "temple candle diya", "sunrise clouds nature", "golden particles dark"]
    random.shuffle(queries)
    for q in queries:
        try:
            res = requests.get(
                "https://pixabay.com/api/videos/",
                params={"key": pixabay_key, "q": q, "per_page": 8},
                timeout=25,
            ).json()
            hits = res.get("hits", [])
            if hits:
                videos = random.choice(hits).get("videos", {})
                for quality in ("small", "tiny", "medium"):
                    url = videos.get(quality, {}).get("url")
                    if url:
                        print(f"Downloading Pixabay backdrop ({q}, {quality})...")
                        with open(filename, "wb") as f:
                            f.write(requests.get(url, timeout=45).content)
                        return filename
        except Exception as e:
            print(f"Pixabay query '{q}' skipped:", e)
    return None


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
                res = requests.post(url, headers=headers, json={"prompt": scene_prompt, "steps": 4}, timeout=45)
                if res.status_code == 200:
                    img_bytes = (
                        res.content
                        if "image/" in res.headers.get("content-type", "")
                        else base64.b64decode(res.json()["result"]["image"])
                    )
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
        raise RuntimeError("No cartoon images generated from Cloudflare.")
    return img_paths


async def make_voice(text, filename="katha_voice.mp3"):
    for voice_name, rate in [("hi-IN-MadhurNeural", "+8%"), ("hi-IN-SwaraNeural", "+8%"), ("hi-IN-MadhurNeural", "+0%")]:
        try:
            await asyncio.wait_for(
                edge_tts.Communicate(text, voice_name, rate=rate).save(filename),
                timeout=25,
            )
            if os.path.exists(filename) and os.path.getsize(filename) > 1000:
                print(f"Voice generated via Edge-TTS ({voice_name})!")
                return
        except Exception as e:
            print(f"Edge-TTS ({voice_name}) failed: {e}")
            await asyncio.sleep(2)

    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if eleven_key:
        try:
            voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "nPczCjzI2devNBz1zQrb")
            res = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
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
                print("Voice generated via ElevenLabs fallback!")
                return
            print(f"ElevenLabs fallback error ({res.status_code}): {res.text[:150]}")
        except Exception as e:
            print("ElevenLabs fallback exception:", e)

    from gtts import gTTS
    gTTS(text=text, lang="hi").save(filename)
    print("Voice generated via gTTS fallback!")


def make_sparkle_transform(seed=42):
    rng = random.Random(seed)
    r = 5
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    glow_mask = np.maximum(0.0, 1.0 - np.sqrt(xx * xx + yy * yy) / (r + 0.5))[:, :, None]
    spark_rgb = np.array([[[255.0, 210.0, 80.0]]])
    sparks = [(rng.uniform(0, 1060), rng.uniform(0, 1060), rng.uniform(45, 115), rng.uniform(0, 6.28)) for _ in range(22)]

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


def make_scene_clip(img_path, seg_d, mode, sparkle_fn):
    pil_img = Image.open(img_path).convert("RGB").resize((1240, 1240), RESAMPLE_BILINEAR)

    def animate_frame(get_frame, t):
        progress = min(1.0, max(0.0, t / max(seg_d, 0.1)))
        if mode == 0:
            crop_sz = int(1240 - 160 * progress)
            x1 = (1240 - crop_sz) // 2
            y1 = x1
        elif mode == 1:
            crop_sz = 1080
            x1 = int(160 * progress)
            y1 = 80
        elif mode == 2:
            crop_sz = int(1080 + 160 * progress)
            x1 = (1240 - crop_sz) // 2
            y1 = x1
        else:
            crop_sz = 1080
            x1 = int(160 * (1.0 - progress))
            y1 = 80
        cropped = pil_img.crop((x1, y1, x1 + crop_sz, y1 + crop_sz)).resize((1080, 1080), RESAMPLE_BILINEAR)
        return np.array(cropped)

    base = ColorClip(size=(1080, 1080), color=(0, 0, 0)).with_duration(seg_d)
    return base.transform(animate_frame).transform(sparkle_fn)


def build_video(data, img_paths, bg_video_path=None, output_file="katha_output.mp4"):
    print("Building video...")
    font_path = get_font()
    voice = AudioFileClip("katha_voice.mp3").with_volume_scaled(1.25)
    duration = voice.duration
    audio_layers, opened_audio, opened_videos = [voice], [voice], []

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
        bgm_raw = AudioFileClip(random.choice(music_files))
        opened_audio.append(bgm_raw)
        bgm = (
            concatenate_audioclips([bgm_raw] * (int(duration // bgm_raw.duration) + 1))
            if bgm_raw.duration < duration
            else bgm_raw
        )
        audio_layers.append(bgm.subclipped(0, min(duration, bgm.duration)).with_volume_scaled(0.14))

    video_layers = []
    n_scenes = len(img_paths)
    scene_dur = duration / n_scenes
    fade_t = min(0.35, scene_dur * 0.25)

    bg_loaded = False
    if bg_video_path and os.path.exists(bg_video_path):
        try:
            raw_bg = VideoFileClip(bg_video_path).without_audio().resized(height=1920)
            opened_videos.append(raw_bg)
            if raw_bg.w < 1080:
                raw_bg = raw_bg.resized(width=1080)
            raw_bg = raw_bg.cropped(x_center=raw_bg.w / 2, y_center=raw_bg.h / 2, width=1080, height=1920)
            bg_motion = (
                concatenate_videoclips([raw_bg] * (int(duration // max(raw_bg.duration, 0.5)) + 1)).subclipped(0, duration)
                if raw_bg.duration < duration
                else raw_bg.subclipped(0, duration)
            )
            video_layers.append(bg_motion)
            bg_loaded = True
        except Exception as e:
            print("Pixabay bg fallback:", e)

    if not bg_loaded:
        for i, img_path in enumerate(img_paths):
            seg_d = scene_dur + (fade_t if i < n_scenes - 1 else 0.0)
            bg_full = ImageClip(img_path).resized(height=1920)
            bg_full = (
                bg_full.cropped(x_center=bg_full.w / 2, y_center=bg_full.h / 2, width=1080, height=1920)
                .with_duration(seg_d)
                .with_start(i * scene_dur)
            )
            if i > 0:
                bg_full = bg_full.with_effects([vfx.CrossFadeIn(fade_t)])
            video_layers.append(bg_full)

    video_layers.append(ColorClip(size=(1080, 1920), color=(14, 8, 26)).with_opacity(0.55).with_duration(duration))
    video_layers.append(ColorClip(size=(1080, 1104), color=(217, 119, 6)).with_duration(duration).with_position(("center", 348)))
    sparkle_fn = make_sparkle_transform()

    for i, img_path in enumerate(img_paths):
        seg_d = scene_dur + (fade_t if i < n_scenes - 1 else 0.0)
        framed = make_scene_clip(img_path, seg_d, i % 4, sparkle_fn).with_start(i * scene_dur).with_position(("center", 360))
        if i > 0:
            framed = framed.with_effects([vfx.CrossFadeIn(fade_t)])
        video_layers.append(framed)

    video_layers.append(ColorClip(size=(960, 128), color=(180, 83, 9)).with_opacity(0.92).with_duration(duration).with_position(("center", 130)))
    video_layers.append(
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

    seg_list = data["segments"]
    total_chars = max(1, sum(len(s["voice"]) for s in seg_list))
    cur_t = 0.0
    for i, item in enumerate(seg_list):
        seg_dur = (len(item["voice"]) / total_chars) * duration
        video_layers.append(
            TextClip(
                font=font_path,
                text=clean_ascii_caps(item["caption"]),
                font_size=68,
                color="yellow" if i % 2 == 0 else "white",
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
        cur_t += seg_dur

    final_audio = CompositeAudioClip(audio_layers).with_duration(duration)
    final = CompositeVideoClip(video_layers, size=(1080, 1920)).with_duration(duration).with_audio(final_audio)
    final.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)
    for a in opened_audio:
        a.close()
    for v in opened_videos:
        v.close()
    final.close()


def upload_video(video_file, data):
    print("Uploading to YouTube...")
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
               
