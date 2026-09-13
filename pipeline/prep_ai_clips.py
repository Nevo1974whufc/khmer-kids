#!/usr/bin/env python3
"""
Optional "real AI motion" booster (free, ~5 min of clicking, never required).

Free web video generators (Google Flow ~12 clips/day, Hailuo, Seedance) can turn
each scene's first frame into a truly animated clip — but they have no free API,
so they can't run inside the automatic pipeline. This script makes the manual
part a fast copy-paste loop:

  1. python3 pipeline/prep_ai_clips.py episodes/episode-001.json
       -> out/ai_frames/scene-NN.png  (exact first frames, dog already in place)
       -> out/ai_prompts.txt          (one copy-paste prompt per scene)
  2. In your free generator of choice: upload each frame, paste its prompt,
     download the clip, save it as out/ai_clips/scene-NN.mp4
  3. Run make_episode.py as usual: scenes with a clip use REAL AI MOTION,
     every other scene falls back to the built-in puppet animation.

Days you skip step 2, the show still renders fully automatic. Nothing breaks.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_episode as me

def main():
    if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
        story = json.load(open(sys.argv[1]))
    else:
        story = json.load(open(me.ROOT / "episodes" / "episode-001.json"))
    frames = me.OUT / "ai_frames"
    frames.mkdir(parents=True, exist_ok=True)
    (me.OUT / "ai_clips").mkdir(exist_ok=True)
    ep = int(story.get("episode", 1))
    prompts = []
    for i, sc in enumerate(story["scenes"], 1):
        base = me.scene_base(sc, ep)
        c, _ = me.pair_for(sc["speaker"], sc.get("expr", "happy"))
        me.draw_actor(base, c, me.actor_cx(sc["speaker"]), 0.0, False, 0.0)
        base.save(frames / f"scene-{i:02d}.png")
        who = ("Mr Long the black-and-white border collie"
               if sc["speaker"] == "mr_long"
               else "Ronnie the small tan chihuahua with the brown collar")
        prompts.append(
            f"scene-{i:02d}: upload scene-{i:02d}.png, prompt: \"3D children's cartoon, "
            f"{who} talking happily to camera, lips moving, gentle head bob and ear "
            f"movement, soft natural light, keep the exact same character and art style, "
            f"camera static\"")
    (me.OUT / "ai_prompts.txt").write_text("\n".join(prompts) + "\n")
    print(f"wrote {len(prompts)} first-frames to {frames}/")
    print("and prompts to out/ai_prompts.txt — drop finished clips into out/ai_clips/")

if __name__ == "__main__":
    main()
