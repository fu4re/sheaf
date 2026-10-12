"""Entry point: `python -m tcg ...`."""
from __future__ import annotations

import sys

from tcg.cli import main

if __name__ == "__main__":
    sys.exit(main())
