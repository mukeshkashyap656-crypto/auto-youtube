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

# 1. VIRAL INDIAN CAR GAMING & SUPERCAR TOPICS (Synced Voice + Captions)
def generate_script():
    api_key = os.environ["GEMINI_API_KEY"].strip()
    client = genai.Client(api_key=api_key)
    themes = [
        "GTA 6 vs GTA 5 Car Crash Physics: Kaun Zyada Real Hai?",
        "Kya 50 Crore ki Bugatti 1000 Speed Breakers Paar Kar Payegi?",
        "Mega Ramp Death Jump: 400 KMPH par Car Hawa Mein Udd Gayi!",
        "Mahindra Thar vs Lamborghini Offroad Challenge in Car Games",
        "300 KMPH par Car ke Brake Fail Ho Jaye Toh Kya Hoga?",
        "GTA 6 ki 3 Sabse Khatarnak Supercars Jo Sabko Chahiye",
        "Police Chase Se Bachne ki 1000 IQ Car Trick",
        "Duniya ki Sabse Fast Car vs Fighter Jet Race in Games",
        "BeamNG Drive Sabse Khatarnak Crash Test Challenge",
        "99% Gamers Car Jump Mein Yeh Galti Karte Hain",
        "1 Crore vs 50 Crore Supercar Ramp Jump Test",
        "Impossible Bridge Stunt: Kya Aakhiri Second Mein Bachegi Car?",
    ]
    chosen_theme = random.choice(themes)
    today_str = time.strftime("%d %B %Y")

    prompt = f"""
    Today is {today_str}. Create a super fast-paced, viral 18-second Indian Car Gaming YouTube Short on: "{chosen_theme}".
    Rules:
    - Start immediately with a shocking 2-second question/challenge hook (NO "Hello doston", NO intro).
    - Keep total voiceover 35-42 words in natural conversational Hindi (Devanagari script) so it sounds energetic.
    - Last segment MUST ask a quick comment question ("Aapki favourite car kaunsi hai?").
    - Return ONLY valid JSON with these exact keys:
    {{
      "title": "Catchy Hinglish title under 58 chars with #shorts #cargaming",
      "description": "2 line gaming description with #cargaming #gta6 #supercars #shorts",
      "tags": ["cargaming", "gta6", "supercars", "beamng", "shorts"],
      "search_query": "2 English words from: sports car, car racing, supercar drift, lamborghini",
      "screen_text": "3 TO 5 WORDS CAPS HOOK NO EMOJI",
      "segments": [
        {{"voice": "Hindi sentence 1 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 2 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 3 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 4 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 5 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 6 (5-7 words)", "caption": "COMMENT YOUR CAR"}}
      ]
    }}
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
            data = json.loads(text)
            if data.get("segments"):
                return data
        except Exception as e:
            last_err = e
            print(f"Attempt {attempt + 1} info: {e}")
            time.sleep(12)
    raise last_err


# 2. ENERGETIC INDIAN GAMING VOICEOVER (Edge-TTS Indian Hindi Primary + ElevenLabs Optional)
async def make_voice(text, filename="car_voice.mp3"):
    # Note: hi-IN-MadhurNeural sounds natural & energetic for Indian Hindi Shorts
    use_eleven = os.environ.get("USE_ELEVENLABS_CAR", "false").lower() == "true"
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()

    if use_eleven and eleven_key:
        try:
            voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
            res = requests.post(
                url,
                headers={"xi-api-key": eleven_key, "Content-Type": "application/json"},
                json={
                    "text": text,
                    "model_id": "eleven_flash_v2_5",
                    "voice_settings": {"stability": 0.4, "similarity_boost": 0.8, "speed": 1.15},
                },
                timeout=30,
            )
            if res.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(res.content)
                print("Voice generated via ElevenLabs!")
                return
        except Exception as e:
            print(f"ElevenLabs fallback triggered: {e}")

    communicate = edge_tts.Communicate(text, "hi-IN-MadhurNeural", rate="+15%")
    await communicate.save(filename)
    print("Voice generated via Indian Edge-TTS (+15% fast gaming pace)!")


# 3. CLIPS COLLECTOR (Checks clips/car/, clips/, and Pixabay fallback)
def get_bg_clips(query, filename="car_bg.mp4"):
    local_clips = []
    for folder in ("clips/car", "clips"):
        for ext in ("*.mp4", "*.MP4", "*.mov", "*.mkv"):
            local_clips.extend(glob.glob(os.path.join(folder, ext)))

    local_clips = list(dict.fromkeys(local_clips))
    if local_clips:
        random.shuffle(local_clips)
        chosen = local_clips[:8]
        print("Using own car clips:", chosen)
        return chosen

    api_key = os.environ["PIXABAY_API_KEY"].strip()
    res = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": query, "per_page": 6},
        timeout=30,
    ).json()
    hits = res.get("hits", []) or requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": "sports car", "per_page": 6},
        timeout=30,
    ).json().get("hits", [])

    if hits:
        videos = random.choice(hits).get("videos", {})
        for quality in ("medium", "small", "large", "tiny"):
            if quality in videos and videos[quality].get("url"):
                video_data = requests.get(videos[quality]["url"], timeout=60).content
                with open(filename, "wb") as f:
                    f.write(video_data)
                return [filename]
    return []


# 4. FAST-CUT 1.8s EDITING + SYNCED CAPTIONS + SFX/BGM MIX
def build_video(data, bg_paths, output_file="car_output.mp4"):
    voice = AudioFileClip("car_voice.mp3").with_volume_scaled(1.25)
    duration = voice.duration

    # Checks BOTH sfx/ and music/ folders!
    music_files = []
    for folder in ("sfx", "music"):
        for ext in ("*.mp3", "*.wav", "*.m4a"):
            music_files.extend(glob.glob(os.path.join(folder, "**", ext), recursive=True))

    bgm_raw = None
    if music_files:
        chosen_bgm = random.choice(music_files)
        print("Mixing background track:", chosen_bgm)
        bgm_raw = AudioFileClip(chosen_bgm)
        if bgm_raw.duration < duration:
            loops = int(duration // bgm_raw.duration) + 1
            bgm = concatenate_audioclips([bgm_raw] * loops)
        else:
            bgm = bgm_raw
        bgm = bgm.subclipped(0, min(duration, bgm.duration)).with_volume_scaled(0.14)
        final_audio = CompositeAudioClip([voice, bgm])
    else:
        final_audio = voice

    # Fast 1.8-second cuts for high retention
    opened_clips = []
    segments_v = []
    if bg_paths:
        target_cut = 1.8
        current_len = 0.0
        idx = 0
        while current_len < duration and idx < 30:
            clip = VideoFileClip(bg_paths[idx % len(bg_paths)]).without_audio()
            opened_clips.append(clip)
            if clip.duration <= 0.3:
                idx += 1
                continue
            cut_len = min(target_cut, clip.duration, duration - current_len)
            max_start = max(0.0, clip.duration - cut_len)
            start_t = random.uniform(0.0, max_start) if max_start > 0.3 else 0.0

            seg = clip.subclipped(start_t, start_t + cut_len)
            seg = seg.resized(height=1920)
            if seg.w < 1080:
                seg = seg.resized(width=1080)
            seg = seg.cropped(x_center=seg.w / 2, y_center=seg.h / 2, width=1080, height=1920)
            segments_v.append(seg)
            current_len += cut_len
            idx += 1

    if segments_v:
        bg = concatenate_videoclips(segments_v)
        if bg.duration > duration:
            bg = bg.subclipped(0, duration)
    else:
        bg = ColorClip(size=(1080, 1920), color=(15, 23, 42)).with_duration(duration)

    overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.20).with_duration(duration)

    # Top Red Hook Banner (grabs attention in 0.5 sec)
    banner_bg = (
        ColorClip(size=(960, 130), color=(185, 28, 28))
        .with_opacity(0.88)
        .with_duration(duration)
        .with_position(("center", 140))
    )

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    title_txt = (
        TextClip(
            font=font_path,
            text=data["screen_text"].upper(),
            font_size=50,
            color="white",
            stroke_color="black",
            stroke_width=4,
            method="caption",
            size=(900, None),
            margin=(0, 12),
        )
        .with_duration(duration)
        .with_position(("center", 165))
    )

    # Synced Captions (matched proportionally to each spoken Hindi line!)
    seg_list = data["segments"]
    total_chars = max(1, sum(len(s["voice"]) for s in seg_list))
    caption_clips = []
    cur_t = 0.0

    for i, item in enumerate(seg_list):
        seg_dur = (len(item["voice"]) / total_chars) * duration
        cap_text = str(item["caption"]).strip().upper()
        cap_color = "yellow" if i % 2 == 0 else "white"

        c_clip = (
            TextClip(
                font=font_path,
                text=cap_text,
                font_size=68,
                color=cap_color,
                stroke_color="black",
                stroke_width=6,
                method="caption",
                size=(920, None),
                margin=(0, 14),
            )
            .with_start(cur_t)
            .with_duration(seg_dur)
            .with_position(("center", 1250))
        )
        caption_clips.append(c_clip)
        cur_t += seg_dur

    final = CompositeVideoClip([bg, overlay, banner_bg, title_txt, *caption_clips]).with_audio(final_audio)
    final.write_videofile(output_file, fps=30, codec="libx264", audio_codec="aac")

    voice.close()
    if bgm_raw:
        bgm_raw.close()
    for c in opened_clips:
        c.close()
    final.close()


# 5. AUTO UPLOAD TO CAR GAME CHANNEL
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
    full_voice_text = " ".join(s["voice"] for s in data["segments"])
    asyncio.run(make_voice(full_voice_text))
    bg_paths = get_bg_clips(data.get("search_query", "sports car"))
    build_video(data, bg_paths)
    upload_video("car_output.mp4", data)
