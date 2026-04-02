#!/usr/bin/env python3
"""
Ashy Terminal Memory Profiler

Run the app with memory tracking enabled.  Usage:

    python tools/memory_profiler.py [--interval SECONDS] [--top N]

Press Ctrl+C to get a snapshot summary and exit.
The profiler also logs periodic snapshots to ~/.config/ashyterm/memory_snapshots/

Tracked metrics:
  - RSS (Resident Set Size) via psutil
  - Top allocations via tracemalloc
  - GObject instance counts
  - Key data structure sizes from TerminalManager, SettingsManager, AIAssistant
"""

import argparse
import gc
import json
import os
import signal
import sys
import threading
import time
import tracemalloc
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def _get_rss_mb():
    """Get current RSS in MB via psutil."""
    import psutil
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def _get_tracemalloc_top(n=15):
    """Get top N memory allocations."""
    snapshot = tracemalloc.take_snapshot()
    # Filter out tracemalloc internals and this profiler
    snapshot = snapshot.filter_traces([
        tracemalloc.Filter(False, "<frozen *>"),
        tracemalloc.Filter(False, tracemalloc.__file__),
        tracemalloc.Filter(False, __file__),
    ])
    stats = snapshot.statistics("lineno")
    return stats[:n]


def _inspect_app_internals():
    """Inspect memory-relevant data structures if the app is running."""
    report = {}

    try:
        from ashyterm.settings.manager import SettingsManager
        # Find SettingsManager instances
        for obj in gc.get_objects():
            if isinstance(obj, SettingsManager):
                report["settings_manager"] = {
                    "change_listeners": len(obj._change_listeners),
                    "change_listeners_alive": sum(
                        1 for ref in obj._change_listeners if ref() is not None
                    ),
                }
                break
    except Exception:
        pass

    try:
        from ashyterm.terminal.ai_assistant import TerminalAiAssistant
        for obj in gc.get_objects():
            if isinstance(obj, TerminalAiAssistant):
                report["ai_assistant"] = {
                    "conversations": len(obj._conversations),
                    "total_messages": sum(
                        len(v) for v in obj._conversations.values()
                    ),
                    "inflight": sum(1 for v in obj._inflight.values() if v),
                    "terminal_refs": len(obj._terminal_refs),
                    "cancel_flags": len(obj._cancel_flags),
                }
                break
    except Exception:
        pass

    try:
        from ashyterm.terminal.registry import TerminalRegistry
        for obj in gc.get_objects():
            if isinstance(obj, TerminalRegistry):
                report["terminal_registry"] = {
                    "terminals": len(obj._terminals),
                    "terminal_refs": len(obj._terminal_refs),
                }
                break
    except Exception:
        pass

    try:
        from ashyterm.core.tasks import AsyncTaskManager
        mgr = AsyncTaskManager.get_instance()
        if mgr:
            report["task_manager"] = {
                "active_futures": len(mgr._active_futures),
                "is_shutdown": mgr._is_shutdown,
            }
    except Exception:
        pass

    try:
        from ashyterm.utils.logger import LoggerManager
        mgr = LoggerManager.get_instance()
        if mgr:
            report["logger_manager"] = {
                "loggers": len(mgr._loggers),
            }
    except Exception:
        pass

    return report


def _format_snapshot(top_stats, internals, rss_mb, elapsed):
    """Format a snapshot for display."""
    lines = [
        f"\n{'='*70}",
        f"  MEMORY SNAPSHOT  |  RSS: {rss_mb:.1f} MB  |  Elapsed: {elapsed:.0f}s",
        f"{'='*70}",
    ]

    if internals:
        lines.append("\n  App Data Structures:")
        for name, data in internals.items():
            lines.append(f"    {name}:")
            for k, v in data.items():
                lines.append(f"      {k}: {v}")

    lines.append(f"\n  Top {len(top_stats)} allocations by line:")
    for i, stat in enumerate(top_stats, 1):
        lines.append(f"    #{i:2d}  {stat.size / 1024:.1f} KiB  {stat}")

    lines.append(f"{'='*70}\n")
    return "\n".join(lines)


def _save_snapshot(snapshot_dir, top_stats, internals, rss_mb, elapsed):
    """Save snapshot to JSON file."""
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    filename = f"snapshot_{datetime.now().strftime('%H%M%S')}.json"
    data = {
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": elapsed,
        "rss_mb": rss_mb,
        "internals": internals,
        "top_allocations": [
            {"size_kb": s.size / 1024, "file": str(s), "count": s.count}
            for s in top_stats
        ],
    }
    filepath = snapshot_dir / filename
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    return filepath


