"""Tests for episode YAML loading and EpisodeRecord derivation."""
from __future__ import annotations

import textwrap

import pytest

from atlas_pipeline import curriculum


def _write_episode(dir_path, idx, **fields):
    base = {
        "episode_number": fields.get("episode_number", idx + 1),
        "cluster": fields.get("cluster", 3),
        "cluster_name": fields.get("cluster_name", "What AI Remembers & Knows"),
        "terms": fields.get("terms", ["Token"]),
        "tier": fields.get("tier", "T2"),
        "one_line_gist": fields.get("one_line_gist", "The atomic unit of text."),
        "target_length_sec": fields.get("target_length_sec", 60),
    }
    import yaml

    (dir_path / f"episode_{idx}.yaml").write_text(yaml.safe_dump(base))


@pytest.fixture
def yaml_dir(tmp_path, monkeypatch):
    d = tmp_path / "episodes_yaml"
    d.mkdir()
    monkeypatch.setattr(curriculum, "EPISODES_YAML_DIR", d)
    return d


def test_load_orders_by_episode_number(yaml_dir):
    _write_episode(yaml_dir, 1, episode_number=12, terms=["Context Window"])
    _write_episode(yaml_dir, 0, episode_number=11, terms=["Token"])
    eps = curriculum.load_all_episodes()
    assert [e.episode_number for e in eps] == [11, 12]


def test_previous_episodes_populated_per_cluster(yaml_dir):
    _write_episode(yaml_dir, 0, episode_number=11, cluster=3, terms=["Token"])
    _write_episode(yaml_dir, 1, episode_number=12, cluster=3, terms=["Context Window"])
    _write_episode(yaml_dir, 2, episode_number=13, cluster=4, terms=["Embedding"])
    eps = {e.episode_number: e for e in curriculum.load_all_episodes()}
    assert eps[11].previous_episodes == []
    assert eps[12].previous_episodes == ["Token"]
    # New cluster resets the running list.
    assert eps[13].previous_episodes == []


def test_record_slug_and_tier_number(yaml_dir):
    _write_episode(yaml_dir, 0, episode_number=11, cluster=3, terms=["Token Window"], tier="T2.5")
    ep = curriculum.get_episode(11)
    assert ep.slug == "c03_e11_token_window"
    assert ep.tier_number == "2.5"


def test_get_episode_unknown_raises(yaml_dir):
    _write_episode(yaml_dir, 0, episode_number=11)
    with pytest.raises(ValueError):
        curriculum.get_episode(99)
