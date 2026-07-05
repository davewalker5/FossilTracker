"""Render Fossil Tracker specimen exports as Markdown."""

from __future__ import annotations

import json
import os
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fossil_tracker.config import PROJECT_ROOT, image_dir


@dataclass(frozen=True)
class SpecimenRecord:
    """A parsed specimen export ready for publication renderers."""

    specimen: dict[str, Any]
    taxonomy: dict[str, Any]
    geological_age: dict[str, Any]
    locality: dict[str, Any]
    provenance: dict[str, Any]
    images: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    measurements: list[dict[str, Any]]
    related_links: list[dict[str, Any]]
    documents: list[dict[str, Any]]

    @classmethod
    def from_export(cls, payload: dict[str, Any]) -> "SpecimenRecord":
        """Build a renderer-friendly model from a specimen JSON export."""

        specimen = payload.get("specimen") or {}
        return cls(
            specimen=specimen,
            taxonomy=payload.get("taxonomy") or {},
            geological_age=specimen.get("geological_age") or payload.get("geological_age") or {},
            locality=specimen.get("locality") or payload.get("locality") or {},
            provenance=payload.get("provenance") or {},
            images=_items(payload.get("images")),
            observations=_items(payload.get("notes") or payload.get("observations")),
            measurements=_items(payload.get("measurements")),
            related_links=_items(payload.get("related links") or payload.get("related_links")),
            documents=_items(payload.get("documents")),
        )

    @classmethod
    def from_json_path(cls, path: Path) -> "SpecimenRecord":
        """Read and parse a specimen export from disk."""

        return cls.from_export(json.loads(path.read_text(encoding="utf-8")))


def render_specimen_markdown(record: SpecimenRecord, output_path: Path | None = None) -> str:
    """Render a specimen record as GitHub/Pandoc-compatible Markdown."""

    output_dir = output_path.parent if output_path else None
    sections: list[str] = [_title(record), _summary_table(record)]

    sections.extend(
        section
        for section in [
            _overview(record),
            _primary_image(record, output_dir),
            _identification(record),
            _geological_context(record),
            _measurements(record),
            _observations(record),
            _provenance(record),
            _image_gallery(record, output_dir),
            _related_links(record),
            _documents(record),
            _record_metadata(record),
        ]
        if section
    )

    return "\n\n".join(section for section in sections if section).rstrip() + "\n"


def render_specimen_file(input_path: Path, output_path: Path | None = None) -> Path:
    """Render one specimen JSON export to a Markdown file and return its path."""

    record = SpecimenRecord.from_json_path(input_path)
    output = output_path or input_path.with_name(f"{_output_stem(record, input_path)}.md")
    output.write_text(render_specimen_markdown(record, output), encoding="utf-8")
    return output


def _items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        items = value.get("items", [])
        return [item for item in items if isinstance(item, dict)]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _title(record: SpecimenRecord) -> str:
    code = _clean(record.specimen.get("collection_code"))
    title = _clean(record.specimen.get("title"))
    if code and title:
        return f"# {code} \u2014 {title}"
    return f"# {code or title or 'Specimen'}"


def _summary_table(record: SpecimenRecord) -> str:
    rows = [
        ("Common name", record.specimen.get("common_name")),
        ("Preparation type", record.specimen.get("preparation_type")),
        ("Geological age", _geological_age_summary(record)),
        ("Locality", _locality_summary(record)),
        ("Acquisition date", record.provenance.get("acquisition_date")),
    ]
    populated = [(label, value) for label, value in rows if _present(value)]
    if not populated:
        return ""
    return _table(["Field", "Value"], populated)


def _overview(record: SpecimenRecord) -> str:
    description = _markdown_block(record.specimen.get("description"))
    if not description:
        return ""
    return f"## Overview\n\n{description}"


def _primary_image(record: SpecimenRecord, output_dir: Path | None) -> str:
    if not record.images:
        return ""
    image = _render_image(record.images[0], output_dir)
    if not image:
        return ""
    return f"## Primary Image\n\n{image}"


