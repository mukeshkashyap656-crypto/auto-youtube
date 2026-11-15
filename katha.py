import asyncio
import base64
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
    ImageClip,
    TextClip,
    concatenate_audioclips,
)

# 1. AI SE PAURANIK KATHA + CHIBI CARTOON SCENES LIKHWANA
def generate_katha():
    api_key = os.environ["GEMINI_API_KEY"].strip()
    client = genai.Client(api_key=api_key)
    topics = [
        "Shabri ke jhoothe ber aur Shri Ram ka prem",
        "Shri Krishna aur Sudama ki sacchi dosti",
        "Nanhe Hanuman ji ka Surya ko fal samajh kar nigalna",
        "Ram Setu mein choti gilhari ki bhakti aur seva",
        "Ganesh ji ne Mata-Pita ki parikrama karke brahmand jeeta",
        "Shri Krishna ka Govardhan Parvat ungli par uthana",
        "Bhakt Prahlad ki bhakti aur Narsingh Avtar",
        "Arjun ki ekaagrata aur chidiya ki aankh wali kahani",
        "Jatayu ka Sita Mata ko bachane ke liye balidaan",
        "Samudra Manthan mein Bhagwan Shiv ka vish peena (Neelkanth)",
        "Kalyug mein Hanuman ji ka aaj bhi dharti par rehna",
        "Shri Krishna ka Kaliya Naag ke fann par nritya",
        "Panchatantra ki kahani: Chatur khargosh aur sher",
        "Karna ki daanveerta aur Shri Krishna ki pariksha",
        "Mahabharat mein Abhimanyu aur Chakravyuh ka rahasya",
    ]
    chosen_topic = random.choice(topics)
    today_str = time.strftime("%d %B %Y")

    prompt = f"""
    Today is {today_str}. Create a heart-touching, fast-paced 20-second Indian Mythological / Moral Katha YouTube Short on: {chosen_topic}.
    Rules:
    - Start immediately with an emotional or shocking 1-line hook (NO "Namaste dosto" or intro).
    - End with a short devotion/moral question asking viewers to comment (e.g., "Jai Shri Ram" or their opinion).
    - Return ONLY valid JSON with these exact keys:
    - "title": Catchy Hindi/Hinglish title under 60 chars with #shorts #katha #ramayan
    - "description": 2 lines devotional story description with #katha #hindikahani #bhakti #shorts
    - "tags": list of 5 short tags like ["katha", "hindikahani", "ramayan", "krishna", "shorts"]
    - "voice_text": 4 short, emotional storytelling sentences in natural Hindi (Devanagari script, 40-50 words total)
    - "screen_text": ONLY 3 to 5 words MAX in Hinglish/English ALL CAPS, NO emojis (example: "SHABRI AUR RAM KATHA", "HANUMAN JI KA CHAMATKAR", "KRISHNA SUDAMA DOSTI")
    - "captions": list of 5 short punchy Hinglish ALL CAPS lines (3 to 4 words each, NO emojis) matching the story order
    - "scene_prompts": list of 4 detailed English image prompts for cute 2D chibi cartoon scenes matching the story in order. Every prompt MUST include: "cute 2D chibi cartoon illustration, Indian mythological folk art style, warm glowing colors, clean dark outlines, expressive cute faces, no text, no watermark"
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
            time.sleep(10)
    raise last_err

# 2. CLOUDFLARE FREE AI SE CUTE CARTOON SCENES BANANA
def make_cartoon_images(scene_prompts):
    cf_account = os.environ["CF_ACCOUNT_ID"].strip()
    cf_token = os.environ["CF_API_TOKEN"].strip()
    url = f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    headers = {"Authorization": f"Bearer {cf_token}"}

    img_paths = []
    for i, scene_prompt in enumerate(scene_prompts[:4]):
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
            time.sleep(3)
        if not saved and img_paths:
            img_paths.append(img_paths[-1])

    if not img_paths:
        raise RuntimeError("No cartoon images could be generated from Cloudflare.")
    return img_paths

# 3. KAHANI VOICEOVER (ElevenLabs "Brian" Storytelling Voice + Edge-TTS Backup)
async def make_voice(text, filename="katha_voice.mp3"):
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = "nPczCjzI2devNBz1zQrb"  # Brian (Deep storytelling voice)

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
                    "stability": 0.50,
                    "similarity_boost": 0.75,
                    "speed": 1.05,
                },
            }
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(res.content)
                print("Voice generated via ElevenLabs (Brian)!")
                return
            else:
                print(f"ElevenLabs failed ({res.status_code}): {res.text[:200]} -> Using edge-tts")
        except Exception as e:
            print(f"ElevenLabs error: {e} -> Using edge-tts")

    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="+5%")
    await communicate.save(filename)
    print("Voice generated via Edge-TTS!")

# 4. SMOOTH CARTOON ZOOM + DYNAMIC CAPTIONS + OPTIONAL BANSURI MUSIC
def build_video(data, img_paths, output_file="katha_output.mp4"):
    voice = AudioFileClip("katha_voice.mp3")
    duration = voice.duration

    audio_layers = [voice]
    music_files = glob.glob("katha_music/*.mp3")
    bgm_raw = None
    if music_files:
        bgm_raw = AudioFileClip(random.choice(music_files))
        if bgm_raw.duration < duration:
            loops = int(duration // bgm_raw.duration) + 1
            bgm = concatenate_audioclips([bgm_raw] * loops)
        else:
            bgm = bgm_raw
        bgm = bgm.subclipped(0, min(duration, bgm.duration)).with_volume_scaled(0.12)
        audio_layers.append(bgm)

    bg_canvas = ColorClip(size=(1080, 1920), color=(18, 12, 32)).with_duration(duration)
    video_layers = [bg_canvas]

    scene_dur = duration / len(img_paths)
    for i, img_path in enumerate(img_paths):
        base_img = ImageClip(img_path).with_duration(scene_dur).resized(width=1080)
        zoomed = base_img.resized(lambda t, sd=scene_dur: 1.0 + 0.06 * (t / max(sd, 0.1)))
        framed = CompositeVideoClip([zoomed.with_position("center")], size=(1080, 1080)).with_duration(scene_dur)
        video_layers.append(framed.with_start(i * scene_dur).with_position(("center", 360)))

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
        .with_position(("center", 160))
    )
    video_layers.append(title_txt)

    captions = data.get("captions") or [data["screen_text"]]
    captions = [str(c).strip().upper() for c in captions if str(c).strip()]
    if not captions:
        captions = [data["screen_text"].upper()]

    cap_dur = duration / len(captions)
    for i, cap_text in enumerate(captions):
        c_clip = (
            TextClip(
                font=font_path,
                text=cap_text,
                font_size=54,
                color="white",
                stroke_color="black",
                stroke_width=5,
                method="caption",
                size=(920, None),
                margin=(0, 12),
            )
            .with_start(i * cap_dur)
            .with_duration(cap_dur)
            .with_position(("center", 1360))
        )
        video_layers.append(c_clip)

    final_audio = CompositeAudioClip(audio_layers).with_duration(duration)
    final = CompositeVideoClip(video_layers, size=(1080, 1920)).with_duration(duration).with_audio(final_audio)
    final.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)

    voice.close()
    if bgm_raw:
        bgm_raw.close()
    final.close()

# 5. 3RD KATHA YOUTUBE CHANNEL PAR UPLOAD KARNA
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
                "tags": data.get("tags", ["katha", "hindikahani", "shorts"]),
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
    asyncio.run(make_voice(data["voice_text"]))
    build_video(data, img_paths)
    upload_video("katha_output.mp4", data)
