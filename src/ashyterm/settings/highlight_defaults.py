"""Highlight defaults — re-exports + manager defaults.

Constants now live in highlight_models.py; this module re-exports for
backward compatibility and adds manager-level defaults.
"""

# Re-export from models — consumers may import from here
from .highlight_models import ANSI_COLOR_MAP, ANSI_MODIFIERS  # noqa: F401 — re-export

# Manager-level defaults (not data models)
HIGHLIGHT_DEFAULTS = {
    "enabled_for_local": True,
    "enabled_for_ssh": True,
    "cat_colorization": True,
    "shell_input_highlighting": False,
    "command_not_found_detection": True,
}

# Commands excluded from context-aware highlighting
DEFAULT_IGNORED_COMMANDS = [
    "grep", "egrep", "fgrep", "rg", "rga",
    "awk", "sed", "sd", "bat", "ls", "git",
    "vim", "nano", "nvim", "emacs", "htop",
    "btop", "top", "less", "more", "man", "info",
    "diff", "colordiff", "delta", "jq", "yq", "grc",
]
