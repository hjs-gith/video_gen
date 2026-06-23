"""Tests for stage-2 image generation (frame A + frame-B variation), mocked API."""
from __future__ import annotations

import pytest

from atlas_pipeline import stage2_images


@pytest.fixture
def fake_client(monkeypatch, fake_image_result):
    calls = []

    class _Images:
        def generate(self, **kwargs):
            calls.append(("generate", kwargs))
            return fake_image_result

        def edit(self, **kwargs):
            calls.append(("edit", kwargs))
            return fake_image_result

    class _Client:
        images = _Images()

    monkeypatch.setattr(stage2_images, "image_client", _Client())
    # Avoid touching the real Atlas bible PNGs.
    monkeypatch.setattr(stage2_images, "get_bible_paths", lambda pose: [])
    monkeypatch.setattr(stage2_images, "log_api_call", lambda *a, **k: None)
    return calls


def _prompts():
    return {
        "meta": {"term": "Token", "image_size": "1024x1024", "image_quality": "low"},
        "scenes": [{
            "scene_id": "S01",
            "beat": "DEFINITION",
            "pose_hint": "pointing",
            "atlas_in_scene": False,
            "image_prompt": "draw a token",
        }],
    }


def test_generates_both_frames_b_from_a(tmp_path, fake_client):
    stage2_images.generate_images(_prompts(), tmp_path)
    imgs = tmp_path / "images"
    assert (imgs / "S01_a.png").exists()
    assert (imgs / "S01_b.png").exists()

    kinds = [c[0] for c in fake_client]
    # Frame A via generate (no atlas), frame B via edit (variation).
    assert kinds == ["generate", "edit"]
    edit_kwargs = fake_client[1][1]
    assert stage2_images._VARIATION_SUFFIX in edit_kwargs["prompt"]
    # The edit is fed an opened file handle (frame A).
    assert hasattr(edit_kwargs["image"], "read")


def test_skips_existing_without_force(tmp_path, fake_client):
    imgs = tmp_path / "images"
    imgs.mkdir()
    (imgs / "S01_a.png").write_bytes(b"existing")
    (imgs / "S01_b.png").write_bytes(b"existing")
    stage2_images.generate_images(_prompts(), tmp_path)
    assert fake_client == []  # nothing regenerated


def test_scene_filter(tmp_path, fake_client):
    prompts = _prompts()
    prompts["scenes"].append({**prompts["scenes"][0], "scene_id": "S02"})
    stage2_images.generate_images(prompts, tmp_path, scene_filter="S02")
    imgs = tmp_path / "images"
    assert not (imgs / "S01_a.png").exists()
    assert (imgs / "S02_a.png").exists()
