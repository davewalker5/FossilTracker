"""Measurement entry pages for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

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


def calculate_ammonite_measurements(diameter: float, umbilical: float, height: float, width: float) -> dict[str, float]:
    """Calculate the four standard dimensionless ammonite ratios."""

    return {
        "Umbilical Ratio (U/D)": umbilical / diameter,
        "Relative Whorl Height (Wh/D)": height / diameter,
        "Relative Shell Thickness (Ww/D)": width / diameter,
        "Whorl Shape (Ww/Wh)": width / height,
    }


def show_measurements(db_path: Path) -> None:
    """Render general and ammonite measurement entry as sub-tabs."""

    specimens = list_specimens(db_path)
    if not specimens:
        st.info("Add a specimen before recording measurements.")
        return

    choices = {f"{row['collection_code']} - {row['title']}": row["id"] for row in specimens}
    selected_label = st.selectbox(
        "Specimen", list(choices), index=specimen_choice_index(specimens),
        key="measurements-specimen", on_change=remember_selected_specimen,
        args=("measurements-specimen", choices),
    )
    remember_default_specimen(selected_label, choices)
    specimen = get_specimen(choices[selected_label], db_path)
    if specimen is None:
        st.warning("Selected specimen was not found.")
        return

    standard_tab, ammonite_tab = st.tabs(["Measurements", "Ammonite Measurements"])
    with standard_tab:
        _show_standard_measurements(specimen["id"], db_path)
    with ammonite_tab:
        _show_ammonite_measurements(specimen["id"], db_path)


def _show_standard_measurements(specimen_id: int, db_path: Path) -> None:
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
        create_specimen_measurement({"specimen_id": specimen_id, "measurement_type_id": type_choices[measurement_type_label], "value": value.strip()}, db_path)
    except sqlite3.IntegrityError:
        st.error("This specimen already has that measurement type.")
        return
    st.success("Measurement added.")
    st.rerun()


def _show_ammonite_measurements(specimen_id: int, db_path: Path) -> None:
    type_ids = {row["name"]: row["id"] for row in list_measurement_types(db_path)}
    required = (*AMMONITE_SOURCE_TYPES, *AMMONITE_DERIVED_TYPES)
    missing = [name for name in required if name not in type_ids]
    if missing:
        st.error("Required ammonite measurement types are missing: " + ", ".join(missing))
        return
    existing = {row["measurement_name"]: row["value"] for row in list_specimen_measurements(specimen_id, db_path)}

    def current(name: str) -> float:
        try:
            return float(existing.get(name, 0.0))
        except (TypeError, ValueError):
            return 0.0

    st.subheader("Ammonite Measurements")
    schematic = files("fossil_tracker").joinpath(
        "assets/images/ammonite-measurements.png"
    )
    st.image(schematic.read_bytes(), caption="Ammonite measurement guide")
    with st.form(f"ammonite-measurements-{specimen_id}"):
        diameter = st.number_input("Shell Diameter (D) in mm", min_value=0.0, value=current(AMMONITE_SOURCE_TYPES[0]))
        umbilical = st.number_input("Umbilical Diameter (U) in mm", min_value=0.0, value=current(AMMONITE_SOURCE_TYPES[1]))
        height = st.number_input("Whorl Height (Wh) in mm", min_value=0.0, value=current(AMMONITE_SOURCE_TYPES[2]))
        width = st.number_input("Whorl Width (Ww) in mm", min_value=0.0, value=current(AMMONITE_SOURCE_TYPES[3]))
        submitted = st.form_submit_button("Save ammonite measurements")
    if not submitted:
        return
    if diameter <= 0 or height <= 0:
        st.error("Shell Diameter and Whorl Height must be greater than zero to calculate ratios.")
        return
    source_values = dict(zip(AMMONITE_SOURCE_TYPES, (diameter, umbilical, height, width)))
    all_values = {**source_values, **calculate_ammonite_measurements(diameter, umbilical, height, width)}
    save_specimen_measurements(specimen_id, {type_ids[name]: format(value, ".10g") for name, value in all_values.items()}, db_path)
    st.success("Ammonite measurements and calculated ratios saved.")
    st.rerun()
