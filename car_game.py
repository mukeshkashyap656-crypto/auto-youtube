import asyncio, glob, json, os, random, re, sys, time
import requests, edge_tts
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy import (
    AudioFileClip, ColorClip, CompositeAudioClip, CompositeVideoClip,
    ImageClip, TextClip, VideoFileClip, concatenate_audioclips, concatenate_videoclips,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

HISTORY_FILE = "history_car.json"
ANTON_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf"
FALLBACK_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)[-40:]
        except Exception:
            pass
    return []


def save_history(title):
    hist = load_history()
    hist.append(title)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(hist[-60:], f, ensure_ascii=False, indent=2)


def get_gaming_font():
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
    return re.sub(r"[^\x20-\x7E]", "", str(txt)).strip().upper() or "CAR GAMING"


def generate_script():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"].strip())
    cars = [
        "GTA 6 Supercars", "Bugatti Tourbillon", "Koenigsegg Jesko Absolut", "Toyota Supra MK4",
        "Nissan GTR R35", "Lamborghini Revuelto", "Ferrari SF90 XX", "Porsche 911 GT3 RS",
        "Pagani Utopia", "McLaren Senna", "Rimac Nevera", "Hennessey Venom F5",
        "Aston Martin Valkyrie", "BMW M4 Competition", "Dodge Challenger Demon", "Mercedes AMG One",
        "Ford Mustang Dark Horse", "Audi R8 V10", "Bugatti Bolide", "Indian Gamers Supercar Collection",
    ]
    angles = [
        "Top Speed & 0-100 KMPH World Record Shock",
        "1v1 Battle vs Closest Rival (Comment War)",
        "Real Price in Crores & Crazy Service Cost in Lakhs",
        "GTA 6 vs GTA 5 Car Physics & Speed Upgrade",
        "Hidden Engineering Secret 99% Log Nahi Jaante",
        "F1 Car vs Hypercar Race Truth",
        "Exhaust Sound & Turbo Flutter Crazy Facts",
        "Drift Control & Racing Game Pro Secret",
    ]
    c1, c2 = random.sample(cars, 2)
    angle = random.choice(angles)
    print(f"Topic: {c1} vs {c2} | {angle}")
    past = load_history()

    prompt = f"""Today is {time.strftime("%d %B %Y %H:%M")} (Run #{random.randint(1000,9999)}).
You are a top Indian Supercar & Car Gaming YouTube Shorts creator. Create a super searchable, high-CTR 18-second Hindi Short on: "{c1}" (or "{c1} vs {c2}") with angle: "{angle}".
FORBIDDEN (Already uploaded, NEVER repeat or write similar titles): {past}
Rules:
- Do NOT do fake live play-by-play commentary. Deliver mind-blowing facts, Crore prices, comparisons, and gaming secrets!
- Start immediately with a shocking 2-second hook (NO "Hello doston", NO intro).
- Keep total voiceover 36-44 words in energetic conversational Hindi (Devanagari script).
- Use today's simple spoken Hindi (the way people talk now), short natural sentences that flow smoothly, no heavy bookish words.
- Last segment MUST trigger comments ("Aapki dream car kaunsi hai comment karo!").
- "title" MUST use searchable Hinglish keywords + max 3 hashtags (#supercars #cargaming #shorts).
- "screen_text" and every "caption" MUST be ONLY English/Hinglish ASCII letters (A-Z, 0-9, ?, !), NO Hindi script, NO emojis.
- Return ONLY valid JSON:
{{"title":"Searchable Hinglish title under 60 chars #supercars #shorts","description":"2 line SEO description with #cargaming #gta6 #supercars #shorts","tags":["cargaming","supercars","gta6","supra","shorts"],"search_query":"sports car","screen_text":"3 TO 5 WORDS CAPS HOOK","segments":[{{"voice":"Hindi fact line 1 (6-7 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi fact line 2 (6-7 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi fact line 3 (6-7 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi fact line 4 (6-7 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi fact line 5 (6-7 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi CTA line 6 (5-7 words)","caption":"COMMENT YOUR CAR"}}]}}"""

    models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash"]
    last_err = None
    for attempt in range(8):
        model_name = models_to_try[attempt % len(models_to_try)]
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=1.0, top_p=0.95),
            )
            text = re.sub(r"^```json\s*|\s*```$", "", (response.text or "").strip(), flags=re.MULTILINE)
            data = json.loads(text)
            if data.get("segments"):
                print("Script generated using:", model_name)
                return data
        except Exception as e:
            last_err = e
            wait_sec = min(60, 10 * (attempt + 1))
            print(f"Attempt {attempt + 1} ({model_name}) failed: {e}. Retrying in {wait_sec}s...")
            time.sleep(wait_sec)
    print("Gemini nahi chala, GitHub Models sahara try kar rahe hain:", last_err)
    from free_ai import fallback_json
    return fallback_json(prompt, lambda d: bool(d.get("segments")))


