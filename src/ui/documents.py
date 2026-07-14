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


def document_notes_preview(value: object, limit: int = 50) -> str:
    """Return a shortened document-notes preview for table display."""

    text = str(value or "")
    return text if len(text) <= limit else f"{text[:limit]}..."


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
    editing_document_id = st.session_state.get("editing_document_id")
    if not any(document["id"] == editing_document_id for document in documents):
        st.session_state.pop("editing_document_id", None)
        editing_document_id = None
    new_editing_document_id = render_document_table(
        documents, db_path, acquisition["id"], editing_document_id
    )
    if new_editing_document_id != editing_document_id:
        st.session_state["editing_document_id"] = new_editing_document_id
        st.session_state.pop("pending_document_delete", None)
        st.rerun()
    selected_document = next(
        (document for document in documents if document["id"] == editing_document_id),
        None,
    )

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
        save_col, clear_col = st.columns(2)
        save_document = save_col.form_submit_button("Save", width="stretch")
        clear_document = clear_col.form_submit_button("Clear", width="stretch")

    if clear_document:
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


def render_document_table(
    documents: list[dict],
    db_path: Path,
    acquisition_id: int,
    selected_id: int | None,
) -> int | None:
    """Render acquisition documents as a selectable table with row deletion."""

    if not documents:
        st.info("No documents recorded.")
        return None

    rows = [
        {
            "Edit": document["id"] == selected_id,
            "Name": Path(document["document_path"]).name,
            "Title": document["title"] or "",
            "Document type": document["document_type"] or "",
            "Notes": document_notes_preview(document["notes"]),
            "Delete": ":material/delete:",
        }
        for document in documents
    ]
    delete_click_key = f"document-delete-click-{acquisition_id}"

    def queue_document_delete() -> None:
        """Queue the document selected through the table's trash icon."""

        click = st.session_state.get(delete_click_key)
        if click is not None and 0 <= click["row"] < len(documents):
            st.session_state["pending_document_delete"] = documents[click["row"]]["id"]

    edited_rows = st.data_editor(
        rows,
        width="stretch",
        hide_index=True,
        disabled=["Name", "Title", "Document type", "Notes"],
        column_config={
            "Edit": st.column_config.CheckboxColumn(
                "", width=48, pinned=True, alignment="center"
            ),
            "Name": st.column_config.TextColumn("Name", width=180),
            "Title": st.column_config.TextColumn("Title", width=180),
            "Document type": st.column_config.TextColumn(
                "Document type", width=150
            ),
            "Notes": st.column_config.TextColumn("Notes", width=300),
            "Delete": st.column_config.ButtonColumn(
                "",
                width=48,
                alignment="center",
                type="tertiary",
                on_click=queue_document_delete,
                key=delete_click_key,
            ),
        },
        column_order=[
            "Edit",
            "Name",
            "Title",
            "Document type",
            "Notes",
            "Delete",
        ],
        key=f"documents-table-{acquisition_id}-{selected_id or 'new'}",
    )
    checked_ids = [
        document["id"]
        for document, row in zip(documents, edited_rows)
        if row["Edit"]
    ]
    newly_checked = [
        document_id for document_id in checked_ids if document_id != selected_id
    ]
    new_selected_id = (
        newly_checked[-1]
        if newly_checked
        else selected_id if selected_id in checked_ids else None
    )

    pending_id = st.session_state.get("pending_document_delete")
    pending_document = next(
        (document for document in documents if document["id"] == pending_id), None
    )
    if pending_id is not None and pending_document is None:
        st.session_state.pop("pending_document_delete", None)
    if pending_document:
        st.warning(f"Delete {Path(pending_document['document_path']).name}?")
        confirm_col, cancel_col = st.columns(2)
        if confirm_col.button(
            "Confirm delete", key=f"confirm-document-{pending_id}", width="stretch"
        ):
            file_deleted = delete_managed_document_file(
                pending_document["document_path"]
            )
            delete_acquisition_document(pending_id, db_path)
            st.session_state.pop("pending_document_delete", None)
            if st.session_state.get("editing_document_id") == pending_id:
                st.session_state.pop("editing_document_id", None)
            if file_deleted:
                st.warning("Document record and uploaded file deleted.")
            else:
                st.warning("Document record deleted.")
            st.rerun()
        if cancel_col.button(
            "Cancel", key=f"cancel-document-{pending_id}", width="stretch"
        ):
            st.session_state.pop("pending_document_delete", None)
            st.rerun()

    return new_selected_id


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
