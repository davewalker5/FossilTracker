"""Search tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ui.common import *  # noqa: F403
from fossil_tracker.db import *  # noqa: F403

def show_register(db_path: Path) -> None:
    """Render the searchable specimen register.

    :param db_path: SQLite database path.
    """

    search = st.text_input("Search", placeholder="Please enter a search term")
    if not search.strip():
        st.info("Enter a search term to search specimens.")
        return

    specimens = list_specimens(db_path, search)
    st.metric("Specimens", len(specimens))

    if not specimens:
        st.info("No matching specimens yet.")
        return

    render_search_results(specimens, db_path)


