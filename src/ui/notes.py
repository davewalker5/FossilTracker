"""Notes tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from fossil_tracker.db import create_observation, get_specimen, list_specimens
from ui.common import (
    OBSERVATION_TYPE_OPTIONS,
    remember_default_specimen,
    remember_selected_specimen,
    render_specimen_observations,
    specimen_choice_index,
)


def observation_date_text(value: date | None) -> str:
    """Return an ISO date string for an optional observation date."""

    return value.isoformat() if value else ""


def show_observation_notes(db_path: Path) -> None:
    """Render observation note management for a specimen.

    :param db_path: SQLite database path.
    """

    specimens = list_specimens(db_path)
    if not specimens:
        st.info("Add a specimen before adding observation notes.")
        return

    choices = {f"{row['collection_code']} - {row['title']}": row["id"] for row in specimens}
    selected_label = st.selectbox(
        "Specimen",
        list(choices),
        index=specimen_choice_index(specimens),
        key="observation-specimen",
        on_change=remember_selected_specimen,
        args=("observation-specimen", choices),
    )
    remember_default_specimen(selected_label, choices)
    specimen = get_specimen(choices[selected_label], db_path)
    if specimen is None:
        st.warning("Selected specimen was not found.")
        return

    st.subheader("Notes")
    render_specimen_observations(specimen["id"], db_path, allow_delete=True)
    with st.form("add-observation", clear_on_submit=True):
        observation_meta = st.columns([1, 1, 1])
        observation_date = observation_meta[0].date_input(
            "Observation date",
            value=None,
            format="YYYY-MM-DD",
        )
        observation_type = observation_meta[1].selectbox(
            "Observation type", OBSERVATION_TYPE_OPTIONS
        )
        related_project = observation_meta[2].text_input("Related project")
        related_url = st.text_input("Related URL")
        public_visible = st.checkbox("Public")
        notes = st.text_area("Notes", height=180)
        add_observation = st.form_submit_button("Add observation")

    if add_observation:
        if not notes.strip():
            st.error("Observation notes are required.")
            return
        create_observation(
            {
                "specimen_id": specimen["id"],
                "observation_date": observation_date_text(observation_date),
                "observation_type": observation_type,
                "notes": notes,
                "related_project": related_project,
                "related_url": related_url,
                "public_visible": public_visible,
            },
            db_path,
        )
        st.success("Observation added.")
        st.rerun()
