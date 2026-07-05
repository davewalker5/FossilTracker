"""Render Fossil Tracker specimen exports as Markdown."""

from __future__ import annotations

import json
import os
import re
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from pathlib import Path
from typing import Any

from fossil_tracker.config import PROJECT_ROOT, image_dir

DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_TIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ][\d:.]+(?:Z|[+-]\d{2}:?\d{2})?$"
)


@dataclass(frozen=True)
class SpecimenRecord:
    """A parsed specimen export ready for publication renderers.

    :param specimen: Core specimen fields from the export payload.
    :param taxonomy: Taxonomic identification fields.
    :param geological_age: Geological age fields associated with the specimen.
    :param locality: Collection locality and formation fields.
    :param provenance: Acquisition and provenance fields.
    :param images: Image records attached to the specimen.
    :param observations: Observation or note records attached to the specimen.
    :param measurements: Measurement records attached to the specimen.
    :param related_links: External link records attached to the specimen.
    :param documents: Document records attached to the specimen.
    :return: Immutable specimen record used by Markdown renderers.
    """

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
        """Build a renderer-friendly model from a specimen JSON export.

        :param payload: Parsed JSON export containing specimen data and related sections.
        :return: Normalized specimen record for rendering.
        """

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
        """Read and parse a specimen export from disk.

        :param path: Path to the JSON export file.
        :return: Normalized specimen record for rendering.
        """

        return cls.from_export(json.loads(path.read_text(encoding="utf-8")))


def render_specimen_markdown(record: SpecimenRecord, output_path: Path | None = None) -> str:
    """Render a specimen record as GitHub/Pandoc-compatible Markdown.

    :param record: Normalized specimen record to render.
    :param output_path: Optional destination path used to make image paths relative.
    :return: Rendered Markdown document text.
    """

    output_dir = output_path.parent if output_path else None
    sections: list[str] = [
        _specimen_header(record),
        _section("specimen-summary", _summary_table(record)),
    ]

    sections.extend(
        section
        for section in [
            _section("specimen-overview", _overview(record)),
            _primary_image(record, output_dir),
            _section("specimen-measurements", _measurements(record)),
            _section("specimen-identification", _identification(record)),
            _section("specimen-geology", _geological_context(record)),
            _section("specimen-observations", _observations(record)),
            _section("specimen-provenance", _provenance(record)),
            _image_gallery(record, output_dir),
            _section("specimen-related-links", _related_links(record)),
            _section("specimen-documents", _documents(record)),
            _section("specimen-metadata", _record_metadata(record)),
        ]
        if section
    )

    body = "\n\n".join(section for section in sections if section).rstrip()
    return f'<article class="specimen-record" markdown="1">\n\n{body}\n\n</article>\n'


def render_specimen_file(input_path: Path, output_path: Path | None = None) -> Path:
    """Render one specimen JSON export to a Markdown file and return its path.

    :param input_path: Path to the specimen JSON export.
    :param output_path: Optional path for the generated Markdown file.
    :return: Path to the written Markdown file.
    """

    record = SpecimenRecord.from_json_path(input_path)
    output = output_path or input_path.with_name(f"{_output_stem(record, input_path)}.md")
    output.write_text(render_specimen_markdown(record, output), encoding="utf-8")
    return output


def _items(value: Any) -> list[dict[str, Any]]:
    """Normalize an export collection to a list of item dictionaries.

    :param value: Export value that may be a list, an ``items`` wrapper, or empty.
    :return: List containing only dictionary items.
    """

    if isinstance(value, dict):
        items = value.get("items", [])
        return [item for item in items if isinstance(item, dict)]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _specimen_header(record: SpecimenRecord) -> str:
    """Build the semantic specimen title block.

    :param record: Specimen record containing title and collection code fields.
    :return: HTML header block for the specimen.
    """

    code = _clean(record.specimen.get("collection_code"))
    title = _clean(record.specimen.get("title"))
    heading = title or code or "Specimen"
    subtitle = _specimen_subtitle(record)
    parts = ['<header class="specimen-header">']
    if code:
        parts.append(f'<p class="specimen-code">{_escape_html_text(code)}</p>')
    parts.append(f"<h1>{_escape_html_text(heading)}</h1>")
    if subtitle:
        parts.append(f'<p class="specimen-subtitle">{_escape_html_text(subtitle)}</p>')
    badges = _specimen_badges(record)
    if badges:
        parts.append(badges)
    parts.append("</header>")
    return "\n".join(parts)


