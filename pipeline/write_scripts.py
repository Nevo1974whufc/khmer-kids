#!/usr/bin/env python3
"""
Batch-write episode storyboards with your LOCAL Ollama model (Pinokio setup).

Runs on YOUR machine (where Pinokio/Ollama live), e.g. once a week:
    python3 pipeline/write_scripts.py --count 7            # next 7 episodes
    python3 pipeline/write_scripts.py --count 30 --model qwen2.5:14b
    OLLAMA_HOST=http://192.168.1.5:11434 python3 pipeline/write_scripts.py

Writes episodes/episode-NNN.json which the daily GitHub Actions render picks up
automatically (hand-written storyboards override the template).
If Ollama is unreachable it falls back to the built-in template, so it can
never break your pipeline.

Tip: commit the generated files and `git push` — then the cloud renders them
while your PC sleeps. Or run make_episode.py locally for a 100% offline setup.
"""
import argparse, json, os, re, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_episode as me

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

def ollama_available():
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False

def extract_json(text):
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if m:
        return json.loads(m.group(1))
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in model reply")
    return json.loads(m.group(0))

def clean_storyboard(obj, ep):
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    scenes = []
    for sc in obj.get("scenes", []):
        if not isinstance(sc, dict):
            continue
        sp = sc.get("speaker")
        en = sc.get("en")
        if sp not in ("mr_long", "ronnie", "both") or not en:
            continue
        bg = sc.get("bg") if sc.get("bg") in ("classroom", "park") else "classroom"
        ex = sc.get("expr") if sc.get("expr") in me.EXPRESSIONS else "happy"
        d = {"speaker": sp, "en": str(en), "km": str(sc.get("km", "")),
             "expr": ex, "bg": bg}
        if sc.get("word"):
            d["word"] = str(sc["word"])
        if sc.get("pause"):
            d["pause"] = float(sc["pause"])
        scenes.append(d)
    if len(scenes) < 6:
        raise ValueError(f"only {len(scenes)} usable scenes")
    return {"episode": ep, "title_en": str(obj.get("title_en", f"Episode {ep}")),
            "title_km": str(obj.get("title_km", "")), "scenes": scenes}

def qwen_storyboard(ep, w1, w2, model):
    prompt = f"""You are the writer of a YouTube cartoon for Khmer children learning English.
Characters: Mr Long (Border Collie, kind teacher) and Ronnie (Chihuahua, excited student).
Write episode {ep} teaching the words "{w1[0]}" (Khmer: {w1[1]}) and "{w2[0]}" (Khmer: {w2[1]}).
Rules: 10-14 short scenes; both dogs speak; very simple English a child can repeat;
each scene's "km" is a natural short Khmer translation; start with greetings and end
with "See you tomorrow! Bye bye!"; include one quiz scene with "pause": 1.5.
Return ONLY strict JSON with this exact schema:
{{"episode": {ep}, "title_en": str, "title_km": str,
 "scenes": [{{"speaker": "mr_long"|"ronnie", "en": str, "km": str,
  "expr": "happy"|"surprised"|"thinking"|"pointing"|"proud"|"sleepy",
  "bg": "classroom"|"park", "word": str, "pause": 1.5}}]}}"""
    body = {"model": model, "prompt": prompt, "stream": False, "format": "json"}
    req = urllib.request.Request(OLLAMA + "/api/generate",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        data = json.load(r)
    return clean_storyboard(extract_json(data["response"]), ep)

def word_pair_for(ep):
    lst_path = me.ROOT / "episodes" / "episodes.json"
    if lst_path.exists():
        lst = json.load(open(lst_path))
        item = next((i for i in lst if int(i.get("episode", 0)) == ep), None)
        if item and item.get("words"):
            w = item["words"]
            return (w[0]["en"], w[0]["km"]), (w[1]["en"], w[1]["km"]) if len(w) > 1 else (w[0]["en"], w[0]["km"])
    a = me.WORD_BANK[(ep * 2) % len(me.WORD_BANK)]
    b = me.WORD_BANK[(ep * 2 + 1) % len(me.WORD_BANK)]
    return a, b

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=7)
    ap.add_argument("--start", type=int, default=None,
                    help="first episode number (default: highest existing + 1)")
    ap.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen2.5"))
    args = ap.parse_args()

    ep_dir = me.ROOT / "episodes"
    if args.start is None:
        existing = [int(p.stem.split("-")[1]) for p in ep_dir.glob("episode-*.json")]
        args.start = (max(existing) + 1) if existing else 1

    have_ollama = ollama_available()
    print(f"ollama at {OLLAMA}: {'ONLINE' if have_ollama else 'offline -> template fallback'}")
    for ep in range(args.start, args.start + args.count):
        w1, w2 = word_pair_for(ep)
        story = None
        if have_ollama:
            try:
                story = qwen_storyboard(ep, w1, w2, args.model)
                print(f"  ep {ep}: written by {args.model}")
            except Exception as e:
                print(f"  ep {ep}: qwen failed ({e}); using template")
        if story is None:
            story = me.template(ep, w1, w2)
        out = ep_dir / f"episode-{ep:03d}.json"
        out.write_text(json.dumps(story, ensure_ascii=False, indent=1))
    print("done")

if __name__ == "__main__":
    main()