async def make_voice(text, filename="car_voice.mp3"):
    for voice_name, rate in [("hi-IN-MadhurNeural", "+15%"), ("hi-IN-SwaraNeural", "+15%"), ("hi-IN-MadhurNeural", "+0%")]:
        try:
            await asyncio.wait_for(edge_tts.Communicate(text, voice_name, rate=rate).save(filename), timeout=25)
            if os.path.exists(filename) and os.path.getsize(filename) > 1000:
                print(f"Voice generated via Edge-TTS ({voice_name})!")
                return
        except Exception as e:
            print(f"Edge-TTS ({voice_name}) failed: {e}")
            await asyncio.sleep(2)

    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if eleven_key:
        try:
            voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
            res = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
                headers={"xi-api-key": eleven_key, "Content-Type": "application/json"},
                json={"text": text, "model_id": "eleven_flash_v2_5", "voice_settings": {"stability": 0.4, "similarity_boost": 0.8, "speed": 1.15}},
                timeout=30,
            )
            if res.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(res.content)
                print("Voice generated via ElevenLabs fallback!")
                return
            print(f"ElevenLabs error ({res.status_code}): {res.text[:150]}")
        except Exception as e:
            print("ElevenLabs fallback error:", e)

    from gtts import gTTS
    gTTS(text=text, lang="hi").save(filename)
    print("Voice generated via gTTS fallback!")


def get_bg_clips(query, filename="car_bg.mp4"):
    local_clips = []
    for folder in ("clips/gta6", "clips/car", "clips"):
        for ext in ("*.mp4", "*.MP4", "*.mov", "*.mkv"):
            local_clips.extend(glob.glob(os.path.join(folder, ext)))
    local_clips = list(dict.fromkeys(local_clips))
    if local_clips:
        return [random.choice(local_clips)]

    api_key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not api_key:
        return []
    try:
        hits = requests.get("https://pixabay.com/api/videos/", params={"key": api_key, "q": query, "per_page": 6}, timeout=25).json().get("hits", [])
        if not hits:
            hits = requests.get("https://pixabay.com/api/videos/", params={"key": api_key, "q": "sports car", "per_page": 6}, timeout=25).json().get("hits", [])
        if hits:
            videos = random.choice(hits).get("videos", {})
            for quality in ("small", "tiny", "medium", "large"):
                if quality in videos and videos[quality].get("url"):
                    print(f"Downloading Pixabay car bg ({quality})...")
                    with open(filename, "wb") as f:
                        f.write(requests.get(videos[quality]["url"], timeout=45).content)
                    return [filename]
    except Exception as e:
        print("Pixabay fallback skipped:", e)
    return []


