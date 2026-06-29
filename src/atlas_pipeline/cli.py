"""Atlas Pipeline CLI — entry point: atlas"""
from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _has_audio(ep_dir: Path, sid: str, lang: str) -> bool:
    """Per-scene audio exists in either provider format (.mp3 OpenAI / .wav local)."""
    return any((ep_dir / "audio" / f"{sid}_{lang}.{ext}").exists() for ext in ("mp3", "wav"))


@click.group()
def main():
    """AI Jargon Atlas — bilingual short-form video course pipeline."""


# ── Bible commands ────────────────────────────────────────────────────────────

@main.group()
def bible():
    """Manage the Atlas character Bible images."""


@bible.command("generate")
@click.option("--force", is_flag=True, help="Overwrite existing bible images.")
@click.option("--dry-run", is_flag=True, help="Print what would happen, make no API calls.")
def bible_generate(force, dry_run):
    """Copy neutral reference and generate 5 Atlas expression images."""
    from .atlas_bible import generate_bible
    generate_bible(force=force, dry_run=dry_run)


@bible.command("lock")
def bible_lock():
    """Lock the Bible after human QC approval."""
    from .atlas_bible import lock_bible
    lock_bible()


# ── Episode commands ──────────────────────────────────────────────────────────

@main.group()
def episode():
    """Run pipeline stages for an episode."""


@episode.command("run")
@click.argument("episode_number", type=int)
@click.option("--stages", default="1,2,3", help="Comma-separated stages to run (1, 2, 3).")
@click.option("--lang", default="en", type=click.Choice(["en", "ko"]), help="TTS voice language.")
@click.option("--overlay", default="ko", type=click.Choice(["en", "ko", "none"]), help="Text overlay language or none.")
@click.option("--scene", default=None, help="Only process this scene ID (e.g. S03).")
@click.option("--quality", default=None, type=click.Choice(["low", "medium", "high", "auto"]), help="Stage 2 image quality (default: config IMAGE_QUALITY). Lower = faster/cheaper.")
@click.option("--size", default=None, help="Stage 2 image size WxH, e.g. 1024x1024 (default: config IMAGE_SIZE).")
@click.option("--image-provider", default=None, type=click.Choice(["openai", "local"]), help="Stage 2 image provider (default: config IMAGE_PROVIDER=openai). 'local' needs your HTTP server running — see IMAGE_LOCAL_URL and docs/local_image_server.md.")
@click.option("--speed", default=None, type=float, help="Stage 3 TTS speech speed 0.25–4.0 (default: config TTS_SPEED).")
@click.option("--tts", "tts_provider", default=None, type=click.Choice(["supertonic", "openai"]), help="Stage 3 TTS provider (default: config TTS_PROVIDER=supertonic, local & free).")
@click.option("--force", is_flag=True, help="Overwrite existing outputs.")
@click.option("--dry-run", is_flag=True, help="Print what would happen, make no API calls.")
@click.option("--no-atlas", is_flag=True, help="Skip Atlas character Bible references.")
@click.option("--no-tts", is_flag=True, help="Stage 3: skip TTS and assemble from existing audio (no API cost).")
def episode_run(episode_number, stages, lang, overlay, scene, quality, size, image_provider, speed, tts_provider, force, dry_run, no_atlas, no_tts):
    """Run pipeline stages for EPISODE_NUMBER."""
    from .curriculum import get_episode
    from .stage1_script import build_script
    from .stage2_images import build_image_prompts, generate_images
    from .stage3_video import assemble_video, generate_tts
    from .utils import episode_dir, load_json, save_json

    ep = get_episode(episode_number)
    ep_dir = episode_dir(ep.cluster, ep.episode_number, ep.terms[0])
    script_path = ep_dir / "script.json"
    image_prompts_path = ep_dir / "image_prompts.json"

    stage_list = [s.strip() for s in stages.split(",")]

    if "1" in stage_list:
        console.rule("[bold]Stage 1: Script[/bold]")
        script = build_script(ep, dry_run=dry_run, force=force)
    else:
        if not script_path.exists():
            console.print("[red]script.json not found. Run stage 1 first.[/red]")
            return
        script = load_json(script_path)

    if "2" in stage_list and not dry_run or ("2" in stage_list and dry_run):
        console.rule("[bold]Stage 2: Images[/bold]")
        if not script:
            console.print("[yellow]No script data — skipping stage 2[/yellow]")
        else:
            image_prompts = build_image_prompts(script, overlay_lang=lang, size=size, quality=quality, dry_run=dry_run)
            if not dry_run:
                save_json(image_prompts, image_prompts_path)
            generate_images(image_prompts, ep_dir, scene_filter=scene, force=force, dry_run=dry_run, provider=image_provider)

    if "3" in stage_list:
        console.rule("[bold]Stage 3: Audio + Video[/bold]")
        if not script:
            if not script_path.exists():
                console.print("[red]script.json not found.[/red]")
                return
            script = load_json(script_path)
        if not no_tts:
            generate_tts(script, ep_dir, lang=lang, scene_filter=scene, speed=speed, force=force, dry_run=dry_run, provider=tts_provider)
        assemble_video(script, ep_dir, lang=lang, overlay=overlay, force=force, dry_run=dry_run)


