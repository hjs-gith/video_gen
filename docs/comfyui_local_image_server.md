# Driving stage 2 with ComfyUI (FLUX.1 dev / FLUX.2 klein)

The pipeline's `--image-provider local` speaks a tiny contract (see
[local_image_server.md](local_image_server.md)):

```
POST {IMAGE_LOCAL_URL}  {prompt, width, height, reference_images:[b64...], steps}  ->  PNG
```

ComfyUI does **not** speak this directly — its API is a workflow-graph protocol. The
clean bridge is a small **shim server** that implements the contract above and
translates each call into ComfyUI's API. Nothing in this repo changes; ComfyUI stays
external; switching models is just swapping a workflow template.

## How ComfyUI's API works

- `POST /prompt` — body `{"prompt": <workflow in API JSON>, "client_id": <id>}`; returns
  `{"prompt_id": ...}`. Queues the graph.
- `GET /history/{prompt_id}` — poll until the entry exists; its `outputs` list the
  images each `SaveImage` node produced (`{filename, subfolder, type}`).
- `GET /view?filename=..&subfolder=..&type=output` — download the PNG bytes.
- `POST /upload/image` — multipart upload of an input image; returns the stored
  `filename` you then set into a `LoadImage` node.

You get the workflow JSON from ComfyUI via **Save → "Save (API Format)"**. That file is
the node graph keyed by node id; you patch a few node inputs per request.

## Mode → template mapping

Stage 2 makes two calls per scene — an opaque **background** then a transparent
**foreground** (`transparent: true`). The shim picks a template from `transparent` +
`reference_images`:

| Call | Request fields | Template | FLUX.2 klein wiring |
| --- | --- | --- | --- |
| Background | `transparent:false`, `reference_images:[]` | `workflow_txt2img.json` | CLIPTextEncode → sampler → VAEDecode → SaveImage |
| Foreground (non-Atlas) | `transparent:true`, `reference_images:[]` | `workflow_txt2img.json` + cutout | …→ SaveImage, then segment to RGBA |
| Foreground (Atlas) | `transparent:true`, bible PNGs (1–2) | `workflow_edit.json` + cutout | LoadImage(s) → VAEEncode (FLUX.2 VAE) → **Multi ReferenceLatent** → sampler, then segment to RGBA |