def _specimen_subtitle(record: SpecimenRecord) -> str:
    """Build a concise natural-history subtitle from key context fields.

    :param record: Specimen record containing age, locality, and preparation fields.
    :return: Hyphen-separated subtitle text, or an empty string.
    """

    geological_age = _geological_age_summary(record) or _clean(record.geological_age.get("era"))
    locality = _locality_summary(record) or _clean(record.locality.get("country"))
    preparation = _clean(record.specimen.get("preparation_type"))
    return " - ".join(value for value in [geological_age, locality, preparation] if value)


def _specimen_badges(record: SpecimenRecord) -> str:
    """Build status badges for fast visual context.

    :param record: Specimen record containing age, locality, and taxonomy data.
    :return: HTML badge container, or an empty string.
    """

    badges: list[tuple[str, str]] = []
    period = _clean(record.geological_age.get("period"))
    country = _clean(record.locality.get("country"))
    locality_precision = _clean(record.locality.get("locality_precision"))

    if period:
        badges.append(("specimen-badge", period))
    if country:
        badges.append(("specimen-badge", country))
    if _identification_is_provisional(record):
        badges.append(("specimen-badge specimen-badge-warning", "Identification provisional"))
    if locality_precision:
        badges.append(
            ("specimen-badge specimen-badge-muted", f"Locality precision: {locality_precision}")
        )

    if not badges:
        return ""

    badge_items = [
        f'<span class="{classes}">{_escape_html_text(label)}</span>'
        for classes, label in badges
    ]
    return '<div class="specimen-badges">\n' + "\n".join(badge_items) + "\n</div>"


def _identification_is_provisional(record: SpecimenRecord) -> bool:
    """Infer whether the taxonomic identification should be flagged as provisional.

    :param record: Specimen record containing taxonomy data.
    :return: True when the identification is incomplete or explicitly undetermined.
    """

    taxonomy_keys = [
        "kingdom",
        "phylum",
        "class_name",
        "subclass",
        "order_name",
        "family",
        "genus",
        "species",
        "identification_notes",
    ]
    if not any(_present(record.taxonomy.get(key)) for key in taxonomy_keys):
        return False
    if _present(record.taxonomy.get("identification_notes")):
        return True
    for key in ["family", "genus", "species"]:
        value = _clean(record.taxonomy.get(key)).lower()
        if value in {"undetermined", "unknown", "indet.", "indet", "cf.", "aff."}:
            return True
    return not any(_present(record.taxonomy.get(key)) for key in ["genus", "species"])


def _summary_table(record: SpecimenRecord) -> str:
    """Render the short specimen summary table.

    :param record: Specimen record containing summary fields.
    :return: Markdown table, or an empty string when no summary fields exist.
    """

    rows = [
        ("Common name", record.specimen.get("common_name")),
        ("Preparation type", record.specimen.get("preparation_type")),
        ("Geological age", _geological_age_summary(record)),
        *_summary_locality_rows(record),
        ("Acquisition date", record.provenance.get("acquisition_date")),
    ]
    populated = [(label, value) for label, value in rows if _present(value)]
    if not populated:
        return ""
    return _table(["Field", "Value"], populated)


def _summary_locality_rows(record: SpecimenRecord) -> list[tuple[str, Any]]:
    """Render concise locality fields for the opening summary table.

    :param record: Specimen record containing locality data.
    :return: Locality fields for the opening summary table.
    """

    return [
        ("Country", record.locality.get("country")),
        ("Locality precision", record.locality.get("locality_precision")),
    ]


def _overview(record: SpecimenRecord) -> str:
    """Render the overview section from the specimen description.

    :param record: Specimen record containing the description field.
    :return: Markdown overview section, or an empty string when absent.
    """

    description = _markdown_block(record.specimen.get("description"))
    if not description:
        return ""
    return f"## Overview\n\n{description}"


def _primary_image(record: SpecimenRecord, output_dir: Path | None) -> str:
    """Render the first image as the primary image section.

    :param record: Specimen record containing image metadata.
    :param output_dir: Optional output directory used to make image paths relative.
    :return: Markdown primary image section, or an empty string when unavailable.
    """

    if not record.images:
        return ""
    image = _render_image(record.images[0], output_dir, is_primary=True)
    if not image:
        return ""
    return f"## Primary Image\n\n{image}"


