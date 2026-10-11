from __future__ import annotations

import os


FAULT_ENV = "BASALTKV_FAULT_POINT"


def crash_if(point: str) -> None:
    """Deterministic process-crash injection used only by the test harness."""
    if os.environ.get(FAULT_ENV) == point:
        os._exit(91)
