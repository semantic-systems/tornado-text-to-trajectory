"""Retrieve article full text for the Media Cloud corpus.

The Media Cloud export carries headline, URL and date but no body, which bounds
what stage 30 can decide and makes those articles unlinkable — stage 31's
toponym matching needs text. This module retrieves the missing bodies.

**The Media Cloud API cannot supply it.** ``mediacloud.types.Story`` declares a
``text`` field, which is misleading: Media Cloud does extract and index the body
so that boolean searches can run against it, but its Story Guide states the text
"is not available for download due to copyright restrictions", and the documented
API response carries no ``text`` key at all. So there is no cheap route, and the
two below are the only ones.

1. **The publisher, directly.** ``robots.txt`` is honoured per domain, including
   ``Crawl-delay``; a disallowed URL is recorded as such and skipped, never
   fetched anyway.
2. **The Wayback Machine**, for anything dead, blocked or geo-walled. 23% of the
   corpus predates 2016 and 40% of URLs are still ``http://``; whole domains have
   gone (714 stories sit on ``cbslocal.com``, folded into cbsnews.com years ago);
   and US local outlets return HTTP 451 to EU traffic, which the archive resolves
   completely because it serves from the US.

Measured on a 594-URL stratified pilot: 54% retrieved at a 1 s archive interval,
but 250 of the 275 failures were archive *connection* errors rather than missing
snapshots, and only 16 articles had no archived copy at all. Raising the interval
to 5 s eliminated the connection errors entirely (10/12 vs 6/12 on the same
URLs), which puts the real ceiling near 85-90%. The binding constraint is
patience, not availability — hence :data:`ARCHIVE_INTERVAL`.

Legal basis for storing the result: EU DSM Art. 3, implemented in Germany as
§60d UrhG, permits a research organisation to reproduce lawfully accessible
works for text and data mining and to retain the copies for research. That
exception cannot be reserved against by rights holders, unlike the commercial
Art. 4 one. It does not license circumvention, so this module never bypasses a
paywall, never ignores ``robots.txt``, and never retries a block by disguising
itself. **Retrieved text is for local processing; what the project publishes
stays links plus derived annotations.**

Failure is recorded, never silently coerced into an empty string: a paywalled
stub that extracts as 180 plausible words is worse than an honest failure,
because it would be labelled as though it were the article.
"""

from __future__ import annotations

import re
import threading
import time
import urllib.robotparser
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Sequence
from urllib.parse import urlparse

import requests

USER_AGENT = ("tornado-text-to-trajectory/0.1 (academic research, Leuphana "
              "University; contact via repository)")
DEFAULT_TIMEOUT = 20
DEFAULT_CRAWL_DELAY = 2.0      # seconds between requests to one domain
# Some sites declare a Crawl-delay far beyond anything a bounded job can honour
# — kfdi.com asks for 300 s, which is 98 hours for its share of the corpus.
# The directive still binds, so the answer is to take *one* article from such a
# domain and record the rest as skipped, not to sleep for days and not to ignore
# it. Under this cap a domain is crawled at the rate it asked for.
MAX_CRAWL_DELAY = 30.0
# Seconds between requests to archive.org, across every worker. 1 s produced
# connection errors on 250 of 275 pilot failures; 5 s produced none. This is
# the single most important tunable in the module: it is the difference
# between ~26,000 and ~41,000 retrieved articles.
ARCHIVE_INTERVAL = 5.0
WAYBACK_DELAY = ARCHIVE_INTERVAL   # backwards-compatible alias
WAYBACK_ATTEMPTS = 3
MAX_HTML_BYTES = 4_000_000

# Below this an "article" is a stub, a redirect notice or a paywall teaser.
MIN_ARTICLE_WORDS = 120
PAYWALL_RE = re.compile(
    r"subscribe to (?:continue|read)|already a subscriber|"
    r"create an account to (?:continue|read)|this content is (?:only )?available "
    r"to subscribers|sign in to read|become a member to|"
    r"you have reached your (?:article|free) limit|register to continue", re.I)
