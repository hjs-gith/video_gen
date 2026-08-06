"""Tests for stage-2 prompt construction (pure, no API)."""
from __future__ import annotations

from atlas_pipeline import stage2_images
from atlas_pipeline.config import TIER_HEX


def test_build_image_prompts_basic(sample_script):
    result = stage2_images.build_image_prompts(sample_script, overlay_lang="en")
    meta = result["meta"]
    assert meta["tier_hex"] == TIER_HEX["T2"]
    assert meta["scene_count"] == 2

    s1, s2 = result["scenes"]
    # Atlas scene carries the mascot blurb + its pose; non-atlas scene does not.
    assert s1["atlas_in_scene"] is True
    assert s1["pose_hint"] == "thinking"
    assert stage2_images.ATLAS_CHARACTER_BLURB in s1["image_prompt"]
    assert s2["atlas_in_scene"] is False
    assert stage2_images.ATLAS_CHARACTER_BLURB not in s2["image_prompt"]


def test_overlay_lang_selects_on_screen_text(sample_script):
    en = stage2_images.build_image_prompts(sample_script, overlay_lang="en")
    ko = stage2_images.build_image_prompts(sample_script, overlay_lang="ko")
    assert "What is a token?" in en["scenes"][0]["image_prompt"]
    assert "토큰이란?" in ko["scenes"][0]["image_prompt"]


def test_pose_inferred_from_beat_when_absent(sample_script):
    # Drop the explicit pose; DEFINITION beat -> "pointing" per BEAT_TO_POSE.
    sample_script["scenes"][1]["atlas_in_scene"] = True
    sample_script["scenes"][1]["atlas_pose"] = None
    result = stage2_images.build_image_prompts(sample_script)
    assert result["scenes"][1]["pose_hint"] == "pointing"


def test_variation_suffix_used_only_for_frame_b():
    # The suffix is a stage-2 constant appended only on the frame-B path.
    assert "SECOND FRAME OF A 2-FRAME" in stage2_images._VARIATION_SUFFIX
    # It is not baked into the base prompt produced by build_image_prompts.
    result = stage2_images.build_image_prompts(
        {"meta": {"tier": "2"}, "scenes": [
            {"scene_id": "S01", "beat": "HOOK", "narration": {}, "visual_intent": "x",
             "on_screen_text": {"en": "Hi"}, "atlas_in_scene": False}
        ]}
    )
    assert "SECOND FRAME OF A 2-FRAME" not in result["scenes"][0]["image_prompt"]


def test_variation_motion_is_scene_specific():
    # Atlas scenes get an on-model Atlas idle; other scenes move only the focal element.
    atlas = stage2_images._variation_motion({"atlas_in_scene": True})
    plain = stage2_images._variation_motion({"atlas_in_scene": False})
    assert "Atlas" in atlas and "tilt" in atlas.lower()
    assert "Atlas" not in plain and "tilt" in plain.lower()


# ── Multi-character scenes: reference binding ────────────────────────────────────
# Regression: with an unlabeled reference list, Atlas's pointing ARM bled onto Byte and
# rendered as a 5th leg. The prompt must bind each reference image to exactly one
# character, and that numbering must match the images actually sent.

def _two_character_scene():
    return {
        "scene_id": "S01",
        "beat": "HOOK",
        "on_screen_text": {"en": "Answer vs. action"},
        "visual_intent": "Atlas points at a panel while Byte waits beside a goal flag",
        "characters": [
            {"name": "atlas", "pose": "pointing"},
            {"name": "byte", "pose": "thinking"},
        ],
    }


def _prompt_for(scene):
    script = {"meta": {"term": "Agent", "tier": "T2"}, "scenes": [scene]}
    return stage2_images.build_image_prompts(script)["scenes"][0]["image_prompt"]


def test_reference_map_numbering_matches_images_actually_sent():
    from atlas_pipeline.characters import reference_plan, scene_characters

    scene = _two_character_scene()
    prompt = _prompt_for(scene)

    sent = [p for _, _, refs in reference_plan(scene_characters(scene)) for p in refs]
    assert len(sent) == 2

    # Each image the API receives is claimed, in order, by exactly one character.
    assert "Reference image 1 = ATLAS" in prompt
    assert "Reference image 2 = BYTE" in prompt
    assert "atlas" in sent[0].name and "byte" in sent[1].name
    # ...and there is no image 3 claimed that we never send.
    assert "Reference image 3" not in prompt
    assert "NEVER copy a pose, limb, body part, or feature" in prompt


def test_anatomy_block_forbids_a_fifth_limb():
    prompt = _prompt_for(_two_character_scene())
    assert "CHARACTER ANATOMY" in prompt
    assert "EXACTLY four legs" in prompt
    assert "never a fifth limb" in prompt
    assert "NO legs, NO feet" in prompt  # Atlas


def test_byte_points_with_nose_not_an_arm():
    from atlas_pipeline.characters import get_character

    byte = get_character("byte")
    brief = byte.pose_brief("pointing")
    assert "NOSE" in brief
    assert "NEVER points by raising a limb like an arm" in brief

    # Atlas, by contrast, points with an arm — the two must not be interchangeable.
    atlas = get_character("atlas")
    assert "ARM" in atlas.pose_brief("pointing")


def test_pose_brief_falls_back_to_bare_pose_word():
    from atlas_pipeline.characters import get_character

    assert get_character("byte").pose_brief("nonexistent") == "a nonexistent pose"
