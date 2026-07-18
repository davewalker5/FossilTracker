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
    is_read_only,
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
    editing_id = st.session_state.get("editing_related_link_id")
    if not any(link["id"] == editing_id for link in links):
        st.session_state.pop("editing_related_link_id", None)
        editing_id = None
    new_editing_id = render_related_link_table(
        links, db_path, specimen["id"], editing_id
    )
    if new_editing_id != editing_id:
        st.session_state["editing_related_link_id"] = new_editing_id
        st.session_state.pop("pending_related_link_delete", None)
        st.rerun()
    selected_link = next((link for link in links if link["id"] == editing_id), None)

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
        save_col, clear_col = st.columns(2)
        save_link = save_col.form_submit_button("Save", disabled=is_read_only(), width="stretch")
        clear_link = clear_col.form_submit_button("Clear", width="stretch")

    if clear_link:
        st.session_state.pop("editing_related_link_id", None)
        st.rerun()

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


def render_related_link_table(
    links: list[dict],
    db_path: Path,
    specimen_id: int,
    selected_id: int | None,
) -> int | None:
    """Render related links as a selectable table with row deletion.

    :param links: Related link rows for the selected specimen.
    :param db_path: SQLite database path.
    """

    if not links:
        st.info("No related links recorded for this specimen.")
        return None

    rows = [
        {
            "Edit": link["id"] == selected_id,
            "Link": link["url"],
            "Title": link["title"] or "",
            "Description": link["description"] or "",
            "Delete": ":material/delete:",
        }
        for link in links
    ]
    delete_click_key = f"related-link-delete-click-{specimen_id}"

    def queue_link_delete() -> None:
        """Queue the link selected through the table's trash icon."""

        click = st.session_state.get(delete_click_key)
        if click is not None and 0 <= click["row"] < len(links):
            st.session_state["pending_related_link_delete"] = links[click["row"]]["id"]

    edited_rows = st.data_editor(
        rows,
        width="stretch",
        hide_index=True,
        disabled=["Link", "Title", "Description"],
        column_config={
            "Edit": st.column_config.CheckboxColumn(
                "", width=48, pinned=True, alignment="center"
            ),
            "Link": st.column_config.LinkColumn("Link", width="large"),
            "Title": st.column_config.TextColumn("Title", width="medium"),
            "Description": st.column_config.TextColumn("Description", width="large"),
            "Delete": st.column_config.ButtonColumn(
                "",
                width=48,
                alignment="center",
                type="tertiary",
                on_click=queue_link_delete,
                key=delete_click_key,
            ),
        },
        column_order=["Edit", "Link", "Title", "Description", "Delete"],
        key=f"related-links-table-{specimen_id}-{selected_id or 'new'}",
    )
    checked_ids = [
        link["id"] for link, row in zip(links, edited_rows) if row["Edit"]
    ]
    newly_checked = [link_id for link_id in checked_ids if link_id != selected_id]
    new_selected_id = (
        newly_checked[-1]
        if newly_checked
        else selected_id if selected_id in checked_ids else None
    )

    pending_id = st.session_state.get("pending_related_link_delete")
    pending_link = next((link for link in links if link["id"] == pending_id), None)
    if pending_id is not None and pending_link is None:
        st.session_state.pop("pending_related_link_delete", None)
    if pending_link:
        st.warning(f"Delete {pending_link['title'] or pending_link['url']}?")
        confirm_col, cancel_col = st.columns(2)
        if confirm_col.button(
            "Confirm delete", key=f"confirm-related-link-{pending_id}", width="stretch"
        ):
            delete_related_link(pending_id, db_path)
            st.session_state.pop("pending_related_link_delete", None)
            if st.session_state.get("editing_related_link_id") == pending_id:
                st.session_state.pop("editing_related_link_id", None)
            st.warning("Link deleted.")
            st.rerun()
        if cancel_col.button(
            "Cancel", key=f"cancel-related-link-{pending_id}", width="stretch"
        ):
            st.session_state.pop("pending_related_link_delete", None)
            st.rerun()

    return new_selected_id
