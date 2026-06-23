"""Shared pytest fixtures and import-time setup.

`config.py` constructs the OpenAI clients at import time, so dummy API keys must
exist *before* any pipeline module is imported. No network call is made at client
construction, so placeholder keys are sufficient for the whole (hermetic) suite.
"""
from __future__ import annotations

import os

os.environ.setdefault("SCRIPT_API", "sk-test")
os.environ.setdefault("IMAGE_API", "sk-test")
os.environ.setdefault("TTS_API", "sk-test")

import pytest  # noqa: E402


@pytest.fixture
def sample_script() -> dict:
    """A minimal but schema-valid two-scene bilingual script."""
    return {
        "meta": {
            "term": "Token",
            "tier": "2",
            "cluster": "3",
            "episode_in_cluster": "3.11",
            "target_length_sec": 60,
            "actual_length_sec": 60,
            "scene_count": 2,
        },
        "scenes": [
            {
                "scene_id": "S01",
                "beat": "HOOK",
                "duration_sec": 4.0,
                "narration": {"en": "Ever wonder what a token is?", "ko": "토큰이 뭔지 궁금하셨나요?"},
                "on_screen_text": {"en": "What is a token?", "ko": "토큰이란?", "position": "center"},
                "atlas_in_scene": True,
                "atlas_pose": "thinking",
                "visual_intent": "Atlas tilts its head, curious, beside a glowing word.",
            },
            {
                "scene_id": "S02",
                "beat": "DEFINITION",
                "duration_sec": 6.0,
                "narration": {"en": "It is a chunk of text.", "ko": "텍스트의 한 조각입니다."},
                "on_screen_text": {"en": "A chunk of text", "ko": "텍스트 조각", "position": "lower-third"},
                "atlas_in_scene": False,
                "atlas_pose": None,
                "visual_intent": "A sentence breaking into pixel tiles, no character.",
            },
        ],
        "quality_checks": {},
    }


@pytest.fixture
def fake_image_result():
    """A fake OpenAI images response carrying a 1x1 PNG as base64."""
    import base64

    # Smallest valid 1x1 PNG.
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    b64 = base64.b64encode(png).decode()

    class _Data:
        def __init__(self):
            self.b64_json = b64

    class _Result:
        def __init__(self):
            self.data = [_Data()]

    return _Result()
