# ashyterm/utils/accessibility.py
"""Accessibility helpers — GTK4 Accessible API wrappers.
Enable Orca / screen readers identify interactive widgets.
"""

from gi.repository import Gtk


def set_label(widget: Gtk.Widget, label: str) -> None:
    """Set accessible LABEL property on widget."""
    widget.update_property(
        [Gtk.AccessibleProperty.LABEL],
        [label],
    )


def set_description(widget: Gtk.Widget, description: str) -> None:
    """Set accessible DESCRIPTION property on widget."""
    widget.update_property(
        [Gtk.AccessibleProperty.DESCRIPTION],
        [description],
    )


def set_role_description(widget: Gtk.Widget, description: str) -> None:
    """Set accessible ROLE_DESCRIPTION property on widget."""
    widget.update_property(
        [Gtk.AccessibleProperty.ROLE_DESCRIPTION],
        [description],
    )


def set_labelled_by(widget: Gtk.Widget, label_widget: Gtk.Widget) -> None:
    """Set LABELLED_BY relation → widget ↔ label_widget."""
    widget.update_relation(
        [Gtk.AccessibleRelation.LABELLED_BY],
        [label_widget],
    )
