"""Taxonomy tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from fossil_tracker.db import (
    create_taxonomy,
    delete_taxonomy,
    get_specimen,
    get_taxonomy_for_specimen,
    list_specimens,
    update_specimen,
    update_taxonomy,
)
from ui.common import (
    CONFIDENCE_OPTIONS,
    option_index,
    remember_default_specimen,
    remember_selected_specimen,
    specimen_choice_index,
)


def show_taxonomy_manager(db_path: Path) -> None:
    """Render one-to-one taxonomy management for the selected specimen.

    :param db_path: SQLite database path.
    """

    specimens = list_specimens(db_path)
    if not specimens:
        st.info("Add a specimen before recording taxonomy.")
        return

    choices = {f"{row['collection_code']} - {row['title']}": row["id"] for row in specimens}
    selected_label = st.selectbox(
        "Specimen",
        list(choices),
        index=specimen_choice_index(specimens),
        key="taxonomy-specimen",
        on_change=remember_selected_specimen,
        args=("taxonomy-specimen", choices),
    )
    remember_default_specimen(selected_label, choices)
    specimen = get_specimen(choices[selected_label], db_path)
    if specimen is None:
        st.warning("Selected specimen was not found.")
        return

    taxonomy = get_taxonomy_for_specimen(specimen["id"], db_path)
    suffix = taxonomy["id"] if taxonomy else f"new-{specimen['id']}"

    st.subheader("Taxonomy")
    with st.form(f"specimen-taxonomy-form-{suffix}", clear_on_submit=taxonomy is None):
        tax_cols = st.columns([1, 1, 1, 1])
        kingdom = tax_cols[0].text_input(
            "Kingdom",
            value=(taxonomy["kingdom"] or "") if taxonomy else "Animalia",
            key=f"specimen-taxonomy-kingdom-{suffix}",
        )
        phylum = tax_cols[1].text_input(
            "Phylum",
            value=(taxonomy["phylum"] or "") if taxonomy else "",
            key=f"specimen-taxonomy-phylum-{suffix}",
        )
        class_name = tax_cols[2].text_input(
            "Class",
            value=(taxonomy["class_name"] or "") if taxonomy else "",
            key=f"specimen-taxonomy-class-{suffix}",
        )
        subclass = tax_cols[3].text_input(
            "Subclass",
            value=(taxonomy["subclass"] or "") if taxonomy else "",
            key=f"specimen-taxonomy-subclass-{suffix}",
        )
        lower_tax_cols = st.columns([1, 1, 1, 1])
        order_name = lower_tax_cols[0].text_input(
            "Order",
            value=(taxonomy["order_name"] or "") if taxonomy else "",
            key=f"specimen-taxonomy-order-{suffix}",
        )
        family = lower_tax_cols[1].text_input(
            "Family",
            value=(taxonomy["family"] or "") if taxonomy else "",
            key=f"specimen-taxonomy-family-{suffix}",
        )
        genus = lower_tax_cols[2].text_input(
            "Genus",
            value=(taxonomy["genus"] or "") if taxonomy else "",
            key=f"specimen-taxonomy-genus-{suffix}",
        )
        species = lower_tax_cols[3].text_input(
            "Species",
            value=(taxonomy["species"] or "") if taxonomy else "",
            key=f"specimen-taxonomy-species-{suffix}",
        )
        confidence = st.selectbox(
            "Identification confidence",
            CONFIDENCE_OPTIONS,
            index=option_index(
                CONFIDENCE_OPTIONS,
                taxonomy["identification_confidence"] if taxonomy else "Unknown",
            ),
            key=f"specimen-taxonomy-confidence-{suffix}",
        )
        notes = st.text_area(
            "Identification notes",
            value=taxonomy["identification_notes"]
            if taxonomy and taxonomy["identification_notes"]
            else "",
            height=200,
            key=f"specimen-taxonomy-notes-{suffix}",
        )
        save_col, delete_col = st.columns([1, 1])
        save_taxonomy = save_col.form_submit_button("Save taxonomy", width="stretch")
        remove_taxonomy = delete_col.form_submit_button(
            "Delete taxonomy", disabled=taxonomy is None, width="stretch"
        )

    values = {
        "kingdom": kingdom,
        "phylum": phylum,
        "class_name": class_name,
        "subclass": subclass,
        "order_name": order_name,
        "family": family,
        "genus": genus,
        "species": species,
        "identification_confidence": confidence,
        "identification_notes": notes,
    }

    if save_taxonomy:
        if taxonomy is None:
            taxon_id = create_taxonomy(values, db_path)
            specimen_values = dict(specimen)
            specimen_values["taxon_id"] = taxon_id
            update_specimen(specimen["id"], specimen_values, db_path)
            st.success("Taxonomy added.")
        else:
            update_taxonomy(taxonomy["id"], values, db_path)
            st.success("Taxonomy updated.")
        st.rerun()

    if remove_taxonomy and taxonomy is not None:
        specimen_values = dict(specimen)
        specimen_values["taxon_id"] = None
        update_specimen(specimen["id"], specimen_values, db_path)
        delete_taxonomy(taxonomy["id"], db_path)
        st.warning("Taxonomy deleted.")
        st.rerun()
