"""A page of samples from stage 25, to check the groups of edits by eye.

One self-contained HTML file: stratified samples, one at a time, with the wording
the method counted highlighted in the texts, so a reader sees what the decision
rested on. Strata cover what an audit needs: random hazards (the typical case),
the cases closest to the rule on either side, bridged groups, real-time LSRs
grouped with survey text, survey statement and narrative left apart (paraphrase),
and comparison pairs that linked (false links, or copies across tornadoes).

Highlighting, per token:

* coloured: inside a specific run shared with another text of the same account;
* orange: in a pair view, inside a specific run the two texts share;
* dotted: inside a specific run shared only with a text of another account of
  the hazard (sharing below the link rule);
* grey: in common runs only (texts of three or more tornadoes), not evidence.

Each sample takes a verdict and a note, kept in the browser (``localStorage``)
and exported as CSV.
"""

from __future__ import annotations

import html
import json
import random
from typing import Any

import pandas as pd

from . import same_source as ss

SHORT = {"pns": "PNS", "storm_events_narrative": "narrative", "dat_comment": "DAT comment",
         "lsr": "LSR"}
ORACLE_TYPES = {"pns", "storm_events_narrative", "dat_comment"}
LINK = ["same account", "independent", "unsure"]

# key, title, question, kind, verdict options
STRATA = [
    ("hazards", "Random hazards", "Are the accounts right? Texts in one coloured box should be "
     "edits of one account; texts in different boxes independent descriptions.", "hazard",
     ["groups right", "groups wrong", "unsure"]),
    ("borderline", "Links just over the rule", "Linked with few shared tokens. Is this one "
     "account (copied wording), or only a shared template or place description?", "pair", LINK),
    ("near_miss", "Just under the rule", "Some specific wording shared, but too little to link. "
     "Independent, or a copy the rule misses?", "pair", LINK),
    ("low_coverage", "Links with low coverage", "Linked, though the shared wording is a small "
     "part of both texts. Is a shared passage enough to call them one account?", "pair", LINK),
    ("pns_narrative_apart", "PNS and narrative left apart", "Survey statement and narrative of "
     "one tornado, not linked. Independent, or a paraphrase the method cannot see?", "pair",
     LINK),
    ("bridged", "Bridged groups", "Some members are linked only through others. Do they all go "
     "back to one account?", "hazard", ["groups right", "groups wrong", "unsure"]),
    ("realtime_lsr", "Real-time LSRs in a survey account", "A spotter, public or EM LSR grouped "
     "with survey text. Does it really share the survey's wording?", "hazard",
     ["groups right", "groups wrong", "unsure"]),
    ("comparison_same_episode", "Comparison pairs that linked: same episode",
     "Texts of two different tornadoes of one episode, linked by the rule. A copy across "
     "tornadoes (one account attached to both), or a false link?", "comparison",
     ["copy across tornadoes", "false link", "unsure"]),
    ("comparison_other_episode", "Comparison pairs that linked: other episode",
     "Texts of two tornadoes in different episodes, linked by the rule. A copy (a reused "
     "text), or a false link?", "comparison", ["copy across tornadoes", "false link", "unsure"]),
]


def esc(text: Any) -> str:
    return html.escape(str(text), quote=True)


# ── marking and rendering a text ───────────────────────────────────────────

def token_states(body: str, prof: ss.Profile, mates: set[int], others: set[int],
                 mate_class: str) -> tuple[list[tuple[str, int, int]], list[str]]:
    """Each token's display class (see the module docstring)."""
    spans = ss.token_spans(body)
    n, k = len(spans), prof.k
    inside, mate, other = [False] * n, [False] * n, [False] * n
    for i, (h, specific) in enumerate(zip(prof.runs, prof.specific)):
        if not specific:
            continue
        for j in range(i, min(i + k, n)):
            inside[j] = True
            if h in mates:
                mate[j] = True
            elif h in others:
                other[j] = True
    states = [mate_class if mate[j] else "x" if other[j] else "" if inside[j] else "c"
              for j in range(n)]
    return spans, states


