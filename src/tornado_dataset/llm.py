"""Client for a locally hosted, OpenAI-compatible LLM server (vLLM).

The dataset uses an LLM for two jobs that no rule can do well — labelling a seed
sample so a cheap classifier has something to learn from, and adjudicating the
cases the cheap classifier is not confident about. Both are *measurement*
instruments, so this module is built around the same discipline as
:mod:`tornado_dataset.http`:

* **every response is cached on disk**, keyed by model + prompt, so a rerun costs
  nothing and an interrupted 20k-row job resumes where it stopped;
* **failures are visible** — a request that never succeeded returns ``None``
  rather than an empty answer that would silently look like a decision;
* **the model identity is recorded** with each answer, because a label produced
  by a different model is a different measurement.

The server is assumed to be reachable at ``API_BASE``. For a model hosted on a
remote machine, forward the port first and leave the default alone::

    ssh -N -L 8000:localhost:8000 you@your-server

Then check it is up::

    curl -s http://127.0.0.1:8000/v1/models
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import requests

DEFAULT_API_BASE = os.environ.get("TORNADO_LLM_BASE", "http://127.0.0.1:8000/v1")
DEFAULT_API_KEY = os.environ.get("TORNADO_LLM_API_KEY", "EMPTY")  # vLLM's placeholder
DEFAULT_CONCURRENCY = 16
DEFAULT_TIMEOUT = 180
MAX_ATTEMPTS = 4


class LLMError(RuntimeError):
    pass


class LLMClient:
    """Thread-safe chat-completions client with an append-only response cache.

    Parameters
    ----------
    model:
        Served model id. ``None`` asks the server which model it has loaded,
        which is what you want with vLLM — the id is the checkpoint path and is
        tedious (and easy to get subtly wrong) to type by hand.
    thinking:
        Qwen 3 models reason before answering unless told not to. For a
        single-label classification the reasoning is pure latency, so it is off
        by default; ``--thinking`` turns it back on for a spot check.
    """

    def __init__(self, api_base: str = DEFAULT_API_BASE, model: str | None = None,
                 api_key: str = DEFAULT_API_KEY, cache_path: Path | None = None,
                 concurrency: int = DEFAULT_CONCURRENCY, temperature: float = 0.0,
                 thinking: bool = False, timeout: int = DEFAULT_TIMEOUT):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.concurrency = concurrency
        self.temperature = temperature
        self.thinking = thinking
        self.timeout = timeout
        self.model = model or self.discover_model()

        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {self.api_key}",
                                      "Content-Type": "application/json"})
        # Whether the server accepts the structured-output and chat-template
        # extras. Established once by :meth:`probe_features` *before* any
        # concurrent work starts — discovering it under load instead means every
        # thread in flight hits the same 400 at once and races to record it,
        # which costs real requests and mislabels the cause.
        self._no_schema = False
        self._no_template_kwargs = False
        self._probed = False

        self._lock = threading.Lock()
        self._cache_path = cache_path
        self._cache: dict[str, str] = {}
        if cache_path is not None:
            self._cache = _read_cache(cache_path)
        self.stats = {"cached": 0, "called": 0, "failed": 0}

    # ── server discovery ────────────────────────────────────────────────────
    def discover_model(self) -> str:
        try:
            r = requests.get(f"{self.api_base}/models",
                             headers={"Authorization": f"Bearer {self.api_key}"},
                             timeout=20)
            r.raise_for_status()
            data = r.json().get("data") or []
            if not data:
                raise LLMError(f"{self.api_base}/models returned no models")
            return data[0]["id"]
        except requests.RequestException as exc:
            raise LLMError(
                f"cannot reach the LLM server at {self.api_base} ({exc}).\n"
                f"If it runs on a remote host, forward the port first:\n"
                f"    ssh -N -L 8000:localhost:8000 you@your-server\n"
                f"or pass --api-base explicitly."
            ) from exc

    # ── single completion ───────────────────────────────────────────────────
    def _payload(self, prompt: str, system: str | None, max_tokens: int,
                 schema: dict[str, Any] | None,
                 temperature: float | None = None) -> dict[str, Any]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": max_tokens,
        }
        if schema is not None and not self._no_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "label", "schema": schema, "strict": True},
            }
        if not self._no_template_kwargs:
            payload["chat_template_kwargs"] = {"enable_thinking": self.thinking}
        return payload

    def probe_features(self, schema: dict[str, Any] | None) -> None:
        """Find out once whether the server accepts the optional extras.

        vLLM builds differ in whether they take ``response_format`` and
        ``chat_template_kwargs``; rather than let every worker rediscover a 400
        simultaneously, one throwaway request settles it up front.
        """
        with self._lock:
            if self._probed:
                return
            self._probed = True
        url = f"{self.api_base}/chat/completions"
        for _ in range(3):
            payload = self._payload("ping", None, 4, schema)
            try:
                r = self._session.post(url, json=payload, timeout=self.timeout)
            except requests.RequestException:
                return                      # let the retry loop in complete() deal with it
            if r.status_code != 400:
                return
            if not self._no_schema and "response_format" in payload:
                self._no_schema = True
                continue
            if not self._no_template_kwargs and "chat_template_kwargs" in payload:
                self._no_template_kwargs = True
                continue
            return

    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 96,
                 schema: dict[str, Any] | None = None, temperature: float | None = None,
                 variant: str = "") -> str | None:
        """Return the assistant text, or ``None`` if every attempt failed.

        ``variant`` separates cache entries that share a prompt but are meant to
        be *different draws* — repeated samples for a self-consistency estimate
        would otherwise all collide on the first answer and report perfect
        agreement, which is the failure mode that silently invalidates the whole
        measurement. Temperature is part of the key for the same reason.
        """
        temp = self.temperature if temperature is None else temperature
        key = _cache_key(self.model, system, prompt, temp, variant)
        with self._lock:
            hit = self._cache.get(key)
        if hit is not None:
            with self._lock:
                self.stats["cached"] += 1
            return hit

        url = f"{self.api_base}/chat/completions"
        last: str = ""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            payload = self._payload(prompt, system, max_tokens, schema, temp)
            try:
                r = self._session.post(url, json=payload, timeout=self.timeout)
            except requests.RequestException as exc:
                last = str(exc)
                time.sleep(2.0 * attempt)
                continue

            if r.status_code == 400:
                # Most likely an unsupported extra field. Drop them one at a
                # time rather than giving up on a server that works fine plain.
                body = r.text[:400]
                stale = (("response_format" in payload) != (schema is not None
                                                            and not self._no_schema)
                         or ("chat_template_kwargs" in payload) != (not self._no_template_kwargs))
                if stale:
                    # Another thread already narrowed the payload while this
                    # request was in flight. Retry with the current shape rather
                    # than blaming an extra that is no longer being sent.
                    continue
                if not self._no_schema and "response_format" in payload:
                    self._no_schema = True
                    last = f"400, retrying without response_format: {body}"
                    continue
                if not self._no_template_kwargs and "chat_template_kwargs" in payload:
                    self._no_template_kwargs = True
                    last = f"400, retrying without chat_template_kwargs: {body}"
                    continue
                last = f"400 {body}"
                break
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"{r.status_code} {r.text[:200]}"
                time.sleep(3.0 * attempt)
                continue
            try:
                r.raise_for_status()
                text = r.json()["choices"][0]["message"]["content"]
            except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
                last = f"{exc}: {r.text[:200]}"
                time.sleep(2.0 * attempt)
                continue

            text = (text or "").strip()
            with self._lock:
                self._cache[key] = text
                self.stats["called"] += 1
                if self._cache_path is not None:
                    _append_cache(self._cache_path, key, self.model, text,
                                  note=_note_of(prompt))
            return text

        with self._lock:
            self.stats["failed"] += 1
        self.last_error = last
        return None

    # ── many completions ────────────────────────────────────────────────────
    def complete_many(self, prompts: Sequence[str], system: str | None = None,
                      max_tokens: int = 96, schema: dict[str, Any] | None = None,
                      progress: Callable[[int], None] | None = None,
                      temperature: float | None = None,
                      variant: str = "") -> list[str | None]:
        """Run prompts concurrently, preserving input order.

        vLLM batches continuously on its side, so throughput comes from having
        several requests in flight rather than from packing several items into
        one prompt. One item per request also means a malformed answer can only
        ever damage its own row — batched prompts fail by silently misaligning
        answers to inputs, which is the kind of error that survives review.
        """
        self.probe_features(schema)
        results: list[str | None] = [None] * len(prompts)

        def work(i: int) -> None:
            results[i] = self.complete(prompts[i], system, max_tokens, schema,
                                       temperature, variant)
            if progress is not None:
                progress(1)

        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            list(pool.map(work, range(len(prompts))))
        return results


# ── cache plumbing ──────────────────────────────────────────────────────────
def _cache_key(model: str, system: str | None, prompt: str,
               temperature: float, variant: str) -> str:
    blob = "\x00".join([model, system or "", prompt, f"{temperature:g}", variant])
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def _note_of(prompt: str) -> str:
    """A short human-readable stub for debugging a cache entry.

    The prompt itself is deliberately *not* stored. At corpus scale the cache
    holds a few hundred thousand entries whose prompts are ~250 tokens of
    near-identical boilerplate, which would make the file hundreds of
    megabytes of text nobody reads. The key is a hash of the full prompt, so
    lookups are unaffected; this is only so a human can tell what a row was.
    """
    for line in prompt.splitlines():
        if line.startswith("HEADLINE:"):
            return line[9:].strip()[:160]
    return prompt[:160]


def _read_cache(path: Path) -> dict[str, str]:
    cache: dict[str, str] = {}
    if not path.exists():
        return cache
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                cache[rec["key"]] = rec["text"]
            except (ValueError, KeyError):
                continue        # a truncated final line after a hard kill
    return cache


def _append_cache(path: Path, key: str, model: str, text: str, note: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"key": key, "model": model, "text": text, "note": note}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def extract_json(text: str | None) -> dict[str, Any] | None:
    """Pull the first JSON object out of a model answer, tolerating chatter."""
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        pass
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start:i + 1])
                except ValueError:
                    start = -1
    return None


def iter_progress(total: int, desc: str) -> tuple[Callable[[int], None], Callable[[], None]]:
    """A tqdm callback pair, degrading to no-ops when tqdm is absent."""
    try:
        from tqdm import tqdm
    except ImportError:
        return (lambda n: None), (lambda: None)
    bar = tqdm(total=total, desc=desc, unit="row")
    lock = threading.Lock()

    def update(n: int) -> None:
        with lock:
            bar.update(n)

    return update, bar.close
