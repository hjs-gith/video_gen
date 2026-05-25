# 2. Image Prompt Builder — for gpt-image-2 (Presentation Style)

A focused prompt that takes the script JSON from Step 1 and produces ready-to-call `gpt-image-2` prompts for each scene. Optimized for **presentation-style videos with minimal illustrations** — think clean lecture slides, not full animations.

This guide is based on OpenAI's official [GPT Image Generation Models Prompting Guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide) (April 21, 2026).

---

## Why This Aesthetic Works for a 50-Episode Series

**Presentation style beats full animation for this project** for three reasons:

1. **gpt-image-2 is exceptional at "clean classroom handout" outputs** — the cookbook's scientific/educational example is literally the template we want
2. **Consistency is easier** — flat, slide-like visuals vary less per generation than complex illustrated scenes
3. **Production scales** — a slide image + voiceover + simple zoom/pan in your editor = a finished episode. You don't need motion designers per scene.

The visual language: **white/off-white background, clean sans-serif typography, simple flat icons, generous whitespace, one accent color per video (the tier color), clear hierarchy, no decorative clutter.**

---

## Key Lessons from the OpenAI Cookbook for gpt-image-2

These shape every prompt we write:

1. **Write like a brief, not a poem.** "Stunning, cinematic, 8K" is noise. "1536x864 slide, white background, single accent #d94f3a, headline top-left, three-icon row centered" is information the model can draw.
2. **Name the deliverable.** Always start with the artifact type: "Create one educational slide titled..." or "Create a clean diagram showing..."
3. **Put literal text in quotes.** Anything that must appear in the image goes in double quotes, verbatim. For tricky terms, consider spelling out letter-by-letter.
4. **Specify what NOT to include.** Negative constraints are first-class. "No clip art, no stock photos, no gradients, no shadows, no decorative elements."
5. **Use `quality="high"` for any text or diagrams.** `medium` is fine for purely illustrative images; `high` is required when small text or labels appear.
6. **Define hierarchy and spacing.** Real slide language: "headline top", "three columns", "small footnote bottom-right". The model respects these.
7. **State invariants on every prompt.** Style, palette, and typography must be restated each call to prevent drift across the 50-episode series.

---

## API Reference (gpt-image-2)

```python
from openai import OpenAI
client = OpenAI()

result = client.images.generate(
    model="gpt-image-2",
    prompt=PROMPT,
    size="1536x864",     # 16:9 deck slide — see size table below
    quality="high",      # use "high" for any text or diagrams
)

import base64
image_bytes = base64.b64decode(result.data[0].b64_json)
with open("scene_S01.png", "wb") as f:
    f.write(image_bytes)
```

### Sizes for this project

| Use | Size | Notes |
|---|---|---|
| **16:9 slide (primary)** | `1536x864` | Cookbook's recommended deck size; main YouTube format |
| **1:1 master (alternative)** | `1024x1024` | If you want one master and crop in editor |
| **9:16 vertical (Shorts/Reels)** | `1024x1536` (portrait) | Generate separately, or letterbox the 16:9 |

For the prototype, I recommend **`1536x864` as the single primary size** — generate once, letterbox or crop in post for vertical platforms.

### Quality

- **`high`** — required for scenes with on-screen text, diagrams, labels, or anything with small text
- **`medium`** — acceptable for purely illustrative scenes with no text
- **`low`** — only for rapid drafting/preview; don't ship

---

## THE LOCKED STYLE SYSTEM

This block goes into **every single prompt**, unchanged, for all 50 episodes. Series consistency depends on it being identical every time.

