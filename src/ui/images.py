"""Images tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from fossil_tracker.db import create_specimen_image, get_specimen, list_specimens
from ui.common import (
    IMAGE_TYPE_OPTIONS,
    remember_default_specimen,
    remember_selected_specimen,
    render_specimen_images,
    save_uploaded_image,
    specimen_choice_index,
)


def show_images_and_notes(db_path: Path) -> None:
    """Render image management for a specimen.

    :param db_path: SQLite database path.
    """

    specimens = list_specimens(db_path)
    if not specimens:
        st.info("Add a specimen before attaching images.")
        return

    choices = {f"{row['collection_code']} - {row['title']}": row["id"] for row in specimens}
    selected_label = st.selectbox(
        "Specimen",
        list(choices),
        index=specimen_choice_index(specimens),
        key="media-specimen",
        on_change=remember_selected_specimen,
        args=("media-specimen", choices),
    )
    remember_default_specimen(selected_label, choices)
    specimen = get_specimen(choices[selected_label], db_path)
    if specimen is None:
        st.warning("Selected specimen was not found.")
        return

    st.subheader("Images")
    render_specimen_images(specimen["id"], db_path, allow_delete=True)
    with st.form("add-image", clear_on_submit=True):
        uploaded = st.file_uploader("Upload image", type=["jpg", "jpeg", "png", "webp", "gif"])
        image_path = st.text_input("Image path")
        image_meta = st.columns([1, 1, 1, 1])
        image_type = image_meta[0].selectbox("Image type", IMAGE_TYPE_OPTIONS)
        caption = image_meta[1].text_input("Caption")
        photographer = image_meta[2].text_input("Photographer")
        date_taken = image_meta[3].text_input("Date taken")
        licence = st.text_input("Licence")
        image_notes = st.text_area("Image notes")
        add_image = st.form_submit_button("Add image")

    if add_image:
        stored_path = image_path.strip()
        if uploaded is not None:
            stored_path = save_uploaded_image(uploaded, specimen)
        if not stored_path:
            st.error("Upload an image or enter an image path.")
            return
        create_specimen_image(
            {
                "specimen_id": specimen["id"],
                "image_path": stored_path,
                "image_type": image_type,
                "caption": caption,
                "photographer": photographer,
                "licence": licence,
                "date_taken": date_taken,
                "notes": image_notes,
            },
            db_path,
        )
        st.success("Image added.")
        st.rerun()