BLOCKED_RE = re.compile(
    r"access denied|are you a robot|enable javascript to|"
    r"your browser is not supported|request unsuccessful|cloudflare", re.I)


@dataclass
class Retrieval:
    """One article's retrieval outcome — the unit the pilot reports on."""

    url: str
    status: str = "not_attempted"     # ok | robots_disallowed | http_error | …
    via: str = ""                     # mediacloud | direct | wayback
    http_status: int | None = None
    final_url: str = ""
    n_words: int = 0
    text: str = ""
    title: str = ""
    error: str = ""
    elapsed_s: float = 0.0
    retrieved_at: str = ""
    # Why this record exists when it is not a first attempt — e.g. an archive
    # re-fetch replacing a direct body that failed the quality checks.
    note: str = ""

    def row(self) -> dict[str, Any]:
        """Everything except the text itself, for the coverage table."""
        d = asdict(self)
        d.pop("text")
        return d


# ── robots.txt ──────────────────────────────────────────────────────────────
class RobotsCache:
    """Per-domain ``robots.txt``, fetched once and reused.

    A domain whose ``robots.txt`` cannot be fetched is treated as allowing —
    the conventional reading, and the alternative would silently drop outlets
    over a transient network error — but the reason is recorded so the coverage
    report can distinguish "permitted" from "unknown".
    """

    def __init__(self, user_agent: str = USER_AGENT, timeout: int = 10):
        self.user_agent = user_agent
        self.timeout = timeout
        self._cache: dict[str, tuple[urllib.robotparser.RobotFileParser | None, str]] = {}
        self._lock = threading.Lock()

    def _load(self, scheme: str, domain: str):
        with self._lock:
            if domain in self._cache:
                return self._cache[domain]
        parser: urllib.robotparser.RobotFileParser | None = None
        note = ""
        try:
            response = requests.get(f"{scheme}://{domain}/robots.txt",
                                    headers={"User-Agent": self.user_agent},
                                    timeout=self.timeout)
            if response.status_code == 200:
                parser = urllib.robotparser.RobotFileParser()
                parser.parse(response.text.splitlines())
                note = "fetched"
            else:
                note = f"http_{response.status_code}"
        except requests.RequestException as exc:
            note = f"unreachable: {type(exc).__name__}"
        with self._lock:
            self._cache[domain] = (parser, note)
        return parser, note

    def check(self, url: str) -> tuple[bool, float, str]:
        """Return ``(allowed, crawl_delay, note)`` for one URL."""
        parts = urlparse(url)
        if not parts.netloc:
            return False, 0.0, "unparseable_url"
        parser, note = self._load(parts.scheme or "https", parts.netloc)
        if parser is None:
            return True, DEFAULT_CRAWL_DELAY, note
        allowed = parser.can_fetch(self.user_agent, url)
        delay = parser.crawl_delay(self.user_agent)
        return allowed, float(delay) if delay else DEFAULT_CRAWL_DELAY, note


# ── fetching ────────────────────────────────────────────────────────────────
def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return session


def fetch_html(session: requests.Session, url: str,
               timeout: int = DEFAULT_TIMEOUT) -> tuple[str, int | None, str, str]:
    """Return ``(html, http_status, final_url, error)``; html is "" on failure."""
    try:
        response = session.get(url, timeout=timeout, allow_redirects=True, stream=True)
    except requests.RequestException as exc:
        return "", None, "", f"{type(exc).__name__}: {str(exc)[:120]}"
    try:
        if response.status_code != 200:
            return "", response.status_code, response.url, ""
        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type.lower():
            return "", 200, response.url, f"not html: {content_type[:60]}"
        raw = response.raw.read(MAX_HTML_BYTES, decode_content=True)
        encoding = response.encoding or "utf-8"
        return raw.decode(encoding, errors="replace"), 200, response.url, ""
    finally:
        response.close()


