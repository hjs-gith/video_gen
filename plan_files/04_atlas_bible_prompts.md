# Atlas Character Bible — 6 Expression Prompts

Refined prompts for generating the full character expression set, matching the established pixel-art reference design.

---

## Refinements Applied to Your Original Prompt

Compared to the prompt you used to generate the reference, I made these tightening edits in every prompt below:

1. **Body shape locked to capsule/blob** (not square) — matches reference
2. **Floating shadow disc** specified beneath body
3. **Cream bezel framing darker screen area** locked in
4. **Eye style** described as "soft-green pixel squares with subtle internal lighter pixels, resembling glowing terminal cursors"
5. **Color palette explicit hex codes** added: cream `#F5E8C9`, soft green `#A8D89C`, charcoal `#1F2530`, transparent BG
6. **Expression defined as what appears ON the screen face** — the conceptual core of the character
7. **Scale and proportions** restated in every prompt for consistency

These changes are *additive* — your original prompt was strong; these just tighten the parts that the image model could otherwise drift on.

---

## SHARED CHARACTER BLOCK (paste into every prompt verbatim)

This is the locked identity. Every Bible prompt below includes it word-for-word.

```
CHARACTER — Atlas (the mascot for an AI education series):

Style: High-quality 16-bit pixel art. Modern indie game aesthetic.
Inspired by retro game sprites and clean developer-tool mascots. Crisp
sprite edges, soft pixel-art lighting, subtle cozy-tech atmosphere.
Animation-friendly design.

Color palette (strict 4-color scheme):
- Muted cream #F5E8C9 — head bezel and body
- Soft green #A8D89C — facial expression on screen
- Charcoal #1F2530 — outline and screen display area
- Transparent background

Head:
A rounded square shaped like a small retro PC monitor or CRT display.
The head has a thick cream-colored bezel (#F5E8C9) framing a darker
rectangular charcoal screen area (#1F2530). The screen is where the
face appears. Dark charcoal outline around the entire head shape.

Eyes:
Two small soft-green (#A8D89C) pixel squares positioned inside the
darker screen area, resembling glowing terminal cursors. Eyes have
subtle lighter pixels inside, suggesting a soft glow.

Body:
A small rounded capsule-shaped body floating directly beneath the head.
The body is cream-colored (#F5E8C9) with a charcoal outline. The body
is slightly smaller than the head. No visible arms, legs, hands, or feet.

Float indicator:
A small horizontal charcoal shadow disc positioned directly below the
body, suggesting Atlas floats just above the ground.

Mouth: None. Atlas has no mouth — expression is conveyed entirely
through the screen face.

Proportions: The character occupies the central 50% of the canvas with
generous transparent padding. Front-facing pose unless otherwise noted.

Forbidden elements: No additional objects, no text labels on the
character itself, no detailed shading beyond the 4-color palette, no
gradients, no photographic rendering, no 3D rendering, no extra
limbs, no facial features beyond what's specified on the screen.
```

---

## CORE PRINCIPLE: The Screen Shows ONE State at a Time

Atlas's screen is a single display surface. It shows exactly one state per frame — never eyes plus an overlay icon simultaneously. Eyes ARE a screen state (the neutral/idle state). When Atlas is thinking, working, erroring, etc., the eyes are **replaced** by the new screen content, not joined by it.

This rule applies to every expression below:

- **Neutral** → screen shows: eyes only
- **Thinking** → screen shows: thinking dots only (no eyes)
- **Working** → screen shows: progress bar only (no eyes)
- **Error** → screen shows: error icon only (no eyes)
- **Happy** → screen shows: smile-arc eye-shapes only (these REPLACE neutral eyes — they are the new screen state)
- **Pointing** → screen shows: directional arrow only (no eyes)

Body pose can still convey additional emotion (tilt, height), but the screen itself is single-purpose. This keeps the design coherent — Atlas's screen reads like a real terminal display, not a cluttered HUD.

---

## EXPRESSION 1 — Atlas Neutral (the canonical anchor)

This is the primary reference image. Match the existing reference as closely as possible.

```
Design the canonical front-facing reference sprite of an AI education
mascot named Atlas. This is the locked reference for all future
generations — visual consistency is the top priority.

[PASTE SHARED CHARACTER BLOCK HERE]

Expression for this image:
NEUTRAL / IDLE pose.

Screen face displays:
Two small soft-green pixel-square eyes positioned in the middle of the
darker screen area, slightly closer to the upper half. Both eyes are
identical in size and shape, evenly spaced horizontally, looking
straight ahead. No additional UI elements on the screen — just the two
calm, glowing terminal-cursor eyes.

Body pose:
Body is centered directly beneath the head. Resting idle position.

Canvas:
1024x1024, transparent background. Atlas centered horizontally and
vertically, occupying the central 50% of the canvas. Generous
transparent padding on all sides.

Output:
Sprite-sheet-ready, animation-friendly, no text, no extra objects.
Quality: high.
```

**Save as:** `bible/atlas_neutral.png`

