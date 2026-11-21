"""Fusion script: export a STEP next to every .f3d/.f3z that lacks one."""

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import adsk.core
import adsk.fusion
import plan


def export_one(app, source: Path) -> None:
    """Import source, export its root component to STEP, always close the document."""
    target = plan.step_target(source)
    temp = target.with_name(target.stem + ".partial.step")
    doc = None
    try:
        options = app.importManager.createFusionArchiveImportOptions(str(source))
        doc = app.importManager.importToNewDocument(options)
        design = adsk.fusion.Design.cast(
            doc.products.itemByProductType("DesignProductType")
        )
        if design is None:
            raise RuntimeError("document has no design")
        export_mgr = design.exportManager
        step_options = export_mgr.createSTEPExportOptions(
            str(temp), design.rootComponent
        )
        if not export_mgr.execute(step_options):
            raise RuntimeError("STEP export returned failure")
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()
        if doc is not None:
            doc.close(False)


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        dialog = ui.createFolderDialog()
        dialog.title = "Select the Construct checkout folder"
        if dialog.showDialog() != adsk.core.DialogResults.DialogOK:
            return
        root = Path(dialog.folder)
        todo = plan.find_missing(root)
        exported = 0
        failed = 0
        log_path = root / "step_export.log"
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"--- {datetime.now().isoformat()} ({len(todo)} files)\n")
            for source in todo:
                try:
                    export_one(app, source)
                    exported += 1
                    log.write(f"OK   {source}\n")
                except Exception as exc:  # one failing file must not stop the run
                    failed += 1
                    log.write(f"FAIL {source}: {exc}\n")
                log.flush()
        ui.messageBox(f"Exported: {exported}\nFailed: {failed}\nLog: {log_path}")
    except Exception:  # show any failure in a message box
        if ui:
            ui.messageBox(traceback.format_exc())
