"""Tests for path/JSON/log/validation helpers."""
from __future__ import annotations

import json

import pytest

from atlas_pipeline import utils


def test_episode_dir_slug_and_subdirs(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "EPISODES_OUTPUT_DIR", tmp_path)
    d = utils.episode_dir(3, 11, "Token")
    assert d.name == "c03_e11_token"
    assert (d / "images").is_dir()
    assert (d / "audio").is_dir()


def test_save_and_load_json_roundtrip_non_ascii(tmp_path):
    path = tmp_path / "x" / "data.json"
    payload = {"ko": "토큰이란?", "n": 3}
    utils.save_json(payload, path)
    assert json.loads(path.read_text(encoding="utf-8")) == payload
    assert utils.load_json(path) == payload


def test_log_api_call_appends_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "LOGS_DIR", tmp_path)
    utils.log_api_call("2_images", "gpt-image-2", 0, 0, 0.1, episode_id="ep", scene_id="S01")
    utils.log_api_call("3a_tts_local_en", "supertonic-3", 5, 0, 0.0, episode_id="ep")
    lines = (tmp_path / "api_calls.jsonl").read_text().splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[1])
    assert rec["cost_usd"] == 0.0
    assert rec["model"] == "supertonic-3"


def test_validate_script_ok(sample_script):
    assert utils.validate_script(sample_script) == []


def test_validate_script_flags_problems(sample_script):
    sample_script["meta"]["actual_length_sec"] = 5  # out of 30–90 range
    sample_script["scenes"][0]["narration"].pop("ko")  # missing KO
    sample_script["scenes"][0]["atlas_pose"] = "bogus"  # invalid pose
    errors = utils.validate_script(sample_script)
    joined = " ".join(errors)
    assert "actual_length_sec" in joined
    assert "narration.ko" in joined
    assert "atlas_pose" in joined


def test_validate_script_no_scenes():
    assert utils.validate_script({"meta": {}, "scenes": []}) == ["No scenes found"]
