"""Streamlit user interface for the Fossil Tracker core register."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from fossil_tracker.config import APP_NAME, database_path
from fossil_tracker.db import (
    SPECIMEN_FIELDS,
    apply_migrations,
    create_specimen,
    delete_specimen,
    export_csv,
    get_specimen,
    list_specimens,
    seed_specimens,
    update_specimen,
)

CONFIDENCE_OPTIONS = ["Unknown", "Low", "Medium", "High"]
PREPARATION_OPTIONS = [
    "",
    "Natural",
    "Polished",
    "Split and polished",
    "Split",
    "Matrix",
    "Prepared",
    "Cast",
]


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.title(APP_NAME)
    st.caption("Personal fossil collection register")

    db_path = database_path()
    try:
        apply_migrations(db_path)
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    with st.sidebar:
        st.subheader("Database")
        st.code(str(db_path), language=None)
        if st.button("Add starter records", use_container_width=True):
            added = seed_specimens(db_path)
            st.success(f"Added {added} starter record{'s' if added != 1 else ''}.")
        csv_file = st.file_uploader("Import CSV", type=["csv"])
        if csv_file is not None and st.button("Import uploaded CSV", use_container_width=True):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as handle:
                handle.write(csv_file.getbuffer())
                temp_path = Path(handle.name)
            from fossil_tracker.db import import_csv

            count = import_csv(temp_path, db_path)
            temp_path.unlink(missing_ok=True)
            st.success(f"Imported {count} record{'s' if count != 1 else ''}.")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as handle:
            export_path = Path(handle.name)
        export_csv(export_path, db_path)
        st.download_button(
            "Download CSV export",
            export_path.read_bytes(),
            file_name="fossil_tracker_export.csv",
            mime="text/csv",
            use_container_width=True,
        )
        export_path.unlink(missing_ok=True)

    tab_register, tab_add, tab_edit = st.tabs(["Register", "Add specimen", "Edit specimen"])

    with tab_register:
        show_register(db_path)

    with tab_add:
        show_add_form(db_path)

    with tab_edit:
        show_edit_form(db_path)


def show_register(db_path: Path) -> None:
    controls = st.columns([2, 1, 1])
    search = controls[0].text_input("Search", placeholder="Collection code, taxon, locality, source")
    confidence = controls[1].selectbox("Ethical confidence", ["All", *CONFIDENCE_OPTIONS])
    documented_only = controls[2].checkbox("Documentation only")

    specimens = list_specimens(db_path, search, confidence, documented_only)
    st.metric("Specimens", len(specimens))

    if not specimens:
        st.info("No matching specimens yet.")
        return

    for specimen in specimens:
        title = f"{specimen['collection_code']} - {specimen['title']}"
        with st.expander(title):
            top = st.columns([1, 1, 1])
            top[0].markdown(f"**Taxon**  \n{_blank(specimen['taxonomic_identification'])}")
            top[1].markdown(f"**Age**  \n{_blank(specimen['geological_age'])}")
            top[2].markdown(f"**Locality**  \n{_blank(specimen['formation_or_locality'])}")

            provenance = st.columns([1, 1, 1])
            provenance[0].markdown(f"**Source**  \n{_blank(specimen['source'])}")
            provenance[1].markdown(f"**Ethical confidence**  \n{_blank(specimen['ethical_confidence'])}")
            provenance[2].markdown(
                f"**Documentation**  \n{'Available' if specimen['documentation_available'] else 'Not recorded'}"
            )

            if specimen["description"]:
                st.markdown("**Description**")
                st.write(specimen["description"])
            if specimen["provenance_notes"] or specimen["legality_ethics_notes"]:
                st.markdown("**Provenance and ethics**")
                st.write(specimen["provenance_notes"] or "")
                st.write(specimen["legality_ethics_notes"] or "")
            if specimen["field_notes_links"]:
                st.markdown("**Field Notes links**")
                st.write(specimen["field_notes_links"])
            if specimen["image_paths"]:
                st.markdown("**Image paths**")
                st.write(specimen["image_paths"])


def show_add_form(db_path: Path) -> None:
    with st.form("add-specimen", clear_on_submit=True):
        values = specimen_inputs("new")
        submitted = st.form_submit_button("Add specimen")
    if submitted:
        if not values["collection_code"] or not values["title"]:
            st.error("Collection code and title are required.")
            return
        specimen_id = create_specimen(values, db_path)
        st.success(f"Added specimen #{specimen_id}.")


def show_edit_form(db_path: Path) -> None:
    specimens = list_specimens(db_path)
    if not specimens:
        st.info("Add a specimen before editing.")
        return

    choices = {f"{row['collection_code']} - {row['title']}": row["id"] for row in specimens}
    selected_label = st.selectbox("Specimen", list(choices))
    specimen = get_specimen(choices[selected_label], db_path)
    if specimen is None:
        st.warning("Selected specimen was not found.")
        return

    with st.form("edit-specimen"):
        values = specimen_inputs("edit", specimen)
        left, right = st.columns([1, 1])
        save = left.form_submit_button("Save changes", use_container_width=True)
        remove = right.form_submit_button("Delete specimen", use_container_width=True)

    if save:
        if not values["collection_code"] or not values["title"]:
            st.error("Collection code and title are required.")
            return
        update_specimen(specimen["id"], values, db_path)
        st.success("Specimen updated.")

    if remove:
        delete_specimen(specimen["id"], db_path)
        st.warning("Specimen deleted.")


def specimen_inputs(prefix: str, specimen: dict | None = None) -> dict:
    data = dict(specimen or {})
    values: dict[str, object] = {}

    basic = st.columns([1, 2, 1])
    values["collection_code"] = basic[0].text_input(
        "Collection code", value=data.get("collection_code", ""), key=f"{prefix}-collection-code"
    )
    values["title"] = basic[1].text_input("Title", value=data.get("title", ""), key=f"{prefix}-title")
    values["common_name"] = basic[2].text_input(
        "Common name", value=data.get("common_name", ""), key=f"{prefix}-common-name"
    )

    context = st.columns([1, 1, 1])
    values["taxonomic_identification"] = context[0].text_input(
        "Taxonomic identification",
        value=data.get("taxonomic_identification", ""),
        key=f"{prefix}-taxon",
    )
    values["geological_age"] = context[1].text_input(
        "Geological age / period", value=data.get("geological_age", ""), key=f"{prefix}-age"
    )
    values["formation_or_locality"] = context[2].text_input(
        "Formation or locality",
        value=data.get("formation_or_locality", ""),
        key=f"{prefix}-locality",
    )

    place = st.columns([1, 1, 1])
    values["country_region"] = place[0].text_input(
        "Country / region", value=data.get("country_region", ""), key=f"{prefix}-country"
    )
    values["storage_location"] = place[1].text_input(
        "Storage location", value=data.get("storage_location", ""), key=f"{prefix}-storage"
    )
    current_preparation = data.get("preparation_type", "")
    if current_preparation not in PREPARATION_OPTIONS:
        PREPARATION_OPTIONS.append(current_preparation)
    values["preparation_type"] = place[2].selectbox(
        "Preparation type",
        PREPARATION_OPTIONS,
        index=PREPARATION_OPTIONS.index(current_preparation),
        key=f"{prefix}-preparation",
    )

    acquisition = st.columns([1, 1, 1, 1])
    values["acquisition_date"] = acquisition[0].text_input(
        "Acquisition date", value=data.get("acquisition_date", ""), key=f"{prefix}-acquisition-date"
    )
    values["source"] = acquisition[1].text_input("Source / seller / collector", value=data.get("source", ""), key=f"{prefix}-source")
    values["purchase_price"] = acquisition[2].text_input(
        "Purchase price", value=data.get("purchase_price", ""), key=f"{prefix}-price"
    )
    values["currency"] = acquisition[3].text_input("Currency", value=data.get("currency", ""), key=f"{prefix}-currency")

    ethics = st.columns([1, 1])
    current_confidence = data.get("ethical_confidence", "Unknown") or "Unknown"
    if current_confidence not in CONFIDENCE_OPTIONS:
        current_confidence = "Unknown"
    values["ethical_confidence"] = ethics[0].selectbox(
        "Ethical confidence",
        CONFIDENCE_OPTIONS,
        index=CONFIDENCE_OPTIONS.index(current_confidence),
        key=f"{prefix}-confidence",
    )
    values["documentation_available"] = ethics[1].checkbox(
        "Documentation available",
        value=bool(data.get("documentation_available", False)),
        key=f"{prefix}-documentation",
    )

    values["description"] = st.text_area("Description", value=data.get("description", ""), key=f"{prefix}-description")
    values["measurements"] = st.text_input("Measurements", value=data.get("measurements", ""), key=f"{prefix}-measurements")
    values["provenance_notes"] = st.text_area(
        "Provenance notes", value=data.get("provenance_notes", ""), key=f"{prefix}-provenance"
    )
    values["legality_ethics_notes"] = st.text_area(
        "Legality / ethical confidence notes",
        value=data.get("legality_ethics_notes", ""),
        key=f"{prefix}-legality",
    )
    values["public_notes"] = st.text_area("Public notes", value=data.get("public_notes", ""), key=f"{prefix}-public")
    values["private_notes"] = st.text_area("Private notes", value=data.get("private_notes", ""), key=f"{prefix}-private")
    values["image_paths"] = st.text_area("Image paths", value=data.get("image_paths", ""), key=f"{prefix}-images")
    values["field_notes_links"] = st.text_area(
        "Field Notes links", value=data.get("field_notes_links", ""), key=f"{prefix}-links"
    )

    return {field: values.get(field, "") for field in SPECIMEN_FIELDS}


def _blank(value: object) -> str:
    return str(value) if value else "Not recorded"


if __name__ == "__main__":
    main()
