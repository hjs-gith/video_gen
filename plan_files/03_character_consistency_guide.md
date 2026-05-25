# 3. Character Consistency Guide — Atlas, the Series Mascot

How to keep one recurring character visually consistent across all 50 episodes of the AI Jargon Atlas, using `gpt-image-2`'s reference-image capabilities.

---

## TL;DR

1. **Design and generate a "Character Bible" once** — 1 canonical neutral image + 5–7 character-sheet variations (poses, expressions)
2. **Save the Bible as your locked reference set** — never regenerate, never edit
3. **For every scene, call `client.images.edit`** with 2–3 Bible images as references + the scene prompt with `input_fidelity="high"`
4. **Never chain outputs.** Every scene references the original Bible, not the previous scene
5. **Lock everything else** — prompt structure, style block, character description — so the *only* variable per scene is the action

This gives the best character consistency available without fine-tuning.

---

## Why "Atlas" Needs to Be a Real Character

Right now we have a placeholder: "rounded square with a dot eye." Before scaling, give it a name and a clear visual identity. A named, defined character:

- Becomes a recognizable brand asset across the series
- Gives the model a stronger semantic anchor ("Atlas the character")
- Lets viewers form emotional connection across episodes
- Makes thumbnails more clickable (recurring face)

**Suggested name:** Atlas (matches the series name "AI Jargon Atlas")

**Suggested character bible:**

```
ATLAS — the series mascot:

Shape: A rounded square, 1:1 proportions, with corners radiused to about
15% of edge length. Solid 4px black outline. Body color: off-white
#F4F1EA (same as background, so the character reads as outline-only with
a few interior elements).

Eye: A single small black filled circle, approximately 12% of the
character's height in diameter, positioned in the upper-center of the
face. No second eye. No eyelashes, eyebrows, or facial details.

Mouth: Optional — a short straight horizontal line about 30% of the
character's width, positioned in the lower-center. Can curve up slightly
for friendly expressions, or be omitted for neutral.

Limbs: Two short stick-figure arms, each ending in a small filled black
circle as a "hand." Arms emerge from left and right sides at about 60%
height. Optionally two short legs of the same style.

Personality cue (for poses): Curious, helpful, slightly playful — like a
friendly research assistant. Not cute, not silly.

Scale: When other objects appear in scene, Atlas should be roughly the
size of a coffee mug relative to a desk, or a child relative to a
bookshelf. Never towering, never tiny.

What Atlas is NOT:
- Not a robot with mechanical parts, gears, antennae, or screens
- Not a humanoid figure with realistic body proportions
- Not photorealistic, not 3D-rendered
- Not detailed — Atlas is intentionally minimal
```

---

## Step 1: Generate the Character Bible (one-time, ~$2–4)

Run these generations **once**. Save the outputs as `bible/atlas_*.png`. Never regenerate — these are your locked references for the entire series.

### Bible Image 1 — Atlas Neutral (the canonical reference)

```
Create a single character reference illustration on a plain off-white
background (#F4F1EA), centered with generous padding.

Character to render — Atlas:
A rounded square with 1:1 proportions and corners radiused to about 15%
of edge length. Solid 4px black outline. Interior body color is identical
to the background (#F4F1EA), making the character read as outline-only.

One single small black filled circle as an eye, approximately 12% of
character height in diameter, positioned in the upper-center of the face.
No second eye. No eyebrows, no eyelashes, no other facial features.

A short straight horizontal black line as a mouth, about 30% of character
width, positioned in the lower-center face area.

Two short stick-figure arms emerge from the left and right sides at 60%
height. Each arm ends in a small filled black circle as a "hand." Arms
hang naturally at the sides.

Style: Clean flat vector illustration. Minimal. Editorial explainer
aesthetic. No gradients, no shadows, no decorative elements, no text,
no background pattern. The character should occupy the central 40% of
the canvas with whitespace around it.

Render text/labels: None.

Quality: high. Size: 1024x1024. Format: clean reference image for use
as a character anchor in subsequent generations.
```

Save as: `bible/atlas_neutral.png`

### Bible Image 2 — Atlas Thinking

Same prompt but change the pose: "One arm raised to touch the side of the face in a 'thinking' gesture. Mouth slightly curved into a small upward arc."

Save as: `bible/atlas_thinking.png`

### Bible Image 3 — Atlas Pointing

"One arm extended to the right, finger-circle pointing. Other arm at side."

Save as: `bible/atlas_pointing.png`

### Bible Image 4 — Atlas with Book

"Holding a small open book in both hands at chest level. Book outlined in black with white pages."

Save as: `bible/atlas_book.png`

### Bible Image 5 — Atlas Confused

"Mouth curved into a small downward wavy line. Eye slightly larger. One arm scratching head."

Save as: `bible/atlas_confused.png`

### Bible Image 6 — Atlas Happy/Excited

