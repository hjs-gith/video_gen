"""Tests for the character registry and multi-character stage-2 conditioning."""
from __future__ import annotations

import pytest

from atlas_pipeline import characters as C
from atlas_pipeline import stage2_images
from atlas_pipeline.utils import validate_script


@pytest.fixture
def byte_character(tmp_path):
    """Register a second character 'byte' with a fake on-disk bible, then clean up."""
    C._bootstrap()  # ensure Atlas is registered first
    bdir = tmp_path / "byte_bible"
    bdir.mkdir()
    (bdir / "byte_neutral.png").write_bytes(b"PNG")
    (bdir / "byte_happy.png").write_bytes(b"PNG")
    byte = C.Character(
        id="byte",
        display_name="Byte",
        seed_path=tmp_path / "byte_neutral.png",
        bible_dir=bdir,
        shared_block="BYTE SHARED DESCRIPTION",
        blurb="BYTE BLURB — a friendly pixel cursor sprite",
        expression_prompts=C.make_expression_prompts("BYTE SHARED DESCRIPTION", {"happy": "grins"}),
        poses=["neutral", "happy"],
        tagline="a friendly pixel cursor sprite",
    )
    C.register(byte)
    yield byte
    C._REGISTRY.pop("byte", None)


def test_registry_resolves_atlas_and_added_character(byte_character):
    ids = {c.id for c in C.all_characters()}
    assert {"atlas", "byte"} <= ids
    assert C.get_character("atlas").display_name == "Atlas"
    assert C.get_character("nope") is None
    # cast_block (fed to the stage-1 writer) mentions every registered character.
    cb = C.cast_block()
    assert "Atlas" in cb and "Byte" in cb


def test_scene_characters_normalizes_both_schemas(byte_character):
    # Legacy atlas_in_scene / atlas_pose.
    legacy = C.scene_characters({"atlas_in_scene": True, "atlas_pose": "error"})
    assert [(c.id, p) for c, p in legacy] == [("atlas", "error")]
    # New array — unknown names are skipped.
    new = C.scene_characters(
        {"characters": [{"name": "byte", "pose": "happy"}, {"name": "ghost", "pose": "x"}]}
    )
    assert [(c.id, p) for c, p in new] == [("byte", "happy")]
    # No characters.
    assert C.scene_characters({"characters": []}) == []


def test_get_bible_paths_and_canonical_refs(byte_character):
    atlas = C.get_character("atlas")
    # Full refs = neutral + pose; canonical = just the pose image.
    full = [p.name for p in C.get_bible_paths(atlas, "pointing")]
    assert full == ["atlas_neutral.png", "atlas_pointing.png"]
    assert [p.name for p in C.canonical_refs(atlas, "pointing")] == ["atlas_pointing.png"]
    # Neutral pose -> just the neutral image.
    assert [p.name for p in C.canonical_refs(atlas, "neutral")] == ["atlas_neutral.png"]


def test_make_expression_prompts_expands_deltas():
    prompts = C.make_expression_prompts("SHARED DESC", {"happy": "grins widely"})
    assert set(prompts) == {"happy"}
    assert "SHARED DESC" in prompts["happy"]
    assert "grins widely" in prompts["happy"]


def _scene(characters):
    return {
        "scene_id": "S01",
        "beat": "HOOK",
        "on_screen_text": {"en": "Hi"},
        "visual_intent": "Atlas and Byte high-five over a glowing token.",
        "characters": characters,
    }


def test_two_characters_inject_both_blurbs(byte_character):
    script = {"meta": {"tier": "2"}, "scenes": [
        _scene([{"name": "atlas", "pose": "pointing"}, {"name": "byte", "pose": "happy"}])
    ]}
    s = stage2_images.build_image_prompts(script)["scenes"][0]
    assert [c["name"] for c in s["characters"]] == ["atlas", "byte"]
    prompt = s["image_prompt"]
    assert stage2_images.ATLAS_CHARACTER_BLURB in prompt   # Atlas blurb
    assert "BYTE BLURB" in prompt                          # Byte blurb
    assert "Atlas, Byte are the only character(s)" in prompt  # plural character rule


def test_frame_a_conditions_on_all_present_bibles(tmp_path, byte_character, monkeypatch):
    refs_seen = []

    def fake_synth(prompt, size, out_path, reference_paths=None):
        out_path.write_bytes(b"PNG")
        refs_seen.append([p.name for p in (reference_paths or [])])

    monkeypatch.setattr(stage2_images.image_local, "synthesize_image", fake_synth)
    monkeypatch.setattr(stage2_images, "log_api_call", lambda *a, **k: None)

    image_prompts = {
        "meta": {"term": "T", "image_size": "800x450", "image_quality": "low"},
        "scenes": [{
            "scene_id": "S01",
            "image_prompt": "x",
            "characters": [{"name": "atlas", "pose": "pointing"}, {"name": "byte", "pose": "happy"}],
        }],
    }
    stage2_images.generate_images(image_prompts, tmp_path, provider="local")

    frame_a_refs = set(refs_seen[0])  # first call is frame A
    assert "atlas_pointing.png" in frame_a_refs   # Atlas canonical ref
    assert "byte_happy.png" in frame_a_refs        # Byte canonical ref


def _valid_script(characters):
    return {
        "meta": {"actual_length_sec": 60},
        "scenes": [{
            "scene_id": "S01",
            "visual_intent": "x",
            "narration": {"en": "a", "ko": "b"},
            "characters": characters,
        }],
    }


def test_validate_script_multichar(byte_character):
    ok = validate_script(_valid_script(
        [{"name": "atlas", "pose": "happy"}, {"name": "byte", "pose": "happy"}]
    ))
    assert not [e for e in ok if "character" in e or "pose" in e]

    unknown = validate_script(_valid_script([{"name": "ghost", "pose": "happy"}]))
    assert any("unknown character" in e for e in unknown)

    bad_pose = validate_script(_valid_script([{"name": "byte", "pose": "zzz"}]))
    assert any("pose" in e for e in bad_pose)
