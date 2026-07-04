"""Documents tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from fossil_tracker.db import create_acquisition_document, get_acquisition, get_specimen, list_specimens
from ui.common import (
    remember_default_specimen,
    remember_selected_specimen,
    render_acquisition_documents,
    save_uploaded_document,
    specimen_choice_index,
)


def show_acquisition_documents(db_path: Path) -> None:
    """Render acquisition document management for a specimen.

    :param db_path: SQLite database path.
    """

    specimens = list_specimens(db_path)
    if not specimens:
        st.info("Add a specimen before attaching documents.")
        return

    specimen_choices = {
        f"{row['collection_code']} - {row['title']}": row["id"] for row in specimens
    }
    selected_specimen_label = st.selectbox(
        "Specimen",
        list(specimen_choices),
        index=specimen_choice_index(specimens),
        key="acquisition-documents-specimen",
        on_change=remember_selected_specimen,
        args=("acquisition-documents-specimen", specimen_choices),
    )
    remember_default_specimen(selected_specimen_label, specimen_choices)
    specimen = get_specimen(specimen_choices[selected_specimen_label], db_path)
    if specimen is None:
        st.warning("Selected specimen was not found.")
        return

    acquisition = get_acquisition(specimen["acquisition_id"], db_path)
    if acquisition is None:
        st.info("No acquisition is linked to this specimen. Link one from Edit specimen.")
        return

    st.subheader("Documents")
    render_acquisition_documents(acquisition["id"], db_path)
    with st.form("add-acquisition-document", clear_on_submit=True):
        uploaded = st.file_uploader("Upload document")
        document_path = st.text_input("Document path")
        document_meta = st.columns([1, 1])
        document_type = document_meta[0].text_input("Document type")
        title = document_meta[1].text_input("Title")
        document_notes = st.text_area("Document notes")
        add_document = st.form_submit_button("Add document")

    if add_document:
        stored_path = document_path.strip()
        if uploaded is not None:
            stored_path = save_uploaded_document(uploaded, specimen)
        if not stored_path:
            st.error("Upload a document or enter a document path.")
            return
        create_acquisition_document(
            {
                "acquisition_id": acquisition["id"],
                "document_path": stored_path,
                "document_type": document_type,
                "title": title,
                "notes": document_notes,
            },
            db_path,
        )
        st.success("Document added.")
        st.rerun()

