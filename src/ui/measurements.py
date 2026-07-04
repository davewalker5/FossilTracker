"""Measurements tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import sqlite3

import streamlit as st

from fossil_tracker.db import (
    create_specimen_measurement,
    get_specimen,
    list_measurement_types,
    list_specimens,
)
from ui.common import (
    remember_default_specimen,
    remember_selected_specimen,
    render_specimen_measurements,
    specimen_choice_index,
)


def show_measurements(db_path: Path) -> None:
    """Render standard measurement management for a specimen.

    :param db_path: SQLite database path.
    """

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

    st.subheader("Measurements")
    render_specimen_measurements(specimen["id"], db_path, allow_delete=True)

    measurement_types = list_measurement_types(db_path)
    if not measurement_types:
        st.info("Add a measurement type in Context before recording measurements.")
        return

    type_choices = {f"{row['name']} ({row['unit']})": row["id"] for row in measurement_types}
    with st.form("add-specimen-measurement", clear_on_submit=True):
        measurement_type_label = st.selectbox("Measurement type", list(type_choices))
        value = st.text_input("Value")
        add_measurement = st.form_submit_button("Add measurement")

    if add_measurement:
        cleaned_value = value.strip()
        if not cleaned_value:
            st.error("Measurement value is required.")
            return
        try:
            create_specimen_measurement(
                {
                    "specimen_id": specimen["id"],
                    "measurement_type_id": type_choices[measurement_type_label],
                    "value": cleaned_value,
                },
                db_path,
            )
        except sqlite3.IntegrityError:
            st.error("This specimen already has that measurement type.")
            return
        st.success("Measurement added.")
        st.rerun()

