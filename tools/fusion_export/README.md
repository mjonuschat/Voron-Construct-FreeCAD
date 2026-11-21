# Fusion STEP export script

Exports a `.step` next to every `.f3d`/`.f3z` in a Construct checkout that has no
`.step`/`.stp` of the same name.

## Install
Copy the `FusionStepExport` folder into Fusion's Scripts folder:

- macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/`
- Windows: `%appdata%\Autodesk\Autodesk Fusion 360\API\Scripts`

## Run
In Fusion open Utilities > Add-Ins > Scripts and Add-Ins (Shift+S), pick
`FusionStepExport` under My Scripts (or the Add-Ins tab) and press Run. Choose the
checkout folder. A summary box shows exported/failed counts; details go to
`step_export.log` in the checkout root.

## What it does and does not do
- Imports each file into a new document, exports the root component to STEP, closes
  without saving. Files are written as `.partial.step` and renamed on success, so
  an interrupted run can simply be repeated.
- One failing file is logged and the run continues.
- Parametric generators export as a single fixed size (whatever the file contains).
- `.f3z` files may fail to import this way; they are logged as failed for manual handling.
- The script is unverified against a live Fusion; it was written from the API docs.

## Committing results
Later, add the generated `.step` files to a fork of the Construct repo and open a pull
request from there. This project takes no GitHub actions itself.
