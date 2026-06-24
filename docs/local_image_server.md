# Local image server (stage 2 `--image-provider local`)

Stage 2 can render images from your own local model instead of OpenAI. You run a
small HTTP server (outside this repo) that wraps an image model; the pipeline POSTs a
prompt plus reference images and writes back the PNG it returns. Enable it with:

```bash
export IMAGE_PROVIDER=local                       # or pass --image-provider local
export IMAGE_LOCAL_URL=http://127.0.0.1:8000/generate
uv run atlas episode run 11 --stages 2 --image-provider local
```

Other env knobs: `IMAGE_LOCAL_MODEL` (label used in the cost log, default
`flux2-klein`), `IMAGE_LOCAL_STEPS` (forwarded as `steps`, default `28`).

## The contract

`POST {IMAGE_LOCAL_URL}` with `Content-Type: application/json`:

```json
{
  "prompt": "the full text prompt built by stage 2",
  "width": 1536,
  "height": 864,
  "reference_images": ["<base64 PNG>", "..."],
  "steps": 28
}
```

Respond with **HTTP 200** and either:
- the raw PNG bytes (`Content-Type: image/png`), or
- JSON `{"image_base64": "<base64 PNG>"}`.

Honor `width`/`height` exactly — frames A and B must match in size so they alternate
cleanly in the assembled video.

### `reference_images` selects the mode

The list length tells your server what to do (this maps directly onto FLUX.2
[klein]'s text-to-image + multi-reference editing in one model):

| `reference_images` | Mode | Used for |
| --- | --- | --- |
| `[]` | text → image | non-Atlas frame A |
| Atlas bible PNGs (1–2) | reference-conditioned generation | Atlas frame A (keeps the mascot on-model) |
| `[frame_a.png]` | img2img variation | frame B (a near-identical alternate frame) |

So a single endpoint covers every stage-2 call.

## Which model

**FLUX.2 [klein] (recommended).** One model does text-to-image *and* multi-reference
editing — exactly the three modes above. The **4B** variant is Apache-2.0 (commercial
use) and fits ~8 GB VRAM; the 9B is non-commercial. See
<https://github.com/black-forest-labs/flux2> and
<https://huggingface.co/black-forest-labs/FLUX.2-klein-4B>.

**FLUX.1 [dev]** is text-to-image only; you would also need **FLUX.1 Kontext [dev]**
(~24 GB) for the reference/img2img modes — two models to serve. Prefer klein unless
you specifically need FLUX.1.

## Reference server stub (FastAPI + diffusers)

This is a starting point, not part of this package. Adapt the pipeline call to the
exact FLUX.2 API you use (`pip install fastapi uvicorn pillow` plus your FLUX deps).

```python
import base64, io
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from PIL import Image
# from your_flux2_klein import pipe   # load FLUX.2 [klein] once at startup

app = FastAPI()

class Req(BaseModel):
    prompt: str
    width: int = 1536
    height: int = 864
    reference_images: list[str] = []
    steps: int = 28

@app.post("/generate")
def generate(r: Req):
    refs = [Image.open(io.BytesIO(base64.b64decode(b))).convert("RGB")
            for b in r.reference_images]
    # No refs -> text-to-image; refs -> multi-reference / img2img editing.
    image = pipe(
        prompt=r.prompt,
        width=r.width, height=r.height,
        num_inference_steps=r.steps,
        reference_images=refs or None,   # adapt to your FLUX.2 pipeline's kwarg
    ).images[0]
    buf = io.BytesIO(); image.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")
```

## Testing the wiring without a GPU

You can verify the pipeline end-to-end with a stub that ignores the prompt and
returns a solid-color PNG:

```python
# stub_server.py
import io
from fastapi import FastAPI
from fastapi.responses import Response
from PIL import Image
app = FastAPI()

@app.post("/generate")
async def generate():
    buf = io.BytesIO(); Image.new("RGB", (1536, 864), (40, 120, 90)).save(buf, "PNG")
    return Response(content=buf.getvalue(), media_type="image/png")
# uvicorn stub_server:app --port 8000
```

Then `uv run atlas episode run 11 --stages 2 --scene S01 --image-provider local
--force` should write `S01_a.png` and `S01_b.png`, and `uv run atlas costs` should
show `$0` `2_images` rows.
