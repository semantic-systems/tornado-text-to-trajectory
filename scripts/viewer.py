"""The corpus viewer — a tool, not a pipeline stage.

A local Flask app for reading articles next to the events they were linked to. Loads the corpus once (about half a minute)
and then serves instantly.

    python scripts/viewer.py
    python scripts/viewer.py --port 8801 --tag march2025

``--corpus mediacloud`` opens the full-text inspection view instead: the bodies
stage 33 retrieved, their quality flags, the headline label beside the full-text
label from stage 34, and one-key verdicts saved for stage 34's ``compare``.

    python scripts/viewer.py --corpus mediacloud
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from tornado_dataset import config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", choices=("lexisnexis", "mediacloud"),
                        default="lexisnexis",
                        help="lexisnexis: articles and their event links (default); "
                             "mediacloud: retrieved full texts and their labels")
    parser.add_argument("--tag", default=None,
                        help="lexisnexis: dataset tag (default: the config window); "
                             "mediacloud: stage 34 --tag whose labels to show")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8799)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    # Imported here so each view only needs what it reads.
    if args.corpus == "mediacloud":
        from tornado_dataset.viewer.fulltext import create_fulltext_app
        app = create_fulltext_app(args.tag)
    else:
        from tornado_dataset.viewer.app import create_app
        app = create_app(args.tag)
    print(f"\n  {args.corpus} viewer → http://{args.host}:{args.port}\n")
    # threaded=False keeps one copy of the store; reloader off so the corpus is
    # not parsed twice on start.
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)


if __name__ == "__main__":
    main()
