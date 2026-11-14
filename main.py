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
    VideoFileClip,
    concatenate_videoclips,
)

# 1. VIRAL NOVEMBER 2026 FREE FIRE SHORTS SCRIPT
def generate_script():
    api_key = os.environ["GEMINI_API_KEY"].strip()
    client = genai.Client(api_key=api_key)
    themes = [
        "Free Fire India vs Free Fire MAX: Which is Better for Low End Phones?",
        "FFWS Global Finals 2026 Shocking Pro Moments & Free Rewards",
        "Upcoming OB56 Update & Advance Server Biggest Secret Changes",
        "How to Claim Free Exclusive Gloo Wall in Ranked Season Goals Fast",
        "Storm Arena & Upcoming Cosmic Fist Event Honest Review",
        "Free Fire India New Parental Control & Playtime Limit Rules Explained",
        "Secret Red Number Headshot Sensitivity & Fire Button Size Trick",
        "99% Players Make This Big Mistake in Clash Squad Rank",
        "MP40 vs M1887 or Best Character Skill Debate (Comment Battle)",
    ]
    chosen_theme = random.choice(themes)

    prompt = f"""
    Create a fast-paced 20-second viral Indian Free Fire YouTube Short on: {chosen_theme}.
    Rules:
    - Start immediately with a shocking 1-line hook (NO "Hello dosto" or intro).
    - End with a short question asking viewers to comment their choice/opinion.
    - Return ONLY valid JSON with these exact keys:
    - "title": Catchy Hinglish title under 60 chars with #shorts #freefireindia
    - "description": 2 lines gaming description with #freefireindia #freefiremax #ffws2026 #ob56update #freefireshorts #shorts
    - "tags": list of 6 short tags like ["freefireindia", "freefiremax", "ffws2026", "freefireshorts", "gaming", "shorts"]
    - "search_query": 2 English words for background video (pick from: "gaming neon", "esports gamer", "cyberpunk dark", "abstract laser")
    - "voice_text": 3 short, punchy sentences in natural spoken Hindi (Devanagari script, 35-45 words total). Use commas and full stops for natural human breathing pauses.
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

# 2. RELIABLE MALE GAMING VOICEOVER (Auto-Retry ke saath)
async def make_voice(text, filename="voice.mp3"):
    clean_text = text.replace('"', '').replace("'", "").strip()
    for attempt in range(4):
        try:
            communicate = edge_tts.Communicate(
                clean_text, 
                "hi-IN-MadhurNeural", 
                rate="+2%"
            )
            await communicate.save(filename)
            if os.path.exists(filename) and os.path.getsize(filename) > 1000:
                print("Voice generated successfully!")
                return
        except Exception as e:
            print(f"Voice attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(5)
    raise Exception("Failed to generate voice after 4 attempts.")

# 3. BACKGROUND VIDEO (Apna clips folder ya Safe Pixabay)
def get_bg_video(query, filename="bg.mp4"):
    # Apne clips folder mein kisi bhi format ki video dhundhega
    local_clips = []
    for ext in ("*.mp4", "*.MP4", "*.mkv", "*.mov", "*.webm"):
        local_clips.extend(glob.glob(f"clips/{ext}"))
        
    if local_clips:
        chosen = random.choice(local_clips)
        print("Using own gameplay clip:", chosen)
        return chosen

    print("No local clips found in 'clips/' folder, trying Pixabay...")
    try:
        api_key = os.environ.get("PIXABAY_API_KEY", "").strip()
        if not api_key:
            print("PIXABAY_API_KEY missing!")
            return None

        res = requests.get(
            "https://pixabay.com",
            params={"key": api_key, "q": query, "per_page": 5},
            timeout=30,
        )
        if res.status_code != 200 or not res.text.strip():
            print("Pixabay returned empty response, trying fallback...")
            return None

        data = res.json()
        hits = data.get("hits", [])

        if not hits:
            res = requests.get(
                "https://pixabay.com",
                params={"key": api_key, "q": "gaming", "per_page": 5},
                timeout=30,
            )
            if res.status_code == 200 and res.text.strip():
                hits = res.json().get("hits", [])

        if hits:
            videos = random.choice(hits).get("videos", {})
            for quality in ("medium", "small", "large", "tiny"):
                if quality in videos and videos[quality].get("url"):
                    mp4_link = videos[quality]["url"]
                    video_data = requests.get(mp4_link, timeout=60).content
                    with open(filename, "wb") as f:
                        f.write(video_data)
                    print("Downloaded Pixabay video successfully!")
                    return filename
    except Exception as e:
        print(f"Pixabay error safely handled: {e}")
        
    return None

# 4. CLEAN VIDEO EDITING (Bina kisi screen text ke)
def build_video(bg_path, output_file="output.mp4"):
    audio = AudioFileClip("voice.mp3")
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

    final = bg.with_audio(audio)
    final.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")
    audio.close()
    final.close()

# 5. YOUTUBE PAR PUBLIC AUTO UPLOAD KARNA
def upload_video(video_file, data):
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"].strip(),
        token_uri="https://googleapis.com",
        client_id=os.environ["YT_CLIENT_ID"].strip(),
        client_secret=os.environ["YT_CLIENT_SECRET"].strip(),
        scopes=["https://googleapis.com"],
    )
    creds.refresh(Request())

    youtube = build("youtube", "v3", credentials=creds)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": data["title"][:95],
                "description": data["description"],
                "tags": data.get("tags", ["freefireindia", "shorts", "gaming"]),
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
    print("SUCCESS! Video Uploaded. ID:", response["id"])

if __name__ == "__main__":
    data = generate_script()
    print("Generated Title:", data["title"])
    asyncio.run(make_voice(data["voice_text"]))
    bg_path = get_bg_video(data["search_query"])
    build_video(bg_path)
    upload_video("output.mp4", data)
    
