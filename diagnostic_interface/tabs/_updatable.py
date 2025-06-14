from typing import runtime_checkable, Protocol


@runtime_checkable
class UpdatableTab(Protocol):
    def set_tab_active(self, active: bool) -> None:
        """
        Set whether this tab is currently active
        :param active: Whether this tab is currently active
        """
        ...