---

## EXPRESSION 2 — Atlas Thinking

Concept: A small thinking indicator appears on the screen alongside the eyes — like a loading thought bubble.

```
Generate a sprite of the same AI education mascot Atlas, in a
THINKING expression. The character identity must remain identical to
the canonical reference.

[PASTE SHARED CHARACTER BLOCK HERE]

Expression for this image:
THINKING pose.

Screen face displays:
NO EYES. The screen does NOT show the neutral two-eye state — the eyes
are replaced entirely by the thinking indicator. The screen displays
three small soft-green (#A8D89C) pixel dots arranged horizontally
across the center of the darker screen area, evenly spaced, like a
typing-indicator or "processing..." animation. The dots are the only
thing on the screen. No eyes, no other UI elements.

Body pose:
Body is tilted very slightly upward, suggesting attentive thought.
Still floating in place with the shadow disc below.

Canvas:
1024x1024, transparent background. Atlas centered, occupying central
50% of canvas.

Output:
Sprite-sheet-ready. Identical character identity to the canonical
reference — same head shape, same body, same outline weight, same
palette. Only the screen content changes.
Quality: high.
```

**Save as:** `bible/atlas_thinking.png`

---

## EXPRESSION 3 — Atlas Working (loading)

Concept: A loading spinner or progress indicator on the screen. The eyes themselves can become focused dashes or be replaced by a loading bar.

```
Generate a sprite of the same AI education mascot Atlas, in a
WORKING / LOADING expression. The character identity must remain
identical to the canonical reference.

[PASTE SHARED CHARACTER BLOCK HERE]

Expression for this image:
WORKING / LOADING pose.

Screen face displays:
NO EYES. The screen does NOT show the neutral two-eye state — the eyes
are replaced entirely by the loading indicator. The screen displays a
single horizontal progress bar centered in the darker screen area: a
thin charcoal-outlined rectangle approximately 70% of the screen's
width, filled about 60% from the left with soft green (#A8D89C). The
empty right portion remains the darker charcoal screen color
(#1F2530). The progress bar is the only thing on the screen. No eyes,
no other UI elements.

Body pose:
Body is straight and centered, focused. Still floating in place with
the small shadow disc below.

Canvas:
1024x1024, transparent background. Atlas centered, occupying central
50% of canvas.

Output:
Sprite-sheet-ready. Identical character identity to the canonical
reference — same head shape, same body, same outline weight, same
palette. Quality: high.
```

**Save as:** `bible/atlas_working.png`

---

## EXPRESSION 4 — Atlas Error (confused)

Concept: A classic error icon or exclamation mark. The eyes can become X-shapes or surprised circles, and a small alert symbol can appear.

```
Generate a sprite of the same AI education mascot Atlas, in an
ERROR / CONFUSED expression. The character identity must remain
identical to the canonical reference.

[PASTE SHARED CHARACTER BLOCK HERE]

Expression for this image:
ERROR / CONFUSED pose.

Screen face displays:
NO EYES. The screen does NOT show the neutral two-eye state — the eyes
are replaced entirely by the error icon. The screen displays a single
large soft-green (#A8D89C) pixel-art exclamation mark "!" centered in
the darker screen area. The exclamation mark is bold, simple, and
takes up most of the screen's vertical space. The exclamation mark is
the only thing on the screen. No eyes, no other UI elements.

Body pose:
Body is tilted very slightly to one side, suggesting a small "uh-oh"
moment. Still floating in place with the shadow disc below.

Canvas:
1024x1024, transparent background. Atlas centered, occupying central
50% of canvas.

Output:
Sprite-sheet-ready. Identical character identity to the canonical
reference — same head shape, same body, same outline weight, same
palette. Quality: high.
```

**Save as:** `bible/atlas_error.png`

---

## EXPRESSION 5 — Atlas Happy / Excited

Concept: Larger, brighter eyes with a small sparkle or "all good" indicator. Could be a small checkmark or stars.

```
Generate a sprite of the same AI education mascot Atlas, in a
HAPPY / EXCITED expression. The character identity must remain
identical to the canonical reference.

[PASTE SHARED CHARACTER BLOCK HERE]

Expression for this image:
HAPPY / EXCITED pose.

Screen face displays:
The screen shows two soft-green (#A8D89C) pixel arcs shaped like
upward curves "^ ^" — like two small smiling/closed-eye shapes. These
arcs REPLACE the neutral square eyes; they are not eyes plus a
modifier, they are the new screen state. Each arc is centered in its
half of the screen, evenly spaced. No additional icons, no sparkles,
no other UI elements — just the two smile-arc shapes filling the
screen.

Body pose:
Body is positioned slightly higher than the neutral pose, as if
bouncing up gently in excitement. The shadow disc beneath the body is
slightly smaller than in neutral (suggesting Atlas has floated a bit
higher). The upward body motion carries the "excited" feeling — the
screen alone shows the happy state.

Canvas:
1024x1024, transparent background. Atlas centered, occupying central
50% of canvas.

Output:
Sprite-sheet-ready. Identical character identity to the canonical
reference — same head shape, same body, same outline weight, same
palette. Quality: high.
```

