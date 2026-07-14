"""Search tab for the Fossil Tracker Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from fossil_tracker.db import list_specimens
from ui.common import render_search_results

SEARCH_PAGE_SIZE = 10


def paginated_specimens(
    specimens: list[dict], page: int, page_size: int = SEARCH_PAGE_SIZE
) -> tuple[list[dict], int, int]:
    """Return one safe page of specimens and pagination metadata."""

    page_count = max(1, (len(specimens) + page_size - 1) // page_size)
    current_page = min(max(page, 1), page_count)
    start = (current_page - 1) * page_size
    return specimens[start : start + page_size], current_page, page_count


def show_register(db_path: Path) -> None:
    """Render the searchable specimen register.

    :param db_path: SQLite database path.
    """

    search = st.text_input(
        "Search", placeholder="Please enter a search term", key="specimen-search"
    )
    query = search.strip()
    if st.session_state.get("specimen-search-query") != query:
        st.session_state["specimen-search-query"] = query
        st.session_state["specimen-search-page"] = 1
        st.session_state["specimen-search-revision"] = (
            st.session_state.get("specimen-search-revision", 0) + 1
        )

    specimens = list_specimens(db_path, query)
    st.metric("Specimens", len(specimens))

    if not specimens:
        st.info("No matching specimens yet.")
        return

    page_specimens, current_page, page_count = paginated_specimens(
        specimens, st.session_state.get("specimen-search-page", 1)
    )
    st.session_state["specimen-search-page"] = current_page
    revision = st.session_state.get("specimen-search-revision", 0)
    render_search_results(
        page_specimens,
        db_path,
        key=f"specimen-search-results-{revision}-{current_page}",
    )

    previous_col, page_col, next_col = st.columns([1, 2, 1])
    if previous_col.button(
        "Previous",
        disabled=current_page == 1,
        width="stretch",
        key=f"specimen-search-previous-{revision}-{current_page}",
    ):
        st.session_state["specimen-search-page"] = current_page - 1
        st.rerun()
    page_col.markdown(
        f"<p style='text-align: center'>Page {current_page} of {page_count}</p>",
        unsafe_allow_html=True,
    )
    if next_col.button(
        "Next",
        disabled=current_page == page_count,
        width="stretch",
        key=f"specimen-search-next-{revision}-{current_page}",
    ):
        st.session_state["specimen-search-page"] = current_page + 1
        st.rerun()
