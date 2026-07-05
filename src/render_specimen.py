from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from fossil_tracker.markdown_renderer import render_specimen_file


def main(argv: list[str] | None = None) -> int:
    """Run the standalone specimen Markdown renderer."""

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=Path, help="Specimen JSON file path")
    parser.add_argument("-o", "--output", type=Path, help="Markdown output path")
    args = parser.parse_args(argv)

    if not args.input.exists():
        parser.error(f"Input file does not exist: {args.input}")

    output_path = render_specimen_file(args.input, args.output)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
