#!/usr/bin/env bash
# Run tests/freecad/test_*.py headlessly under AstoCAD's FreeCADCmd.
# pytest is not available inside AstoCAD's interpreter, so a small runner calls every
# module-level test_* function and reports failures through the exit code.
# Override the binary with FREECADCMD=/path/to/freecadcmd.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null && pwd)"
FREECADCMD="${FREECADCMD:-$HOME/Applications/AstoCAD.app/Contents/Resources/bin/freecadcmd}"

# FreeCADCmd swallows prints from a script file argument and treats a long multi-line "-c"
# argument as a file name, so the runner travels in an environment variable and "-c" execs it.
export CONSTRUCT_TEST_DIR="$REPO_ROOT/tests/freecad"
export CONSTRUCT_TEST_RUNNER="
import importlib.util, os, sys, traceback
from pathlib import Path
failed = 0
passed = 0
for path in sorted(Path(os.environ['CONSTRUCT_TEST_DIR']).glob('test_*.py')):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        failed += 1
        print(f'ERROR loading {path.name}', flush=True)
        traceback.print_exc()
        sys.stdout.flush()
        continue
    for name in sorted(n for n in vars(module) if n.startswith('test_')):
        try:
            getattr(module, name)()
        except Exception:
            failed += 1
            print(f'FAIL {path.name}::{name}', flush=True)
            traceback.print_exc()
            sys.stdout.flush()
        else:
            passed += 1
            print(f'PASS {path.name}::{name}', flush=True)
print(f'{passed} passed, {failed} failed', flush=True)
sys.exit(1 if failed or not passed else 0)
"
exec "$FREECADCMD" -c "import os; exec(os.environ['CONSTRUCT_TEST_RUNNER'])"