def _identification(record: SpecimenRecord) -> str:
    rows = []
    for label, key in [
        ("Kingdom", "kingdom"),
        ("Phylum", "phylum"),
        ("Class", "class_name"),
        ("Order", "order_name"),
        ("Family", "family"),
        ("Genus", "genus"),
        ("Species", "species"),
    ]:
        value = record.taxonomy.get(key)
        if _present(value):
            rows.append((label, value))

    notes = _markdown_block(record.taxonomy.get("identification_notes"))
    parts = ["## Identification"]
    if rows:
        parts.append(_table(["Rank", "Taxon"], rows))
    if notes:
        parts.append(notes)
    return "\n\n".join(parts) if len(parts) > 1 else ""


def _geological_context(record: SpecimenRecord) -> str:
    age_range = _age_range(record.geological_age)
    rows = [
        ("Era", record.geological_age.get("era")),
        ("Period", record.geological_age.get("period")),
        ("Epoch", record.geological_age.get("epoch")),
        ("Stage", record.geological_age.get("stage")),
        ("Geological age range", age_range),
        ("Formation", record.locality.get("formation")),
        ("Member", record.locality.get("member")),
        ("Region", record.locality.get("region")),
        ("Country", record.locality.get("country")),
        ("Locality precision", record.locality.get("locality_precision")),
    ]
    populated = [(label, value) for label, value in rows if _present(value)]
    if not populated:
        return ""
    return f"## Geological Context\n\n{_table(['Field', 'Value'], populated)}"


def _measurements(record: SpecimenRecord) -> str:
    rows = []
    for measurement in record.measurements:
        label = measurement.get("measurement_type") or measurement.get("measurement_name")
        value = _measurement_value(measurement)
        if _present(label) and _present(value):
            rows.append((label, value))
    if not rows:
        return ""
    return f"## Measurements\n\n{_table(['Measurement', 'Value'], rows, align_right={1})}"


def _observations(record: SpecimenRecord) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for observation in record.observations:
        notes = _markdown_block(observation.get("notes"))
        if not notes:
            continue
        observation_type = _clean(observation.get("observation_type")) or "Observation"
        grouped.setdefault(observation_type, []).append(notes)

    if not grouped:
        return ""

    parts = ["## Observations"]
    for observation_type, notes_items in grouped.items():
        parts.append(f"### {observation_type}\n\n" + "\n\n".join(notes_items))
    return "\n\n".join(parts)


def _provenance(record: SpecimenRecord) -> str:
    rows = [
        ("Acquisition date", record.provenance.get("acquisition_date")),
        ("Source", record.provenance.get("source_name")),
        ("Source type", record.provenance.get("source_type")),
        ("Purchase price", record.provenance.get("purchase_price")),
        ("Currency", record.provenance.get("currency")),
        ("Ethical confidence", record.provenance.get("ethical_confidence")),
    ]
    populated = [(label, value) for label, value in rows if _present(value)]
    notes = [
        _markdown_block(record.provenance.get("provenance_summary")),
        _markdown_block(record.provenance.get("legality_notes")),
        _markdown_block(record.provenance.get("notes")),
    ]
    notes = [note for note in notes if note]
    if not populated and not notes:
        return ""

    parts = ["## Provenance"]
    if populated:
        parts.append(_table(["Field", "Value"], populated))
    parts.extend(notes)
    return "\n\n".join(parts)


def _image_gallery(record: SpecimenRecord, output_dir: Path | None) -> str:
    remaining = [_render_image(image, output_dir) for image in record.images[1:]]
    remaining = [image for image in remaining if image]
    if not remaining:
        return ""
    images = "\n\n".join(remaining)
    return f"## Image Gallery\n\n{images}"


def _related_links(record: SpecimenRecord) -> str:
    items = []
    for link in record.related_links:
        url = _clean(link.get("url"))
        if not url:
            continue
        title = _clean(link.get("title")) or url
        description = _clean(link.get("description"))
        item = f"- [{title}]({url})"
        if description:
            item = f"{item} - {description}"
        items.append(item)
    if not items:
        return ""
    return "## Related Links\n\n" + "\n".join(items)


def _documents(record: SpecimenRecord) -> str:
    rows = []
    for document in record.documents:
        title = document.get("title")
        document_type = document.get("document_type")
        filename = document.get("filename") or document.get("document_path")
        row = (title, document_type, filename)
        if any(_present(value) for value in row):
            rows.append(row)
    if not rows:
        return ""
    return f"## Documents\n\n{_table(['Title', 'Document type', 'Filename'], rows)}"


