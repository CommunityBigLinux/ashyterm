"""Tests for osc7_tracker — OSC7 terminal tracking logic."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestOSC7TerminalTrackerInit:
    """Tests for OSC7TerminalTracker initialization."""

    def test_init_defaults(self):
        from ashyterm.utils.osc7_tracker import OSC7TerminalTracker

        tracker = OSC7TerminalTracker()
        assert tracker.parser is not None
        assert tracker.on_directory_changed is None

    def test_init_with_settings_manager(self):
        from ashyterm.utils.osc7_tracker import OSC7TerminalTracker

        mock_settings = {"osc7_enabled": True}
        tracker = OSC7TerminalTracker(settings_manager=mock_settings)
        assert tracker.settings_manager == mock_settings


class TestGetOSC7Tracker:
    """Tests for global tracker singleton."""

    def test_returns_singleton(self):
        from ashyterm.utils.osc7_tracker import (
            get_osc7_tracker,
        )

        t1 = get_osc7_tracker()
        t2 = get_osc7_tracker()
        assert t1 is t2

    def test_returns_tracker_instance(self):
        from ashyterm.utils.osc7_tracker import (
            OSC7TerminalTracker,
            get_osc7_tracker,
        )

        result = get_osc7_tracker()
        assert isinstance(result, OSC7TerminalTracker)


class TestOSC7ParserIntegration:
    """Tests for OSC7Parser within tracker context."""

    def test_parse_valid_file_uri(self):
        from ashyterm.utils.osc7 import parse_directory_uri

        uri = "file://localhost/home/user/projects"
        result = parse_directory_uri(uri)
        assert result is not None
        assert result.path == "/home/user/projects"
        assert result.hostname == "localhost"

    def test_parse_uri_with_spaces_in_path(self):
        from ashyterm.utils.osc7 import parse_directory_uri

        uri = "file://localhost/home/user/my%20projects"
        result = parse_directory_uri(uri)
        assert result is not None
        assert result.path == "/home/user/my projects"

    def test_parse_empty_uri(self):
        from ashyterm.utils.osc7 import parse_directory_uri

        assert parse_directory_uri("") is None

    def test_parse_non_file_uri(self):
        from ashyterm.utils.osc7 import parse_directory_uri

        assert parse_directory_uri("http://example.com") is None

    def test_parse_uri_with_port(self):
        from ashyterm.utils.osc7 import parse_directory_uri

        uri = "file://localhost:8080/home/user"
        result = parse_directory_uri(uri)
        assert result is not None
        assert result.path == "/home/user"

    def test_display_path_root(self):
        from ashyterm.utils.osc7 import OSC7Parser

        parser = OSC7Parser()
        display = parser._create_display_path("/var/log/syslog")
        assert display == "/var/log/syslog"


class TestOSC7Info:
    """Tests for OSC7Info data structure."""

    def test_osc7_info_fields(self):
        from ashyterm.utils.osc7 import OSC7Info

        info = OSC7Info(hostname="myhost", path="/home/user", display_path="~")
        assert info.hostname == "myhost"
        assert info.path == "/home/user"
        assert info.display_path == "~"

    def test_osc7_info_immutability(self):
        """OSC7Info is a NamedTuple — fields are read-only."""
        from ashyterm.utils.osc7 import OSC7Info

        info = OSC7Info(hostname="h", path="/p", display_path="~")
        with pytest.raises(AttributeError):
            info.hostname = "new"  # type: ignore[misc]


class TestTrackerThreadSafety:
    """Tests for thread safety constructs in tracker."""

    def test_has_lock(self):
        from ashyterm.utils.osc7_tracker import OSC7TerminalTracker

        tracker = OSC7TerminalTracker()
        assert hasattr(tracker, "_lock")

    def test_global_lock_exists(self):
        from ashyterm.utils.osc7_tracker import _tracker_lock

        assert _tracker_lock is not None
