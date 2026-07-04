"""Edit Specimen tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from fossil_tracker.db import delete_specimen, get_specimen, list_specimens, update_specimen
from ui.common import (
    remember_default_specimen,
    remember_selected_specimen,
    specimen_choice_index,
    specimen_inputs,
)


def stay_on_edit_tab() -> None:
    """Keep the main navigation on Edit Specimen after form submission."""

    st.session_state["pending_main_tab"] = "Edit specimen"


def show_edit_form(db_path: Path) -> None:
    """Render the edit/delete specimen form.

    :param db_path: SQLite database path.
    """

    specimens = list_specimens(db_path)
    if not specimens:
        st.info("Add a specimen before editing.")
        return

    choices = {f"{row['collection_code']} - {row['title']}": row["id"] for row in specimens}
    selected_label = st.selectbox(
        "Specimen",
        list(choices),
        index=specimen_choice_index(specimens),
        key="edit-specimen-select",
        on_change=remember_selected_specimen,
        args=("edit-specimen-select", choices),
    )
    remember_default_specimen(selected_label, choices)
    specimen = get_specimen(choices[selected_label], db_path)
    if specimen is None:
        st.warning("Selected specimen was not found.")
        return

    values = specimen_inputs("edit", specimen, db_path)
    left, right = st.columns([1, 1])
    save = left.button("Save changes", width="stretch", on_click=stay_on_edit_tab)
    remove = right.button("Delete specimen", width="stretch", on_click=stay_on_edit_tab)

    if save:
        if not values["collection_code"] or not values["title"]:
            st.error("Collection code and title are required.")
            return
        update_specimen(specimen["id"], values, db_path)
        st.success("Specimen updated.")

    if remove:
        delete_specimen(specimen["id"], db_path)
        st.warning("Specimen deleted.")
