# ashyterm/ui/dialogs/session_edit_validation.py
"""Validation and session data collection for SessionEditDialog.

Pure-logic helpers extracted from SessionEditDialog to enable unit testing.
Each function receives explicit parameters — no implicit self dependencies.
"""

import copy
from typing import Any, Dict, List, Optional

from ...sessions.models import SessionItem
from ...utils.exceptions import HostnameValidationError, SSHKeyError
from ...utils.security import validate_ssh_hostname, validate_ssh_key_file
from ...utils.platform import get_ssh_directory


# ── Validation ──────────────────────────────────────────────────────

def validate_basic_fields(name_text: str) -> tuple[bool, List[str]]:
    """Validate session name is non-empty.

    Returns (valid, errors).
    """
    errors: List[str] = []
    if not name_text.strip():
        errors.append("Session name is required.")
    return (len(errors) == 0, errors)


def validate_local_fields(
    working_dir: str,
) -> tuple[bool, List[str]]:
    """Validate local terminal working directory exists if provided."""
    errors: List[str] = []
    if working_dir.strip():
        from pathlib import Path
        p = Path(working_dir.strip())
        if not p.is_dir():
            errors.append("Working directory must exist and be a folder.")
    return (len(errors) == 0, errors)


def validate_hostname(hostname: str) -> tuple[bool, List[str]]:
    """Validate SSH hostname."""
    errors: List[str] = []
    if not hostname.strip():
        errors.append("Server Address is required.")
        return (False, errors)
    try:
        validate_ssh_hostname(hostname)
    except HostnameValidationError as e:
        errors.append(e.user_message)
    return (len(errors) == 0, errors)


def validate_ssh_key_file_path(key_path: str) -> tuple[bool, List[str]]:
    """Validate SSH key file if path provided."""
    errors: List[str] = []
    if not key_path.strip():
        return (True, [])  # Empty is OK (user may not have set one yet)
    try:
        validate_ssh_key_file(key_path)
    except SSHKeyError as e:
        errors.append(e.user_message)
    return (len(errors) == 0, errors)


def validate_post_login_command(enabled: bool, command: str) -> tuple[bool, List[str]]:
    """Post-login command must not be empty when enabled."""
    errors: List[str] = []
    if enabled and not command.strip():
        errors.append("Post-login command cannot be empty when enabled.")
    return (len(errors) == 0, errors)


def validate_sftp_directory(enabled: bool, local_dir: str) -> tuple[bool, List[str]]:
    """SFTP local directory must exist if provided."""
    errors: List[str] = []
    if not enabled:
        return (True, [])
    if local_dir.strip():
        from pathlib import Path
        p = Path(local_dir.strip())
        if not p.is_dir():
            errors.append("SFTP local directory must exist and be a directory.")
    return (len(errors) == 0, errors)


def validate_ssh_fields(
    hostname: str, key_path: str, auth_is_key: bool,
    post_login_enabled: bool, post_login_command: str,
    sftp_enabled: bool, sftp_local_dir: str,
) -> tuple[bool, List[str]]:
    """Run all SSH field validations. Returns (valid, combined_errors)."""
    all_errors: List[str] = []

    ok, errs = validate_hostname(hostname)
    if not ok:
        all_errors.extend(errs)

    if auth_is_key:
        ok, errs = validate_ssh_key_file_path(key_path)
        if not ok:
            all_errors.extend(errs)

    ok, errs = validate_post_login_command(post_login_enabled, post_login_command)
    if not ok:
        all_errors.extend(errs)

    ok, errs = validate_sftp_directory(sftp_enabled, sftp_local_dir)
    if not ok:
        all_errors.extend(errs)

    return (len(all_errors) == 0, all_errors)


def validate_port_forward(data: dict) -> List[str]:
    """Validate port forwarding data. Returns list of error messages."""
    errors: List[str] = []
    local_port = data.get("local_port", 0)
    remote_port = data.get("remote_port", 0)
    local_host = data.get("local_host", "")

    if not (1024 < local_port <= 65535):
        errors.append(
            "Local port must be between 1025 and 65535 "
            "(ports below 1024 require administrator privileges)."
        )
    if not (1 <= remote_port <= 65535):
        errors.append("Remote port must be between 1 and 65535.")
    if not local_host:
        errors.append("Local host cannot be empty.")

    return errors


