import asyncio
import json
import os
import random
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

# 1. AI SE SCRIPT AUR TITLE LIKHWANA (Gemini 2.5 Flash)
def generate_script():
    api_key = os.environ["GEMINI_API_KEY"].strip()
    themes = ["Space & Universe", "Human Body", "Ocean Mysteries", "Science Facts", "World History", "Animal Kingdom"]
    chosen_theme = random.choice(themes)

    prompt = f"""
    Create a short 25-second viral YouTube Shorts fact script on the theme: {chosen_theme}.
    Return ONLY valid JSON with these exact keys:
    - "title": Catchy Hinglish/English title under 60 chars with #shorts #facts
    - "description": 2 lines description with hashtags
    - "tags": list of 5 short tags
    - "search_query": 2 simple English words for stock background video (example: "galaxy stars", "ocean waves")
    - "voice_text": 3 short, exciting sentences in natural Hindi (Devanagari script) for voiceover
    - "screen_text": Short punchy summary in Hinglish/English (max 25 words) to display on screen
    """

    last_err = None
    for use_vertex in (False, True):
        try:
            client = genai.Client(vertexai=True, api_key=api_key) if use_vertex else genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.strip("`").replace("json", "", 1).strip()
            return json.loads(text)
        except Exception as e:
            last_err = e
            print(f"Gemini attempt (vertexai={use_vertex}) info: {e}")
    raise last_err

# 2. FREE AI VOICEOVER BANANA (Edge-TTS Hindi Male Voice)
async def make_voice(text, filename="voice.mp3"):
    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural")
    await communicate.save(filename)

# 3. PIXABAY SE FREE STOCK VIDEO DOWNLOAD KARNA
def download_bg_video(query, filename="bg.mp4"):
    api_key = os.environ["PIXABAY_API_KEY"].strip()
    res = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": query, "per_page": 5},
        timeout=30,
    ).json()
    hits = res.get("hits", [])

    if not hits:
        res = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": api_key, "q": "nature", "per_page": 5},
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
                return True
    return False

# 4. VIDEO EDITING (9:16 Shorts Format)
def build_video(screen_text, has_bg, output_file="output.mp4"):
    audio = AudioFileClip("voice.mp3")
    duration = audio.duration

    if has_bg:
        bg = VideoFileClip("bg.mp4").without_audio()
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

    overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.4).with_duration(duration)
    txt = TextClip(
        font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        text=screen_text,
        font_size=62,
        color="yellow",
        stroke_color="black",
        stroke_width=3,
        method="caption",
        size=(920, None),
    ).with_duration(duration).with_position("center")

    final = CompositeVideoClip([bg, overlay, txt]).with_audio(audio)
    final.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")
    audio.close()
    final.close()

# 5. YOUTUBE PAR AUTO UPLOAD KARNA
def upload_video(video_file, data):
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
            "snippet": {
                "title": data["title"][:95],
                "description": data["description"],
                "tags": data.get("tags", ["shorts", "facts"]),
                "categoryId": "27",
            },
            "status": {
                "privacyStatus": "private",  # Pehla test dekhne ke baad ise "public" kar dein
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
    has_bg = download_bg_video(data["search_query"])
    build_video(data["screen_text"], has_bg)
    upload_video("output.mp4", data)