```
SERIES STYLE — AI JARGON ATLAS:
Clean educational slide design. Off-white background (#F4F1EA).
Modern sans-serif typography (Inter or similar). Bold black text for
headlines and labels. Generous whitespace. Minimal flat icons —
geometric shapes, single-line illustrations, no detailed drawings.
One accent color per slide: [TIER_HEX]. Crisp 1.5–2px black outlines on
icons. No gradients, no shadows (except optional soft contact shadow
under floating elements), no photographic textures, no clip art, no
stock photography, no 3D rendering, no decorative flourishes.
The aesthetic resembles a polished editorial explainer slide — like
something from a premium business or science magazine.
```

### Tier Accent Colors

| Tier | Hex | Used for |
|---|---|---|
| T1   | `#D94F3A` | Everyday terms |
| T2   | `#2C5F4F` | Workplace terms |
| T2.5 | `#B8741A` | Capability terms |
| T2.7 | `#4A5FB8` | Knob/dial terms |
| T3   | `#6B3A8C` | Big-picture terms |

---

## PROMPT CONSTRUCTION TEMPLATE

Every scene's prompt follows this exact six-part order. The cookbook explicitly warns against unstructured prose; this skimmable order is what `gpt-image-2` parses best.

```
[1. DELIVERABLE]
Create one educational presentation slide for a series on AI concepts.

[2. STYLE SYSTEM — paste verbatim, never modify]
SERIES STYLE — AI JARGON ATLAS:
Clean educational slide design. Off-white background (#F4F1EA). Modern
sans-serif typography (Inter or similar). Bold black text for headlines
and labels. Generous whitespace. Minimal flat icons — geometric shapes,
single-line illustrations, no detailed drawings. One accent color per
slide: [TIER_HEX]. Crisp 1.5–2px black outlines on icons. No gradients,
no shadows, no photographic textures, no clip art, no stock photography,
no 3D rendering, no decorative flourishes. The aesthetic resembles a
polished editorial explainer slide.

[3. LAYOUT]
Canvas: 1536x864 (16:9). Layout: [describe — e.g., "Headline top-left,
single large icon centered, short caption bottom-right"]. Hierarchy:
[describe — e.g., "Headline largest, caption small, icon dominant"].

[4. CONTENT]
Headline (verbatim, exact spelling): "[ON_SCREEN_TEXT_EN]"
[If Korean version: Headline: "[ON_SCREEN_TEXT_KO]"]
[Optional caption, label, or callout text — also in quotes if verbatim]
Visual element: [translation of visual_intent into concrete iconography —
e.g., "A simple flat-style icon of a stack of three books on the left,
with a small geometric AI-shape (rounded square with a single dot eye)
on the right, connected by a thin arrow"]

[5. CONSTRAINTS]
- All text rendered crisply and legibly
- Render text EXACTLY as written, no extra characters or words
- Single accent color only: [TIER_HEX]
- No watermark, no logos, no extra text beyond what is specified
- No people, no faces, no hands (unless explicitly part of the metaphor)
- No gradient backgrounds, no drop shadows except a faint contact shadow

[6. RENDERING SPEC]
Quality: high. Format: 16:9 educational slide ready for video voiceover.
```

---

## EXAMPLE: Full Prompt for One Scene

For a scene in the "RAG" episode (Tier 1) where we introduce the open-book-exam metaphor:

**`visual_intent` from script:**
> A simple split-screen layout: on the left, an AI shape (rounded square with a dot eye) sitting at an empty desk looking confused. On the right, the same AI shape at a desk with three open books, looking confident. A small label above each side.

**Generated `gpt-image-2` prompt:**

