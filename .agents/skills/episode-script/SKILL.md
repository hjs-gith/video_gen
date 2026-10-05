---
name: episode-script
description: >-
  Generate or refine an episode's bilingual script.json for the AI Jargon Atlas
  video pipeline by chatting — before running stages 2 (images) and 3 (video).
  Use when the user wants to write, edit, review, or iterate on an episode script.
argument-hint: "[episode-number]"
allowed-tools: Read Edit Write Glob Grep Bash
---

# Authoring AI Jargon Atlas episode scripts

`script.json` is the creative heart of an episode: narration, scenes, on-screen
text, Atlas mascot poses, and visual intent all flow downstream from it. Stages 2
(images) and 3 (audio + video) read whatever is in `script.json` when they run. Use
this skill to write a script or refine an existing one *conversationally* until it's
right, then hand off to stage 2.

## Boundaries

- **Draft and edit the script by hand**, directly from the episode YAML and the
  rules below. Do **not** call the stage-1 OpenAI API (`atlas episode run N
  --stages 1`) — that defeats the purpose of crafting it together.
- Do **not** run stages 2 or 3 automatically. End by telling the user the next
  command.
- Preserve Korean text exactly (UTF-8); never machine-translate EN↔KO literally.

## 1. Locate the files

- **Input** (episode brief): `episodes_yaml/episode_<N-1>.yaml`. Filenames are
  0-indexed (`episode_10.yaml` is episode 11); the `episode_number` field inside is
  authoritative. Fields: `term(s)`, `tier`, `cluster`, `cluster_name`,
  `one_line_gist`, `metaphor_seed`, `example_scenario`, `target_length_sec`,
  `next_episode_teaser`.
- **Output**: `episodes/<slug>/script.json`, where `<slug>` is
  `c{cluster:02d}_e{episode:02d}_{term_slug}` — the first term lowercased with spaces
  and hyphens turned into `_` (e.g. `c03_e11_token`). Exact logic lives in
  `src/atlas_pipeline/utils.py:episode_dir` and `curriculum.py:EpisodeRecord.slug`.
- Quick orientation: `uv run atlas episode list` and `uv run atlas episode status N`.
- A complete real example to model: `episodes/c03_e11_token/script.json`. Read it
  before drafting your first script.

## 2. Workflow

1. Read the episode YAML for this number.
2. If `script.json` exists, read it; otherwise plan a new one.
3. Propose narration, scene breakdown, on-screen text, Atlas poses, and visual
   intent. Show focused diffs and iterate with the user, one beat/scene at a time.
4. Write the file with UTF-8 and `ensure_ascii=false`, 2-space indent (matches
   `utils.save_json`). When editing an existing file, change only the fields in play.
5. Validate (section 5) and report any issues.
6. Tell the user the next step: `uv run atlas episode run N --stages 2`.

## 3. Schema

Top level: `{ "meta": {...}, "scenes": [...], "quality_checks": {...} }`.

`meta`:
- `term`, `tier` ("1" | "2" | "2.5" | "2.7" | "3"), `cluster`, `episode_in_cluster`
  (e.g. "3.11")
- `target_length_sec`, `actual_length_sec` (your estimate of the written length)
- `english_word_count`, `korean_syllable_count` (pacing references)
- `scene_count`
- `one_sentence_pitch_en` / `_ko`, `sticky_takeaway_en` (≤12 words) / `_ko`
- `next_episode_teaser_en` / `_ko` (optional)

`scenes[]` — each entry is ONE visual on screen, in order:
- `scene_id`: "S01", "S02", … (sequential; used for image/audio filenames)
- `beat`: `HOOK | DEFINITION | METAPHOR | CONCRETE_EXAMPLE | WHY_IT_MATTERS | STICKY_TAKEAWAY`
- `start_sec`, `end_sec`, `duration_sec`: **planning references only** — actual TTS
  audio length wins downstream, so keep them roughly coherent but don't obsess.
