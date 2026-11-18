import asyncio, base64, glob, json, math, os, random, re, sys, time
from datetime import datetime, timedelta, timezone
import numpy as np
from PIL import Image
import requests, edge_tts
from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy import (
    AudioFileClip, ColorClip, CompositeAudioClip, CompositeVideoClip,
    ImageClip, TextClip, VideoFileClip, concatenate_audioclips,
    concatenate_videoclips, vfx,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

RESAMPLE_BILINEAR = getattr(Image, "Resampling", Image).BILINEAR
ANTON_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf"
FALLBACK_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def get_font():
    for p in ("fonts/*.ttf", "*.ttf"):
        found = glob.glob(p)
        if found: return found[0]
    tmp = "/tmp/Anton-Regular.ttf"
    if os.path.exists(tmp): return tmp
    try:
        r = requests.get(ANTON_FONT_URL, timeout=20)
        if r.ok and len(r.content) > 10000:
            open(tmp, "wb").write(r.content)
            return tmp
    except Exception:
        pass
    return FALLBACK_FONT

def clean_ascii_caps(txt):
    return re.sub(r"[^\x20-\x7E]", "", str(txt)).strip().upper() or "BHAKTI KATHA"

def get_today_bhagwan_topic():
    ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    topics = {
        0: ("Somwar Special - Bhagwan Shiv", [
            "Samudra Manthan mein Bhagwan Shiv ka vish peena (Neelkanth)",
            "Bhagwan Shiv ki jataon mein Maa Ganga ke samane ki katha",
            "Bholenath ki kripa aur Markandeya Rishi ko amar vardaan",
            "Maa Parvati ki tapashya aur Shiv-Parvati vivah rahasya",
        ]),
        1: ("Mangalwar Special - Hanuman Ji", [
            "Nanhe Hanuman ji ka Surya ko fal samajh kar nigalna",
            "Hanuman ji ka Lanka Dahan aur Shri Ram bhakti",
            "Sanjeevani booti laane ke liye Hanuman ji ka Dronagiri parvat uthana",
            "Kalyug mein Hanuman ji ka aaj bhi dharti par rehna",
        ]),
        2: ("Budhwar Special - Ganesh Ji", [
            "Ganesh ji ne Mata-Pita ki parikrama karke brahmand jeeta",
            "Bhagwan Ganesh ji ke Ekdant banne ki adbhut kahani",
            "Ganesh ji ne bina ruke poori Mahabharat kaise likhi",
            "Kuber ka ghamand aur Bal Ganesh ji ki leela",
        ]),
        3: ("Guruwar Special - Bhagwan Vishnu & Shri Krishna", [
            "Bhakt Prahlad ki bhakti aur Bhagwan Narsingh Avtar",
            "Shri Krishna aur Sudama ki sacchi dosti",
            "Shri Krishna ka Govardhan Parvat chhoti ungli par uthana",
            "Gajendra Moksha: Jab Bhagwan Vishnu nange pair daud pade",
        ]),
        4: ("Shukrawar Special - Maa Durga & Maa Lakshmi", [
            "Maa Durga ka Mahishasura par vijay aur Navdurga shakti",
            "Samudra Manthan se Maa Lakshmi ke prakat hone ki katha",
            "Maa Lakshmi ke 8 swaroop aur ghar mein sukh-shanti ka rahasya",
            "Maa Santoshi aur sacche bhakt ki pariksha",
        ]),
        5: ("Shaniwar Special - Shani Dev & Hanuman Ji", [
            "Shani Dev aur Hanuman ji ki mitrata aur adbhut vachan",
            "Shani Dev kaise bane teeno lokon ke sabse bade Nyayadhish",
            "Raja Dashrath ki stuti aur Shani Dev ka vardaan",
            "Shaniwar ko Pipal ke ped ki puja ka pauranik rahasya",
        ]),
        6: ("Ravivar Special - Shri Ram & Surya Dev", [
            "Shabri ke jhoothe ber aur Shri Ram ka atoot prem",
            "Ram Setu mein choti gilhari ki bhakti aur seva",
            "Jatayu ka Sita Mata ko bachane ke liye mahan balidaan",
            "Surya Dev ke saat ghodon wale rath ka adbhut rahasya",
        ]),
    }
    lbl, opts = topics[ist.weekday()]
    return lbl, random.choice(opts)

def generate_katha():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"].strip())
    day_label, chosen_topic = get_today_bhagwan_topic()
    print(f"Today's Schedule ({day_label}): {chosen_topic}")
    prompt = f"""Today is {day_label}. Create a gripping 19-second Indian Mythological Katha YouTube Short on: "{chosen_topic}".
Rules:
- Start immediately with an emotional/curiosity hook (NO "Namaste doston", NO intro).
- Keep total voiceover 38-45 words in emotional Hindi (Devanagari script).
- Last segment MUST ask viewers to comment (e.g., "Har Har Mahadev", "Jai Shri Ram", matching today's deity).
- "screen_text" and every "caption" MUST be ONLY English/Hinglish ASCII letters (A-Z, 0-9, ?, !), NO Hindi script, NO emojis.
- Keep character appearance IDENTICAL across all 6 "scene_prompts" (repeat exact clothing, skin tone, crown/ornaments).
- Every scene_prompt MUST include: "cute 2D chibi cartoon illustration, Indian mythological folk art style, warm golden glowing colors, clean dark outlines, expressive cute faces, no text, no watermark".
- Return ONLY valid JSON:
{{"title":"Catchy title under 58 chars with #shorts #katha #bhakti","description":"2 lines devotional description with #katha #hindikahani #bhakti #shorts","tags":["katha","bhakti","hindikahani","mythology","shorts"],"screen_text":"3 TO 5 WORDS CAPS HOOK","segments":[{{"voice":"Hindi sentence 1 (6-8 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi sentence 2 (6-8 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi sentence 3 (6-8 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi sentence 4 (6-8 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi sentence 5 (6-8 words)","caption":"2-3 WORDS CAPS"}},{{"voice":"Hindi sentence 6 (5-7 words)","caption":"COMMENT DEITY NAME"}}],"scene_prompts":["Scene 1...","Scene 2...","Scene 3...","Scene 4...","Scene 5...","Scene 6..."]}}"""
    models = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash"]
    last_err = None
    for attempt in range(4):
        m = models[attempt % len(models)]
        try:
            res = client.models.generate_content(model=m, contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
            txt = res.text.strip()
            if txt.startswith("```"): txt = txt.strip("`").replace("json", "", 1).strip()
            data = json.loads(txt)
            if data.get("segments") and data.get("scene_prompts"):
                print("Script generated using:", m)
                return data
        except Exception as e:
            last_err = e
            print(f"Attempt {attempt + 1} ({m}) info: {e}")
            time.sleep(5)
    raise last_err

def fetch_pixabay_bg_video(filename="katha_bg_motion.mp4"):
    local = [f for ext in ("*.mp4", "*.mov", "*.mkv") for f in glob.glob(os.path.join("katha_clips", ext))]
    if local: return random.choice(local)
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key: return None
    queries = ["golden clouds sky", "temple candle diya", "sunrise clouds nature", "golden particles dark"]
    random.shuffle(queries)
    for q in queries:
        try:
            hits = requests.get("https://pixabay.com/api/videos/", params={"key": key, "q": q, "per_page": 8}, timeout=25).json().get("hits", [])
            if hits:
                vids = random.choice(hits).get("videos", {})
                for qual in ("small", "tiny", "medium"):
                    url = vids.get(qual, {}).get("url")
                    if url:
                        print(f"Downloading Pixabay backdrop ({q}, {qual})...")
                        open(filename, "wb").write(requests.get(url, timeout=45).content)
                        return filename
        except Exception as e:
            print(f"Pixabay '{q}' skipped:", e)
    return None

def make_cartoon_images(scene_prompts):
    url = f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CF_ACCOUNT_ID'].strip()}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    headers = {"Authorization": f"Bearer {os.environ['CF_API_TOKEN'].strip()}"}
    paths = []
    for i, sp in enumerate(scene_prompts[:6]):
        fn, saved = f"scene_{i}.jpg", False
        for att in range(2):
            try:
                r = requests.post(url, headers=headers, json={"prompt": sp, "steps": 4}, timeout=45)
                if r.status_code == 200:
                    img_b = r.content if "image/" in r.headers.get("content-type", "") else base64.b64decode(r.json()["result"]["image"])
                    open(fn, "wb").write(img_b)
                    paths.append(fn)
                    print(f"Generated cartoon scene {i + 1}")
                    saved = True
                    break
                print(f"Cloudflare error ({r.status_code}): {r.text[:200]}")
            except Exception as e:
                print(f"Image attempt {att + 1} error: {e}")
            time.sleep(2)
        if not saved and paths: paths.append(paths[-1])
    if not paths: raise RuntimeError("No cartoon images generated from Cloudflare.")
    return paths

async def make_voice(text, filename="katha_voice.mp3"):
    for v, rate in [("hi-IN-MadhurNeural", "+8%"), ("hi-IN-SwaraNeural", "+8%"), ("hi-IN-MadhurNeural", "+0%")]:
        try:
            await asyncio.wait_for(edge_tts.Communicate(text, v, rate=rate).save(filename), timeout=25)
            if os.path.exists(filename) and os.path.getsize(filename) > 1000:
                print(f"Voice generated via Edge-TTS ({v})!")
                return
        except Exception as e:
            print(f"Edge-TTS ({v}) failed: {e}")
            await asyncio.sleep(2)
    ekey = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if ekey:
        try:
            vid = os.environ.get("ELEVENLABS_VOICE_ID", "nPczCjzI2devNBz1zQrb")
            r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128", headers={"xi-api-key": ekey, "Content-Type": "application/json"}, json={"text": text, "model_id": "eleven_flash_v2_5", "voice_settings": {"stability": 0.50, "similarity_boost": 0.75, "speed": 1.05}}, timeout=30)
            if r.status_code == 200:
                open(filename, "wb").write(r.content)
                print("Voice generated via ElevenLabs fallback!")
                return
            print(f"ElevenLabs error ({r.status_code}): {r.text[:150]}")
        except Exception as e:
            print("ElevenLabs exception:", e)
    from gtts import gTTS
    gTTS(text=text, lang="hi").save(filename)
    print("Voice generated via gTTS fallback!")

def make_sparkle_transform(seed=42):
    rng = random.Random(seed)
    r = 5
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    glow = np.maximum(0.0, 1.0 - np.sqrt(xx * xx + yy * yy) / (r + 0.5))[:, :, None]
    rgb = np.array([[[255.0, 210.0, 80.0]]])
    sparks = [(rng.uniform(0, 1060), rng.uniform(0, 1060), rng.uniform(45, 115), rng.uniform(0, 6.28)) for _ in range(22)]
    def apply_sparks(gf, t):
        fr = np.array(gf(t), copy=True)
        fh, fw, _ = fr.shape
        if fh <= 2 * r or fw <= 2 * r: return fr
        for x0, y0, spd, ph in sparks:
            cy, cx = r + int((y0 - t * spd) % (fh - 2 * r)), r + int((x0 + math.sin(t * 2.2 + ph) * 20) % (fw - 2 * r))
            tw = 0.35 + 0.55 * (0.5 + 0.5 * math.sin(t * 5.0 + ph))
            fr[cy - r:cy + r + 1, cx - r:cx + r + 1] = np.clip(fr[cy - r:cy + r + 1, cx - r:cx + r + 1].astype(np.float32) + glow * rgb * tw, 0, 255).astype(np.uint8)
        return fr
    return apply_sparks

def make_scene_clip(img_path, seg_d, mode, sparkle_fn):
    pil = Image.open(img_path).convert("RGB").resize((1240, 1240), RESAMPLE_BILINEAR)
    def anim(gf, t):
        p = min(1.0, max(0.0, t / max(seg_d, 0.1)))
        if mode == 0: sz, x1, y1 = int(1240 - 160 * p), (1240 - int(1240 - 160 * p)) // 2, (1240 - int(1240 - 160 * p)) // 2
        elif mode == 1: sz, x1, y1 = 1080, int(160 * p), 80
        elif mode == 2: sz, x1, y1 = int(1080 + 160 * p), (1240 - int(1080 + 160 * p)) // 2, (1240 - int(1080 + 160 * p)) // 2
        else: sz, x1, y1 = 1080, int(160 * (1.0 - p)), 80
        return np.array(pil.crop((x1, y1, x1 + sz, y1 + sz)).resize((1080, 1080), RESAMPLE_BILINEAR))
    return ColorClip(size=(1080, 1080), color=(0, 0, 0)).with_duration(seg_d).transform(anim).transform(sparkle_fn)

def build_video(data, img_paths, bg_video_path=None, output_file="katha_output.mp4"):
    print("Building video...")
    font_path = get_font()
    voice = AudioFileClip("katha_voice.mp3").with_volume_scaled(1.25)
    duration = voice.duration
    audio_layers, opened_a, opened_v = [voice], [voice], []
    mfiles = []
    for fld in ("katha_music", "music", "sfx"):
        for ext in ("*.mp3", "*.wav", "*.m4a"):
            for fp in glob.glob(os.path.join(fld, "**", ext), recursive=True):
                try:
                    pr = AudioFileClip(fp)
                    if pr.duration >= 8.0: mfiles.append(fp)
                    pr.close()
                except Exception: pass
    if mfiles:
        bgm_r = AudioFileClip(random.choice(mfiles))
        opened_a.append(bgm_r)
        bgm = concatenate_audioclips([bgm_r] * (int(duration // bgm_r.duration) + 1)) if bgm_r.duration < duration else bgm_r
        audio_layers.append(bgm.subclipped(0, min(duration, bgm.duration)).with_volume_scaled(0.14))

    v_layers, n_sc = [], len(img_paths)
    sc_dur = duration / n_sc
    fade_t = min(0.35, sc_dur * 0.25)
    bg_ok = False
    if bg_video_path and os.path.exists(bg_video_path):
        try:
            raw = VideoFileClip(bg_video_path).without_audio().resized(height=1920)
            opened_v.append(raw)
            if raw.w < 1080: raw = raw.resized(width=1080)
            raw = raw.cropped(x_center=raw.w / 2, y_center=raw.h / 2, width=1080, height=1920)
            v_layers.append((concatenate_videoclips([raw] * (int(duration // max(raw.duration, 0.5)) + 1)).subclipped(0, duration)) if raw.duration < duration else raw.subclipped(0, duration))
            bg_ok = True
        except Exception as e:
            print("Pixabay bg fallback:", e)
    if not bg_ok:
        for i, ip in enumerate(img_paths):
            sd = sc_dur + (fade_t if i < n_sc - 1 else 0.0)
            bg = ImageClip(ip).resized(height=1920)
            bg = bg.cropped(x_center=bg.w / 2, y_center=bg.h / 2, width=1080, height=1920).with_duration(sd).with_start(i * sc_dur)
            if i > 0: bg = bg.with_effects([vfx.CrossFadeIn(fade_t)])
            v_layers.append(bg)

    v_layers.append(ColorClip(size=(1080, 1920), color=(14, 8, 26)).with_opacity(0.55).with_duration(duration))
    v_layers.append(ColorClip(size=(1080, 1104), color=(217, 119, 6)).with_duration(duration).with_position(("center", 348)))
    sp_fn = make_sparkle_transform()
    for i, ip in enumerate(img_paths):
        sd = sc_dur + (fade_t if i < n_sc - 1 else 0.0)
        fr = make_scene_clip(ip, sd, i % 4, sp_fn).with_start(i * sc_dur).with_position(("center", 360))
        if i > 0: fr = fr.with_effects([vfx.CrossFadeIn(fade_t)])
        v_layers.append(fr)

    v_layers.append(ColorClip(size=(960, 128), color=(180, 83, 9)).with_opacity(0.92).with_duration(duration).with_position(("center", 130)))
    v_layers.append(TextClip(font=font_path, text=clean_ascii_caps(data["screen_text"]), font_size=54, color="white", stroke_color="black", stroke_width=4, method="caption", size=(900, None), margin=(0, 10)).with_duration(duration).with_position(("center", 150)))

    segs = data["segments"]
    tot_c = max(1, sum(len(s["voice"]) for s in segs))
    cur_t = 0.0
    for i, item in enumerate(segs):
        sd = (len(item["voice"]) / tot_c) * duration
        v_layers.append(TextClip(font=font_path, text=clean_ascii_caps(item["caption"]), font_size=68, color="yellow" if i % 2 == 0 else "white", stroke_color="black", stroke_width=6, method="caption", size=(920, None), margin=(0, 14)).with_start(cur_t).with_duration(sd).with_position(("center", 1500)))
        cur_t += sd

    final = CompositeVideoClip(v_layers, size=(1080, 1920)).with_duration(duration).with_audio(CompositeAudioClip(audio_layers).with_duration(duration))
    final.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=4)
    for a in opened_a: a.close()
    for v in opened_v: v.close()
    final.close()

def upload_video(video_file, data):
    print("Uploading to YouTube...")
    creds = Credentials(token=None, refresh_token=os.environ["YT_REFRESH_TOKEN_KATHA"].strip(), token_uri="https://oauth2.googleapis.com/token", client_id=os.environ["YT_CLIENT_ID"].strip(), client_secret=os.environ["YT_CLIENT_SECRET"].strip(), scopes=["https://www.googleapis.com/auth/youtube.upload"])
    creds.refresh(Request())
    yt = build("youtube", "v3", credentials=creds)
    req = yt.videos().insert(part="snippet,status", body={"snippet": {"title": data["title"][:95], "description": data["description"], "tags": data.get("tags", ["katha", "bhakti", "shorts"]), "categoryId": "24"}, "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}, media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True))
    print("SUCCESS! Katha Video Uploaded. ID:", req.execute()["id"])

if __name__ == "__main__":
    data = generate_katha()
    print("Generated Title:", data["title"])
    img_paths = make_cartoon_images(data["scene_prompts"])
    bg_video = fetch_pixabay_bg_video()
    asyncio.run(make_voice(" ".join(s["voice"] for s in data["segments"])))
    build_video(data, img_paths, bg_video_path=bg_video)
    upload_video("katha_output.mp4", data)
