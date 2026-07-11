#!/usr/bin/env python3
"""Serve the static web UI on port 5173 (no Node.js required)."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve NCC compliance web UI")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "web",
    )
    args = parser.parse_args()

    handler = partial(SimpleHTTPRequestHandler, directory=str(args.directory))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Web UI: http://127.0.0.1:{args.port}/")
    print("Press Ctrl+C to stop.")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
