from __future__ import annotations

import math
import re

# Canonical division keys → debut Elo for fighters with no WHR history yet.
STARTING_ELO_BY_KEY: dict[str, float] = {
    "HW": 1900.0,
    "LHW": 1800.0,
    "MW": 1750.0,
    "WW": 1700.0,
    "LW": 1500.0,
    "FW": 1450.0,
    "BW": 1400.0,
    "FLW": 1300.0,
    "WBW": 800.0,
    "WFLW": 600.0,
    "WSW": 550.0,
}

# Women's featherweight (not in original table; between WSW and WBW).
STARTING_ELO_BY_KEY["WFW"] = 700.0

_ALIASES: dict[str, str] = {
    "HW": "HW",
    "HEAVYWEIGHT": "HW",
    "HEAVY WEIGHT": "HW",
    "LHW": "LHW",
    "LIGHT HEAVYWEIGHT": "LHW",
    "LIGHTHEAVYWEIGHT": "LHW",
    "MW": "MW",
    "MIDDLEWEIGHT": "MW",
    "WW": "WW",
    "WELTERWEIGHT": "WW",
    "LW": "LW",
    "LIGHTWEIGHT": "LW",
    "FW": "FW",
    "FEATHERWEIGHT": "FW",
    "BW": "BW",
    "BANTAMWEIGHT": "BW",
    "FLW": "FLW",
    "FLYWEIGHT": "FLW",
    "WSW": "WSW",
    "WOMENS STRAWWEIGHT": "WSW",
    "WOMEN'S STRAWWEIGHT": "WSW",
    "WOMEN STRAWWEIGHT": "WSW",
    "STRAWWEIGHT": "WSW",
    "WFLW": "WFLW",
    "WOMENS FLYWEIGHT": "WFLW",
    "WOMEN'S FLYWEIGHT": "WFLW",
    "WOMEN FLYWEIGHT": "WFLW",
    "WBW": "WBW",
    "WOMENS BANTAMWEIGHT": "WBW",
    "WOMEN'S BANTAMWEIGHT": "WBW",
    "WOMEN BANTAMWEIGHT": "WBW",
    "WFW": "WFW",
    "WOMENS FEATHERWEIGHT": "WFW",
    "WOMEN'S FEATHERWEIGHT": "WFW",
    "WOMEN FEATHERWEIGHT": "WFW",
}

_NOISE_RE = re.compile(
    r"\b(UFC|WEC|BELLATOR|TITLE|BOUT|INTERIM|MAIN|EVENT|CHAMPIONSHIP)\b",
    re.IGNORECASE,
)


def _clean_weightclass_text(raw: str) -> str:
    text = raw.strip().upper()
    text = _NOISE_RE.sub("", text)
    text = re.sub(r"[^A-Z0-9'\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_weightclass_key(raw: str | None) -> str | None:
    """Map a fight weight-class label to a canonical key (HW, LW, WSW, ...)."""
    if raw is None:
        return None
    text = _clean_weightclass_text(str(raw))
    if not text:
        return None
    if text in _ALIASES:
        return _ALIASES[text]
    if text in STARTING_ELO_BY_KEY:
        return text
    if "WOMEN" in text or text.startswith("W"):
        if "STRAW" in text:
            return "WSW"
        if "FLY" in text:
            return "WFLW"
        if "BANTAM" in text:
            return "WBW"
        if "FEATHER" in text:
            return "WFW"
    if "HEAVY" in text and "LIGHT" not in text:
        return "HW"
    if "LIGHT" in text and "HEAVY" in text:
        return "LHW"
    if "MIDDLE" in text:
        return "MW"
    if "WELTER" in text:
        return "WW"
    if "LIGHT" in text:
        return "LW"
    if "FEATHER" in text:
        return "FW"
    if "BANTAM" in text:
        return "BW"
    if "FLY" in text:
        return "FLW"
    if "OPEN" in text or "CATCH" in text:
        return "HW"
    return None


def starting_elo_for(
    weightclass: str | None,
    *,
    overrides: dict[str, float] | None = None,
) -> float | None:
    """Return debut Elo for a weight class, or None if the class is unknown."""
    key = normalize_weightclass_key(weightclass)
    if key is None:
        return None
    table = dict(STARTING_ELO_BY_KEY)
    if overrides:
        table.update({str(k).upper(): float(v) for k, v in overrides.items()})
    return table.get(key)


def gamma_from_elo(elo: float) -> float:
    return 10 ** (elo / 400.0)


def gamma_elo_for_debut(
    weightclass: str | None,
    *,
    overrides: dict[str, float] | None = None,
) -> tuple[float, float] | None:
    """Gamma and Elo for a fighter with no fights yet; None if class unknown."""
    elo = starting_elo_for(weightclass, overrides=overrides)
    if elo is None:
        return None
    return gamma_from_elo(elo), elo