# archive.org is ONE host no matter which publisher an article came from, so it
# needs a throttle shared across every worker. Per-domain politeness does nothing
# for it: the first pilot ran 14 workers, each treating the archive as its own
# domain, and every one of 271 lookups came back 429.
_ARCHIVE_LOCK = threading.Lock()
_ARCHIVE_LAST = [0.0]


def set_archive_interval(seconds: float) -> None:
    """Set the global archive.org request interval for this run."""
    global ARCHIVE_INTERVAL
    ARCHIVE_INTERVAL = float(seconds)


def _archive_throttle(min_interval: float | None = None) -> None:
    interval = ARCHIVE_INTERVAL if min_interval is None else min_interval
    with _ARCHIVE_LOCK:
        wait = interval - (time.monotonic() - _ARCHIVE_LAST[0])
        if wait > 0:
            time.sleep(wait)
        _ARCHIVE_LAST[0] = time.monotonic()


def wayback_url(url: str, when: str | None = None) -> str:
    """Snapshot URL for the capture nearest ``when``.

    Built directly rather than looked up. ``web.archive.org/web/<ts>id_/<url>``
    redirects to the nearest capture on its own, so the separate availability
    API — which is the endpoint that rate-limited the first pilot into the
    ground — is not needed at all, and this costs one request instead of two.
    ``id_`` asks for the original bytes without the archive's toolbar injected.
    """
    stamp = (str(when).replace("-", "")[:8] or "") if when else ""
    return f"https://web.archive.org/web/{stamp or '2015'}id_/{url}"


def fetch_wayback(session: requests.Session, url: str, when: str | None = None,
                  timeout: int = DEFAULT_TIMEOUT) -> tuple[str, str]:
    """Return ``(html, reason)`` for the archived copy of ``url``.

    A 429 is reported as ``rate_limited``, never as ``no_snapshot``: the two mean
    opposite things — one says try again, the other says the article is
    unrecoverable — and collapsing them would understate what the archive can
    actually supply.
    """
    target = wayback_url(url, when)
    last = ""
    for attempt in range(1, WAYBACK_ATTEMPTS + 1):
        _archive_throttle()
        try:
            response = session.get(target, timeout=timeout, allow_redirects=True,
                                   stream=True)
        except requests.RequestException as exc:
            last = type(exc).__name__
            time.sleep(ARCHIVE_INTERVAL * attempt)
            continue
        try:
            if response.status_code == 429:
                last = "rate_limited"
                time.sleep(ARCHIVE_INTERVAL * 2 * attempt)
                continue
            if response.status_code in (404, 410):
                return "", "no_snapshot"
            if response.status_code != 200:
                last = f"http_{response.status_code}"
                time.sleep(ARCHIVE_INTERVAL * attempt)
                continue
            raw = response.raw.read(MAX_HTML_BYTES, decode_content=True)
            return raw.decode(response.encoding or "utf-8", errors="replace"), ""
        finally:
            response.close()
    return "", f"archive_{last}"