```
Create one educational presentation slide for a series on AI concepts.

SERIES STYLE — AI JARGON ATLAS:
Clean educational slide design. Off-white background (#F4F1EA). Modern
sans-serif typography (Inter or similar). Bold black text for headlines
and labels. Generous whitespace. Minimal flat icons — geometric shapes,
single-line illustrations, no detailed drawings. One accent color per
slide: #D94F3A. Crisp 1.5–2px black outlines on icons. No gradients,
no shadows, no photographic textures, no clip art, no stock photography,
no 3D rendering, no decorative flourishes. The aesthetic resembles a
polished editorial explainer slide.

Canvas: 1536x864 (16:9). Layout: Split screen — left half and right half
divided by a thin vertical line. Each side has a small label at the top
and a flat-icon scene below. Hierarchy: Labels small and clean, scene
icons dominant.

Headline labels (verbatim, exact spelling):
Left side label: "WITHOUT RAG"
Right side label: "WITH RAG"

Visual elements:
Left side: A simple flat-icon "AI character" — a rounded square outlined
in black with a single small dot for an eye — sitting at a minimal desk.
The desk is empty. The character's expression line suggests uncertainty
(a small wavy mouth). Black outlines only with no fill except the
off-white background.

Right side: The same flat-icon AI character at an identical desk, but
now with three open books stacked or fanned out in front of it. The
books are outlined in black with the accent color #D94F3A filling
the pages. The character looks confident (a small upturned mouth
line). A thin black arrow points from the books toward the character's
eye, indicating "looking up information".

Constraints:
- All text rendered crisply and legibly
- Render text EXACTLY as "WITHOUT RAG" and "WITH RAG", no extra characters
- Single accent color only: #D94F3A (used on the books and nowhere else)
- No watermark, no logos, no extra text
- No people, no human faces, no hands
- No gradient backgrounds, no drop shadows

Quality: high. Format: 16:9 educational slide ready for video voiceover.
```

---

## THE BUILDER PROMPT (for LLM input)

Paste this into your script-to-image conversion step:

````
You are a visual director and prompt engineer for "AI Jargon Atlas" — a
presentation-style educational video series. Your job: take a script JSON
and produce one ready-to-call gpt-image-2 prompt for each scene.

These prompts will be sent directly to the OpenAI Images API
(model="gpt-image-2", size="1536x864", quality="high"). They must be
written in the structured 6-part format defined in the style guide.

═══════════════════════════════════════════════
INPUTS
═══════════════════════════════════════════════

SCRIPT_JSON:        [paste the full Script Builder output]
LANGUAGE_VARIANT:   [en | ko] — which language's on_screen_text to use
                    in the image. (Generate twice if you need both.)

═══════════════════════════════════════════════
LOCKED STYLE SYSTEM — DO NOT MODIFY
═══════════════════════════════════════════════

[Paste the SERIES STYLE block from the guide verbatim]

Tier hex colors:
- T1: #D94F3A   T2: #2C5F4F   T2.5: #B8741A
- T2.7: #4A5FB8   T3: #6B3A8C

═══════════════════════════════════════════════
RULES
═══════════════════════════════════════════════

For each scene in SCRIPT_JSON.scenes:

1. Read the scene's `visual_intent` and `on_screen_text` fields.
2. Translate `visual_intent` into concrete iconography using the series'
   visual vocabulary:
   - AI = rounded square outlined in black with a single dot eye
   - Humans = simple silhouettes, no facial detail
   - Data/documents = stacked rectangles or paper-stack icons
   - Knowledge sources = open books, file icons, or library shapes
   - Connections/flow = thin black arrows
3. Build the prompt in the exact 6-part order: Deliverable → Style System →
   Layout → Content → Constraints → Rendering Spec.
4. Quote all on-screen text verbatim. Specify "render text EXACTLY as
   written."
5. Use only the tier's accent color, applied to ONE visual element.
   Everything else stays off-white background + black outline.
6. Restate every invariant in every prompt — do not assume earlier scenes'
   context carries over. The image model has no memory between calls.
7. If a scene is purely a text card (no illustration), still build a full
   prompt — just describe a minimal layout with the headline centered.

═══════════════════════════════════════════════
OUTPUT SCHEMA
═══════════════════════════════════════════════

Return VALID JSON with this exact shape:

