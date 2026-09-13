#!/usr/bin/env python3
"""
Mr Long & Ronnie — Learn English!  Daily episode generator.

100% free-tier pipeline:
  * script  : episodes/episodes.json list / episode-NNN.json / template / Gemini
  * voices  : Gemini TTS (free tier) when key present, else espeak-ng offline
  * video   : per-frame PUPPET ANIMATION (mouth flaps driven by the audio
              waveform, head bob, tilt, idle breathing) over locked art,
              rendered through ffmpeg (static build via imageio-ffmpeg)
  * subs    : EN + Khmer burned in via libass with bundled Noto Sans Khmer

Usage:
  python3 pipeline/make_episode.py                       # auto episode for today
  python3 pipeline/make_episode.py episodes/episode-001.json
"""
import base64, json, math, os, random, re, shutil, subprocess, sys, urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUT = ROOT / "out"
W, H, FPS = 1280, 720, 24
FONTSDIR = ASSETS / "fonts"

# ------------------------------------------------------------------ speakers
SPEAKERS = {
    "mr_long": {
        "sheet": ASSETS / "characters" / "mr_long_talk.png",
        "fallback_sheet": ASSETS / "characters" / "mr_long_sprites.png",
        "side": "left",
        "gemini_voice": "Sadaltager",      # warm, knowledgeable teacher
        "espeak": ["-v", "en", "-p", "30", "-s", "145"],
    },
    "ronnie": {
        "sheet": ASSETS / "characters" / "ronnie_talk.png",
        "fallback_sheet": ASSETS / "characters" / "ronnie_sprites.png",
        "side": "right",
        "gemini_voice": "Puck",            # cheerful, playful
        "espeak": ["-v", "en", "-p", "85", "-s", "175"],
    },
}
EXPRESSIONS = ["happy", "surprised", "thinking", "pointing", "proud", "sleepy"]

WORD_BANK = [  # (english, khmer) — one pair per auto-episode day
    ("apple", "ផ្លែប៉ោម"), ("banana", "ចេក"), ("water", "ទឹក"),
    ("dog", "ឆ្កែ"), ("cat", "ឆ្មា"), ("sun", "ព្រះអាទិត្យ"),
    ("star", "ផ្កាយ"), ("red", "ពណ៌ក្រហម"), ("blue", "ពណ៌ខៀវ"),
    ("one", "មួយ"), ("two", "ពីរ"), ("three", "បី"),
    ("big", "ធំ"), ("small", "តូច"), ("friend", "មិត្តភក្ដិ"),
    ("eat", "ហូប"), ("drink", "ផឹក"), ("ball", "បាល់"),
    ("book", "សៀវភៅ"), ("happy", "សប្បាយចិត្ត"),
]

# ------------------------------------------------------------------ curriculum
SCENARIO_BG = {"home": "home", "laundry": "home", "kitchen": "kitchen",
               "market": "market", "beach": "beach", "river": "beach",
               "angkor": "angkor", "street": "street", "park": "park",
               "classroom": "classroom", "temple": "angkor"}

# one or two story beats per scenario so episodes feel like little adventures
ACTION = {
 "home": [("ronnie", "Look! Bubbles everywhere! Hee hee!", "មើល! ពពុះនៅគ្រប់កន្លែង!", "happy"),
          ("mr_long", "Work first, play later!", "ធ្វើការសិន លេងពេលក្រោយ!", "proud")],
 "kitchen": [("ronnie", "Yum yum! My tummy is singing!", "ឆ្ងាញ់ណាស់!", "happy"),
             ("mr_long", "Wash your paws before we eat!", "លាងដៃមុនពេលហូប!", "pointing")],
 "market": [("mr_long", "How much is it, please?", "តើវាថ្លៃប៉ុន្មាន?", "pointing"),
            ("ronnie", "Two thousand riel, please! Here you go!", "សូម! ពីរពាន់រៀល!", "proud")],
 "beach": [("ronnie", "Splash splash! The water is warm!", "ប្លោក! ទឹកកក់ក្ដៅ!", "happy"),
           ("mr_long", "Stay where I can see you, Ronnie!", "នៅកន្លែងដែលខ្ញុំមើលឃើញ!", "pointing")],
 "angkor": [("mr_long", "These stones are almost a thousand years old!", "ថ្មទាំងនេះជិតមួយពាន់ឆ្នាំហើយ!", "proud"),
            ("ronnie", "Wow! It is like a giant's castle!", "វ៉ូវ! ដូចប្រាសាទយក្ស!", "surprised")],
 "street": [("ronnie", "Beep beep! Off we go!", "ប៊ីប! ចេញដំណើរ!", "happy"),
            ("mr_long", "Always look both ways, friends!", "មើលទាំងសងខាង!", "pointing")],
 "park": [("ronnie", "Let's play after the lesson!", "តោះលេងបន្ទាប់ពីមេរៀន!", "happy"),
          ("mr_long", "Nature is our second classroom!", "ធម្ជាតិជាថ្ាក់រៀនទីពីរ!", "proud")],
 "classroom": [("ronnie", "I love school!", "ខ្ញុំស្រឡាញ់សាលារៀន!", "happy"),
               ("mr_long", "Eyes on me, class!", "មើលមកខ្ញុំ!", "pointing")],
}