def _identification(record: SpecimenRecord) -> str:
    """Render taxonomic identification fields and notes.

    :param record: Specimen record containing taxonomy data.
    :return: Markdown identification section, or an empty string when absent.
    """

    rows = []
    for label, key in [
        ("Kingdom", "kingdom"),
        ("Phylum", "phylum"),
        ("Class", "class_name"),
        ("Subclass", "subclass"),
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
        parts.append(_callout("Identification note.", notes, "specimen-note-warning"))
    return "\n\n".join(parts) if len(parts) > 1 else ""


def _geological_context(record: SpecimenRecord) -> str:
    """Render geological age and locality context fields.

    :param record: Specimen record containing geological age and locality data.
    :return: Markdown geological context section, or an empty string when absent.
    """

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
    """Render specimen measurements as a Markdown table.

    :param record: Specimen record containing measurement rows.
    :return: Markdown measurements section, or an empty string when absent.
    """

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
    """Render specimen observations grouped by observation type.

    :param record: Specimen record containing observations or notes.
    :return: Markdown observations section, or an empty string when absent.
    """

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
    """Render provenance fields and narrative notes.

    :param record: Specimen record containing provenance data.
    :return: Markdown provenance section, or an empty string when absent.
    """

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
    """Render all non-primary images as a gallery section.

    :param record: Specimen record containing image metadata.
    :param output_dir: Optional output directory used to make image paths relative.
    :return: Markdown image gallery section, or an empty string when absent.
    """

    remaining = [_render_image(image, output_dir) for image in record.images[1:]]
    remaining = [image for image in remaining if image]
    if not remaining:
        return ""
    images = "\n\n".join(remaining)
    return f"## Image Gallery\n\n{images}"


def _related_links(record: SpecimenRecord) -> str:
    """Render external related links as a Markdown list.

    :param record: Specimen record containing related link entries.
    :return: Markdown related links section, or an empty string when absent.
    """

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
    """Render attached document metadata as a Markdown table.

    :param record: Specimen record containing document entries.
    :return: Markdown documents section, or an empty string when absent.
    """

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
    """Render collection code and timestamp metadata.

    :param record: Specimen record containing metadata fields.
    :return: Markdown record metadata section, or an empty string when absent.
    """

    rows = [
        ("Collection code", record.specimen.get("collection_code")),
        ("Created date", record.specimen.get("created_at")),
        ("Last updated date", record.specimen.get("updated_at")),
    ]
    populated = [(label, value) for label, value in rows if _present(value)]
    if not populated:
        return ""
    return f"## Record Metadata\n\n{_table(['Field', 'Value'], populated)}"


def _render_image(
    image: dict[str, Any],
    output_dir: Path | None,
    *,
    is_primary: bool = False,
) -> str:
    """Render one image and its metadata as Markdown.

    :param image: Image metadata dictionary from the export.
    :param output_dir: Optional output directory used to make the image path relative.
    :param is_primary: When true, add the primary-image styling hook.
    :return: HTML figure block, or an empty string when no path exists.
    """

    stored_path = _clean(image.get("image_path") or image.get("path"))
    if not stored_path:
        return ""
    path = _markdown_image_path(stored_path, output_dir)
    caption = _clean(image.get("caption"))
    alt = caption or Path(stored_path).stem
    classes = "specimen-figure"
    if is_primary:
        classes = f"{classes} specimen-primary-image"
    parts = [
        f'<figure class="{classes}">',
        "",
        f'<img src="{_escape_html_attr(path)}" alt="{_escape_html_attr(alt)}">',
    ]
    metadata = [
        caption,
        _label_value("Type", image.get("image_type")),
        _label_value("Photographer", image.get("photographer")),
        _label_value("Licence", image.get("licence")),
        _label_value("Date", image.get("date_taken") or image.get("date")),
    ]
    metadata = [_clean(value) for value in metadata if _present(value)]
    if metadata:
        parts.extend(
            [
                "",
                "<figcaption>",
                _escape_html_text("; ".join(metadata)),
                "</figcaption>",
            ]
        )
    parts.extend(["", "</figure>"])
    return "\n".join(parts)


def _markdown_image_path(stored_path: str, output_dir: Path | None) -> str:
    """Resolve an exported image path for use in Markdown.

    :param stored_path: Image path stored in the specimen export.
    :param output_dir: Optional output directory used to make the path relative.
    :return: POSIX-style path suitable for a Markdown image link.
    """

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
    """Combine a measurement value and unit for display.

    :param measurement: Measurement metadata dictionary from the export.
    :return: Display text containing the value, unit, both, or an empty string.
    """

    value = _clean(measurement.get("value"))
    unit = _clean(measurement.get("measurement_unit") or measurement.get("unit"))
    if value and unit:
        return f"{value} {unit}"
    return value or unit


def _geological_age_summary(record: SpecimenRecord) -> str:
    """Build a concise geological age summary.

    :param record: Specimen record containing geological age fields.
    :return: Slash-separated period, epoch, and stage text.
    """

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
    """Build a concise locality summary.

    :param record: Specimen record containing locality fields.
    :return: Comma-separated locality, region, and country text.
    """

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
    """Format maximum and minimum age values as a geological range.

    :param age: Geological age dictionary containing optional ``max_ma`` and ``min_ma``.
    :return: Display text for the geological age range.
    """

    max_ma = _clean(age.get("max_ma"))
    min_ma = _clean(age.get("min_ma"))
    if max_ma and min_ma:
        return f"{max_ma}-{min_ma} Ma"
    if max_ma:
        return f"from {max_ma} Ma"
    if min_ma:
        return f"to {min_ma} Ma"
    return ""


def _section(class_name: str, content: str) -> str:
    """Wrap generated content in a semantic section for catalogue styling.

    :param class_name: CSS class to apply to the section.
    :param content: Markdown or HTML content to wrap.
    :return: HTML section containing the content, or an empty string.
    """

    if not content:
        return ""
    return f'<section class="{class_name}" markdown="1">\n\n{content}\n\n</section>'


def _callout(title: str, body: str, class_name: str = "") -> str:
    """Render interpretive text as a styled callout block.

    :param title: Short callout heading.
    :param body: Markdown body text to place in the callout.
    :param class_name: Optional additional CSS class.
    :return: HTML callout block.
    """

    classes = "specimen-note"
    if class_name:
        classes = f"{classes} {class_name}"
    return (
        f'<div class="{classes}" markdown="1">\n'
        f"<strong>{_escape_html_text(title)}</strong>\n\n"
        f"{body}\n"
        "</div>"
    )


def _table(
    headers: list[str],
    rows: list[tuple[Any, ...]],
    align_right: set[int] | None = None,
) -> str:
    """Render a Markdown table from headers and rows.

    :param headers: Column labels for the table header.
    :param rows: Row values to render beneath the header.
    :param align_right: Optional set of column indexes to right-align.
    :return: Markdown table text.
    """

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
    """Format a label and value pair for inline metadata.

    :param label: Label to display before the value.
    :param value: Value to clean and display.
    :return: ``"Label: value"`` text, or an empty string when the value is absent.
    """

    cleaned = _display_value(value)
    return f"{label}: {cleaned}" if cleaned else ""


def _markdown_block(value: Any) -> str:
    """Clean a value for use as a Markdown block.

    :param value: Value that may contain Markdown text.
    :return: Stripped text, or an empty string when the value is absent.
    """

    return str(value).strip() if _present(value) else ""


def _clean(value: Any) -> str:
    """Convert a value to stripped text.

    :param value: Value to normalize.
    :return: Stripped string value, or an empty string for ``None``.
    """

    if value is None:
        return ""
    return str(value).strip()


def _display_value(value: Any) -> str:
    """Convert a value to rendered display text.

    :param value: Value to normalize and format for Markdown output.
    :return: Display string with recognized dates formatted for readers.
    """

    if isinstance(value, datetime):
        return value.strftime("%d-%b-%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d-%b-%Y")

    cleaned = _clean(value)
    if DATE_ONLY_RE.match(cleaned):
        try:
            return date.fromisoformat(cleaned).strftime("%d-%b-%Y")
        except ValueError:
            return cleaned
    if DATE_TIME_RE.match(cleaned):
        try:
            return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).strftime(
                "%d-%b-%Y %H:%M"
            )
        except ValueError:
            return cleaned
    return cleaned


