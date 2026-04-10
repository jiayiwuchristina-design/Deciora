from __future__ import annotations

import os
from typing import Any


TRUTHY_DEBUG_VALUES = {"1", "true", "yes", "on", "debug"}
DEBUG_ENV_VARS = ("OPPORTUNITY_DEBUG", "RESEARCH_DEBUG", "APP_DEBUG")


def _is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in TRUTHY_DEBUG_VALUES


def is_debug_mode(session_state: Any | None = None) -> bool:
    if session_state is not None:
        try:
            if bool(session_state.get("developer_debug_mode")):
                return True
        except Exception:
            pass
    return any(_is_truthy(os.getenv(name)) for name in DEBUG_ENV_VARS)


def debug_mode_source(session_state: Any | None = None) -> str:
    if session_state is not None:
        try:
            if bool(session_state.get("developer_debug_mode")):
                return "session_state.developer_debug_mode"
        except Exception:
            pass
    for name in DEBUG_ENV_VARS:
        if _is_truthy(os.getenv(name)):
            return f"env:{name}"
    return "off"