"Both arms raised slightly. Mouth curved up clearly. Eye slightly larger."

Save as: `bible/atlas_happy.png`

### Bible Image 7 — Atlas Walking

"Side profile. One arm and one leg forward, other back, mid-stride."

Save as: `bible/atlas_walking.png`

---

## Step 2: Quality-Check the Bible

Before producing any episode, lay all 7 Bible images side-by-side on a single canvas. Ask:

- [ ] Is the rounded square the same size and corner radius in all 7?
- [ ] Is the eye in the same position, same size, same shape in all 7?
- [ ] Is the outline weight identical in all 7?
- [ ] Do the limbs use the same proportions?
- [ ] Does the character "feel" like the same character across all 7?

If any image fails: regenerate that single image, do not modify the others. Once all 7 pass, the Bible is **locked**. Never regenerate again.

---

## Step 3: Per-Scene Generation Pattern

For every scene in every episode:

```python
from openai import OpenAI
import base64

client = OpenAI()

def generate_scene(scene_id, scene_prompt, pose_hint="neutral"):
    """
    Generate one scene using Atlas character bible references.
    pose_hint determines which Bible images to use as anchors.
    """
    # Always include the neutral as the primary anchor
    # Plus 1–2 pose-relevant references
    POSE_REFERENCES = {
        "neutral":   ["atlas_neutral.png"],
        "thinking":  ["atlas_neutral.png", "atlas_thinking.png"],
        "pointing":  ["atlas_neutral.png", "atlas_pointing.png"],
        "reading":   ["atlas_neutral.png", "atlas_book.png"],
        "confused":  ["atlas_neutral.png", "atlas_confused.png"],
        "happy":     ["atlas_neutral.png", "atlas_happy.png"],
        "walking":   ["atlas_neutral.png", "atlas_walking.png"],
    }

    reference_files = [
        open(f"bible/{ref}", "rb")
        for ref in POSE_REFERENCES[pose_hint]
    ]

    result = client.images.edit(
        model="gpt-image-2",
        image=reference_files,
        prompt=scene_prompt,
        size="1536x864",
        quality="high",
        input_fidelity="high"   # critical for character preservation
    )

    image_bytes = base64.b64decode(result.data[0].b64_json)
    with open(f"output/scene_{scene_id}.png", "wb") as f:
        f.write(image_bytes)

    return f"output/scene_{scene_id}.png"
```

### The Scene Prompt Structure (updated for character consistency)

When using `images.edit` with character references, the prompt no longer needs to *describe* Atlas — the reference images carry that. Instead, focus the prompt on:

1. **What scene Atlas is in**
2. **What Atlas is doing** (matching the pose_hint)
3. **What other elements are in the scene**
4. **What must NOT change about Atlas**

Example for a "RAG" episode scene:

```
Place the character from the reference images into a new educational
slide scene.

Character preservation (critical):
- Use the EXACT same character from the reference images
- Preserve the character's shape (rounded square), proportions, outline
  weight, eye position and size, and overall visual identity
- The character is "Atlas," the series mascot — do not redesign,
  do not add features, do not change colors

Scene composition:
Canvas: 1536x864 (16:9 educational slide). Off-white background
(#F4F1EA). Atlas is positioned on the LEFT side of the canvas at
about 30% from the left edge, vertically centered, in a "reading" pose
(holding the open book from the reference). On the RIGHT side, place
three large open books stacked at slight angles. A thin black arrow
flows from the books toward Atlas's eye, indicating "Atlas looking
things up."

Color: Single accent color #D94F3A applied ONLY to the pages of the
three open books on the right. All other elements (Atlas, arrows,
outlines) remain black on off-white background.

Style:
Clean editorial slide design. Modern sans-serif. Minimal flat icons.
Crisp 1.5–2px black outlines. No gradients, no shadows, no textures,
no clip art, no stock photography aesthetic.

Text on slide (render verbatim, exact spelling):
Top center, bold sans-serif: "Looking things up"

Constraints:
- Atlas must look IDENTICAL to the reference images
- Only one accent color: #D94F3A
- Do not change Atlas's proportions, outline, or features
- No watermark, no extra text, no logos
- Render text exactly as "Looking things up"

Quality: high.
```

Notice what changed from the original Image Prompt Builder:

- **No more describing Atlas in detail** — the reference handles it
- **Explicit "preserve the character" constraints** — the cookbook recommends restating invariants on every call
- **`input_fidelity="high"` in the API call** — critical for preserving the reference character

---

## Updated Image Prompt Builder Logic

Your Image Prompt Builder should now include one extra field per scene: `pose_hint`. This tells the generation step which Bible images to pass as references.

