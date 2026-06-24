"""Local image-generation provider — talks to a user-run HTTP server.

The pipeline POSTs a prompt plus a list of reference images; the list length selects
the mode, which maps directly onto FLUX.2 [klein]'s multi-reference editing:

    reference_images == []          -> text-to-image          (non-Atlas frame A)
    reference_images == [bible...]  -> reference-conditioned   (Atlas frame A)
    reference_images == [frame_a]   -> img2img variation       (frame B)

The server (which lives outside this repo) must implement the contract in
docs/local_image_server.md. Dependency-free: stdlib urllib/json/base64 only.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path

from .config import IMAGE_LOCAL_STEPS, IMAGE_LOCAL_URL

_TIMEOUT_SEC = 300


def _parse_size(size: str) -> tuple[int, int]:
    """'1536x864' -> (1536, 864)."""
    w, _, h = size.lower().partition("x")
    return int(w), int(h)


def synthesize_image(
    prompt: str,
    size: str,
    out_path: Path,
    reference_paths: list[Path] | None = None,
) -> None:
    """Render one image via the local HTTP server and write it to out_path (PNG)."""
    width, height = _parse_size(size)
    refs = [
        base64.b64encode(Path(p).read_bytes()).decode()
        for p in (reference_paths or [])
    ]
    payload = json.dumps({
        "prompt": prompt,
        "width": width,
        "height": height,
        "reference_images": refs,
        "steps": IMAGE_LOCAL_STEPS,
    }).encode()

    req = urllib.request.Request(
        IMAGE_LOCAL_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read()
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Local image server unreachable at {IMAGE_LOCAL_URL}: {e}. "
            "Is it running? See docs/local_image_server.md."
        ) from e

    # Raw PNG bytes, or a JSON body carrying base64.
    if "application/json" in content_type:
        image_bytes = base64.b64decode(json.loads(body)["image_base64"])
    else:
        image_bytes = body

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(image_bytes)
