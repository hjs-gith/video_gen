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
  "steps": 28,
  "transparent": false
}
```

Respond with **HTTP 200** and either:
- the raw PNG bytes (`Content-Type: image/png`), or
- JSON `{"image_base64": "<base64 PNG>"}`.

Honor `width`/`height` exactly — the background and foreground layers must match in
size so the foreground composites and floats cleanly over the background in stage 3.

### Two layers per scene: `transparent` + `reference_images`

Stage 2 renders **two layers** per scene (a parallax pair, composited in stage 3): a
static **background** and a floating **foreground**. Two request fields tell your
server which one to produce:

| Call | `transparent` | `reference_images` | What to render |
| --- | --- | --- | --- |
| Background | `false` | `[]` | the setting + headline, **no** focal subject — an opaque PNG |
| Foreground (non-Atlas) | `true` | `[]` | the focal prop(s) only, on a **transparent** background |
| Foreground (Atlas) | `true` | Atlas bible PNGs (1–2) | Atlas + focal prop(s), transparent, conditioned on the refs so the mascot stays on-model |

**When `transparent` is true, return an RGBA PNG with the subject isolated on a fully
transparent background** (alpha = 0 everywhere except the subject). FLUX doesn't emit
alpha natively, so cut it out after generating — e.g. `rembg`/segmentation, or generate
on a flat key color and remove it. (OpenAI uses its native `background="transparent"`
instead; that path is handled inside the pipeline, not here.)

> Note: stage 2 splits one `visual_intent` into a "background setting" prompt and a
> "focal subject" prompt. If a prop reads as belonging to both, refine that scene's
> `visual_intent`/`on_screen_text` so the subject is clearly the foreground.

## Which model

**FLUX.2 [klein] (recommended).** One model does text-to-image *and* multi-reference
editing — exactly the three modes above. The **4B** variant is Apache-2.0 (commercial
use) and fits ~8 GB VRAM; the 9B is non-commercial. See
<https://github.com/black-forest-labs/flux2> and
<https://huggingface.co/black-forest-labs/FLUX.2-klein-4B>.

**FLUX.1 [dev]** is text-to-image only; you would also need **FLUX.1 Kontext [dev]**
(~24 GB) for the reference/img2img modes — two models to serve. Prefer klein unless
you specifically need FLUX.1.

**Using ComfyUI?** ComfyUI's API is a workflow-graph protocol, not this simple
contract. Run the small shim in [comfyui_local_image_server.md](comfyui_local_image_server.md),
which implements this contract and translates each call into ComfyUI's
`/prompt` + `/upload/image` + `/view` API — so the pipeline stays unchanged and
swapping FLUX.1 ↔ FLUX.2 is just a different workflow template.

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
# from rembg import remove           # or any segmentation model, for cutouts

app = FastAPI()

class Req(BaseModel):
    prompt: str
    width: int = 1536
    height: int = 864
    reference_images: list[str] = []
    steps: int = 28
    transparent: bool = False

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
    if r.transparent:
        image = remove(image.convert("RGBA"))  # isolate subject on transparent bg
    buf = io.BytesIO(); image.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")
```

## Testing the wiring without a GPU

You can verify the pipeline end-to-end with a stub that ignores the prompt and
returns a solid background, or a semi-transparent block for the foreground so the
float is visible:

```python
# stub_server.py
import io
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from PIL import Image
app = FastAPI()

class Req(BaseModel):
    width: int = 1536
    height: int = 864
    transparent: bool = False

@app.post("/generate")
async def generate(r: Req):
    if r.transparent:                                  # foreground: a floating box
        img = Image.new("RGBA", (r.width, r.height), (0, 0, 0, 0))
        img.paste((230, 120, 60, 255), (r.width // 3, r.height // 3,
                                        2 * r.width // 3, 2 * r.height // 3))
    else:                                              # background: solid fill
        img = Image.new("RGB", (r.width, r.height), (40, 120, 90))
    buf = io.BytesIO(); img.save(buf, "PNG")
    return Response(content=buf.getvalue(), media_type="image/png")
# uvicorn stub_server:app --port 8000
```

Then `uv run atlas episode run 11 --stages 2 --scene S01 --image-provider local
--force` should write `S01_bg.png` and `S01_fg.png`, and `uv run atlas costs` should
show `$0` `2_images` rows. Run stage 3 and you'll see the orange block gently bob over
the green background.
