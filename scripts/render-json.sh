#!/usr/bin/env bash

export PROJECT_ROOT=$( cd "$(dirname "$0")/.." ; pwd -P )
cd "$PROJECT_ROOT"

. venv/bin/activate

if [[ "$1" == */* ]]; then
    INPUT_FILE="$1"
elif [[ -n "$FOSSIL_TRACKER_EXPORT" ]]; then
    INPUT_FILE="$FOSSIL_TRACKER_EXPORT/$1.json"
else
    INPUT_FILE="$PROJECT_ROOT/data/export/$1.json"
fi

RENDER_ARGS=(--input "$INPUT_FILE")
if [[ -n "$2" ]]; then
    RENDER_ARGS+=(--cdn-url "$2")
fi

python "$PROJECT_ROOT/src/render_specimen.py" "${RENDER_ARGS[@]}"
