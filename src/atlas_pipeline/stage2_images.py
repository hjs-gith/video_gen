"""Stage 2: Build image prompts and generate images via gpt-image-2."""
from __future__ import annotations

import base64
from pathlib import Path

from rich.console import Console

from . import image_local
from .characters import (
    canonical_refs,
    get_bible_paths,
    get_character,
    scene_characters,
)
from .config import (
    ATLAS_BEATS,
    ATLAS_CHARACTER_BLURB,
    BEAT_TO_POSE,
    IMAGE_LOCAL_MODEL,
    IMAGE_MODEL,
    IMAGE_PROVIDER,
    IMAGE_QUALITY,
    IMAGE_SIZE,
    SERIES_STYLE_BLOCK,
    TIER_HEX,
    image_client,
)
from .utils import episode_dir, load_json, log_api_call, save_json

console = Console()

_DELIVERABLE = "Create one educational presentation slide for a series on AI concepts."

_CONSTRAINTS = """\
- All text rendered crisply and legibly
- Render text EXACTLY as written, no extra characters or words
- Single accent color only: {tier_hex}
- No watermark, no logos, no extra text beyond what is specified
- {character_rule}
- No gradient backgrounds, no drop shadows except a faint contact shadow"""

_CHARACTER_RULE_NONE = "No characters; show only the pixel-art props, icons, and text described"


def _character_rule(present: list) -> str:
    """The constraint line naming which character(s) may appear."""
    if not present:
        return _CHARACTER_RULE_NONE
    names = ", ".join(char.display_name for char, _ in present)
    verb = "is" if len(present) == 1 else "are"
    return f"{names} {verb} the only character(s); no realistic humans, no photographic faces"

_RENDERING_SPEC = "Quality: high. Format: 16:9 educational slide ready for video voiceover."

# Appended to frame B's prompt. Frame B is generated as an edit of frame A so the
# two alternate as a 2-frame idle loop in the video (stage 3). The awkward "jitter"
# comes from the model drifting the WHOLE image; the cure is to hard-lock everything
# and permit exactly one small, named micro-motion ({motion}, filled per scene).
_VARIATION_SUFFIX = (
    "SECOND FRAME OF A 2-FRAME PIXEL-ART IDLE LOOP.\n"
    "This is frame 2 of a looping idle animation built directly from the provided "
    "image (frame 1). Reproduce the provided image PIXEL-FOR-PIXEL: identical "
    "composition and layout, every outline and shape in the same place, all the same "
    "colors and the same accent color, the same background, and ALL text identical "
    "(same words, same glyphs, same weight, same position — do NOT re-letter, re-wrap, "
    "or re-render any text). Do not shift, rescale, recolor, or redraw anything except "
    "the one element named next.\n"
    "THE ONLY CHANGE — a subtle micro-motion of just a few pixels:\n"
    "{motion}\n"
    "Keep it gentle so frames 1 and 2 alternate as a calm, living loop, never a jump cut."
)


_ATLAS_MOTION = (
    "Atlas does a tiny idle float: its whole body drifts up by about 2 pixels "
    "and tilts very slightly (about 2–3 degrees), as if gently bobbing in place "
    "(the charcoal contact-shadow disc beneath shrinks a touch to match the lift). "
    "Its soft-green pixel face stays EXACTLY the same — same eyes, same screen "
    "expression, same emotion; do NOT blink, do NOT narrow or reshape the eyes, "
    "do NOT change the face at all. Atlas stays perfectly on-model; nothing else "
    "in the scene moves."
)
_CHARACTER_MOTION = (
    "The character(s) do a tiny idle float: each drifts up by about 2 pixels and "
    "tilts very slightly (about 2–3 degrees), as if gently bobbing in place. Their "
    "faces, expressions, colors, and outlines stay EXACTLY the same — only position "
    "and tilt change, and each stays perfectly on-model. Nothing else moves."
)
_FOCAL_MOTION = (
    "The single main focal element does a tiny idle float: it drifts by 1–2 pixels "
    "and tilts very slightly (about 2–3 degrees), as if gently bobbing in place. "
    "Its shape, colors, and any face or expression stay EXACTLY the same — only its "
    "position and tilt change. Every other prop, icon, text, and pixel stays exactly "
    "as in frame 1."
)


def _variation_motion(scene: dict) -> str:
    """The single small motion frame B is allowed, chosen to suit the scene.

    Naming one concrete element (and forbidding all others) is what keeps the loop
    from reading as a glitch — like the second cel of a hand-drawn idle animation.
    """
    present = scene_characters(scene)
    ids = {char.id for char, _ in present}
    if not present:
        return _FOCAL_MOTION
    if ids == {"atlas"}:
        return _ATLAS_MOTION
    return _CHARACTER_MOTION


