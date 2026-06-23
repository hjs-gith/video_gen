"""Tests for stage-3 TTS provider dispatch and audio-path resolution (mocked)."""
from __future__ import annotations

import pytest

from atlas_pipeline import stage3_video, tts_local


@pytest.fixture
def captured_logs(monkeypatch):
    logs = []
    monkeypatch.setattr(stage3_video, "log_api_call", lambda *a, **k: logs.append((a, k)))
    # Duration probing reads a real audio file; stub it.
    monkeypatch.setattr(stage3_video, "_audio_duration", lambda p: 1.0)
    return logs


def test_audio_path_resolves_either_extension(tmp_path):
    (tmp_path / "S01_en.wav").write_bytes(b"x")
    assert stage3_video._audio_path(tmp_path, "S01", "en").suffix == ".wav"
    (tmp_path / "S02_en.mp3").write_bytes(b"x")
    assert stage3_video._audio_path(tmp_path, "S02", "en").suffix == ".mp3"
    assert stage3_video._audio_path(tmp_path, "S03", "en") is None


def test_supertonic_provider_writes_wav_and_zero_cost(tmp_path, sample_script, captured_logs, monkeypatch):
    def fake_synth(text, lang, out_path, speed=None):
        out_path.write_bytes(b"RIFFfake")
        return 1.0

    monkeypatch.setattr(tts_local, "synthesize_to_file", fake_synth)

    stage3_video.generate_tts(sample_script, tmp_path, lang="en", provider="supertonic")

    audio = tmp_path / "audio"
    assert (audio / "S01_en.wav").exists()
    assert not (audio / "S01_en.mp3").exists()
    assert all(kw["cost_usd"] == 0.0 for _, kw in captured_logs)
    assert all(kw["stage"] == "3a_tts_local_en" for _, kw in captured_logs)


def test_openai_provider_writes_mp3_and_cost(tmp_path, sample_script, captured_logs, monkeypatch):
    class _Speech:
        def create(self, **kwargs):
            class _R:
                content = b"ID3fake"
            return _R()

    class _Audio:
        speech = _Speech()

    class _Client:
        audio = _Audio()

    monkeypatch.setattr(stage3_video, "tts_client", _Client())

    stage3_video.generate_tts(sample_script, tmp_path, lang="en", provider="openai")

    audio = tmp_path / "audio"
    assert (audio / "S01_en.mp3").exists()
    assert any(kw["cost_usd"] > 0 for _, kw in captured_logs)
    assert all(kw["stage"] == "3a_tts_en" for _, kw in captured_logs)


def test_switching_provider_replaces_stale_file(tmp_path, sample_script, captured_logs, monkeypatch):
    audio = tmp_path / "audio"
    audio.mkdir()
    (audio / "S01_en.mp3").write_bytes(b"old openai")

    def fake_synth(text, lang, out_path, speed=None):
        out_path.write_bytes(b"RIFFfake")
        return 1.0

    monkeypatch.setattr(tts_local, "synthesize_to_file", fake_synth)

    # force=True so it regenerates; supertonic should remove the stale .mp3.
    stage3_video.generate_tts(
        sample_script, tmp_path, lang="en", provider="supertonic", force=True, scene_filter="S01"
    )
    assert (audio / "S01_en.wav").exists()
    assert not (audio / "S01_en.mp3").exists()