def render(body: str, spans: list[tuple[str, int, int]], states: list[str]) -> str:
    """The text with runs of equally marked tokens wrapped in one span each."""
    text = str(body)
    if len(text.lower()) != len(text):      # a rare letter whose lower case is longer
        text = text.lower()
    out: list[str] = []
    buf: list[str] = []
    cur = ""
    pos = 0

    def flush() -> None:
        if buf:
            out.append(f'<span class="{cur}">{"".join(buf)}</span>' if cur else "".join(buf))
            buf.clear()

    for (_, a, b), s in zip(spans, states):
        gap = esc(text[pos:a])
        if s != cur:
            flush()
            out.append(gap)
            cur = s
        else:
            buf.append(gap)
        buf.append(esc(text[a:b]))
        pos = b
    flush()
    out.append(esc(text[pos:]))
    return "".join(out)


# ── the page ───────────────────────────────────────────────────────────────

class Page:
    def __init__(self, links: pd.DataFrame, texts: pd.DataFrame, rows: pd.DataFrame,
                 r: dict) -> None:
        self.r, self.rows = r, rows
        self.info = texts.set_index("textref_uid")
        self.by_hazard = {h: g for h, g in rows.groupby("hazard_uid")}
        self.hazard = (links.drop_duplicates("hazard_uid")
                       .set_index("hazard_uid")[["hazard_source", "episode_uid",
                                                 "convective_day"]])
        pairs = r["pairs"]
        self.pair = {}
        for p in pairs.itertuples():
            self.pair[(p.hazard_uid, p.a_uid, p.b_uid)] = p
            self.pair[(p.hazard_uid, p.b_uid, p.a_uid)] = p

    # pieces
    def text_meta(self, u: str, label: str, row: Any = None, extra: str = "") -> str:
        i = self.info.loc[u]
        kind = SHORT.get(i.source_type, i.source_type)
        if i.source_type == "lsr" and isinstance(i.lsr_class, str):
            kind = f"{'survey' if i.lsr_class == 'survey' else 'real-time'} LSR"
        bits = [f"<b>{esc(label)}</b>", f'<span class="kind k-{esc(i.source_type)}">'
                f"{esc(kind)}</span>"]
        if isinstance(i.office, str):
            bits.append(esc(i.office))
        if isinstance(i.published_at, str) and i.source_type in ("pns", "lsr"):
            when = i.published_at[:16].replace("T", " ")
            bits.append(esc(when) + (" (event time)" if i.source_type == "lsr" else ""))
        prof = self.r["profiles"][u]
        bits.append(f"{prof.n_specific} of {prof.n_tokens} tokens specific")
        if row is not None:
            if row.is_representative and row.group_size > 1:
                bits.append('<span class="tag">representative</span>')
            if not row.comparable:
                bits.append('<span class="tag warn">too short to link</span>')
        if extra:
            bits.append(extra)
        bits.append(f'<code title="{esc(u)}">{esc(u[-8:])}</code>')
        return " · ".join(bits)

    def text_card(self, u: str, label: str, mates: set[int], others: set[int],
                  mate_class: str, row: Any = None, extra: str = "",
                  profiles: dict | None = None, focus: bool = False) -> str:
        prof = (profiles or self.r["profiles"])[u]
        body = self.info.at[u, "body"]
        spans, states = token_states(body, prof, mates, others, mate_class)
        return (f'<article class="text{" focus" if focus else ""}">'
                f'<div class="meta">{self.text_meta(u, label, row, extra)}</div>'
                f'<div class="body">{render(body, spans, states)}</div></article>')

    def layout(self, hazard: str) -> tuple[list[list[str]], dict[str, str], dict[str, int]]:
        """Accounts in display order, a label per text and a colour index per account."""
        g = self.by_hazard[hazard]
        order = self.r["order"]
        groups: dict[str, list[str]] = {}
        for u, gid in zip(g.textref_uid, g.edit_group):
            groups.setdefault(gid, []).append(u)
        rep = dict(zip(g.edit_group, g.representative_uid))
        # Larger accounts first; within one, the representative first.
        accounts = [sorted(groups[gid], key=lambda u, r=rep[gid]: (u != r, order[u]))
                    for gid in sorted(groups, key=lambda x: (-len(groups[x]), order[rep[x]]))]
        labels, colour, n, c = {}, {}, 0, 0
        for members in accounts:
            for u in members:
                n += 1
                labels[u] = f"T{n}"
            if len(members) > 1:
                for u in members:
                    colour[u] = c % 6
                c += 1
        return accounts, labels, colour

    def hazard_header(self, hazard: str) -> str:
        h = self.hazard.loc[hazard]
        g = self.by_hazard[hazard]
        ep = h.episode_uid if isinstance(h.episode_uid, str) else "no episode"
        return (f'<div class="hz">{esc(str(h.hazard_source).upper())} hazard '
                f'<code title="{esc(hazard)}">{esc(hazard[-8:])}</code> · '
                f"{esc(h.convective_day)} · episode <code>{esc(ep[-8:])}</code> · "
                f"{len(g)} text{'s' if len(g) != 1 else ''} in {g.hazard_accounts.iat[0]} "
                f"account{'s' if g.hazard_accounts.iat[0] != 1 else ''}</div>")

    def accounts_view(self, hazard: str) -> str:
        accounts, labels, colour = self.layout(hazard)
        g = self.by_hazard[hazard].set_index("textref_uid")
        prof = self.r["profiles"]
        out = []
        for letter, members in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 9, accounts):
            row0 = g.loc[members[0]]
            outside = set().union(*[prof[u].run_set for m in accounts if m is not members
                                    for u in m]) if len(accounts) > 1 else set()
            cls = f"acct a{colour[members[0]]}" if members[0] in colour else "acct solo"
            title = (f"Account {letter}: {len(members)} texts" if len(members) > 1
                     else f"Account {letter}: on its own")
            if row0.bridged:
                title += ' <span class="tag">bridged</span>'
            cards = []
            for u in members:
                row = g.loc[u]
                mates = set().union(*[prof[v].run_set for v in members if v != u]) \
                    if len(members) > 1 else set()
                extra = ""
                if isinstance(row.contained_in, str):
                    extra = (f"contained in {labels.get(row.contained_in, '?')} "
                             f"({row.max_coverage:.2f})")
                elif len(members) > 1 and not row.is_representative \
                        and pd.notna(row.coverage_by_representative):
                    extra = f"covered {row.coverage_by_representative:.2f} by the representative"
                cards.append(self.text_card(u, labels[u], mates, outside,
                                            f"m{colour.get(u, 0)}", row, extra))
            out.append(f'<div class="{cls}"><h4>{title}</h4>{"".join(cards)}</div>')
        return "".join(out) + self.matrix(hazard, labels)

    def matrix(self, hazard: str, labels: dict[str, str]) -> str:
        uids = sorted(labels, key=lambda u: int(labels[u][1:]))
        if len(uids) < 2 or len(uids) > 16:
            return ""
        m = self.r["min_shared"]
        head = "".join(f"<th>{labels[u]}</th>" for u in uids)
        body = []
        for a in uids:
            cells = []
            for b in uids:
                if a == b:
                    cells.append('<td class="d">—</td>')
                    continue
                p = self.pair.get((hazard, a, b))
                if p is None:
                    cells.append('<td class="na">·</td>')
                    continue
                cov = p.a_in_b if p.a_uid == a else p.b_in_a
                cells.append(f'<td class="{"lk" if p.shared >= m else ""}" '
                             f'title="{labels[a]} covered {cov:.2f} by {labels[b]}">'
                             f"{p.shared}<small>{cov:.2f}</small></td>")
            body.append(f"<tr><th>{labels[a]}</th>{''.join(cells)}</tr>")
        return (f'<details class="matrix"><summary>Pair table: shared tokens (link at ≥{m}); '
                f"small: share of the row's text covered by the column's</summary>"
                f"<table><tr><th></th>{head}</tr>{''.join(body)}</table></details>")

    def pair_line(self, p: Any, la: str, lb: str) -> str:
        m = self.r["min_shared"]
        verdict = "linked" if p.shared >= m else "not linked"
        return (f'<div class="pairline"><b>{la} – {lb}</b>: {p.shared} shared specific tokens '
                f"(rule ≥{m}: <b>{verdict}</b>) · {la} covered {p.a_in_b:.2f} by {lb}, "
                f"{lb} covered {p.b_in_a:.2f} by {la}</div>")

    # samples
    def hazard_sample(self, hazard: str) -> str:
        return self.hazard_header(hazard) + self.accounts_view(hazard)

    def pair_sample(self, hazard: str, a: str, b: str) -> str:
        p = self.pair[(hazard, a, b)]
        a, b = p.a_uid, p.b_uid
        _, labels, _ = self.layout(hazard)
        g = self.by_hazard[hazard].set_index("textref_uid")
        prof = self.r["profiles"]
        cards = [self.text_card(u, labels[u], prof[v].run_set, set(), "p", g.loc[u], focus=True)
                 for u, v in ((a, b), (b, a))]
        n = len(g)
        return (self.hazard_header(hazard) + self.pair_line(p, labels[a], labels[b])
                + f'<div class="two">{"".join(cards)}</div>'
                + f'<details class="all"><summary>All {n} texts of this hazard, by account'
                  f"</summary>{self.accounts_view(hazard)}</details>")

    def comparison_sample(self, kept: str, stand_in: str, scope: str) -> str:
        prof = self.r["profiles_pair"]
        s = ss.compare(prof[kept], prof[stand_in])
        meta = self.r["meta"]
        cards = []
        for u, v, label in ((kept, stand_in, "kept"), (stand_in, kept, "stand-in")):
            hz = sorted(meta[u]["hazards"])
            ep = sorted(meta[u]["episodes"])
            where = (f"hazard{'s' if len(hz) > 1 else ''} "
                     + ", ".join(f'<code title="{esc(h)}">{esc(h[-8:])}</code>' for h in hz)
                     + f" · episode <code>{esc(ep[0][-8:])}</code>")
            cards.append(self.text_card(u, label, prof[v].run_set, set(), "p", extra=where,
                                        profiles=prof, focus=True))
        return (f'<div class="pairline">{s.shared} shared specific tokens (rule '
                f"≥{self.r['min_shared']}) · kept covered {s.a_in_b:.2f}, stand-in "
                f"{s.b_in_a:.2f} · {esc(scope.replace('_', ' '))}. For a comparison pair a run "
                "counts as specific in up to one hazard besides the two texts' own.</div>"
                + f'<div class="two">{"".join(cards)}</div>')


