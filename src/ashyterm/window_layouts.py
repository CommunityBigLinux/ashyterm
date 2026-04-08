"""Window layout save/restore mixin — layouts and session state."""


class WindowLayoutsMixin:
    """Mixin: layout management — move layouts, delegate to state_manager."""

    def move_layout(self, layout_name: str, old_folder: str, new_folder: str) -> None:
        """Delegate layout move operation to state manager.

        Args:
            layout_name: Name of the layout to move.
            old_folder: Current folder path of the layout.
            new_folder: Target folder path for the layout.
        """
        self.state_manager.move_layout(layout_name, old_folder, new_folder)
