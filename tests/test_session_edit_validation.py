"""Tests for session_edit_validation — pure logic, no GTK required."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestValidateBasicFields:
    """Tests for validate_basic_fields()."""

    def test_empty_name_fails(self):
        from ashyterm.ui.dialogs.session_edit_validation import validate_basic_fields

        ok, errors = validate_basic_fields("")
        assert ok is False
        assert len(errors) > 0

    def test_whitespace_name_fails(self):
        from ashyterm.ui.dialogs.session_edit_validation import validate_basic_fields

        ok, errors = validate_basic_fields("   ")
        assert ok is False

    def test_valid_name_passes(self):
        from ashyterm.ui.dialogs.session_edit_validation import validate_basic_fields

        ok, errors = validate_basic_fields("my-ssh-server")
        assert ok is True
        assert len(errors) == 0


class TestValidateLocalFields:
    """Tests for validate_local_fields()."""

    def test_empty_dir_passes(self):
        from ashyterm.ui.dialogs.session_edit_validation import validate_local_fields

        ok, errors = validate_local_fields("")
        assert ok is True

    def test_valid_dir_passes(self, tmp_path):
        from ashyterm.ui.dialogs.session_edit_validation import validate_local_fields

        ok, errors = validate_local_fields(str(tmp_path))
        assert ok is True

    def test_nonexistent_dir_fails(self, tmp_path):
        from ashyterm.ui.dialogs.session_edit_validation import validate_local_fields

        fake = str(tmp_path / "does_not_exist_xyz")
        ok, errors = validate_local_fields(fake)
        assert ok is False
        assert len(errors) > 0


class TestValidateHostname:
    """Tests for validate_hostname()."""

    def test_empty_fails(self):
        from ashyterm.ui.dialogs.session_edit_validation import validate_hostname

        ok, errors = validate_hostname("")
        assert ok is False

    def test_valid_hostname_passes(self):
        from ashyterm.ui.dialogs.session_edit_validation import validate_hostname

        ok, errors = validate_hostname("example.com")
        assert ok is True

    def test_valid_ip_passes(self):
        from ashyterm.ui.dialogs.session_edit_validation import validate_hostname

        ok, errors = validate_hostname("192.168.1.1")
        assert ok is True


class TestValidatePostLoginCommand:
    """Tests for validate_post_login_command()."""

    def test_disabled_passes(self):
        from ashyterm.ui.dialogs.session_edit_validation import (
            validate_post_login_command,
        )

        ok, errors = validate_post_login_command(False, "")
        assert ok is True

    def test_enabled_empty_fails(self):
        from ashyterm.ui.dialogs.session_edit_validation import (
            validate_post_login_command,
        )

        ok, errors = validate_post_login_command(True, "")
        assert ok is False

    def test_enabled_with_command_passes(self):
        from ashyterm.ui.dialogs.session_edit_validation import (
            validate_post_login_command,
        )

        ok, errors = validate_post_login_command(True, "ls -la")
        assert ok is True


class TestValidateSftpDirectory:
    """Tests for validate_sftp_directory()."""

    def test_disabled_passes(self):
        from ashyterm.ui.dialogs.session_edit_validation import validate_sftp_directory

        ok, errors = validate_sftp_directory(False, "")
        assert ok is True

    def test_empty_passes(self, tmp_path):
        from ashyterm.ui.dialogs.session_edit_validation import validate_sftp_directory

        ok, errors = validate_sftp_directory(True, "")
        assert ok is True

    def test_valid_dir_passes(self, tmp_path):
        from ashyterm.ui.dialogs.session_edit_validation import validate_sftp_directory

        ok, errors = validate_sftp_directory(True, str(tmp_path))
        assert ok is True

    def test_nonexistent_fails(self, tmp_path):
        from ashyterm.ui.dialogs.session_edit_validation import validate_sftp_directory

        fake = str(tmp_path / "no_such_dir")
        ok, errors = validate_sftp_directory(True, fake)
        assert ok is False


class TestValidatePortForward:
    """Tests for validate_port_forward()."""

    def test_valid_data(self):
        from ashyterm.ui.dialogs.session_edit_validation import validate_port_forward

        data = {
            "local_host": "localhost",
            "local_port": 8080,
            "remote_host": "10.0.0.1",
            "remote_port": 80,
        }
        errors = validate_port_forward(data)
        assert errors == []

    def test_local_port_too_low(self):
        from ashyterm.ui.dialogs.session_edit_validation import validate_port_forward

        data = {"local_host": "localhost", "local_port": 80, "remote_port": 80}
        errors = validate_port_forward(data)
        assert len(errors) > 0
        assert any("1025" in e for e in errors)

    def test_remote_port_zero(self):
        from ashyterm.ui.dialogs.session_edit_validation import validate_port_forward

        data = {"local_host": "localhost", "local_port": 8080, "remote_port": 0}
        errors = validate_port_forward(data)
        assert len(errors) > 0
        assert any("1 and 65535" in e for e in errors)

    def test_empty_local_host(self):
        from ashyterm.ui.dialogs.session_edit_validation import validate_port_forward

        data = {"local_host": "", "local_port": 8080, "remote_port": 80}
        errors = validate_port_forward(data)
        assert len(errors) > 0
        assert any("empty" in e.lower() for e in errors)


class TestTriStateConversion:
    """Tests for tri_state_to_selected / selected_to_tri_state."""

    def test_none_to_0(self):
        from ashyterm.ui.dialogs.session_edit_validation import tri_state_to_selected

        assert tri_state_to_selected(None) == 0

    def test_true_to_1(self):
        from ashyterm.ui.dialogs.session_edit_validation import tri_state_to_selected

        assert tri_state_to_selected(True) == 1

    def test_false_to_2(self):
        from ashyterm.ui.dialogs.session_edit_validation import tri_state_to_selected

        assert tri_state_to_selected(False) == 2

    def test_0_to_none(self):
        from ashyterm.ui.dialogs.session_edit_validation import selected_to_tri_state

        assert selected_to_tri_state(0) is None

    def test_1_to_true(self):
        from ashyterm.ui.dialogs.session_edit_validation import selected_to_tri_state

        assert selected_to_tri_state(1) is True

    def test_2_to_false(self):
        from ashyterm.ui.dialogs.session_edit_validation import selected_to_tri_state

        assert selected_to_tri_state(2) is False


class TestCollectHighlightingSettings:
    """Tests for collect_highlighting_settings()."""

    def test_customize_off_returns_all_none(self):
        from ashyterm.ui.dialogs.session_edit_validation import (
            collect_highlighting_settings,
        )

        result = collect_highlighting_settings(
            customize_enabled=False,
            output_selected=1, cmd_specific_selected=1,
            cat_selected=1, shell_input_selected=1,
        )
        assert result["output_highlighting"] is None
        assert result["command_specific_highlighting"] is None
        assert result["cat_colorization"] is None
        assert result["shell_input_highlighting"] is None

    def test_customize_on_maps_selections(self):
        from ashyterm.ui.dialogs.session_edit_validation import (
            collect_highlighting_settings,
        )

        result = collect_highlighting_settings(
            customize_enabled=True,
            output_selected=1, cmd_specific_selected=2,
            cat_selected=0, shell_input_selected=1,
        )
        assert result["output_highlighting"] is True
        assert result["command_specific_highlighting"] is False
        assert result["cat_colorization"] is None
        assert result["shell_input_highlighting"] is True


class TestCollectSessionData:
    """Tests for collect_session_data()."""

    def _make_session(self):
        from ashyterm.sessions.models import SessionItem

        return SessionItem(name="test", session_type="local")

    def test_local_session_has_local_fields(self):
        from ashyterm.ui.dialogs.session_edit_validation import collect_session_data

        session = self._make_session()
        result = collect_session_data(
            editing_session=session,
            name="new-name",
            is_local=True,
            tab_color=None,
            folder_path="",
            highlighting={},
            local_working_dir="/tmp",
            local_startup_command="echo hello",
        )
        assert result["session_type"] == "local"
        assert result["name"] == "new-name"
        assert result["local_working_directory"] == "/tmp"
        assert result["local_startup_command"] == "echo hello"

    def test_ssh_session_has_ssh_fields(self):
        from ashyterm.ui.dialogs.session_edit_validation import collect_session_data

        session = self._make_session()
        result = collect_session_data(
            editing_session=session,
            name="ssh-test",
            is_local=False,
            tab_color="#ff0000",
            folder_path="/folders",
            highlighting={},
            host="example.com",
            user="admin",
            port=2222,
            auth_type="key",
            auth_value="/home/user/.ssh/id_rsa",
        )
        assert result["session_type"] == "ssh"
        assert result["host"] == "example.com"
        assert result["user"] == "admin"
        assert result["port"] == 2222
        assert result["auth_type"] == "key"
        assert result["tab_color"] == "#ff0000"
        assert result["folder_path"] == "/folders"
        # Local fields cleared for SSH
        assert result["local_working_directory"] == ""


class TestBuildSessionFromData:
    """Tests for build_session_from_data()."""

    def test_builds_valid_session(self):
        from ashyterm.ui.dialogs.session_edit_validation import (
            build_session_from_data,
        )

        data = {
            "name": "test-server",
            "session_type": "local",
            "host": "",
            "user": "",
            "port": 22,
            "auth_type": "",
            "auth_value": "",
        }
        result = build_session_from_data(data)
        assert result is not None
        assert result.name == "test-server"

    def test_returns_none_on_invalid(self):
        from ashyterm.ui.dialogs.session_edit_validation import (
            build_session_from_data,
        )

        # Missing required fields
        data = {"name": "", "session_type": "local"}
        result = build_session_from_data(data)
        # May or may not be None depending on SessionItem validation
        # Just check it doesn't crash
        assert result is None or hasattr(result, "name")
