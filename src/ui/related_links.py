"""Related Links tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ui.common import *  # noqa: F403
from fossil_tracker.db import *  # noqa: F403

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
    render_related_links(specimen["id"], db_path, allow_delete=True)

    with st.form("add-related-link", clear_on_submit=True):
        url = st.text_input("URL")
        add_link = st.form_submit_button("Add link")

    if add_link:
        cleaned_url = url.strip()
        error = validate_related_link_url(cleaned_url)
        if error:
            st.error(error)
            return
        create_related_link(
            {
                "specimen_id": specimen["id"],
                "url": cleaned_url,
            },
            db_path,
        )
        st.success("Link added.")
        st.rerun()


