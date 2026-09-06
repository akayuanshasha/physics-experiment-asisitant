import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from cambria_math_map import decode_cambria_math


def test_exp11_semiconductor_equation():
    broken = "I = ܫ ቂ݁ ௤௎ ൗ ௞் −1ቃ"
    fixed, count = decode_cambria_math(broken, "exp11")
    assert fixed == "I = 𝐼 [𝑒 𝑞𝑈 ⁄ 𝑘𝑇 −1]"
    assert count == 9


def test_exp12_beating_equation_symbols():
    broken = "ఠభିఠమ / ଶగ = ݂ଵ − ݂ଶ; ݂௬ / ݂௫"
    fixed, count = decode_cambria_math(broken, "exp12")
    assert fixed == "𝜔1−𝜔2 / 2𝜋 = 𝑓1 − 𝑓2; 𝑓𝑦 / 𝑓𝑥"
    assert count == 15


def test_mapping_is_experiment_scoped():
    text = "真实正文可能包含 தமிழ் తెలుగు"
    assert decode_cambria_math(text, "exp1") == (text, 0)