def _present(value: Any) -> bool:
    """Check whether a value should be rendered.

    :param value: Value to test for renderable content.
    :return: ``True`` when the value is non-empty, otherwise ``False``.
    """

    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _escape_table_cell(value: Any) -> str:
    """Escape a value for safe use in a Markdown table cell.

    :param value: Cell value to clean and escape.
    :return: Single-line table cell text with pipe characters escaped.
    """

    return " ".join(_display_value(value).splitlines()).replace("|", "\\|")


def _escape_image_text(value: str) -> str:
    """Escape text for use in a Markdown image label.

    :param value: Alt text or caption value.
    :return: Text with Markdown image label delimiters escaped.
    """

    return value.replace("[", "\\[").replace("]", "\\]")


def _escape_html_text(value: Any) -> str:
    """Escape text for safe use in an HTML text node.

    :param value: Value to normalize and escape.
    :return: HTML-escaped text.
    """

    return escape(_display_value(value), quote=False)


def _escape_html_attr(value: Any) -> str:
    """Escape text for safe use in an HTML attribute.

    :param value: Value to normalize and escape.
    :return: HTML-escaped attribute value.
    """

    return escape(_display_value(value), quote=True)


def _output_stem(record: SpecimenRecord, input_path: Path) -> str:
    """Choose the output filename stem for a rendered specimen file.

    :param record: Specimen record containing an optional collection code.
    :param input_path: Source JSON path used as a fallback stem.
    :return: Collection code or input filename stem.
    """

    return _clean(record.specimen.get("collection_code")) or input_path.stem
