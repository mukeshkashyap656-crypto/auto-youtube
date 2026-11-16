import asyncio, glob, json, os, random, re, time
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
    ImageClip, TextClip, VideoFileClip, concatenate_audioclips, concatenate_videoclips,
)

ANTON_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf"
FALLBACK_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

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
    return cleaned or "CAR GAMING"

def generate_script():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"].strip())
    themes = [
        "Bugatti Chiron vs Koenigsegg Jesko: Asli Zindagi Mein Kaun Tez Hai?",
        "GTA 6 ki 3 Aisi Supercars Jo Real Life Mein 30 Crore Se Mehengi Hain!",
        "Supra MK4 vs Nissan GTR R35: Kaun Hai Asli JDM King?",
        "99% Gamers Nitro aur Drift Timing Mein Yeh Galti Karte Hain!",
        "Lamborghini Revuelto vs Ferrari SF90: Kaun Hai Asli Track Monster?",
        "Duniya ki 3 Sabse Mehengi Supercars Jo Sirf Racing Games Mein Chala Sakte Ho!",
        "Porsche 911 GT3 RS vs Bugatti: Corners Mein Kaun Jeetega?",
        "F1 Car vs Supercar: 0 se 300 KMPH Race Mein Kaun Jeetega?",
        "GTA 6 Car Physics vs GTA 5: 3 Bade Badlav Jo Sabko Chaunka Denge!",
        "Real Life Car Crash vs Gaming Physics: Kaunsa Zyada Khatarnak Hai?",
    ]
    chosen_theme = random.choice(themes)
    today_str = time.strftime("%d %B %Y")
    prompt = f"""
    Today is {today_str}. Create a super engaging, viral 18-second Indian Supercar & Gaming Facts YouTube Short on: "{chosen_theme}".
    Rules:
    - Do NOT do fake live play-by-play commentary. Deliver mind-blowing facts, comparisons, and pro secrets!
    - Start immediately with a shocking 2-second hook (NO "Hello doston", NO intro).
    - Keep total voiceover 36-44 words in energetic conversational Hindi (Devanagari script).
    - Last segment MUST ask viewers to pick a side or comment their favorite car.
    - "screen_text" and every "caption" MUST be ONLY English/Hinglish ASCII letters (A-Z, 0-9, ?, !), NO Hindi script, NO emojis.
    - Return ONLY valid JSON:
    {{
      "title": "Catchy Hinglish title under 58 chars with #shorts #supercars #cargaming",
      "description": "2 line car gaming description with #cargaming #gta6 #supercars #shorts",
      "tags": ["cargaming", "supercars", "gta6", "bugatti", "shorts"],
      "search_query": "sports car",
      "screen_text": "3 TO 5 WORDS CAPS HOOK",
      "segments": [
        {{"voice": "Hindi fact line 1 (6-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi fact line 2 (6-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi fact line 3 (6-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi fact line 4 (6-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi fact line 5 (6-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi CTA line 6 (5-7 words)", "caption": "COMMENT YOUR PICK"}}
      ]
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
            if data.get("segments"):
                print("Script generated using:", model_name)
                return data
        except Exception as e:
            last_err = e
            print(f"Attempt {attempt + 1} ({model_name}) info: {e}")
            time.sleep(5)
    raise last_err

async def make_voice(text, filename="car_voice.mp3"):
    for voice_name, rate in [("hi-IN-MadhurNeural", "+15%"), ("hi-IN-SwaraNeural", "+15%"), ("hi-IN-MadhurNeural", "+0%")]:
        try:
            await edge_tts.Communicate(text, voice_name, rate=rate).save(filename)
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
        random.shuffle(local_clips)
        print("Using own car clips:", local_clips[:8])
        return local_clips[:8]

    api_key = os.environ["PIXABAY_API_KEY"].strip()
    hits = requests.get("https://pixabay.com/api/videos/", params={"key": api_key, "q": query, "per_page": 6}, timeout=30).json().get("hits", [])
    if not hits:
        hits = requests.get("https://pixabay.com/api/videos/", params={"key": api_key, "q": "sports car", "per_page": 6}, timeout=30).json().get("hits", [])
    if hits:
        videos = random.choice(hits).get("videos", {})
        for quality in ("medium", "small", "large", "tiny"):
            if quality in videos and videos[quality].get("url"):
                with open(filename, "wb") as f:
                    f.write(requests.get(videos[quality]["url"], timeout=60).content)
                return [filename]
    return []

def build_video(data, bg_paths, output_file="car_output.mp4"):
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
            (bgm_candidates if probe.duration >= 8.0 else sfx_candidates).append(af) if probe.duration >= 0.2 else None
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

    opened_clips, segments_v = [], []
    if bg_paths:
        target_cut, current_len, idx = 2.0, 0.0, 0
        while current_len < duration and idx < 30:
            clip = VideoFileClip(bg_paths[idx % len(bg_paths)]).without_audio()
            opened_clips.append(clip)
            if clip.duration <= 0.3:
                idx += 1
                continue
            cut_len = min(target_cut, clip.duration, duration - current_len)
            safe_start = min(3.0, clip.duration * 0.18)
            safe_end = min(clip.duration, max(safe_start + cut_len, clip.duration * 0.65))
            max_start = max(0.0, safe_end - cut_len)
            min_start = min(safe_start, max_start)
            start_t = random.uniform(min_start, max_start) if max_start > min_start else 0.0

            seg = clip.subclipped(start_t, start_t + cut_len)
            bg_fill = seg.resized(height=1920)
            if bg_fill.w < 1080:
                bg_fill = bg_fill.resized(width=1080)
            bg_fill = bg_fill.cropped(x_center=bg_fill.w / 2, y_center=bg_fill.h / 2, width=1080, height=1920)

            if seg.w >= seg.h:
                bg_blur = bg_fill.resized(width=80).resized((1080, 1920))
                dark_veil = ColorClip(size=(1080, 1920), color=(8, 12, 22)).with_opacity(0.62).with_duration(cut_len)
                fg = seg.resized(width=1080)
                fg_y = max(360, (1920 - fg.h) // 2 - 110)
                border = ColorClip(size=(1080, fg.h + 14), color=(220, 38, 38)).with_duration(cut_len).with_position(("center", fg_y - 7))
                comp_seg = CompositeVideoClip([bg_blur, dark_veil, border, fg.with_position(("center", fg_y))], size=(1080, 1920)).with_duration(cut_len)
            else:
                comp_seg = CompositeVideoClip([bg_fill, ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.18).with_duration(cut_len)], size=(1080, 1920)).with_duration(cut_len)
            segments_v.append(comp_seg)
            current_len += cut_len
            idx += 1

    bg = concatenate_videoclips(segments_v).subclipped(0, duration) if segments_v else ColorClip(size=(1080, 1920), color=(15, 23, 42)).with_duration(duration)
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

    final_audio = CompositeAudioClip(audio_tracks) if len(audio_tracks) > 1 else voice
    final = CompositeVideoClip([bg, banner_bg, title_txt, *meme_overlays, *caption_clips]).with_audio(final_audio)
    final.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)

    for a in opened_audio:
        a.close()
    for c in opened_clips:
        c.close()
    final.close()

def upload_video(video_file, data):
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