V_ML = ["Hello everyone! I am Mr Long!", "Welcome back, friends! I am Mr Long!",
        "Good day, class! Mr Long here!", "Hello hello! Teacher Mr Long here!"]
V_R = ["Hi hi hi! I am Ronnie! Let's learn English!", "Hello hello! It's me, Ronnie! English time!",
       "Woo hoo! Ronnie here! Let's go go go!", "Yay! I am Ronnie! Ready to learn!"]

def build_curriculum(item):
    """Turn one curriculum entry (scenario + words + phrase) into a storyboard."""
    ep = int(item.get("episode", 1))
    rnd = random.Random(ep * 7919 + 13)
    pick = lambda L: L[rnd.randrange(len(L))]
    bg = SCENARIO_BG.get(item.get("scenario", "classroom"), "classroom")
    words = item.get("words", [])
    ph = item.get("phrase")
    S = []
    def add(sp, en, km, ex="happy", b=bg, word=None, pause=0.0):
        S.append({"speaker": sp, "en": en, "km": km, "expr": ex, "bg": b,
                  **({"word": word} if word else {}), **({"pause": pause} if pause else {})})
    add("mr_long", pick(V_ML), "សួស្ដីអនកទាំងអស់គ្នា! ខ្ញុំឈ្មោះ មីស្ទើរ ឡុង!")
    add("ronnie", pick(V_R) + " Wow, look where we are today!", "វ៉ូវ! មើលកន្លែងដែលយើងនៅថ្ងៃនេះ!", "surprised")
    add("mr_long", f"Today's adventure: {item.get('title_en', 'a new place')}!",
        f"ការផ្សងព្រេងថ្ងៃនេះ: {item.get('title_km', '')}!", "pointing")
    if ph:
        add("mr_long", f"Our magic phrase: {ph['en']}", ph["km"], "pointing")
        add("ronnie", ph["en"], ph["km"], "proud")
    for j, w in enumerate(words[:3]):
        add("mr_long", f"New word {j + 1}: {w['en']}. {w['en']}!", w["km"], "pointing", word=w["en"])
        add("ronnie", f"{str(w['en']).capitalize()}! {str(w['en']).capitalize()}!", w["km"], "happy", word=w["en"])
        if j == 0:
            add("mr_long", "Repeat after me. Say it loud!", "និយាយតាមខ្ញុំ! និយាយឲយខ្លាំង!", "proud")
    for sp, en, km, ex in ACTION.get(item.get("scenario", "classroom"), ACTION["classroom"]):
        add(sp, en, km, ex)
    w0 = words[0] if words else {"en": "friend", "km": "មិត្តភក្ដិ"}
    add("mr_long", f"Quiz time! Where is the {w0['en']}? Point to it!",
        "ពេលសំណួរ! " + w0["km"] + " នៅឯណា? ចង្អុលវា!", "thinking", pause=1.5, word=w0["en"])
    add("ronnie", f"There! The {w0['en']}! Did I win?", "នោះហើយ " + w0["km"] + "!", "pointing", word=w0["en"])
    add("mr_long", "Yes Ronnie! Well done, everyone!", "បាទហើយ រ៉ូនី! ពូកែណាស់អ្នកទាំងអស់គ្នា!", "proud")
    add("ronnie", "See you tomorrow! Bye bye!", "ជួបគ្នាថ្ងៃស្អែក! លាហើយ!", "happy")
    return {"episode": ep, "title_en": item.get("title_en", f"Episode {ep}"),
            "title_km": item.get("title_km", ""), "scenes": S}

# ------------------------------------------------------------------ ffmpeg
def ffmpeg_bin():
    p = shutil.which("ffmpeg")
    if p:
        return p
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

FF = None  # resolved lazily so importing never needs ffmpeg installed

def get_ff():
    global FF
    if FF is None:
        FF = ffmpeg_bin()
    return FF

def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, cmd[:4]))} failed:\n{r.stderr[-3000:]}")
    return r

def duration(path):
    r = subprocess.run([get_ff(), "-i", str(path), "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", r.stderr)
    if not m:
        return 1.0
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)

def has_subtitles_filter():
    r = subprocess.run([get_ff(), "-hide_banner", "-filters"], capture_output=True, text=True)
    return re.search(r"^\s*.*subtitles", r.stdout, re.M) is not None