# ── Session Data Collection ────────────────────────────────────────

def tri_state_to_selected(value: Optional[bool]) -> int:
    """Map tri-state (None/True/False) → ComboRow selection index."""
    if value is None:
        return 0
    return 1 if value else 2


def selected_to_tri_state(selected: int) -> Optional[bool]:
    """Map ComboRow selection index → tri-state (None/True/False)."""
    if selected == 0:
        return None
    if selected == 1:
        return True
    return False


def collect_highlighting_settings(
    customize_enabled: bool,
    output_selected: int,
    cmd_specific_selected: int,
    cat_selected: int,
    shell_input_selected: int,
) -> Dict[str, Any]:
    """Collect highlighting override values from UI state."""
    if not customize_enabled:
        return {
            "output_highlighting": None,
            "command_specific_highlighting": None,
            "cat_colorization": None,
            "shell_input_highlighting": None,
        }
    return {
        "output_highlighting": selected_to_tri_state(output_selected),
        "command_specific_highlighting": selected_to_tri_state(cmd_specific_selected),
        "cat_colorization": selected_to_tri_state(cat_selected),
        "shell_input_highlighting": selected_to_tri_state(shell_input_selected),
    }


def collect_session_data(
    editing_session: SessionItem,
    name: str,
    is_local: bool,
    tab_color: Optional[str],
    folder_path: str,
    highlighting: Dict[str, Any],
    # Local fields
    local_working_dir: str = "",
    local_startup_command: str = "",
    # SSH fields
    host: str = "",
    user: str = "",
    port: int = 22,
    auth_type: str = "",
    auth_value: str = "",
    # SSH options
    post_login_enabled: bool = False,
    post_login_command: str = "",
    x11_forwarding: bool = False,
    sftp_enabled: bool = False,
    sftp_local_dir: str = "",
    sftp_remote_dir: str = "",
    port_forwardings: Optional[List[dict]] = None,
) -> dict:
    """Collect all session data from form fields into a dict.

    Args are explicit — no implicit self dependency.
    """
    session_data = editing_session.to_dict()
    session_data.update({
        "name": name.strip(),
        "session_type": "local" if is_local else "ssh",
    })

    # Highlighting
    session_data.update(highlighting)

    # Tab color
    session_data["tab_color"] = tab_color or None

    # Folder
    session_data["folder_path"] = folder_path

    if is_local:
        session_data.update({
            "local_working_directory": local_working_dir.strip(),
            "local_startup_command": local_startup_command.strip(),
            # Clear SSH fields
            "host": "", "user": "", "auth_type": "", "auth_value": "",
            "sftp_session_enabled": False,
            "port_forwardings": [],
            "x11_forwarding": False,
        })
    else:
        session_data.update({
            "host": host.strip(),
            "user": user.strip(),
            "port": port,
            "auth_type": auth_type,
            "auth_value": auth_value if auth_type == "key" else "",
            "post_login_command_enabled": post_login_enabled,
            "post_login_command": post_login_command if post_login_enabled else "",
            "x11_forwarding": x11_forwarding,
            "sftp_session_enabled": sftp_enabled,
            "sftp_local_directory": sftp_local_dir.strip(),
            "sftp_remote_directory": sftp_remote_dir.strip(),
            "port_forwardings": copy.deepcopy(port_forwardings or []),
            # Clear local fields
            "local_working_directory": "",
            "local_startup_command": "",
        })

    return session_data


def build_session_from_data(
    session_data: dict, raw_password: str = "",
) -> Optional[SessionItem]:
    """Build SessionItem from collected data. Returns None on validation failure."""
    updated = SessionItem.from_dict(session_data)
    if updated.uses_password_auth() and raw_password:
        updated.auth_value = raw_password

    if not updated.validate():
        return None  # Caller should call updated.get_validation_errors()
    return updated


def get_default_ssh_key_dir() -> str:
    """Return default SSH key directory path."""
    return str(get_ssh_directory())