# ── extraction ──────────────────────────────────────────────────────────────
def extract_text(html: str, url: str = "") -> tuple[str, str, str]:
    """Return ``(text, title, reason)`` using trafilatura.

    ``reason`` is empty on success and names the problem otherwise, so a stub or
    a paywall teaser is never mistaken for a short article.
    """
    if not html:
        return "", "", "empty_html"
    try:
        import trafilatura
    except ImportError:  # pragma: no cover
        return "", "", "trafilatura_not_installed"

    # Precision first, then the default settings if that came back thin. On news
    # pages `favor_precision` occasionally discards most of the body along with
    # the boilerplate, and a 58-word result is indistinguishable from a genuine
    # stub unless the looser pass is tried.
    text = trafilatura.extract(html, url=url or None, favor_precision=True,
                               include_comments=False, include_tables=False) or ""
    if len(text.split()) < MIN_ARTICLE_WORDS:
        fallback = trafilatura.extract(html, url=url or None, include_comments=False,
                                       include_tables=False) or ""
        if len(fallback.split()) > len(text.split()):
            text = fallback
    title = ""
    try:
        meta = trafilatura.extract_metadata(html)
        title = (getattr(meta, "title", "") or "") if meta else ""
    except Exception:
        title = ""

    words = len(text.split())
    if words == 0:
        return "", title, "no_text_extracted"
    if PAYWALL_RE.search(text[:2000]) and words < 400:
        return text, title, "paywall_stub"
    if BLOCKED_RE.search(text[:1000]) and words < 200:
        return text, title, "blocked_or_js_required"
    if words < MIN_ARTICLE_WORDS:
        return text, title, f"too_short_{words}w"
    return text, title, ""


# ── one article, all routes ─────────────────────────────────────────────────
def retrieve_one(session: requests.Session, robots: RobotsCache, url: str,
                 published: str | None = None, *, use_wayback: bool = True,
                 timeout: int = DEFAULT_TIMEOUT) -> Retrieval:
    """Direct fetch, falling back to the archive; extraction decides success."""
    started = time.monotonic()
    result = Retrieval(url=url, retrieved_at=datetime.now(timezone.utc)
                       .isoformat(timespec="seconds"))

    allowed, _, note = robots.check(url)
    if not allowed:
        result.status = "robots_disallowed"
        result.error = note
        result.elapsed_s = round(time.monotonic() - started, 2)
        return result

    html, code, final, error = fetch_html(session, url, timeout)
    result.http_status, result.final_url = code, final
    if html:
        text, title, reason = extract_text(html, final or url)
        if not reason:
            result.status, result.via = "ok", "direct"
            result.text, result.title, result.n_words = text, title, len(text.split())
            result.elapsed_s = round(time.monotonic() - started, 2)
            return result
        result.error = reason
    elif error:
        result.error = error

    # Dead, blocked, or extracted to nothing usable — try the archive.
    direct_error = result.error or (f"http_{code}" if code else "no_html")
    if use_wayback:
        archived, why = fetch_wayback(session, url, published, timeout)
        if archived:
            text, title, reason = extract_text(archived, url)
            if not reason:
                result.status, result.via = "ok", "wayback"
                result.text, result.title = text, title
                result.n_words = len(text.split())
                result.elapsed_s = round(time.monotonic() - started, 2)
                return result
            result.error = f"direct:{direct_error}|archive:{reason}"
        else:
            result.error = f"direct:{direct_error}|archive:{why}"

    # Status names the *reason it is unavailable*, and keeps "the archive was
    # rate-limited" separate from "no archived copy exists" — retryable versus
    # genuinely lost.
    if "archive:archive_rate_limited" in result.error:
        result.status = "archive_rate_limited"
    elif result.error.startswith("paywall") or "archive:paywall" in result.error:
        result.status = "paywalled"
    elif result.error.startswith("blocked") or "archive:blocked" in result.error:
        result.status = "blocked"
    elif result.http_status == 451:
        result.status = "geo_blocked"       # GDPR wall; common for US local news
    elif result.http_status and result.http_status >= 400:
        result.status = "http_error"
    elif result.error:
        result.status = "extraction_failed"
    else:
        result.status = "unknown_failure"
    result.elapsed_s = round(time.monotonic() - started, 2)
    return result


