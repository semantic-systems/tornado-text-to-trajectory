"""Flask app for browsing the LexisNexis corpus and its candidate links.

Local, single-user, read-mostly. The store holds everything in memory, so the
routes are thin: filter the index, hand back one article with its links, or hand
back one episode as GeoJSON for the interactive map.

    python scripts/16_viewer.py            # http://127.0.0.1:8799

The annotation screen (phase 2) will POST labels here and they will be written
straight to `outputs/annotation/`, which is the reason this is a server rather
than a static bundle.
"""

from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from .store import Store


def create_app(tag: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config["store"] = Store(tag)

    @app.get("/")
    def index():
        store: Store = app.config["store"]
        return render_template("index.html", facets=store.facets(), tag=store.tag)

    @app.get("/api/articles")
    def api_articles():
        store: Store = app.config["store"]
        year = request.args.get("year", type=int)
        min_score = request.args.get("min_score", type=float)
        return jsonify(store.search(
            query=request.args.get("q", "").strip(),
            year=year,
            status=request.args.get("status", ""),
            source=request.args.get("source", ""),
            relation=request.args.get("relation", ""),
            min_score=min_score,
            has_links=request.args.get("has_links", ""),
            offset=request.args.get("offset", default=0, type=int),
            limit=min(request.args.get("limit", default=50, type=int), 200),
        ))

    @app.get("/api/article/<uid>")
    def api_article(uid: str):
        store: Store = app.config["store"]
        article = store.article(uid)
        if article is None:
            return jsonify({"error": "unknown article"}), 404
        return jsonify(article)

    @app.get("/api/episode/<uid>")
    def api_episode(uid: str):
        store: Store = app.config["store"]
        episode = store.episode_detail(uid)
        if episode is None:
            return jsonify({"error": "unknown episode"}), 404
        return jsonify(episode)

    return app
