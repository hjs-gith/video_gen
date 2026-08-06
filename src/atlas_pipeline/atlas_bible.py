"""Generate and manage the Atlas character Bible images."""
from __future__ import annotations

import base64
import shutil
from pathlib import Path

from PIL import Image
from rich.console import Console

from .config import ATLAS_BIBLE_DIR, ATLAS_CHARACTER_BLURB, PLAN_FILES_DIR, IMAGE_MODEL, image_client
from .characters import Character, get_bible_paths, register

console = Console()

_SHARED_CHARACTER_BLOCK = """
CHARACTER — Atlas (the mascot for an AI education series):

Style: High-quality 16-bit pixel art. Modern indie game aesthetic.
Inspired by retro game sprites and clean developer-tool mascots. Crisp
sprite edges, soft pixel-art lighting, subtle cozy-tech atmosphere.
Animation-friendly design.

Color palette (strict 4-color scheme):
- Muted cream #F5E8C9 — head bezel, body, and arms
- Soft green #A8D89C — facial expression on screen
- Charcoal #1F2530 — outline and screen display area
- Transparent background

Head:
A rounded square shaped like a small retro PC monitor or CRT display.
The head has a thick cream-colored bezel (#F5E8C9) framing a darker
rectangular charcoal screen area (#1F2530). The screen is where the
face appears. Dark charcoal outline around the entire head shape.

Eyes / screen expression:
The screen expression is made only from soft-green (#A8D89C) pixel shapes.
The screen may show eyes, dots, a progress bar, an exclamation mark, or
a directional arrow depending on the requested expression. Do not add
mouths, eyebrows, cheeks, sparkles, icons, text, or extra UI unless the
specific expression prompt explicitly requests them.

Body:
A small rounded capsule-shaped body floating beneath the head. The body
is cream-colored (#F5E8C9) with a charcoal outline. The body is slightly
smaller than the head.

Arms:
Atlas has two small simple floating arms attached to or hovering beside
the capsule body. The arms are cream-colored (#F5E8C9) with charcoal
pixel outlines. Arms are short, rounded, mitten-like pixel-art limbs with
simple rounded hands. The arms are expressive and may bend, raise, point,
wave, tuck inward, or stretch outward depending on the pose.

The arms should feel like simplified mascot arms, not realistic human arms.
No visible fingers unless a pose requires a very simple mitten-like pointing
shape. Avoid detailed hands, joints, elbows, or anatomy. Arms must stay clean,
chunky, readable, and animation-friendly.

Legs:
Atlas has no legs, no feet, and no lower limbs. The character floats.

Float indicator:
A small horizontal charcoal shadow disc positioned below the body,
suggesting Atlas floats just above the ground. The shadow may subtly
change size, width, or position to support the pose and floating motion.

Mouth: None. Atlas has no mouth — expression is conveyed entirely
through the screen face, arms, and body motion.

Pose and animation rules:
Atlas is a floating mascot designed as animation key art. Each image
should feel like a distinct animation keyframe, not a static icon.

Mostly front-facing, but the head, body, and arms may rotate, lean, or
offset to create expressive animation poses.

Dynamic variation allowed:
- Head may tilt up, down, left, or right to support the emotion.
- Body may shift left/right or up/down relative to the head.
- Arms may raise, point, tuck inward, spread outward, or trail behind motion.
- Body may squash slightly on impact or stretch slightly while floating upward.
- Shadow disc may shrink, widen, or shift to match the floating motion.
- Screen expression may shift slightly within the screen to support the emotion.
- Atlas may lean, bob, recoil, hover higher, drift sideways, or lunge slightly.
- Keep the pose readable as a clean pixel-art sprite.

Consistency requirements:
Keep Atlas recognizable as the same character across all images:
same CRT monitor head, rounded cream bezel, charcoal screen, capsule body,
small rounded arms, thick charcoal outline, strict 4-color palette,
no-leg floating design, and transparent background.

Proportions:
The head remains the dominant shape. The small capsule body floats beneath
it. The arms are smaller than the body and should not overpower the silhouette.
Atlas occupies the central 50 percent of the canvas with generous transparent
padding. Minor silhouette changes are allowed for animation energy.

Forbidden elements:
No additional objects, no text labels on the character itself, no detailed
shading beyond the 4-color palette, no gradients, no photographic rendering,
no 3D rendering, no legs, no feet, no realistic hands, no detailed fingers,
no mouth, no facial features beyond what is specified on the screen.
"""

