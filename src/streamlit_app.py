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


def apply_compact_header_style() -> None:
    """Reduce the Streamlit toolbar height while retaining its controls."""

    st.markdown(
        """
        <style>
            header[data-testid="stHeader"] {
                height: 2.75rem;
                min-height: 2.75rem;
            }

            div[data-testid="stToolbar"] {
                height: 2.75rem;
            }

            div[data-testid="stMainBlockContainer"] {
                padding-top: 3.5rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def specimen_strapline(specimen: dict | None) -> str:
    """Return the collection strapline for the current specimen."""

    strapline = "Personal fossil collection register"
    if specimen is None:
        return strapline
    label = " - ".join(
        part for part in [specimen["collection_code"], specimen["title"]] if part
    )
    return f"{strapline}: {label}" if label else strapline


def handle_main_tab_change() -> None:
    """Clear the current specimen whenever the user enters Browse."""

    if st.session_state.get("main_tabs") == "Browse":
        st.session_state.pop("current_specimen_id", None)


def apply_specimen_tab_style(specimen_selected: bool) -> None:
    """Visually disable specimen-only tabs until a specimen is selected."""

    if specimen_selected:
        return
    st.markdown(
        """
        <style>
            .st-key-main_tabs [role="tablist"] > [role="tab"]:nth-child(n+3):nth-child(-n+10) {
                color: var(--text-color);
                cursor: not-allowed;
                filter: grayscale(1);
                opacity: 0.35;
                pointer-events: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
    apply_compact_header_style()
    st.title(f"{APP_NAME} v{__version__}")

    db_path = database_path()
    try:
        apply_migrations(db_path)
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    selected_specimen_available = selected_specimen_exists(db_path)
    current_specimen = (
        get_specimen(int(st.session_state["current_specimen_id"]), db_path)
        if selected_specimen_available
        else None
    )
    st.caption(specimen_strapline(current_specimen))
    st.caption(f"Database: {db_path}")

    main_tab_labels = [
        "Browse",
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
    unrestricted_tabs = {"Browse", "Add specimen", "Reference Data"}
    if (
        not selected_specimen_available
        and st.session_state.get("main_tabs", "Browse") not in unrestricted_tabs
    ):
        st.session_state["main_tabs"] = "Browse"

    apply_specimen_tab_style(selected_specimen_available)

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
        on_change=handle_main_tab_change,
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
