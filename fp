#!/bin/sh
# Run flatpack tools with FreeCAD's bundled Python (it has FreeCAD, shapely, numpy, scipy).
FREECAD_APP="${FREECAD_APP:-/Applications/FreeCAD.app}"
export FREECAD_APP
REPO="$(cd "$(dirname "$0")" && pwd)"
if [ "$1" = "test" ]; then
  exec "$FREECAD_APP/Contents/Resources/bin/python" "$REPO/tests/test_dsl.py"
fi
PYTHONPATH="$REPO:$FREECAD_APP/Contents/Resources/lib${PYTHONPATH:+:$PYTHONPATH}" \
  exec "$FREECAD_APP/Contents/Resources/bin/python" -m flatpack "$@"
