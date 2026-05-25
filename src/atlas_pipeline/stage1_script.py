"""Stage 1: Generate bilingual script JSON via gpt-5.4."""
from __future__ import annotations

import json

from rich.console import Console

from .config import SCRIPT_MODEL, script_client
from .curriculum import EpisodeRecord
from .utils import episode_dir, load_json, log_api_call, save_json, validate_script

console = Console()

_SYSTEM_PROMPT = (
    'You are a scriptwriter for "AI Jargon Atlas" — a short-form bilingual '
    "educational video series (30–90 sec) explaining AI terms to "
    "non-developers (curious professionals who've heard the words but can't "
    "quite explain them).\n\n"
    "Your job: produce the SCRIPT only. Image prompts, animation, and sound "
    "design are handled by separate tools downstream. Focus on writing, "
    "timing, and clear visual intent.\n\n"
    "Output must be VALID JSON. No prose outside the JSON."
)

_USER_PROMPT_TEMPLATE = """\
═══════════════════════════════════════════════
VARIABLES
═══════════════════════════════════════════════

TERM:                   {term}
TIER:                   {tier}
CLUSTER:                {cluster_name}
EPISODE_IN_CLUSTER:     {episode_in_cluster}
ONE_LINE_GIST:          {one_line_gist}
METAPHOR_SEED:          {metaphor_seed}
EXAMPLE_SCENARIO:       {example_scenario}
TARGET_LENGTH_SEC:      {target_length_sec}
PREVIOUS_EPISODES:      {previous_episodes}
NEXT_EPISODE_TEASER:    {next_episode_teaser}

═══════════════════════════════════════════════
RULES
═══════════════════════════════════════════════

PACING:
- English: ~150 words per minute
- Korean: ~290 syllables per minute
- Stay within ±10% of TARGET_LENGTH_SEC

BEAT STRUCTURE (every episode follows this):
1. HOOK (3–5 sec)
2. DEFINITION (5–8 sec)
3. METAPHOR (10–15 sec)
4. CONCRETE_EXAMPLE (10–20 sec)
5. WHY_IT_MATTERS (5–10 sec)
6. STICKY_TAKEAWAY (3–5 sec)

SCENES:
- Each scene = 3–8 seconds (one visual per scene)
- Each beat may contain 1–3 scenes
- Scenes are units of VISUAL change, not narration breaks
- Total scenes for a 60-sec video: typically 10–14

VOICE:
- Warm, smart-friend tone, second person ("you")
- No jargon used to explain jargon (or define it in ≤5 words)
- Korean: 존댓말, natural spoken rhythm, NOT literal translation
- One mild moment of wit per video; no forced jokes

CLUSTER-AWARE WRITING:
- If PREVIOUS_EPISODES are listed, you may reference those terms briefly
  without re-explaining them. This builds continuity within the mini-season.
- If NEXT_EPISODE_TEASER is given, end with a hook leading into the next episode.
- The viewer is following a mini-season arc, not isolated lessons.

ON-SCREEN TEXT:
- Reinforces KEYWORDS only — never duplicates narration
- Max 7 words per card
- Each card needs ≥2 sec on screen

ATLAS CHARACTER & WORLD:
- The series has a mascot named Atlas: a small floating pixel-art robot with a
  rounded retro CRT-monitor head (cream bezel, charcoal screen, soft-green pixel
  face), a capsule body, two short mitten arms, no legs, no mouth. Atlas shows
  emotion through its screen face and arm/body pose.
- Every scene lives in a cozy 16-bit pixel-art world (warm retro-game explainer).
- Atlas has six expression poses: neutral, thinking, working, error, happy,
  pointing. Pick the one that best fits the scene's mood/action.
- DECIDE PER SCENE whether Atlas appears:
  - If the scene needs a character or actor (someone reacting, demonstrating,
    driving the metaphor), put Atlas in it as an INTEGRATED participant — Atlas
    drives the taxi, points at the breaking tiles, cheers at the result, etc.
    NEVER use a human/office-worker stand-in; Atlas plays that role instead.
  - If the scene is pure explanation (a diagram, text breaking into tiles, a
    chart, a labeled container) and no actor is needed, leave Atlas out and show
    only the explanatory pixel-art elements.

VISUAL INTENT (the key field):
- Describe the scene in plain language an artist could draw
- Include: subjects, action, composition, mood
- When Atlas is in the scene, write Atlas directly into the description as a
  participant in the action (and reflect its pose). When Atlas is absent,
  describe only the explanatory pixel-art elements — no characters.
- Write what should be SHOWN, not how to prompt an image AI
- 1–3 sentences per scene, concrete and visualizable

═══════════════════════════════════════════════
OUTPUT SCHEMA
═══════════════════════════════════════════════

{{
  "meta": {{
    "term": "string",
    "tier": "string",
    "cluster": "string",
    "episode_in_cluster": "string",
    "target_length_sec": number,
    "actual_length_sec": number,
    "english_word_count": number,
    "korean_syllable_count": number,
    "scene_count": number,
    "one_sentence_pitch_en": "string",
    "one_sentence_pitch_ko": "string",
    "sticky_takeaway_en": "string (≤12 words)",
    "sticky_takeaway_ko": "string",
    "next_episode_teaser_en": "string (optional, ≤15 words)",
    "next_episode_teaser_ko": "string (optional)"
  }},

  "scenes": [
    {{
      "scene_id": "S01",
      "beat": "HOOK | DEFINITION | METAPHOR | CONCRETE_EXAMPLE | WHY_IT_MATTERS | STICKY_TAKEAWAY",
      "start_sec": 0.0,
      "end_sec": 4.0,
      "duration_sec": 4.0,
      "narration": {{
        "en": "English voiceover text.",
        "ko": "한국어 보이스오버 내용."
      }},
      "on_screen_text": {{
        "en": "≤7 words, keyword reinforcement only",
        "ko": "≤7 단어, 키워드 강조용",
        "position": "center | upper-third | lower-third"
      }},
      "atlas_in_scene": true,
      "atlas_pose": "neutral | thinking | working | error | happy | pointing (REQUIRED when atlas_in_scene is true; omit or null otherwise)",
      "visual_intent": "Plain-language description of what the scene should show. 1–3 sentences."
    }}
  ],

  "quality_checks": {{
    "word_count_within_tolerance": true,
    "no_unexplained_jargon": true,
    "metaphor_is_visualizable": true,
    "korean_sounds_natural_not_translated": true,
    "sticky_takeaway_is_quotable": true,
    "all_visual_intents_are_concrete": true
  }}
}}

═══════════════════════════════════════════════
NOW GENERATE
═══════════════════════════════════════════════

Produce the complete JSON for the variables provided.
Validate against the schema before returning.
Return only the JSON, nothing else.\
"""


