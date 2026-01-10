from __future__ import annotations

import time
from contextlib import contextmanager


def _now() -> float:
    return time.perf_counter()


def fmt_seconds(s: float) -> str:
    if s < 60:
        return f"{s:.2f}s"
    return f"{s/60:.1f}min"


@contextmanager
def step(title: str):
    start = _now()
    print(f"[START] {title}")
    try:
        yield
        cost = _now() - start
        print(f"[DONE ] {title} ({fmt_seconds(cost)})")
    except Exception as e:
        cost = _now() - start
        print(f"[FAIL ] {title} ({fmt_seconds(cost)}): {e}")
        raise
