#!/usr/bin/env bash

export PROJECT_ROOT=$( cd "$(dirname "$0")/.." ; pwd -P )
cd "$PROJECT_ROOT"

. venv/bin/activate

unset FOSSIL_TRACKER_DB
unset FOSSIL_TRACKER_DOCUMENTS
unset FOSSIL_TRACKER_IMAGES

streamlit run src/streamlit_app.py
