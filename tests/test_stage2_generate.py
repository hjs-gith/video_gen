"""Tests for stage-2 image generation (background + transparent foreground), mocked API."""
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
            "image_prompt_bg": "draw the setting",
            "image_prompt_fg": "draw the token only",
        }],
    }


def test_generates_background_then_transparent_foreground(tmp_path, fake_client):
    stage2_images.generate_images(_prompts(), tmp_path)
    imgs = tmp_path / "images"
    assert (imgs / "S01_bg.png").exists()
    assert (imgs / "S01_fg.png").exists()

    kinds = [c[0] for c in fake_client]
    # Non-atlas scene: both layers via generate (no reference images).
    assert kinds == ["generate", "generate"]
    bg_kwargs, fg_kwargs = fake_client[0][1], fake_client[1][1]
    # Background is opaque; foreground requests native transparency.
    assert "background" not in bg_kwargs
    assert bg_kwargs["prompt"] == "draw the setting"
    assert fg_kwargs["background"] == "transparent"
    assert fg_kwargs["output_format"] == "png"
    assert fg_kwargs["prompt"] == "draw the token only"


def test_skips_existing_without_force(tmp_path, fake_client):
    imgs = tmp_path / "images"
    imgs.mkdir()
    (imgs / "S01_bg.png").write_bytes(b"existing")
    (imgs / "S01_fg.png").write_bytes(b"existing")
    stage2_images.generate_images(_prompts(), tmp_path)
    assert fake_client == []  # nothing regenerated


def test_scene_filter(tmp_path, fake_client):
    prompts = _prompts()
    prompts["scenes"].append({**prompts["scenes"][0], "scene_id": "S02"})
    stage2_images.generate_images(prompts, tmp_path, scene_filter="S02")
    imgs = tmp_path / "images"
    assert not (imgs / "S01_bg.png").exists()
    assert (imgs / "S02_bg.png").exists()
