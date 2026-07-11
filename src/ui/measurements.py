"""Measurement entry pages for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

import math
import sqlite3
from importlib.resources import files
from pathlib import Path

import streamlit as st

from fossil_tracker.db import (
    create_specimen_measurement,
    get_specimen,
    list_measurement_types,
    list_specimen_measurements,
    list_specimens,
    save_specimen_measurements,
)
from ui.common import (
    remember_default_specimen,
    remember_selected_specimen,
    render_specimen_measurements,
    specimen_choice_index,
)

AMMONITE_SOURCE_TYPES = (
    "Shell Diameter (D)",
    "Umbilical Diameter (U)",
    "Whorl Height (Wh)",
    "Whorl Width (Ww)",
)
AMMONITE_DERIVED_TYPES = (
    "Umbilical Ratio (U/D)",
    "Relative Whorl Height (Wh/D)",
    "Relative Shell Thickness (Ww/D)",
    "Whorl Shape (Ww/Wh)",
)
ORTHOCONE_SOURCE_TYPES = (
    "Shell Length (L)",
    "Maximum Diameter",
    "Minimum Diameter",
    "Number of Visible Chambers",
    "Average Chamber Spacing",
    "Siphuncle Position",
    "Siphuncle Diameter",
)
ORTHOCONE_DERIVED_TYPES = (
    "Expansion Angle",
    "Taper Rate",
    "Chambers per cm",
)
SIPHUNCLE_POSITIONS = ("Central", "Subcentral", "Ventral", "Dorsal", "Unknown")


def calculate_ammonite_measurements(
    diameter: float, umbilical: float, height: float, width: float
) -> dict[str, float]:
    """Calculate the four standard dimensionless ammonite ratios.

    :param diameter: Shell diameter in millimetres.
    :param umbilical: Umbilical diameter in millimetres.
    :param height: Whorl height in millimetres.
    :param width: Whorl width in millimetres.
    :return: Calculated values keyed by measurement type name.
    """

    # Keep the formulas together so the displayed and persisted values cannot diverge.
    return {
        "Umbilical Ratio (U/D)": umbilical / diameter,
        "Relative Whorl Height (Wh/D)": height / diameter,
        "Relative Shell Thickness (Ww/D)": width / diameter,
        "Whorl Shape (Ww/Wh)": width / height,
    }


def calculate_orthocone_measurements(
    length: float,
    maximum_diameter: float,
    minimum_diameter: float,
    visible_chambers: int,
) -> dict[str, float]:
    """Calculate standard derived orthocone measurements.

    :param length: Preserved shell length in millimetres.
    :param maximum_diameter: Largest external diameter in millimetres.
    :param minimum_diameter: Narrowest external diameter in millimetres.
    :param visible_chambers: Number of visible preserved chambers.
    :return: Expansion angle, taper rate, and chambers per centimetre.
    """

    # The brief defines a full apex angle, hence twice the arctangent result.
    expansion_angle = math.degrees(
        2 * math.atan((maximum_diameter - minimum_diameter) / (2 * length))
    )
    # Length is recorded in mm; multiplying chambers/mm by ten gives chambers/cm.
    return {
        "Expansion Angle": expansion_angle,
        "Taper Rate": (maximum_diameter - minimum_diameter) / length,
        "Chambers per cm": visible_chambers / (length / 10),
    }


def show_measurements(db_path: Path) -> None:
    """Render general, ammonite, and orthocone measurement entry tabs.

    :param db_path: SQLite database path.
    :return: None.
    """

    # A shared specimen selector keeps all three measurement tabs synchronized.
    specimens = list_specimens(db_path)
    if not specimens:
        st.info("Add a specimen before recording measurements.")
        return

    choices = {f"{row['collection_code']} - {row['title']}": row["id"] for row in specimens}
    selected_label = st.selectbox(
        "Specimen",
        list(choices),
        index=specimen_choice_index(specimens),
        key="measurements-specimen",
        on_change=remember_selected_specimen,
        args=("measurements-specimen", choices),
    )
    remember_default_specimen(selected_label, choices)
    specimen = get_specimen(choices[selected_label], db_path)
    if specimen is None:
        st.warning("Selected specimen was not found.")
        return

    # Specialist forms remain independent while sharing the selected specimen.
    standard_tab, ammonite_tab, orthocone_tab = st.tabs(
        ["Measurements", "Ammonite Measurements", "Orthocone Measurements"]
    )
    with standard_tab:
        _show_standard_measurements(specimen["id"], db_path)
    with ammonite_tab:
        _show_ammonite_measurements(specimen["id"], db_path)
    with orthocone_tab:
        _show_orthocone_measurements(specimen["id"], db_path)


def _show_standard_measurements(specimen_id: int, db_path: Path) -> None:
    """Render generic measurement listing and entry.

    :param specimen_id: Selected specimen primary key.
    :param db_path: SQLite database path.
    :return: None.
    """

    # Preserve the original free-choice measurement workflow in its own tab.
    st.subheader("Measurements")
    render_specimen_measurements(specimen_id, db_path, allow_delete=True)
    measurement_types = list_measurement_types(db_path)
    if not measurement_types:
        st.info("Add a measurement type in Reference Data before recording measurements.")
        return
    type_choices = {f"{row['name']} ({row['unit']})": row["id"] for row in measurement_types}
    with st.form("add-specimen-measurement", clear_on_submit=True):
        measurement_type_label = st.selectbox("Measurement type", list(type_choices))
        value = st.text_input("Value")
        submitted = st.form_submit_button("Add measurement")
    if not submitted:
        return
    if not value.strip():
        st.error("Measurement value is required.")
        return
    try:
        # Generic entry retains insert-only behavior to guard against accidental replacement.
        create_specimen_measurement(
            {
                "specimen_id": specimen_id,
                "measurement_type_id": type_choices[measurement_type_label],
                "value": value.strip(),
            },
            db_path,
        )
    except sqlite3.IntegrityError:
        st.error("This specimen already has that measurement type.")
        return
    st.success("Measurement added.")
    st.rerun()


def _show_ammonite_measurements(specimen_id: int, db_path: Path) -> None:
    """Render and save the ammonite-specific measurement form.

    :param specimen_id: Selected specimen primary key.
    :param db_path: SQLite database path.
    :return: None.
    """

    # Resolve ids by stable type names before constructing the save payload.
    type_ids = _required_measurement_type_ids(
        (*AMMONITE_SOURCE_TYPES, *AMMONITE_DERIVED_TYPES), "ammonite", db_path
    )
    if type_ids is None:
        return
    existing = _existing_measurement_values(specimen_id, db_path)

    st.subheader("Ammonite Measurements")
    # Read package bytes so the image also works from an installed wheel.
    schematic = files("fossil_tracker").joinpath("assets/images/ammonite-measurements.png")
    st.image(schematic.read_bytes(), caption="Ammonite measurement guide")
    with st.form(f"ammonite-measurements-{specimen_id}"):
        diameter = st.number_input(
            "Shell Diameter (D) in mm", min_value=0.0,
            value=_current_float(existing, AMMONITE_SOURCE_TYPES[0]),
        )
        umbilical = st.number_input(
            "Umbilical Diameter (U) in mm", min_value=0.0,
            value=_current_float(existing, AMMONITE_SOURCE_TYPES[1]),
        )
        height = st.number_input(
            "Whorl Height (Wh) in mm", min_value=0.0,
            value=_current_float(existing, AMMONITE_SOURCE_TYPES[2]),
        )
        width = st.number_input(
            "Whorl Width (Ww) in mm", min_value=0.0,
            value=_current_float(existing, AMMONITE_SOURCE_TYPES[3]),
        )
        submitted = st.form_submit_button("Save ammonite measurements")
    if not submitted:
        return
    if diameter <= 0 or height <= 0:
        st.error("Shell Diameter and Whorl Height must be greater than zero to calculate ratios.")
        return

    # Save source values and ratios in one transaction to keep them synchronized.
    source_values = dict(zip(AMMONITE_SOURCE_TYPES, (diameter, umbilical, height, width)))
    all_values = {
        **source_values,
        **calculate_ammonite_measurements(diameter, umbilical, height, width),
    }
    _save_named_measurements(specimen_id, type_ids, all_values, db_path)
    st.success("Ammonite measurements and calculated ratios saved.")
    st.rerun()


def _show_orthocone_measurements(specimen_id: int, db_path: Path) -> None:
    """Render and save the orthocone-specific measurement form.

    :param specimen_id: Selected specimen primary key.
    :param db_path: SQLite database path.
    :return: None.
    """

    # Ensure every source and calculated measurement can be persisted before entry.
    type_ids = _required_measurement_type_ids(
        (*ORTHOCONE_SOURCE_TYPES, *ORTHOCONE_DERIVED_TYPES), "orthocone", db_path
    )
    if type_ids is None:
        return
    existing = _existing_measurement_values(specimen_id, db_path)
    current_position = existing.get("Siphuncle Position", "Unknown")
    position_index = (
        SIPHUNCLE_POSITIONS.index(current_position)
        if current_position in SIPHUNCLE_POSITIONS
        else SIPHUNCLE_POSITIONS.index("Unknown")
    )

    st.subheader("Orthocone Measurements")
    # The guide is an application resource included in the distributable wheel.
    schematic = files("fossil_tracker").joinpath("assets/images/orthocone-measurements.png")
    st.image(schematic.read_bytes(), caption="Orthocone measurement guide")
    with st.form(f"orthocone-measurements-{specimen_id}"):
        length = st.number_input(
            "Shell Length (L) in mm", min_value=0.0,
            value=_current_float(existing, ORTHOCONE_SOURCE_TYPES[0]),
        )
        maximum_diameter = st.number_input(
            "Maximum Diameter in mm", min_value=0.0,
            value=_current_float(existing, ORTHOCONE_SOURCE_TYPES[1]),
        )
        minimum_diameter = st.number_input(
            "Minimum Diameter in mm", min_value=0.0,
            value=_current_float(existing, ORTHOCONE_SOURCE_TYPES[2]),
        )
        visible_chambers = st.number_input(
            "Number of Visible Chambers", min_value=0, step=1,
            value=_current_int(existing, ORTHOCONE_SOURCE_TYPES[3]),
        )
        chamber_spacing = st.number_input(
            "Average Chamber Spacing in mm", min_value=0.0,
            value=_current_float(existing, ORTHOCONE_SOURCE_TYPES[4]),
        )
        siphuncle_position = st.selectbox(
            "Siphuncle Position", SIPHUNCLE_POSITIONS, index=position_index
        )
        siphuncle_diameter_text = st.text_input(
            "Siphuncle Diameter in mm (optional)",
            value=existing.get("Siphuncle Diameter", ""),
        )
        submitted = st.form_submit_button("Save Orthocone Measurements")

    # Show calculated values from the current form state as an immediate reference.
    calculated = None
    if length > 0 and maximum_diameter >= minimum_diameter:
        calculated = calculate_orthocone_measurements(
            length, maximum_diameter, minimum_diameter, int(visible_chambers)
        )
        _show_orthocone_calculated_values(calculated)
    if not submitted:
        return
    if length <= 0:
        st.error("Shell Length must be greater than zero to calculate derived values.")
        return
    if maximum_diameter <= 0 or minimum_diameter <= 0:
        st.error("Maximum Diameter and Minimum Diameter must be greater than zero.")
        return
    if minimum_diameter > maximum_diameter:
        st.error("Minimum Diameter cannot be greater than Maximum Diameter.")
        return
    if visible_chambers <= 0 or chamber_spacing <= 0:
        st.error(
            "Number of Visible Chambers and Average Chamber Spacing must be greater than zero."
        )
        return
    try:
        # A blank optional field is represented as None so a prior value is removed.
        siphuncle_diameter = _optional_positive_float(siphuncle_diameter_text)
    except ValueError:
        st.error("Siphuncle Diameter must be a positive number or left blank.")
        return

    source_values: dict[str, float | int | str | None] = {
        "Shell Length (L)": length,
        "Maximum Diameter": maximum_diameter,
        "Minimum Diameter": minimum_diameter,
        "Number of Visible Chambers": int(visible_chambers),
        "Average Chamber Spacing": chamber_spacing,
        "Siphuncle Position": siphuncle_position,
        "Siphuncle Diameter": siphuncle_diameter,
    }
    all_values = {**source_values, **(calculated or {})}
    _save_named_measurements(specimen_id, type_ids, all_values, db_path)
    st.success("Orthocone measurements and calculated values saved.")
    st.rerun()


def _show_orthocone_calculated_values(values: dict[str, float]) -> None:
    """Display calculated orthocone values below the entry form.

    :param values: Calculated values keyed by measurement type name.
    :return: None.
    """

    # Metrics give the three derived values equal visual prominence.
    st.subheader("Calculated Values")
    angle_column, taper_column, chamber_column = st.columns(3)
    angle_column.metric("Expansion Angle", f"{values['Expansion Angle']:.1f}°")
    taper_column.metric("Taper Rate", f"{values['Taper Rate']:.3f} mm/mm")
    chamber_column.metric("Chambers per cm", f"{values['Chambers per cm']:.1f}")


def _required_measurement_type_ids(
    names: tuple[str, ...], group_name: str, db_path: Path
) -> dict[str, int] | None:
    """Resolve required measurement type ids and report missing definitions.

    :param names: Required measurement type names.
    :param group_name: Human-readable specialist measurement group.
    :param db_path: SQLite database path.
    :return: Type ids keyed by name, or None when definitions are missing.
    """

    # Name lookup decouples specialist forms from database-generated ids.
    all_type_ids = {row["name"]: row["id"] for row in list_measurement_types(db_path)}
    missing = [name for name in names if name not in all_type_ids]
    if missing:
        st.error(
            f"Required {group_name} measurement types are missing: " + ", ".join(missing)
        )
        return None
    return {name: all_type_ids[name] for name in names}


def _existing_measurement_values(specimen_id: int, db_path: Path) -> dict[str, str]:
    """Return existing specimen measurement values keyed by type name.

    :param specimen_id: Selected specimen primary key.
    :param db_path: SQLite database path.
    :return: Existing string values keyed by measurement name.
    """

    # A dictionary provides constant-time defaults for every specialist field.
    return {
        row["measurement_name"]: row["value"]
        for row in list_specimen_measurements(specimen_id, db_path)
    }


def _current_float(existing: dict[str, str], name: str) -> float:
    """Coerce a stored measurement into a safe numeric form default.

    :param existing: Existing values keyed by measurement name.
    :param name: Measurement name to retrieve.
    :return: Stored float value, or zero when missing or invalid.
    """

    # Invalid legacy data should not prevent the form from rendering.
    try:
        return float(existing.get(name, 0.0))
    except (TypeError, ValueError):
        return 0.0


def _current_int(existing: dict[str, str], name: str) -> int:
    """Coerce a stored measurement into a safe integer form default.

    :param existing: Existing values keyed by measurement name.
    :param name: Measurement name to retrieve.
    :return: Stored integer value, or zero when missing or invalid.
    """

    # Float coercion tolerates legacy strings such as ``"5.0"``.
    try:
        return int(float(existing.get(name, 0)))
    except (TypeError, ValueError):
        return 0


def _optional_positive_float(value: str) -> float | None:
    """Parse an optional positive decimal measurement.

    :param value: User-entered text.
    :return: Parsed float, or None when the input is blank.
    :raises ValueError: If the value is non-numeric or not positive.
    """

    # Blank input intentionally clears the optional stored measurement.
    if not value.strip():
        return None
    parsed = float(value)
    if parsed <= 0:
        raise ValueError("value must be positive")
    return parsed


def _save_named_measurements(
    specimen_id: int,
    type_ids: dict[str, int],
    values: dict[str, float | int | str | None],
    db_path: Path,
) -> None:
    """Format and atomically save measurements addressed by type name.

    :param specimen_id: Selected specimen primary key.
    :param type_ids: Measurement type ids keyed by name.
    :param values: Values keyed by measurement type name.
    :param db_path: SQLite database path.
    :return: None.
    """

    # Numeric formatting avoids persisting Python-specific float representations.
    formatted = {
        type_ids[name]: None if value is None else format(value, ".10g")
        if isinstance(value, float)
        else str(value)
        for name, value in values.items()
    }
    save_specimen_measurements(specimen_id, formatted, db_path)
