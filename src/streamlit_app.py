"""Streamlit entrypoint for Fossil Tracker."""

from __future__ import annotations

import streamlit as st

from fossil_tracker.config import APP_NAME, database_path
from fossil_tracker.db import apply_migrations, seed_specimens
from ui.add_specimen import show_add_form
from ui.documents import show_acquisition_documents
from ui.edit_specimen import show_edit_form
from ui.images import show_images_and_notes
from ui.measurements import show_measurements
from ui.notes import show_observation_notes
from ui.provenance import show_provenance_manager
from ui.reference_data import show_context_manager
from ui.related_links import show_related_links
from ui.search import show_register


def main() -> None:
    """Run the Streamlit application."""

    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.title(APP_NAME)
    st.caption("Personal fossil collection register")

    db_path = database_path()
    try:
        apply_migrations(db_path)
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    with st.sidebar:
        st.subheader("Database")
        st.code(str(db_path), language=None)
        if st.button("Add starter records", width="stretch"):
            added = seed_specimens(db_path)
            st.success(f"Added {added} starter record{'s' if added != 1 else ''}.")

    pending_main_tab = st.session_state.pop("pending_main_tab", None)
    if pending_main_tab is not None:
        st.session_state["main_tabs"] = pending_main_tab

    (
        tab_register,
        tab_add,
        tab_edit,
        tab_provenance,
        tab_documents,
        tab_images,
        tab_observations,
        tab_measurements,
        tab_links,
        tab_context,
    ) = st.tabs(
        [
            "Search",
            "Add specimen",
            "Edit specimen",
            "Provenance",
            "Documents",
            "Images",
            "Notes",
            "Measurements",
            "Related links",
            "Reference Data",
        ],
        key="main_tabs",
        on_change="rerun",
        default=pending_main_tab,
    )

    with tab_register:
        show_register(db_path)

    with tab_add:
        show_add_form(db_path)

    with tab_edit:
        show_edit_form(db_path)

    with tab_context:
        show_context_manager(db_path)

    with tab_provenance:
        show_provenance_manager(db_path)

    with tab_documents:
        show_acquisition_documents(db_path)

    with tab_images:
        show_images_and_notes(db_path)

    with tab_observations:
        show_observation_notes(db_path)

    with tab_measurements:
        show_measurements(db_path)

    with tab_links:
        show_related_links(db_path)


if __name__ == "__main__":
    main()
