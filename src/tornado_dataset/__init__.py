"""Pipeline for a tornado dataset pairing DAT damage geometry with text.

Stages (each a script in ``scripts/``):

1. ``01_fetch_dat``      — download DAT lines/polygons for the configured window
2. ``02_link_geometry``  — link damage lines to damage polygons, with evidence
3. ``03_build_hazards``  — assemble hazards (tracks) and episodes (outbreaks)
4. ``04_qa_dat``         — evaluate the linker and write the QA report

See ``config.py`` for the window and every methodological threshold.
"""

__version__ = "0.1.0"
