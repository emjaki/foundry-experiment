#!/usr/bin/env python3
"""Stub for seeding NCC excerpts into Azure AI Search / Foundry IQ."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed NCC knowledge base (stub)")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "samples" / "ncc",
        help="Directory of NCC markdown excerpts",
    )
    args = parser.parse_args()

    files = sorted(args.source_dir.glob("*.md"))
    print(f"Found {len(files)} NCC excerpt file(s) in {args.source_dir}")
    for path in files:
        print(f"  - {path.name}")
    print("Wire this script to your Azure AI Search indexer in production.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
