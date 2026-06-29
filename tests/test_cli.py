"""CLI surface tests via Click's CliRunner (no real work performed)."""
from __future__ import annotations

from click.testing import CliRunner

from atlas_pipeline.cli import main


def test_regen_command_exists():
    res = CliRunner().invoke(main, ["episode", "regen", "--help"])
    assert res.exit_code == 0
    assert "Re-generate the background + foreground" in res.output


def test_select_command_removed():
    res = CliRunner().invoke(main, ["episode", "select", "--help"])
    assert res.exit_code != 0  # no such command


def test_run_has_tts_option():
    res = CliRunner().invoke(main, ["episode", "run", "--help"])
    assert res.exit_code == 0
    assert "--tts" in res.output
    assert "supertonic" in res.output


def test_run_rejects_bad_tts_provider():
    res = CliRunner().invoke(main, ["episode", "run", "11", "--tts", "bogus"])
    assert res.exit_code != 0