def _record_metadata(record: SpecimenRecord) -> str:
    rows = [
        ("Collection code", record.specimen.get("collection_code")),
        ("Created date", record.specimen.get("created_at")),
        ("Last updated date", record.specimen.get("updated_at")),
    ]
    populated = [(label, value) for label, value in rows if _present(value)]
    if not populated:
        return ""
    return f"## Record Metadata\n\n{_table(['Field', 'Value'], populated)}"


def _render_image(image: dict[str, Any], output_dir: Path | None) -> str:
    stored_path = _clean(image.get("image_path") or image.get("path"))
    if not stored_path:
        return ""
    path = _markdown_image_path(stored_path, output_dir)
    caption = _clean(image.get("caption"))
    alt = caption or Path(stored_path).stem
    parts = [f"![{_escape_image_text(alt)}]({path})"]
    metadata = [
        caption,
        _label_value("Type", image.get("image_type")),
        _label_value("Photographer", image.get("photographer")),
        _label_value("Licence", image.get("licence")),
        _label_value("Date", image.get("date_taken") or image.get("date")),
    ]
    metadata = [_clean(value) for value in metadata if _present(value)]
    if metadata:
        parts.append(f"*{'; '.join(metadata)}*")
    return "\n\n".join(parts)


def _markdown_image_path(stored_path: str, output_dir: Path | None) -> str:
    if output_dir is None:
        return stored_path

    path = Path(stored_path).expanduser()
    if path.is_absolute():
        resolved_path = path
    elif path.parent == Path("."):
        resolved_path = image_dir() / path
    else:
        resolved_path = PROJECT_ROOT / path

    try:
        return Path(os.path.relpath(resolved_path, output_dir)).as_posix()
    except ValueError:
        return resolved_path.as_posix()


def _measurement_value(measurement: dict[str, Any]) -> str:
    value = _clean(measurement.get("value"))
    unit = _clean(measurement.get("measurement_unit") or measurement.get("unit"))
    if value and unit:
        return f"{value} {unit}"
    return value or unit


def _geological_age_summary(record: SpecimenRecord) -> str:
    return " / ".join(
        value
        for value in [
            _clean(record.geological_age.get("period")),
            _clean(record.geological_age.get("epoch")),
            _clean(record.geological_age.get("stage")),
        ]
        if value
    )


def _locality_summary(record: SpecimenRecord) -> str:
    return ", ".join(
        value
        for value in [
            _clean(record.locality.get("locality_name")),
            _clean(record.locality.get("region")),
            _clean(record.locality.get("country")),
        ]
        if value
    )


def _age_range(age: dict[str, Any]) -> str:
    max_ma = _clean(age.get("max_ma"))
    min_ma = _clean(age.get("min_ma"))
    if max_ma and min_ma:
        return f"{max_ma}-{min_ma} Ma"
    if max_ma:
        return f"from {max_ma} Ma"
    if min_ma:
        return f"to {min_ma} Ma"
    return ""


def _table(
    headers: list[str],
    rows: list[tuple[Any, ...]],
    align_right: set[int] | None = None,
) -> str:
    align_right = align_right or set()
    header_row = "| " + " | ".join(_escape_table_cell(header) for header in headers) + " |"
    separator_cells = [("---:" if index in align_right else "---") for index in range(len(headers))]
    separator_row = "| " + " | ".join(separator_cells) + " |"
    body_rows = [
        "| " + " | ".join(_escape_table_cell(value) for value in row) + " |"
        for row in rows
    ]
    return "\n".join([header_row, separator_row, *body_rows])


def _label_value(label: str, value: Any) -> str:
    cleaned = _clean(value)
    return f"{label}: {cleaned}" if cleaned else ""


def _markdown_block(value: Any) -> str:
    return str(value).strip() if _present(value) else ""


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _escape_table_cell(value: Any) -> str:
    return " ".join(_clean(value).splitlines()).replace("|", "\\|")


def _escape_image_text(value: str) -> str:
    return value.replace("[", "\\[").replace("]", "\\]")


def _output_stem(record: SpecimenRecord, input_path: Path) -> str:
    return _clean(record.specimen.get("collection_code")) or input_path.stem
