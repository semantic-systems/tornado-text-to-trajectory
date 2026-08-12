"""Stage 16 — run the corpus viewer.

A local Flask app for reading articles next to the events they were linked to,
which is the thing a CSV cannot do. Loads the corpus once (about half a minute)
and then serves instantly.

    python scripts/16_viewer.py
    python scripts/16_viewer.py --port 8801 --tag march2025
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from tornado_dataset import config
from tornado_dataset.viewer.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default=None, help="dataset tag (default: the config window)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8799)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    app = create_app(args.tag)
    print(f"\n  corpus viewer → http://{args.host}:{args.port}\n")
    # threaded=False keeps one copy of the store; reloader off so the corpus is
    # not parsed twice on start.
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)


if __name__ == "__main__":
    main()
