"""Highlight data models — HighlightRule, HighlightContext, HighlightConfig."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ashyterm.utils.re_engine import engine as _re_engine

# ANSI color name → index (0-15). Stdlib: 0-7, Bright: 8-15.
ANSI_COLOR_MAP = {
    "black": 0, "red": 1, "green": 2, "yellow": 3,
    "blue": 4, "magenta": 5, "cyan": 6, "white": 7,
    "bright_black": 8, "bright_red": 9, "bright_green": 10,
    "bright_yellow": 11, "bright_blue": 12, "bright_magenta": 13,
    "bright_cyan": 14, "bright_white": 15,
}

# ANSI modifier codes → escape sequence digit
ANSI_MODIFIERS = {
    "bold": "1", "dim": "2", "italic": "3", "underline": "4",
    "blink": "5", "reverse": "7", "strikethrough": "9",
}


@dataclass(slots=True)
class HighlightRule:
    """Single syntax highlighting rule — multi-group regex support."""

    name: str
    pattern: str
    colors: List[Optional[str]]  # color per capture group
    enabled: bool = True
    description: str = ""
    comment: str = ""
    action: str = "next"  # "next" | "stop" — continue or halt rule processing

    def __post_init__(self):
        """Default colors → ["white"]; normalize action."""
        if not self.colors:
            self.colors = ["white"]
        if self.action not in ("next", "stop"):
            self.action = "next"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize → dict for JSON."""
        result = {
            "name": self.name, "pattern": self.pattern,
            "colors": self.colors, "enabled": self.enabled,
        }
        if self.description:
            result["description"] = self.description
        if self.comment:
            result["comment"] = self.comment
        if self.action != "next":
            result["action"] = self.action
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HighlightRule":
        """Deserialize ← dict."""
        colors = data.get("colors", ["white"])
        if not colors:
            colors = ["white"]
        action = data.get("action", "next")
        if action not in ("next", "stop"):
            action = "next"
        return cls(
            name=data.get("name", ""), pattern=data.get("pattern", ""),
            colors=colors, enabled=data.get("enabled", True),
            description=data.get("description", ""),
            comment=data.get("comment", ""), action=action,
        )

    def is_valid(self) -> bool:
        """Regex compiles without error."""
        if not self.pattern:
            return False
        try:
            _re_engine.compile(self.pattern)
            return True
        except _re_engine.error:
            return False


@dataclass(slots=True)
class HighlightContext:
    """Command-specific highlighting — overrides global rules per command."""

    command_name: str
    triggers: List[str] = field(default_factory=list)
    rules: List[HighlightRule] = field(default_factory=list)
    enabled: bool = True
    description: str = ""
    use_global_rules: bool = False  # include global rules alongside context rules

    def to_dict(self) -> Dict[str, Any]:
        """Serialize → dict for JSON."""
        return {
            "name": self.command_name,
            "triggers": self.triggers,
            "rules": [r.to_dict() for r in self.rules],
            "enabled": self.enabled,
            "description": self.description,
            "use_global_rules": self.use_global_rules,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HighlightContext":
        """Deserialize ← dict."""
        rules = [HighlightRule.from_dict(r) for r in data.get("rules", [])]
        name = data.get("name") or data.get("command_name", "")
        triggers = data.get("triggers", [name] if name else [])
        return cls(
            command_name=name, triggers=triggers, rules=rules,
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
            use_global_rules=data.get("use_global_rules", False),
        )


@dataclass(slots=True)
class HighlightConfig:
    """Top-level highlight system configuration."""

    enabled_for_local: bool = False
    enabled_for_ssh: bool = False
    context_aware_enabled: bool = True
    global_rules: List[HighlightRule] = field(default_factory=list)
    contexts: Dict[str, HighlightContext] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize → dict for JSON."""
        return {
            "enabled_for_local": self.enabled_for_local,
            "enabled_for_ssh": self.enabled_for_ssh,
            "context_aware_enabled": self.context_aware_enabled,
            "global_rules": [r.to_dict() for r in self.global_rules],
            "contexts": {n: c.to_dict() for n, c in self.contexts.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HighlightConfig":
        """Deserialize ← dict."""
        rules_data = data.get("global_rules", data.get("rules", []))
        rules = [HighlightRule.from_dict(r) for r in rules_data]
        contexts = {
            n: HighlightContext.from_dict(c)
            for n, c in data.get("contexts", {}).items()
        }
        return cls(
            enabled_for_local=data.get("enabled_for_local", False),
            enabled_for_ssh=data.get("enabled_for_ssh", False),
            context_aware_enabled=data.get("context_aware_enabled", True),
            global_rules=rules, contexts=contexts,
        )
