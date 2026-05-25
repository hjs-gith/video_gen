from pathlib import Path

from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()

ROOT = Path(__file__).parent.parent.parent
EPISODES_YAML_DIR = ROOT / "episodes_yaml"
EPISODES_OUTPUT_DIR = ROOT / "episodes"
ATLAS_BIBLE_DIR = ROOT / "atlas" / "bible"
LOGS_DIR = ROOT / "logs"
PLAN_FILES_DIR = ROOT / "plan_files"

SCRIPT_MODEL = os.getenv("SCRIPT_MODEL", "gpt-5.4")
IMAGE_MODEL = "gpt-image-2"
IMAGE_SIZE = "1536x864"
IMAGE_QUALITY = "high"
TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE_EN = "nova"
TTS_VOICE_KO = "nova"
TTS_SPEED = float(os.getenv("TTS_SPEED", "1.1"))  # 0.25–4.0; 1.0 = normal

TIER_HEX: dict[str, str] = {
    "T1": "#D94F3A",
    "T2": "#2C5F4F",
    "T2.5": "#B8741A",
    "T2.7": "#4A5FB8",
    "T3": "#6B3A8C",
}

# Maps beat type → Atlas pose name for atlas_in_scene inference
BEAT_TO_POSE: dict[str, str] = {
    "HOOK": "neutral",
    "DEFINITION": "pointing",
    "METAPHOR": "thinking",
    "CONCRETE_EXAMPLE": "working",
    "WHY_IT_MATTERS": "happy",
    "STICKY_TAKEAWAY": "neutral",
}

# Poses that always include Atlas
ATLAS_BEATS = {"HOOK", "STICKY_TAKEAWAY"}

# Verbatim style block — must be identical across all 50 episodes
SERIES_STYLE_BLOCK = (
    "SERIES STYLE — AI JARGON ATLAS:\n"
    "A cozy 16-bit pixel-art explainer scene (modern indie-game aesthetic).\n"
    "Soft cream background (#F5E8C9) with subtle, restrained pixel texture.\n"
    "Every illustrated element — props, icons, and any characters — is clean\n"
    "pixel art with thick charcoal (#1F2530) outlines, soft pixel lighting,\n"
    "and a limited cozy-tech palette. One accent color per scene for emphasis:\n"
    "{tier_hex}. Headlines and labels stay crisp, bold, and highly legible,\n"
    "sitting clearly above the scene with strong contrast (a clean pixel or\n"
    "sans-serif face). Generous breathing room around the focal subject.\n"
    "No gradients beyond simple pixel dithering, no drop shadows (a soft\n"
    "contact shadow under floating elements is fine), no photographic\n"
    "textures, no stock photography, no 3D rendering, no realistic humans,\n"
    "no clip art. The mood is calm, friendly, premium cozy-tech — like a\n"
    "warm retro-game explainer."
)

# Compact on-model description of Atlas for scene composition (distilled from
# atlas_bible._SHARED_CHARACTER_BLOCK). Injected into image prompts when a
# scene includes Atlas; the bible reference PNGs carry the precise look.
ATLAS_CHARACTER_BLURB = (
    "ATLAS (series mascot — render exactly like the reference image):\n"
    "A small floating pixel-art robot. Its head is a rounded retro CRT monitor\n"
    "with a thick cream (#F5E8C9) bezel and a darker charcoal (#1F2530) screen;\n"
    "the face is made only of soft-green (#A8D89C) pixels. A small cream capsule\n"
    "body floats beneath the head, with two short rounded mitten-like cream arms\n"
    "and a small charcoal contact-shadow disc below. No legs, no feet, no mouth.\n"
    "Keep Atlas on-model: strict 4-color palette, thick charcoal outline. Place\n"
    "Atlas naturally inside the scene as a participant, not a flat cutout sticker."
)


def _client(env_var: str) -> OpenAI:
    key = os.getenv(env_var, "").strip().strip("'\"")
    if not key:
        raise RuntimeError(f"Missing {env_var} in .env")
    return OpenAI(api_key=key)


script_client = _client("SCRIPT_API")
image_client = _client("IMAGE_API")
tts_client = _client("TTS_API")