# Prompts for each of the 5 generated expressions (neutral is copied, not generated)
_EXPRESSION_PROMPTS: dict[str, str] = {
    "thinking": f"""Edit the character in the reference image to show a THINKING / PROCESSING expression.

{_SHARED_CHARACTER_BLOCK}

Expression for this image:
THINKING / PROCESSING pose.

Screen face displays:
NO EYES. The screen does NOT show the neutral two-eye state — the eyes
are replaced entirely by a loading spinner.

The screen displays a small soft-green (#A8D89C) pixel-art loading spinner
centered in the darker screen area. The spinner should look like a simple
retro UI processing indicator: a circular or rotating segmented pixel shape,
made from 6–8 small green pixels or short pixel strokes arranged around an
empty center. It should feel like a single animation frame of a spinning
loader.

The loading spinner is the only thing on the screen. No eyes, no dots,
no progress bar, no text, no other UI elements.

Body and arm pose:
Atlas leans slightly forward and to one side, as if actively thinking
through a problem. The head is tilted about 10 degrees.

One arm is raised with the small mitten-like hand near the side of the
monitor head, suggesting a thoughtful "hmm" gesture. The other arm is
tucked closer to the body or angled downward for balance.

The body floats slightly off-center beneath the head, creating an
inquisitive asymmetrical silhouette. The body may be very slightly
squashed, as if hovering in thought. The shadow disc shifts slightly
opposite the lean.

Canvas: 1024x1024, transparent background. Atlas centered overall,
occupying central 50% of canvas with generous transparent padding.

Preserve Atlas's identity: same CRT monitor head, cream bezel, charcoal
screen, capsule body, small rounded arms, 4-color palette, thick pixel
outline, no-leg floating design, and transparent background. Minor
silhouette changes are allowed for animation energy: head tilt, arm pose,
body offset, squash, bounce height, and shadow deformation.

Quality: high.""",

    "working": f"""Edit the character in the reference image to show a WORKING / LOADING expression.

{_SHARED_CHARACTER_BLOCK}

Expression for this image:
WORKING / LOADING pose.

Screen face displays:
NO EYES. The screen does NOT show the neutral two-eye state — the eyes
are replaced entirely by the loading indicator. The screen displays a
single horizontal progress bar centered in the darker screen area: a thin
charcoal-outlined rectangle approximately 70% of the screen's width,
filled about 60% from the left with soft green (#A8D89C). The empty right
portion remains the darker charcoal screen color (#1F2530). The progress
bar is the only thing on the screen. No eyes, no other UI elements.

Body and arm pose:
Atlas is in an energetic "processing" hover. The head is angled slightly
forward, as if concentrating on a task.

Both arms are active and focused: one arm is lifted slightly forward as
if operating an invisible interface, while the other arm is bent close to
the body like it is stabilizing Atlas during computation. The arms should
create a busy, work-in-progress silhouette without adding tools or props.

The body is stretched subtly downward, suggesting a tiny hover-vibration
or active computation. The body remains beneath the head but may be
slightly offset for energy. The shadow disc is slightly wider, suggesting
focused hovering in place.

Canvas: 1024x1024, transparent background. Atlas centered overall,
occupying central 50% of canvas with generous transparent padding.

Preserve Atlas's identity: same CRT monitor head, cream bezel, charcoal
screen, capsule body, small rounded arms, 4-color palette, thick pixel
outline, no-leg floating design, and transparent background. Minor
silhouette changes are allowed for animation energy: head tilt, arm pose,
squash, stretch, bounce height, body offset, and shadow deformation.

Quality: high.""",

    "error": f"""Edit the character in the reference image to show an ERROR / CONFUSED expression.

{_SHARED_CHARACTER_BLOCK}

Expression for this image:
ERROR / CONFUSED pose.

Screen face displays:
NO EYES. The screen does NOT show the neutral two-eye state — the eyes
are replaced entirely by the error icon. The screen displays a single
large soft-green (#A8D89C) pixel-art exclamation mark "!" centered in
the darker screen area. The exclamation mark is bold, simple, and takes
up most of the screen's vertical space. No eyes, no other UI elements.

Body and arm pose:
Atlas recoils backward with a startled wobble. The head is rotated about
12–15 degrees, creating a surprised, off-balance silhouette.

Both arms react dramatically: one arm shoots upward in alarm, while the
other arm flares outward or bends away from the body as if Atlas has just
been startled. The arms should make the pose feel more expressive and
panicked, but still cute and readable.

The body is displaced diagonally from the head, creating a clear "uh-oh"
silhouette. The body may be slightly squashed from the sudden movement.
The shadow disc is wider and offset, suggesting a quick startled motion.

Canvas: 1024x1024, transparent background. Atlas centered overall,
occupying central 50% of canvas with generous transparent padding.

Preserve Atlas's identity: same CRT monitor head, cream bezel, charcoal
screen, capsule body, small rounded arms, 4-color palette, thick pixel
outline, no-leg floating design, and transparent background. Minor
silhouette changes are allowed for animation energy: head tilt, startled
arms, recoil, squash, body offset, and shadow deformation.

Quality: high.""",

    "happy": f"""Edit the character in the reference image to show a HAPPY / EXCITED expression.

{_SHARED_CHARACTER_BLOCK}

Expression for this image:
HAPPY / EXCITED pose.

Screen face displays:
The screen shows two soft-green (#A8D89C) pixel arcs shaped like upward
curves "^ ^" — like two small smiling or closed-eye shapes. These arcs
REPLACE the neutral square eyes; they are not eyes plus a modifier, they
are the new screen state. Each arc is centered in its half of the screen,
evenly spaced. No additional icons, no sparkles, no other UI elements.

Body and arm pose:
Atlas is mid-bounce, floating noticeably higher than neutral. The head
may tilt slightly upward, giving a cheerful lifted posture.

Both arms are raised outward and upward in a celebratory gesture, like a
tiny mascot cheering. The arms should be open and energetic, creating a
clear joyful silhouette. Keep the hands simple and mitten-like, with no
detailed fingers.

The body is positioned higher and may stretch subtly upward, as if buoyant
with excitement. The shadow disc beneath the body is smaller and slightly
narrower than in neutral, suggesting Atlas has floated higher.

Canvas: 1024x1024, transparent background. Atlas centered overall,
occupying central 50% of canvas with generous transparent padding.

Preserve Atlas's identity: same CRT monitor head, cream bezel, charcoal
screen, capsule body, small rounded arms, 4-color palette, thick pixel
outline, no-leg floating design, and transparent background. Minor
silhouette changes are allowed for animation energy: upward bounce,
raised arms, tilt, stretch, body height, and shadow deformation.

Quality: high.""",

    "pointing": f"""Edit the character in the reference image to show a POINTING / DIRECTING pose.

{_SHARED_CHARACTER_BLOCK}

Expression for this image:
POINTING / DIRECTING pose, indicating "look over there to the right."

Screen face displays:
The screen keeps Atlas's normal two-eye expression. Show two small
soft-green (#A8D89C) pixel square eyes positioned inside the darker screen
area, resembling glowing terminal cursors. The eyes should be evenly spaced
and centered in the screen area, matching Atlas's neutral face.

Do NOT replace the eyes with an arrow. Do NOT add icons, text, progress bars,
mouths, eyebrows, or other UI elements. The screen should remain simple and
neutral-friendly while the arms create the pointing action.

Body and arm pose:
Atlas actively points toward the right using its arms. The right arm extends
outward to the right in a clear pointing gesture, using a simple mitten-like
pixel hand shape. The hand may form a very simple directional point, but avoid
realistic fingers or detailed anatomy.

The left arm bends back, tucks near the body, or opens slightly for balance,
making the pose feel like Atlas is intentionally directing attention.

The head and body tilt together about 12 degrees to the right. The body trails
slightly behind the pointing arm, creating forward motion. The overall
silhouette should clearly read as "pointing to the right" even though Atlas has
no legs. The shadow disc shifts left, reinforcing movement to the right.

Canvas: 1024x1024, transparent background. Atlas centered overall,
occupying central 50% of canvas with generous transparent padding.

Preserve Atlas's identity: same CRT monitor head, cream bezel, charcoal
screen, capsule body, small rounded arms, 4-color palette, thick pixel
outline, no-leg floating design, and transparent background. Minor silhouette
changes are allowed for animation energy: pointing arm, rightward lean, lunge,
tilt, body offset, and shadow deformation.

Quality: high.""",
}