For each request the shim patches: the **positive CLIPTextEncode** text, **width/height**
(EmptyLatentImage or the sampler's latent), a fresh **seed**, and — for the edit
template — the **LoadImage `image` filename(s)** to the just-uploaded references. When
`transparent` is true it must also **cut the subject out to RGBA** (see below).

### Transparency (foreground layer)

ComfyUI/FLUX render opaque images, so for `transparent: true` add a background-removal
step before returning — either an `rembg`/segmentation custom node inside the workflow
(e.g. `Image Remove Background (rembg)`) whose `SaveImage` writes an RGBA PNG, or remove
it in the shim after fetching the bytes (`pip install rembg`). Return the RGBA PNG.

## Which model

- **FLUX.2 [klein] (recommended):** one checkpoint does txt2img *and* multi-reference
  editing, so you need only the two templates above. The 4B is Apache-2.0 (~8 GB VRAM).
  Multi-reference = encode each reference with the FLUX.2 VAE → Multi ReferenceLatent →
  sampler. See <https://docs.comfy.org/tutorials/flux/flux-2-klein>.
- **FLUX.1 [dev]:** txt2img only. Reference/editing needs the separate **FLUX.1 Kontext
  [dev]** model and its own template (a third template + extra weights). Prefer klein
  unless you specifically need FLUX.1.

## The shim server

Runs next to ComfyUI. `pip install fastapi uvicorn requests`, then
`uvicorn comfy_shim:app --port 8000`, and point the pipeline at it:

```bash
export IMAGE_PROVIDER=local
export IMAGE_LOCAL_URL=http://127.0.0.1:8000/generate
uv run atlas episode run 11 --stages 2 --image-provider local
```

```python
# comfy_shim.py — translate the stage-2 contract into ComfyUI API calls.
import base64, copy, io, json, time, uuid
import requests
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel

COMFY = "http://127.0.0.1:8188"          # your ComfyUI server
TXT2IMG = json.load(open("workflow_txt2img.json"))
EDIT    = json.load(open("workflow_edit.json"))

# --- node ids to patch: read these off YOUR exported API-format workflows ---
# (open the JSON; find the node whose class_type matches and note its key)
TXT_NODES  = {"prompt": "6", "latent": "5", "seed": "3", "save": "9"}
EDIT_NODES = {"prompt": "6", "seed": "3", "save": "9",
              "load_images": ["10", "11"]}   # LoadImage nodes for up to 2 refs

app = FastAPI()

class Req(BaseModel):
    prompt: str
    width: int = 1536
    height: int = 864
    reference_images: list[str] = []
    steps: int = 28
    transparent: bool = False

def _upload(png_b64: str) -> str:
    data = base64.b64decode(png_b64)
    r = requests.post(f"{COMFY}/upload/image",
                      files={"image": (f"ref_{uuid.uuid4().hex}.png", data, "image/png")},
                      data={"type": "input", "overwrite": "true"})
    r.raise_for_status()
    return r.json()["name"]

def _build(req: Req) -> dict:
    if req.reference_images:
        g, n = copy.deepcopy(EDIT), EDIT_NODES
        names = [_upload(b) for b in req.reference_images]
        for slot, name in zip(n["load_images"], names):
            g[slot]["inputs"]["image"] = name
    else:
        g, n = copy.deepcopy(TXT2IMG), TXT_NODES
        g[n["latent"]]["inputs"]["width"] = req.width
        g[n["latent"]]["inputs"]["height"] = req.height
    g[n["prompt"]]["inputs"]["text"] = req.prompt
    g[n["seed"]]["inputs"]["seed"] = uuid.uuid4().int % (2**32)
    return g

@app.post("/generate")
def generate(req: Req):
    client_id = uuid.uuid4().hex
    pid = requests.post(f"{COMFY}/prompt",
                        json={"prompt": _build(req), "client_id": client_id}
                        ).json()["prompt_id"]
    # poll until the job shows up in history with outputs
    while True:
        hist = requests.get(f"{COMFY}/history/{pid}").json()
        if pid in hist:
            outs = hist[pid]["outputs"]
            img = next(i for o in outs.values() if "images" in o for i in o["images"])
            break
        time.sleep(0.5)
    png = requests.get(f"{COMFY}/view", params={
        "filename": img["filename"], "subfolder": img.get("subfolder", ""),
        "type": img.get("type", "output")}).content
    if req.transparent:                       # foreground layer -> isolate to RGBA
        from rembg import remove              # pip install rembg  (or use a node)
        png = remove(png)
    return Response(content=png, media_type="image/png")
```

### Adapting it

1. Build your FLUX workflow in ComfyUI, test it in the UI, then **Save (API Format)**
   twice: once for txt2img (no LoadImage) → `workflow_txt2img.json`, once for editing
   (LoadImage → VAEEncode → Multi ReferenceLatent) → `workflow_edit.json`.
2. Open each JSON and fill `TXT_NODES` / `EDIT_NODES` with the real node-id keys
   (match by `class_type`: CLIPTextEncode = prompt, EmptyLatentImage/EmptySD3LatentImage
   = latent, the sampler's seed node = seed, SaveImage = save, LoadImage = references).
3. The edit template needs as many `LoadImage` nodes as the most references you'll send
   (Atlas foregrounds send up to 2 bible images). If you send fewer than the template
   has, either give unused LoadImage nodes a harmless default image or use the "Flux
   Klein Ref Grid" approach to stitch references into one image.
4. Keep width/height consistent so the background and foreground match for the stage-3
   parallax composite. For `transparent` foregrounds, add the rembg cutout (shown above)
   or a background-removal node so the returned PNG is RGBA.

## Verify without wiring FLUX yet

The stub in [local_image_server.md](local_image_server.md#testing-the-wiring-without-a-gpu)
returns a solid PNG for any request — use it first to confirm the pipeline ↔ contract
path, then drop in this ComfyUI shim once your FLUX workflow runs in the UI.
