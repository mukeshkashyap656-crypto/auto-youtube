import asyncio, glob, io, json, os, random, re, sys, time
import requests
import edge_tts
from PIL import Image
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy import (
    AudioFileClip, ColorClip, CompositeAudioClip, CompositeVideoClip,
    TextClip, VideoFileClip, concatenate_audioclips, concatenate_videoclips,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

HISTORY_FILE = "history_ff.json"
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
    cleaned = re.sub(r"[^\x20-\x7E]", "", str(txt)).strip().upper()
    return cleaned or "FREE FIRE"


def list_files(patterns):
    files = []
    for pat in patterns:
        files.extend(glob.glob(pat))
    return [os.path.basename(p) for p in sorted(set(files))]


def extract_preview_parts(pattern, label, limit=8):
    files = glob.glob(pattern)
    if not files:
        return [], []
    random.shuffle(files)
    names, parts = [], []
    for path in files[:limit]:
        name = os.path.basename(path)
        names.append(name)
        c = None
        try:
            c = VideoFileClip(path)
            t = min(max(0.1, c.duration * 0.5), max(0.1, c.duration - 0.1))
            img = Image.fromarray(c.get_frame(t))
            img.thumbnail((384, 384))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=65)
            parts.append(f"{label} filename: {name}")
            parts.append(types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg"))
        except Exception as e:
            print(f"Preview skip for {name}: {e}")
        finally:
            if c is not None:
                c.close()
    return names, parts


def generate_script():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"].strip())
    ff_topics = [
        "One-Tap Headshot Sensitivity (2GB/4GB/6GB/8GB RAM)",
        "Fire Button Size & DPI Secret for Red Numbers",
        "MP40 vs M1887 vs UMP Close Range King",
        "AWM vs M82B Double Sniper Fast Switch Trick",
        "Woodpecker vs AC80 vs Desert Eagle One-Tap",
        "Best CS Rank Character Skill Combination",
        "BR Rank Solo Push Hidden Survival Strategy",
        "Tatsuya, Orion, Sonia, Alok & Chrono Secret Use",
        "Fast Crouch Gloo Wall & Jump Shot Pro Trick",
        "Old Free Fire (2018-2019) vs New Free Fire Nostalgia",
        "Old Peak & Factory Roof Fights Rare Facts",
        "Free Gun Skin & Pro Gameplay Without Diamonds",
        "99% Players Make This Mistake in 1v4 Clutch",
        "Low End Phone Lag Fix & Ultra Smooth Settings",
        "Free Fire Secret Myth Buster That Shocks Players",
        "Evo Gun vs Normal Skin Real Damage Truth",
    ]
    ff_angles = [
        "Secret Setting That Pros Never Share",
        "Shocking Comparison & Comment Battle",
        "3 Mistakes Ruining Your Rank Push",
        "Rare Fact 99% Players Don't Know",
        "Best Trick After New Update",
    ]
    chosen_topic = f"{random.choice(ff_topics)} — {random.choice(ff_angles)}"
    print("Topic:", chosen_topic)
    past = load_history()

    avail_clips, clip_parts = extract_preview_parts("clips/freefire/*.mp4", "Gameplay Clip", limit=8)
    avail_memes, meme_parts = extract_preview_parts("memes/*.mp4", "Ending Meme", limit=6)
    avail_sfx = list_files(["sfx/*.mp3", "sfx/*.wav"])
    avail_music = list_files(["music/*.mp3", "music/*.wav", "music/*.m4a", "sfx/*.mp3", "sfx/*.wav", "sfx/*.m4a"])

    prompt = f"""
    Today is {time.strftime("%d %B %Y %H:%M")} (Run #{random.randint(1000,9999)}).
    You are a top Indian Free Fire YouTube Shorts creator. Create a super searchable, high-CTR 18-second Hindi Short on: "{chosen_topic}".
    FORBIDDEN (Already uploaded, NEVER repeat or write similar titles): {past}
    Available files:
    - Gameplay clips: {avail_clips if avail_clips else ["NONE"]}
    - Ending memes: {avail_memes if avail_memes else ["NONE"]}
    - Hook SFX: {avail_sfx if avail_sfx else ["NONE"]}
    - Background music: {avail_music if avail_music else ["NONE"]}
    Rules:
    - Start immediately with a shocking 2-second curiosity/search hook (NO "Hello doston", NO intro).
    - Do NOT fake play-by-play commentary; give crisp viral tips, comparisons, or facts!
    - Keep total voiceover 35-44 words in energetic conversational Hindi (Devanagari script).
    - Last segment MUST trigger comments (e.g., "Aapki favourite gun kaunsi hai comment karo!").
    - "title" MUST use searchable Hinglish keywords + max 3 hashtags (#freefire #freefireshorts #shorts).
    - "screen_text" and every "caption" MUST be ONLY English/Hinglish ASCII letters (A-Z, 0-9, ?, !), NO Hindi script, NO emojis.
    - Return ONLY valid JSON:
    {{
      "title": "Searchable Hinglish title under 60 chars #freefire #shorts",
      "description": "2 line SEO description with #freefire #freefireindia #freefireshorts #shorts",
      "tags": ["freefire", "freefireshorts", "freefireindia", "headshot", "shorts"],
      "search_query": "gaming neon",
      "screen_text": "3 TO 5 WORDS CAPS HOOK",
      "segments": [
        {{"voice": "Hindi sentence 1 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 2 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 3 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 4 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 5 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 6 (5-7 words)", "caption": "COMMENT YOUR PICK"}}
      ],
      "chosen_clips": ["1 best matching filename from Gameplay clips"],
      "chosen_meme": "1 exact filename from Ending memes (or empty string)",
      "chosen_sfx": "1 exact filename from Hook SFX (or empty string)",
      "chosen_music": "1 exact filename from Background music (or empty string)"
    }}
    """
    models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash"]
    last_err = None
    for attempt in range(8):
        model_name = models_to_try[attempt % len(models_to_try)]
        try:
            req_contents = [*clip_parts, *meme_parts, prompt] if (attempt < 2 and (clip_parts or meme_parts)) else prompt
            response = client.models.generate_content(
                model=model_name,
                contents=req_contents,
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


async def make_voice(text, filename="voice.mp3"):
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
            voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
            res = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
                headers={"xi-api-key": eleven_key, "Content-Type": "application/json"},
                json={"text": text, "model_id": "eleven_flash_v2_5", "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "speed": 1.15}},
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


def get_bg_clips(data, filename="bg.mp4"):
    all_local = glob.glob("clips/freefire/*.mp4")
    if all_local:
        raw_chosen = data.get("chosen_clips", [])
        if isinstance(raw_chosen, list):
            for name in raw_chosen:
                candidate = os.path.join("clips", "freefire", os.path.basename(str(name)))
                if os.path.isfile(candidate):
                    return [candidate]
        return [random.choice(all_local)]

    api_key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not api_key:
        return []
    query = data.get("search_query", "gaming")
    hits = requests.get("https://pixabay.com/api/videos/", params={"key": api_key, "q": query, "per_page": 5}, timeout=30).json().get("hits", [])
    if not hits:
        hits = requests.get("https://pixabay.com/api/videos/", params={"key": api_key, "q": "gaming", "per_page": 5}, timeout=30).json().get("hits", [])
    if hits:
        videos = random.choice(hits).get("videos", {})
        for quality in ("small", "tiny", "medium", "large"):
            if quality in videos and videos[quality].get("url"):
                print(f"Downloading Pixabay bg ({quality})...")
                with open(filename, "wb") as f:
                    f.write(requests.get(videos[quality]["url"], timeout=45).content)
                return [filename]
    return []


def pick_smart_file(folders, ai_choice, extensions, min_dur=None, max_dur=None):
    all_files = []
    for folder in folders:
        for ext in extensions:
            all_files.extend(glob.glob(os.path.join(folder, f"*{ext}")))
    valid_files = []
    for fpath in all_files:
        if min_dur is None and max_dur is None:
            valid_files.append(fpath)
            continue
        try:
            probe = AudioFileClip(fpath)
            d = probe.duration
            probe.close()
            if (min_dur is None or d >= min_dur) and (max_dur is None or d <= max_dur):
                valid_files.append(fpath)
        except Exception:
            pass
    if not valid_files:
        return None
    if isinstance(ai_choice, str) and ai_choice.strip():
        target_name = os.path.basename(ai_choice.strip())
        for vf in valid_files:
            if os.path.basename(vf) == target_name:
                return vf
    return random.choice(valid_files)


def build_video(data, bg_paths, output_file="output.mp4"):
    print("Building video...")
    font_path = get_gaming_font()
    voice = AudioFileClip("voice.mp3").with_volume_scaled(1.25)
    duration = voice.duration

    meme_path = pick_smart_file(["memes"], data.get("chosen_meme"), [".mp4"])
    sfx_path = pick_smart_file(["sfx"], data.get("chosen_sfx"), [".mp3", ".wav"], max_dur=7.9)
    music_path = pick_smart_file(["music", "sfx"], data.get("chosen_music"), [".mp3", ".wav", ".m4a"], min_dur=8.0)

    meme_raw, meme_dur = None, 0.0
    if meme_path:
        meme_raw = VideoFileClip(meme_path)
        if meme_raw.duration > 0.2:
            meme_dur = min(meme_raw.duration, 2.5)
        else:
            meme_raw.close()
            meme_raw = None

    sfx_raw, sfx_outro_dur = None, 0.0
    if sfx_path:
        sfx_raw = AudioFileClip(sfx_path)
        if sfx_raw.duration <= 0.1:
            sfx_raw.close()
            sfx_raw = None
        elif meme_dur == 0.0:
            sfx_outro_dur = min(sfx_raw.duration, 2.0)

    bg_dur = duration + sfx_outro_dur
    audio_layers, bgm_raw = [voice], None
    if music_path:
        bgm_raw = AudioFileClip(music_path)
        bgm = concatenate_audioclips([bgm_raw] * (int(duration // bgm_raw.duration) + 1)) if bgm_raw.duration < duration else bgm_raw
        audio_layers.append(bgm.subclipped(0, min(duration, bgm.duration)).with_volume_scaled(0.13))
    if sfx_raw:
        if meme_dur > 0.0:
            audio_layers.append(sfx_raw.subclipped(0, min(sfx_raw.duration, 1.2)).with_volume_scaled(0.40).with_start(0))
        elif sfx_outro_dur > 0.0:
            audio_layers.append(sfx_raw.subclipped(0, sfx_outro_dur).with_volume_scaled(0.80).with_start(duration))

    opened_clips = []
    if bg_paths:
        primary = VideoFileClip(bg_paths[0]).without_audio()
        opened_clips.append(primary)
        if primary.duration < bg_dur:
            loops = int(bg_dur // max(primary.duration, 0.5)) + 1
            seg = concatenate_videoclips([primary] * loops).subclipped(0, bg_dur)
        else:
            max_st = max(0.0, primary.duration - bg_dur)
            st = random.uniform(0.0, max_st) if max_st > 0.5 else 0.0
            seg = primary.subclipped(st, st + bg_dur)

        if seg.w >= seg.h:
            bg_small = seg.resized(height=142)
            if bg_small.w < 80:
                bg_small = bg_small.resized(width=80)
            bg_blur = bg_small.cropped(x_center=bg_small.w / 2, y_center=bg_small.h / 2, width=80, height=142).resized((1080, 1920))
            dark_veil = ColorClip(size=(1080, 1920), color=(8, 12, 22)).with_opacity(0.62).with_duration(bg_dur)
            fg = seg.resized(width=1080)
            fg_y = max(360, (1920 - fg.h) // 2 - 110)
            border = ColorClip(size=(1080, fg.h + 14), color=(220, 38, 38)).with_duration(bg_dur).with_position(("center", fg_y - 7))
            bg = CompositeVideoClip([bg_blur, dark_veil, border, fg.with_position(("center", fg_y))], size=(1080, 1920)).with_duration(bg_dur)
        else:
            bg_fill = seg.resized(height=1920)
            if bg_fill.w < 1080:
                bg_fill = bg_fill.resized(width=1080)
            bg_fill = bg_fill.cropped(x_center=bg_fill.w / 2, y_center=bg_fill.h / 2, width=1080, height=1920)
            bg = CompositeVideoClip([bg_fill, ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.18).with_duration(bg_dur)], size=(1080, 1920)).with_duration(bg_dur)
    else:
        bg = ColorClip(size=(1080, 1920), color=(15, 23, 42)).with_duration(bg_dur)

    banner_bg = ColorClip(size=(960, 130), color=(185, 28, 28)).with_opacity(0.92).with_duration(bg_dur).with_position(("center", 145))
    title_txt = TextClip(font=font_path, text=clean_ascii_caps(data["screen_text"]), font_size=56, color="white", stroke_color="black", stroke_width=4, method="caption", size=(900, None), margin=(0, 10)).with_duration(bg_dur).with_position(("center", 165))

    seg_list = data["segments"]
    total_chars = max(1, sum(len(s["voice"]) for s in seg_list))
    caption_clips, cur_t = [], 0.0
    for i, item in enumerate(seg_list):
        seg_dur = (len(item["voice"]) / total_chars) * duration
        caption_clips.append(TextClip(font=font_path, text=clean_ascii_caps(item["caption"]), font_size=74, color="yellow" if i % 2 == 0 else "white", stroke_color="black", stroke_width=6, method="caption", size=(920, None), margin=(0, 14)).with_start(cur_t).with_duration(seg_dur).with_position(("center", 1290)))
        cur_t += seg_dur

    video_layers = [bg, banner_bg, title_txt, *caption_clips]
    if meme_raw and meme_dur > 0.0:
        meme_seg = meme_raw.subclipped(0, meme_dur)
        meme_vid = meme_seg.without_audio().resized(width=1080)
        if meme_vid.h > 1920:
            meme_vid = meme_vid.resized(height=1920)
        video_layers.append(ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_duration(meme_dur).with_start(duration))
        video_layers.append(meme_vid.with_start(duration).with_position("center"))
        if meme_seg.audio is not None:
            audio_layers.append(meme_seg.audio.with_start(duration))

    total_dur = duration + meme_dur + sfx_outro_dur
    final_audio = CompositeAudioClip(audio_layers).with_duration(total_dur)
    final = CompositeVideoClip(video_layers, size=(1080, 1920)).with_duration(total_dur).with_audio(final_audio)
    final.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)

    voice.close()
    if bgm_raw:
        bgm_raw.close()
    if sfx_raw:
        sfx_raw.close()
    if meme_raw:
        meme_raw.close()
    for c in opened_clips:
        c.close()
    final.close()


def upload_video(video_file, data):
    print("Uploading to YouTube...")
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"].strip(),
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
            "snippet": {"title": data["title"][:95], "description": data["description"], "tags": data.get("tags", ["freefire", "shorts", "gaming"]), "categoryId": "20"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True),
    )
    print("SUCCESS! Video Uploaded. ID:", request.execute()["id"])


if __name__ == "__main__":
    data = generate_script()
    print("Generated Title:", data["title"])
    asyncio.run(make_voice(" ".join(s["voice"] for s in data["segments"])))
    bg_paths = get_bg_clips(data)
    build_video(data, bg_paths)
    upload_video("output.mp4", data)
    save_history(data["title"])
