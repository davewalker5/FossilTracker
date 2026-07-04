"""Compatibility imports for Fossil Tracker Streamlit helpers."""

from __future__ import annotations

from streamlit_app import main
from ui.common import save_uploaded_document, save_uploaded_image, validate_related_link_url

__all__ = [
    "main",
    "save_uploaded_document",
    "save_uploaded_image",
    "validate_related_link_url",
]


if __name__ == "__main__":
    main()
