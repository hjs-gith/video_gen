"""Tests for the local image HTTP provider adapter (mocked transport)."""
from __future__ import annotations

import base64
import io
import json

import pytest

from atlas_pipeline import image_local


def _tiny_png() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )


class _FakeResp:
    def __init__(self, body: bytes, content_type: str):
        self._body = body
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_parse_size():
    assert image_local._parse_size("1536x864") == (1536, 864)
    assert image_local._parse_size("1024X1024") == (1024, 1024)


def test_posts_payload_and_writes_raw_png(tmp_path, monkeypatch):
    ref = tmp_path / "ref.png"
    ref.write_bytes(_tiny_png())
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["headers"] = req.headers
        captured["body"] = json.loads(req.data)
        return _FakeResp(_tiny_png(), "image/png")

    monkeypatch.setattr(image_local.urllib.request, "urlopen", fake_urlopen)

    out = tmp_path / "out.png"
    image_local.synthesize_image("draw a token", "1536x864", out, [ref])

    assert out.read_bytes() == _tiny_png()
    body = captured["body"]
    assert body["prompt"] == "draw a token"
    assert body["width"] == 1536 and body["height"] == 864
    assert body["reference_images"] == [base64.b64encode(_tiny_png()).decode()]
    assert "steps" in body
    assert body["transparent"] is False  # opaque by default


def test_transparent_flag_forwarded(tmp_path, monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data)
        return _FakeResp(_tiny_png(), "image/png")

    monkeypatch.setattr(image_local.urllib.request, "urlopen", fake_urlopen)
    image_local.synthesize_image("x", "512x512", tmp_path / "o.png", None, transparent=True)
    assert captured["body"]["transparent"] is True


def test_accepts_json_base64_response(tmp_path, monkeypatch):
    payload = json.dumps({"image_base64": base64.b64encode(_tiny_png()).decode()}).encode()

    monkeypatch.setattr(
        image_local.urllib.request,
        "urlopen",
        lambda req, timeout=None: _FakeResp(payload, "application/json"),
    )

    out = tmp_path / "out.png"
    image_local.synthesize_image("x", "512x512", out, None)
    assert out.read_bytes() == _tiny_png()


def test_unreachable_server_raises_clear_error(tmp_path, monkeypatch):
    import urllib.error

    def boom(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(image_local.urllib.request, "urlopen", boom)
    with pytest.raises(RuntimeError, match="Local image server unreachable"):
        image_local.synthesize_image("x", "512x512", tmp_path / "o.png", None)
