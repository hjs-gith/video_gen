"""Tests for stage-3 frame alternation timing and end-to-end assembly."""
from __future__ import annotations

import numpy as np
import pytest

from atlas_pipeline import stage3_video


def test_frame_index_alternates_every_interval():
    fi, n = 0.5, 2
    assert stage3_video._frame_index(0.0, n, fi) == 0   # A
    assert stage3_video._frame_index(0.49, n, fi) == 0  # A
    assert stage3_video._frame_index(0.5, n, fi) == 1   # B
    assert stage3_video._frame_index(0.99, n, fi) == 1  # B
    assert stage3_video._frame_index(1.0, n, fi) == 0   # back to A
    assert stage3_video._frame_index(1.5, n, fi) == 1   # B


def test_assemble_alternates_two_frames(tmp_path):
    """End-to-end: a 2-frame scene must visibly switch between its frames."""
    pytest.importorskip("PIL")
    from PIL import Image

    images = tmp_path / "images"
    audio = tmp_path / "audio"
    images.mkdir()
    audio.mkdir()

    # Two solidly distinct frames so any switch is unambiguous.
    Image.new("RGB", (160, 90), (255, 0, 0)).save(images / "S01_a.png")
    Image.new("RGB", (160, 90), (0, 0, 255)).save(images / "S01_b.png")

    # A short, audible mono tone so the scene has real duration (~1.5s).
    from moviepy import AudioArrayClip

    sr = 22050
    tone = (0.3 * np.sin(2 * np.pi * 220 * np.arange(int(1.5 * sr)) / sr)).reshape(-1, 1)
    AudioArrayClip(tone, fps=sr).write_audiofile(str(audio / "S01_en.mp3"), logger=None)

    script = {
        "meta": {"term": "Demo", "cluster": "0"},
        "scenes": [{
            "scene_id": "S01",
            "narration": {"en": "x", "ko": "x"},
            "duration_sec": 1.5,
        }],
    }

    stage3_video.assemble_video(script, tmp_path, lang="en", overlay="none", force=True)

    out = tmp_path / f"{tmp_path.name}_en_overlay-none.mp4"
    assert out.exists()

    from moviepy import VideoFileClip

    with VideoFileClip(str(out)) as clip:
        # Sample past the 0.3s start fade; t=0.6 is in flip-phase B (blue-ish),
        # t=1.1 is back in phase A (red-ish). They must differ.
        fa = clip.get_frame(0.6)
        fb = clip.get_frame(1.1)
    # Red channel dominates one sampled frame, blue the other.
    assert (fa[..., 2].mean() - fa[..., 0].mean()) * (fb[..., 2].mean() - fb[..., 0].mean()) < 0
