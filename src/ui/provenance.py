"""Provenance tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from fossil_tracker.db import (
    create_acquisition,
    get_acquisition,
    get_specimen,
    list_specimens,
    update_acquisition,
    update_specimen,
)
from ui.common import (
    CONFIDENCE_OPTIONS,
    is_read_only,
    SOURCE_TYPE_OPTIONS,
    option_index,
    remember_default_specimen,
    remember_selected_specimen,
    specimen_choice_index,
)


def parse_acquisition_date(value: object) -> date | None:
    """Parse an acquisition date stored as YYYY-MM-DD text."""

    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def show_provenance_manager(db_path: Path) -> None:
    """Render provenance management for the selected specimen.

    :param db_path: SQLite database path.
    """

    specimens = list_specimens(db_path)
    if not specimens:
        st.info("Add a specimen before linking provenance records.")
        return

    specimen_choices = {
        f"{row['collection_code']} - {row['title']}": row["id"] for row in specimens
    }
    selected_specimen_label = st.selectbox(
        "Specimen",
        list(specimen_choices),
        index=specimen_choice_index(specimens),
        key="provenance-specimen",
        on_change=remember_selected_specimen,
        args=("provenance-specimen", specimen_choices),
    )
    remember_default_specimen(selected_specimen_label, specimen_choices)
    specimen = get_specimen(specimen_choices[selected_specimen_label], db_path)
    if specimen is None:
        st.warning("Selected specimen was not found.")
        return

    acquisition = get_acquisition(specimen["acquisition_id"], db_path)
    data = dict(acquisition or {})
    widget_suffix = f"{specimen['id']}-{data.get('id', 'new')}"
    stored_acquisition_date = data.get("acquisition_date", "")
    acquisition_date_value = parse_acquisition_date(stored_acquisition_date)

    st.subheader("Provenance")
    with st.form(f"provenance-form-{widget_suffix}"):
        top = st.columns([1, 1, 1])
        acquisition_date = top[0].date_input(
            "Acquisition date",
            value=acquisition_date_value,
            key=f"provenance-date-{widget_suffix}",
            format="YYYY-MM-DD",
        )
        if stored_acquisition_date and acquisition_date_value is None:
            top[0].warning(
                "Existing date is not in YYYY-MM-DD format. Pick a date to replace it."
            )
        source_name = top[1].text_input(
            "Source / seller / collector",
            value=data.get("source_name", ""),
            key=f"provenance-source-{widget_suffix}",
        )
        source_type = top[2].selectbox(
            "Source type",
            SOURCE_TYPE_OPTIONS,
            index=option_index(SOURCE_TYPE_OPTIONS, data.get("source_type", "")),
            key=f"provenance-source-type-{widget_suffix}",
        )
        seller_url = st.text_input(
            "Seller URL",
            value=data.get("seller_url", ""),
            key=f"provenance-seller-url-{widget_suffix}",
        )
        price = st.columns([1, 1])
        purchase_price = price[0].text_input(
            "Purchase price",
            value=data.get("purchase_price", ""),
            key=f"provenance-price-{widget_suffix}",
        )
        currency = price[1].text_input(
            "Currency",
            value=data.get("currency", ""),
            key=f"provenance-currency-{widget_suffix}",
        )
        confidence = st.selectbox(
            "Ethical confidence",
            CONFIDENCE_OPTIONS,
            index=option_index(CONFIDENCE_OPTIONS, data.get("ethical_confidence", "Unknown")),
            key=f"provenance-confidence-{widget_suffix}",
        )
        provenance_summary = st.text_area(
            "Provenance summary",
            value=data.get("provenance_summary", ""),
            key=f"provenance-summary-{widget_suffix}",
        )
        legality_notes = st.text_area(
            "Legality notes",
            value=data.get("legality_notes", ""),
            key=f"provenance-legality-{widget_suffix}",
        )
        notes = st.text_area(
            "Private acquisition notes",
            value=data.get("notes", ""),
            key=f"provenance-notes-{widget_suffix}",
        )
        save_acquisition = st.form_submit_button(
            "Save provenance", disabled=is_read_only()
        )

    if save_acquisition:
        acquisition_date_text = (
            acquisition_date.isoformat()
            if acquisition_date
            else str(stored_acquisition_date or "")
            if stored_acquisition_date and acquisition_date_value is None
            else ""
        )
        values = {
            "acquisition_date": acquisition_date_text,
            "source_name": source_name,
            "source_type": source_type,
            "seller_url": seller_url,
            "purchase_price": purchase_price,
            "currency": currency,
            "provenance_summary": provenance_summary,
            "legality_notes": legality_notes,
            "ethical_confidence": confidence,
            "notes": notes,
        }
        if acquisition is None:
            acquisition_id = create_acquisition(values, db_path)
            specimen_values = dict(specimen)
            specimen_values["acquisition_id"] = acquisition_id
            update_specimen(specimen["id"], specimen_values, db_path)
            st.success("Provenance added.")
        else:
            update_acquisition(acquisition["id"], values, db_path)
            st.success("Provenance updated.")
        st.rerun()
