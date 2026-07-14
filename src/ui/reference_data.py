"""Reference Data tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import sqlite3

import streamlit as st

from fossil_tracker.db import (
    create_document_type,
    create_image_type,
    create_licence,
    create_geological_age,
    create_locality,
    create_measurement_type,
    create_preparation_type,
    delete_document_type,
    delete_geological_age,
    delete_image_type,
    delete_licence,
    delete_locality,
    delete_measurement_type,
    delete_preparation_type,
    list_document_types,
    list_geological_ages,
    list_image_types,
    list_licences,
    list_localities,
    list_measurement_types,
    list_preparation_types,
    update_document_type,
    update_geological_age,
    update_image_type,
    update_licence,
    update_locality,
    update_measurement_type,
    update_preparation_type,
)
from ui.common import (
    render_geological_age_table,
    render_licence_table,
    render_locality_table,
    render_measurement_type_table,
    render_preparation_type_table,
    render_simple_type_table,
)


def _selected_record(records: list[dict], state_key: str, table_renderer, **kwargs) -> dict | None:
    """Return the record selected through a reference table checkbox."""

    selected_id = st.session_state.get(state_key)
    if not any(row["id"] == selected_id for row in records):
        selected_id = None
    new_selected_id = table_renderer(records, selected_id, **kwargs)
    if new_selected_id != selected_id:
        st.session_state[state_key] = new_selected_id
        st.rerun()
    return next((row for row in records if row["id"] == selected_id), None)


def _clear_selection(state_key: str) -> None:
    """Clear the active reference record without changing persisted data."""

    st.session_state[state_key] = None


def show_context_manager(db_path: Path) -> None:
    """Render locality, age, preparation, licensing, and measurement reference forms.

    :param db_path: SQLite database path.
    """

    (
        ages_tab,
        localities_tab,
        preparation_tab,
        licensing_tab,
        measurement_tab,
        image_types_tab,
        document_types_tab,
    ) = st.tabs(
        [
            "Geological ages",
            "Localities",
            "Preparation types",
            "Licensing",
            "Measurement types",
            "Image types",
            "Document types",
        ]
    )

    with ages_tab:
        show_geological_age_manager(db_path)

    with localities_tab:
        show_locality_manager(db_path)

    with preparation_tab:
        show_preparation_type_manager(db_path)

    with licensing_tab:
        show_licence_manager(db_path)

    with measurement_tab:
        show_measurement_type_manager(db_path)

    with image_types_tab:
        show_image_type_manager(db_path)

    with document_types_tab:
        show_document_type_manager(db_path)

def show_geological_age_manager(db_path: Path) -> None:
    """Render geological age reference data management.

    :param db_path: SQLite database path.
    """

    records = list_geological_ages(db_path)
    st.subheader("Geological ages")
    state_key = "selected-geological-age-id"
    selected_row = _selected_record(records, state_key, render_geological_age_table)
    selected_id = selected_row["id"] if selected_row else None

    with st.form(f"geological-age-form-{selected_id or 'new'}", clear_on_submit=selected_id is None):
        age_cols = st.columns([1, 1, 1, 1])
        era = age_cols[0].text_input(
            "Era", value=(selected_row["era"] or "") if selected_row else "", key=f"age-era-{selected_id or 'new'}"
        )
        period = age_cols[1].text_input(
            "Period",
            value=(selected_row["period"] or "") if selected_row else "",
            key=f"age-period-{selected_id or 'new'}",
        )
        epoch = age_cols[2].text_input(
            "Epoch",
            value=(selected_row["epoch"] or "") if selected_row else "",
            key=f"age-epoch-{selected_id or 'new'}",
        )
        stage = age_cols[3].text_input(
            "Stage",
            value=(selected_row["stage"] or "") if selected_row else "",
            key=f"age-stage-{selected_id or 'new'}",
        )
        range_cols = st.columns([1, 1])
        max_ma = range_cols[0].text_input(
            "Max Ma",
            value="" if not selected_row or selected_row["max_ma"] is None else str(selected_row["max_ma"]),
            key=f"age-max-{selected_id or 'new'}",
        )
        min_ma = range_cols[1].text_input(
            "Min Ma",
            value="" if not selected_row or selected_row["min_ma"] is None else str(selected_row["min_ma"]),
            key=f"age-min-{selected_id or 'new'}",
        )
        save_col, delete_col, clear_col = st.columns(3)
        save_age = save_col.form_submit_button("Save")
        remove_age = delete_col.form_submit_button("Delete", disabled=selected_row is None)
        clear_age = clear_col.form_submit_button("Clear")

    values = {
        "era": era,
        "period": period,
        "epoch": epoch,
        "stage": stage,
        "max_ma": max_ma,
        "min_ma": min_ma,
    }
    if clear_age:
        _clear_selection(state_key)
        st.rerun()

    if save_age:
        if selected_row is None:
            create_geological_age(values, db_path)
            st.success("Geological age added.")
        else:
            update_geological_age(selected_row["id"], values, db_path)
            st.success("Geological age updated.")
        st.rerun()

    if remove_age and selected_row is not None:
        try:
            delete_geological_age(selected_row["id"], db_path)
        except sqlite3.IntegrityError:
            st.error("This geological age is in use and cannot be deleted.")
            return
        st.warning("Geological age deleted.")
        st.rerun()


def show_locality_manager(db_path: Path) -> None:
    """Render locality reference data management.

    :param db_path: SQLite database path.
    """

    records = list_localities(db_path)
    st.subheader("Localities")
    state_key = "selected-locality-id"
    selected_row = _selected_record(records, state_key, render_locality_table)
    selected_id = selected_row["id"] if selected_row else None

    with st.form(f"locality-form-{selected_id or 'new'}", clear_on_submit=selected_id is None):
        loc_cols = st.columns([1, 1, 1])
        locality_name = loc_cols[0].text_input(
            "Locality name",
            value=(selected_row["locality_name"] or "") if selected_row else "",
            key=f"locality-name-{selected_id or 'new'}",
        )
        formation = loc_cols[1].text_input(
            "Formation",
            value=(selected_row["formation"] or "") if selected_row else "",
            key=f"locality-formation-{selected_id or 'new'}",
        )
        member = loc_cols[2].text_input(
            "Member",
            value=(selected_row["member"] or "") if selected_row else "",
            key=f"locality-member-{selected_id or 'new'}",
        )
        geo_cols = st.columns([1, 1, 1, 1])
        region = geo_cols[0].text_input(
            "Region",
            value=(selected_row["region"] or "") if selected_row else "",
            key=f"locality-region-{selected_id or 'new'}",
        )
        country = geo_cols[1].text_input(
            "Country",
            value=(selected_row["country"] or "") if selected_row else "",
            key=f"locality-country-{selected_id or 'new'}",
        )
        latitude = geo_cols[2].text_input(
            "Latitude",
            value="" if not selected_row or selected_row["latitude"] is None else str(selected_row["latitude"]),
            key=f"locality-latitude-{selected_id or 'new'}",
        )
        longitude = geo_cols[3].text_input(
            "Longitude",
            value="" if not selected_row or selected_row["longitude"] is None else str(selected_row["longitude"]),
            key=f"locality-longitude-{selected_id or 'new'}",
        )
        precision = st.text_input(
            "Locality precision",
            value=(selected_row["locality_precision"] or "") if selected_row else "",
            key=f"locality-precision-{selected_id or 'new'}",
        )
        notes = st.text_area(
            "Locality notes",
            value=selected_row["locality_notes"] if selected_row and selected_row["locality_notes"] else "",
            key=f"locality-notes-{selected_id or 'new'}",
        )
        save_col, delete_col, clear_col = st.columns(3)
        save_locality = save_col.form_submit_button("Save")
        remove_locality = delete_col.form_submit_button("Delete", disabled=selected_row is None)
        clear_locality = clear_col.form_submit_button("Clear")

    values = {
        "locality_name": locality_name,
        "formation": formation,
        "member": member,
        "region": region,
        "country": country,
        "latitude": latitude,
        "longitude": longitude,
        "locality_precision": precision,
        "locality_notes": notes,
    }
    if clear_locality:
        _clear_selection(state_key)
        st.rerun()

    if save_locality:
        if selected_row is None:
            create_locality(values, db_path)
            st.success("Locality added.")
        else:
            update_locality(selected_row["id"], values, db_path)
            st.success("Locality updated.")
        st.rerun()

    if remove_locality and selected_row is not None:
        try:
            delete_locality(selected_row["id"], db_path)
        except sqlite3.IntegrityError:
            st.error("This locality is in use and cannot be deleted.")
            return
        st.warning("Locality deleted.")
        st.rerun()


def show_preparation_type_manager(db_path: Path) -> None:
    """Render preparation type reference data management.

    :param db_path: SQLite database path.
    """

    records = list_preparation_types(db_path)
    st.subheader("Preparation types")
    state_key = "selected-preparation-type-id"
    selected_row = _selected_record(records, state_key, render_preparation_type_table)
    selected_id = selected_row["id"] if selected_row else None

    with st.form(f"preparation-type-form-{selected_id or 'new'}", clear_on_submit=selected_id is None):
        name = st.text_input(
            "Name",
            value=(selected_row["name"] or "") if selected_row else "",
            key=f"preparation-type-name-{selected_id or 'new'}",
        )
        description = st.text_area(
            "Description",
            value=selected_row["description"] if selected_row and selected_row["description"] else "",
            key=f"preparation-type-description-{selected_id or 'new'}",
        )
        save_col, delete_col, clear_col = st.columns(3)
        save_preparation = save_col.form_submit_button("Save")
        remove_preparation = delete_col.form_submit_button("Delete", disabled=selected_row is None)
        clear_preparation = clear_col.form_submit_button("Clear")

    if clear_preparation:
        _clear_selection(state_key)
        st.rerun()

    if save_preparation:
        if not name.strip():
            st.error("Preparation type name is required.")
            return
        values = {"name": name.strip(), "description": description}
        try:
            if selected_row is None:
                create_preparation_type(values, db_path)
                st.success("Preparation type added.")
            else:
                update_preparation_type(selected_row["id"], values, db_path)
                st.success("Preparation type updated.")
        except sqlite3.IntegrityError:
            st.error("A preparation type with that name already exists.")
            return
        st.rerun()

    if remove_preparation and selected_row is not None:
        try:
            delete_preparation_type(selected_row["id"], db_path)
        except sqlite3.IntegrityError:
            st.error("This preparation type is in use and cannot be deleted.")
            return
        st.warning("Preparation type deleted.")
        st.rerun()


def show_licence_manager(db_path: Path) -> None:
    """Render licence reference data management.

    :param db_path: SQLite database path.
    """

    licences = list_licences(db_path)
    st.subheader("Licensing")
    state_key = "selected-licence-id"
    selected_row = _selected_record(licences, state_key, render_licence_table)
    selected_id = selected_row["id"] if selected_row else None

    with st.form(f"licence-form-{selected_id or 'new'}", clear_on_submit=selected_id is None):
        name = st.text_input(
            "Licence name",
            value=(selected_row["name"] or "") if selected_row else "",
            key=f"licence-name-{selected_id or 'new'}",
        )
        url = st.text_input(
            "Licence URL",
            value=(selected_row["url"] or "") if selected_row else "",
            key=f"licence-url-{selected_id or 'new'}",
        )
        notes = st.text_area(
            "Licence notes",
            value=selected_row["notes"] if selected_row and selected_row["notes"] else "",
            key=f"licence-notes-{selected_id or 'new'}",
        )
        save_col, delete_col, clear_col = st.columns(3)
        save_licence = save_col.form_submit_button("Save")
        remove_licence = delete_col.form_submit_button("Delete", disabled=selected_row is None)
        clear_licence = clear_col.form_submit_button("Clear")

    if clear_licence:
        _clear_selection(state_key)
        st.rerun()

    if save_licence:
        if not name.strip():
            st.error("Licence name is required.")
            return
        values = {"name": name.strip(), "notes": notes, "url": url.strip()}
        try:
            if selected_row is None:
                create_licence(values, db_path)
                st.success("Licence added.")
            else:
                update_licence(selected_row["id"], values, db_path)
                st.success("Licence updated.")
        except sqlite3.IntegrityError:
            st.error("A licence with that name already exists.")
            return
        st.rerun()

    if remove_licence and selected_row is not None:
        delete_licence(selected_row["id"], db_path)
        st.warning("Licence deleted.")
        st.rerun()


def show_measurement_type_manager(db_path: Path) -> None:
    """Render measurement type reference data management.

    :param db_path: SQLite database path.
    """

    measurement_types = list_measurement_types(db_path)
    st.subheader("Measurement types")
    state_key = "selected-measurement-type-id"
    selected_row = _selected_record(measurement_types, state_key, render_measurement_type_table)
    selected_id = selected_row["id"] if selected_row else None

    with st.form(f"measurement-type-form-{selected_id or 'new'}", clear_on_submit=selected_id is None):
        form_cols = st.columns([2, 1])
        name = form_cols[0].text_input(
            "Name",
            value=(selected_row["name"] or "") if selected_row else "",
            key=f"measurement-type-name-{selected_id or 'new'}",
        )
        unit = form_cols[1].text_input(
            "Unit",
            value=selected_row["unit"] if selected_row else "",
            key=f"measurement-type-unit-{selected_id or 'new'}",
        )
        description = st.text_area(
            "Description",
            value=selected_row["description"] if selected_row and selected_row["description"] else "",
            key=f"measurement-type-description-{selected_id or 'new'}",
        )
        save_col, delete_col, clear_col = st.columns(3)
        save_measurement_type = save_col.form_submit_button("Save")
        remove_measurement_type = delete_col.form_submit_button("Delete", disabled=selected_row is None)
        clear_measurement_type = clear_col.form_submit_button("Clear")

    if clear_measurement_type:
        _clear_selection(state_key)
        st.rerun()

    if save_measurement_type:
        if not name.strip():
            st.error("Measurement type name is required.")
            return
        if not unit.strip():
            st.error("Measurement type unit is required.")
            return
        try:
            values = {
                "name": name.strip(),
                "unit": unit.strip(),
                "description": description,
            }
            if selected_row is None:
                create_measurement_type(values, db_path)
                st.success("Measurement type added.")
            else:
                update_measurement_type(selected_row["id"], values, db_path)
                st.success("Measurement type updated.")
        except sqlite3.IntegrityError:
            st.error("A measurement type with that name already exists.")
            return
        st.rerun()

    if remove_measurement_type and selected_row is not None:
        try:
            delete_measurement_type(selected_row["id"], db_path)
        except sqlite3.IntegrityError:
            st.error("This measurement type is in use and cannot be deleted.")
            return
        st.warning("Measurement type deleted.")
        st.rerun()


def show_image_type_manager(db_path: Path) -> None:
    """Render image type reference data management."""

    image_types = list_image_types(db_path)
    st.subheader("Image types")
    state_key = "selected-image-type-id"
    selected_row = _selected_record(
        image_types, state_key, render_simple_type_table, key="image-type-table"
    )
    selected_id = selected_row["id"] if selected_row else None

    with st.form(f"image-type-form-{selected_id or 'new'}", clear_on_submit=selected_id is None):
        name = st.text_input(
            "Name",
            value=(selected_row["name"] or "") if selected_row else "",
            key=f"image-type-name-{selected_id or 'new'}",
        )
        description = st.text_area(
            "Description",
            value=selected_row["description"] if selected_row and selected_row["description"] else "",
            key=f"image-type-description-{selected_id or 'new'}",
        )
        save_col, delete_col, clear_col = st.columns(3)
        save_image_type = save_col.form_submit_button("Save")
        remove_image_type = delete_col.form_submit_button("Delete", disabled=selected_row is None)
        clear_image_type = clear_col.form_submit_button("Clear")

    if clear_image_type:
        _clear_selection(state_key)
        st.rerun()

    if save_image_type:
        if not name.strip():
            st.error("Image type name is required.")
            return
        values = {"name": name.strip(), "description": description}
        try:
            if selected_row is None:
                create_image_type(values, db_path)
                st.success("Image type added.")
            else:
                update_image_type(selected_row["id"], values, db_path)
                st.success("Image type updated.")
        except sqlite3.IntegrityError:
            st.error("An image type with that name already exists.")
            return
        st.rerun()

    if remove_image_type and selected_row is not None:
        try:
            delete_image_type(selected_row["id"], db_path)
        except sqlite3.IntegrityError:
            st.error("This image type is in use and cannot be deleted.")
            return
        st.warning("Image type deleted.")
        st.rerun()


def show_document_type_manager(db_path: Path) -> None:
    """Render document type reference data management."""

    document_types = list_document_types(db_path)
    st.subheader("Document types")
    state_key = "selected-document-type-id"
    selected_row = _selected_record(
        document_types, state_key, render_simple_type_table, key="document-type-table"
    )
    selected_id = selected_row["id"] if selected_row else None

    with st.form(
        f"document-type-form-{selected_id or 'new'}",
        clear_on_submit=selected_id is None,
    ):
        name = st.text_input(
            "Name",
            value=(selected_row["name"] or "") if selected_row else "",
            key=f"document-type-name-{selected_id or 'new'}",
        )
        description = st.text_area(
            "Description",
            value=selected_row["description"] if selected_row and selected_row["description"] else "",
            key=f"document-type-description-{selected_id or 'new'}",
        )
        save_col, delete_col, clear_col = st.columns(3)
        save_document_type = save_col.form_submit_button("Save")
        remove_document_type = delete_col.form_submit_button("Delete", disabled=selected_row is None)
        clear_document_type = clear_col.form_submit_button("Clear")

    if clear_document_type:
        _clear_selection(state_key)
        st.rerun()

    if save_document_type:
        if not name.strip():
            st.error("Document type name is required.")
            return
        values = {"name": name.strip(), "description": description}
        try:
            if selected_row is None:
                create_document_type(values, db_path)
                st.success("Document type added.")
            else:
                update_document_type(selected_row["id"], values, db_path)
                st.success("Document type updated.")
        except sqlite3.IntegrityError:
            st.error("A document type with that name already exists.")
            return
        st.rerun()

    if remove_document_type and selected_row is not None:
        try:
            delete_document_type(selected_row["id"], db_path)
        except sqlite3.IntegrityError:
            st.error("This document type is in use and cannot be deleted.")
            return
        st.warning("Document type deleted.")
        st.rerun()
