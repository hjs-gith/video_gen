"""Stage-2 provider dispatch: local provider routes to the HTTP adapter."""
from __future__ import annotations

from pathlib import Path

import pytest

from atlas_pipeline import stage2_images


@pytest.fixture
def local_calls(monkeypatch):
    calls = []

    def fake_synth(prompt, size, out_path, reference_paths=None):
        out_path.write_bytes(b"PNGLOCAL")
        calls.append({"prompt": prompt, "refs": list(reference_paths or []), "out": out_path})

    monkeypatch.setattr(stage2_images.image_local, "synthesize_image", fake_synth)
    monkeypatch.setattr(stage2_images, "log_api_call", lambda *a, **k: calls.append(("log", k)))
    # Atlas frame A should condition on these "bible" reference paths.
    monkeypatch.setattr(
        stage2_images,
        "get_bible_paths",
        lambda character, pose: [Path("/bible/neutral.png"), Path(f"/bible/{pose}.png")],
    )
    # If openai were touched, fail loudly.
    class _Boom:
        def __getattr__(self, _):
            raise AssertionError("openai image_client must not be used for local provider")
    monkeypatch.setattr(stage2_images, "image_client", _Boom())
    return calls


def _prompts(atlas_in):
    return {
        "meta": {"term": "Token", "image_size": "800x450", "image_quality": "low"},
        "scenes": [{
            "scene_id": "S01",
            "beat": "HOOK",
            "pose_hint": "thinking",
            "atlas_in_scene": atlas_in,
            "image_prompt": "draw a token",
        }],
    }


def test_local_atlas_frame_a_uses_bible_refs_frame_b_uses_a(tmp_path, local_calls):
    stage2_images.generate_images(_prompts(atlas_in=True), tmp_path, provider="local")

    synth = [c for c in local_calls if isinstance(c, dict)]
    assert (tmp_path / "images" / "S01_a.png").exists()
    assert (tmp_path / "images" / "S01_b.png").exists()

    # Frame A conditions on the two bible paths.
    a, b = synth[0], synth[1]
    assert [p.name for p in a["refs"]] == ["neutral.png", "thinking.png"]
    # Frame B conditions on frame A and carries the idle-loop directive + Atlas motion.
    assert b["refs"] == [tmp_path / "images" / "S01_a.png"]
    assert "SECOND FRAME OF A 2-FRAME" in b["prompt"]
    assert "Atlas does a tiny idle" in b["prompt"]

    logs = [c for c in local_calls if isinstance(c, tuple)]
    assert all(kw["cost_usd"] == 0.0 and kw["model"] == stage2_images.IMAGE_LOCAL_MODEL for _, kw in logs)


def test_local_non_atlas_frame_a_has_no_refs(tmp_path, local_calls):
    stage2_images.generate_images(_prompts(atlas_in=False), tmp_path, provider="local")
    synth = [c for c in local_calls if isinstance(c, dict)]
    assert synth[0]["refs"] == []  # text-to-image
