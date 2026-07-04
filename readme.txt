AI JARGON ATLAS — VIDEO PIPELINE
==================================

A pipeline for producing 50 short bilingual (EN+KR) educational videos
explaining AI jargon to non-developers. Each episode is 30–90 seconds,
features a pixel-art mascot named Atlas, and goes through three stages:
Script → Images → Video.


FIRST-TIME SETUP
----------------

1. Make sure your .env file has the three API keys:
     SCRIPT_API = 'sk-...'   (for script generation via gpt-5.4)
     IMAGE_API  = 'sk-...'   (for image generation via gpt-image-2)
     TTS_API    = 'sk-...'   (for voice generation via gpt-4o-mini-tts)

   Note: stages 1 and 2 (script + images) use the OpenAI APIs above. Stage 3
   voiceover defaults to a LOCAL, free TTS engine (Supertonic) and needs no key;
   the TTS_API key is only used if you opt into OpenAI TTS with --tts openai.

2. Install dependencies:
     uv sync

   This also pulls Supertonic (local TTS). On the first stage-3 run, its model
   files (~once) download into models/supertonic/ in this repo — not your global
   cache. Set SUPERTONIC_MODEL_DIR in .env to relocate them.

3. Generate the Atlas character Bible (one-time, ~$3):
     uv run atlas bible generate

   This copies plan_files/atlas_neutral.png into atlas/bible/ and uses
   it as a reference to generate 5 expression variants (thinking, working,
   error, happy, pointing) via the OpenAI Images API.

   After generation, review the quality check composite:
     atlas/bible/quality_check.png

   If it looks good, lock the Bible so it won't be accidentally regenerated:
     uv run atlas bible lock

   You only ever run this once. All episodes share these same reference images.


ADDING EPISODES
---------------

Each episode is a small YAML file in episodes_yaml/.
The filename is 0-indexed (episode_10.yaml = episode number 11).

Example: episodes_yaml/episode_10.yaml
  episode_number: 11
  cluster: 3
  cluster_name: "What AI Remembers & Knows"
  terms:
    - "Token"
  tier: "T2"
  one_line_gist: "The atomic unit of text that LLMs actually read and count."
  metaphor_seed: "words chopped into syllables"
  example_scenario: "ChatGPT hitting its context limit mid-conversation"
  target_length_sec: 60
  next_episode_teaser: "Context Window"

Tier values: T1 (everyday), T2 (workplace), T2.5 (capability),
             T2.7 (technical knob), T3 (big-picture)

See the curriculum in plan_files/ai_jargon_curriculum.md for all 50 terms.
Add episodes one at a time as you need them — no need to create all 50 upfront.

To see all available episodes:
  uv run atlas curriculum
  uv run atlas episode list


RUNNING AN EPISODE (full pipeline)
-----------------------------------

