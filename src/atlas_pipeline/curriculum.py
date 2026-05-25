from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from .config import EPISODES_YAML_DIR


@dataclass
class EpisodeRecord:
    episode_number: int
    cluster: int
    cluster_name: str
    terms: list[str]
    tier: str
    one_line_gist: str
    target_length_sec: int
    metaphor_seed: Optional[str] = None
    example_scenario: Optional[str] = None
    next_episode_teaser: Optional[str] = None
    previous_episodes: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        term = self.terms[0].lower().replace(" ", "_").replace("-", "_")
        return f"c{self.cluster:02d}_e{self.episode_number:02d}_{term}"

    @property
    def tier_number(self) -> str:
        return self.tier.lstrip("T")


def load_all_episodes() -> list[EpisodeRecord]:
    paths = sorted(EPISODES_YAML_DIR.glob("episode_*.yaml"))
    if not paths:
        raise FileNotFoundError(f"No episode YAML files found in {EPISODES_YAML_DIR}")

    raw_episodes: list[dict] = []
    for p in paths:
        with open(p) as f:
            raw_episodes.append(yaml.safe_load(f))

    raw_episodes.sort(key=lambda e: e["episode_number"])

    episodes: list[EpisodeRecord] = []
    for raw in raw_episodes:
        ep = EpisodeRecord(
            episode_number=raw["episode_number"],
            cluster=raw["cluster"],
            cluster_name=raw["cluster_name"],
            terms=raw["terms"],
            tier=raw["tier"],
            one_line_gist=raw["one_line_gist"],
            target_length_sec=raw.get("target_length_sec", 60),
            metaphor_seed=raw.get("metaphor_seed"),
            example_scenario=raw.get("example_scenario"),
            next_episode_teaser=raw.get("next_episode_teaser"),
        )
        episodes.append(ep)

    # Populate previous_episodes within each cluster
    cluster_terms: dict[int, list[str]] = {}
    for ep in episodes:
        prev = cluster_terms.get(ep.cluster, []).copy()
        ep.previous_episodes = prev
        cluster_terms.setdefault(ep.cluster, [])
        cluster_terms[ep.cluster].extend(ep.terms)

    return episodes


def get_episode(episode_number: int) -> EpisodeRecord:
    episodes = load_all_episodes()
    for ep in episodes:
        if ep.episode_number == episode_number:
            return ep
    available = [ep.episode_number for ep in episodes]
    raise ValueError(f"Episode {episode_number} not found. Available: {available}")
