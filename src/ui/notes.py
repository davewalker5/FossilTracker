"""Notes tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from fossil_tracker.db import (
    create_observation,
    get_specimen,
    list_observations,
    list_specimens,
    update_observation,
)
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


def parse_observation_date(value: object) -> date | None:
    """Parse an observation date stored as YYYY-MM-DD text."""

    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


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
    observations = list_observations(specimen["id"], db_path)
    editing_observation_id = st.session_state.get("editing_observation_id")
    selected_observation = next(
        (
            observation
            for observation in observations
            if observation["id"] == editing_observation_id
        ),
        None,
    )
    if editing_observation_id and selected_observation is None:
        st.session_state.pop("editing_observation_id", None)

    form_suffix = selected_observation["id"] if selected_observation else "new"
    stored_date = selected_observation["observation_date"] if selected_observation else ""
    date_value = parse_observation_date(stored_date)
    stored_type = selected_observation["observation_type"] if selected_observation else ""
    note_type_options = list(OBSERVATION_TYPE_OPTIONS)
    if stored_type and stored_type not in note_type_options:
        note_type_options.append(stored_type)

    with st.form(
        f"observation-form-{form_suffix}",
        clear_on_submit=selected_observation is None,
    ):
        observation_meta = st.columns([1, 1])
        observation_date = observation_meta[0].date_input(
            "Date",
            value=date_value,
            format="YYYY-MM-DD",
            key=f"observation-date-{form_suffix}",
        )
        if stored_date and date_value is None:
            observation_meta[0].warning(
                "Existing date is not in YYYY-MM-DD format. Pick a date to replace it."
            )
        observation_type = observation_meta[1].selectbox(
            "Note type",
            note_type_options,
            index=note_type_options.index(stored_type or ""),
            key=f"observation-type-{form_suffix}",
        )
        notes = st.text_area(
            "Notes",
            value=(selected_observation["notes"] or "") if selected_observation else "",
            height=180,
            key=f"observation-notes-{form_suffix}",
        )
        action_col, clear_col = st.columns(2)
        save_observation = action_col.form_submit_button(
            "Save" if selected_observation else "Add", width="stretch"
        )
        clear_observation = clear_col.form_submit_button("Clear", width="stretch")

    if clear_observation:
        st.session_state.pop("editing_observation_id", None)
        st.rerun()

    if save_observation:
        if not notes.strip():
            st.error("Observation notes are required.")
            return
        date_text = (
            observation_date_text(observation_date)
            if observation_date
            else str(stored_date or "")
            if stored_date and date_value is None
            else ""
        )
        values = {
            "specimen_id": specimen["id"],
            "observation_date": date_text,
            "observation_type": observation_type,
            "notes": notes,
        }
        if selected_observation:
            update_observation(selected_observation["id"], values, db_path)
            st.session_state.pop("editing_observation_id", None)
            st.success("Observation updated.")
        else:
            create_observation(values, db_path)
            st.success("Observation added.")
        st.rerun()
