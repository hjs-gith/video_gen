"""Stage 2: Build image prompts and generate images via gpt-image-2."""
from __future__ import annotations

import base64
from pathlib import Path

from rich.console import Console

from . import image_local
from .atlas_bible import get_bible_paths
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

_CHARACTER_RULE_ATLAS = "Atlas is the only character; no realistic humans, no photographic faces"
_CHARACTER_RULE_NONE = "No characters; show only the pixel-art props, icons, and text described"

# Layer-specific rules for the parallax scheme: a static background layer and a
# transparent foreground (the focal subject) that gently floats over it in stage 3.
_CHARACTER_RULE_BG = (
    "Render ONLY the background setting and the headline — NO characters and NO "
    "central focal objects. Leave the focal area open/empty so a separate foreground "
    "layer can be composited on top"
)
_CHARACTER_RULE_FG_ATLAS = (
    "Render ONLY Atlas and the essential focal object(s) — nothing else: no setting, "
    "no scenery, no background fill, no headline text"
)
_CHARACTER_RULE_FG_NONE = (
    "Render ONLY the essential focal object(s)/prop(s) described — nothing else: no "
    "setting, no scenery, no background fill, no headline text"
)

_BG_LAYER_NOTE = (
    "LAYER — BACKGROUND: This is the static backdrop of a parallax scene. Include the "
    "headline text. Do NOT draw the focal subject; leave its area open so the "
    "foreground layer sits on top cleanly."
)
_FG_LAYER_NOTE = (
    "LAYER — FOREGROUND: Render the focal subject(s) only, centered, on a FULLY "
    "TRANSPARENT background (PNG alpha). No background fill, no scenery, no headline "
    "text, no ground/contact shadow. This layer is composited over the background and "
    "gently floats up and down, so keep generous empty margins around the subject."
)

_RENDERING_SPEC = "Quality: high. Format: 16:9 educational slide ready for video voiceover."


def _build_prompt(
    scene: dict,
    tier_hex: str,
    overlay_lang: str,
    atlas_in_scene: bool,
    pose: str,
    size: str,
    layer: str | None = None,
) -> str:
    """Build the image prompt for a scene.

    ``layer`` selects what gets drawn:
      - ``None`` -> the legacy full scene (background + subject + headline)
      - ``"bg"`` -> background/setting + headline only, no focal subject
      - ``"fg"`` -> the focal subject only, on a transparent background, no headline
    """
    style = SERIES_STYLE_BLOCK.format(tier_hex=tier_hex)
    on_screen = scene.get("on_screen_text", {})
    text = on_screen.get(overlay_lang, on_screen.get("en", ""))
    position = on_screen.get("position", "center")
    visual_intent = scene.get("visual_intent", "")

    parts = [_DELIVERABLE, style]

    # Atlas is the focal subject, so its description belongs with the layer that
    # actually draws it: the foreground (or the legacy full frame), never the bg.
    if atlas_in_scene and layer != "bg":
        parts.append(ATLAS_CHARACTER_BLURB)
        parts.append(
            f"Atlas appears with a {pose} pose, integrated into the action described "
            "below; match Atlas to the reference image(s) provided."
        )

    if layer == "bg":
        layout = f'Canvas: {size}. Headline position: {position}.'
        content = f'Headline (verbatim, exact spelling): "{text}"\nBackground setting: {visual_intent}'
        character_rule = _CHARACTER_RULE_BG
        layer_note = _BG_LAYER_NOTE
    elif layer == "fg":
        layout = f'Canvas: {size}. Transparent background (RGBA).'
        content = f'Focal subject(s): {visual_intent}'
        character_rule = _CHARACTER_RULE_FG_ATLAS if atlas_in_scene else _CHARACTER_RULE_FG_NONE
        layer_note = _FG_LAYER_NOTE
    else:
        layout = f'Canvas: {size}. Headline position: {position}.'
        content = f'Headline (verbatim, exact spelling): "{text}"\nVisual element: {visual_intent}'
        character_rule = _CHARACTER_RULE_ATLAS if atlas_in_scene else _CHARACTER_RULE_NONE
        layer_note = None

    constraints = _CONSTRAINTS.format(tier_hex=tier_hex, character_rule=character_rule)
    parts.extend([layout, content, constraints])
    if layer_note:
        parts.append(layer_note)
    parts.append(_RENDERING_SPEC)
    return "\n\n".join(parts)