def draw(page: Page, rng: random.Random, n: int) -> list[dict]:
    """The samples of every stratum, each ``{stratum, id, hazard, a, b, html}``."""
    r, rows = page.r, page.rows
    pairs, m = r["pairs"].sort_values(["hazard_uid", "a_uid", "b_uid"]), r["min_shared"]
    cov = pairs[["a_in_b", "b_in_a"]].max(axis=1)
    linked = pairs.shared >= m
    hz = rows.drop_duplicates("hazard_uid")
    oracle_groups = set(rows.edit_group[rows.source_type.isin(ORACLE_TYPES)])
    hazard_pools = {
        "hazards": sorted(hz.hazard_uid[hz.hazard_texts >= 2]),
        "bridged": sorted(set(rows.hazard_uid[rows.bridged])),
        "realtime_lsr": sorted(set(rows.hazard_uid[(rows.lsr_class == "real_time")
                                                   & rows.edit_group.isin(oracle_groups)])),
    }
    pair_pools = {
        "borderline": pairs[linked & (pairs.shared < m + 5)],
        "near_miss": pairs[~linked & (pairs.shared >= 5)],
        "low_coverage": pairs[linked & (cov < 0.25)],
        "pns_narrative_apart": pairs[~linked & (pairs.a_type == "pns")
                                     & (pairs.b_type == "storm_events_narrative")],
    }
    comparison_pools = {
        f"comparison_{scope}": c[c.shared >= m].sort_values(["kept_uid", "stand_in_uid"])
        for scope, c in r["comparison"].items()}

    out = []
    for key, *_ in STRATA:
        if key in hazard_pools:
            pool = hazard_pools[key]
            for h in rng.sample(pool, min(n, len(pool))):
                out.append({"stratum": key, "id": f"{key}:{h}", "hazard": h, "a": "", "b": "",
                            "pool": len(pool), "html": page.hazard_sample(h)})
        elif key in pair_pools:
            pool = pair_pools[key]
            for i in rng.sample(range(len(pool)), min(n, len(pool))):
                p = pool.iloc[i]
                out.append({"stratum": key, "id": f"{key}:{p.hazard_uid}:{p.a_uid}:{p.b_uid}",
                            "hazard": p.hazard_uid, "a": p.a_uid, "b": p.b_uid,
                            "pool": len(pool),
                            "html": page.pair_sample(p.hazard_uid, p.a_uid, p.b_uid)})
        else:
            pool = comparison_pools[key]
            scope = key.removeprefix("comparison_")
            for i in rng.sample(range(len(pool)), min(n, len(pool))):
                p = pool.iloc[i]
                out.append({"stratum": key, "id": f"{key}:{p.kept_uid}:{p.stand_in_uid}",
                            "hazard": "", "a": p.kept_uid, "b": p.stand_in_uid,
                            "pool": len(pool),
                            "html": page.comparison_sample(p.kept_uid, p.stand_in_uid, scope)})
    return out


