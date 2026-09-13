# Mr Long & Ronnie — Learn English! (Khmer Kids)

A daily cartoon that teaches Khmer children English. **Fully automated, $0/month.**
Mr Long (Border Collie) teaches, Ronnie (Chihuahua) learns. Same dogs, same voices,
every single day — the art is locked and reused, never redrawn.

---

# START HERE — 3 one-time actions, then it runs forever

## ① Push this folder to GitHub (5 min)
In this folder:
```
git init
git remote add origin https://github.com/Nevo1974whufc/khmer-kids.git
git add -A && git commit -m "Mr Long & Ronnie auto pipeline"
git push -f origin main
```
(If your default branch is `master`, use that. Pushing overwrites the old broken
`publish.yml` — that's intended.)

## ② Add ONE secret for nice voices (2 min)
* Get a free key: https://aistudio.google.com/apikey
* GitHub → your repo → **Settings → Secrets and variables → Actions → New repository secret**
  Name: `GEMINI_API_KEY` Value: the key.
*(Skip it and the show still works with robotic offline voices.)*

## ③ Send Google the audit form — the switch that enables auto-publish (5 min + wait)
Google locks API uploads to *private* until your project passes a **free** compliance
audit. Open https://support.google.com/youtube/contact/yt_api_form and paste the
ready-made answers from **`docs/AUDIT_FORM_TEXT.md`** (copy-paste, nothing to write).
Approval usually takes days to a few weeks. You get an email.

---

# What happens automatically from now on

* **Every day 14:00 Cambodia time** GitHub Actions: picks the next episode from
  `episodes/episodes.json` (your list) → writes voices → renders the 720p video with
  English + Khmer subtitles → saves it as an **Artifact** on the run page.
* **While you wait for Google's email:** drag that artifact into YouTube Studio
  (30 s/day) — or just let them pile up and publish later.
* **The day the approval email arrives (2 min, one time):** on your PC run
  `scripts/setup_once.bat` (Windows) or `scripts/setup_once.sh`. It asks for two
  things, prints two values; paste them as repo secrets `YT_CLIENT_SECRET` and
  `YT_TOKEN_JSON`. **From the next day, publishing is automatic too. Done forever.**

Nothing else. No Pipedream needed. No paid anything. Your PC can be off.

---

# 📚 The curriculum — continuous episodes 2–54

`episodes/curriculum.json` holds 9 themed units of real Cambodian life, in order:
**Home & Daily Life** (laundry, cleaning, breakfast, bedtime) → **Market & Shopping**
(fruit stall, money, fish market) → **Food & Kitchen** → **Beach & Outdoors** →
**Siem Reap & Angkor** (Angkor Wat, Bayon's smiling faces, Ta Prohm's trees, Apsara
dance, Tonle Sap, tuk-tuk ride, sunrise, the Khmer Empire, Old Market) →
**Getting Around** → **Weather & Nature** → **School & Friends** →
**Festivals & Culture** (Khmer New Year, Pchum Ben, Water Festival, birthdays).

Each entry = scenario + 3 words (EN/KM) + one "magic phrase" (EN/KM). The engine
expands it into an ~18-scene adventure: arrive on location, phrase practice, word
teaching with word cards, a story beat ("How much is it?" at the market, "Splash!"
at the beach, "These stones are a thousand years old!" at Angkor), quiz, praise,
goodbye. Episode 26 (Angkor Wat) is rendered as the demo in `out/`.

**Extending the series:** append an entry with the next episode number (one minute
per episode). New location? Drop one background png into `assets/backgrounds/`
and add its name to `SCENARIO_BG` in the script.

# 💰 The money plan (rules verified Sept 2026)

**Getting paid at all:** YouTube Partner Program needs **1,000 subscribers +
4,000 public watch hours** (long-form only — Shorts feed views do NOT count
toward the hours) or **10M Shorts views in 90 days**. **Apply before
1 Feb 2027**: after that date new applicants need 8,000 hours / 20M Shorts views.

**What kids content earns:** made-for-kids = contextual ads only → **$1–3 RPM**
(vs $5–15 adult niches). ~100k views/month ≈ $100–300. No comments/end screens,
but custom thumbnails ARE allowed. Educational kids content earns at the better
end (parents co-watch); sponsors appear at 10k+ subs — that's the real money later.

**What the pipeline now ships EVERY day, automatically:**
1. the long-form episode (builds the 4,000 watch hours),
2. a vertical **#Shorts** cut (builds subscribers + the 10M-views backup path),
3. a bright click-worthy **thumbnail** (use it in Studio when publishing),
4. an SEO **title + bilingual description** with hashtags,
5. a **soundtrack**: synthesized royalty-free music bed under every scene, a "ding"
   on new words and a "tada" on praise (`assets/audio/` — $0, zero copyright risk).

**Staying monetizable under the "inauthentic content" policy:** YouTube bans
mass-produced templated uploads, not AI tools. Built-in defences: different words,
greetings, quiz lines and praise every episode (seeded per episode number), real
teaching value (vocabulary, quiz, Khmer translations), and — while you use Mode A —
**you glance at each episode before publishing**, which is the strongest possible
"human authorship" signal. No AI-disclosure label needed: clearly fantastical
cartoons are exempt from the synthetic-content label.

**Realistic timeline:** first 100 subs 1–3 months; 1,000 subs + 4,000 hours
typically 6–12 months with daily uploads; AdSense pays out once you pass $100.
First upgrade to buy with revenue: nothing — the stack is $0 by design. A GPU
later only if you want the optional AI-motion booster.

---

# Optional extras (ignore until curious)

* **REAL AI motion (the honest version).** I checked every route in Sept 2026:
  there is **no free video API that can run in an automatic pipeline** —
  HuggingFace's Wan routes to paid fal-ai, the Gemini API free tier lists Veo as
  unavailable, Google Flow/Veo free is web-only (~12 clips/day, watermarked), and
  local FramePack/Wan needs an RTX GPU. So: the pipeline animates the dogs itself
  by default (always on, $0). When you *want* full AI motion for an episode, run
  `python3 pipeline/prep_ai_clips.py` → it writes each scene's first frame plus a
  copy-paste prompt; spend ~5 min generating clips in any free web tool (Flow,
  Hailuo, Seedance); save them as `out/ai_clips/scene-NN.mp4`; the next render
  uses real AI video exactly there and puppets everywhere else. Skip it any day
  and nothing breaks.
* **Qwen/Pinokio scripts:** on your PC, `python pipeline/write_scripts.py --count 7`
  writes a week of scripts with your local Ollama; commit + push. Without it, the
  cloud writes scripts itself (Gemini) or uses the built-in template.
* **New character later:** add one sprite sheet + one entry in `SPEAKERS`
  (see `docs/CHARACTER_BIBLE.md`). Old episodes never change.
* **Change words/topics:** edit `episodes/episodes.json`. Full custom script for a
  day: drop an `episodes/episode-NNN.json` (see episode-001.json).

# Why the dogs never change
Episodes never regenerate characters — they crop from locked sprite sheets in
`assets/characters/`. Voices are fixed names in the code. `docs/CHARACTER_BIBLE.md`
holds the rules and the exact prompts, in case a sheet is ever lost.

# What I already tested
* Full render of episode 1 on a clean machine: 48 s video, 720p, EN+KM subs ✔
* **Dogs are animated, not static:** mouth flaps follow the actual voice waveform,
  plus head bob/tilt and idle breathing, every scene ✔ (frame-checked)
* **Revenue pack renders with every episode:** vertical #Shorts (15 s, 720×1280) ✔,
  thumbnail ✔, SEO title/description ✔ (all frame/file-checked)
* Qwen scriptwriter against a live (stubbed) Ollama ✔ and offline fallback ✔
* CI installs everything itself (ffmpeg, fonts, espeak) — nothing to install in the cloud ✔
