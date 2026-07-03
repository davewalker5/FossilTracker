"""Streamlit user interface for the Fossil Tracker core register."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import streamlit as st

from fossil_tracker.config import APP_NAME, PROJECT_ROOT, database_path, image_dir
from fossil_tracker.db import (
    SPECIMEN_FIELDS,
    apply_migrations,
    create_acquisition,
    create_acquisition_document,
    create_geological_age,
    create_locality,
    create_observation,
    create_preparation_type,
    create_specimen_image,
    create_specimen,
    create_taxonomy,
    delete_acquisition_document,
    delete_observation,
    delete_specimen_image,
    delete_specimen,
    export_csv,
    get_acquisition,
    get_specimen,
    get_geological_age,
    get_locality,
    get_taxonomy,
    has_acquisition_documents,
    list_geological_ages,
    list_acquisition_documents,
    list_acquisitions,
    list_localities,
    list_observations,
    list_preparation_types,
    list_specimen_images,
    list_specimens,
    list_taxonomy,
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
IMAGE_TYPE_OPTIONS = ["", "Overall", "Close-up", "Matrix", "Label", "Comparison", "Other"]
OBSERVATION_TYPE_OPTIONS = ["", "General", "Morphology", "Condition", "Measurement", "Research note", "Other"]
SOURCE_TYPE_OPTIONS = ["", "Seller", "Collector", "Gift", "Field collection", "Auction", "Unknown", "Other"]


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

    tab_register, tab_add, tab_edit, tab_context, tab_provenance, tab_notes = st.tabs(
        ["Register", "Add specimen", "Edit specimen", "Context", "Provenance", "Images and notes"]
    )

    with tab_register:
        show_register(db_path)

    with tab_add:
        show_add_form(db_path)

    with tab_edit:
        show_edit_form(db_path)

    with tab_context:
        show_context_manager(db_path)

    with tab_provenance:
        show_provenance_manager(db_path)

    with tab_notes:
        show_images_and_notes(db_path)


def show_register(db_path: Path) -> None:
    controls = st.columns([2, 1, 1])
    search = controls[0].text_input("Search", placeholder="Collection code, taxon, locality, source")
    confidence = controls[1].selectbox("Ethical confidence", ["All", *CONFIDENCE_OPTIONS])
    documented_only = controls[2].checkbox("Has documents")

    specimens = list_specimens(db_path, search, confidence, documented_only)
    st.metric("Specimens", len(specimens))

    if not specimens:
        st.info("No matching specimens yet.")
        return

    for specimen in specimens:
        title = f"{specimen['collection_code']} - {specimen['title']}"
        with st.expander(title):
            taxon = get_taxonomy(specimen["taxon_id"], db_path)
            age = get_geological_age(specimen["geological_age_id"], db_path)
            locality = get_locality(specimen["locality_id"], db_path)
            acquisition = get_acquisition(specimen["acquisition_id"], db_path)
            top = st.columns([1, 1, 1])
            top[0].markdown(f"**Taxon**  \n{_blank(taxonomy_label(taxon))}")
            top[1].markdown(f"**Age**  \n{_blank(geological_age_label(age))}")
            top[2].markdown(f"**Locality**  \n{_blank(locality_label(locality))}")

            provenance = st.columns([1, 1, 1, 1])
            provenance[0].markdown(f"**Source**  \n{_blank(acquisition['source_name'] if acquisition else '')}")
            provenance[1].markdown(f"**Ethical confidence**  \n{_blank(acquisition['ethical_confidence'] if acquisition else '')}")
            provenance[2].markdown(
                f"**Documents**  \n{'Available' if has_acquisition_documents(specimen['acquisition_id'], db_path) else 'Not recorded'}"
            )
            provenance[3].markdown(
                f"**Public**  \n{'Yes' if specimen['public_visible'] else 'No'}"
            )

            if specimen["description"]:
                st.markdown("**Description**")
                st.write(specimen["description"])
            if acquisition and (acquisition["provenance_summary"] or acquisition["legality_notes"]):
                st.markdown("**Provenance and ethics**")
                st.write(acquisition["provenance_summary"] or "")
                st.write(acquisition["legality_notes"] or "")
            if specimen["field_notes_links"]:
                st.markdown("**Field Notes links**")
                st.write(specimen["field_notes_links"])
            render_specimen_images(specimen["id"], db_path)
            render_specimen_observations(specimen["id"], db_path)


def show_add_form(db_path: Path) -> None:
    with st.form("add-specimen", clear_on_submit=True):
        values = specimen_inputs("new", db_path=db_path)
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
        values = specimen_inputs("edit", specimen, db_path)
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


def show_context_manager(db_path: Path) -> None:
    taxonomy_tab, ages_tab, localities_tab, preparation_tab = st.tabs(
        ["Taxonomy", "Geological ages", "Localities", "Preparation types"]
    )

    with taxonomy_tab:
        st.subheader("Taxonomy")
        render_reference_list([taxonomy_label(row) for row in list_taxonomy(db_path)])
        with st.form("add-taxonomy", clear_on_submit=True):
            tax_cols = st.columns([1, 1, 1, 1])
            kingdom = tax_cols[0].text_input("Kingdom", value="Animalia")
            phylum = tax_cols[1].text_input("Phylum")
            class_name = tax_cols[2].text_input("Class")
            order_name = tax_cols[3].text_input("Order")
            family_cols = st.columns([1, 1, 1])
            family = family_cols[0].text_input("Family")
            genus = family_cols[1].text_input("Genus")
            species = family_cols[2].text_input("Species")
            confidence = st.selectbox("Identification confidence", CONFIDENCE_OPTIONS)
            notes = st.text_area("Identification notes")
            add_taxon = st.form_submit_button("Add taxonomy")
        if add_taxon:
            create_taxonomy(
                {
                    "kingdom": kingdom,
                    "phylum": phylum,
                    "class_name": class_name,
                    "order_name": order_name,
                    "family": family,
                    "genus": genus,
                    "species": species,
                    "identification_confidence": confidence,
                    "identification_notes": notes,
                },
                db_path,
            )
            st.success("Taxonomy record added.")
            st.rerun()

    with ages_tab:
        st.subheader("Geological ages")
        render_reference_list([geological_age_label(row) for row in list_geological_ages(db_path)])
        with st.form("add-geological-age", clear_on_submit=True):
            age_cols = st.columns([1, 1, 1, 1])
            era = age_cols[0].text_input("Era")
            period = age_cols[1].text_input("Period")
            epoch = age_cols[2].text_input("Epoch")
            stage = age_cols[3].text_input("Stage")
            range_cols = st.columns([1, 1])
            max_ma = range_cols[0].text_input("Max Ma")
            min_ma = range_cols[1].text_input("Min Ma")
            notes = st.text_area("Notes")
            add_age = st.form_submit_button("Add geological age")
        if add_age:
            create_geological_age(
                {
                    "era": era,
                    "period": period,
                    "epoch": epoch,
                    "stage": stage,
                    "max_ma": max_ma,
                    "min_ma": min_ma,
                    "notes": notes,
                },
                db_path,
            )
            st.success("Geological age added.")
            st.rerun()

    with localities_tab:
        st.subheader("Localities")
        render_reference_list([locality_label(row) for row in list_localities(db_path)])
        with st.form("add-locality", clear_on_submit=True):
            loc_cols = st.columns([1, 1, 1])
            locality_name = loc_cols[0].text_input("Locality name")
            formation = loc_cols[1].text_input("Formation")
            member = loc_cols[2].text_input("Member")
            geo_cols = st.columns([1, 1, 1, 1])
            region = geo_cols[0].text_input("Region")
            country = geo_cols[1].text_input("Country")
            latitude = geo_cols[2].text_input("Latitude")
            longitude = geo_cols[3].text_input("Longitude")
            precision = st.text_input("Locality precision")
            notes = st.text_area("Locality notes")
            add_locality = st.form_submit_button("Add locality")
        if add_locality:
            create_locality(
                {
                    "locality_name": locality_name,
                    "formation": formation,
                    "member": member,
                    "region": region,
                    "country": country,
                    "latitude": latitude,
                    "longitude": longitude,
                    "locality_precision": precision,
                    "locality_notes": notes,
                },
                db_path,
            )
            st.success("Locality added.")
            st.rerun()

    with preparation_tab:
        st.subheader("Preparation types")
        render_reference_list([row["name"] for row in list_preparation_types(db_path)])
        with st.form("add-preparation-type", clear_on_submit=True):
            name = st.text_input("Name")
            description = st.text_area("Description")
            add_preparation = st.form_submit_button("Add preparation type")
        if add_preparation:
            if not name.strip():
                st.error("Preparation type name is required.")
                return
            create_preparation_type({"name": name, "description": description}, db_path)
            st.success("Preparation type added.")
            st.rerun()


def show_provenance_manager(db_path: Path) -> None:
    acquisitions = list_acquisitions(db_path)
    st.subheader("Acquisitions")
    render_reference_list([acquisition_label(row) for row in acquisitions])

    with st.form("add-acquisition", clear_on_submit=True):
        top = st.columns([1, 1, 1])
        acquisition_date = top[0].text_input("Acquisition date")
        source_name = top[1].text_input("Source / seller / collector")
        source_type = top[2].selectbox("Source type", SOURCE_TYPE_OPTIONS)
        seller_url = st.text_input("Seller URL")
        price = st.columns([1, 1])
        purchase_price = price[0].text_input("Purchase price")
        currency = price[1].text_input("Currency")
        confidence = st.selectbox("Ethical confidence", CONFIDENCE_OPTIONS)
        provenance_summary = st.text_area("Provenance summary")
        legality_notes = st.text_area("Legality notes")
        notes = st.text_area("Private acquisition notes")
        add_acquisition = st.form_submit_button("Add acquisition")

    if add_acquisition:
        create_acquisition(
            {
                "acquisition_date": acquisition_date,
                "source_name": source_name,
                "source_type": source_type,
                "seller_url": seller_url,
                "purchase_price": purchase_price,
                "currency": currency,
                "provenance_summary": provenance_summary,
                "legality_notes": legality_notes,
                "ethical_confidence": confidence,
                "notes": notes,
            },
            db_path,
        )
        st.success("Acquisition added.")
        st.rerun()

    if not acquisitions:
        return

    st.subheader("Acquisition documents")
    choices = {acquisition_label(row): row["id"] for row in acquisitions}
    selected = st.selectbox("Acquisition", list(choices), key="document-acquisition")
    acquisition_id = choices[selected]
    render_acquisition_documents(acquisition_id, db_path)
    with st.form("add-acquisition-document", clear_on_submit=True):
        document_path = st.text_input("Document path")
        document_type = st.text_input("Document type")
        title = st.text_input("Title")
        document_notes = st.text_area("Document notes")
        add_document = st.form_submit_button("Add document")

    if add_document:
        if not document_path.strip():
            st.error("Document path is required.")
            return
        create_acquisition_document(
            {
                "acquisition_id": acquisition_id,
                "document_path": document_path,
                "document_type": document_type,
                "title": title,
                "notes": document_notes,
            },
            db_path,
        )
        st.success("Document added.")
        st.rerun()


def show_images_and_notes(db_path: Path) -> None:
    specimens = list_specimens(db_path)
    if not specimens:
        st.info("Add a specimen before attaching images or notes.")
        return

    choices = {f"{row['collection_code']} - {row['title']}": row["id"] for row in specimens}
    selected_label = st.selectbox("Specimen", list(choices), key="media-specimen")
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

    st.subheader("Observation notes")
    render_specimen_observations(specimen["id"], db_path, allow_delete=True)
    with st.form("add-observation", clear_on_submit=True):
        observation_meta = st.columns([1, 1, 1])
        observation_date = observation_meta[0].text_input("Observation date")
        observation_type = observation_meta[1].selectbox(
            "Observation type", OBSERVATION_TYPE_OPTIONS
        )
        related_project = observation_meta[2].text_input("Related project")
        related_url = st.text_input("Related URL")
        notes = st.text_area("Notes", height=180)
        add_observation = st.form_submit_button("Add observation")

    if add_observation:
        if not notes.strip():
            st.error("Observation notes are required.")
            return
        create_observation(
            {
                "specimen_id": specimen["id"],
                "observation_date": observation_date,
                "observation_type": observation_type,
                "notes": notes,
                "related_project": related_project,
                "related_url": related_url,
            },
            db_path,
        )
        st.success("Observation added.")
        st.rerun()


def render_acquisition_documents(acquisition_id: int, db_path: Path) -> None:
    documents = list_acquisition_documents(acquisition_id, db_path)
    if not documents:
        st.info("No acquisition documents recorded.")
        return
    for document in documents:
        label = document["title"] or document["document_path"]
        with st.expander(label):
            st.code(document["document_path"], language=None)
            if document["document_type"]:
                st.caption(document["document_type"])
            if document["notes"]:
                st.write(document["notes"])
            if st.button("Delete document", key=f"delete-document-{document['id']}"):
                delete_acquisition_document(document["id"], db_path)
                st.warning("Document deleted.")
                st.rerun()


def render_specimen_images(
    specimen_id: int, db_path: Path, allow_delete: bool = False
) -> None:
    images = list_specimen_images(specimen_id, db_path)
    if not images:
        if allow_delete:
            st.info("No images recorded for this specimen.")
        return

    st.markdown("**Images**")
    columns = st.columns(3)
    for index, image in enumerate(images):
        with columns[index % 3]:
            path = resolve_image_path(image["image_path"])
            if path.exists():
                st.image(str(path), caption=image["caption"] or image["image_type"] or None)
            else:
                st.code(image["image_path"], language=None)
                if image["caption"]:
                    st.caption(image["caption"])
            details = image_details(image)
            if details:
                st.caption(details)
            if image["notes"]:
                st.markdown(image["notes"])
            if allow_delete and st.button("Delete image", key=f"delete-image-{image['id']}"):
                delete_specimen_image(image["id"], db_path)
                st.warning("Image deleted.")
                st.rerun()


def render_specimen_observations(
    specimen_id: int, db_path: Path, allow_delete: bool = False
) -> None:
    observations = list_observations(specimen_id, db_path)
    if not observations:
        if allow_delete:
            st.info("No observation notes recorded for this specimen.")
        return

    st.markdown("**Observation notes**")
    for observation in observations:
        heading = observation["observation_type"] or "Observation"
        if observation["observation_date"]:
            heading = f"{heading} - {observation['observation_date']}"
        with st.expander(heading, expanded=allow_delete):
            st.markdown(observation["notes"])
            links = []
            if observation["related_project"]:
                links.append(observation["related_project"])
            if observation["related_url"]:
                links.append(observation["related_url"])
            if links:
                st.caption(" | ".join(links))
            if allow_delete and st.button(
                "Delete observation", key=f"delete-observation-{observation['id']}"
            ):
                delete_observation(observation["id"], db_path)
                st.warning("Observation deleted.")
                st.rerun()


def specimen_inputs(prefix: str, specimen: dict | None = None, db_path: Path | None = None) -> dict:
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

    taxonomy_records = list_taxonomy(db_path)
    geological_age_records = list_geological_ages(db_path)
    locality_records = list_localities(db_path)
    preparation_records = list_preparation_types(db_path)
    acquisition_records = list_acquisitions(db_path)

    context = st.columns([1, 1, 1])
    values["taxon_id"] = context[0].selectbox(
        "Taxonomic identification",
        record_ids(taxonomy_records),
        format_func=lambda value: record_option_label(value, taxonomy_records, taxonomy_label),
        index=record_index(taxonomy_records, data.get("taxon_id")),
        key=f"{prefix}-taxon-id",
    )
    values["geological_age_id"] = context[1].selectbox(
        "Geological age / period",
        record_ids(geological_age_records),
        format_func=lambda value: record_option_label(value, geological_age_records, geological_age_label),
        index=record_index(geological_age_records, data.get("geological_age_id")),
        key=f"{prefix}-age-id",
    )
    values["locality_id"] = context[2].selectbox(
        "Formation or locality",
        record_ids(locality_records),
        format_func=lambda value: record_option_label(value, locality_records, locality_label),
        index=record_index(locality_records, data.get("locality_id")),
        key=f"{prefix}-locality-id",
    )
    place = st.columns([1, 1, 1])
    locality = get_locality(values["locality_id"], db_path)
    place[0].text_input(
        "Country / region",
        value=locality["country"] if locality and locality["country"] else "",
        key=f"{prefix}-country-display",
        disabled=True,
    )
    values["storage_location"] = place[1].text_input(
        "Storage location", value=data.get("storage_location", ""), key=f"{prefix}-storage"
    )
    values["preparation_type_id"] = place[2].selectbox(
        "Preparation type",
        record_ids(preparation_records),
        format_func=lambda value: record_option_label(value, preparation_records, lambda row: row["name"]),
        index=record_index(preparation_records, data.get("preparation_type_id")),
        key=f"{prefix}-preparation-type-id",
    )

    provenance = st.columns([2, 1])
    values["acquisition_id"] = provenance[0].selectbox(
        "Acquisition / provenance",
        record_ids(acquisition_records),
        format_func=lambda value: record_option_label(value, acquisition_records, acquisition_label),
        index=record_index(acquisition_records, data.get("acquisition_id")),
        key=f"{prefix}-acquisition-id",
    )
    values["public_visible"] = provenance[1].checkbox(
        "Public record",
        value=bool(data.get("public_visible", False)),
        key=f"{prefix}-public-visible",
    )

    values["description"] = st.text_area("Description", value=data.get("description", ""), key=f"{prefix}-description")
    values["measurements"] = st.text_input("Measurements", value=data.get("measurements", ""), key=f"{prefix}-measurements")
    values["public_notes"] = st.text_area("Public notes", value=data.get("public_notes", ""), key=f"{prefix}-public")
    values["private_notes"] = st.text_area("Private notes", value=data.get("private_notes", ""), key=f"{prefix}-private")
    values["field_notes_links"] = st.text_area(
        "Field Notes links", value=data.get("field_notes_links", ""), key=f"{prefix}-links"
    )

    return {field: values.get(field, "") for field in SPECIMEN_FIELDS}


def save_uploaded_image(uploaded_file, specimen: dict) -> str:
    """Save an uploaded Streamlit file and return its stored path."""

    storage_dir = image_dir()
    storage_dir.mkdir(parents=True, exist_ok=True)
    collection_code = safe_filename(str(specimen["collection_code"]))
    original_name = safe_filename(uploaded_file.name)
    destination = unique_path(storage_dir / f"{collection_code}_{original_name}")
    destination.write_bytes(uploaded_file.getbuffer())
    try:
        return str(destination.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(destination)


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    cleaned = cleaned.strip(".-")
    return cleaned or "image"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    for counter in range(1, 1000):
        candidate = path.with_name(f"{stem}-{counter}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not create a unique image filename.")


def resolve_image_path(image_path: str) -> Path:
    path = Path(image_path).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def image_details(image: dict) -> str:
    parts = [
        image["image_type"],
        image["photographer"],
        image["date_taken"],
        image["licence"],
    ]
    return " | ".join(str(part) for part in parts if part)


def render_reference_list(labels: list[str]) -> None:
    if not labels:
        st.info("No records yet.")
        return
    for label in labels[:25]:
        st.write(label)
    if len(labels) > 25:
        st.caption(f"{len(labels) - 25} more records not shown.")


def record_ids(records: list[dict]) -> list[int | None]:
    return [None, *[record["id"] for record in records]]


def record_index(records: list[dict], current_id: object) -> int:
    if current_id in {None, ""}:
        return 0
    ids = [record["id"] for record in records]
    try:
        return ids.index(int(current_id)) + 1
    except (ValueError, TypeError):
        return 0


def record_option_label(value: int | None, records: list[dict], label_func) -> str:
    if value is None:
        return "Not recorded"
    for record in records:
        if record["id"] == value:
            return label_func(record)
    return "Not recorded"


def taxonomy_label(taxon: dict | None) -> str:
    if not taxon:
        return ""
    scientific_name = " ".join(
        part for part in [taxon["genus"], taxon["species"]] if part
    )
    higher_taxonomy = " / ".join(
        part
        for part in [
            taxon["kingdom"],
            taxon["phylum"],
            taxon["class_name"],
            taxon["order_name"],
            taxon["family"],
        ]
        if part
    )
    base = scientific_name or taxon["identification_notes"] or higher_taxonomy
    confidence = taxon["identification_confidence"]
    if confidence and confidence != "Unknown":
        return f"{base} ({confidence})"
    return base or "Unnamed taxon"


def locality_label(locality: dict | None) -> str:
    if not locality:
        return ""
    place = ", ".join(
        part
        for part in [locality["locality_name"], locality["region"], locality["country"]]
        if part
    )
    stratigraphy = " / ".join(
        part for part in [locality["formation"], locality["member"]] if part
    )
    if place and stratigraphy:
        return f"{place} - {stratigraphy}"
    return place or stratigraphy or "Unnamed locality"


def geological_age_label(age: dict | None) -> str:
    if not age:
        return ""
    parts = [age["era"], age["period"], age["epoch"], age["stage"]]
    label = " / ".join(part for part in parts if part)
    range_label = ""
    if age["max_ma"] is not None or age["min_ma"] is not None:
        range_label = f" ({_blank(age['max_ma'])}-{_blank(age['min_ma'])} Ma)"
    return f"{label or 'Unnamed age'}{range_label}"


def acquisition_label(acquisition: dict | None) -> str:
    if not acquisition:
        return ""
    parts = [
        acquisition["source_name"],
        acquisition["source_type"],
        acquisition["acquisition_date"],
    ]
    label = " - ".join(part for part in parts if part)
    confidence = acquisition["ethical_confidence"]
    if confidence and confidence != "Unknown":
        label = f"{label} ({confidence})" if label else confidence
    return label or "Unnamed acquisition"


def _blank(value: object) -> str:
    return str(value) if value else "Not recorded"


if __name__ == "__main__":
    main()