@episode.command("status")
@click.argument("episode_number", type=int)
def episode_status(episode_number):
    """Show completion status for EPISODE_NUMBER."""
    from .curriculum import get_episode
    from .utils import episode_dir, load_json

    ep = get_episode(episode_number)
    ep_dir = episode_dir(ep.cluster, ep.episode_number, ep.terms[0])

    script_path = ep_dir / "script.json"
    has_script = script_path.exists()

    table = Table(title=f"Episode {episode_number}: {', '.join(ep.terms)}")
    table.add_column("Item")
    table.add_column("Status")

    def _status(ok: bool) -> str:
        return "[green]✓[/green]" if ok else "[red]✗[/red]"

    table.add_row("script.json", _status(has_script))

    if has_script:
        script = load_json(script_path)
        scenes = script.get("scenes", [])
        for s in scenes:
            sid = s["scene_id"]
            has_bg = (ep_dir / "images" / f"{sid}_bg.png").exists()
            has_fg = (ep_dir / "images" / f"{sid}_fg.png").exists()
            has_a = (ep_dir / "images" / f"{sid}_a.png").exists()
            has_b = (ep_dir / "images" / f"{sid}_b.png").exists()
            has_en = _has_audio(ep_dir, sid, "en")
            has_ko = _has_audio(ep_dir, sid, "ko")
            if has_bg or has_fg:
                img_status = (
                    "[green]BG+FG[/green]" if has_bg and has_fg
                    else "[yellow]partial[/yellow]"
                )
            else:
                img_status = (
                    "[green]A+B[/green]" if has_a and has_b
                    else "[yellow]partial[/yellow]" if has_a or has_b
                    else "[red]missing[/red]"
                )
            audio_status = f"EN={'✓' if has_en else '✗'} KO={'✓' if has_ko else '✗'}"
            table.add_row(sid, f"img:{img_status} audio:{audio_status}")

    mp4s = list(ep_dir.glob("*.mp4"))
    for mp4 in mp4s:
        table.add_row(mp4.name, "[green]✓[/green]")

    console.print(table)


@episode.command("regen")
@click.argument("episode_number", type=int)
@click.argument("scene_id")
@click.option("--quality", default=None, type=click.Choice(["low", "medium", "high", "auto"]), help="Image quality (default: config IMAGE_QUALITY).")
@click.option("--size", default=None, help="Image size WxH (default: config IMAGE_SIZE).")
@click.option("--image-provider", default=None, type=click.Choice(["openai", "local"]), help="Image provider (default: config IMAGE_PROVIDER). 'local' needs your HTTP server running.")
def episode_regen(episode_number, scene_id, quality, size, image_provider):
    """Re-generate the background + foreground image layers for one (awkward) scene (e.g. atlas episode regen 11 S03)."""
    from .curriculum import get_episode
    from .stage2_images import build_image_prompts, generate_images
    from .utils import episode_dir, load_json, save_json

    ep = get_episode(episode_number)
    ep_dir = episode_dir(ep.cluster, ep.episode_number, ep.terms[0])
    script_path = ep_dir / "script.json"
    if not script_path.exists():
        console.print("[red]script.json not found. Run stage 1 first.[/red]")
        return

    script = load_json(script_path)
    image_prompts = build_image_prompts(script, overlay_lang="en", size=size, quality=quality)
    save_json(image_prompts, ep_dir / "image_prompts.json")
    generate_images(image_prompts, ep_dir, scene_filter=scene_id, force=True, provider=image_provider)


