"""Shared visual language for the figures and the interactive map.

Colours come from one validated palette rather than per-chart choices, so a
reader who learns "darker blue = stronger tornado" on the map reads the figures
the same way.

**EF is encoded with an ordinal ramp** (one hue, light→dark) because the scale is
ordered — never a rainbow, and never a value-ramp on the bar charts, where bar
length already carries the magnitude and a second encoding would be redundant.

The ramp has five steps because that is how many the blue ramp supports while
keeping every adjacent pair visibly apart (ΔL ≥ 0.06) *and* the lightest step
clear of the surface (≥ 2:1) — checked with the palette validator, not by eye.
So EF4 and EF5 share the top class, which is also the conventional
"violent tornado" grouping. Unrated records (``UNKNOWN``, ``EFU``, ``TSTM/Wind``,
missing) are a separate grey class, never a ramp step: absence of a rating is not
a low rating.
"""

from __future__ import annotations

import re

# ── surfaces and ink ─────────────────────────────────────────────────────────
LIGHT = {
    "surface": "#fcfcfb", "plane": "#f9f9f7", "primary": "#0b0b0b",
    "secondary": "#52514e", "muted": "#898781", "grid": "#e1e0d9",
    "axis": "#c3c2b7", "series1": "#2a78d6", "series2": "#eb6834",
    "unrated": "#898781",
}
DARK = {
    "surface": "#1a1a19", "plane": "#0d0d0d", "primary": "#ffffff",
    "secondary": "#c3c2b7", "muted": "#898781", "grid": "#2c2c2a",
    "axis": "#383835", "series1": "#3987e5", "series2": "#d95926",
    "unrated": "#898781",
}

# Ordinal ramps: light→dark on the light surface, and its own steps chosen for
# the dark surface (a flipped light ramp would not clear the dark band).
EF_RAMP_LIGHT = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]
EF_RAMP_DARK = ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4"]

# Sequential ramp for continuous magnitude (density surfaces).
SEQUENTIAL_LIGHT = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf",
                    "#184f95", "#0d366b"]

EF_CLASSES = ["EF0", "EF1", "EF2", "EF3", "EF4+"]
EF_CLASS_LABELS = {"EF0": "EF0", "EF1": "EF1", "EF2": "EF2", "EF3": "EF3",
                   "EF4+": "EF4–EF5"}
UNRATED = "unrated"

_EF_NUMBER = re.compile(r"EF\s*[-]?\s*([0-5])", re.IGNORECASE)


def ef_class(value: object) -> str:
    """Map a DAT ``efscale`` string to one of five ordered classes or ``unrated``."""
    text = str(value or "").strip().upper()
    match = _EF_NUMBER.search(text.replace(" ", ""))
    if not match:
        return UNRATED
    number = int(match.group(1))
    return "EF4+" if number >= 4 else f"EF{number}"


def ef_colour(ef: str, dark: bool = False) -> str:
    ramp = EF_RAMP_DARK if dark else EF_RAMP_LIGHT
    palette = DARK if dark else LIGHT
    return ramp[EF_CLASSES.index(ef)] if ef in EF_CLASSES else palette["unrated"]


def matplotlib_style() -> dict:
    """Recessive chrome: hairline grid, no top/right spines, muted ticks."""
    return {
        "figure.facecolor": LIGHT["surface"], "axes.facecolor": LIGHT["surface"],
        "savefig.facecolor": LIGHT["surface"],
        "axes.edgecolor": LIGHT["axis"], "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": LIGHT["grid"], "grid.linewidth": 0.8,
        "grid.linestyle": "-", "axes.axisbelow": True,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlepad": 10,
        "axes.titlecolor": LIGHT["primary"],
        "axes.labelsize": 10, "axes.labelcolor": LIGHT["secondary"],
        "xtick.color": LIGHT["muted"], "ytick.color": LIGHT["muted"],
        "xtick.labelcolor": LIGHT["secondary"], "ytick.labelcolor": LIGHT["secondary"],
        "xtick.labelsize": 9, "ytick.labelsize": 9,
        "font.family": "sans-serif",
        "font.sans-serif": ["system-ui", "-apple-system", "Segoe UI", "Helvetica", "Arial"],
        "font.size": 10, "legend.frameon": False, "legend.fontsize": 9,
        "figure.dpi": 130, "savefig.bbox": "tight",
    }
