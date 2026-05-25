"""Stage 2: Build image prompts and generate images via gpt-image-2."""
from __future__ import annotations

import base64
from pathlib import Path

from rich.console import Console

from .atlas_bible import get_bible_paths
from .config import (
    ATLAS_BEATS,
    ATLAS_CHARACTER_BLURB,
    BEAT_TO_POSE,
    IMAGE_MODEL,
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

_RENDERING_SPEC = "Quality: high. Format: 16:9 educational slide ready for video voiceover."


def _build_prompt(
    scene: dict,
    tier_hex: str,
    overlay_lang: str,
    atlas_in_scene: bool,
    pose: str,
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
    if atlas_in_scene:
        parts.append(ATLAS_CHARACTER_BLURB)
        parts.append(
            f"Atlas appears in this scene with a {pose} pose, integrated into the "
            "action described below; match Atlas to the reference image(s) provided."
        )
    character_rule = _CHARACTER_RULE_ATLAS if atlas_in_scene else _CHARACTER_RULE_NONE
    constraints = _CONSTRAINTS.format(tier_hex=tier_hex, character_rule=character_rule)

    parts.extend([layout, content, constraints, _RENDERING_SPEC])
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

        prompt = _build_prompt(scene, tier_hex, overlay_lang, atlas_in_scene, pose, size)
        scenes_out.append({
            "scene_id": scene["scene_id"],
            "beat": beat,
            "pose_hint": pose,
            "atlas_in_scene": atlas_in_scene,
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
            console.print(f"\n[bold]{s['scene_id']}[/bold] ({s['beat']}, pose={s['pose_hint']}, atlas={s['atlas_in_scene']})")
            console.print(s["image_prompt"][:400] + "...")
        return result

    return result


def generate_images(
    image_prompts: dict,
    ep_dir: Path,
    scene_filter: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    images_dir = ep_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    meta = image_prompts.get("meta", {})
    episode_id = meta.get("term", "unknown")
    size = meta.get("image_size", IMAGE_SIZE)
    quality = meta.get("image_quality", IMAGE_QUALITY)

    for scene in image_prompts.get("scenes", []):
        sid = scene["scene_id"]
        if scene_filter and sid != scene_filter:
            continue

        for candidate in ("a", "b"):
            out_path = images_dir / f"{sid}_{candidate}.png"
            if out_path.exists() and not force:
                console.print(f"[dim]{sid}_{candidate}.png exists — skipping[/dim]")
                continue

            if dry_run:
                console.print(f"[dim]DRY RUN: Would generate {sid}_{candidate}.png[/dim]")
                continue

            console.print(f"Generating {sid}_{candidate}.png ({size}, quality={quality}) ...")
            _generate_one(scene, out_path, episode_id, size, quality)


def _generate_one(scene: dict, out_path: Path, episode_id: str, size: str, quality: str) -> None:
    prompt = scene["image_prompt"]
    sid = scene["scene_id"]
    atlas_in = scene.get("atlas_in_scene", False)
    pose = scene.get("pose_hint", "neutral")

    if atlas_in:
        bible_paths = get_bible_paths(pose)
        if bible_paths:
            images = [open(p, "rb") for p in bible_paths]
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
            console.print(f"[yellow]No bible images found for pose '{pose}' — falling back to generate[/yellow]")
            atlas_in = False

    if not atlas_in:
        result = image_client.images.generate(
            model=IMAGE_MODEL,
            prompt=prompt,
            size=size,
            quality=quality,
        )

    image_bytes = base64.b64decode(result.data[0].b64_json)
    out_path.write_bytes(image_bytes)

    log_api_call(
        stage="2_images",
        model=IMAGE_MODEL,
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.12 if atlas_in else 0.10,
        episode_id=episode_id,
        scene_id=sid,
        extra={"atlas_in_scene": atlas_in, "pose": pose},
    )
    console.print(f"[green]✓[/green] {out_path.name}")


def select_candidate(ep_dir: Path, scene_id: str, candidate: str) -> None:
    src = ep_dir / "images" / f"{scene_id}_{candidate}.png"
    dst = ep_dir / "images" / f"{scene_id}_selected.png"
    if not src.exists():
        raise FileNotFoundError(f"Candidate not found: {src}")
    import shutil
    shutil.copy2(src, dst)
    console.print(f"[green]✓[/green] {scene_id}_selected.png → candidate {candidate}")
