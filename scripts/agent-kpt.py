#!/usr/bin/env python3
import sys
from pathlib import Path

MIN_PYTHON = (3, 10)

if sys.version_info < MIN_PYTHON:
    found = ".".join(str(part) for part in sys.version_info[:3])
    print(
        "agent-kpt requires Python 3.10+; "
        f"this launcher is running on Python {found}.",
        file=sys.stderr,
    )
    print(
        "Select a newer interpreter and retry "
        "(for example: python3.11 on macOS/Linux or py -3.11 on Windows).",
        file=sys.stderr,
    )
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_kpt.cli import main

raise SystemExit(main())
