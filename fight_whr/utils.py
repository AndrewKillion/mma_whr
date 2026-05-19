from __future__ import annotations


class UnstableRatingException(Exception):
    pass


def test_stability(
    v1: list[list[float]], v2: list[list[float]], precision: float = 10e-3
) -> bool:
    v1_flattened = [x for y in v1 for x in y]
    v2_flattened = [x for y in v2 for x in y]
    for x1, x2 in zip(v1_flattened, v2_flattened):
        if abs(x2 - x1) > precision:
            return False
    return True