class PeriodicProfiler:
    """Runs periodic memory snapshots in a background thread."""

    def __init__(self, interval=30, top_n=15, snapshot_dir=None):
        self.interval = interval
        self.top_n = top_n
        self.snapshot_dir = Path(snapshot_dir) if snapshot_dir else (
            Path.home() / ".config" / "ashyterm" / "memory_snapshots"
        )
        self._stop = threading.Event()
        self._thread = None
        self._start_time = time.monotonic()
        self._snapshots = []

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[Memory Profiler] Started. Interval: {self.interval}s. "
              f"Snapshots saved to: {self.snapshot_dir}")

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def take_snapshot(self, label="manual"):
        elapsed = time.monotonic() - self._start_time
        rss_mb = _get_rss_mb()
        top_stats = _get_tracemalloc_top(self.top_n)
        internals = _inspect_app_internals()

        snapshot_text = _format_snapshot(top_stats, internals, rss_mb, elapsed)
        print(snapshot_text)

        filepath = _save_snapshot(
            self.snapshot_dir, top_stats, internals, rss_mb, elapsed
        )
        self._snapshots.append({
            "label": label,
            "elapsed": elapsed,
            "rss_mb": rss_mb,
        })
        print(f"[Memory Profiler] Snapshot saved: {filepath}")
        return snapshot_text

    def _run(self):
        while not self._stop.wait(self.interval):
            try:
                self.take_snapshot(label="periodic")
            except Exception as e:
                print(f"[Memory Profiler] Error taking snapshot: {e}")

    def print_summary(self):
        if not self._snapshots:
            print("[Memory Profiler] No snapshots taken.")
            return

        print(f"\n{'='*50}")
        print("  MEMORY PROFILE SUMMARY")
        print(f"{'='*50}")
        for s in self._snapshots:
            print(f"  [{s['label']:>10}] {s['elapsed']:6.0f}s  RSS: {s['rss_mb']:.1f} MB")

        min_rss = min(s['rss_mb'] for s in self._snapshots)
        max_rss = max(s['rss_mb'] for s in self._snapshots)
        growth = max_rss - min_rss
        print(f"\n  Min RSS: {min_rss:.1f} MB | Max RSS: {max_rss:.1f} MB | Growth: {growth:.1f} MB")
        print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="Ashy Terminal Memory Profiler")
    parser.add_argument(
        "--interval", type=int, default=30,
        help="Seconds between periodic snapshots (default: 30)"
    )
    parser.add_argument(
        "--top", type=int, default=15,
        help="Number of top allocations to show (default: 15)"
    )
    parser.add_argument(
        "--frames", type=int, default=10,
        help="tracemalloc frame depth (default: 10)"
    )
    args = parser.parse_args()

    # Start tracemalloc before importing the app
    tracemalloc.start(args.frames)

    profiler = PeriodicProfiler(interval=args.interval, top_n=args.top)

    # Take initial snapshot before app starts
    rss_before = _get_rss_mb()
    print(f"[Memory Profiler] Initial RSS: {rss_before:.1f} MB")

    # Import and start the app
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    gi.require_version("Vte", "3.91")

    # Initialize translations before importing app (it uses _() at module level)
    from ashyterm.utils.translation_utils import _  # noqa: F401
    from ashyterm.app import CommTerminalApp

    app = CommTerminalApp()

    # Handle Ctrl+C: print summary and exit
    original_sigint = signal.getsignal(signal.SIGINT)

    def sigint_handler(signum, frame):
        print("\n[Memory Profiler] Interrupted — taking final snapshot...")
        profiler.take_snapshot(label="final")
        profiler.stop()
        profiler.print_summary()

        current_rss = _get_rss_mb()
        current_traced, peak_traced = tracemalloc.get_traced_memory()
        print(f"  Final RSS: {current_rss:.1f} MB")
        print(f"  Traced: current={current_traced/1024/1024:.1f} MB, "
              f"peak={peak_traced/1024/1024:.1f} MB")
        tracemalloc.stop()

        # Restore original handler and re-raise
        signal.signal(signal.SIGINT, original_sigint)
        os.kill(os.getpid(), signal.SIGINT)

    signal.signal(signal.SIGINT, sigint_handler)

    # Start periodic profiling
    profiler.start()

    # Take snapshot after app initialization (delayed)
    def _take_init_snapshot():
        from gi.repository import GLib
        GLib.timeout_add_seconds(5, lambda: profiler.take_snapshot("post-init") or False)

    from gi.repository import GLib
    GLib.idle_add(_take_init_snapshot)

    # Run the app
    exit_code = app.run(sys.argv[1:] if len(sys.argv) > 1 else [])

    # App exited normally
    profiler.take_snapshot(label="exit")
    profiler.stop()
    profiler.print_summary()
    tracemalloc.stop()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
