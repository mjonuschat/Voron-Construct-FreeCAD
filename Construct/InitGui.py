# FreeCAD execs this file inside a function, so keep the logic in an importable module.
from voron_construct.ui import command as _construct_command

_construct_command.register()
