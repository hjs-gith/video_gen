"""Stage 3: TTS audio generation and video assembly."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from rich.console import Console

from .config import (
    TTS_MODEL,
    TTS_PROVIDER,
    TTS_SPEED,
    TTS_VOICE_EN,
    TTS_VOICE_KO,
    tts_client,
)
from .utils import log_api_call

console = Console()

_DURATION_TOLERANCE_SEC = 0.5


def _frame_index(t: float, n: int, flip_interval: float) -> int:
    """Which of `n` frames is shown at time `t` when flipping every `flip_interval`."""
    return int(t / flip_interval) % n


def _float_offset(t: float, amplitude: float, period: float) -> int:
    """Vertical pixel offset of the floating foreground layer at time `t`.

    A smooth sine bob: 0 at t=0, swinging ±`amplitude` px every `period` seconds.
    """
    return int(round(amplitude * math.sin(2 * math.pi * t / period)))


def _audio_path(audio_dir: Path, sid: str, lang: str) -> Path | None:
    """Resolve an existing per-scene audio file regardless of provider extension.

    OpenAI TTS writes .mp3; local Supertonic writes .wav. Returns the first that
    exists, or None.
    """
    for ext in ("mp3", "wav"):
        p = audio_dir / f"{sid}_{lang}.{ext}"
        if p.exists():
            return p
    return None


def generate_tts(
    script: dict,
    ep_dir: Path,
    lang: str = "en",
    scene_filter: str | None = None,
    speed: float | None = None,
    force: bool = False,
    dry_run: bool = False,
    provider: str | None = None,
) -> None:
    audio_dir = ep_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    provider = provider or TTS_PROVIDER
    speed = TTS_SPEED if speed is None else speed
    narration_key = "en" if lang == "en" else "ko"
    episode_id = script.get("meta", {}).get("term", "unknown")

    ext = "wav" if provider == "supertonic" else "mp3"

    for scene in script.get("scenes", []):
        sid = scene["scene_id"]
        if scene_filter and sid != scene_filter:
            continue

        out_path = audio_dir / f"{sid}_{lang}.{ext}"
        existing = _audio_path(audio_dir, sid, lang)
        if existing and not force:
            console.print(f"[dim]{existing.name} exists — skipping[/dim]")
            continue

        narration = scene.get("narration", {}).get(narration_key, "")
        if not narration:
            console.print(f"[yellow]No {lang} narration for {sid} — skipping[/yellow]")
            continue

        if dry_run:
            console.print(f"[dim]DRY RUN: Would generate {out_path.name} ({provider})[/dim]")
            continue

        # Switching providers can leave a stale file at the other extension; drop it
        # so assembly doesn't pick up the old voice.
        if existing and existing != out_path:
            existing.unlink()

        if provider == "supertonic":
            console.print(f"TTS {sid} ({lang}, supertonic) ...")
            from .tts_local import synthesize_to_file

            synthesize_to_file(narration, lang, out_path, speed)
            log_api_call(
                stage=f"3a_tts_local_{lang}",
                model="supertonic-3",
                tokens_in=len(narration.split()),
                tokens_out=0,
                cost_usd=0.0,
                episode_id=episode_id,
                scene_id=sid,
                extra={"provider": "supertonic"},
            )
        else:
            voice = TTS_VOICE_EN if lang == "en" else TTS_VOICE_KO
            console.print(f"TTS {sid} ({lang}, openai, speed={speed}) ...")
            response = tts_client.audio.speech.create(
                model=TTS_MODEL,
                voice=voice,
                input=narration,
                speed=speed,
            )
            out_path.write_bytes(response.content)
            log_api_call(
                stage=f"3a_tts_{lang}",
                model=TTS_MODEL,
                tokens_in=len(narration.split()),
                tokens_out=0,
                cost_usd=len(narration) * 0.000015,
                episode_id=episode_id,
                scene_id=sid,
                extra={"speed": speed, "provider": "openai"},
            )

        actual_dur = _audio_duration(out_path)
        target_dur = scene.get("duration_sec", 0)
        if abs(actual_dur - target_dur) > _DURATION_TOLERANCE_SEC:
            console.print(
                f"  [yellow]Duration mismatch {sid}: audio={actual_dur:.1f}s, script={target_dur:.1f}s[/yellow]"
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
        VideoClip,
        concatenate_videoclips,
        vfx,
    )

    crossfade = 0.4
    tail_gap = 0.8        # uniform pause held after each (trimmed) narration
    silence_thresh = 0.02  # ~-34 dBFS; quieter than this is treated as silence
    keep_tail = 0.10     # natural buffer kept after the last speech sample
    flip_interval = 0.5  # legacy: seconds per frame when alternating A/B (~2 fps)
    float_amplitude = 10  # px the foreground floats up/down (layered scenes)
    float_period = 2.5    # seconds per full up-down float cycle
    scene_clips = []
    for scene in script.get("scenes", []):
        sid = scene["scene_id"]

        # Preferred: a static background layer + a transparent foreground that floats.
        # Fallback (older episodes): the two-frame A/B alternation.
        img_bg = ep_dir / "images" / f"{sid}_bg.png"
        img_fg = ep_dir / "images" / f"{sid}_fg.png"
        img_a = ep_dir / "images" / f"{sid}_a.png"
        img_b = ep_dir / "images" / f"{sid}_b.png"
        if not (img_bg.exists() or img_a.exists() or img_b.exists()):
            console.print(f"[yellow]No image for {sid} — skipping scene[/yellow]")
            continue

        # Pick audio (provider-agnostic: .mp3 or .wav)
        audio_path = _audio_path(ep_dir / "audio", sid, lang)
        if audio_path is None:
            console.print(f"[yellow]No audio for {sid} ({lang}) — skipping scene[/yellow]")
            continue

        audio_clip = AudioFileClip(str(audio_path))
        # Trim any TTS trailing silence so the gap between scenes is uniform
        end = min(_speech_end(audio_clip, silence_thresh) + keep_tail, audio_clip.duration)
        audio_clip = audio_clip.subclipped(0, end)
        duration = audio_clip.duration
        hold = duration + tail_gap  # linger on the frame after narration ends

        if img_bg.exists():
            # Layered parallax: static background, foreground gently floating over it.
            bg_clip = ImageClip(str(img_bg)).with_duration(hold)
            w, h = bg_clip.size
            base_layers = [bg_clip]
            if img_fg.exists():
                fg_clip = (
                    ImageClip(str(img_fg), transparent=True)
                    .with_duration(hold)
                    .with_position(
                        lambda t, a=float_amplitude, p=float_period: (0, _float_offset(t, a, p))
                    )
                )
                base_layers.append(fg_clip)
        else:
            # Legacy A/B: alternate every flip_interval across `hold`. One frame -> static.
            frame_paths = [p for p in (img_a, img_b) if p.exists()]
            if len(frame_paths) == 1:
                img_clip = ImageClip(str(frame_paths[0])).with_duration(hold)
                w, h = img_clip.size
            else:
                # Pre-load the frames once and switch by time — far cheaper than
                # building (and compositing) dozens of short ImageClips per scene.
                frames = [ImageClip(str(p)).get_frame(0) for p in frame_paths]
                n = len(frames)

                def _make_frame(t, _frames=frames, _n=n, _fi=flip_interval):
                    return _frames[_frame_index(t, _n, _fi)]

                img_clip = VideoClip(frame_function=_make_frame, duration=hold)
                h, w = frames[0].shape[:2]
            base_layers = [img_clip]

        layers = list(base_layers)

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
