"""Documents tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from fossil_tracker.db import (
    create_acquisition_document,
    delete_acquisition_document,
    get_acquisition,
    get_specimen,
    list_acquisition_documents,
    list_document_types,
    list_specimens,
    update_acquisition_document,
)
from ui.common import (
    delete_managed_document_file,
    remember_default_specimen,
    remember_selected_specimen,
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
    documents = list_acquisition_documents(acquisition["id"], db_path)
    render_document_table(documents, db_path)

    editing_document_id = st.session_state.get("editing_document_id")
    selected_document = next(
        (document for document in documents if document["id"] == editing_document_id),
        None,
    )
    if editing_document_id and selected_document is None:
        st.session_state.pop("editing_document_id", None)

    form_suffix = selected_document["id"] if selected_document else "new"
    document_type_records = list_document_types(db_path)
    document_type_options = type_options(document_type_records)

    if selected_document:
        st.markdown("**Edit document details**")
    else:
        st.markdown("**Add document**")

    with st.form(
        f"acquisition-document-form-{form_suffix}",
        clear_on_submit=selected_document is None,
    ):
        uploaded = None
        if selected_document is None:
            uploaded = st.file_uploader("Upload document")
        document_meta = st.columns([1, 1])
        document_type = document_meta[0].selectbox(
            "Document type",
            document_type_options,
            index=type_option_index(
                document_type_options,
                selected_document["document_type_id"] if selected_document else None,
            ),
            format_func=lambda value: type_option_label(value, document_type_records),
            key=f"document-type-{form_suffix}",
        )
        title = document_meta[1].text_input(
            "Title",
            value=(selected_document["title"] or "") if selected_document else "",
            key=f"document-title-{form_suffix}",
        )
        document_notes = st.text_area(
            "Document notes",
            value=(selected_document["notes"] or "") if selected_document else "",
            key=f"document-notes-{form_suffix}",
        )
        action_col, cancel_col = st.columns([1, 1])
        save_document = action_col.form_submit_button(
            "Save document details" if selected_document else "Add document"
        )
        cancel_edit = cancel_col.form_submit_button(
            "Cancel editing", disabled=selected_document is None
        )

    if cancel_edit:
        st.session_state.pop("editing_document_id", None)
        st.rerun()

    if save_document:
        if selected_document:
            update_acquisition_document(
                selected_document["id"],
                {
                    "acquisition_id": acquisition["id"],
                    "document_path": selected_document["document_path"],
                    "document_type_id": document_type,
                    "title": title,
                    "notes": document_notes,
                },
                db_path,
            )
            st.session_state.pop("editing_document_id", None)
            st.success("Document details updated.")
            st.rerun()

        if uploaded is None:
            st.error("Upload a document.")
            return
        stored_path = save_uploaded_document(uploaded, specimen)
        create_acquisition_document(
            {
                "acquisition_id": acquisition["id"],
                "document_path": stored_path,
                "document_type_id": document_type,
                "title": title,
                "notes": document_notes,
            },
            db_path,
        )
        st.success("Document added.")
        st.rerun()


def render_document_table(documents: list[dict], db_path: Path) -> None:
    """Render acquisition documents as an editable table-like list."""

    if not documents:
        st.info("No documents recorded.")
        return

    header_cols = st.columns([3, 3, 2, 1, 1])
    header_cols[0].markdown("**Name**")
    header_cols[1].markdown("**Title**")
    header_cols[2].markdown("**Document type**")

    for document in documents:
        row_cols = st.columns([3, 3, 2, 1, 1])
        row_cols[0].write(Path(document["document_path"]).name)
        row_cols[1].write(document["title"] or "")
        row_cols[2].write(document["document_type"] or "")
        if row_cols[3].button(
            "Edit",
            icon=":material/edit:",
            key=f"edit-document-{document['id']}",
            help="Edit document details",
            width="stretch",
        ):
            st.session_state["editing_document_id"] = document["id"]
            st.rerun()
        if row_cols[4].button(
            "Delete",
            key=f"delete-document-{document['id']}",
            width="stretch",
        ):
            file_deleted = delete_managed_document_file(document["document_path"])
            delete_acquisition_document(document["id"], db_path)
            if st.session_state.get("editing_document_id") == document["id"]:
                st.session_state.pop("editing_document_id", None)
            if file_deleted:
                st.warning("Document record and uploaded file deleted.")
            else:
                st.warning("Document record deleted.")
            st.rerun()


def type_options(records: list[dict]) -> list[int | None]:
    """Return optional type ids for document type selectboxes."""

    return [None, *[row["id"] for row in records]]


def type_option_index(options: list[int | None], current_value: object) -> int:
    """Return the selectbox index for an optional reference id."""

    try:
        return options.index(int(current_value) if current_value else None)
    except ValueError:
        return 0


def type_option_label(value: int | None, records: list[dict]) -> str:
    """Render the optional document type placeholder."""

    if value is None:
        return "Not recorded"
    for record in records:
        if record["id"] == value:
            return record["name"]
    return "Not recorded"
