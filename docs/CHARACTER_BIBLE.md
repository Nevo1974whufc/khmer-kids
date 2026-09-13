# CHARACTER BIBLE — Mr Long & Ronnie

**The golden rule: the dogs are drawn ONCE and reused forever.**
Episodes crop sprites from the locked sheets; no episode may regenerate a character.
Master reference (the approved look): `assets/characters/master_reference_dogs.jpg`.

Style of the whole show: high-budget CG family-film look — realistic detailed fur,
soft natural sunlight, warm friendly expressions (as in the master reference).

---

## MR LONG — Border Collie, the teacher

Locked look (no accessories — never add glasses, scarf, hat or collar):
- Adult Border Collie, black-and-white coat.
- Black covers both ears and surrounds both eyes; broad white blaze runs down the
  middle of the face; white muzzle; black nose.
- Big fluffy white ruff on the chest; black back; white front legs; fluffy tail with white tip.
- Warm amber-brown eyes; gentle, patient teacher smile.
- Semi-erect ears with tips folding forward.
- Personality: kind, encouraging, speaks slowly and clearly.

Voice: Gemini TTS `Sadaltager` (warm/knowledgeable). espeak fallback `-p 30 -s 145`.

Sprite sheet: `assets/characters/mr_long_sprites.png`
Expression order (reading order): happy, surprised, thinking, pointing, proud, sleepy.

Regeneration prompt (only if a sheet is ever lost — keep output side by side with the
master reference and reject anything that drifts):
> 3D animated family-film character, realistic fur, soft natural sunlight: adult Border
> Collie, black-and-white coat, black ears and eye patches, broad white facial blaze,
> white muzzle and chest ruff, amber-brown eyes, black nose, semi-erect folding ears,
> NO accessories. Six head-and-shoulders portraits on flat light-grey: happy, surprised,
> thinking paw-on-chin, explaining paw-raised, proud grin, sleepy yawning.

## RONNIE — Chihuahua, the student

Locked look:
- Tiny smooth-coat Chihuahua, fawn golden-tan with white chest, white belly,
  small white spot on the forehead, white muzzle.
- Huge upright pointed ears; big sparkling brown eyes; black nose.
- ONE accessory only: a thin simple dark-brown collar. Nothing else, ever.
- Happy open mouth, tongue often showing; tail curled up.
- Personality: excitable, curious, repeats words proudly, makes cute mistakes.

Voice: Gemini TTS `Puck` (cheerful). espeak fallback `-p 85 -s 175`.

Sprite sheet: `assets/characters/ronnie_sprites.png`
Expression order (reading order): happy, surprised, thinking, pointing, proud, sleepy.

Regeneration prompt:
> 3D animated family-film character, realistic short fur, soft natural sunlight: tiny
> smooth-coat Chihuahua, fawn coat, white chest and forehead spot, huge upright ears,
> brown eyes, thin dark-brown collar only. Six head-and-shoulders portraits on flat
> light-grey: happy tongue-out, surprised, thinking paw-on-chin, explaining paw-raised,
> proud grin, sleepy yawning.

---

## Sets
- `assets/backgrounds/classroom.png` — Mr Long's teaching scenes.
- `assets/backgrounds/park.png` — Ronnie's scenes.
New sets may be added; characters may never be redrawn for a set.

## Animation system (why it moves but never changes)
- Each dog has a **talking sheet**: 6 expressions × 2 mouth states (closed / open),
  `*_talk.png`. The engine cuts them once and animates per frame:
  mouth flap driven by the audio waveform, head bob + tilt while talking,
  gentle breathing when idle. Same locked art in every episode, forever.
- If a talking sheet is ever missing, the pipeline falls back to the old
  expression sheet and bobs without mouth flaps — it never fails.

## Subtitles & type
- English line: DejaVu Sans Bold, white, bottom band.
- Khmer line: **Noto Sans Khmer** (bundled, OFL) in yellow, under the English.
- Khmer shaping rendered by libass (ffmpeg `subtitles` filter) — never by PIL.

## DO / DON'T
- DO reuse sprites; DO keep both dogs in every episode; DO end with "See you tomorrow".
- DON'T regenerate characters per episode; DON'T add clothes/accessories;
  DON'T change voices; DON'T switch art style between scenes.

## Adding a character later
Same pipeline: one locked sprite sheet (6 expressions), one voice, one `SPEAKERS`
entry, then `"speaker": "<name>"` in storyboards. Existing episodes never change.
