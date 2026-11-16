import asyncio
import glob
import io
import json
import os
import random
import re
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


# 1. AI VISION DIRECTOR: CLIP & MEME DEKH KAR SCRIPT + SYNCED CAPTIONS BANANA
def generate_script():
    api_key = os.environ["GEMINI_API_KEY"].strip()
    client = genai.Client(api_key=api_key)
    themes = [
        "Secret Red Number Headshot Sensitivity & Fire Button Size Trick",
        "99% Players Make This Big Mistake in Clash Squad Rank",
        "MP40 vs M1887 vs UMP: Close Range Ka Asli King Kaun?",
        "Old Free Fire Rare Facts & Nostalgia That New Players Don't Know",
        "Fast Crouch Gloo Wall & 1v4 Clutch Pro Secret",
        "BR Rank Secret Survival & Hidden Pro Strategy",
        "Free Fire Myth vs Fact That Surprises Pro Players",
        "Best Gun Skin Without Spending Diamonds (Free Trick)",
        "Sniper AWM Double Switch Fast Shot Secret",
        "Low End Phone 2GB/4GB RAM Lag Fix & Smooth Settings",
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
    avail_sfx = list_files(["sfx/*.mp3", "sfx/*.wav"])
    avail_music = list_files(["music/*.mp3", "sfx/*.mp3"])

    prompt = f"""
    Today is {today_str}. You are a viral Indian Free Fire YouTube Shorts director & scriptwriter.
    Look at the Gameplay Clip previews and Ending Meme previews provided above.
    Create a fast-paced 18-second Short on: "{chosen_theme}".

    Available files you MUST choose from:
    - Gameplay clips: {avail_clips if avail_clips else ["NONE"]}
    - Ending memes: {avail_memes if avail_memes else ["NONE"]}
    - Hook SFX: {avail_sfx if avail_sfx else ["NONE"]}
    - Background music: {avail_music if avail_music else ["NONE"]}

    Rules:
    - Start immediately with a shocking 2-second hook (NO "Hello doston", NO intro).
    - Do NOT fake play-by-play commentary ("dekho ab bande ko mara") unless it clearly fits; give crisp pro tips/facts/battles!
    - Keep total voiceover 35-44 words in natural energetic Hindi (Devanagari script).
    - Last segment MUST ask viewers a comment question (e.g., "MP40 ya M1887 comment karo!").
    - IMPORTANT: "screen_text" and every "caption" MUST be ONLY English/Hinglish ASCII letters (A-Z, 0-9, ?, !), NO Hindi script, NO emojis.
    - Return ONLY valid JSON with these exact keys:
    {{
      "title": "Catchy Hinglish title under 58 chars with #shorts #freefire",
      "description": "2 lines gaming description with #freefire #freefireindia #freefireshorts #shorts",
      "tags": ["freefire", "freefireshorts", "headshot", "gaming", "shorts"],
      "search_query": "gaming neon",
      "screen_text": "3 TO 5 WORDS CAPS HOOK",
      "segments": [
        {{"voice": "Hindi sentence 1 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 2 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 3 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 4 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 5 (5-7 words)", "caption": "2-3 WORDS CAPS"}},
        {{"voice": "Hindi sentence 6 (5-7 words)", "caption": "COMMENT YOUR GUN"}}
      ],
      "chosen_clips": ["exact filenames from Gameplay clips"],
      "chosen_meme": "1 exact filename from Ending memes (or empty string)",
      "chosen_sfx": "1 exact filename from Hook SFX (or empty string)",
      "chosen_music": "1 exact filename from Background music (or empty string)"
    }}
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
            data = json.loads(text)
            if data.get("segments"):
                return data
        except Exception as e:
            last_err = e
            print(f"Attempt {attempt + 1} info: {e}")
            time.sleep(10)
    raise last_err


# 2. FAST INDIAN HINDI VOICEOVER (Edge-TTS Indian Primary + Optional ElevenLabs)
async def make_voice(text, filename="voice.mp3"):
    use_eleven = os.environ.get("USE_ELEVENLABS_FF", "false").lower() == "true"
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")

    if use_eleven and eleven_key:
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"
            res = requests.post(
                url,
                headers={"xi-api-key": eleven_key, "Content-Type": "application/json"},
                json={
                    "text": text,
                    "model_id": "eleven_flash_v2_5",
                    "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "speed": 1.15},
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
    print("Voice generated via Indian Edge-TTS (+15%)!")


# 3. SMART CLIPS SELECTION
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
        chosen_paths.extend(remaining[: max(0, 6 - len(chosen_paths))])
        print("Selected Free Fire clips:", chosen_paths)
        return chosen_paths[:6]

    api_key = os.environ["PIXABAY_API_KEY"].strip()
    query = data.get("search_query", "gaming")
    res = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": query, "per_page": 5},
        timeout=30,
    ).json()
    hits = res.get("hits", []) or requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": api_key, "q": "gaming", "per_page": 5},
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


# 4. FAST-CUT (1.8s) + HD BLUR BACKDROP + ANTON FONT + SYNCED CAPTIONS + MEME
def build_video(data, bg_paths, output_file="output.mp4"):
    font_path = get_gaming_font()
    voice = AudioFileClip("voice.mp3").with_volume_scaled(1.25)
    duration = voice.duration

    meme_path = pick_smart_file(["memes"], data.get("chosen_meme"), [".mp4"])
    sfx_path = pick_smart_file(["sfx"], data.get("chosen_sfx"), [".mp3", ".wav"], max_dur=7.9)
    music_path = pick_smart_file(["music", "sfx"], data.get("chosen_music"), [".mp3", ".wav", ".m4a"], min_dur=8.0)

    meme_raw = None
    meme_dur = 0.0
    if meme_path:
        print("Selected ending meme:", meme_path)
        meme_raw = VideoFileClip(meme_path)
        if meme_raw.duration > 0.2:
            meme_dur = min(meme_raw.duration, 2.5)
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
            sfx_outro_dur = min(sfx_raw.duration, 2.0)

    bg_dur = duration + sfx_outro_dur
    audio_layers = [voice]
    bgm_raw = None

    if music_path:
        print("Selected BGM:", music_path)
        bgm_raw = AudioFileClip(music_path)
        if bgm_raw.duration < duration:
            loops = int(duration // bgm_raw.duration) + 1
            bgm = concatenate_audioclips([bgm_raw] * loops)
        else:
            bgm = bgm_raw
        bgm = bgm.subclipped(0, min(duration, bgm.duration)).with_volume_scaled(0.13)
        audio_layers.append(bgm)

    if sfx_raw:
        if meme_dur > 0.0:
            audio_layers.append(sfx_raw.subclipped(0, min(sfx_raw.duration, 1.2)).with_volume_scaled(0.40).with_start(0))
        elif sfx_outro_dur > 0.0:
            audio_layers.append(sfx_raw.subclipped(0, sfx_outro_dur).with_volume_scaled(0.80).with_start(duration))

    opened_clips = []
    segments = []
    if bg_paths:
        target_cut = 1.8
        current_len = 0.0
        idx = 0
        while current_len < bg_dur and idx < 30:
            clip = VideoFileClip(bg_paths[idx % len(bg_paths)]).without_audio()
            opened_clips.append(clip)
            if clip.duration <= 0.3:
                idx += 1
                continue
            cut_len = min(target_cut, clip.duration, bg_dur - current_len)
            max_start = max(0.0, clip.duration - cut_len)
            start_t = random.uniform(0.0, max_start) if max_start > 0.3 else 0.0

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
                dark_veil = ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.18).with_duration(cut_len)
                comp_seg = CompositeVideoClip([bg_fill, dark_veil], size=(1080, 1920)).with_duration(cut_len)

            segments.append(comp_seg)
            current_len += cut_len
            idx += 1

    if segments:
        bg = concatenate_videoclips(segments)
        if bg.duration > bg_dur:
            bg = bg.subclipped(0, bg_dur)
    else:
        bg = ColorClip(size=(1080, 1920), color=(15, 23, 42)).with_duration(bg_dur)

    # Top Red Hook Banner
    banner_bg = (
        ColorClip(size=(960, 130), color=(185, 28, 28))
        .with_opacity(0.92)
        .with_duration(bg_dur)
        .with_position(("center", 145))
    )

    title_txt = (
        TextClip(
            font=font_path,
            text=clean_ascii_caps(data["screen_text"]),
            font_size=56,
            color="white",
            stroke_color="black",
            stroke_width=4,
            method="caption",
            size=(900, None),
            margin=(0, 10),
        )
        .with_duration(bg_dur)
        .with_position(("center", 165))
    )

    # Synced Alternating Yellow/White Captions
    seg_list = data["segments"]
    total_chars = max(1, sum(len(s["voice"]) for s in seg_list))
    caption_clips = []
    cur_t = 0.0

    for i, item in enumerate(seg_list):
        seg_dur = (len(item["voice"]) / total_chars) * duration
        cap_text = clean_ascii_caps(item["caption"])
        cap_color = "yellow" if i % 2 == 0 else "white"

        c_clip = (
            TextClip(
                font=font_path,
                text=cap_text,
                font_size=74,
                color=cap_color,
                stroke_color="black",
                stroke_width=6,
                method="caption",
                size=(920, None),
                margin=(0, 14),
            )
            .with_start(cur_t)
            .with_duration(seg_dur)
            .with_position(("center", 1290))
        )
        caption_clips.append(c_clip)
        cur_t += seg_dur

    video_layers = [bg, banner_bg, title_txt, *caption_clips]
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
    full_voice = " ".join(s["voice"] for s in data["segments"])
    asyncio.run(make_voice(full_voice))
    bg_paths = get_bg_clips(data)
    build_video(data, bg_paths)
    upload_video("output.mp4", data)