@episode.command("list")
@click.option("--cluster", default=None, type=int, help="Filter by cluster number.")
def episode_list(cluster):
    """List all available episodes."""
    from .curriculum import load_all_episodes
    from .utils import episode_dir

    episodes = load_all_episodes()
    if cluster:
        episodes = [e for e in episodes if e.cluster == cluster]

    table = Table(title="Episodes")
    table.add_column("Ep#", justify="right")
    table.add_column("Cluster")
    table.add_column("Term(s)")
    table.add_column("Tier")
    table.add_column("Script")
    table.add_column("Images")
    table.add_column("Video")

    for ep in episodes:
        ep_dir = episode_dir(ep.cluster, ep.episode_number, ep.terms[0])
        has_script = (ep_dir / "script.json").exists()
        images_dir = ep_dir / "images"
        if images_dir.exists():
            bg_frames = {p.name[:-7] for p in images_dir.glob("*_bg.png")}
            a_frames = {p.name[:-6] for p in images_dir.glob("*_a.png")}
            b_frames = {p.name[:-6] for p in images_dir.glob("*_b.png")}
            img_count = len(bg_frames | (a_frames & b_frames))
        else:
            img_count = 0
        mp4s = len(list(ep_dir.glob("*.mp4")))
        table.add_row(
            str(ep.episode_number),
            f"C{ep.cluster}: {ep.cluster_name[:20]}",
            ", ".join(ep.terms),
            ep.tier,
            "✓" if has_script else "·",
            str(img_count) if img_count else "·",
            str(mp4s) if mp4s else "·",
        )

    console.print(table)


# ── Utility commands ──────────────────────────────────────────────────────────

@main.command()
def curriculum():
    """Pretty-print all available episodes from episodes_yaml/."""
    from .curriculum import load_all_episodes

    episodes = load_all_episodes()
    console.print(f"[bold]{len(episodes)} episode(s) available:[/bold]\n")

    current_cluster = None
    for ep in episodes:
        if ep.cluster != current_cluster:
            current_cluster = ep.cluster
            console.print(f"\n[bold underline]Cluster {ep.cluster}: {ep.cluster_name}[/bold underline]")
        prev = f" (after: {', '.join(ep.previous_episodes)})" if ep.previous_episodes else ""
        console.print(f"  [{ep.tier}] Ep{ep.episode_number}: {', '.join(ep.terms)}{prev}")


@main.command()
def costs():
    """Summarize API costs from logs/api_calls.jsonl."""
    from .config import LOGS_DIR

    log_path = LOGS_DIR / "api_calls.jsonl"
    if not log_path.exists():
        console.print("[yellow]No api_calls.jsonl found.[/yellow]")
        return

    records = []
    with open(log_path) as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    if not records:
        console.print("[yellow]No log records found.[/yellow]")
        return

    total = sum(r.get("cost_usd", 0) for r in records)

    by_stage: dict[str, float] = {}
    by_episode: dict[str, float] = {}
    for r in records:
        stage = r.get("stage", "unknown")
        ep = r.get("episode_id", "unknown")
        cost = r.get("cost_usd", 0)
        by_stage[stage] = by_stage.get(stage, 0) + cost
        by_episode[ep] = by_episode.get(ep, 0) + cost

    console.print(f"\n[bold]Total cost: ${total:.4f}[/bold]")

    t = Table(title="By Stage")
    t.add_column("Stage")
    t.add_column("Cost (USD)", justify="right")
    for stage, cost in sorted(by_stage.items(), key=lambda x: -x[1]):
        t.add_row(stage, f"${cost:.4f}")
    console.print(t)

    t2 = Table(title="By Episode")
    t2.add_column("Episode")
    t2.add_column("Cost (USD)", justify="right")
    for ep, cost in sorted(by_episode.items(), key=lambda x: -x[1]):
        t2.add_row(ep, f"${cost:.4f}")
    console.print(t2)