def build(links: pd.DataFrame, texts: pd.DataFrame, rows: pd.DataFrame, r: dict, *,
          tag: str, per_stratum: int, seed: int) -> str:
    page = Page(links, texts, rows, r)
    samples = draw(page, random.Random(f"{seed}-samples"), per_stratum)
    strata = {key: {"title": t, "question": q, "kind": kind, "options": opts}
              for key, t, q, kind, opts in STRATA}
    pools = {}
    for s in samples:
        pools[s["stratum"]] = s["pool"]
    sections = "".join(
        f'<section class="sample" hidden data-id="{esc(s["id"])}" '
        f'data-stratum="{s["stratum"]}" data-hazard="{esc(s["hazard"])}" '
        f'data-a="{esc(s["a"])}" data-b="{esc(s["b"])}">{s["html"]}</section>'
        for s in samples)
    nav = "".join(
        f'<button class="st" data-stratum="{key}"><span>{esc(meta["title"])}</span>'
        f'<small data-count="{key}">{sum(s["stratum"] == key for s in samples)} of '
        f'{pools.get(key, 0):,}</small></button>'
        for key, meta in strata.items() if pools.get(key))
    config = {"strata": strata, "storageKey": f"same_source_verdicts:{tag}:{seed}",
              "rule": r["min_shared"], "tag": tag}
    return TEMPLATE.replace("__NAV__", nav).replace("__SECTIONS__", sections).replace(
        "__CONFIG__", json.dumps(config).replace("</", "<\\/")).replace(
        "__TAG__", esc(tag)).replace("__RULE__", str(r["min_shared"])).replace(
        "__N__", str(per_stratum)).replace("__SEED__", str(seed))


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Same-source samples</title>
<style>
:root{--bg:#fafaf8;--panel:#fff;--ink:#1d1d1f;--mute:#6b6b70;--line:#e3e2dd;--accent:#2e6f95;
--p:#f6c88f;--x:#8a8a8a;--c:#a4a4a8;--warn:#b4442f;
--a0:#cfe3f3;--a1:#d6ecd2;--a2:#f3dccd;--a3:#e5d9f2;--a4:#f5ecc4;--a5:#d4ecea;
--b0:#4b8bbf;--b1:#5c9e52;--b2:#c47a48;--b3:#8a68b3;--b4:#b59a2c;--b5:#3f9690}
@media (prefers-color-scheme:dark){:root{--bg:#161618;--panel:#1f1f22;--ink:#e9e9ec;--mute:#9a9aa2;
--line:#34343a;--accent:#7fb3d8;--p:#8a5a22;--x:#9a9aa2;--c:#6e6e76;--warn:#e07b65;
--a0:#1f3a50;--a1:#253f22;--a2:#4a3020;--a3:#352a49;--a4:#443b16;--a5:#1c3e3b}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,system-ui,
"Segoe UI",sans-serif}
.wrap{display:grid;grid-template-columns:260px 1fr;min-height:100vh}
nav{border-right:1px solid var(--line);padding:16px;position:sticky;top:0;height:100vh;
overflow:auto;background:var(--panel)}
nav h1{font-size:15px;margin:0 0 4px}
nav p{color:var(--mute);font-size:12px;margin:0 0 12px}
.st{display:block;width:100%;text-align:left;border:1px solid transparent;background:none;
color:inherit;padding:8px;border-radius:6px;cursor:pointer;font:inherit}
.st small{display:block;color:var(--mute);font-size:11px}
.st:hover{background:var(--bg)}.st.on{border-color:var(--accent);background:var(--bg)}
.legend{font-size:12px;color:var(--mute);margin-top:16px;border-top:1px solid var(--line);
padding-top:12px}.legend div{margin:4px 0}
main{padding:0 28px 28px;max-width:1300px}
.bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px}
.bar .pos{color:var(--mute);margin-right:auto}
.ctl{position:sticky;top:0;z-index:2;background:var(--bg);padding:10px 0 4px;
border-bottom:1px solid var(--line);margin-bottom:12px}
button.b{border:1px solid var(--line);background:var(--panel);color:inherit;padding:6px 12px;
border-radius:6px;cursor:pointer;font:inherit}
button.b:hover{border-color:var(--accent)}
button.v.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.question{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);
padding:8px 12px;border-radius:6px;margin:0 0 12px}
.hz{color:var(--mute);margin-bottom:8px}
.pairline{margin:8px 0 12px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.acct{border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin:10px 0;
background:var(--panel)}
.acct h4{margin:0 0 6px;font-size:13px}
.acct.solo{border-style:dashed}
.a0{border-left:5px solid var(--b0)}.a1{border-left:5px solid var(--b1)}
.a2{border-left:5px solid var(--b2)}.a3{border-left:5px solid var(--b3)}
.a4{border-left:5px solid var(--b4)}.a5{border-left:5px solid var(--b5)}
.text{border-top:1px solid var(--line);padding:6px 0}
.acct .text:first-of-type{border-top:0}
.two .text{border:1px solid var(--line);border-radius:8px;padding:8px 10px;background:var(--panel)}
.meta{font-size:12px;color:var(--mute);margin-bottom:4px}
.meta b{color:var(--ink)}
.body{white-space:pre-wrap;font-size:13.5px}
.kind{padding:0 5px;border-radius:4px;background:var(--bg);border:1px solid var(--line)}
.tag{padding:0 5px;border-radius:4px;border:1px solid var(--accent);color:var(--accent)}
.tag.warn{border-color:var(--warn);color:var(--warn)}
code{font-size:11px}
.m0{background:var(--a0)}.m1{background:var(--a1)}.m2{background:var(--a2)}
.m3{background:var(--a3)}.m4{background:var(--a4)}.m5{background:var(--a5)}
.p{background:var(--p)}
.x{text-decoration:underline dotted var(--x);text-underline-offset:3px}
.c{color:var(--c)}
details{margin:12px 0}summary{cursor:pointer;color:var(--accent)}
table{border-collapse:collapse;margin-top:8px;font-size:12px}
td,th{border:1px solid var(--line);padding:3px 6px;text-align:center}
td small{display:block;color:var(--mute);font-size:10px}
td.lk{background:var(--a0);font-weight:600}td.d,td.na{color:var(--mute)}
textarea{width:100%;min-height:44px;margin-top:8px;background:var(--panel);color:inherit;
border:1px solid var(--line);border-radius:6px;padding:6px;font:inherit}
.keys{color:var(--mute);font-size:12px}
@media (max-width:800px){.wrap{grid-template-columns:1fr}nav{position:static;height:auto}
.two{grid-template-columns:1fr}main{padding:16px}}
</style></head><body><div class="wrap">
<nav><h1>Same-source samples</h1>
<p>Tag __TAG__ · rule ≥__RULE__ shared tokens · up to __N__ per stratum · seed __SEED__</p>
__NAV__
<div class="legend">
<div><span class="m0">coloured</span>: shared with a text of the same account</div>
<div><span class="p">orange</span>: shared by the two texts in question</div>
<div><span class="x">dotted</span>: shared only with another account (below the rule)</div>
<div><span class="c">grey</span>: common wording (3+ tornadoes), not evidence</div>
<div style="margin-top:8px">Only runs of 5 tokens count; a highlighted stretch is one or
more such runs.</div>
<div style="margin-top:8px"><button class="b" id="export">Export verdicts (CSV)</button></div>
<div id="done" style="margin-top:6px"></div>
</div></nav>
<main>
<div class="ctl"><div class="bar"><span class="pos" id="pos"></span>
<button class="b" id="prev">← prev</button><button class="b" id="next">next →</button></div>
<div class="bar" id="verdicts"></div></div>
<p class="question" id="question"></p>
<textarea id="note" placeholder="note (kept with the verdict)"></textarea>
<p class="keys">Keys: ← → or j k to move, 1 2 3 for a verdict.</p>
__SECTIONS__
</main></div>
<script>
const CFG = __CONFIG__;
const all = [...document.querySelectorAll("section.sample")];
let store = {};
try { store = JSON.parse(localStorage.getItem(CFG.storageKey) || "{}"); } catch (e) {}
function save() { try { localStorage.setItem(CFG.storageKey, JSON.stringify(store)); } catch (e) {} }
let stratum = all.length ? all[0].dataset.stratum : null, idx = 0;
const list = () => all.filter(s => s.dataset.stratum === stratum);
function show() {
  all.forEach(s => s.hidden = true);
  const L = list(); if (!L.length) return;
  idx = Math.max(0, Math.min(idx, L.length - 1));
  const s = L[idx]; s.hidden = false;
  const meta = CFG.strata[stratum];
  document.getElementById("pos").textContent = `${meta.title} · ${idx + 1} of ${L.length}`;
  document.getElementById("question").textContent = meta.question;
  const v = store[s.dataset.id] || {};
  const bar = document.getElementById("verdicts"); bar.innerHTML = "";
  meta.options.forEach((o, i) => {
    const b = document.createElement("button");
    b.className = "b v" + (v.verdict === o ? " on" : ""); b.textContent = `${i + 1} ${o}`;
    b.onclick = () => verdict(o); bar.appendChild(b);
  });
  document.getElementById("note").value = v.note || "";
  document.querySelectorAll(".st").forEach(b => b.classList.toggle("on", b.dataset.stratum === stratum));
  history.replaceState(null, "", `#${stratum}/${idx + 1}`);
  tally(); window.scrollTo(0, 0);
}
function current() { return list()[idx]; }
function record(patch) {
  const s = current(); if (!s) return;
  const d = s.dataset;
  store[d.id] = Object.assign(store[d.id] || {}, {stratum: d.stratum, hazard: d.hazard,
                              a: d.a, b: d.b}, patch);
  save();
}
function verdict(o) { record({verdict: o}); show(); }
function tally() {
  const n = Object.values(store).filter(v => v.verdict).length;
  document.getElementById("done").textContent = `${n} verdicts so far`;
}
document.getElementById("note").addEventListener("input", e => record({note: e.target.value}));
document.getElementById("prev").onclick = () => { idx--; show(); };
document.getElementById("next").onclick = () => { idx++; show(); };
document.querySelectorAll(".st").forEach(b => b.onclick = () => { stratum = b.dataset.stratum; idx = 0; show(); });
document.addEventListener("keydown", e => {
  if (e.target.tagName === "TEXTAREA") return;
  if (e.key === "ArrowRight" || e.key === "j") { idx++; show(); }
  else if (e.key === "ArrowLeft" || e.key === "k") { idx--; show(); }
  else if (["1", "2", "3"].includes(e.key)) {
    const o = CFG.strata[stratum].options[+e.key - 1]; if (o) verdict(o);
  }
});
document.getElementById("export").onclick = () => {
  const q = x => `"${String(x ?? "").replace(/"/g, '""')}"`;
  const lines = [["sample", "stratum", "hazard_uid", "text_a", "text_b", "verdict", "note"].join(",")];
  for (const [id, v] of Object.entries(store))
    lines.push([id, v.stratum, v.hazard, v.a, v.b, v.verdict, v.note].map(q).join(","));
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([lines.join("\\n")], {type: "text/csv"}));
  a.download = `same_source_verdicts_${CFG.tag}.csv`; a.click();
};
const m = location.hash.match(/^#([a-z_]+)\\/(\\d+)$/);
if (m && CFG.strata[m[1]]) { stratum = m[1]; idx = +m[2] - 1; }
show();
</script></body></html>
"""