Replace 11 with your episode number.

  STAGE 1 — Script
  ----------------
  Preview the prompt (no API call):
    uv run atlas episode run 11 --stages 1 --dry-run

  Generate the bilingual JSON script:
    uv run atlas episode run 11 --stages 1

  Output: episodes/c03_e11_token/script.json

  Each scene carries bilingual narration, a short on-screen headline, an
  Atlas mascot flag/pose, and a visual_intent used to build the image prompt.
  See "THE SCRIPT (script.json)" below for the full field-by-field structure.

  You can manually edit script.json before running stage 2.
  Stages 2 and 3 read whatever is in script.json at the time they run.


  REFINING THE SCRIPT BY CHAT (optional, recommended)
  ---------------------------------------------------
  script.json is the creative heart of the episode — it's worth getting right
  before you spend on images and video. You can refine it conversationally with
  a coding agent instead of (or after) the stage-1 draft:

    - Claude Code:  run the /episode-script skill, e.g. "/episode-script 11"
                    or just ask it to tweak a scene for episode 11.
    - Codex / other: point the agent at AGENTS.md; it routes to the same
                    procedure.

  The skill (.claude/skills/episode-script/SKILL.md) teaches the agent the
  schema, the editorial rules (beats, pacing, bilingual voice, Atlas poses),
  and how to validate. It edits script.json directly — no API cost — then you
  run stage 2 when happy.


  STAGE 2 — Images
  ----------------
  Preview image prompts (no API call):
    uv run atlas episode run 11 --stages 2 --dry-run

  Generate images (2 frames per scene, ~$1.50 per episode):
    uv run atlas episode run 11 --stages 2

  Output: episodes/c03_e11_token/images/S01_a.png, S01_b.png, ...

  Each scene gets TWO frames: S01_a.png and S01_b.png. Frame B is generated as
  the SECOND CEL of a 2-frame pixel-art idle loop, edited from frame A: the whole
  image is hard-locked pixel-for-pixel (same composition, colors, and text) and
  exactly ONE element makes a tiny few-pixel micro-motion — for Atlas scenes a
  gentle float-bob + blink, otherwise a soft pulse on the single accent element.
  Naming one moving element (and forbidding all others) is what keeps the loop
  from reading as a glitch. BOTH frames are used — stage 3 alternates between them
  (~2 fps). They are NOT competing candidates to pick between.

  Every image is a cozy 16-bit pixel-art slide. Scenes the script marked
  atlas_in_scene=true include the Atlas mascot (rendered from the locked
  Bible references using the scene's atlas_pose); other scenes are pure
  pixel-art explainers with no character. The short on_screen_text headline
  is rendered directly INTO the image.

  Image size and quality (lower = faster and cheaper while iterating):
    --quality low|medium|high|auto   default: high
    --size WxH                       default: 1536x864 (16:9)
  Example — quick, cheap drafts while tuning prompts:
    uv run atlas episode run 11 --stages 2 --quality low

  Review the frames. If a scene came out awkward, re-roll BOTH of its frames:
    uv run atlas episode regen 11 S03

  (regen is shorthand for: episode run 11 --stages 2 --scene S03 --force)

  Image provider:
    --image-provider openai   gpt-image-2 — the default
    --image-provider local    your own local model behind an HTTP server (free)
  The default can also be set via IMAGE_PROVIDER in .env. The 'local' provider
  POSTs each prompt (plus any Atlas/frame reference images) to IMAGE_LOCAL_URL
  and writes back the PNG, so you can run your own FLUX.2 backend with no API
  cost; stages downstream don't care which provider made the frames. See the
  next section to stand one up.


  RUNNING YOUR OWN IMAGE BACKEND (FLUX.2, optional — wire up any time)
  -------------------------------------------------------------------
  The 'local' provider lets you swap gpt-image-2 for your own FLUX.2 generator
  running OUTSIDE this repo, at no API cost. Nothing in the pipeline changes —
  stage 2 just POSTs each prompt (plus any Atlas/frame reference images) to one
  HTTP endpoint and expects a PNG back. You can set this up later:

    1. Build/host a FLUX.2 [klein] generator outside this project. Two routes:
         - ComfyUI: load a FLUX.2 klein workflow, then run the small shim in
           docs/comfyui_local_image_server.md, which translates the pipeline's
           request into ComfyUI's /prompt + /upload/image + /view API.
         - Plain HTTP server: any server that loads FLUX.2 and implements the
           one-call contract in docs/local_image_server.md.
       FLUX.2 [klein] 4B is recommended: Apache-2.0, ~8GB VRAM, and one model
       covers text-to-image AND the Atlas/reference modes (unlike FLUX.1 dev,
       which is text-to-image only and needs FLUX.1 Kontext for references).

    2. Point the pipeline at it (in .env or your shell):
         IMAGE_PROVIDER=local
         IMAGE_LOCAL_URL=http://127.0.0.1:8000/generate

    3. Run stage 2 against your backend:
         uv run atlas episode run 11 --stages 2 --image-provider local

  The endpoint receives {prompt, width, height, reference_images[], steps} and
  returns a PNG. reference_images carries the locked Atlas Bible PNGs (mascot
  scenes) or frame A (when making frame B), base64-encoded; an empty list means
  plain text-to-image. Full contract, a GPU-free test stub, and the ComfyUI
  shim live in docs/local_image_server.md and docs/comfyui_local_image_server.md.


  STAGE 3 — Audio + Video
  -----------------------
  Generate TTS audio and assemble the video:
    uv run atlas episode run 11 --stages 3 --lang en --overlay ko

  This produces one MP4 with English voice and Korean captions. Each slide
  gently alternates between its two frames (~2 fps) for a subtle animation.

  TTS provider:
    --tts supertonic   local, on-device, FREE — the default (no API cost)
    --tts openai       OpenAI gpt-4o-mini-tts (may sound more natural; costs $)
  The default provider can also be set via TTS_PROVIDER in .env.
  Supertonic writes .wav per scene; OpenAI writes .mp3. Assembly accepts either.

  Language options:
    --lang en|ko          which language to use for voiceover
    --overlay en|ko|none  caption language (the spoken narration shown as
                          bottom closed captions), or none to disable captions

  Captions show the full narration text, wrapped on a semi-transparent bar at
  the bottom. (The short on-screen headline is baked into the slide image
  during stage 2 and is independent of the caption language.)

  Speech speed (works for both providers):
    --speed 0.25–4.0   how fast the voice talks (default: 1.1)
  Example:
    uv run atlas episode run 11 --stages 3 --lang en --speed 1.2 --force

  Common combinations:
    --lang en --overlay ko    English voice + Korean captions
    --lang ko --overlay en    Korean voice + English captions
    --lang ko --overlay ko    Korean voice + Korean captions
    --lang en --overlay none  English voice, no captions (default prototype)

  Each combination produces a separate MP4:
    episodes/c03_e11_token/c03_e11_token_en_overlay-ko.mp4

  To regenerate just one scene's audio (one TTS call), then rebuild the video:
    uv run atlas episode run 11 --stages 3 --scene S03 --lang en --force

  To rebuild the video from existing audio with NO TTS cost (e.g. after
  changing caption/transition styling), add --no-tts:
    uv run atlas episode run 11 --stages 3 --lang en --overlay ko --no-tts --force

  Note: Audio duration is authoritative. If the TTS comes out longer or
  shorter than the script's target duration_sec, the video will use the
  actual audio duration. A warning is printed when the difference exceeds
  0.5 seconds.

  Assembly behavior (automatic): each scene is a static image (no zoom).
  Scenes blend with a ~0.4s crossfade. Any trailing silence baked into the
  TTS is trimmed, then a uniform ~0.9s pause is held after each line so the
  pacing is consistent. These constants live at the top of assemble_video()
  in src/atlas_pipeline/stage3_video.py if you want to tune the feel.


THE SCRIPT (script.json)
------------------------

Stage 1 is the heart of the pipeline — images, captions, and timing are all
derived from script.json. It is plain JSON you can hand-edit; stages 2 and 3
always read whatever is in the file at the time they run.

Top-level shape:

  {
    "meta":   { ...episode-level metadata... },
    "scenes": [ ...ordered list of scenes... ],
    "quality_checks": { ...model's self-reported booleans... }
  }

meta (episode-level):
  term                       the jargon term this episode explains
  tier                       difficulty tier ("1", "2", "2.5", "2.7", "3")
  cluster                    cluster name
  episode_in_cluster         e.g. "3.11"
  target_length_sec          requested length
  actual_length_sec          model's estimate of the written length
  english_word_count         pacing reference (~150 words/min)
  korean_syllable_count      pacing reference (~290 syllables/min)
  scene_count                number of scenes
  one_sentence_pitch_en/ko   one-line summary of the episode
  sticky_takeaway_en/ko      the quotable closing line
  next_episode_teaser_en/ko  optional lead-in to the next episode

scenes[] — each entry is ONE visual on screen:
  scene_id          "S01", "S02", ... (used for image/audio filenames)
  beat              HOOK | DEFINITION | METAPHOR | CONCRETE_EXAMPLE |
                    WHY_IT_MATTERS | STICKY_TAKEAWAY
  start_sec         timeline start (planning reference)
  end_sec           timeline end (planning reference)
  duration_sec      target duration — a TARGET only; actual audio length wins
  narration.en      English voiceover (spoken; also the EN caption text)
  narration.ko      Korean voiceover (spoken; also the KO caption text)
  on_screen_text.en short headline (<=7 words) baked INTO the image
  on_screen_text.ko Korean headline baked into the image
  on_screen_text.position   center | upper-third | lower-third
  atlas_in_scene    true  -> the Atlas mascot is drawn into this scene
                    false -> pure pixel-art explainer, no character
  atlas_pose        when atlas_in_scene is true: neutral | thinking |
                    working | error | happy | pointing  (null otherwise)
  visual_intent     plain-language description of the scene; this is what the
                    stage-2 image prompt is built from

What feeds what:
  - narration   -> what you HEAR (TTS) and what shows as captions (stage 3)
  - on_screen_text -> what you SEE printed inside the slide image (stage 2);
                   independent of the caption language
  - atlas_in_scene / atlas_pose -> whether the mascot appears, and its pose
  - visual_intent -> the scene illustration in the stage-2 image

To tweak wording or visuals, edit the relevant field and re-run stage 2
and/or stage 3 (use --no-tts to rebuild the video without re-charging TTS).


TYPICAL WORKFLOW FOR ONE EPISODE
---------------------------------

  uv run atlas episode run 11 --stages 1          # generate script
  # edit script.json if needed
  uv run atlas episode run 11 --stages 2          # generate images
  uv run atlas episode select 11 S01 a            # select candidates
  uv run atlas episode select 11 S02 b
  # ... repeat for all scenes
  uv run atlas episode run 11 --stages 3 --lang en --overlay ko
  # review the MP4


CHECKING STATUS AND COSTS
--------------------------

  uv run atlas episode status 11      # per-scene breakdown
  uv run atlas costs                  # total cost by stage and episode


FILE STRUCTURE
--------------

  .env                            API keys
  episodes_yaml/episode_NN.yaml  Episode input data (one file per episode)
  atlas/bible/                   Atlas character reference images (locked)
  models/supertonic/             Local TTS model files (downloaded once; gitignored)
  episodes/
    c03_e11_token/
      script.json                Stage 1 output
      image_prompts.json         Stage 2 intermediate
      images/
        S01_a.png                Frame A (both frames are used in the video)
        S01_b.png                Frame B (variation of A; alternates with A)
      audio/
        S01_en.wav               English TTS per scene (.wav local / .mp3 OpenAI)
        S01_ko.wav               Korean TTS per scene
      c03_e11_token_en_overlay-ko.mp4   Final video
  logs/api_calls.jsonl           Append-only cost log
  plan_files/                    Original planning documents (reference only)
  src/atlas_pipeline/            Python source code


FORCE-REGENERATING OUTPUTS
---------------------------

Every stage is idempotent: it skips existing files unless you pass --force.

  uv run atlas episode run 11 --stages 1 --force     # regenerate script
  uv run atlas episode run 11 --stages 2 --force     # regenerate all images
  uv run atlas episode run 11 --stages 3 --force     # regenerate audio + video
