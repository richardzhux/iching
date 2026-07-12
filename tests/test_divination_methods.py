from collections import Counter
from datetime import datetime
from itertools import product

import pytest

from iching.core.divination import MeihuaMethod, ShicaoMethod


class _SequenceRng:
    def __init__(self, draws):
        self._draws = iter(draws)

    def random(self):
        return next(self._draws)


@pytest.mark.parametrize(
    ("draws", "expected"),
    [
        ((0.75, 0.5, 0.5), 6),
        ((0.0, 0.5, 0.5), 7),
        ((0.75, 0.0, 0.0), 8),
        ((0.0, 0.0, 0.0), 9),
    ],
)
def test_yarrow_uses_canonical_removal_boundaries(draws, expected):
    assert ShicaoMethod._calculate_line(_SequenceRng(draws)) == expected


def test_yarrow_elementary_outcomes_have_exact_canonical_weights():
    outcomes = Counter(
        ShicaoMethod._calculate_line(_SequenceRng(draws))
        for draws in product((0.0, 0.25, 0.5, 0.75), (0.0, 0.5), (0.0, 0.5))
    )

    assert outcomes == {6: 1, 7: 5, 8: 7, 9: 3}


def test_meihua_numbers_use_first_number_for_upper_trigram():
    answers = iter(("y", "101", "202", "303"))

    lines = MeihuaMethod().generate_lines(
        interactive=True,
        input_func=lambda _prompt: next(answers),
        sleep_func=lambda _seconds: None,
    )

    assert lines == [7, 7, 6, 8, 7, 7]


def test_meihua_time_uses_classical_lunar_formula():
    cast_time = datetime(2026, 7, 12, 10, 30)

    trigrams = MeihuaMethod._calculate_trigrams(cast_time)

    assert trigrams == (8, 6, 4)
    assert MeihuaMethod._construct_hexagram(*trigrams) == [8, 7, 8, 6, 8, 8]


def test_meihua_time_uses_chinese_new_year_as_year_boundary():
    assert MeihuaMethod._calculate_trigrams(datetime(2026, 2, 16, 10, 30)) == (7, 5, 5)


def test_meihua_constructs_upper_zhen_over_lower_kan_bottom_to_top():
    assert MeihuaMethod._construct_hexagram(4, 6, 4) == [8, 7, 8, 9, 8, 8]
