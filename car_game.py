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
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)

# 1. AI SE VIRAL CAR GAMING & SUPERCARS SCRIPT LIKHWANA
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
    ]
    chosen_theme = random.choice(themes)

    prompt = f"""
    Create a fast-paced 20-second viral Indian Car Gaming & Supercars YouTube Short on: {chosen_theme}.
    Rules:
    - Start immediately with a shocking 1-line hook (NO "Hello dosto" or intro).
    - End with a short question asking viewers to comment their favorite car.
    - Return ONLY valid JSON with these exact keys:
    - "title": Catchy Hinglish title under 60 chars with #shorts #cargaming #supercars
    - "description": 2 lines car gaming description with #cargame #racing #supercars #shorts
    - "tags": list of 5 short tags like ["cargaming", "supercars", "racing", "shorts", "cars"]
    - "search_query": 2 English words for stock car video (pick from: "sports car", "car racing", "supercar drift", "lamborghini")
    - "voice_text": 3 short, high-energy sentences in natural Hindi (Devanagari script, 35-45 words total)
    - "screen_text": ONLY 3 to 5 words MAX in Hinglish/English ALL CAPS, NO emojis (example: "BUGATTI VS LAMBORGHINI KING?", "99% RACERS YEH GALTI KARTE", "FASTEST CAR SECRET TRICK")
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

# 2. TEZ GAMING STYLE HINDI VOICEOVER
async def make_voice(text, filename="car_voice.mp3"):
    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="+10%")
    await communicate.save(filename)

# 3. BACKGROUND CAR VIDEO
def get_bg_video(query, filename="car_bg.mp4"):
    local_clips = glob.glob("car_clips/*.mp4")
    if local_clips:
        chosen = random.choice(local_clips)
        print("Using own car clip:", chosen)
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
                return filename
    return None

# 4. CLEAN VIDEO EDITING
def build_video(screen_text, bg_path, output_file="car_output.mp4"):
    audio = AudioFileClip("car_voice.mp3")
    duration = audio.duration

    if bg_path:
        bg = VideoFileClip(bg_path).without_audio()
        if bg.duration < duration:
            loops = int(duration // bg.duration) + 1
            bg = concatenate_videoclips([bg] * loops)
        bg = bg.subclipped(0, duration)
        bg = bg.resized(height=1920)
        if bg.w < 1080:
            bg = bg.resized(width=1080)
        bg = bg.cropped(x_center=bg.w / 2, y_center=bg.h / 2, width=1080, height=1920)
    else:
        bg = ColorClip(size=(1080, 1920), color=(15, 23, 42)).with_duration(duration)

    overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.20).with_duration(duration)
    txt = TextClip(
        font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        text=screen_text.upper(),
        font_size=54,
        color="yellow",
        stroke_color="black",
        stroke_width=4,
        method="caption",
        size=(900, None),
    ).with_duration(duration).with_position(("center", 240))

    final = CompositeVideoClip([bg, overlay, txt]).with_audio(audio)
    final.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")
    audio.close()
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
    bg_path = get_bg_video(data["search_query"])
    build_video(data["screen_text"], bg_path)
    upload_video("car_output.mp4", data)
