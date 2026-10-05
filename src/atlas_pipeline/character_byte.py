"""Byte — the second recurring character: a small pixel-art golden puppy.

Where Atlas is the calm explainer robot, Byte is the eager learner: it reacts,
gets confused, and celebrates, which makes it useful for HOOK and payoff beats
and for two-hander scenes with Atlas.

Byte is defined the "new character" way — a canonical description plus one short
delta per pose — and `make_expression_prompts` expands those into full bible
edit-prompts. (Atlas keeps its own bespoke hand-tuned prompts.)
"""
from __future__ import annotations

from .characters import (
    Character,
    default_bible_dir,
    default_seed_path,
    make_expression_prompts,
    register,
)

# Poses match Atlas's set so BEAT_TO_POSE (config.py) resolves for Byte too.
POSE_ORDER = ["neutral", "thinking", "working", "error", "happy", "pointing"]

# Canonical description — embedded into every pose prompt to hold Byte on-model.
_SHARED_BLOCK = """
Character: BYTE — a small, cute pixel-art puppy (a golden-retriever-ish young dog).

Style: High-quality 16-bit pixel art. Modern indie game aesthetic. Clean, crisp
sprite edges, soft pixel-art lighting, subtle cozy-tech atmosphere. Byte is drawn
in the same pixel-art language as Atlas so they belong in one scene.

Strict palette:
- Cream-gold fur #FFE59D — the body, head, ears, legs and tail
- Warm gold shading and slightly lighter cream highlights within the fur
- Thick near-black charcoal-brown outline around the whole silhouette
- Green collar #449351 around the neck
- Round gold tag #FDBA55 hanging from the front of the collar
- Small coral-red tongue #F56C3A

Body: A young four-legged puppy with chibi proportions — a large round friendly
head relative to a small compact body, four short legs, and a fluffy tail. Soft
fluffy fur texture suggested with a few pixel clusters, never noisy.

POSTURE IS FREE. Byte is a real, mobile dog: it stands, walks, trots, runs,
leaps, crouches, digs, sniffs the ground, and stretches. The neutral reference
happens to show Byte sitting, but that sitting stance is NOT part of Byte's
identity and must not be carried into other poses. Re-pose the whole body and
change the camera angle (three-quarter view, full side profile, from behind)
whenever it makes the pose read better. Byte moves like a dog on four legs —
never like a person: it does not stand upright on its hind legs and its front
legs are legs and paws, not arms and hands.

Ears: Long, soft, floppy ears that hang down beside the cheeks and frame the
face. The ears are the main pose-readable feature — they lift, perk, droop, or
flatten depending on the emotion.

Face: Two large round solid-black pixel eyes, each with a single white highlight
pixel. A small rounded black nose centered above the muzzle. The mouth is a thin
dark pixel line; a small coral-red tongue may show below it.

Byte expresses emotion through EARS, EYES, TAIL, HEAD TILT, and PAWS — it has no
screen and no UI. Never give Byte a monitor head, screen face, text, icons, or
any Atlas feature. Byte is a dog, not a robot.

Keep Byte on-model: same chibi proportions, same strict palette, same thick
outline, same floppy-eared silhouette. Do not add clothing, accessories, hats,
or patterns. Byte carries no props beyond the green collar and its gold tag —
EXCEPT an item it is explicitly described as carrying in the pose below, which
it holds in its mouth (never in a paw, like a hand).
""".strip()

# Compact version injected into stage-2 scene prompts.
BYTE_CHARACTER_BLURB = (
    "BYTE (the puppy — match the character in the reference image):\n"
    "A small pixel-art golden puppy with chibi proportions: a big round head, a compact\n"
    "body, four short legs, and a fluffy tail. Cream-gold fur (#FFE59D) with a thick\n"
    "near-black outline, long floppy ears framing the face, two big round black eyes\n"
    "each with a white highlight pixel, and a small black nose. It wears a green collar\n"
    "(#449351) with a round gold tag (#FDBA55). Byte is a mobile four-legged dog — it\n"
    "stands, trots, leaps, crouches, digs, and sniffs, seen from whatever angle suits\n"
    "the action; do not default to sitting and facing the viewer, and never stand it\n"
    "upright on its hind legs like a person. Expression comes from its ears, eyes,\n"
    "tail, and head tilt — Byte has no screen, no UI, and no robot parts. Place Byte\n"
    "naturally inside the scene as a participant, not a flat cutout sticker."
)

_TAGLINE = (
    "the eager learner, a small pixel-art golden puppy with floppy ears, big black "
    "eyes, and a green collar with a gold tag; reacts, gets confused, and celebrates "
    "— good for hooks, payoffs, and playing off Atlas"
)