# ── many articles, polite per domain ────────────────────────────────────────
def retrieve_many(items: Sequence[dict[str, Any]], *, workers: int = 12,
                  use_wayback: bool = True, timeout: int = DEFAULT_TIMEOUT,
                  progress: Callable[[int], None] | None = None,
                  store_path=None) -> list[Retrieval]:
    """Retrieve a batch, serialising within each domain and parallel across them.

    Politeness and throughput usually trade off; here they do not. The corpus
    spans 2,296 domains with the top ten holding 14% of it, so giving each domain
    its own sequential worker and running many workers at once is both gentle per
    publisher and fast overall. Grouping by domain is what makes ``Crawl-delay``
    enforceable at all — a flat thread pool would interleave hosts and honour it
    for none of them.
    """
    robots = RobotsCache()
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_domain[urlparse(item["url"]).netloc].append(item)

    results: dict[str, Retrieval] = {}
    lock = threading.Lock()

    def work(domain_items: list[dict[str, Any]]) -> None:
        session = _session()
        delay = DEFAULT_CRAWL_DELAY
        for index, item in enumerate(domain_items):
            allowed, crawl_delay, note = robots.check(item["url"])
            delay = max(crawl_delay, DEFAULT_CRAWL_DELAY)
            if index and delay > MAX_CRAWL_DELAY:
                # Honour the directive by stopping, not by sleeping for hours.
                outcome = Retrieval(
                    url=item["url"], status="robots_crawl_delay_too_long",
                    error=f"Crawl-delay {delay:g}s > {MAX_CRAWL_DELAY:g}s cap",
                    retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            else:
                if index:
                    time.sleep(delay)
                outcome = retrieve_one(session, robots, item["url"],
                                       item.get("publish_date"),
                                       use_wayback=use_wayback, timeout=timeout)
            with lock:
                results[item["url"]] = outcome
            if store_path is not None:
                # Written before the next request, so an interrupted run loses
                # at most the article in flight.
                append_store(store_path, outcome)
            if progress:
                progress(1)
        session.close()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, by_domain.values()))
    return [results[item["url"]] for item in items if item["url"] in results]


# ── resumable on-disk store ─────────────────────────────────────────────────
# A full pass is ~48,700 articles and, at the archive interval that actually
# works, runs for over a day. It must survive being interrupted, so every
# outcome is appended the moment it is known and a restart skips what is already
# there. Append-only: a partially written final line after a hard kill costs one
# article, not the file.
_STORE_LOCK = threading.Lock()

# Statuses worth attempting again on a later pass, because they describe the
# state of the network rather than the article. Everything else — a robots
# disallow, a genuinely missing snapshot, a paywall — is settled, and retrying
# it just annoys the server.
RETRYABLE = {"archive_rate_limited", "unknown_failure", "archive_connection",
             "not_attempted"}


def load_store(path) -> dict[str, dict[str, Any]]:
    """Read prior outcomes, keyed by URL. Missing file -> empty."""
    from pathlib import Path
    import json

    path = Path(path)
    out: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                out[record["url"]] = record          # later wins: a retry supersedes
            except (ValueError, KeyError):
                continue
    return out


def append_store(path, retrieval: "Retrieval") -> None:
    """Append one outcome, text included, atomically enough for a crash."""
    from pathlib import Path
    import json

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _STORE_LOCK, path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(retrieval), ensure_ascii=False) + "\n")


def pending(items: Sequence[dict[str, Any]], store: dict[str, dict[str, Any]],
            retry_failed: bool = False) -> list[dict[str, Any]]:
    """Which items still need work, given what the store already holds."""
    todo = []
    for item in items:
        prior = store.get(item["url"])
        if prior is None:
            todo.append(item)
        elif prior.get("status") != "ok" and retry_failed:
            status = str(prior.get("status", ""))
            error = str(prior.get("error", ""))
            if status in RETRYABLE or "ConnectionError" in error or "429" in error:
                todo.append(item)
    return todo


