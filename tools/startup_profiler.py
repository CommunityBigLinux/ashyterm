#!/usr/bin/env python3
"""Startup profiler for Ashy Terminal - measures real startup time."""

import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

_T0 = time.perf_counter()

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk

_T_GI = time.perf_counter()

import ashyterm

_T_PKG = time.perf_counter()

from ashyterm.app import CommTerminalApp

_T_APP_IMPORT = time.perf_counter()


class ProfiledApp(CommTerminalApp):
    def _on_startup(self, app):
        t = time.perf_counter()
        super()._on_startup(app)
        self._startup_ms = (time.perf_counter() - t) * 1000

    def _process_and_execute_args(self, arguments):
        t0 = time.perf_counter()
        args = self._parse_command_line_args(arguments)
        t1 = time.perf_counter()

        assert self.settings_manager is not None
        behavior = self.settings_manager.get("new_instance_behavior", "new_tab")
        windows = self.get_windows()
        target_window = windows[0] if windows else None
        has_explicit_command = (
            args["ssh_target"] or args["execute_command"] or args["working_directory"]
        )

        if args["force_new_window"] or behavior == "new_window" or not target_window:
            t2 = time.perf_counter()
            window = self.create_new_window(
                initial_working_directory=args["working_directory"],
                initial_execute_command=args["execute_command"],
                close_after_execute=args["close_after_execute"],
                initial_ssh_target=args["ssh_target"],
            )
            t3 = time.perf_counter()
            self._present_window_and_request_focus(window)
            t4 = time.perf_counter()

            print(f"\n=== _process_and_execute_args ===")
            print(f"  parse_args:       {(t1-t0)*1000:7.1f} ms")
            print(f"  create_window:    {(t3-t2)*1000:7.1f} ms")
            print(f"  present_window:   {(t4-t3)*1000:7.1f} ms")
        else:
            super()._process_and_execute_args(arguments)

    def do_command_line(self, command_line):
        t = time.perf_counter()
        ret = super().do_command_line(command_line)
        cmd_ms = (time.perf_counter() - t) * 1000
        total_ms = (time.perf_counter() - _T0) * 1000

        print("\n=== Overall Startup Timings ===")
        print(f"  Python + gi imports:  {(_T_GI - _T0)*1000:7.1f} ms")
        print(f"  ashyterm package:     {(_T_PKG - _T_GI)*1000:7.1f} ms")
        print(f"  app import:           {(_T_APP_IMPORT - _T_PKG)*1000:7.1f} ms")
        print(f"  _on_startup:          {self._startup_ms:7.1f} ms")
        print(f"  do_command_line:      {cmd_ms:7.1f} ms")
        print(f"  ---")
        print(f"  TOTAL TO PRESENT:     {total_ms:7.1f} ms")

        GLib.timeout_add(200, self.quit)
        return ret


if __name__ == "__main__":
    app = ProfiledApp()
    app.run([])