# One short delta per pose; make_expression_prompts() expands these into full prompts.
_POSE_DELTAS = {
    "thinking": (
        "Byte is STANDING ON ALL FOUR LEGS, stopped mid-stride, seen in three-quarter "
        "view. It tilts its head sharply to one side — the classic curious puppy "
        "head-tilt. One front paw is lifted off the ground and curled in the air, "
        "caught mid-step. One floppy ear cocks higher than the other. The eyes look up "
        "and off to one side; the mouth is closed, no tongue. The tail is raised and "
        "held still, slightly curled. Alert and pondering — NOT sitting."
    ),
    "working": (
        "Byte is FETCHING — trotting back with the result it was sent to get. Seen in "
        "three-quarter view, it moves briskly TOWARD the viewer at a confident, "
        "purposeful clip: one front leg reaches forward mid-stride while the opposite "
        "back leg pushes off, so the body is clearly in motion, not standing still. The "
        "head is carried high and proud, the floppy ears bounce upward with the trot, "
        "and the tail is raised and mid-wag.\n"
        "Held crosswise in its MOUTH (never in a paw) is ONE small rolled-up pixel "
        "scroll in series cream #F5E8C9 with a thick charcoal outline — the result Byte "
        "retrieved. Keep the scroll SMALL (no wider than Byte's head) and plain: no "
        "text, no glyphs, no seal, no ribbon, no glow, no accent color. The mouth is "
        "closed around the scroll, so no tongue shows. The eyes are the normal round "
        "black eyes with white highlights, bright and pleased with itself.\n"
        "Nothing else in the image: no other props, no icons, no ground, no motion "
        "lines. A dog proudly delivering what it was sent for — NOT sitting, NOT digging."
    ),
    "error": (
        "Byte is STARTLED and scrambling backward, seen in three-quarter view. It "
        "recoils away from something: the front legs are splayed and braced stiffly, "
        "the body leans back and away, and the weight is thrown onto its haunches, as "
        "if it just jumped back in fright. Both floppy ears droop flat and low against "
        "the head. The eyes are wide and round. The mouth hangs open in a small worried "
        "'o'. The tail tucks down between the back legs. Add ONE small coral-red pixel "
        "question mark floating in the air above and beside the head — nothing else, no "
        "other icons or text."
    ),
    "happy": (
        "Byte is MID-LEAP AND FULLY AIRBORNE, seen in three-quarter/side view: all four "
        "paws are off the ground, the body stretched out in a joyful bound, front legs "
        "reaching forward and back legs kicking out behind. Both floppy ears fly upward "
        "and outward with the motion. The eyes become two upward-curving pixel arcs "
        "'^ ^' (happy closed eyes), REPLACING the round black eyes entirely. The mouth "
        "is open in a wide happy smile with the small coral-red tongue clearly showing. "
        "The tail is raised and mid-wag. Bounding, weightless joy — clearly in the air, "
        "NOT sitting, and NOT standing upright on its hind legs like a person."
    ),
    "pointing": (
        "Byte is in the classic bird-dog POINT stance, seen in FULL SIDE PROFILE. It "
        "stands with the body low, long and level; one front paw is lifted and curled "
        "up close to the chest; the muzzle stretches forward with the nose down, "
        "sniffing out a scent; and the tail is held straight out behind, in one "
        "continuous line with the back and the head — the whole dog forms a single "
        "arrow directing attention forward. Both ears lean forward, perked and "
        "attentive. The eyes stay the normal round black eyes with white highlights, "
        "alert and locked on the target ahead. Nothing else — no icons, no text, no "
        "scent lines. Byte is a hunting dog on the trail, showing you where to look."
    ),
}

# One concrete line per pose, injected into stage-2 SCENE prompts (condensed from the
# pose deltas above). Byte is four-legged and indicates direction with its NOSE and body
# line — spelling that out stops Atlas's pointing ARM being copied onto Byte as a 5th leg.
BYTE_POSE_BRIEFS = {
    "neutral": (
        "sitting calmly on its haunches, ears floppy, eyes round and bright, tail curled "
        "beside it"
    ),
    "thinking": (
        "standing on all four legs, stopped mid-stride, head cocked sharply to one side "
        "in a curious puppy head-tilt, one front paw lifted and curled mid-step"
    ),
    "working": (
        "trotting briskly toward the viewer on all four legs, head high and proud, tail "
        "mid-wag, carrying a small rolled cream scroll crosswise in its MOUTH — the "
        "result it fetched"
    ),
    "error": (
        "scrambling backward on all four legs, front legs splayed and braced, both ears "
        "drooping flat, eyes wide, tail tucked down"
    ),
    "happy": (
        "mid-leap and fully airborne on a joyful bound, all four paws off the ground, "
        "ears flying up, eyes as two upward arcs '^ ^', tongue out in a wide smile"
    ),
    "pointing": (
        "in the classic bird-dog POINT stance, seen in side profile: body low and level, "
        "muzzle stretched forward with the NOSE DOWN on a scent, one front paw curled up "
        "against its chest, tail straight out behind so the whole dog forms an arrow. "
        "Byte indicates direction with its NOSE and the line of its body — it NEVER "
        "points by raising a limb like an arm, and it never gains an extra limb"
    ),
}

BYTE_ANATOMY = (
    "a four-legged dog — EXACTLY four legs and no more, never a fifth limb, never an "
    "extra paw. NO arms, NO hands, NO screen, NO monitor head, NO robot parts. Byte "
    "indicates direction with its NOSE and body line, not by raising a limb like an arm."
)

BYTE = Character(
    id="byte",
    display_name="Byte",
    seed_path=default_seed_path("byte"),        # seeds/byte_neutral.png
    bible_dir=default_bible_dir("byte"),        # characters/byte/
    shared_block=_SHARED_BLOCK,
    blurb=BYTE_CHARACTER_BLURB,
    expression_prompts=make_expression_prompts(_SHARED_BLOCK, _POSE_DELTAS),
    poses=POSE_ORDER,
    pose_briefs=BYTE_POSE_BRIEFS,
    anatomy=BYTE_ANATOMY,
    tagline=_TAGLINE,
)

register(BYTE)