# ── archive re-fetch for direct bodies that fail the quality checks ─────────
# A direct fetch can succeed technically and still return the wrong page: a
# soft 404 to the front page, or a cookie-consent wall served to EU traffic in
# place of the article (1,070 retrievals across a group of US TV-station sites
# land on one YouTube consent page). The quality checks catch these, but the
# crawl never tried the archive for them, because extraction had "succeeded".
# Archive copies pass the same checks at 98.5%, and the snapshot is taken nearest
# the publication date — before the article died or the wall went up.
#
# Store semantics: an archive copy that extracts cleanly *and mentions a
# tornado* is appended to the store and supersedes the direct record (the old
# line stays in the file). An
# archive failure never touches the store — the direct body remains the record,
# still flagged — and is written to a separate log instead, so a rerun skips it.

def _refetch_settled(outcome: str) -> bool:
    """Outcomes not worth another attempt: done, or no usable copy exists."""
    return outcome == "ok" or outcome == "no_snapshot" or outcome.startswith("extract:")


def load_refetch_log(path) -> dict[str, dict[str, Any]]:
    """Prior re-fetch attempts keyed by URL; later wins. Missing file -> empty."""
    from pathlib import Path
    import json

    path = Path(path)
    out: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                record = json.loads(line)
                out[record["url"]] = record
            except (ValueError, KeyError):
                continue
    return out


