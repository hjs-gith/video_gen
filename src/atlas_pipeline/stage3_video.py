"""Stage 3: TTS audio generation and video assembly."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from rich.console import Console

from .config import TTS_MODEL, TTS_SPEED, TTS_VOICE_EN, TTS_VOICE_KO, tts_client
from .utils import log_api_call

console = Console()

_DURATION_TOLERANCE_SEC = 0.5


def generate_tts(
    script: dict,
    ep_dir: Path,
    lang: str = "en",
    scene_filter: str | None = None,
    speed: float | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    audio_dir = ep_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    speed = TTS_SPEED if speed is None else speed
    voice = TTS_VOICE_EN if lang == "en" else TTS_VOICE_KO
    narration_key = "en" if lang == "en" else "ko"
    episode_id = script.get("meta", {}).get("term", "unknown")

    for scene in script.get("scenes", []):
        sid = scene["scene_id"]
        if scene_filter and sid != scene_filter:
            continue

        out_path = audio_dir / f"{sid}_{lang}.mp3"
        if out_path.exists() and not force:
            console.print(f"[dim]{out_path.name} exists — skipping[/dim]")
            continue

        narration = scene.get("narration", {}).get(narration_key, "")
        if not narration:
            console.print(f"[yellow]No {lang} narration for {sid} — skipping[/yellow]")
            continue

        if dry_run:
            console.print(f"[dim]DRY RUN: Would generate {out_path.name} (speed={speed})[/dim]")
            continue

        console.print(f"TTS {sid} ({lang}, speed={speed}) ...")
        response = tts_client.audio.speech.create(
            model=TTS_MODEL,
            voice=voice,
            input=narration,
            speed=speed,
        )
        out_path.write_bytes(response.content)

        # Duration check
        actual_dur = _audio_duration(out_path)
        target_dur = scene.get("duration_sec", 0)
        if abs(actual_dur - target_dur) > _DURATION_TOLERANCE_SEC:
            console.print(
                f"  [yellow]Duration mismatch {sid}: audio={actual_dur:.1f}s, script={target_dur:.1f}s[/yellow]"
            )

        log_api_call(
            stage=f"3a_tts_{lang}",
            model=TTS_MODEL,
            tokens_in=len(narration.split()),
            tokens_out=0,
            cost_usd=len(narration) * 0.000015,
            episode_id=episode_id,
            scene_id=sid,
            extra={"speed": speed},
        )
        console.print(f"[green]✓[/green] {out_path.name} ({actual_dur:.1f}s)")


def _audio_duration(path: Path) -> float:
    try:
        from moviepy import AudioFileClip
        with AudioFileClip(str(path)) as clip:
            return clip.duration
    except Exception:
        return 0.0


def _speech_end(audio_clip, threshold: float = 0.02, fps: int = 22050) -> float:
    """Seconds at which the last non-silent audio sample occurs."""
    arr = audio_clip.to_soundarray(fps=fps)
    amp = np.max(np.abs(arr), axis=1) if arr.ndim == 2 else np.abs(arr)
    loud = np.where(amp > threshold)[0]
    if len(loud) == 0:
        return audio_clip.duration
    return (loud[-1] + 1) / fps


def assemble_video(
    script: dict,
    ep_dir: Path,
    lang: str = "en",
    overlay: str = None,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    meta = script.get("meta", {})
    term = meta.get("term", "episode").lower().replace(" ", "_")
    cluster = meta.get("cluster", "c00") if isinstance(meta.get("cluster"), str) else f"c{meta.get('cluster', 0):02d}"

    output_name = f"{ep_dir.name}_{lang}_overlay-{overlay}.mp4"
    output_path = ep_dir / output_name

    if output_path.exists() and not force:
        console.print(f"[dim]{output_name} exists — skipping (use --force to overwrite)[/dim]")
        return

    if dry_run:
        console.print(f"[dim]DRY RUN: Would assemble {output_name}[/dim]")
        return

    from moviepy import (
        AudioFileClip,
        ColorClip,
        CompositeVideoClip,
        ImageClip,
        TextClip,
        concatenate_videoclips,
        vfx,
    )

    crossfade = 0.4
    tail_gap = 0.8        # uniform pause held after each (trimmed) narration
    silence_thresh = 0.02  # ~-34 dBFS; quieter than this is treated as silence
    keep_tail = 0.10     # natural buffer kept after the last speech sample
    scene_clips = []
    for scene in script.get("scenes", []):
        sid = scene["scene_id"]

        # Pick image
        img_selected = ep_dir / "images" / f"{sid}_selected.png"
        img_fallback = ep_dir / "images" / f"{sid}_a.png"
        img_path = img_selected if img_selected.exists() else img_fallback
        if not img_path.exists():
            console.print(f"[yellow]No image for {sid} — skipping scene[/yellow]")
            continue

        # Pick audio
        audio_path = ep_dir / "audio" / f"{sid}_{lang}.mp3"
        if not audio_path.exists():
            console.print(f"[yellow]No audio for {sid} ({lang}) — skipping scene[/yellow]")
            continue

        audio_clip = AudioFileClip(str(audio_path))
        # Trim any TTS trailing silence so the gap between scenes is uniform
        end = min(_speech_end(audio_clip, silence_thresh) + keep_tail, audio_clip.duration)
        audio_clip = audio_clip.subclipped(0, end)
        duration = audio_clip.duration
        hold = duration + tail_gap  # linger on the still frame after narration ends

        # Static image, held a beat past the narration (no motion)
        img_clip = ImageClip(str(img_path)).with_duration(hold)
        w, h = img_clip.size

        layers = [img_clip]

        # Bottom closed captions: the spoken narration in the chosen language
        if overlay != "none":
            caption = scene.get("narration", {}).get(overlay, "")
            if caption:
                pad = 16
                bottom_margin = int(h * 0.04)
                txt_clip = TextClip(
                    text=caption,
                    font=_get_font(overlay),
                    font_size=38,
                    color="white",
                    stroke_color="black",
                    stroke_width=1,
                    method="caption",
                    size=(int(w * 0.86), None),
                    text_align="center",
                    margin=(0, 10),
                ).with_duration(hold)

                bar_h = txt_clip.h + 2 * pad
                bar_y = h - bar_h - bottom_margin
                bar_clip = (
                    ColorClip((w, bar_h), color=(0, 0, 0))
                    .with_opacity(0.55)
                    .with_duration(hold)
                    .with_position((0, bar_y))
                )
                txt_clip = txt_clip.with_position(("center", bar_y + pad))
                layers.extend([bar_clip, txt_clip])

        composite = CompositeVideoClip(layers).with_audio(audio_clip)
        scene_clips.append(composite)

    if not scene_clips:
        console.print("[red]No scene clips to assemble.[/red]")
        return

    if len(scene_clips) > 1:
        scene_clips = [scene_clips[0]] + [
            c.with_effects([vfx.CrossFadeIn(crossfade)]) for c in scene_clips[1:]
        ]
        final = concatenate_videoclips(scene_clips, method="compose", padding=-crossfade)
    else:
        final = scene_clips[0]

    final = final.with_effects([vfx.FadeIn(0.3), vfx.FadeOut(0.3)])
    final.write_videofile(str(output_path), fps=24, codec="libx264", audio_codec="aac", logger=None)
    console.print(f"[green]✓[/green] {output_name} ({final.duration:.1f}s)")


def _get_font(lang: str) -> str:
    if lang == "ko":
        candidates = [
            "/System/Library/Fonts/Supplemental/NotoSansKR-Regular.otf",
            "/Library/Fonts/NotoSansKR-Regular.otf",
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
        for c in candidates:
            if Path(c).exists():
                return c
        console.print("[yellow]Noto Sans KR font not found — falling back to system default[/yellow]")
    return "Arial"