**Save as:** `bible/atlas_happy.png`

---

## EXPRESSION 6 — Atlas Pointing

Concept: Since Atlas has no arms, "pointing" must work differently. The screen face can show an arrow indicator, and the body can tilt in the direction being indicated.

```
Generate a sprite of the same AI education mascot Atlas, in a
POINTING / DIRECTING expression. The character identity must remain
identical to the canonical reference.

[PASTE SHARED CHARACTER BLOCK HERE]

Expression for this image:
POINTING / DIRECTING pose, indicating "look over there to the right."

Screen face displays:
NO EYES. The screen does NOT show the neutral two-eye state — the eyes
are replaced entirely by a single directional arrow. The screen
displays one large soft-green (#A8D89C) pixel-art arrow ">" pointing
right, centered in the darker screen area. The arrow is bold, simple,
and takes up most of the screen's horizontal space. The arrow is the
only thing on the screen. No eyes, no other UI elements.

Body pose:
The body and head are tilted slightly to the right, as if the entire
character is gesturing toward something on the right. Still floating
in place with the small shadow disc below.

Canvas:
1024x1024, transparent background. Atlas centered, occupying central
50% of canvas.

Output:
Sprite-sheet-ready. Identical character identity to the canonical
reference — same head shape, same body, same outline weight, same
palette. Quality: high.

Note: a mirrored version pointing LEFT can be generated by swapping
"right" and "left" in this prompt (arrow becomes "<", body tilts left).
```

**Save as:** `bible/atlas_pointing.png` (and optionally `atlas_pointing_left.png`)

---

## How to Run These

### Recommended approach for the Bible: image-to-image with the reference

Since you already have one canonical reference image, **don't use `images.generate` for the remaining 5 expressions**. Use `images.edit` with the reference as input. This dramatically improves consistency.

```python
from openai import OpenAI
import base64

client = OpenAI()

# Generate one expression at a time using the original as reference
result = client.images.edit(
    model="gpt-image-2",
    image=[open("bible/atlas_neutral.png", "rb")],  # the canonical reference
    prompt=THINKING_PROMPT,  # one of the 5 expression prompts above
    size="1024x1024",
    quality="high",
    input_fidelity="high",  # critical
    background="transparent"  # preserves transparency
)

image_bytes = base64.b64decode(result.data[0].b64_json)
with open("bible/atlas_thinking.png", "wb") as f:
    f.write(image_bytes)
```

For each new expression, the prompt should:

1. Open with **"Edit the character in the reference image to show a [NEW EXPRESSION]"**
2. **Restate the shared character block** (the model needs the constraints repeated even with a reference)
3. Specify what the **new expression on the screen** looks like
4. Explicitly state: **"Preserve all aspects of the character except the screen expression and body pose. Keep identical head shape, outline weight, color palette, body shape, and proportions."**

### Quality check after generation

Lay all 6 images on a single canvas side-by-side. Verify:

- [ ] Head shape and bezel thickness identical across all 6
- [ ] Body shape and size identical across all 6
- [ ] Color palette identical — no extra colors crept in
- [ ] Outline weight identical
- [ ] Float-shadow disc present and similar size in all 6
- [ ] All expression elements use the same soft green (`#A8D89C`)

If any image fails: regenerate that one with stronger preservation language. Don't modify the rest.

---

## Optional: Additional Expressions to Add Later

These weren't in your requested list but might be useful later. All follow the single-state rule — the screen shows ONE icon, no eyes alongside:

- **Atlas Sleeping** — screen shows "Z Z Z" only, useful for "knowledge cutoff" episodes
- **Atlas Searching** — screen shows a magnifying glass icon only, useful for RAG/retrieval episodes
- **Atlas Connecting** — screen shows a WiFi or link icon only, useful for MCP/tool-use episodes
- **Atlas Locked** — screen shows a padlock icon only, useful for guardrails/safety episodes

These would slot naturally into specific episodes from your curriculum. You can add them to the Bible later as needed; the 6 above are enough to start.

---

## A Note on Why This Character Design Is Especially Strong

The screen-as-face design solves a problem most AI mascots have: how to express "what the AI is doing internally" without anthropomorphizing it. By making the face a UI surface, you can literally render the concept of each episode *on the character itself*:

- "Hallucination" episode → Atlas's screen glitches with static pixels
- "Memory" episode → Atlas's screen shows a save icon
- "Context window" episode → Atlas's screen shows scrolling text
- "Agent" episode → Atlas's screen shows a checklist with items being ticked off

This means Atlas isn't just a mascot — Atlas is a *visualization tool* for the concept being taught. That's a much stronger creative asset than a generic character.

When you scale to 50 episodes, consider building **term-specific Atlas variants** for the most important terms, in addition to the 6 base expressions. They'll become some of the most memorable moments in the series.