def build_script(
    episode: EpisodeRecord,
    dry_run: bool = False,
    force: bool = False,
) -> dict:
    ep_dir = episode_dir(episode.cluster, episode.episode_number, episode.terms[0])
    script_path = ep_dir / "script.json"

    if script_path.exists() and not force:
        console.print(f"[dim]script.json already exists — skipping (use --force to overwrite)[/dim]")
        return load_json(script_path)

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        term=", ".join(episode.terms),
        tier=episode.tier_number,
        cluster_name=episode.cluster_name,
        episode_in_cluster=f"{episode.cluster}.{episode.episode_number}",
        one_line_gist=episode.one_line_gist,
        metaphor_seed=episode.metaphor_seed or "(none — derive your own)",
        example_scenario=episode.example_scenario or "(none — use a relatable everyday scenario)",
        target_length_sec=episode.target_length_sec,
        previous_episodes=(
            ", ".join(episode.previous_episodes) if episode.previous_episodes else "(none — first episode in cluster)"
        ),
        next_episode_teaser=episode.next_episode_teaser or "(none)",
    )

    if dry_run:
        console.print("[bold]--- SYSTEM PROMPT ---[/bold]")
        console.print(_SYSTEM_PROMPT)
        console.print("\n[bold]--- USER PROMPT ---[/bold]")
        console.print(user_prompt)
        return {}

    console.print(f"Generating script for [bold]{episode.terms[0]}[/bold] (ep {episode.episode_number}) via {SCRIPT_MODEL} ...")

    response = script_client.chat.completions.create(
        model=SCRIPT_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    usage = response.usage
    # Rough cost estimate: gpt-4.5 pricing as placeholder
    cost = (usage.prompt_tokens * 0.000075 + usage.completion_tokens * 0.0003) if usage else 0.0

    log_api_call(
        stage="1_script",
        model=SCRIPT_MODEL,
        tokens_in=usage.prompt_tokens if usage else 0,
        tokens_out=usage.completion_tokens if usage else 0,
        cost_usd=cost,
        episode_id=episode.slug,
    )

    raw = response.choices[0].message.content
    try:
        script = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Model returned invalid JSON: {e}\n\nRaw output:\n{raw}") from e

    errors = validate_script(script)
    if errors:
        console.print(f"[yellow]Script validation warnings:[/yellow]")
        for err in errors:
            console.print(f"  [yellow]• {err}[/yellow]")

    save_json(script, script_path)
    console.print(f"[green]✓[/green] script.json saved ({script.get('meta', {}).get('scene_count', '?')} scenes, {script.get('meta', {}).get('actual_length_sec', '?')}s)")
    return script
