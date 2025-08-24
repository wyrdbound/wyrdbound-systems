"""Debug utilities for GRIMOIRE runner."""

# Global debug flag
_debug_enabled = False


def set_debug_enabled(enabled: bool) -> None:
    """Set the global debug flag."""
    global _debug_enabled
    _debug_enabled = enabled


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled."""
    return _debug_enabled


def debug_print(*args, **kwargs) -> None:
    """Print debug message only if debug mode is enabled."""
    if _debug_enabled:
        print("[DEBUG]", *args, **kwargs)
