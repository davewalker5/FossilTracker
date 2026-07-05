#!/usr/bin/env bash

export PROJECT_ROOT=$( cd "$(dirname "$0")/.." ; pwd -P )
cd "$PROJECT_ROOT"

. venv/bin/activate

if [[ "$1" == */* ]]; then
    INPUT_FILE="$1"
else
    INPUT_FILE="$PROJECT_ROOT/data/export/$1.json"
fi

unset FOSSIL_TRACKER_DB
unset FOSSIL_TRACKER_DOCUMENTS
unset FOSSIL_TRACKER_IMAGES
unset FOSSIL_TRACKER_EXPORT

python "$PROJECT_ROOT/src/render_specimen.py" --input "$INPUT_FILE"
