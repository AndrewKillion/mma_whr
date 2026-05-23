from __future__ import annotations

import math

# Internal WHR parameter r = ln(gamma) for within-career movement around division offset.
# ~±650 Elo of movement within a division on top of elo_offset.
RATING_R_MIN = -6.0
RATING_R_MAX = 6.0


def clamp_rating_r(r: float) -> float:
    return max(RATING_R_MIN, min(RATING_R_MAX, r))


def log_gamma_from_elo(elo: float) -> float:
    return elo * math.log(10) / 400.0


def gamma_from_elo(elo: float) -> float:
    log_g = clamp_rating_r(log_gamma_from_elo(elo))
    rval = math.exp(log_g)
    if not math.isfinite(rval) or rval <= 0.0:
        raise AttributeError("bad adjusted gamma")
    return rval


def opponent_adjusted_gamma_from_elo(opponent_elo: float) -> float:
    return gamma_from_elo(opponent_elo)