# ------------------------------------------------------------------ TTS
def tts(text, speaker, out_wav):
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        try:
            return gemini_tts(text, SPEAKERS[speaker]["gemini_voice"], out_wav, key)
        except Exception as e:
            print(f"  ! gemini tts failed ({e}); falling back to espeak", file=sys.stderr)
    cmd = ["espeak-ng"] + SPEAKERS[speaker]["espeak"] + ["-w", str(out_wav), text]
    run(cmd)

def gemini_tts(text, voice, out_wav, key):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "gemini-2.5-flash-preview-tts:generateContent?key=" + key)
    body = {"contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"response_modalities": ["AUDIO"],
                                 "speech_config": {"voice_config": {
                                     "prebuilt_voice_config": {"voice_name": voice}}}}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    pcm = base64.b64decode(data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
    raw = out_wav.with_suffix(".raw")
    raw.write_bytes(pcm)
    run([get_ff(), "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", raw,
         "-ar", "44100", "-ac", "2", out_wav])
    raw.unlink()

def silence(out_wav, secs):
    run([get_ff(), "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", f"{secs:.2f}", out_wav])

# ------------------------------------------------------- soundtrack (free, synthesized)
MUSIC = ASSETS / "audio" / "music_bed.wav"
DING = ASSETS / "audio" / "ding.wav"
TADA = ASSETS / "audio" / "tada.wav"

def music_only(out_wav, secs):
    if not MUSIC.exists():
        return silence(out_wav, secs)
    run([get_ff(), "-y", "-t", f"{secs:.2f}", "-i", MUSIC, "-af",
         f"volume=0.6,afade=t=out:st={max(0.0, secs - 0.6):.2f}:d=0.6",
         "-ar", "44100", "-ac", "2", out_wav])

def mix_scene_audio(voice, out_wav, secs, sfx=None):
    """Voice + gentle music bed (+ ding/tada). Falls back to bare voice."""
    if not MUSIC.exists():
        run([get_ff(), "-y", "-i", voice, "-ar", "44100", "-ac", "2", out_wav])
        return
    inputs = ["-i", voice, "-t", f"{secs:.2f}", "-i", MUSIC]
    fc = "[1:a]volume=0.16[m]"
    if sfx and Path(sfx).exists():
        inputs += ["-i", sfx]
        fc += (";[2:a]adelay=350|350,volume=0.6[s];"
               "[0:a][m][s]amix=inputs=3:duration=first:normalize=0[aout]")
    else:
        fc += ";[0:a][m]amix=inputs=2:duration=first:normalize=0[aout]"
    run([get_ff(), "-y", *inputs, "-filter_complex", fc, "-map", "[aout]",
         "-ar", "44100", "-ac", "2", out_wav])

# ------------------------------------------------------------------ puppets
def bands(proj, thr):
    on = proj > thr
    out, start = [], None
    for i, v in enumerate(on):
        if v and start is None:
            start = i
        if not v and start is not None:
            if i - start > 10:
                out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(on)))
    return out