def _build_prompt(
    scene: dict,
    tier_hex: str,
    overlay_lang: str,
    present: list,
    size: str,
) -> str:
    style = SERIES_STYLE_BLOCK.format(tier_hex=tier_hex)
    on_screen = scene.get("on_screen_text", {})
    text = on_screen.get(overlay_lang, on_screen.get("en", ""))
    position = on_screen.get("position", "center")
    visual_intent = scene.get("visual_intent", "")

    layout = f'Canvas: {size}. Headline position: {position}.'
    content = f'Headline (verbatim, exact spelling): "{text}"\nVisual element: {visual_intent}'

    parts = [_DELIVERABLE, style]
    for char, pose in present:
        parts.append(char.blurb)
        parts.append(
            f"{char.display_name} appears in this scene with a {pose} pose, integrated "
            f"into the action described below; match {char.display_name} to the "
            "reference image(s) provided."
        )
    constraints = _CONSTRAINTS.format(tier_hex=tier_hex, character_rule=_character_rule(present))

    parts.extend([layout, content, constraints, _RENDERING_SPEC])
    return "\n\n".join(parts)


def _resolve_characters(scene: dict) -> list:
    """Resolve the characters in a source (stage-1) scene -> [(Character, pose)].

    Honors the explicit `characters` array, then legacy `atlas_in_scene`/`atlas_pose`,
    then infers Atlas from the beat/visual_intent for older scripts with neither field.
    """
    beat = scene.get("beat", "")
    entries = scene.get("characters")
    if entries:
        out = []
        for e in entries:
            char = get_character(e.get("name", ""))
            if char is not None:
                out.append((char, e.get("pose") or BEAT_TO_POSE.get(beat, "neutral")))
        return out

    atlas_in = scene.get("atlas_in_scene")
    if atlas_in is None:  # legacy inference for scripts lacking any character field
        atlas_in = beat in ATLAS_BEATS or "atlas" in scene.get("visual_intent", "").lower()
    if atlas_in:
        atlas = get_character("atlas")
        pose = scene.get("atlas_pose") or BEAT_TO_POSE.get(beat, "neutral")
        return [(atlas, pose)] if atlas is not None else []
    return []


def build_image_prompts(
    script: dict,
    overlay_lang: str = "en",
    size: str | None = None,
    quality: str | None = None,
    dry_run: bool = False,
    no_characters: bool = False,
) -> dict:
    size = size or IMAGE_SIZE
    quality = quality or IMAGE_QUALITY
    meta = script.get("meta", {})
    tier = meta.get("tier", "T2")
    tier_hex = TIER_HEX.get(f"T{tier}", TIER_HEX["T2"])

    scenes_out = []
    for scene in script.get("scenes", []):
        beat = scene.get("beat", "")
        present = [] if no_characters else _resolve_characters(scene)  # [(Character, pose), ...]

        prompt = _build_prompt(scene, tier_hex, overlay_lang, present, size)
        scenes_out.append({
            "scene_id": scene["scene_id"],
            "beat": beat,
            "characters": [{"name": char.id, "pose": pose} for char, pose in present],
            # Back-compat fields (single-character era):
            "pose_hint": present[0][1] if present else "neutral",
            "atlas_in_scene": any(char.id == "atlas" for char, _ in present),
            "visual_intent_source": scene.get("visual_intent", ""),
            "on_screen_text_used": scene.get("on_screen_text", {}).get(overlay_lang, ""),
            "image_prompt": prompt,
        })

    result = {
        "meta": {
            "term": meta.get("term"),
            "tier": tier,
            "tier_hex": tier_hex,
            "overlay_lang": overlay_lang,
            "image_model": IMAGE_MODEL,
            "image_size": size,
            "image_quality": quality,
            "scene_count": len(scenes_out),
        },
        "scenes": scenes_out,
    }

    if dry_run:
        for s in scenes_out:
            cast = ", ".join(f"{c['name']}:{c['pose']}" for c in s["characters"]) or "none"
            console.print(f"\n[bold]{s['scene_id']}[/bold] ({s['beat']}, cast={cast})")
            console.print(s["image_prompt"][:400] + "...")
        return result

    return result