{
  "meta": {
    "term": "string (from script)",
    "tier": "string",
    "tier_hex": "string",
    "language_variant": "en | ko",
    "image_model": "gpt-image-2",
    "image_size": "1536x864",
    "image_quality": "high",
    "scene_count": number
  },

  "scenes": [
    {
      "scene_id": "S01",
      "visual_intent_source": "the original visual_intent from script",
      "on_screen_text_used": "the on_screen_text in chosen language",
      "image_prompt": "the full 6-part prompt, ready to send to gpt-image-2",
      "api_call_example": "client.images.generate(model='gpt-image-2', prompt=image_prompt, size='1536x864', quality='high')"
    }
  ],

  "consistency_checklist": {
    "all_prompts_include_style_system_verbatim": true,
    "all_text_quoted_with_exact_spelling": true,
    "single_accent_color_used_per_scene": true,
    "negative_constraints_present_in_every_prompt": true,
    "deliverable_named_first_in_every_prompt": true,
    "quality_high_specified": true
  }
}

═══════════════════════════════════════════════
NOW GENERATE
═══════════════════════════════════════════════

Return only the JSON. Do not include explanations.
````

---

## Production Workflow Checklist

For each episode:

1. **Run Script Builder** → get script JSON
2. **Run this Image Prompt Builder** → get image prompt JSON
3. **Loop the scenes** → call gpt-image-2 API per scene → save PNGs
4. **Quality review** → check that text rendered correctly, accent color is consistent, no extra elements
5. **Retry weak frames individually** (~10–20% of scenes typically need a regen) — change one thing per retry
6. **Drop images into video editor** → match to voiceover timing → add simple zoom/pan if desired → export

### Things That Will Save You Time

- **Generate 2 candidates per scene** (`n=2` if supported, or call twice). Pick the best. Adds ~$0.10 per scene but cuts retry rounds.
- **Pin the gpt-image-2 model snapshot** in production (don't use a floating alias) so behavior doesn't drift mid-series.
- **Log every prompt + output** so you can A/B compare when something looks off.
- **Build a "good prompts" library** — when one scene comes out perfectly, save the exact prompt as a reference for future similar scenes.
- **Run a moderation check** on user-derived text (probably not needed here since all content is curriculum-controlled, but worth knowing).

### Common Failure Modes & Fixes

| Symptom | Fix |
|---|---|
| Text comes out garbled or misspelled | Re-quote the text and add "render text EXACTLY as written, character-for-character" |
| Korean text doesn't render | Hangul rendering is unreliable in image models; consider overlaying Korean text in your video editor as a separate layer instead of asking the image AI to render it |
| Style drifts (extra colors appearing) | Add "ONLY one accent color: [HEX]. All other elements must be black outline on off-white background." |
| Icons look like clip art | Add "geometric line-art only, no clip-art aesthetic, no stock illustration look" |
| Layout doesn't match what you specified | Be more concrete about position: "headline at exactly 80px from top, centered horizontally" |
| Inconsistent across scenes | Verify the style system block is byte-identical across all prompts; even small changes cause drift |

---

## A Note on Korean Text in Images

Image models — gpt-image-2 included — handle Korean (Hangul) less reliably than Latin script. For the bilingual series, the safest workflow is:

1. **Generate slides with English on-screen text** via gpt-image-2
2. **Overlay Korean text in your video editor** as a separate text layer on the same slide
3. This gives you perfect typography control for Korean and avoids regen costs from misspelled Hangul

If you do want both languages baked into the image, generate one slide per language variant and accept that some Korean renders may need retries.

---

## Decision Recap

For the prototype, lock these:

- **Model:** `gpt-image-2`
- **Size:** `1536x864` (one master 16:9; crop in post for vertical)
- **Quality:** `high` for all scenes (every scene has text)
- **Style:** locked SERIES STYLE block, used verbatim
- **Accent:** one tier color per episode, applied to one element per scene
- **Text approach:** English baked into image; Korean overlaid in video editor

Once you've run 5–10 pilot scenes and the aesthetic is locked, this becomes a fully automatable pipeline.
