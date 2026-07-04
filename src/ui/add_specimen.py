"""Add Specimen tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from fossil_tracker.db import create_specimen
from ui.common import specimen_inputs


ADD_SPECIMEN_WIDGET_KEYS = [
    "new-collection-code",
    "new-title",
    "new-common-name",
    "new-taxon-id",
    "new-age-id",
    "new-locality-id",
    "new-storage",
    "new-preparation-type-id",
    "new-public-visible",
    "new-description",
]


def show_add_form(db_path: Path) -> None:
    """Render the add-specimen form.

    :param db_path: SQLite database path.
    """

    if st.session_state.pop("clear_add_specimen_form", False):
        for key in ADD_SPECIMEN_WIDGET_KEYS:
            st.session_state.pop(key, None)

    success_message = st.session_state.pop("add_specimen_success", None)
    if success_message:
        st.success(success_message)

    values = specimen_inputs("new", db_path=db_path)
    submitted = st.button("Add specimen")
    if submitted:
        if not values["collection_code"] or not values["title"]:
            st.error("Collection code and title are required.")
            return
        specimen_id = create_specimen(values, db_path)
        st.session_state["add_specimen_success"] = f"Added specimen #{specimen_id}."
        st.session_state["clear_add_specimen_form"] = True
        st.rerun()
