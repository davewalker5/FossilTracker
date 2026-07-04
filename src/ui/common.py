"""Shared Streamlit UI helpers for Fossil Tracker."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

from fossil_tracker.config import PROJECT_ROOT, document_dir, image_dir
from fossil_tracker.db import (
    SPECIMEN_FIELDS,
    delete_acquisition_document,
    delete_observation,
    delete_related_link,
    delete_specimen_image,
    delete_specimen_measurement,
    get_acquisition,
    get_geological_age,
    get_locality,
    list_acquisition_documents,
    list_geological_ages,
    list_localities,
    list_observations,
    list_preparation_types,
    list_related_links,
    list_specimen_images,
    list_specimen_measurements,
    list_taxonomy,
    next_collection_code,
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

def render_acquisition_documents(acquisition_id: int, db_path: Path) -> None:
    """Render documents linked to one acquisition.

    :param acquisition_id: Acquisition primary key.
    :param db_path: SQLite database path.
    """

    documents = list_acquisition_documents(acquisition_id, db_path)
    if not documents:
        st.info("No documents recorded.")
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
    """Render images linked to one specimen.

    :param specimen_id: Specimen primary key.
    :param db_path: SQLite database path.
    :param allow_delete: Whether delete buttons should be shown.
    """

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
    """Render observation notes linked to one specimen.

    :param specimen_id: Specimen primary key.
    :param db_path: SQLite database path.
    :param allow_delete: Whether delete buttons should be shown.
    """

    observations = list_observations(specimen_id, db_path)
    if not observations:
        if allow_delete:
            st.info("No observation notes recorded for this specimen.")
        return

    st.markdown("**Notes**")
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
            st.caption("Public" if observation["public_visible"] else "Private")
            if allow_delete and st.button(
                "Delete observation", key=f"delete-observation-{observation['id']}"
            ):
                delete_observation(observation["id"], db_path)
                st.warning("Observation deleted.")
                st.rerun()


def render_specimen_measurements(
    specimen_id: int, db_path: Path, allow_delete: bool = False
) -> None:
    """Render measurements linked to one specimen.

    :param specimen_id: Specimen primary key.
    :param db_path: SQLite database path.
    :param allow_delete: Whether delete controls should be shown.
    """

    measurements = list_specimen_measurements(specimen_id, db_path)
    if not measurements:
        if allow_delete:
            st.info("No measurements recorded for this specimen.")
        return

    st.markdown("**Measurements**")
    for measurement in measurements:
        label = (
            f"{measurement['measurement_name']}: "
            f"{measurement['value']} {measurement['measurement_unit']}"
        )
        if allow_delete:
            value_col, action_col = st.columns([5, 1])
            value_col.write(label)
            if action_col.button("Delete", key=f"delete-measurement-{measurement['id']}"):
                st.session_state["pending_measurement_delete"] = measurement["id"]
                st.rerun()

            if st.session_state.get("pending_measurement_delete") == measurement["id"]:
                confirm_col, cancel_col = st.columns([1, 1])
                if confirm_col.button("Confirm delete", key=f"confirm-measurement-{measurement['id']}"):
                    delete_specimen_measurement(measurement["id"], db_path)
                    st.session_state.pop("pending_measurement_delete", None)
                    st.warning("Measurement deleted.")
                    st.rerun()
                if cancel_col.button("Cancel", key=f"cancel-measurement-{measurement['id']}"):
                    st.session_state.pop("pending_measurement_delete", None)
                    st.rerun()
        else:
            st.write(label)


def render_related_links(
    specimen_id: int, db_path: Path, allow_delete: bool = False
) -> None:
    """Render Field Notes links linked to one specimen.

    :param specimen_id: Specimen primary key.
    :param db_path: SQLite database path.
    :param allow_delete: Whether delete controls should be shown.
    """

    links = list_related_links(specimen_id, db_path)
    if not links:
        if allow_delete:
            st.info("No related links recorded for this specimen.")
        return

    st.markdown("**Field Notes links**")
    for link in links:
        if allow_delete:
            link_col, action_col = st.columns([5, 1])
            link_col.markdown(f"[{link['url']}]({link['url']})")
            if action_col.button("Delete", key=f"delete-related-link-{link['id']}"):
                st.session_state["pending_related_link_delete"] = link["id"]
                st.rerun()

            if st.session_state.get("pending_related_link_delete") == link["id"]:
                confirm_col, cancel_col = st.columns([1, 1])
                if confirm_col.button("Confirm delete", key=f"confirm-related-link-{link['id']}"):
                    delete_related_link(link["id"], db_path)
                    st.session_state.pop("pending_related_link_delete", None)
                    st.warning("Link deleted.")
                    st.rerun()
                if cancel_col.button("Cancel", key=f"cancel-related-link-{link['id']}"):
                    st.session_state.pop("pending_related_link_delete", None)
                    st.rerun()
        else:
            st.markdown(f"- [{link['url']}]({link['url']})")


def specimen_inputs(prefix: str, specimen: dict | None = None, db_path: Path | None = None) -> dict:
    """Render shared specimen input controls.

    :param prefix: Stable key prefix for Streamlit widgets.
    :param specimen: Existing specimen values for edit mode.
    :param db_path: Optional SQLite database path.
    :return: Values keyed by specimen field name.
    """

    data = dict(specimen or {})
    values: dict[str, object] = {}
    collection_code = data.get("collection_code", "")
    if not specimen:
        collection_code = next_collection_code(db_path)

    basic = st.columns([1, 2, 1])
    values["collection_code"] = basic[0].text_input(
        "Collection code", value=collection_code, key=f"{prefix}-collection-code"
    )
    values["title"] = basic[1].text_input("Title", value=data.get("title", ""), key=f"{prefix}-title")
    values["common_name"] = basic[2].text_input(
        "Common name", value=data.get("common_name", ""), key=f"{prefix}-common-name"
    )

    taxonomy_records = list_taxonomy(db_path)
    geological_age_records = list_geological_ages(db_path)
    locality_records = list_localities(db_path)
    preparation_records = list_preparation_types(db_path)
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

    values["acquisition_id"] = data.get("acquisition_id", "")
    values["public_visible"] = st.checkbox(
        "Public record",
        value=bool(data.get("public_visible", False)),
        key=f"{prefix}-public-visible",
    )

    values["description"] = st.text_area("Description", value=data.get("description", ""), key=f"{prefix}-description")
    return {field: values.get(field, "") for field in SPECIMEN_FIELDS}


def save_uploaded_image(uploaded_file, specimen: dict) -> str:
    """Save an uploaded Streamlit file and return its stored path.

    :param uploaded_file: Streamlit uploaded file object.
    :param specimen: Specimen row used for the filename prefix.
    :return: Project-relative path when possible, otherwise absolute path.
    """

    storage_dir = image_dir()
    storage_dir.mkdir(parents=True, exist_ok=True)
    collection_code = safe_filename(str(specimen["collection_code"]))
    original_name = safe_filename(uploaded_file.name)
    destination = unique_path(storage_dir / f"{collection_code}_{original_name}")
    destination.write_bytes(uploaded_file.getbuffer())
    try:
        # Keep default project-local uploads portable in Datasette views.
        return str(destination.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(destination)


def save_uploaded_document(uploaded_file, specimen: dict) -> str:
    """Save an uploaded acquisition document and return its stored path.

    :param uploaded_file: Streamlit uploaded file object.
    :param specimen: Specimen row used for the filename prefix.
    :return: Project-relative path when possible, otherwise absolute path.
    """

    storage_dir = document_dir()
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
    """Convert a display value into a filesystem-safe filename segment.

    :param value: Raw filename or label.
    :return: Safe filename segment.
    """

    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    cleaned = cleaned.strip(".-")
    return cleaned or "image"


def unique_path(path: Path) -> Path:
    """Return a non-existing path by adding a numeric suffix when needed.

    :param path: Preferred filesystem path.
    :return: Available filesystem path.
    """

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
    """Resolve a stored image path for display.

    :param image_path: Stored relative or absolute image path.
    :return: Absolute image path.
    """

    path = Path(image_path).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def image_details(image: dict) -> str:
    """Build a compact image metadata label.

    :param image: Image row.
    :return: Human-readable metadata string.
    """

    parts = [
        image["image_type"],
        image["photographer"],
        image["date_taken"],
        image["licence"],
    ]
    return " | ".join(str(part) for part in parts if part)


def render_reference_list(labels: list[str]) -> None:
    """Render a compact list of reference labels.

    :param labels: Labels to display.
    """

    if not labels:
        st.info("No records yet.")
        return
    for label in labels[:25]:
        st.write(label)
    if len(labels) > 25:
        st.caption(f"{len(labels) - 25} more records not shown.")


def search_result_row(specimen: dict, db_path: Path) -> dict[str, str]:
    """Build one row for the Search results table.

    :param specimen: Specimen row.
    :param db_path: SQLite database path.
    :return: Display row keyed by table column.
    """

    locality = get_locality(specimen["locality_id"], db_path)
    acquisition = get_acquisition(specimen["acquisition_id"], db_path)
    country_region = ""
    if locality:
        country_region = ", ".join(
            part for part in [locality["country"], locality["region"]] if part
        )

    return {
        "Collection Code": specimen["collection_code"] or "",
        "Title": specimen["title"] or "",
        "Common Name": specimen["common_name"] or "",
        "Country/Region": country_region,
        "Acquisition Date": acquisition["acquisition_date"] if acquisition else "",
    }


def render_search_results(specimens: list[dict], db_path: Path) -> None:
    """Render Search results with per-row edit actions.

    :param specimens: Matching specimen rows.
    :param db_path: SQLite database path.
    """

    widths = [1.2, 2.2, 1.4, 1.6, 1.2, 0.7]
    headers = [
        "Collection Code",
        "Title",
        "Common Name",
        "Country/Region",
        "Acquisition Date",
        "",
    ]
    header_cols = st.columns(widths)
    for column, header in zip(header_cols, headers, strict=True):
        column.markdown(f"**{header}**" if header else "")

    for specimen in specimens:
        row = search_result_row(specimen, db_path)
        row_cols = st.columns(widths)
        row_cols[0].write(row["Collection Code"])
        row_cols[1].write(row["Title"])
        row_cols[2].write(row["Common Name"])
        row_cols[3].write(row["Country/Region"])
        row_cols[4].write(row["Acquisition Date"])
        if row_cols[5].button("Edit", key=f"edit-search-result-{specimen['id']}"):
            st.session_state["current_specimen_id"] = specimen["id"]
            st.success("Selected for editing. Open the Edit specimen tab.")


def render_taxonomy_table(records: list[dict]) -> None:
    """Render taxonomy records as a scan-friendly table.

    :param records: Taxonomy rows to display.
    """

    if not records:
        st.info("No records yet.")
        return

    st.dataframe(
        [
            {
                "Scientific name": " ".join(
                    part for part in [row["genus"], row["species"]] if part
                )
                or "",
                "Kingdom": row["kingdom"] or "",
                "Phylum": row["phylum"] or "",
                "Class": row["class_name"] or "",
                "Order": row["order_name"] or "",
                "Family": row["family"] or "",
                "Confidence": row["identification_confidence"] or "",
                "Notes": row["identification_notes"] or "",
            }
            for row in records
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "Scientific name": st.column_config.TextColumn("Scientific name", width="medium"),
            "Notes": st.column_config.TextColumn("Notes", width="large"),
        },
    )


def render_geological_age_table(records: list[dict]) -> None:
    """Render geological age records as a scan-friendly table.

    :param records: Geological age rows to display.
    """

    if not records:
        st.info("No records yet.")
        return

    st.dataframe(
        [
            {
                "Era": row["era"] or "",
                "Period": row["period"] or "",
                "Epoch": row["epoch"] or "",
                "Stage": row["stage"] or "",
                "Max Ma": row["max_ma"] if row["max_ma"] is not None else "",
                "Min Ma": row["min_ma"] if row["min_ma"] is not None else "",
            }
            for row in records
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "Max Ma": st.column_config.NumberColumn("Max Ma", format="%.2f"),
            "Min Ma": st.column_config.NumberColumn("Min Ma", format="%.2f"),
        },
    )


def render_locality_table(records: list[dict]) -> None:
    """Render locality records as a scan-friendly table.

    :param records: Locality rows to display.
    """

    if not records:
        st.info("No records yet.")
        return

    st.dataframe(
        [
            {
                "Locality": row["locality_name"] or "",
                "Formation": row["formation"] or "",
                "Member": row["member"] or "",
                "Region": row["region"] or "",
                "Country": row["country"] or "",
                "Latitude": row["latitude"] if row["latitude"] is not None else "",
                "Longitude": row["longitude"] if row["longitude"] is not None else "",
                "Precision": row["locality_precision"] or "",
                "Notes": row["locality_notes"] or "",
            }
            for row in records
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "Latitude": st.column_config.NumberColumn("Latitude", format="%.6f"),
            "Longitude": st.column_config.NumberColumn("Longitude", format="%.6f"),
            "Notes": st.column_config.TextColumn("Notes", width="large"),
        },
    )


def render_preparation_type_table(records: list[dict]) -> None:
    """Render preparation type records as a scan-friendly table.

    :param records: Preparation type rows to display.
    """

    if not records:
        st.info("No records yet.")
        return

    st.dataframe(
        [
            {
                "Name": row["name"] or "",
                "Description": row["description"] or "",
            }
            for row in records
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn("Name", width="medium"),
            "Description": st.column_config.TextColumn("Description", width="large"),
        },
    )


def render_measurement_type_table(records: list[dict]) -> None:
    """Render measurement type records as a scan-friendly table.

    :param records: Measurement type rows to display.
    """

    if not records:
        st.info("No records yet.")
        return

    st.dataframe(
        [
            {
                "Name": row["name"] or "",
                "Unit": row["unit"] or "",
                "Description": row["description"] or "",
            }
            for row in records
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn("Name", width="medium"),
            "Unit": st.column_config.TextColumn("Unit", width="small"),
            "Description": st.column_config.TextColumn("Description", width="large"),
        },
    )


def record_ids(records: list[dict]) -> list[int | None]:
    """Return selectbox option ids with an initial blank option.

    :param records: Rows containing id values.
    :return: List of ids prefixed with None.
    """

    return [None, *[record["id"] for record in records]]


def record_index(records: list[dict], current_id: object) -> int:
    """Return the selectbox index for a current record id.

    :param records: Rows containing id values.
    :param current_id: Currently selected id.
    :return: Selectbox index.
    """

    if current_id in {None, ""}:
        return 0
    ids = [record["id"] for record in records]
    try:
        return ids.index(int(current_id)) + 1
    except (ValueError, TypeError):
        return 0


def record_option_label(value: int | None, records: list[dict], label_func) -> str:
    """Render one selectbox option label.

    :param value: Selected option id.
    :param records: Rows containing id values.
    :param label_func: Function that renders a row label.
    :return: Display label for the option.
    """

    if value is None:
        return "Not recorded"
    for record in records:
        if record["id"] == value:
            return label_func(record)
    return "Not recorded"


def option_index(options: list[str], value: object) -> int:
    """Return the index of a value in a fixed option list.

    :param options: Available options.
    :param value: Current value.
    :return: Matching index, or 0 when absent.
    """

    try:
        return options.index(str(value or ""))
    except ValueError:
        return 0


def specimen_choice_index(specimens: list[dict]) -> int:
    """Return the specimen selectbox index for the current session specimen.

    :param specimens: Specimen rows containing id values.
    :return: Selectbox index.
    """

    current_id = st.session_state.get("current_specimen_id")
    if current_id in {None, ""}:
        return 0
    ids = [row["id"] for row in specimens]
    try:
        return ids.index(int(current_id))
    except (ValueError, TypeError):
        return 0


def remember_selected_specimen(widget_key: str, choices: dict[str, int]) -> None:
    """Store the specimen id chosen in a selectbox callback.

    :param widget_key: Selectbox session-state key.
    :param choices: Mapping of selectbox labels to specimen ids.
    """

    selected_label = st.session_state.get(widget_key)
    if selected_label in choices:
        st.session_state["current_specimen_id"] = choices[selected_label]


def remember_default_specimen(selected_label: str, choices: dict[str, int]) -> None:
    """Initialize the current specimen id when no prior selection exists.

    :param selected_label: Currently selected selectbox label.
    :param choices: Mapping of selectbox labels to specimen ids.
    """

    if "current_specimen_id" not in st.session_state and selected_label in choices:
        st.session_state["current_specimen_id"] = choices[selected_label]


def validate_related_link_url(url: str) -> str | None:
    """Validate a related link URL enough to catch obvious mistakes.

    :param url: Trimmed URL value.
    :return: Error message, or None when valid.
    """

    if not url:
        return "URL is required."
    if re.search(r"\s", url):
        return "URL cannot contain spaces."
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "Enter a full URL starting with http:// or https://."
    return None


def taxonomy_label(taxon: dict | None) -> str:
    """Build a display label for a taxonomy row.

    :param taxon: Taxonomy row or None.
    :return: Display label.
    """

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
    """Build a display label for a locality row.

    :param locality: Locality row or None.
    :return: Display label.
    """

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
    """Build a display label for a geological age row.

    :param age: Geological age row or None.
    :return: Display label.
    """

    if not age:
        return ""
    parts = [age["era"], age["period"], age["epoch"], age["stage"]]
    label = " / ".join(part for part in parts if part)
    range_label = ""
    if age["max_ma"] is not None or age["min_ma"] is not None:
        range_label = f" ({_blank(age['max_ma'])}-{_blank(age['min_ma'])} Ma)"
    return f"{label or 'Unnamed age'}{range_label}"


def acquisition_label(acquisition: dict | None) -> str:
    """Build a display label for an acquisition row.

    :param acquisition: Acquisition row or None.
    :return: Display label.
    """

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
    """Render empty values consistently in the UI.

    :param value: Value to render.
    :return: String value or "Not recorded".
    """

    return str(value) if value else "Not recorded"

