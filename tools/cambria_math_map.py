"""Deterministic repair for the two Foxit-corrupted Cambria Math subsets.

The PDFs in exp11 and exp12 render correctly, but Foxit 2025 wrote the same
incorrect values to both the embedded font cmap and the PDF /ToUnicode CMap.
Consequently every normal PDF text extractor returns Tamil, Telugu, Syriac,
NKo, Sinhala, or Ethiopic characters for mathematical glyphs.

The mappings below are deliberately scoped by experiment.  They were derived
from outline fingerprints matched against the other Cambria Math subsets in
this corpus, then checked against the rendered source pages.  Keeping the map
scoped prevents a real character in another document from being rewritten.
"""

from __future__ import annotations


# Wrong extracted Unicode -> glyph represented by that outline.
# Mathematical alphanumeric characters are retained where the PDF uses them;
# ordinary digits and operators remain ordinary Unicode for RAG readability.
CAMBRIA_MATH_MAPS: dict[str, dict[str, str]] = {
    "exp11": {
        "ଵ": "1", "ோ": "𝑅", "\u0cc5": "𝑇", "ௗ": "𝑑", "்": "𝑇",
        "ܴ": "𝑅", "ଶ": "2", "ߗ": "Ω", "ଷ": "3", "ܫ": "𝐼",
        "ௌ": "𝑆", "݁": "𝑒", "௤": "𝑞", "௎": "𝑈", "௞": "𝑘",
        "ቂ": "[", "ቃ": "]",
        "ൗ": "⁄", "ସ": "4", "ܸ": "𝑉", "\u0bbc": "𝐶", "\u0bbd": "𝐷",
        "\u0bda": "𝑔", "భ": "1", "మ": "2", "ܷ": "𝑈", "ర": "4",
        "ା": "+", "ି": "−", "య": "3", "ೄ": "𝑆", "ߜ": "𝛿",
        "ഃ": "𝛿",
    },
    "exp12": {
        "ݐ": "𝑡", "௡": "𝑛", "݊": "𝑛", "݂": "𝑓", "௠": "𝑚",
        "ܶ": "𝑇", "ௌ": "𝑆", "ݔ": "𝑥", "݉": "𝑚", "ݒ": "𝑣",
        "ܸ": "𝑉", "௣": "𝑝", "൜": "{", "ଵ": "1", "߱": "𝜔",
        "߮": "𝜑", "ଶ": "2", "ఠ": "𝜔", "భ": "1", "ି": "−",
        "మ": "2", "ఝ": "𝜑", "ା": "+", "ன": "𝜔", "\u0ba6": "𝜑",
        "గ": "𝜋", "௬": "𝑦", "௫": "𝑥", "ቚ": "|",
        # These controls occur only because the corrupt Syriac characters
        # made the extractor enter right-to-left layout.
        "\u202b": "", "\u202c": "",
    },
}


def decode_cambria_math(text: str, experiment: str) -> tuple[str, int]:
    """Repair known Cambria Math characters and return ``(text, count)``."""
    mapping = CAMBRIA_MATH_MAPS.get(experiment)
    if not mapping or not text:
        return text, 0
    count = sum(text.count(source) for source in mapping)
    return text.translate(str.maketrans(mapping)), count
