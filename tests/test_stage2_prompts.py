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
    assert "ALTERNATE FRAME" in stage2_images._VARIATION_SUFFIX
    # It is not baked into the base prompt produced by build_image_prompts.
    result = stage2_images.build_image_prompts(
        {"meta": {"tier": "2"}, "scenes": [
            {"scene_id": "S01", "beat": "HOOK", "narration": {}, "visual_intent": "x",
             "on_screen_text": {"en": "Hi"}, "atlas_in_scene": False}
        ]}
    )
    assert stage2_images._VARIATION_SUFFIX not in result["scenes"][0]["image_prompt"]
