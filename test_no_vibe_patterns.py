from pathlib import Path

ROOT = Path(__file__).parent
TEXT = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in ROOT.rglob("*.html"))

FORBIDDEN = [
    "linear-gradient", "radial-gradient", "box-shadow", "lucide", "emoji",
    "pricing", "testimonial", "bento", "neon", "sparkle", "glassmorphism",
]


def test_frontend_does_not_use_listed_vibe_patterns():
    lowered = TEXT.lower()
    for token in FORBIDDEN:
        assert token not in lowered, token
