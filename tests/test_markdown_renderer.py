"""Markdown specimen renderer tests."""

from __future__ import annotations

import json
from pathlib import Path

from fossil_tracker.markdown_renderer import (
    SpecimenRecord,
    render_specimen_file,
    render_specimen_markdown,
)
from fossil_tracker.config import PROJECT_ROOT


def specimen_export() -> dict:
    return {
        "specimen": {
            "collection_code": "FT-0001",
            "title": "Polished Madagascan Ammonite",
            "common_name": "Ammonite",
            "description": "Polished cross-section.\n\n- Chamber structure visible",
            "preparation_type": "Split and polished",
            "geological_age": {
                "era": "Mesozoic",
                "period": "Jurassic",
                "epoch": "Early Jurassic",
                "stage": "Toarcian",
                "max_ma": 183.7,
                "min_ma": 174.1,
            },
            "locality": {
                "locality_name": "Exact locality unknown",
                "formation": "Unknown",
                "member": "",
                "region": "Mahajanga",
                "country": "Madagascar",
                "locality_precision": "Region only",
            },
            "created_at": "2026-07-01T10:00:00+00:00",
            "updated_at": "2026-07-04T10:00:00+00:00",
        },
        "taxonomy": {
            "kingdom": "Animalia",
            "phylum": "Mollusca",
            "class_name": "Cephalopoda",
            "order_name": "Ammonitida",
            "family": "Undetermined",
            "identification_notes": "**Likely** ammonoid; genus pending.",
        },
        "provenance": {
            "acquisition_date": "2026-07-03",
            "source_name": "Example dealer",
            "source_type": "Dealer",
            "purchase_price": "25.00",
            "currency": "GBP",
            "ethical_confidence": "Medium",
            "provenance_summary": "Dealer supplied as Madagascan material.",
        },
        "images": {
            "items": [
                {
                    "image_path": "images/FT-0001-hero.jpg",
                    "image_type": "Overall",
                    "caption": "Overall polished face",
                    "photographer": "D. Walker",
                    "licence": "Private",
                    "date_taken": "2026-07-03",
                },
                {
                    "image_path": "images/FT-0001-detail.jpg",
                    "image_type": "Macro",
                    "caption": "Suture detail",
                },
            ]
        },
        "notes": {
            "items": [
                {
                    "observation_type": "Morphology",
                    "notes": "Ribbing is visible around the outer whorl.",
                },
                {
                    "observation_type": "Preservation",
                    "notes": "- Polished face\n- Matrix retained",
                },
            ]
        },
        "measurements": {
            "items": [
                {
                    "measurement_type": "Diameter",
                    "value": "29",
                    "measurement_unit": "mm",
                }
            ]
        },
        "related links": {
            "items": [
                {
                    "title": "Field note",
                    "url": "https://fieldnotes.example/ammonite",
                    "description": "Contextual note.",
                }
            ]
        },
        "documents": {
            "items": [
                {
                    "title": "Receipt",
                    "document_type": "Receipt",
                    "document_path": "documents/FT-0001-receipt.pdf",
                }
            ]
        },
    }


def test_render_specimen_markdown_contains_publication_sections() -> None:
    markdown = render_specimen_markdown(SpecimenRecord.from_export(specimen_export()))

    assert "# FT-0001 \u2014 Polished Madagascan Ammonite" in markdown
    assert "| Common name | Ammonite |" in markdown
    assert "## Overview\n\nPolished cross-section.\n\n- Chamber structure visible" in markdown
    assert "![Overall polished face](images/FT-0001-hero.jpg)" in markdown
    assert "*Overall polished face; Type: Overall; Photographer: D. Walker; Licence: Private; Date: 2026-07-03*" in markdown
    assert "| Class | Cephalopoda |" in markdown
    assert "**Likely** ammonoid; genus pending." in markdown
    assert "| Geological age range | 183.7-174.1 Ma |" in markdown
    assert "| Formation | Unknown |" in markdown
    assert "| Diameter | 29 mm |" in markdown
    assert "### Morphology\n\nRibbing is visible around the outer whorl." in markdown
    assert "### Preservation\n\n- Polished face\n- Matrix retained" in markdown
    assert "| Ethical confidence | Medium |" in markdown
    assert "## Image Gallery\n\n![Suture detail](images/FT-0001-detail.jpg)" in markdown
    assert "- [Field note](https://fieldnotes.example/ammonite) - Contextual note." in markdown
    assert "| Receipt | Receipt | documents/FT-0001-receipt.pdf |" in markdown
    assert "| Last updated date | 2026-07-04T10:00:00+00:00 |" in markdown


def test_render_specimen_markdown_omits_empty_sections() -> None:
    markdown = render_specimen_markdown(
        SpecimenRecord.from_export(
            {
                "specimen": {
                    "collection_code": "FT-0002",
                    "title": "Sparse record",
                }
            }
        )
    )

    assert "## Overview" not in markdown
    assert "## Measurements" not in markdown
    assert "## Related Links" not in markdown
    assert "| Collection code | FT-0002 |" in markdown


def test_render_specimen_file_writes_collection_code_markdown(tmp_path: Path) -> None:
    input_path = tmp_path / "export.json"
    input_path.write_text(json.dumps(specimen_export()), encoding="utf-8")

    output_path = render_specimen_file(input_path)

    assert output_path == tmp_path / "FT-0001.md"
    assert output_path.read_text(encoding="utf-8").startswith(
        "# FT-0001 \u2014 Polished Madagascan Ammonite\n"
    )


def test_render_specimen_file_resolves_configured_image_folder(
    tmp_path: Path, monkeypatch
) -> None:
    image_folder = tmp_path / "images"
    export_folder = tmp_path / "export"
    export_folder.mkdir()
    monkeypatch.setenv("FOSSIL_TRACKER_IMAGES", str(image_folder))
    payload = specimen_export()
    payload["images"]["items"][0]["image_path"] = "FT-0001-hero.jpg"
    input_path = export_folder / "FT-0001.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    output_path = render_specimen_file(input_path)

    assert "![Overall polished face](../images/FT-0001-hero.jpg)" in output_path.read_text(
        encoding="utf-8"
    )


def test_render_specimen_markdown_resolves_default_image_folder(monkeypatch) -> None:
    monkeypatch.delenv("FOSSIL_TRACKER_IMAGES", raising=False)
    payload = specimen_export()
    payload["images"]["items"][0]["image_path"] = "FT-0001-hero.jpg"
    record = SpecimenRecord.from_export(payload)

    markdown = render_specimen_markdown(
        record,
        PROJECT_ROOT / "data" / "export" / "FT-0001.md",
    )

    assert "![Overall polished face](../images/FT-0001-hero.jpg)" in markdown
