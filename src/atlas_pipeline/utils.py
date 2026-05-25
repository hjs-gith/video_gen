from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .config import EPISODES_OUTPUT_DIR, LOGS_DIR


def episode_dir(cluster_id: int, episode_number: int, term: str) -> Path:
    term_slug = term.lower().replace(" ", "_").replace("-", "_")
    name = f"c{cluster_id:02d}_e{episode_number:02d}_{term_slug}"
    path = EPISODES_OUTPUT_DIR / name
    path.mkdir(parents=True, exist_ok=True)
    (path / "images").mkdir(exist_ok=True)
    (path / "audio").mkdir(exist_ok=True)
    return path


def save_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def log_api_call(
    stage: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    episode_id: Optional[str] = None,
    scene_id: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "model": model,
        "episode_id": episode_id,
        "scene_id": scene_id,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost_usd,
    }
    if extra:
        record.update(extra)
    with open(LOGS_DIR / "api_calls.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def validate_script(script: dict) -> list[str]:
    from .atlas_bible import EXPRESSION_ORDER

    errors: list[str] = []
    meta = script.get("meta", {})
    scenes = script.get("scenes", [])

    if not scenes:
        errors.append("No scenes found")
        return errors

    actual = meta.get("actual_length_sec", 0)
    if not (30 <= actual <= 90):
        errors.append(f"actual_length_sec={actual} is outside 30–90s range")

    for s in scenes:
        sid = s.get("scene_id", "?")
        if not s.get("visual_intent"):
            errors.append(f"{sid}: missing visual_intent")
        narration = s.get("narration", {})
        if not narration.get("en"):
            errors.append(f"{sid}: missing narration.en")
        if not narration.get("ko"):
            errors.append(f"{sid}: missing narration.ko")
        if s.get("atlas_in_scene"):
            pose = s.get("atlas_pose")
            if pose not in EXPRESSION_ORDER:
                errors.append(
                    f"{sid}: atlas_in_scene is true but atlas_pose={pose!r} "
                    f"is missing or not one of {EXPRESSION_ORDER}"
                )

    return errors
