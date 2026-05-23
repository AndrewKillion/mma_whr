from __future__ import annotations

import math

from fight_whr import Base
from fight_whr.weightclass_elo import (
    STARTING_ELO_BY_KEY,
    gamma_from_elo,
    normalize_weightclass_key,
    starting_elo_for,
)


def test_normalize_weightclass_labels() -> None:
    assert normalize_weightclass_key("Lightweight") == "LW"
    assert normalize_weightclass_key("WOMEN'S STRAWWEIGHT") == "WSW"
    assert normalize_weightclass_key("UFC HEAVYWEIGHT TITLE") == "HW"
    assert normalize_weightclass_key("CATCH WEIGHT") == "HW"
    assert normalize_weightclass_key(None) is None


def test_starting_elo_table() -> None:
    assert starting_elo_for("HW") == 1900.0
    assert starting_elo_for("LW") == 1500.0
    assert starting_elo_for("WSW") == 550.0
    assert starting_elo_for("WBW") == 800.0
    assert starting_elo_for("bogus division") is None


def test_first_fight_uses_weightclass_debut_elo() -> None:
    whr = Base()
    whr.create_fight(
        "debut_lw",
        "vet",
        "A",
        1,
        0,
        3,
        {"weightclass": "Lightweight"},
    )
    whr.create_fight("vet", "other", "A", 1, 0, 3, {"weightclass": "Lightweight"})
    debut_day = whr.fighter_by_name("debut_lw").days[0]
    assert abs(debut_day.elo - STARTING_ELO_BY_KEY["LW"]) < 1e-6
    assert abs(debut_day.gamma() - gamma_from_elo(1500.0)) < 1e-9


def test_first_fight_without_weightclass_keeps_legacy_prior() -> None:
    whr = Base()
    whr.create_fight("legacy", "vet", "A", 1, 0, 3, {})
    whr.create_fight("vet", "other", "A", 1, 0, 3, {})
    debut_day = whr.fighter_by_name("legacy").days[0]
    assert debut_day.elo == 0.0
    assert debut_day.gamma() == 1.0


def test_probability_future_match_debut_weightclasses() -> None:
    whr = Base()
    whr.create_fight("vet_hw", "opp", "A", 1, 0, 3, {"weightclass": "Heavyweight"})
    p_hw, p_lw = whr.probability_future_match(
        "vet_hw",
        "rookie_lw",
        weightclass2="Lightweight",
    )
    assert p_hw > p_lw
    assert math.isclose(p_hw + p_lw, 1.0, rel_tol=1e-9)

    p_debut_hw, p_debut_lw = whr.probability_future_match(
        "ghost_hw",
        "ghost_lw",
        weightclass1="Heavyweight",
        weightclass2="Lightweight",
    )
    assert p_debut_hw > p_debut_lw
    assert abs(p_debut_hw - 1 / (1 + 10 ** ((1500 - 1900) / 400))) < 0.01
