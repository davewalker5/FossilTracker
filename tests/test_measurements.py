import pytest

from ui.measurements import (
    _optional_positive_float,
    calculate_ammonite_measurements,
    calculate_orthocone_measurements,
)


def test_calculate_ammonite_measurements() -> None:
    ratios = calculate_ammonite_measurements(100.0, 30.0, 40.0, 20.0)

    assert ratios == pytest.approx(
        {
            "Umbilical Ratio (U/D)": 0.3,
            "Relative Whorl Height (Wh/D)": 0.4,
            "Relative Shell Thickness (Ww/D)": 0.2,
            "Whorl Shape (Ww/Wh)": 0.5,
        }
    )


def test_calculate_orthocone_measurements() -> None:
    ratios = calculate_orthocone_measurements(100.0, 20.0, 10.0, 37)

    assert ratios == pytest.approx(
        {
            "Expansion Angle": 5.72481045,
            "Taper Rate": 0.1,
            "Chambers per cm": 3.7,
        }
    )


def test_optional_positive_float() -> None:
    assert _optional_positive_float("") is None
    assert _optional_positive_float(" 2.5 ") == 2.5
    with pytest.raises(ValueError):
        _optional_positive_float("0")
