"""Compatibility shim — the parser now lives in ``tornado_dataset.text.lexisnexis``.

Kept so that ``python src/parse_lexisnexis_rtf.py`` and any existing imports keep
working unchanged. New code should import from the package instead::

    from tornado_dataset.text.lexisnexis import parse_directory, to_dataframe
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tornado_dataset.text.lexisnexis import *  # noqa: F401,F403
from tornado_dataset.text.lexisnexis import main

if __name__ == "__main__":
    main()
