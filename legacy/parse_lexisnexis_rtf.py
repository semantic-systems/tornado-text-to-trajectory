"""Compatibility shim — the parser now lives in ``tornado_dataset.text.lexisnexis``.

Kept so that existing imports keep working. New code should import from the
package instead, and the import itself is stage 23::

    from tornado_dataset.text.lexisnexis import parse_directory, to_dataframe
    python scripts/23_import_lexisnexis.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tornado_dataset.text.lexisnexis import *  # noqa: F401,F403

if __name__ == "__main__":
    sys.exit("run scripts/23_import_lexisnexis.py instead")
