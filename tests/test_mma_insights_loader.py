from __future__ import annotations

from fight_whr.data.mma_insights_loader import normalize_method


def test_normalize_standard_method_codes() -> None:
    assert normalize_method("TKO") == "KO"
    assert normalize_method("SUB") == "Submission"
    assert normalize_method("U_D") == "Unanimous"
    assert normalize_method("D_U") == "Unanimous"
    assert normalize_method("S_D") == "Split"
    assert normalize_method("D_S") == "Split"
    assert normalize_method("OTH") is None


def test_normalize_legacy_text_methods() -> None:
    assert normalize_method("KO/TKO") == "KO"
    assert normalize_method("Submission") == "Submission"
    assert normalize_method("Unanimous Decision") == "Unanimous"
    assert normalize_method("Split Decision") == "Split"
