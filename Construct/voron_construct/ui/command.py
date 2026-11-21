"""The Construct_Show command, its toolbar button and menu entry. Needs FreeCADGui."""

from __future__ import annotations

from pathlib import Path

COMMAND_NAME = "Construct_Show"
TOOLTIP = "Load the Construct / I Need CAD...Lots of CAD"
ICON_PATH = (
    Path(__file__).resolve().parents[2] / "Resources" / "icons" / "construct.svg"
)

_panel = None


def toggle_panel() -> None:
    """Create the dock panel on first use; afterwards show or hide it."""
    global _panel
    import FreeCADGui as Gui
    from PySide6 import QtCore

    if _panel is None:
        from .panel import create_panel

        main_window = Gui.getMainWindow()
        _panel = create_panel(main_window)
        main_window.addDockWidget(QtCore.Qt.RightDockWidgetArea, _panel)
        _panel.show()
    elif _panel.isVisible():
        _panel.hide()
    else:
        _panel.show()
        _panel.raise_()


class ShowConstructCommand:
    def GetResources(self) -> dict:
        return {"Pixmap": str(ICON_PATH), "MenuText": "Construct", "ToolTip": TOOLTIP}

    def IsActive(self) -> bool:
        return True

    def Activated(self) -> None:
        toggle_panel()


class _ConstructManipulator:
    """Add the command to every workbench.

    It goes in the Tools menu after the Addon Manager, and on the File toolbar.
    """

    def modifyMenuBar(self) -> list[dict]:
        return [{"insert": COMMAND_NAME, "menuItem": "Std_AddonMgr", "after": ""}]

    def modifyToolBars(self) -> list[dict]:
        return [{"append": COMMAND_NAME, "toolBar": "File"}]


_manipulator = _ConstructManipulator()


def register() -> None:
    import FreeCADGui as Gui

    Gui.addCommand(COMMAND_NAME, ShowConstructCommand())
    Gui.addWorkbenchManipulator(_manipulator)