def build_video(data, bg_paths, output_file="car_output.mp4"):
    print("Building Car video...")
    font_path = get_gaming_font()
    voice = AudioFileClip("car_voice.mp3").with_volume_scaled(1.25)
    duration = voice.duration
    opened_audio, audio_tracks = [voice], [voice]

    all_audio_files = []
    for folder in ("sfx", "music"):
        for ext in ("*.mp3", "*.wav", "*.m4a"):
            all_audio_files.extend(glob.glob(os.path.join(folder, "**", ext), recursive=True))

    bgm_candidates, sfx_candidates = [], []
    for af in all_audio_files:
        try:
            probe = AudioFileClip(af)
            if probe.duration >= 8.0:
                bgm_candidates.append(af)
            elif probe.duration >= 0.2:
                sfx_candidates.append(af)
            probe.close()
        except Exception:
            pass

    if bgm_candidates:
        bgm_raw = AudioFileClip(random.choice(bgm_candidates))
        opened_audio.append(bgm_raw)
        bgm = concatenate_audioclips([bgm_raw] * (int(duration // bgm_raw.duration) + 1)) if bgm_raw.duration < duration else bgm_raw
        audio_tracks.append(bgm.subclipped(0, min(duration, bgm.duration)).with_volume_scaled(0.13))

    if sfx_candidates:
        try:
            hook_sfx = AudioFileClip(random.choice(sfx_candidates))
            opened_audio.append(hook_sfx)
            audio_tracks.append(hook_sfx.subclipped(0, min(1.2, hook_sfx.duration)).with_start(0.0).with_volume_scaled(0.45))
        except Exception:
            pass

    opened_clips = []
    if bg_paths:
        primary = VideoFileClip(bg_paths[0]).without_audio()
        opened_clips.append(primary)
        if primary.duration > 12.0:
            s0 = min(2.0, primary.duration * 0.12)
            s1 = max(s0 + 4.0, primary.duration * 0.78)
            clean_clip = primary.subclipped(s0, min(primary.duration, s1))
        else:
            clean_clip = primary

        if clean_clip.duration < duration:
            seg = concatenate_videoclips([clean_clip] * (int(duration // max(clean_clip.duration, 0.5)) + 1)).subclipped(0, duration)
        else:
            max_st = max(0.0, clean_clip.duration - duration)
            st = random.uniform(0.0, max_st) if max_st > 0.5 else 0.0
            seg = clean_clip.subclipped(st, st + duration)

        if seg.w >= seg.h:
            bg_small = seg.resized(height=142)
            if bg_small.w < 80:
                bg_small = bg_small.resized(width=80)
            bg_blur = bg_small.cropped(x_center=bg_small.w / 2, y_center=bg_small.h / 2, width=80, height=142).resized((1080, 1920))
            dark_veil = ColorClip(size=(1080, 1920), color=(8, 12, 22)).with_opacity(0.62).with_duration(duration)
            fg = seg.resized(width=1080)
            fg_y = max(360, (1920 - fg.h) // 2 - 110)
            border = ColorClip(size=(1080, fg.h + 14), color=(220, 38, 38)).with_duration(duration).with_position(("center", fg_y - 7))
            bg = CompositeVideoClip([bg_blur, dark_veil, border, fg.with_position(("center", fg_y))], size=(1080, 1920)).with_duration(duration)
        else:
            bg_fill = seg.resized(height=1920)
            if bg_fill.w < 1080:
                bg_fill = bg_fill.resized(width=1080)
            bg_fill = bg_fill.cropped(x_center=bg_fill.w / 2, y_center=bg_fill.h / 2, width=1080, height=1920)
            bg = CompositeVideoClip([bg_fill, ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.18).with_duration(duration)], size=(1080, 1920)).with_duration(duration)
    else:
        bg = ColorClip(size=(1080, 1920), color=(15, 23, 42)).with_duration(duration)

    banner_bg = ColorClip(size=(960, 130), color=(185, 28, 28)).with_opacity(0.92).with_duration(duration).with_position(("center", 145))
    title_txt = TextClip(font=font_path, text=clean_ascii_caps(data["screen_text"]), font_size=56, color="white", stroke_color="black", stroke_width=4, method="caption", size=(900, None), margin=(0, 10)).with_duration(duration).with_position(("center", 165))

    seg_list = data["segments"]
    total_chars = max(1, sum(len(s["voice"]) for s in seg_list))
    caption_clips, cur_t = [], 0.0
    for i, item in enumerate(seg_list):
        seg_dur = (len(item["voice"]) / total_chars) * duration
        caption_clips.append(TextClip(font=font_path, text=clean_ascii_caps(item["caption"]), font_size=74, color="yellow" if i % 2 == 0 else "white", stroke_color="black", stroke_width=6, method="caption", size=(920, None), margin=(0, 14)).with_start(cur_t).with_duration(seg_dur).with_position(("center", 1290)))
        cur_t += seg_dur

    meme_overlays, meme_files = [], []
    for ext in ("*.mp4", "*.png", "*.jpg", "*.jpeg"):
        meme_files.extend(glob.glob(os.path.join("memes", "**", ext), recursive=True))
    if meme_files and duration > 2.5:
        chosen_meme = random.choice(meme_files)
        meme_start = max(0.0, duration - 1.4)
        meme_dur = min(1.4, duration - meme_start)
        try:
            if chosen_meme.lower().endswith(".mp4"):
                m_vid = VideoFileClip(chosen_meme)
                opened_clips.append(m_vid)
                m_dur = min(meme_dur, m_vid.duration)
                meme_overlays.append(m_vid.subclipped(0, m_dur).resized(width=340).with_start(meme_start).with_position(("center", 320)))
                if m_vid.audio is not None:
                    audio_tracks.append(m_vid.audio.subclipped(0, m_dur).with_start(meme_start).with_volume_scaled(0.65))
            else:
                meme_overlays.append(ImageClip(chosen_meme).resized(width=340).with_duration(meme_dur).with_start(meme_start).with_position(("center", 320)))
        except Exception as e:
            print("Meme skipped:", e)

    final_audio = (CompositeAudioClip(audio_tracks) if len(audio_tracks) > 1 else voice).with_duration(duration)
    final = CompositeVideoClip([bg, banner_bg, title_txt, *meme_overlays, *caption_clips], size=(1080, 1920)).with_duration(duration).with_audio(final_audio)
    final.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)

    for a in opened_audio:
        a.close()
    for c in opened_clips:
        c.close()
    final.close()


def upload_video(video_file, data):
    print("Uploading Car video to YouTube...")
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN_CAR"].strip(),
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
            "snippet": {"title": data["title"][:95], "description": data["description"], "tags": data.get("tags", ["cargaming", "supercars", "gta6", "shorts"]), "categoryId": "20"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True),
    )
    print("SUCCESS! Car Video Uploaded. ID:", request.execute()["id"])


if __name__ == "__main__":
    data = generate_script()
    print("Generated Title:", data["title"])
    asyncio.run(make_voice(" ".join(s["voice"] for s in data["segments"])))
    bg_paths = get_bg_clips(data.get("search_query", "sports car"))
    build_video(data, bg_paths)
    upload_video("car_output.mp4", data)
    save_history(data["title"])
