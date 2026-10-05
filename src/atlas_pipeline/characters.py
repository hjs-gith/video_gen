"""Character registry — the on-model recurring characters in the series.

Historically the pipeline had exactly one character (Atlas), hardcoded everywhere.
This module generalizes that into a registry so any number of characters can be
defined once and then generated as pose "bibles", written into scripts, and
rendered on-model — including two characters together in one scene.

A character is defined by:
  - a neutral SEED image (e.g. seeds/<id>_neutral.png), hand-made/curated,
  - a canonical text description (`shared_block`) + a compact `blurb`,
  - a set of expression/pose edit-prompts (built from the seed via images.edit).

Atlas registers itself from `atlas_bible.py` (which owns its long prompt text);
new characters register from their own definition module. `_bootstrap()` imports
those definition modules lazily so this module has no import cycle with them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import ROOT

CHARACTERS_DIR = ROOT / "characters"


@dataclass(frozen=True)
class Character:
    """One on-model character and where its bible lives."""

    id: str
    display_name: str
    seed_path: Path            # neutral seed PNG (input to bible generation)
    bible_dir: Path            # holds <id>_neutral.png, <id>_<pose>.png, locked.txt
    shared_block: str          # canonical description, embedded in pose prompts
    blurb: str                 # compact description injected into stage-2 prompts
    expression_prompts: dict   # pose -> full edit prompt (for poses[1:])
    poses: list                # ordered; poses[0] is the (copied) neutral base
    tagline: str = ""          # one-line description for the stage-1 CAST prompt
    # pose -> one concrete sentence, injected into stage-2 SCENE prompts. Without this
    # the scene prompt carries only the bare pose word ("pointing"), which has no owner
    # and bleeds onto the other character in multi-character scenes.
    pose_briefs: dict = field(default_factory=dict)
    # Inviolable body rules, e.g. "exactly four legs — never a fifth limb". Stops limbs
    # and features migrating between characters that share a scene.
    anatomy: str = ""

    def pose_brief(self, pose: str) -> str:
        return self.pose_briefs.get(pose) or f"a {pose} pose"

    @property
    def neutral_path(self) -> Path:
        return self.bible_dir / f"{self.id}_neutral.png"

    def pose_path(self, pose: str) -> Path:
        return self.bible_dir / f"{self.id}_{pose}.png"

    def is_locked(self) -> bool:
        return (self.bible_dir / "locked.txt").exists()


_REGISTRY: dict[str, Character] = {}
_BOOTSTRAPPED = False


def register(character: Character) -> None:
    """Add (or replace) a character in the registry."""
    _REGISTRY[character.id] = character


def _bootstrap() -> None:
    """Import character-definition modules once so they self-register.

    Done lazily (not at module import) to avoid an import cycle: the definition
    modules import `Character`/`register` from here.
    """
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    _BOOTSTRAPPED = True
    from . import atlas_bible  # noqa: F401  — registers Atlas
    from . import character_byte  # noqa: F401  — registers Byte
    # To add a character: create its definition module and import it here so it
    # self-registers, e.g.  `from . import character_<id>  # noqa: F401`.


def get_character(cid: str) -> Character | None:
    _bootstrap()
    return _REGISTRY.get(cid)


def all_characters() -> list[Character]:
    _bootstrap()
    return list(_REGISTRY.values())


def is_registered(cid: str) -> bool:
    return get_character(cid) is not None


def scene_characters(scene: dict) -> list[tuple[Character, str]]:
    """Resolve which characters appear in a scene, and with what pose.

    Supports the new `characters: [{name, pose}]` array and the legacy
    `atlas_in_scene`/`atlas_pose` fields. Unknown names are skipped. Pose defaults
    to "neutral"; beat-based pose inference for legacy scripts lives in stage 2.
    """
    out: list[tuple[Character, str]] = []
    entries = scene.get("characters")
    if entries:
        for e in entries:
            char = get_character(e.get("name", ""))
            if char is not None:
                out.append((char, e.get("pose") or "neutral"))
    elif scene.get("atlas_in_scene"):
        char = get_character("atlas")
        if char is not None:
            pose = scene.get("atlas_pose") or scene.get("pose_hint") or "neutral"
            out.append((char, pose))
    return out


def cast_block() -> str:
    """Render the registered cast as a block for the stage-1 script prompt."""
    lines = []
    for c in all_characters():
        tag = c.tagline or c.blurb.split("\n", 1)[0]
        lines.append(f'- {c.display_name} (name: "{c.id}") — {tag}')
        lines.append(f"  Poses: {', '.join(c.poses)}. Pick the one that fits the scene.")
    return "\n".join(lines)


def get_bible_paths(character: Character, pose: str) -> list[Path]:
    """Neutral + pose references for a character (used to condition frame A)."""
    paths = [character.neutral_path]
    if pose and pose != "neutral":
        pp = character.pose_path(pose)
        if pp.exists():
            paths.append(pp)
    return [p for p in paths if p.exists()]


def canonical_refs(character: Character, pose: str) -> list[Path]:
    """A single best reference for a character — its pose image, else neutral.

    Used for multi-character scenes so conditioning stays to ~one image per
    character (passing every character's full neutral+pose set dilutes fidelity).
    """
    pp = character.pose_path(pose)
    if pose and pose != "neutral" and pp.exists():
        return [pp]
    return [character.neutral_path] if character.neutral_path.exists() else []


def reference_plan(
    present: list[tuple[Character, str]]
) -> list[tuple[Character, str, list[Path]]]:
    """Ordered (character, pose, refs) — the single source of truth for which reference
    images get sent, for whom, and in what order.

    Stage 2 derives BOTH the API image list and the prompt's "reference image N = X"
    map from this, so the two can never disagree. Characters whose bible files are
    missing contribute no refs and are simply absent from the plan's numbering.
    """
    if len(present) == 1:
        char, pose = present[0]
        return [(char, pose, get_bible_paths(char, pose))]
    return [(char, pose, canonical_refs(char, pose)) for char, pose in present]


def default_seed_path(cid: str) -> Path:
    """Conventional seed location for a new character."""
    from .config import SEEDS_DIR

    return SEEDS_DIR / f"{cid}_neutral.png"


def default_bible_dir(cid: str) -> Path:
    """Conventional bible directory for a new character."""
    return CHARACTERS_DIR / cid


# Titles reused when expanding short pose deltas into full prompts (below).
_POSE_TITLES = {
    "thinking": "THINKING / PROCESSING expression",
    "working": "WORKING / LOADING expression",
    "error": "ERROR / CONFUSED expression",
    "happy": "HAPPY / EXCITED expression",
    "pointing": "POINTING / DIRECTING pose",
}


def make_expression_prompts(
    shared_block: str,
    pose_deltas: dict[str, str],
    canvas: str = "1024x1024",
) -> dict[str, str]:
    """Expand short per-pose deltas into full bible edit-prompts.

    Lets a NEW character be defined with just a description + a one-line delta per
    pose, instead of authoring a full prompt each. (Atlas keeps its own bespoke,
    hand-tuned prompts and does not use this.)
    """
    prompts: dict[str, str] = {}
    for pose, delta in pose_deltas.items():
        title = _POSE_TITLES.get(pose, f"{pose.upper()} pose")
        prompts[pose] = (
            f"Edit the character in the reference image to show a {title}.\n\n"
            f"{shared_block}\n\n"
            f"Expression / pose for this image:\n{delta}\n\n"
            f"Canvas: {canvas}, transparent background. The character is centered, "
            "occupying the central 50-65% of the canvas with generous transparent "
            "padding. Show the WHOLE body — do not crop any limb or the tail.\n\n"
            "IDENTITY IS FIXED, POSTURE IS NOT. Preserve the character's identity "
            "exactly: same proportions, same color palette, same outline weight, same "
            "facial features and markings, same design language as the reference image. "
            "But the body posture, limb positions, head angle, and camera viewing angle "
            "MUST change to express the pose described above. The reference image shows "
            "only the character's resting pose — treat it as a source of identity, NOT "
            "as a posture to copy. Do not simply reuse the reference's stance with small "
            "tweaks; re-pose the whole body so the pose reads clearly in silhouette."
            "\n\nQuality: high."
        )
    return prompts
