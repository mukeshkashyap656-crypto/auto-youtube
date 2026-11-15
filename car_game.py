import asyncio
import glob
import json
import os
import random
import time
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
    TextClip,
    VideoFileClip,
    concatenate_audioclips,
    concatenate_videoclips,
)

# 1. VIRAL CAR GAMING & SUPERCARS SCRIPT (15+ Fresh Formats)
def generate_script():
    api_key = os.environ["GEMINI_API_KEY"].strip()
    client = genai.Client(api_key=api_key)
    themes = [
        "Fastest Supercars & Hypercars Speed Secrets in Racing Games",
        "99% Gamers Make This Big Mistake While Drifting & Cornering",
        "Bugatti vs Lamborghini vs Koenigsegg Speed Debate (Comment Battle)",
        "GTA 5 / Forza Horizon / Car Racing Games Secret Pro Tricks",
        "Most Expensive & Rare Supercars Facts That Will Shock You",
        "How Pro Car Racers Win Last-Second Overtakes in Games",
        "Braking Point Secret That Cuts Lap Time by 3 Seconds",
        "Manual Gear vs Automatic Gear: Which Is Actually Faster?",
        "Top 3 Fastest Cars in Asphalt / Forza / Racing Games",
        "Why F1 Cars Corner Faster Than Any Supercar",
        "Nitro & Boost Timing Mistake That Costs You First Place",
        "Supercar Myth vs Fact That Racing Gamers Believe",
        "JDM Cars vs European Hypercars (Comment Battle)",
        "Secret Wet Track & Drift Control Pro Technique",
        "Insane Top Speed Records & Engine Sound Facts",
    ]
    chosen_theme = random.choice(themes)
    today_str = time.strftime("%d %B %Y")

    prompt = f"""
    Today is {today_str}. Create a fresh, fast-paced 20-second viral Indian Car Gaming & Supercars YouTube Short on: {chosen_theme}.
    Rules:
    - Start immediately with a shocking 1-line hook (NO "Hello dosto" or intro).
    - End with a short question asking viewers to comment their favorite car.
    - Return ONLY valid JSON with these exact keys:
    - "title": Catchy Hinglish title under 60 chars with #shorts #cargaming #supercars
    - "description": 2 lines car gaming description with #cargame #racing #supercars #shorts
    - "tags": list of 5 short tags like ["cargaming", "supercars", "racing", "shorts", "cars"]
    - "search_query": 2 English words for stock car video (pick from: "sports car", "car racing", "supercar drift", "lamborghini")
    - "voice_text": 3 to 4 short, high-energy sentences in natural Hindi (Devanagari script, 35-45 words total)
    - "screen_text": ONLY 3 to 5 words MAX in Hinglish/English ALL CAPS, NO emojis (example: "BUGATTI VS LAMBORGHINI KING?", "99% RACERS YEH GALTI KARTE", "FASTEST CAR SECRET TRICK")
    - "captions": list of 4 short punchy Hinglish/English ALL CAPS lines (3 to 4 words each, NO emojis) matching the voiceover order
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
            return json.loads(text)
        except Exception as e:
            last_err = e
            print(f"Attempt {attempt + 1} info: {e}")
            time.sleep(12)
    raise last_err

# 2. TEZ GAMING STYLE HINDI VOICEOVER (ElevenLabs + Edge-TTS Backup)
async def make_voice(text, filename="car_voice.mp3"):
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = "JBFqnCBsd6RMkjVDRZzb"

    if eleven_key:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
            headers = {
                "xi-api-key": eleven_key,
                "Content-Type": "application/json",
            }
            payload = {
                "text": text,
                "model_id": "eleven_flash_v2_5",
                "voice_settings": {
                    "stability": 0.45,
                    "similarity_boost": 0.75,
                    "speed": 1.1,
                },
            }
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(res.content)
                print("Voice generated via ElevenLabs!")
                return
            else:
                print(f"ElevenLabs failed ({res.status_code}): {res.text[:200]} -> Using edge-tts")
        except Exception as e:
            print(f"ElevenLabs error: {e} -> Using edge-tts")

    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="+10%")
    await communicate.save(filename)
    print("Voice generated via Edge-TTS!")

# 3. MULTIPLE CAR CLIPS (Sirf clips/car ya Pixabay)
def get_bg_clips(query, filename="car_bg.mp4"):
    local_clips = glob.glob("clips/car/*.mp4")
    if local_clips:
        random.shuffle(local_clips)
        chosen = local_clips[:4]
        print("Using own car clips:", chosen)
        return chosen

    api_key = os.environ["PIXABAY_API_KEY"].strip()
    res = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": query, "per_page": 6},
        timeout=30,
    ).json()
    hits = res.get("hits", [])

    if not hits:
        res = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": api_key, "q": "sports car", "per_page": 6},
            timeout=30,
        ).json()
        hits = res.get("hits", [])

    if hits:
        videos = random.choice(hits).get("videos", {})
        for quality in ("medium", "small", "large", "tiny"):
            if quality in videos and videos[quality].get("url"):
                mp4_link = videos[quality]["url"]
                video_data = requests.get(mp4_link, timeout=60).content
                with open(filename, "wb") as f:
                    f.write(video_data)
                return [filename]
    return []

# 4. FAST-CUT EDITING + DYNAMIC CAPTIONS + BGM
def build_video(data, bg_paths, output_file="car_output.mp4"):
    voice = AudioFileClip("car_voice.mp3")
    duration = voice.duration

    music_files = glob.glob("music/*.mp3")
    bgm_raw = None
    if music_files:
        bgm_raw = AudioFileClip(random.choice(music_files))
        if bgm_raw.duration < duration:
            loops = int(duration // bgm_raw.duration) + 1
            bgm = concatenate_audioclips([bgm_raw] * loops)
        else:
            bgm = bgm_raw
        bgm = bgm.subclipped(0, min(duration, bgm.duration)).with_volume_scaled(0.12)
        final_audio = CompositeAudioClip([voice, bgm])
    else:
        final_audio = voice

    opened_clips = []
    segments = []
    if bg_paths:
        target_cut = 4.5
        current_len = 0.0
        idx = 0
        while current_len < duration and idx < 20:
            clip = VideoFileClip(bg_paths[idx % len(bg_paths)]).without_audio()
            opened_clips.append(clip)
            if clip.duration <= 0.2:
                idx += 1
                continue
            cut_len = min(target_cut, clip.duration, duration - current_len)
            max_start = max(0.0, clip.duration - cut_len)
            start_t = random.uniform(0.0, max_start) if max_start > 0.5 else 0.0

            seg = clip.subclipped(start_t, start_t + cut_len)
            seg = seg.resized(height=1920)
            if seg.w < 1080:
                seg = seg.resized(width=1080)
            seg = seg.cropped(x_center=seg.w / 2, y_center=seg.h / 2, width=1080, height=1920)
            segments.append(seg)
            current_len += cut_len
            idx += 1

    if segments:
        bg = concatenate_videoclips(segments)
        if bg.duration > duration:
            bg = bg.subclipped(0, duration)
    else:
        bg = ColorClip(size=(1080, 1920), color=(15, 23, 42)).with_duration(duration)

    overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.22).with_duration(duration)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    title_txt = (
        TextClip(
            font=font_path,
            text=data["screen_text"].upper(),
            font_size=48,
            color="yellow",
            stroke_color="black",
            stroke_width=4,
            method="caption",
            size=(920, None),
            margin=(0, 12),
        )
        .with_duration(duration)
        .with_position(("center", 200))
    )

    captions = data.get("captions") or [data["screen_text"]]
    captions = [str(c).strip().upper() for c in captions if str(c).strip()]
    if not captions:
        captions = [data["screen_text"].upper()]

    cap_dur = duration / len(captions)
    caption_clips = []
    for i, cap_text in enumerate(captions):
        c_clip = (
            TextClip(
                font=font_path,
                text=cap_text,
                font_size=56,
                color="white",
                stroke_color="black",
                stroke_width=5,
                method="caption",
                size=(920, None),
                margin=(0, 12),
            )
            .with_start(i * cap_dur)
            .with_duration(cap_dur)
            .with_position(("center", 1220))
        )
        caption_clips.append(c_clip)

    final = CompositeVideoClip([bg, overlay, title_txt, *caption_clips]).with_audio(final_audio)
    final.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")

    voice.close()
    if bgm_raw:
        bgm_raw.close()
    for c in opened_clips:
        c.close()
    final.close()

# 5. CAR GAME CHANNEL PAR PUBLIC AUTO UPLOAD KARNA
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
            "snippet": {
                "title": data["title"][:95],
                "description": data["description"],
                "tags": data.get("tags", ["cargaming", "supercars", "shorts"]),
                "categoryId": "20",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True),
    )
    response = request.execute()
    print("SUCCESS! Car Video Uploaded. ID:", response["id"])

if __name__ == "__main__":
    data = generate_script()
    print("Generated Title:", data["title"])
    asyncio.run(make_voice(data["voice_text"]))
    bg_paths = get_bg_clips(data["search_query"])
    build_video(data, bg_paths)
    upload_video("car_output.mp4", data)