- `narration`: `{ "en": "...", "ko": "..." }` (spoken; also the caption text)
- `on_screen_text`: `{ "en": "≤7 words", "ko": "...", "position": "center | upper-third | lower-third" }`
- `atlas_in_scene`: boolean
- `atlas_pose`: one of `neutral | thinking | working | error | happy | pointing`
  when `atlas_in_scene` is true; `null` otherwise
- `visual_intent`: 1–3 plain-language sentences describing what to show

`quality_checks`: booleans you self-assess (`word_count_within_tolerance`,
`no_unexplained_jargon`, `metaphor_is_visualizable`,
`korean_sounds_natural_not_translated`, `sticky_takeaway_is_quotable`,
`all_visual_intents_are_concrete`).

## 4. Editorial rules

**Beat structure** (every episode, in order): HOOK (3–5s) → DEFINITION (5–8s) →
METAPHOR (10–15s) → CONCRETE_EXAMPLE (10–20s) → WHY_IT_MATTERS (5–10s) →
STICKY_TAKEAWAY (3–5s). Each beat may span 1–3 scenes; a 60s video is typically
10–14 scenes, each a unit of *visual* change (3–8s).

**Pacing**: EN ~150 words/min, KO ~290 syllables/min. Total within 30–90s and within
±10% of `target_length_sec`.

**Voice**: warm, smart-friend, second person ("you"). Never explain jargon with more
jargon (or define it in ≤5 words). Korean uses 존댓말 with natural spoken rhythm — write
it natively, not as a literal translation of the English. One mild moment of wit per
video; no forced jokes.

**Cluster awareness**: if earlier episodes in the cluster are known, you may reference
their terms without re-explaining ("remember the context window?"). If a
`next_episode_teaser` exists, end with a hook into it.

**On-screen text**: reinforces KEYWORDS only — never duplicates the narration. ≤7
words per card; each needs ≥2s on screen.

**visual_intent**: describe subjects, action, composition, mood in plain language an
artist could draw. Say what is SHOWN, not how to prompt an image model.

**Atlas (the mascot)**: a small floating pixel-art robot with a CRT-monitor head; it
emotes through its screen face and pose. Six poses: `neutral, thinking, working,
error, happy, pointing`. Decide **per scene** whether Atlas appears:
- Needs an actor (someone reacting, demonstrating, driving the metaphor) →
  `atlas_in_scene: true`, with Atlas as the integrated participant (never a human
  stand-in). Pick the pose that fits the moment.
- Pure explanation (a diagram, text breaking into tiles, a chart) → `atlas_in_scene:
  false`, `atlas_pose: null`, show only the explanatory pixel-art.

## 5. What each field feeds

- `narration` → what you HEAR (TTS) and the on-screen captions.
- `on_screen_text` → the short headline baked INTO the slide image (stage 2);
  independent of the caption language.
- `atlas_in_scene` / `atlas_pose` → whether the mascot appears and how.
- `visual_intent` → the scene illustration (stage 2 builds the image prompt from it).

## 6. Validate

Run the project validator (works offline, no API keys):

```
uv run python -c "import json,sys; from atlas_pipeline.utils import validate_script; e=validate_script(json.load(open(sys.argv[1]))); print('\n'.join('• '+x for x in e) or 'OK')" episodes/<slug>/script.json
```

It flags: no scenes, `actual_length_sec` outside 30–90, missing `visual_intent`,
missing `narration.en`/`.ko`, and an invalid/missing `atlas_pose` when
`atlas_in_scene` is true. Also check by hand: `scene_id`s sequential from S01;
`meta.scene_count` matches the array; recompute `actual_length_sec`,
`english_word_count`, and `korean_syllable_count` after edits.

## 7. Editing tips

- Adding/removing a scene → renumber every later `scene_id`, update
  `meta.scene_count`, and re-flow the `start_sec`/`end_sec`/`duration_sec` so they
  stay roughly continuous.
- Keep `meta` in sync with `scenes` after every change.
- Tweaking wording vs visuals are independent: edit `narration` to change what's
  heard/captioned, `on_screen_text` for the baked headline, `visual_intent`/
  `atlas_*` for the picture — then re-run only the stages affected.
