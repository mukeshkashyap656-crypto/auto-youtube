import asyncio
import glob
import io
import json
import os
import random
import time
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
    AudioFileClip,
    ColorClip,
    CompositeAudioClip,
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
    concatenate_audioclips,
    concatenate_videoclips,
)

def list_files(pattern):
    return [os.path.basename(p) for p in sorted(glob.glob(pattern))]

def extract_preview_parts(pattern, label, limit=8):
    files = glob.glob(pattern)
    if not files:
        return [], []
    random.shuffle(files)
    selected = files[:limit]
    names = []
    parts = []
    for path in selected:
        name = os.path.basename(path)
        names.append(name)
        c = None
        try:
            c = VideoFileClip(path)
            t = min(max(0.1, c.duration * 0.5), max(0.1, c.duration - 0.1))
            frame = c.get_frame(t)
            img = Image.fromarray(frame)
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

# 1. AI DIRECTOR: CLIP & MEME DEKH KAR TOPIC, SCRIPT AUR MATCHING FILES CHUNNA
def generate_script():
    api_key = os.environ["GEMINI_API_KEY"].strip()
    client = genai.Client(api_key=api_key)
    themes = [
        "Secret Red Number Headshot Sensitivity & Fire Button Size Trick",
        "99% Players Make This Big Mistake in Clash Squad Rank",
        "MP40 vs M1887 or Best Character Skill Debate (Comment Battle)",
        "Old Free Fire Rare Facts & Nostalgia That New Players Don't Know",
        "Fast Crouch Gloo Wall & 1v4 Clutch Pro Secret",
        "BR Rank Secret Survival & Hidden Pro Strategy",
        "Free Fire Myth vs Fact That Surprises Pro Players",
        "Best Gun Skin Without Spending Diamonds (Free Trick)",
        "Sniper AWM Double Switch Fast Shot Secret",
        "Low End Phone 2GB/4GB RAM Lag Fix & Smooth Gameplay Settings",
        "Top 3 Overpowered Character Combinations for CS Rank Push",
        "Why Old Peak & Factory Roof Fights Were Legendary",
        "Rush vs Camp Strategy: How Grandmaster Players Win",
        "Hidden Movement Speed & Jump Shot Pro Technique",
        "Rare Evo Gun Facts & Most Underrated Gun in Free Fire",
    ]
    chosen_theme = random.choice(themes)
    today_str = time.strftime("%d %B %Y")

    avail_clips, clip_parts = extract_preview_parts("clips/freefire/*.mp4", "Gameplay Clip", limit=8)
    avail_memes, meme_parts = extract_preview_parts("memes/*.mp4", "Ending Meme", limit=6)
    avail_sfx = list_files("sfx/*.mp3")
    avail_music = list_files("music/*.mp3")

    prompt = f"""
    Today is {today_str}. You are a viral Indian Free Fire YouTube Shorts director & scriptwriter.
    Look at the Gameplay Clip previews and Ending Meme previews provided above.
    Create a fast-paced 18-second Short on: {chosen_theme}.

    Available files you MUST choose from:
    - Gameplay clips: {avail_clips if avail_clips else ["NONE"]}
    - Ending memes: {avail_memes if avail_memes else ["NONE"]}
    - Hook SFX: {avail_sfx if avail_sfx else ["NONE"]}
    - Background music: {avail_music if avail_music else ["NONE"]}

    Rules:
    - Start immediately with a shocking 1-line hook (NO "Hello dosto" or intro).
    - Pick the Gameplay clips whose visuals best match your topic, and pick the Ending meme whose reaction best fits your ending punchline/question.
    - End with a short question asking viewers to comment their choice/opinion.
    - Return ONLY valid JSON with these exact keys:
    - "title": Catchy Hinglish title under 60 chars with #shorts #freefire
    - "description": 2 lines gaming description with #freefire #freefireindia #freefireshorts #shorts
    - "tags": list of 5 short tags like ["freefire", "freefireshorts", "headshot", "gaming", "shorts"]
    - "search_query": 2 English words for stock fallback video (pick from: "gaming neon", "esports gamer", "cyberpunk dark", "abstract laser")
    - "voice_text": 3 to 4 short, high-energy sentences in natural Hindi (Devanagari script, 35-45 words total)
    - "screen_text": ONLY 3 to 5 words MAX in Hinglish/English ALL CAPS, NO emojis
    - "captions": list of 4 short punchy Hinglish/English ALL CAPS lines (3 to 4 words each, NO emojis) matching the voiceover order
    - "chosen_clips": list of up to 5 exact filenames from Gameplay clips that BEST match visually (or [] if NONE)
    - "chosen_meme": 1 exact filename from Ending memes that BEST fits the ending mood (or "" if NONE)
    - "chosen_sfx": 1 exact filename from Hook SFX that BEST fits (or "" if NONE)
    - "chosen_music": 1 exact filename from Background music that BEST fits the vibe (or "" if NONE)
    """

    last_err = None
    for attempt in range(4):
        try:
            req_contents = [*clip_parts, *meme_parts, prompt] if (attempt < 2 and (clip_parts or meme_parts)) else prompt
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=req_contents,
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

# 2. FAST & VIRAL HINDI VOICEOVER (ElevenLabs "Adam" + Edge-TTS Backup)
async def make_voice(text, filename="voice.mp3"):
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = "pNInz6obpgDQGcFmaJgB"  # Adam (Viral Shorts voice)

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
                    "speed": 1.15,
                },
            }
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(res.content)
                print("Voice generated via ElevenLabs (Adam)!")
                return
            else:
                print(f"ElevenLabs failed ({res.status_code}): {res.text[:200]} -> Using edge-tts")
        except Exception as e:
            print(f"ElevenLabs error: {e} -> Using edge-tts")

    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="+15%")
    await communicate.save(filename)
    print("Voice generated via Edge-TTS!")

