"""Images tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from fossil_tracker.db import (
    create_specimen_image,
    get_specimen,
    list_image_types,
    list_licences,
    list_specimen_images,
    list_specimens,
    update_specimen_image,
)
from ui.common import (
    remember_default_specimen,
    remember_selected_specimen,
    render_specimen_images,
    save_uploaded_image,
    specimen_choice_index,
)


def image_date_text(value: object) -> str:
    """Return an ISO date string for an optional date picker value."""

    return value.isoformat() if value else ""


def parse_image_date(value: object) -> date | None:
    """Parse an image date stored as YYYY-MM-DD text."""

    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def image_licence_options(licences: list[dict]) -> list[str]:
    """Return optional image licence choices from reference data."""

    return ["", *[row["name"] for row in licences]]


def image_licence_label(value: str) -> str:
    """Render an optional image licence choice."""

    return value or "Not recorded"


def option_with_current(options: list[str], current_value: object) -> list[str]:
    """Include a stored value in a selectbox option list when needed."""

    current_text = str(current_value or "")
    if current_text and current_text not in options:
        return [*options, current_text]
    return options


def option_index(options: list[str], current_value: object) -> int:
    """Return the selectbox index for an existing value."""

    try:
        return options.index(str(current_value or ""))
    except ValueError:
        return 0


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
    images = list_specimen_images(specimen["id"], db_path)
    editing_image_id = st.session_state.get("editing_image_id")
    selected_image = next((image for image in images if image["id"] == editing_image_id), None)
    if editing_image_id and selected_image is None:
        st.session_state.pop("editing_image_id", None)

    licence_options = option_with_current(
        image_licence_options(list_licences(db_path)),
        selected_image["licence"] if selected_image else "",
    )
    image_type_records = list_image_types(db_path)
    image_type_options = type_options(image_type_records)
    form_suffix = selected_image["id"] if selected_image else "new"
    stored_date_taken = selected_image["date_taken"] if selected_image else ""
    date_taken_value = parse_image_date(stored_date_taken)

    if selected_image:
        st.markdown("**Edit image details**")
    else:
        st.markdown("**Add image**")

    with st.form(f"image-form-{form_suffix}", clear_on_submit=selected_image is None):
        uploaded = None
        if selected_image is None:
            uploaded = st.file_uploader("Upload image", type=["jpg", "jpeg", "png", "webp", "gif"])
        image_meta = st.columns([1, 1, 1, 1])
        image_type = image_meta[0].selectbox(
            "Image type",
            image_type_options,
            index=type_option_index(
                image_type_options,
                selected_image["image_type_id"] if selected_image else None,
            ),
            format_func=lambda value: type_option_label(value, image_type_records),
            key=f"image-type-{form_suffix}",
        )
        caption = image_meta[1].text_input(
            "Caption",
            value=(selected_image["caption"] or "") if selected_image else "",
            key=f"image-caption-{form_suffix}",
        )
        photographer = image_meta[2].text_input(
            "Photographer",
            value=(selected_image["photographer"] or "") if selected_image else "",
            key=f"image-photographer-{form_suffix}",
        )
        date_taken = image_meta[3].date_input(
            "Date taken",
            value=date_taken_value,
            format="YYYY-MM-DD",
            key=f"image-date-{form_suffix}",
        )
        if stored_date_taken and date_taken_value is None:
            image_meta[3].warning(
                "Existing date is not in YYYY-MM-DD format. Pick a date to replace it."
            )
        licence = st.selectbox(
            "Licence",
            licence_options,
            index=option_index(licence_options, selected_image["licence"] if selected_image else ""),
            format_func=image_licence_label,
            key=f"image-licence-{form_suffix}",
        )
        image_notes = st.text_area(
            "Image notes",
            value=(selected_image["notes"] or "") if selected_image else "",
            key=f"image-notes-{form_suffix}",
        )
        action_col, cancel_col = st.columns([1, 1])
        save_image = action_col.form_submit_button(
            "Save image details" if selected_image else "Add image"
        )
        cancel_edit = cancel_col.form_submit_button(
            "Cancel editing", disabled=selected_image is None
        )

    if cancel_edit:
        st.session_state.pop("editing_image_id", None)
        st.rerun()

    if save_image:
        date_taken_text = (
            image_date_text(date_taken)
            if date_taken
            else str(stored_date_taken or "")
            if stored_date_taken and date_taken_value is None
            else ""
        )
        if selected_image:
            update_specimen_image(
                selected_image["id"],
                {
                    "specimen_id": specimen["id"],
                    "image_path": selected_image["image_path"],
                    "image_type_id": image_type,
                    "caption": caption,
                    "photographer": photographer,
                    "licence": licence,
                    "date_taken": date_taken_text,
                    "notes": image_notes,
                },
                db_path,
            )
            st.success("Image details updated.")
            st.session_state.pop("editing_image_id", None)
            st.rerun()

        if uploaded is None:
            st.error("Upload an image.")
            return
        stored_path = save_uploaded_image(uploaded, specimen)
        create_specimen_image(
            {
                "specimen_id": specimen["id"],
                "image_path": stored_path,
                "image_type_id": image_type,
                "caption": caption,
                "photographer": photographer,
                "licence": licence,
                "date_taken": date_taken_text,
                "notes": image_notes,
            },
            db_path,
        )
        st.success("Image added.")
        st.rerun()


def type_options(records: list[dict]) -> list[int | None]:
    """Return optional type ids for image type selectboxes."""

    return [None, *[row["id"] for row in records]]


def type_option_index(options: list[int | None], current_value: object) -> int:
    """Return the selectbox index for an optional reference id."""

    try:
        return options.index(int(current_value) if current_value else None)
    except ValueError:
        return 0


def type_option_label(value: int | None, records: list[dict]) -> str:
    """Render the optional image type placeholder."""

    if value is None:
        return "Not recorded"
    for record in records:
        if record["id"] == value:
            return record["name"]
    return "Not recorded"