def build_image_prompts(
    script: dict,
    overlay_lang: str = "en",
    size: str | None = None,
    quality: str | None = None,
    dry_run: bool = False,
) -> dict:
    size = size or IMAGE_SIZE
    quality = quality or IMAGE_QUALITY
    meta = script.get("meta", {})
    tier = meta.get("tier", "T2")
    tier_hex = TIER_HEX.get(f"T{tier}", TIER_HEX["T2"])

    scenes_out = []
    for scene in script.get("scenes", []):
        beat = scene.get("beat", "")
        pose = scene.get("atlas_pose") or BEAT_TO_POSE.get(beat, "neutral")
        atlas_in_scene = scene.get("atlas_in_scene")
        if atlas_in_scene is None:
            atlas_in_scene = beat in ATLAS_BEATS or "atlas" in scene.get("visual_intent", "").lower()

        common = (scene, tier_hex, overlay_lang, atlas_in_scene, pose, size)
        scenes_out.append({
            "scene_id": scene["scene_id"],
            "beat": beat,
            "pose_hint": pose,
            "atlas_in_scene": atlas_in_scene,
            "visual_intent_source": scene.get("visual_intent", ""),
            "on_screen_text_used": scene.get("on_screen_text", {}).get(overlay_lang, ""),
            "image_prompt": _build_prompt(*common),
            "image_prompt_bg": _build_prompt(*common, layer="bg"),
            "image_prompt_fg": _build_prompt(*common, layer="fg"),
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
            "animation": "layered",  # bg + floating fg (stage 3); see _generate_*.
            "scene_count": len(scenes_out),
        },
        "scenes": scenes_out,
    }

    if dry_run:
        for s in scenes_out:
            console.print(f"\n[bold]{s['scene_id']}[/bold] ({s['beat']}, pose={s['pose_hint']}, atlas={s['atlas_in_scene']})")
            console.print(f"[dim]— background layer —[/dim]\n{s['image_prompt_bg'][:300]} ...")
            console.print(f"[dim]— foreground layer —[/dim]\n{s['image_prompt_fg'][:300]} ...")
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

        path_bg = images_dir / f"{sid}_bg.png"
        path_fg = images_dir / f"{sid}_fg.png"

        # Background layer — the static backdrop (setting + headline, no subject).
        if path_bg.exists() and not force:
            console.print(f"[dim]{path_bg.name} exists — skipping[/dim]")
        elif dry_run:
            console.print(f"[dim]DRY RUN: Would generate {path_bg.name} ({provider})[/dim]")
        else:
            console.print(f"Generating {path_bg.name} ({provider}, {size}, quality={quality}) ...")
            _generate_background(scene, path_bg, episode_id, size, quality, provider)

        # Foreground layer — the focal subject on a transparent background, which
        # stage 3 floats over the background for a dynamic parallax scene.
        if path_fg.exists() and not force:
            console.print(f"[dim]{path_fg.name} exists — skipping[/dim]")
        elif dry_run:
            console.print(f"[dim]DRY RUN: Would generate {path_fg.name} (transparent foreground)[/dim]")
        else:
            console.print(f"Generating {path_fg.name} (transparent foreground) ...")
            _generate_foreground(scene, path_fg, episode_id, size, quality, provider)


def _render(
    provider: str,
    prompt: str,
    size: str,
    quality: str,
    out_path: Path,
    reference_paths: list[Path],
    transparent: bool = False,
) -> None:
    """Render one image via the chosen provider and write it to out_path.

    `reference_paths` empty -> text-to-image; non-empty -> reference/img2img editing.
    `transparent` -> request an RGBA cutout (foreground layer): the local server
    returns a transparent PNG; OpenAI uses its native `background="transparent"`.
    """
    if provider == "local":
        image_local.synthesize_image(prompt, size, out_path, reference_paths, transparent=transparent)
        return

    # openai
    kwargs: dict = {"model": IMAGE_MODEL, "prompt": prompt, "size": size, "quality": quality}
    if transparent:
        kwargs["background"] = "transparent"
        kwargs["output_format"] = "png"
    if reference_paths:
        images = [open(p, "rb") for p in reference_paths]
        try:
            result = image_client.images.edit(
                image=images[0] if len(images) == 1 else images,
                **kwargs,
            )
        finally:
            for f in images:
                f.close()
    else:
        result = image_client.images.generate(**kwargs)
    out_path.write_bytes(base64.b64decode(result.data[0].b64_json))


def _generate_background(
    scene: dict, out_path: Path, episode_id: str, size: str, quality: str, provider: str
) -> None:
    """Generate the static background layer: setting + headline, no focal subject."""
    sid = scene["scene_id"]
    prompt = scene.get("image_prompt_bg", scene["image_prompt"])

    _render(provider, prompt, size, quality, out_path, [], transparent=False)

    log_api_call(
        stage="2_images",
        model=IMAGE_LOCAL_MODEL if provider == "local" else IMAGE_MODEL,
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0 if provider == "local" else 0.10,
        episode_id=episode_id,
        scene_id=sid,
        extra={"layer": "bg", "provider": provider},
    )
    console.print(f"[green]✓[/green] {out_path.name}")


def _generate_foreground(
    scene: dict, out_path: Path, episode_id: str, size: str, quality: str, provider: str
) -> None:
    """Generate the floating foreground layer: focal subject on a transparent bg.

    Atlas scenes condition on the bible references to keep the mascot on-model;
    other scenes are a plain (transparent) text-to-image of the focal prop(s).
    """
    sid = scene["scene_id"]
    prompt = scene.get("image_prompt_fg", scene["image_prompt"])
    atlas_in = scene.get("atlas_in_scene", False)
    pose = scene.get("pose_hint", "neutral")

    reference_paths: list[Path] = []
    if atlas_in:
        reference_paths = get_bible_paths(pose)
        if not reference_paths:
            console.print(f"[yellow]No bible images found for pose '{pose}' — generating foreground without references[/yellow]")

    _render(provider, prompt, size, quality, out_path, reference_paths, transparent=True)

    log_api_call(
        stage="2_images",
        model=IMAGE_LOCAL_MODEL if provider == "local" else IMAGE_MODEL,
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0 if provider == "local" else (0.12 if atlas_in else 0.10),
        episode_id=episode_id,
        scene_id=sid,
        extra={"layer": "fg", "atlas_in_scene": atlas_in, "pose": pose, "provider": provider},
    )
    console.print(f"[green]✓[/green] {out_path.name}")