# 3. SMART CLIPS SELECTION (AI Vision Chosen + Random Fill + Pixabay Fallback)
def get_bg_clips(data, filename="bg.mp4"):
    all_local = glob.glob("clips/freefire/*.mp4")
    if all_local:
        chosen_paths = []
        raw_chosen = data.get("chosen_clips", [])
        if isinstance(raw_chosen, list):
            for name in raw_chosen:
                candidate = os.path.join("clips", "freefire", os.path.basename(str(name)))
                if os.path.isfile(candidate) and candidate not in chosen_paths:
                    chosen_paths.append(candidate)

        remaining = [p for p in all_local if p not in chosen_paths]
        random.shuffle(remaining)
        chosen_paths.extend(remaining[: max(0, 5 - len(chosen_paths))])
        print("Selected Free Fire clips:", chosen_paths)
        return chosen_paths[:5]

    api_key = os.environ["PIXABAY_API_KEY"].strip()
    query = data.get("search_query", "gaming")
    res = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": query, "per_page": 5},
        timeout=30,
    ).json()
    hits = res.get("hits", [])

    if not hits:
        res = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": api_key, "q": "gaming", "per_page": 5},
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

def pick_smart_file(folder, ai_choice, pattern):
    all_files = glob.glob(pattern)
    if not all_files:
        return None
    if isinstance(ai_choice, str) and ai_choice.strip():
        candidate = os.path.join(folder, os.path.basename(ai_choice.strip()))
        if os.path.isfile(candidate):
            return candidate
    return random.choice(all_files)

# 4. FAST-CUT (3s) + CAPTIONS + SMART BGM + SMART SFX + SMART ENDING MEME
def build_video(data, bg_paths, output_file="output.mp4"):
    voice = AudioFileClip("voice.mp3")
    duration = voice.duration

    meme_path = pick_smart_file("memes", data.get("chosen_meme"), "memes/*.mp4")
    sfx_path = pick_smart_file("sfx", data.get("chosen_sfx"), "sfx/*.mp3")
    music_path = pick_smart_file("music", data.get("chosen_music"), "music/*.mp3")

    meme_raw = None
    meme_dur = 0.0
    if meme_path:
        print("Selected ending meme:", meme_path)
        meme_raw = VideoFileClip(meme_path)
        if meme_raw.duration > 0.2:
            meme_dur = min(meme_raw.duration, 2.8)
        else:
            meme_raw.close()
            meme_raw = None

    sfx_raw = None
    sfx_outro_dur = 0.0
    if sfx_path:
        print("Selected SFX:", sfx_path)
        sfx_raw = AudioFileClip(sfx_path)
        if sfx_raw.duration <= 0.1:
            sfx_raw.close()
            sfx_raw = None
        elif meme_dur == 0.0:
            sfx_outro_dur = min(sfx_raw.duration, 2.5)

    bg_dur = duration + sfx_outro_dur

    audio_layers = [voice]
    bgm_raw = None
    if music_path:
        print("Selected music:", music_path)
        bgm_raw = AudioFileClip(music_path)
        if bgm_raw.duration < duration:
            loops = int(duration // bgm_raw.duration) + 1
            bgm = concatenate_audioclips([bgm_raw] * loops)
        else:
            bgm = bgm_raw
        bgm = bgm.subclipped(0, min(duration, bgm.duration)).with_volume_scaled(0.12)
        audio_layers.append(bgm)

    if sfx_raw:
        if meme_dur > 0.0:
            sfx_clip = sfx_raw.subclipped(0, min(sfx_raw.duration, 1.2)).with_volume_scaled(0.35).with_start(0)
            audio_layers.append(sfx_clip)
        elif sfx_outro_dur > 0.0:
            sfx_clip = sfx_raw.subclipped(0, sfx_outro_dur).with_volume_scaled(0.85).with_start(duration)
            audio_layers.append(sfx_clip)

    opened_clips = []
    segments = []
    if bg_paths:
        target_cut = 3.0
        current_len = 0.0
        idx = 0
        while current_len < bg_dur and idx < 25:
            clip = VideoFileClip(bg_paths[idx % len(bg_paths)]).without_audio()
            opened_clips.append(clip)
            if clip.duration <= 0.2:
                idx += 1
                continue
            cut_len = min(target_cut, clip.duration, bg_dur - current_len)
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
        if bg.duration > bg_dur:
            bg = bg.subclipped(0, bg_dur)
    else:
        bg = ColorClip(size=(1080, 1920), color=(15, 23, 42)).with_duration(bg_dur)

    overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.22).with_duration(bg_dur)

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
        .with_duration(bg_dur)
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
            .with_position(("center", 1380))
        )
        caption_clips.append(c_clip)

    video_layers = [bg, overlay, title_txt, *caption_clips]
    if meme_raw and meme_dur > 0.0:
        meme_seg = meme_raw.subclipped(0, meme_dur)
        meme_vid = meme_seg.without_audio().resized(width=1080)
        if meme_vid.h > 1920:
            meme_vid = meme_vid.resized(height=1920)
        meme_bg = ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_duration(meme_dur)
        video_layers.append(meme_bg.with_start(duration))
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

# 5. YOUTUBE PAR PUBLIC AUTO UPLOAD KARNA
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
                "tags": data.get("tags", ["freefire", "shorts", "gaming"]),
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
    bg_paths = get_bg_clips(data)
    build_video(data, bg_paths)
    upload_video("output.mp4", data)