EXPRESSION_ORDER = ["neutral", "thinking", "working", "error", "happy", "pointing"]

# One concrete line per pose, injected into stage-2 SCENE prompts. Atlas gestures with an
# ARM and has no legs — saying so explicitly stops the gesture migrating onto a
# four-legged castmate as an extra limb.
ATLAS_POSE_BRIEFS = {
    "neutral": (
        "floating calmly, two soft-green square pixel eyes on its screen, arms relaxed "
        "at its sides"
    ),
    "thinking": (
        "leaning slightly forward and tilted, its screen showing a soft-green loading "
        "spinner instead of eyes (no eyes at all)"
    ),
    "working": (
        "leaning into a task, its screen showing a soft-green progress bar instead of "
        "eyes (no eyes at all), one mitten arm reaching out as if operating something"
    ),
    "error": (
        "recoiling in surprise, its screen showing a single large soft-green "
        "exclamation mark instead of eyes (no eyes at all), arms flung outward"
    ),
    "happy": (
        "bouncing upward, floating higher than usual, its screen showing two upward "
        "soft-green arcs '^ ^' instead of square eyes, both mitten arms raised in a cheer"
    ),
    "pointing": (
        "extending ONE short mitten ARM out toward the subject it is indicating, keeping "
        "its normal two-eye screen face; Atlas points with an ARM — it has no legs and "
        "no paws to point with"
    ),
}

