"""Streamlit entrypoint for Fossil Tracker."""

from __future__ import annotations

import streamlit as st

from fossil_tracker import __version__
from fossil_tracker.config import APP_NAME, database_path
from fossil_tracker.db import apply_migrations, get_specimen, list_specimens
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
from ui.taxonomy import show_taxonomy_manager


SPECIMEN_REQUIRED_TABS = {
    "Edit specimen",
    "Taxonomy",
    "Provenance",
    "Documents",
    "Images",
    "Notes",
    "Measurements",
    "Related links",
}


def selected_specimen_exists(db_path) -> bool:
    """Return whether the current session specimen id points to an existing specimen."""

    current_id = st.session_state.get("current_specimen_id")
    if current_id in {None, ""}:
        return False
    try:
        specimen_id = int(current_id)
    except (TypeError, ValueError):
        st.session_state.pop("current_specimen_id", None)
        return False

    if get_specimen(specimen_id, db_path) is not None:
        return True

    st.session_state.pop("current_specimen_id", None)
    return False


def show_specimen_required_fallback(db_path) -> None:
    """Render useful content when a specimen-specific tab is opened too early."""

    st.info("Select or add a specimen before using this tab.")
    if list_specimens(db_path):
        show_register(db_path)
    else:
        show_add_form(db_path)


def main() -> None:
    """Run the Streamlit application."""

    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.title(f"{APP_NAME} v{__version__}")
    st.caption("Personal fossil collection register")

    db_path = database_path()
    st.caption(f"Database: {db_path}")
    try:
        apply_migrations(db_path)
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    main_tab_labels = [
        "Search",
        "Add specimen",
        "Edit specimen",
        "Taxonomy",
        "Provenance",
        "Documents",
        "Images",
        "Notes",
        "Measurements",
        "Related links",
        "Reference Data",
    ]

    pending_main_tab = st.session_state.pop("pending_main_tab", None)
    if pending_main_tab in main_tab_labels:
        st.session_state["main_tabs"] = pending_main_tab

    selected_specimen_available = selected_specimen_exists(db_path)

    (
        tab_register,
        tab_add,
        tab_edit,
        tab_taxonomy,
        tab_provenance,
        tab_documents,
        tab_images,
        tab_observations,
        tab_measurements,
        tab_links,
        tab_context,
    ) = st.tabs(
        main_tab_labels,
        key="main_tabs",
        on_change="rerun",
    )

    if tab_register.open:
        with tab_register:
            show_register(db_path)

    if tab_add.open:
        with tab_add:
            show_add_form(db_path)

    if tab_edit.open:
        with tab_edit:
            if selected_specimen_available:
                show_edit_form(db_path)
            else:
                show_specimen_required_fallback(db_path)

    if tab_taxonomy.open:
        with tab_taxonomy:
            if selected_specimen_available:
                show_taxonomy_manager(db_path)
            else:
                show_specimen_required_fallback(db_path)

    if tab_context.open:
        with tab_context:
            show_context_manager(db_path)

    if tab_provenance.open:
        with tab_provenance:
            if selected_specimen_available:
                show_provenance_manager(db_path)
            else:
                show_specimen_required_fallback(db_path)

    if tab_documents.open:
        with tab_documents:
            if selected_specimen_available:
                show_acquisition_documents(db_path)
            else:
                show_specimen_required_fallback(db_path)

    if tab_images.open:
        with tab_images:
            if selected_specimen_available:
                show_images_and_notes(db_path)
            else:
                show_specimen_required_fallback(db_path)

    if tab_observations.open:
        with tab_observations:
            if selected_specimen_available:
                show_observation_notes(db_path)
            else:
                show_specimen_required_fallback(db_path)

    if tab_measurements.open:
        with tab_measurements:
            if selected_specimen_available:
                show_measurements(db_path)
            else:
                show_specimen_required_fallback(db_path)

    if tab_links.open:
        with tab_links:
            if selected_specimen_available:
                show_related_links(db_path)
            else:
                show_specimen_required_fallback(db_path)


if __name__ == "__main__":
    main()
