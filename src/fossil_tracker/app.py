"""Streamlit user interface for the Fossil Tracker core register."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import streamlit as st

from fossil_tracker.config import APP_NAME, DEFAULT_IMAGE_DIR, PROJECT_ROOT, database_path
from fossil_tracker.db import (
    SPECIMEN_FIELDS,
    apply_migrations,
    create_observation,
    create_specimen_image,
    create_specimen,
    delete_observation,
    delete_specimen_image,
    delete_specimen,
    export_csv,
    get_specimen,
    list_observations,
    list_specimen_images,
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
IMAGE_TYPE_OPTIONS = ["", "Overall", "Close-up", "Matrix", "Label", "Comparison", "Other"]
OBSERVATION_TYPE_OPTIONS = ["", "General", "Morphology", "Condition", "Measurement", "Research note", "Other"]


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

    tab_register, tab_add, tab_edit, tab_notes = st.tabs(
        ["Register", "Add specimen", "Edit specimen", "Images and notes"]
    )

    with tab_register:
        show_register(db_path)

    with tab_add:
        show_add_form(db_path)

    with tab_edit:
        show_edit_form(db_path)

    with tab_notes:
        show_images_and_notes(db_path)


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
            render_specimen_images(specimen["id"], db_path)
            render_specimen_observations(specimen["id"], db_path)


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
    values["field_notes_links"] = st.text_area(
        "Field Notes links", value=data.get("field_notes_links", ""), key=f"{prefix}-links"
    )

    return {field: values.get(field, "") for field in SPECIMEN_FIELDS}


def save_uploaded_image(uploaded_file, specimen: dict) -> str:
    """Save an uploaded Streamlit file and return a project-relative path."""

    DEFAULT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    collection_code = safe_filename(str(specimen["collection_code"]))
    original_name = safe_filename(uploaded_file.name)
    destination = unique_path(DEFAULT_IMAGE_DIR / f"{collection_code}_{original_name}")
    destination.write_bytes(uploaded_file.getbuffer())
    return str(destination.relative_to(PROJECT_ROOT))


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


def _blank(value: object) -> str:
    return str(value) if value else "Not recorded"


if __name__ == "__main__":
    main()
