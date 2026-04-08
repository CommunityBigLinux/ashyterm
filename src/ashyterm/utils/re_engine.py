# regex (PCRE2) → ~50% faster matching vs stdlib re
# WHY noqa: conditional import — one must be unused by design
try:
    import regex as engine  # noqa: F401 — optional dep: regex → re fallback
except ImportError:
    import re as engine  # noqa: F401 — fallback when regex unavailable