def generate_images(
    image_prompts: dict,
    ep_dir: Path,
    scene_filter: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    provider: str | None = None,
) -> None:
    images_dir = ep_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    provider = provider or IMAGE_PROVIDER
    meta = image_prompts.get("meta", {})
    episode_id = meta.get("term", "unknown")
    size = meta.get("image_size", IMAGE_SIZE)
    quality = meta.get("image_quality", IMAGE_QUALITY)

    for scene in image_prompts.get("scenes", []):
        sid = scene["scene_id"]
        if scene_filter and sid != scene_filter:
            continue

        path_a = images_dir / f"{sid}_a.png"
        path_b = images_dir / f"{sid}_b.png"

        # Frame A — the base frame.
        if path_a.exists() and not force:
            console.print(f"[dim]{path_a.name} exists — skipping[/dim]")
        elif dry_run:
            console.print(f"[dim]DRY RUN: Would generate {path_a.name} ({provider})[/dim]")
        else:
            console.print(f"Generating {path_a.name} ({provider}, {size}, quality={quality}) ...")
            _generate_frame_a(scene, path_a, episode_id, size, quality, provider)

        # Frame B — a slight variation of A, for the 2-frame animation loop.
        if path_b.exists() and not force:
            console.print(f"[dim]{path_b.name} exists — skipping[/dim]")
        elif dry_run:
            console.print(f"[dim]DRY RUN: Would generate {path_b.name} (variation of A)[/dim]")
        elif not path_a.exists():
            console.print(f"[yellow]No {path_a.name} to vary — skipping {path_b.name}[/yellow]")
        else:
            console.print(f"Generating {path_b.name} (variation of A) ...")
            _generate_frame_b(scene, path_b, path_a, episode_id, size, quality, provider)


def _render(
    provider: str,
    prompt: str,
    size: str,
    quality: str,
    out_path: Path,
    reference_paths: list[Path],
) -> None:
    """Render one image via the chosen provider and write it to out_path.

    `reference_paths` empty -> text-to-image; non-empty -> reference/img2img editing.
    """
    if provider == "local":
        image_local.synthesize_image(prompt, size, out_path, reference_paths)
        return

    # openai
    if reference_paths:
        images = [open(p, "rb") for p in reference_paths]
        try:
            result = image_client.images.edit(
                model=IMAGE_MODEL,
                image=images[0] if len(images) == 1 else images,
                prompt=prompt,
                size=size,
                quality=quality,
            )
        finally:
            for f in images:
                f.close()
    else:
        result = image_client.images.generate(
            model=IMAGE_MODEL,
            prompt=prompt,
            size=size,
            quality=quality,
        )
    out_path.write_bytes(base64.b64decode(result.data[0].b64_json))


def _generate_frame_a(
    scene: dict, out_path: Path, episode_id: str, size: str, quality: str, provider: str
) -> None:
    """Generate the base frame, conditioning on every present character's bible.

    One character -> its neutral+pose references (as before). Two characters -> one
    canonical reference each, to keep conditioning to ~one image per character.
    """
    prompt = scene["image_prompt"]
    sid = scene["scene_id"]
    present = scene_characters(scene)

    reference_paths: list[Path] = []
    if len(present) == 1:
        char, pose = present[0]
        reference_paths = get_bible_paths(char, pose)
        if not reference_paths:
            console.print(f"[yellow]No bible images for {char.id} pose '{pose}' — falling back to text-to-image[/yellow]")
    elif len(present) > 1:
        for char, pose in present:
            reference_paths.extend(canonical_refs(char, pose))

    _render(provider, prompt, size, quality, out_path, reference_paths)

    log_api_call(
        stage="2_images",
        model=IMAGE_LOCAL_MODEL if provider == "local" else IMAGE_MODEL,
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0 if provider == "local" else (0.12 if present else 0.10),
        episode_id=episode_id,
        scene_id=sid,
        extra={
            "characters": [{"name": c.id, "pose": p} for c, p in present],
            "frame": "a",
            "provider": provider,
        },
    )
    console.print(f"[green]✓[/green] {out_path.name}")


def _generate_frame_b(
    scene: dict, out_path: Path, frame_a_path: Path, episode_id: str, size: str, quality: str, provider: str
) -> None:
    """Generate frame B as the second cel of a 2-frame idle loop (edit of frame A)."""
    sid = scene["scene_id"]
    suffix = _VARIATION_SUFFIX.format(motion=_variation_motion(scene))
    prompt = scene["image_prompt"] + "\n\n" + suffix

    _render(provider, prompt, size, quality, out_path, [frame_a_path])

    log_api_call(
        stage="2_images",
        model=IMAGE_LOCAL_MODEL if provider == "local" else IMAGE_MODEL,
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0 if provider == "local" else 0.12,
        episode_id=episode_id,
        scene_id=sid,
        extra={"frame": "b", "variation_of": "a", "provider": provider},
    )
    console.print(f"[green]✓[/green] {out_path.name}")