def refetch_pending(items: Sequence[dict[str, Any]],
                    log: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Items not yet re-fetched, plus those whose last attempt was transient."""
    return [i for i in items
            if i["url"] not in log or not _refetch_settled(str(log[i["url"]].get("outcome", "")))]


def refetch_one(session: requests.Session, url: str, published: str | None = None,
                timeout: int = DEFAULT_TIMEOUT) -> tuple[Retrieval | None, str]:
    """Archive copy of ``url`` as a Retrieval, or ``(None, reason)``.

    No robots check: these URLs were already fetched directly under the
    publisher's robots.txt, and the request goes to archive.org, not to them.
    """
    started = time.monotonic()
    archived, why = fetch_wayback(session, url, published, timeout)
    if not archived:
        return None, why or "archive_unknown"
    text, title, reason = extract_text(archived, url)
    if reason:
        return None, f"extract:{reason}"
    # Media Cloud's `tornado*` query matched this page, so a copy that never
    # mentions one is no better than the direct body it would replace — often
    # the archive captured the same redirect (e.g. to the outlet's YouTube page).
    from .lexisnexis_filter import mention_positions
    if not mention_positions(text.split()):
        return None, "extract:archive_copy_no_tornado_mention"
    return Retrieval(url=url, status="ok", via="wayback", http_status=200,
                     final_url=wayback_url(url, published), n_words=len(text.split()),
                     text=text, title=title, elapsed_s=round(time.monotonic() - started, 2),
                     retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds")
                     ), ""


def refetch_many(items: Sequence[dict[str, Any]], *, store_path, log_path,
                 timeout: int = DEFAULT_TIMEOUT,
                 progress: Callable[[int], None] | None = None) -> dict[str, int]:
    """Re-fetch each item from the archive; returns outcome counts.

    Sequential on purpose: every request goes to archive.org, which is throttled
    globally, so parallel workers would only queue behind the same lock.
    Each ``item`` carries ``url``, ``publish_date`` and the ``flags`` that failed.
    """
    from collections import Counter
    from pathlib import Path
    import json

    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter = Counter()
    session = _session()
    try:
        for item in items:
            flags = ",".join(item.get("flags") or [])
            result, why = refetch_one(session, item["url"], item.get("publish_date"), timeout)
            if result is not None:
                result.note = f"archive_refetch: direct body failed {flags}"
                append_store(store_path, result)
            outcome = "ok" if result is not None else why
            counts[outcome] += 1
            with _STORE_LOCK, log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "url": item["url"], "outcome": outcome, "failed_flags": flags,
                    "n_words": result.n_words if result else 0,
                    "attempted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }) + "\n")
            if progress:
                progress(1)
    finally:
        session.close()
    return dict(counts)


# ── text quality ────────────────────────────────────────────────────────────
# A retrieval counted `ok` has passed extraction: a body of at least
# MIN_ARTICLE_WORDS that is not an obvious paywall or bot wall. That is a low bar.
# The checks below ask whether the body is *the article the headline names*,
# which extraction cannot tell. They are flags for inspection with stated
# thresholds, not silent filters: each one is reported with its rate, and
# `quality_ok` is defined from the hard flags only, so the definition can be
# changed without re-reading 38,000 bodies.
#
# The strongest check is free. Media Cloud collected this corpus with a
# full-text query for `tornado*` against *its own* extraction of each page, so a
# correct body should mention a tornado. One that does not is most likely a
# different page — a redirect to a section front, a template, a truncated
# extraction — though it can also be an article whose only mention sat in a
# caption or related-links box that trafilatura drops. Hence a flag, not proof.

TITLE_MISMATCH_CONTAINMENT = 0.30   # below this, retrieved title != headline
TEMPLATE_MIN_HEADLINES = 3          # one body under this many distinct headlines…
TEMPLATE_MAX_TITLE_SIM = 0.30       # …that also disagree with it = a template page
BOILERPLATE_DOMAIN_MIN_DOCS = 10    # need this many docs to call a line boilerplate
BOILERPLATE_LINE_SHARE = 0.50       # line in >= half a domain's docs is boilerplate
HIGH_BOILERPLATE_SHARE = 0.30       # flag a body whose words are this much boilerplate
VERY_LONG_WORDS = 8_000             # live blogs and whole-page dumps
MIN_ENGLISH_STOPWORD_SHARE = 0.15   # English prose runs ~0.35-0.45

# Hard flags make `quality_ok` False; soft flags are reported only.
#
# `title_mismatch` was hard in the first version and is soft on evidence: of
# the 1,278 articles it rejected on its own, the median body mentioned a tornado
# 9 times — *more* than passing articles (6) — and 92% mentioned one at least 3
# times. They were the right articles, retitled after Media Cloud indexed them
# (live-update pages, AP stories re-headlined as they develop). A changed title
# is not a wrong page.
HARD_FLAGS = ("no_tornado_mention", "redirected_home", "template_body",
              "not_english")
SOFT_FLAGS = ("title_mismatch", "high_boilerplate", "very_long")

_EN_STOPWORDS = frozenset(
    "the a an and or of to in on at for with by from is are was were be been has "
    "have had it its this that as but not they he she we you his her their our".split())
_HOME_PATH_RE = re.compile(r"^/?(index\.(?:html?|php|aspx?))?$", re.I)


def _stopword_share(text: str) -> float:
    words = re.findall(r"[a-z']+", text.lower())
    return sum(w in _EN_STOPWORDS for w in words) / len(words) if words else 0.0


def _redirected_home(url: str, final_url: str, via: str) -> bool:
    """A direct fetch that ended on a site's front page rather than the article.

    Only meaningful for direct fetches; an archive fetch's final URL is the
    archive's, not the publisher's.
    """
    if via != "direct" or not final_url:
        return False
    start, end = urlparse(url), urlparse(final_url)
    return bool(_HOME_PATH_RE.match(end.path or "/")
                and not _HOME_PATH_RE.match(start.path or "/"))


def _boilerplate_lines(docs: "pd.DataFrame") -> dict[str, set[str]]:
    """Per domain, the paragraphs that recur across most of its documents."""
    from collections import Counter

    out: dict[str, set[str]] = {}
    for domain, group in docs.groupby("domain"):
        if len(group) < BOILERPLATE_DOMAIN_MIN_DOCS:
            continue
        counts: Counter[str] = Counter()
        for text in group.text:
            counts.update({line.strip() for line in str(text).split("\n")
                           if len(line.split()) >= 4})
        cutoff = BOILERPLATE_LINE_SHARE * len(group)
        common = {line for line, n in counts.items() if n >= cutoff}
        if common:
            out[domain] = common
    return out


def quality_table(store: dict[str, dict[str, Any]], events: "pd.DataFrame") -> "pd.DataFrame":
    """One row per retrieved article, with every quality measure and flag.

    ``events`` supplies the Media Cloud headline and its ``dup_group``, which the
    title-agreement and template checks compare against. The table carries no
    article text, so it can be shared and inspected freely.
    """
    import pandas as pd
    from . import matching
    from .lexisnexis_filter import body_key, mention_positions

    ok = [{"url": u, **{k: r.get(k) for k in ("via", "final_url", "title", "text",
                                               "n_words")}}
          for u, r in store.items() if r.get("status") == "ok"]
    docs = pd.DataFrame(ok)
    if docs.empty:
        return docs
    meta = events[["url", "title", "dup_group", "media_name", "year_band",
                   "domain_size"]].rename(columns={"title": "headline"})
    docs = docs.merge(meta, on="url", how="inner")
    docs["domain"] = docs.media_name.astype(str)
    docs["text"] = docs.text.fillna("").astype(str)

    docs["n_mentions"] = docs.text.map(lambda t: len(mention_positions(t.split())))
    docs["title_containment"] = [
        matching.title_similarity(h, t)["containment"] if t else float("nan")
        for h, t in zip(docs.headline, docs.title.fillna(""))]
    docs["redirected_home_"] = [_redirected_home(u, f or "", v or "")
                                for u, f, v in zip(docs.url, docs.final_url, docs.via)]
    docs["stopword_share"] = docs.text.map(_stopword_share)

    # Syndication versus templates. One body under several headlines is normal
    # wire copy *if the headlines agree with it*; one body under several
    # headlines that all disagree with it is the same error page served for
    # many URLs.
    docs["body_key"] = body_key(docs.text)
    per_body = docs.groupby("body_key").agg(
        body_headlines=("dup_group", "nunique"),
        body_title_sim=("title_containment", "median"))
    docs = docs.join(per_body, on="body_key")

    common = _boilerplate_lines(docs)

    def boiler_share(row) -> float:
        lines = common.get(row.domain)
        if not lines or not row.n_words:
            return 0.0
        hit = sum(len(l.split()) for l in row.text.split("\n") if l.strip() in lines)
        return hit / max(row.n_words, 1)

    docs["boilerplate_share"] = docs.apply(boiler_share, axis=1)

    docs["no_tornado_mention"] = docs.n_mentions == 0
    docs["title_mismatch"] = docs.title_containment < TITLE_MISMATCH_CONTAINMENT
    docs["redirected_home"] = docs.redirected_home_
    # A template is a page served for many URLs that is about none of them. The
    # first version required only shared-and-disagreeing headlines, which is
    # also what *retitled wire copy* looks like: its 20 single-flag rejections
    # had a median of 12 tornado mentions. Requiring the body to be off-topic
    # as well separates the two.
    docs["template_body"] = ((docs.body_headlines >= TEMPLATE_MIN_HEADLINES)
                             & (docs.body_title_sim < TEMPLATE_MAX_TITLE_SIM)
                             & (docs.n_mentions == 0))
    docs["not_english"] = docs.stopword_share < MIN_ENGLISH_STOPWORD_SHARE
    docs["high_boilerplate"] = docs.boilerplate_share >= HIGH_BOILERPLATE_SHARE
    docs["very_long"] = docs.n_words >= VERY_LONG_WORDS
    docs["quality_ok"] = ~docs[list(HARD_FLAGS)].any(axis=1)

    keep = ["url", "dup_group", "headline", "domain", "via", "year_band",
            "domain_size", "n_words", "n_mentions", "title_containment",
            "stopword_share", "boilerplate_share", "body_key", "body_headlines",
            *HARD_FLAGS, *SOFT_FLAGS, "quality_ok"]
    return docs[keep]
