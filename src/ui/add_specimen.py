"""Add Specimen tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ui.common import *  # noqa: F403
from fossil_tracker.db import *  # noqa: F403

def show_add_form(db_path: Path) -> None:
    """Render the add-specimen form.

    :param db_path: SQLite database path.
    """

    with st.form("add-specimen", clear_on_submit=True):
        values = specimen_inputs("new", db_path=db_path)
        submitted = st.form_submit_button("Add specimen")
    if submitted:
        if not values["collection_code"] or not values["title"]:
            st.error("Collection code and title are required.")
            return
        specimen_id = create_specimen(values, db_path)
        st.success(f"Added specimen #{specimen_id}.")