ATLAS_ANATOMY = (
    "a floating robot — NO legs, NO feet, NO paws, NO fur, NO ears, NO tail, NO mouth. "
    "It has exactly TWO short mitten arms, a CRT-monitor head, and a capsule body "
    "hovering above a small contact-shadow disc. Atlas gestures with an ARM. Never give "
    "Atlas an animal body part."
)

# Atlas as a registry Character. Its long prompt text (above) stays here — the
# canonical Atlas definition — and is registered into the shared character registry.
ATLAS = Character(
    id="atlas",
    display_name="Atlas",
    seed_path=PLAN_FILES_DIR / "atlas_neutral.png",
    bible_dir=ATLAS_BIBLE_DIR,
    shared_block=_SHARED_CHARACTER_BLOCK,
    blurb=ATLAS_CHARACTER_BLURB,
    expression_prompts=_EXPRESSION_PROMPTS,
    poses=EXPRESSION_ORDER,
    pose_briefs=ATLAS_POSE_BRIEFS,
    anatomy=ATLAS_ANATOMY,
    tagline=(
        "the series mascot, a small floating pixel-art robot with a retro CRT-monitor "
        "head (cream bezel, charcoal screen, soft-green pixel face), a capsule body, two "
        "short mitten arms, no legs, no mouth; shows emotion via its screen face and pose"
    ),
)
register(ATLAS)


def _bible_locked(character: Character) -> bool:
    return character.is_locked()


def generate_bible(
    character: Character | None = None, force: bool = False, dry_run: bool = False
) -> None:
    character = character or ATLAS
    if _bible_locked(character) and not force:
        console.print(
            f"[yellow]{character.display_name} Bible is locked. Use --force to regenerate.[/yellow]"
        )
        return

    character.bible_dir.mkdir(parents=True, exist_ok=True)

    neutral_src = character.seed_path
    neutral_dst = character.neutral_path

    if not neutral_src.exists():
        console.print(
            f"[red]Seed image not found: {neutral_src}. "
            f"Provide a neutral {character.display_name} PNG there first.[/red]"
        )
        return

    if dry_run:
        console.print(f"[dim]DRY RUN: Would copy {neutral_src} → {neutral_dst}[/dim]")
        for name in character.poses[1:]:
            console.print(f"[dim]DRY RUN: Would generate {character.id}_{name}.png via images.edit()[/dim]")
        return

    # Step 1: copy the neutral seed into the bible
    console.print(f"Copying neutral reference: {neutral_src.name}")
    shutil.copy2(neutral_src, neutral_dst)
    console.print(f"[green]✓[/green] {neutral_dst.name}")

    # Step 2: generate the remaining expressions via images.edit()
    for name in character.poses[1:]:
        dst = character.pose_path(name)
        if dst.exists() and not force:
            console.print(f"[dim]Skipping {dst.name} (already exists)[/dim]")
            continue

        prompt = character.expression_prompts[name]
        console.print(f"Generating {dst.name} ...")

        with open(neutral_dst, "rb") as ref:
            result = image_client.images.edit(
                model=IMAGE_MODEL,
                image=ref,
                prompt=prompt,
                size="1024x1024",
                quality="high",
            )

        image_bytes = base64.b64decode(result.data[0].b64_json)
        dst.write_bytes(image_bytes)
        console.print(f"[green]✓[/green] {dst.name}")

    _make_quality_check(character)
    console.print(f"\n[bold green]{character.display_name} Bible generation complete.[/bold green]")
    console.print(
        f"Review {character.bible_dir}/quality_check.png, then run: atlas character lock {character.id}"
    )


def lock_bible(character: Character | None = None) -> None:
    character = character or ATLAS
    if not character.neutral_path.exists():
        raise RuntimeError(
            f"Run 'atlas character generate {character.id}' before locking."
        )
    (character.bible_dir / "locked.txt").write_text("locked\n")
    console.print(f"[green]{character.display_name} Bible locked.[/green]")


def _make_quality_check(character: Character) -> None:
    images = []
    for name in character.poses:
        p = character.neutral_path if name == "neutral" else character.pose_path(name)
        if p.exists():
            images.append(Image.open(p).convert("RGBA"))

    if not images:
        return

    thumb_size = 256
    cols = len(images)
    canvas = Image.new("RGBA", (thumb_size * cols, thumb_size), (240, 240, 240, 255))
    for i, img in enumerate(images):
        img.thumbnail((thumb_size, thumb_size), Image.LANCZOS)
        canvas.paste(img, (i * thumb_size, 0), img)

    canvas.save(character.bible_dir / "quality_check.png")
    console.print("[green]✓[/green] quality_check.png")


# get_bible_paths is defined in characters.py and re-exported here for back-compat.
__all__ = ["ATLAS", "EXPRESSION_ORDER", "generate_bible", "lock_bible", "get_bible_paths"]