def cut_cell(pil, box, bg):
    """Cut one portrait out of the sheet with clean alpha (hole-filled)."""
    x0, y0, x1, y1 = box
    sub = np.asarray(pil.crop(box)).astype(int)
    keep = np.abs(sub - bg).sum(2) > 40
    removed = ~keep
    h, w = removed.shape
    seen = np.zeros_like(removed)
    from collections import deque
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            if removed[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if removed[y, x] and not seen[y, x]:
                seen[y, x] = True
                dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and removed[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                dq.append((ny, nx))
    keep |= removed & ~seen
    k = keep.copy()
    k[1:, :] &= keep[:-1, :]
    k[:-1, :] &= keep[1:, :]
    k[:, 1:] &= keep[:, :-1]
    k[:, :-1] &= keep[:, 1:]
    keep = k
    ys, xs = np.where(keep)
    if len(ys) == 0:
        return None
    crop = pil.crop((x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1))
    alpha = Image.fromarray((keep[ys.min():ys.max() + 1, xs.min():xs.max() + 1] * 255).astype("uint8"))
    crop.putalpha(alpha)
    return crop

def extract_rows(path):
    im = np.asarray(Image.open(path).convert("RGB")).astype(int)
    bg = im[2, 2]
    mask = (np.abs(im - bg).sum(2) > 40)
    pil = Image.open(path).convert("RGB")
    width = im.shape[1]
    rows = []
    for (y0, y1) in bands(mask.sum(1), width * 0.02):
        cols = bands(mask[y0:y1].sum(0), im.shape[0] * 0.01)
        if len(cols) != 6:
            # paws/ears can bridge the gaps between portraits; the sheet is a
            # uniform 6-across grid, so fall back to equal columns
            cols = [(i * width // 6, (i + 1) * width // 6) for i in range(6)]
        cells = [c for c in (cut_cell(pil, (x0, y0, x1, y1), bg) for (x0, x1) in cols) if c]
        if cells:
            rows.append(cells)
    return rows

PUPPETS = {}
def load_puppet(spk):
    """Returns (closed[6], open[6]) head images, scaled to 560px tall."""
    if spk in PUPPETS:
        return PUPPETS[spk]
    cfg = SPEAKERS[spk]
    path = cfg["sheet"] if Path(cfg["sheet"]).exists() else cfg["fallback_sheet"]
    rows = extract_rows(path)
    if len(rows) >= 2 and len(rows[0]) >= 6 and len(rows[1]) >= 6:
        closed, opn = rows[0][:6], rows[1][:6]
    else:  # old-style sheet: no mouth pairs, bob only
        closed = rows[0][:6]
        opn = closed
    def scale(imgs):
        out = []
        for im in imgs:
            h = 560
            w = int(im.width * h / im.height)
            out.append(im.resize((w, h), Image.LANCZOS))
        return out
    PUPPETS[spk] = (scale(closed), scale(opn))
    return PUPPETS[spk]

def pair_for(spk, expr):
    closed, opn = load_puppet(spk)
    idx = EXPRESSIONS.index(expr) if expr in EXPRESSIONS else 0
    idx = min(idx, len(closed) - 1)
    return closed[idx], opn[idx]

# ------------------------------------------------------------------ audio
def envelope(wav, nframes):
    """Normalised per-video-frame loudness of the wav (drives the mouth)."""
    import wave as _wave
    w = _wave.open(str(wav))
    rate, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
    a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64)
    if ch == 2:
        a = a[0::2]
    spf = max(1, rate // FPS)
    need = nframes * spf
    if len(a) < need:
        a = np.concatenate([a, np.zeros(need - len(a))])
    rms = np.sqrt((a[:need].reshape(nframes, spf) ** 2).mean(1))
    mx = rms.max() or 1.0
    e = rms / mx
    e = np.convolve(e, np.array([0.4, 0.6]), mode="same")
    return e

# ------------------------------------------------------------------ drawing
def load_en_font():
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(p).exists():
            return p
    return None

def scene_base(scene, ep):
    """Static layer: background + word card + badge + subtitle band."""
    bgp = ASSETS / "backgrounds" / f"{scene.get('bg', 'classroom')}.png"
    if not bgp.exists():
        bgp = ASSETS / "backgrounds" / "classroom.png"
    bg = Image.open(bgp).convert("RGB")
    canvas = bg.resize((W, H))
    draw = ImageDraw.Draw(canvas, "RGBA")
    en_bold = load_en_font()
    if scene.get("word"):
        f = ImageFont.truetype(en_bold, 110) if en_bold else ImageFont.load_default()
        txt = scene["word"].upper()
        l, t, r, b = draw.textbbox((0, 0), txt, font=f)
        tw, th = r - l, b - t
        draw.rounded_rectangle([W/2 - tw/2 - 40, 60, W/2 + tw/2 + 40, 60 + th + 50], 28,
                               fill=(255, 255, 255, 225), outline=(30, 30, 30, 255), width=5)
        draw.text((W/2 - tw/2 - l, 75 - t), txt, font=f, fill=(214, 40, 40))
    f = ImageFont.truetype(en_bold, 30) if en_bold else ImageFont.load_default()
    badge = f"MR LONG & RONNIE  •  EPISODE {ep}"
    draw.rounded_rectangle([20, 16, 20 + 640, 66], 22, fill=(0, 0, 0, 130))
    draw.text((36, 22), badge, font=f, fill=(255, 255, 255))
    draw.rectangle([0, H - 130, W, H], fill=(0, 0, 0, 150))
    return canvas

def card_base(kind, ep, title_en):
    canvas = Image.new("RGB", (W, H), (255, 208, 64) if kind == "title" else (96, 176, 255))
    draw = ImageDraw.Draw(canvas, "RGBA")
    en_bold = load_en_font()

    def big(text, y, size, fill):
        f = ImageFont.truetype(en_bold, size) if en_bold else ImageFont.load_default()
        l, t, r, b = draw.textbbox((0, 0), text, font=f)
        draw.text((W/2 - (r - l)/2 - l, y), text, font=f, fill=fill)
    if kind == "title":
        big("MR LONG & RONNIE", 130, 92, (214, 40, 40))
        big("LEARN ENGLISH!", 245, 66, (40, 40, 40))
        big(f"EPISODE {ep}: {title_en}", 360, 48, (40, 40, 40))
    else:
        big("WELL DONE!", 160, 92, (255, 255, 255))
        big("SEE YOU TOMORROW!", 300, 60, (255, 255, 255))
        big("SUBSCRIBE FOR DAILY ENGLISH", 410, 36, (30, 30, 90))
    return canvas

def v_scene_base(scene, ep):
    """Vertical 720x1280 first-frame for Shorts."""
    sw, sh = 720, 1280
    bg = Image.open(ASSETS / "backgrounds" / f"{scene.get('bg', 'classroom')}.png").convert("RGB")
    r = max(sw / bg.width, sh / bg.height)
    bg = bg.resize((int(bg.width * r), int(bg.height * r)))
    l = (bg.width - sw) // 2
    t = (bg.height - sh) // 2
    canvas = bg.crop((l, t, l + sw, t + sh))
    draw = ImageDraw.Draw(canvas, "RGBA")
    en_bold = load_en_font()
    if scene.get("word"):
        f = ImageFont.truetype(en_bold, 84) if en_bold else ImageFont.load_default()
        txt = scene["word"].upper()
        l0, t0, r0, b0 = draw.textbbox((0, 0), txt, font=f)
        tw, th = r0 - l0, b0 - t0
        draw.rounded_rectangle([sw/2 - tw/2 - 30, 70, sw/2 + tw/2 + 30, 70 + th + 44], 24,
                               fill=(255, 255, 255, 235), outline=(30, 30, 30, 255), width=5)
        draw.text((sw/2 - tw/2 - l0, 82 - t0), txt, font=f, fill=(214, 40, 40))
    f = ImageFont.truetype(en_bold, 26) if en_bold else ImageFont.load_default()
    draw.rounded_rectangle([16, 14, 470, 58], 20, fill=(0, 0, 0, 130))
    draw.text((28, 20), f"MR LONG & RONNIE • EP {ep}", font=f, fill=(255, 255, 255))
    draw.rectangle([0, sh - 190, sw, sh], fill=(0, 0, 0, 160))
    return canvas

def build_short(story, ep, wavs, use_ass):
    """A vertical #Shorts cut: word scenes + goodbye, ~30 s, same locked art."""
    sw, sh = 720, 1280
    word_idxs = [i for i, sc in enumerate(story["scenes"], 1) if sc.get("word")]
    sel = word_idxs[:4]
    if story["scenes"]:
        sel.append(len(story["scenes"]))
    parts = []
    for n, i in enumerate(sel):
        sc = story["scenes"][i - 1]
        wav = wavs[i]
        d = duration(wav) + 0.3
        base = v_scene_base(sc, ep)
        s = sc["speaker"]
        c, o = pair_for(s, sc.get("expr", "happy"))

        def tall(img):
            h = 860
            w = int(img.width * h / img.height)
            return img.resize((w, h), Image.LANCZOS)
        actors = [{"spk": s, "closed": tall(c), "open": tall(o), "talks": True, "cx": sw // 2}]
        ass = OUT / f"_vs{n}.ass"
        lines = [("EN", sc["en"])]
        if sc.get("km"):
            lines.append(("KM", sc["km"]))
        write_ass(ass, lines, d, sw, sh)
        out = OUT / f"_vs{n}.mp4"
        animate_video(base, actors, wav, int(d * FPS), ass, out, use_ass, width=sw, height=sh)
        parts.append(out)
    lst = OUT / "_vlist.txt"
    lst.write_text("\n".join(f"file '{p.name}'" for p in parts))
    run([get_ff(), "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
         OUT / f"episode-{ep:03d}_short.mp4"])
    first_word = story["scenes"][sel[0] - 1].get("word", "English") if sel else "English"
    (OUT / f"episode-{ep:03d}_short.description.txt").write_text(
        f"Mr Long & Ronnie teach '{first_word}' in 30 seconds! "
        f"English for Khmer kids. #Shorts #LearnEnglish #KhmerKids #EnglishForKids")
    print(f"  + short -> episode-{ep:03d}_short.mp4")

def render_thumbnail(story, ep):
    """Click-worthy 1280x720 thumbnail: both dogs + the episode's first word."""
    arr = np.zeros((720, 1280, 3), dtype=np.uint8)
    for y in range(720):
        arr[y, :] = (255, max(0, 205 - int(90 * y / 720)), 0)
    canvas = Image.fromarray(arr)
    draw = ImageDraw.Draw(canvas, "RGBA")
    en = load_en_font()
    for spk, x in [("mr_long", 30), ("ronnie", 1280 - 500)]:
        _, o = pair_for(spk, "happy")
        im = o.resize((470, 470), Image.LANCZOS)
        canvas.paste(im, (x, 720 - 480), im)
    word = next((sc.get("word") for sc in story["scenes"] if sc.get("word")), "ENGLISH")
    f = ImageFont.truetype(en, 140) if en else ImageFont.load_default()
    txt = word.upper()
    l, t, r, b = draw.textbbox((0, 0), txt, font=f)
    tw = r - l
    draw.text((640 - tw / 2 - l, 120 - t), txt, font=f, fill=(255, 255, 255),
              stroke_width=10, stroke_fill=(200, 30, 30))
    f2 = ImageFont.truetype(en, 44) if en else ImageFont.load_default()
    draw.rounded_rectangle([30, 30, 300, 96], 26, fill=(200, 30, 30, 235))
    draw.text((52, 38), f"EPISODE {ep}", font=f2, fill=(255, 255, 255))
    canvas.save(OUT / f"episode-{ep:03d}.thumbnail.png")
    print(f"  + thumbnail -> episode-{ep:03d}.thumbnail.png")

def draw_actor(canvas, img, cx, t, talking, energy, height=H):
    """Paste one puppet with bob / tilt / breath so it feels alive."""
    bob = (7 if talking else 3) * math.sin(2 * math.pi * (2.1 if talking else 0.55) * t)
    rot = (2.6 if talking else 0.9) * math.sin(2 * math.pi * (1.4 if talking else 0.22) * t + cx)
    sc = 1.03 if talking and energy > 0.45 else 1.0
    im = img
    if sc != 1.0:
        im = img.resize((int(img.width * sc), int(img.height * sc)), Image.LANCZOS)
    if abs(rot) > 0.05:
        im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    x = int(cx - im.width / 2)
    y = int(height - 20 - im.height + bob)
    canvas.paste(im, (x, y), im)

def actor_cx(spk):
    closed, _ = load_puppet(spk)
    w = closed[0].width
    return 60 + w / 2 if SPEAKERS[spk]["side"] == "left" else W - 60 - w / 2

# ------------------------------------------------------------------ render
def animate_video(base, actors, wav, nframes, ass, out_mp4, use_ass, width=W, height=H, env_wav=None):
    """actors: list of dicts(spk, closed, open, talks). Streams raw frames to ffmpeg."""
    env = envelope(env_wav or wav, nframes) if any(a["talks"] for a in actors) else np.zeros(nframes)
    vf = "null"
    if use_ass and ass:
        vf = f"subtitles=filename={ass}:fontsdir={FONTSDIR}"
    cmd = [get_ff(), "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-s", f"{width}x{height}",
           "-pix_fmt", "rgb24", "-r", str(FPS), "-i", "-", "-i", wav,
           "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-ar", "44100", "-ac", "2", out_mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    mouth = {}
    try:
        for i in range(nframes):
            t = i / FPS
            canvas = base.copy()
            for a in actors:
                e = env[i] if a["talks"] else 0.0
                if a["talks"]:  # hysteresis so the mouth doesn't buzz
                    prev = mouth.get(a["spk"], False)
                    mouth[a["spk"]] = e > 0.22 if not prev else e >= 0.12
                img = a["open"] if (a["talks"] and mouth.get(a["spk"]) and e > 0.10) else a["closed"]
                draw_actor(canvas, img, a["cx"], t, a["talks"] and e > 0.10, e, height)
            proc.stdin.write(canvas.tobytes())
    except BrokenPipeError:
        proc.stdin.close()
        raise RuntimeError("ffmpeg died: " + proc.stderr.read().decode()[-2000:])
    proc.stdin.close()
    err = proc.stderr.read()
    if proc.wait() != 0:
        raise RuntimeError(err.decode()[-2000:])

def clip_video(clip, wav, ass, out_mp4, use_ass, secs):
    """Use a pre-generated AI clip (any free web tool) as the scene visual."""
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS}")
    if use_ass and ass:
        vf += f",subtitles=filename={ass}:fontsdir={FONTSDIR}"
    cmd = [get_ff(), "-y", "-stream_loop", "-1", "-i", clip, "-i", wav,
           "-t", f"{secs:.2f}", "-vf", vf, "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-ar", "44100", "-ac", "2", out_mp4]
    run(cmd)

def write_ass(out_ass, lines, secs, width=W, height=H):
    en_sz = 44 if width < 1000 else 54
    km_sz = 38 if width < 1000 else 46
    end = f"0:00:{secs:05.2f}"
    ev = [f"Dialogue: 0,0:00:00.00,{end},{style},,0,0,0,,{text}" for style, text in lines]
    out_ass.write_text(
        f"[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: EN,DejaVu Sans,{en_sz},&H00FFFFFF,&H000000FF,&H00000000,&HC0000000,-1,0,0,0,"
        "100,100,0,0,1,3,1,2,30,30,78,1\n"
        f"Style: KM,Noto Sans Khmer,{km_sz},&H003BEBFF,&H000000FF,&H00000000,&HC0000000,-1,0,0,0,"
        "100,100,0,0,1,3,1,2,30,30,18,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        + "\n".join(ev) + "\n")

def ts(s):
    h, m = int(s // 3600), int(s % 3600 // 60)
    return f"{h:02d}:{m:02d}:{s % 60:06.3f}".replace(".", ",")

# ------------------------------------------------------------------ build
def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    OUT.mkdir(exist_ok=True)
    if arg and Path(arg).exists():
        story = json.load(open(arg))
        if isinstance(story, list):  # curriculum.json passed directly: use today's (or --ep) entry
            story = auto_storyboard()
    else:
        story = auto_storyboard()
        sb = ROOT / "episodes" / f"episode-{int(story.get('episode', 1)):03d}.json"
        if sb.exists():  # hand-written storyboard overrides the template
            story = json.load(open(sb))
    ep = int(story.get("episode", 1))
    use_ass = has_subtitles_filter()
    parts, srt, cur = [], [], 0.0
    wavs = {}

    def render_part(idx, base, actors, wav, ass_lines, secs, clip=None, env_wav=None):
        nonlocal cur
        ass = None
        if ass_lines:
            ass = OUT / f"_a{idx}.ass"
            write_ass(ass, ass_lines, secs)
        out = OUT / f"_p{idx}.mp4"
        if clip is not None:
            clip_video(clip, wav, ass, out, use_ass, secs)
        else:
            nframes = int(secs * FPS)
            animate_video(base, actors, wav, nframes, ass, out, use_ass, env_wav=env_wav)
        parts.append(out)
        return secs

    # title card
    tw = OUT / "_c0.wav"
    music_only(tw, 2.6)
    d = duration(tw)
    actors = [{"spk": s, "closed": pair_for(s, "happy")[0], "open": pair_for(s, "happy")[1],
               "talks": False, "cx": actor_cx(s)} for s in ("mr_long", "ronnie")]
    lines = []
    if story.get("title_en"):
        lines.append(("EN", story["title_en"]))
    if story.get("title_km"):
        lines.append(("KM", story["title_km"]))
    render_part("000", card_base("title", ep, story.get("title_en", "")), actors, tw, lines, d)
    cur += d

    for i, sc in enumerate(story["scenes"], 1):
        wav = OUT / f"_s{i}.wav"
        tts(sc["en"], sc["speaker"], wav)
        d = duration(wav) + 0.35 + sc.get("pause", 0.0)
        mixed = OUT / f"_m{i}.wav"
        sfx = DING if sc.get("word") else (TADA if sc.get("expr") == "proud" else None)
        mix_scene_audio(wav, mixed, d, sfx)
        wavs[i] = mixed
        base = scene_base(sc, ep)
        speakers = [sc["speaker"]] if sc["speaker"] != "both" else ["mr_long", "ronnie"]
        actors = []
        for s in ("mr_long", "ronnie"):
            if s not in speakers:
                continue
            c, o = pair_for(s, sc.get("expr", "happy"))
            actors.append({"spk": s, "closed": c, "open": o, "talks": s == sc["speaker"] or sc["speaker"] == "both", "cx": actor_cx(s)})
        lines = [("EN", sc["en"])]
        if sc.get("km"):
            lines.append(("KM", sc["km"]))
        clip = OUT / "ai_clips" / f"scene-{i:02d}.mp4"
        render_part(f"{i:03d}", base, actors, mixed, lines, d,
                    clip=clip if clip.exists() else None, env_wav=wav)
        srt.append((cur, cur + d, f"{sc['en']}\n{sc.get('km', '')}"))
        cur += d

    # end card
    ew = OUT / "_c9.wav"
    music_only(ew, 3.0)
    d = duration(ew)
    actors = [{"spk": s, "closed": pair_for(s, "proud")[0], "open": pair_for(s, "proud")[1],
               "talks": False, "cx": actor_cx(s)} for s in ("mr_long", "ronnie")]
    render_part("999", card_base("end", ep, ""), actors, ew, None, d)

    lst = OUT / "_list.txt"
    lst.write_text("\n".join(f"file '{p.name}'" for p in parts))
    final = OUT / f"episode-{ep:03d}.mp4"
    run([get_ff(), "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", final])

    with open(OUT / f"episode-{ep:03d}.srt", "w") as f:
        for n, (a, b, txt) in enumerate(srt, 1):
            f.write(f"{n}\n{ts(a)} --> {ts(b)}\n{txt}\n\n")
    title = (f"{story.get('title_en', '')} | Learn English for Khmer Kids - "
             f"Mr Long & Ronnie Episode {ep}")
    desc = (title + "\n" + story.get("title_km", "") +
            "\nLearn English words with Mr Long the Border Collie and Ronnie the "
            "Chihuahua! English vocabulary for children in Cambodia, with Khmer "
            "subtitles. New episode every day! "
            "#LearnEnglish #KhmerKids #MrLongAndRonnie #EnglishForKids #Cambodia")
    (OUT / f"episode-{ep:03d}.description.txt").write_text(desc)
    (OUT / f"episode-{ep:03d}.title.txt").write_text(title)
    try:
        render_thumbnail(story, ep)
    except Exception as e:
        print("thumbnail failed:", e)
    try:
        build_short(story, ep, wavs, use_ass)
    except Exception as e:
        print("short failed:", e)
    print(f"OK -> {final}  ({cur:.0f}s, {len(story['scenes'])} scenes)")

def auto_storyboard():
    """Pick today's episode: curriculum first, then episodes.json, else word bank."""
    from datetime import date
    day = max(0, (date.today() - date(2026, 9, 10)).days)
    # optional override: python make_episode.py episodes/curriculum.json 7  -> episode 7
    ep = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else day + 1
    day = ep - 1
    cur_path = ROOT / "episodes" / "curriculum.json"
    if cur_path.exists():
        for item in json.load(open(cur_path)):
            if int(item.get("episode", -1)) == ep:
                return build_curriculum(item)
    lst_path = ROOT / "episodes" / "episodes.json"
    if lst_path.exists():
        lst = json.load(open(lst_path))
        item = lst[day % len(lst)]
        ep = int(item.get("episode", day + 1))
        words = item.get("words", [])
        w1 = (words[0]["en"], words[0]["km"]) if words else WORD_BANK[day % len(WORD_BANK)]
        w2 = (words[1]["en"], words[1]["km"]) if len(words) > 1 else w1
        st = template(ep, w1, w2)
        st["title_en"] = item.get("title_en", st["title_en"])
        st["title_km"] = item.get("title_km", st["title_km"])
        return st
    w1 = WORD_BANK[(day * 2) % len(WORD_BANK)]
    w2 = WORD_BANK[(day * 2 + 1) % len(WORD_BANK)]
    return template(day + 1, w1, w2)

def template(ep, w1, w2):
    e1, k1 = w1
    e2, k2 = w2
    S = []
    def add(sp, en, km, ex="happy", bg="classroom", word=None, pause=0.0):
        S.append({"speaker": sp, "en": en, "km": km, "expr": ex, "bg": bg,
                  **({"word": word} if word else {}), **({"pause": pause} if pause else {})})
    add("mr_long", "Hello everyone! I am Mr Long!", "សួស្ដីអ្នកទាំងអស់គ្នា! ខ្ញុំ្មោះ មីស្ទើរ ឡុង!")
    add("ronnie", "Hi hi hi! I am Ronnie! Let's learn English!", "សួស្ដី! ខ្ញុំឈ្មោះ រ៉ូនី! តោះរៀនភាសាអង់គ្លេស!", "happy", "park")
    add("mr_long", f"Today's first word is: {e1}. {e1}!", f"ពាក្យទីមួយថ្ងៃនេះគឺ {k1}!", "pointing", "classroom", e1)
    add("ronnie", f"{e1.capitalize()}! I can say {e1}!", f"{k1}! ខ្ញុំអាចនិយាយថា {e1}!", "surprised", "park", e1)
    add("mr_long", pick(REP), "និយាយតាមខ្ញុំ! និយាយឲយខលាំង!", "proud")
    add("ronnie", f"{e1.capitalize()}! Yes! I got it!", f"{k1}! បាទ! ខ្ញុំចេះហើយ!", "proud", "park")
    add("mr_long", f"Our second word is: {e2}. {e2}!", f"ពាក្យទីពីរគឺ {k2}!", "pointing", "classroom", e2)
    add("ronnie", f"{e2.capitalize()}! {e2.capitalize()}! That is easy!", f"{k2}! ងាយស្រួលណាស់!", "happy", "park", e2)
    add("mr_long", pick(QUIZ).format(w=e1), "ពេលសំណួរ! " + k1 + " នៅឯណា? ចង្អុលវា!", "thinking", "classroom", e1, pause=1.5)
    add("ronnie", "There! The " + e1 + "! Did I win?", "នោះហើយ! " + k1 + "! តើខ្ញុំឈ្នះទេ?", "pointing", "park", e1)
    add("mr_long", pick(PRAISE), "បាទហើយ រ៉ូនី! ពូកែណាស់អ្នកទាំងអស់គ្នា!", "proud")
    add("ronnie", pick(BYE), "ជួបគ្នាថ្ងៃស្អែក! លាហើយ!", "happy", "park")
    return {"episode": ep, "title_en": f"{e1.capitalize()} and {e2.capitalize()}",
            "title_km": f"{k1} និង {k2}", "scenes": S}

if __name__ == "__main__":
    main()
