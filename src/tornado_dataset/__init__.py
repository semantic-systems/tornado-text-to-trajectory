"""Pipeline for a tornado dataset pairing DAT damage geometry with text.

Stages (each a script in ``scripts/``) are numbered by phase: 1x events,
2x text collection, 3x text selection and linking, 4x annotation and
analysis, 5x method studies. The README lists them in run order; the events
phase, for example:

* ``10_fetch_dat``          — download DAT lines/polygons for the configured window
* ``11_link_geometry``      — link damage lines to damage polygons, with evidence
* ``12_build_hazards``      — assemble hazards (tracks) and episodes (outbreaks)
* ``13_fetch_references``   — download NCEI Storm Events and SPC's tornado file
* ``14_match_references``   — match both to DAT hazards
* ``17_qa_events``          — the events quality report

See ``config.py`` for the window and every methodological threshold.
"""

__version__ = "0.1.0"
