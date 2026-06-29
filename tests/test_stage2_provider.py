"""Stage-2 provider dispatch: local provider routes to the HTTP adapter."""
from __future__ import annotations

from pathlib import Path

import pytest

from atlas_pipeline import stage2_images


@pytest.fixture
def local_calls(monkeypatch):
    calls = []

    def fake_synth(prompt, size, out_path, reference_paths=None, transparent=False):
        out_path.write_bytes(b"PNGLOCAL")
        calls.append({
            "prompt": prompt,
            "refs": list(reference_paths or []),
            "out": out_path,
            "transparent": transparent,
        })

    monkeypatch.setattr(stage2_images.image_local, "synthesize_image", fake_synth)
    monkeypatch.setattr(stage2_images, "log_api_call", lambda *a, **k: calls.append(("log", k)))
    # The Atlas foreground should condition on these "bible" reference paths.
    monkeypatch.setattr(stage2_images, "get_bible_paths", lambda pose: [Path("/bible/neutral.png"), Path(f"/bible/{pose}.png")])
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
            "image_prompt_bg": "draw the setting",
            "image_prompt_fg": "draw the token only",
        }],
    }


def test_local_atlas_bg_opaque_fg_transparent_with_bible_refs(tmp_path, local_calls):
    stage2_images.generate_images(_prompts(atlas_in=True), tmp_path, provider="local")

    synth = [c for c in local_calls if isinstance(c, dict)]
    assert (tmp_path / "images" / "S01_bg.png").exists()
    assert (tmp_path / "images" / "S01_fg.png").exists()

    bg, fg = synth[0], synth[1]
    # Background: opaque, no references (the setting only).
    assert bg["refs"] == [] and bg["transparent"] is False
    assert bg["prompt"] == "draw the setting"
    # Foreground: transparent cutout conditioned on the two bible references.
    assert [p.name for p in fg["refs"]] == ["neutral.png", "thinking.png"]
    assert fg["transparent"] is True
    assert fg["prompt"] == "draw the token only"

    logs = [c for c in local_calls if isinstance(c, tuple)]
    assert all(kw["cost_usd"] == 0.0 and kw["model"] == stage2_images.IMAGE_LOCAL_MODEL for _, kw in logs)


def test_local_non_atlas_foreground_has_no_refs(tmp_path, local_calls):
    stage2_images.generate_images(_prompts(atlas_in=False), tmp_path, provider="local")
    synth = [c for c in local_calls if isinstance(c, dict)]
    bg, fg = synth[0], synth[1]
    assert bg["refs"] == [] and bg["transparent"] is False
    assert fg["refs"] == [] and fg["transparent"] is True  # transparent text-to-image
