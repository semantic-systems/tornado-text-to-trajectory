"""Which official texts each hazard has: one count per kind, from stages 20 and 24.

Kinds, in the order reports and the map show them:

* ``pns`` — the hazard's primary survey section (stage 20, ``primary_survey_of``);
* ``narrative`` — Storm Events event narratives (stage 24, ``narrative_of``);
* ``dat_comment`` — distinct DAT comments (stage 24, ``comment_of``);
* ``lsr_survey`` / ``lsr_real_time`` — LSRs linked to the hazard (stage 20,
  ``describes``), apart by the report's source field: a survey team's, or a
  spotter's, the public's, an emergency manager's and so on.

The first three are oracle text (written from the survey); LSRs are the
office's reports during and just after the event. News is not official text and
is not counted here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .. import config

KINDS = {"pns": "survey statement (PNS)", "narrative": "Storm Events narrative",
         "dat_comment": "DAT comment", "lsr_survey": "survey LSR",
         "lsr_real_time": "real-time LSR"}
ORACLE = ("pns", "narrative", "dat_comment")


def counts(tag: str) -> pd.DataFrame | None:
    """Per hazard (index ``hazard_uid``), the number of texts of each kind.

    ``None`` when neither stage 20 nor stage 24 has written its tables. A hazard
    with no text is absent; callers reindex.
    """
    P = config.PROCESSED_DIR
    parts = []
    nws_links, nws_refs = P / f"textlinks_nws_{tag}.csv", P / f"textrefs_nws_{tag}.csv"
    if nws_links.exists() and nws_refs.exists():
        links = pd.read_csv(nws_links, usecols=["textref_uid", "target_uid", "link_relation"],
                            low_memory=False)
        src = pd.read_csv(nws_refs, usecols=["textref_uid", "lsr_source"], low_memory=False)
        survey = src.lsr_source.astype(str).str.upper().str.contains("SURVEY")
        lsr_kind = dict(zip(src.textref_uid, np.where(survey, "lsr_survey", "lsr_real_time")))
        pns = links[links.link_relation == "primary_survey_of"].assign(kind="pns")
        lsr = links[links.link_relation == "describes"]
        parts += [pns, lsr.assign(kind=lsr.textref_uid.map(lsr_kind))]
    rec_links = P / f"textlinks_records_{tag}.csv"
    if rec_links.exists():
        rl = pd.read_csv(rec_links, usecols=["textref_uid", "target_uid", "link_level",
                                             "link_relation"])
        rl = rl[rl.link_level == "hazard"]
        kind = {"narrative_of": "narrative", "comment_of": "dat_comment"}
        parts.append(rl[rl.link_relation.isin(kind)].assign(kind=rl.link_relation.map(kind)))
    if not parts:
        return None
    links = (pd.concat(parts)[["textref_uid", "target_uid", "kind"]]
             .drop_duplicates(["textref_uid", "target_uid"]))
    table = links.groupby(["target_uid", "kind"]).size().unstack(fill_value=0)
    table.index.name = "hazard_uid"
    return table.reindex(columns=list(KINDS), fill_value=0)
