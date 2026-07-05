"""Related Links tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from fossil_tracker.db import (
    create_related_link,
    delete_related_link,
    get_specimen,
    list_related_links,
    list_specimens,
    update_related_link,
)
from ui.common import (
    remember_default_specimen,
    remember_selected_specimen,
    specimen_choice_index,
    validate_related_link_url,
)


def show_related_links(db_path: Path) -> None:
    """Render Field Notes link management for a specimen.

    :param db_path: SQLite database path.
    """

    specimens = list_specimens(db_path)
    if not specimens:
        st.info("Add a specimen before attaching related links.")
        return

    choices = {f"{row['collection_code']} - {row['title']}": row["id"] for row in specimens}
    selected_label = st.selectbox(
        "Specimen",
        list(choices),
        index=specimen_choice_index(specimens),
        key="related-links-specimen",
        on_change=remember_selected_specimen,
        args=("related-links-specimen", choices),
    )
    remember_default_specimen(selected_label, choices)
    specimen = get_specimen(choices[selected_label], db_path)
    if specimen is None:
        st.warning("Selected specimen was not found.")
        return

    st.subheader("Related links")
    links = list_related_links(specimen["id"], db_path)
    render_related_link_table(links, db_path)

    editing_id = st.session_state.get("editing_related_link_id")
    selected_link = next((link for link in links if link["id"] == editing_id), None)
    if editing_id is not None and selected_link is None:
        st.session_state.pop("editing_related_link_id", None)
        editing_id = None

    with st.form(
        f"related-link-form-{editing_id or 'new'}",
        clear_on_submit=editing_id is None,
    ):
        title = st.text_input(
            "Title",
            value=(selected_link["title"] or "") if selected_link else "",
            key=f"related-link-title-{editing_id or 'new'}",
        )
        url = st.text_input(
            "URL",
            value=(selected_link["url"] or "") if selected_link else "",
            key=f"related-link-url-{editing_id or 'new'}",
        )
        description = st.text_area(
            "Description",
            value=(selected_link["description"] or "") if selected_link else "",
            key=f"related-link-description-{editing_id or 'new'}",
        )
        save_link = st.form_submit_button("Save link")

    if save_link:
        cleaned_url = url.strip()
        error = validate_related_link_url(cleaned_url)
        if error:
            st.error(error)
            return
        values = {
            "specimen_id": specimen["id"],
            "url": cleaned_url,
            "title": title.strip(),
            "description": description.strip(),
        }
        if selected_link is None:
            create_related_link(values, db_path)
            st.success("Link added.")
        else:
            update_related_link(selected_link["id"], values, db_path)
            st.session_state.pop("editing_related_link_id", None)
            st.success("Link updated.")
        st.rerun()


def render_related_link_table(links: list[dict], db_path: Path) -> None:
    """Render related links as an editable table-like list.

    :param links: Related link rows for the selected specimen.
    :param db_path: SQLite database path.
    """

    if not links:
        st.info("No related links recorded for this specimen.")
        return

    header_cols = st.columns([3, 2, 4, 1, 1])
    header_cols[0].markdown("**Link**")
    header_cols[1].markdown("**Title**")
    header_cols[2].markdown("**Description**")

    for link in links:
        row_cols = st.columns([3, 2, 4, 1, 1])
        row_cols[0].markdown(f"[{link['url']}]({link['url']})")
        row_cols[1].write(link["title"] or "")
        row_cols[2].write(link["description"] or "")
        if row_cols[3].button(
            "Edit",
            icon=":material/edit:",
            key=f"edit-related-link-{link['id']}",
            help="Edit link",
            width="stretch",
        ):
            st.session_state["editing_related_link_id"] = link["id"]
            st.session_state.pop("pending_related_link_delete", None)
            st.rerun()
        if row_cols[4].button(
            "Delete",
            key=f"delete-related-link-{link['id']}",
            width="stretch",
        ):
            st.session_state["pending_related_link_delete"] = link["id"]
            st.rerun()

        if st.session_state.get("pending_related_link_delete") == link["id"]:
            confirm_col, cancel_col = st.columns([1, 1])
            if confirm_col.button(
                "Confirm delete",
                key=f"confirm-related-link-{link['id']}",
                width="stretch",
            ):
                delete_related_link(link["id"], db_path)
                st.session_state.pop("pending_related_link_delete", None)
                if st.session_state.get("editing_related_link_id") == link["id"]:
                    st.session_state.pop("editing_related_link_id", None)
                st.warning("Link deleted.")
                st.rerun()
            if cancel_col.button(
                "Cancel",
                key=f"cancel-related-link-{link['id']}",
                width="stretch",
            ):
                st.session_state.pop("pending_related_link_delete", None)
                st.rerun()