```json
{
  "scene_id": "S03",
  "visual_intent_source": "Atlas reading three books with arrow to his eye",
  "pose_hint": "reading",
  "image_prompt": "[full prompt as shown above]",
  "reference_bible_images": ["atlas_neutral.png", "atlas_book.png"],
  "api_call": "client.images.edit(model='gpt-image-2', image=[...], prompt=image_prompt, size='1536x864', quality='high', input_fidelity='high')"
}
```

Add `pose_hint` to your Script Builder schema too — let the script LLM decide which Atlas pose fits each scene.

---

## What About Chaining Frames?

You asked specifically about passing the previous frame as the reference for the next. Here's the honest answer:

**Don't do it for character consistency.** Drift compounds. By scene 8, the character will look subtly different from scene 1, and the difference grows nonlinearly.

**Do consider it for narrative continuity** within a *single* scene transition where Atlas needs to be in nearly-identical pose with one small change. Example: "Atlas opens the book" → previous frame helps. But even then, always include the neutral Bible image as a co-reference to anchor identity.

The cookbook's children's book example chains forward, but that's for *narrative* drift (the character moves through a story) rather than visual consistency. Your use case is closer to a logo or mascot — you want it identical every time.

**Rule of thumb:**
- Anchor identity → reference the Bible
- Anchor a specific pose continuation → reference Bible + previous frame
- Anchor a brand-new pose → reference Bible only

Never let Atlas drift more than one generation away from a Bible image.

---

## Cost Implications

Using `images.edit` with 2 reference images is slightly more expensive than `images.generate` alone, but for a 50-episode series the math works out:

- **Without reference images:** ~$0.04–0.08 per scene at `quality="high"`. You'll re-roll ~30% of scenes due to character drift. Effective cost ~$0.10/scene.
- **With Bible references:** ~$0.08–0.15 per scene. You'll re-roll ~10%. Effective cost ~$0.12/scene.

For a typical 12-scene episode: roughly $1.50 with references vs $1.20 without. The $0.30 per episode is well worth the consistency and the time saved on re-rolls.

(Pricing is approximate — check the current OpenAI pricing page before scaling.)

---

## Common Failure Modes & Fixes

| Symptom | Fix |
|---|---|
| Atlas's eye drifts to a different position | Use `input_fidelity="high"`. If still drifting, add explicit: "Eye position must match reference: upper-center of face." |
| Outline weight varies between scenes | Add: "Outline weight must match reference exactly: 4px solid black." |
| Atlas suddenly has 2 eyes | Add explicit constraint: "ONE eye only, no second eye." |
| Atlas looks more cartoonish in some scenes | Reduce the variation in pose_hint. If always using "neutral" + one extra, drift is minimal. |
| Color of Atlas's body changes | Add: "Atlas body color is identical to background #F4F1EA. Do not fill the character with any other color." |
| Atlas appears in the wrong size | Specify size explicitly: "Atlas occupies approximately 25% of canvas height." |

---

## The Full Updated Pipeline

```
┌──────────────────────────────────────────────────────────┐
│  ONE-TIME (do once, never repeat):                       │
│  1. Generate 7 Atlas Bible images via images.generate    │
│  2. Quality-check all 7 side-by-side                     │
│  3. Lock the Bible folder; never modify                  │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  PER EPISODE:                                            │
│  1. Run Script Builder → script.json                     │
│     (now includes "pose_hint" field per scene)           │
│  2. Run Image Prompt Builder → image_prompts.json        │
│     (now references Bible images, uses images.edit)      │
│  3. Loop scenes → call gpt-image-2 with Bible refs       │
│  4. Review outputs; re-roll any drift cases              │
│  5. Drop images into video editor with voiceover         │
└──────────────────────────────────────────────────────────┘
```

---

## Recommended Pilot Sequence

Before scaling to 50 episodes, validate the Bible approach with one full episode:

1. **Day 1:** Generate the 7 Bible images. Iterate on Atlas's design until you're happy. Lock the Bible.
2. **Day 2:** Pick "Token" as your pilot term. Run Script Builder. Run Image Prompt Builder. Generate all ~12 scenes using the Bible references.
3. **Day 3:** Lay all 12 scenes side-by-side. Check for drift. Note any patterns (e.g., "every time Atlas is on the right side of frame, his eye shifts"). Add those patterns as constraints.
4. **Day 4:** Re-run any failed scenes with refined prompts. Cut the episode.
5. **Day 5:** Watch the full episode. If Atlas feels consistent throughout — you're ready to scale. If not, iterate the Bible or constraints once more.

If after one full pilot episode Atlas still drifts noticeably, you have two escalation paths:

- **Pre-generate more Bible variants** (15–20 instead of 7) covering every pose you'll need
- **Consider fine-tuning a custom character model** via OpenAI's vision fine-tuning — only worth it if you're committed to 50+ episodes and pilot revealed unfixable drift

For a 50-episode series with simple line-art aesthetic, the Bible approach should be sufficient.
