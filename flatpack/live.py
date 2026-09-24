"""Live view inside the FreeCAD GUI: rebuilds the model every time a .py file is saved.

Start it with FlatpackLive.FCMacro (or `./fp live models/x.py`).
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

PKG_DIR = Path(__file__).resolve().parent
PARAMS = "User parameter:BaseApp/Preferences/Macros/Flatpack"
POLL_MS = 400
# When launched with FreeCAD (./fp live), wait this long before touching
# documents: FreeCAD's Start page finishes setting itself up on a timer after
# launch and segfaults if a document appears first.
STARTUP_DELAY_MS = 4000

PLY = (0.86, 0.71, 0.50)
CLASH = (1.0, 0.1, 0.1)
AXES = ((0.9, 0.1, 0.1), (0.1, 0.75, 0.1), (0.15, 0.3, 1.0))  # x y z
LABEL_FONT = 48
PUNCH = (0.35, 0.55, 0.85)
PUNCH_UNUSED = (0.9, 0.6, 0.1)


def _purge_modules(roots):
    """Forget modules loaded from our files so the next import sees fresh code."""
    roots = [str(r) + os.sep for r in roots]
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if name != __name__ and f and any(os.path.abspath(f).startswith(r) for r in roots):
            del sys.modules[name]


def _set_color(obj, rgb, line=False):
    vo = obj.ViewObject
    if vo is None:
        return
    if line:
        vo.LineColor = tuple(rgb)
        vo.PointColor = tuple(rgb)
        vo.LineWidth = 3
    else:
        vo.ShapeColor = tuple(rgb)


def _mark_color(obj, value):
    if not hasattr(obj, "FlatpackColor"):
        obj.addProperty("App::PropertyString", "FlatpackColor", "Flatpack")
        obj.setEditorMode("FlatpackColor", 2)
    obj.FlatpackColor = value


def _mark(obj, fid, source=""):
    for prop, value in (("FlatpackId", fid), ("FlatpackSource", source)):
        if not hasattr(obj, prop):
            obj.addProperty("App::PropertyString", prop, "Flatpack")
            obj.setEditorMode(prop, 1)
        setattr(obj, prop, value)


def _raise_view(doc):
    """Bring the model's 3D view in front of FreeCAD's Start page."""
    mdi = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
    if mdi is None:
        return
    for w in mdi.subWindowList():
        if w.windowTitle().startswith(doc.Label):
            mdi.setActiveSubWindow(w)
            return


class Panel(QtWidgets.QDockWidget):
    def __init__(self, session):
        super().__init__("Flatpack")
        self.setObjectName("FlatpackLive")
        self.session = session
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        self.file = QtWidgets.QLabel()
        self.file.setWordWrap(True)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        self.list = QtWidgets.QListWidget()
        self.list.setWordWrap(True)
        self.list.itemDoubleClicked.connect(self._select)
        row = QtWidgets.QHBoxLayout()
        for label, fn in (("Rebuild", session.rebuild), ("Open model…", session.choose),
                          ("Stop", session.stop)):
            b = QtWidgets.QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addWidget(self.file)
        lay.addWidget(self.status)
        lay.addWidget(self.list, 1)
        lay.addLayout(row)
        self.setWidget(w)

    def show_result(self, ok, headline, items):
        color = "#2a8a2a" if ok else "#c62828"
        self.status.setText(f"<b style='color:{color}'>{headline}</b>")
        self.list.clear()
        for text, names in items:
            it = QtWidgets.QListWidgetItem(text)
            it.setData(QtCore.Qt.UserRole, names)
            self.list.addItem(it)

    def _select(self, item):
        self.session.select(item.data(QtCore.Qt.UserRole) or [])


class Session:
    def __init__(self, model_path):
        self.model_path = Path(model_path).resolve()
        self.stamps = {}
        self.pending = False
        self.first = True
        self.doc_name = None
        self.panel = Panel(self)
        Gui.getMainWindow().addDockWidget(QtCore.Qt.RightDockWidgetArea, self.panel)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.poll)

    # -- lifecycle -------------------------------------------------------
    def start(self):
        self.panel.file.setText(f"Watching <code>{self.model_path}</code>")
        self.stamps = self._stamps()
        self.rebuild()
        self.timer.start(POLL_MS)

    def stop(self):
        self.timer.stop()
        self.panel.close()
        self.panel.deleteLater()
        if getattr(Gui, "_flatpack_live", None) is self:
            Gui._flatpack_live = None
        App.Console.PrintMessage("Flatpack live view stopped\n")

    def choose(self):
        path = ask_model(self.model_path)
        if path:
            self.model_path = Path(path).resolve()
            self.first = True
            self.start()

    # -- watching --------------------------------------------------------
    def _watched(self):
        files = set(PKG_DIR.glob("*.py"))
        for p in self.model_path.parent.rglob("*.py"):
            if not any(part.startswith(".") for part in p.parts):
                files.add(p)
        files.add(self.model_path)
        return files

    def _stamps(self):
        out = {}
        for f in self._watched():
            try:
                out[f] = f.stat().st_mtime_ns
            except OSError:
                pass
        return out

    def poll(self):
        now = self._stamps()
        if now != self.stamps:
            # Editors often save in several steps; wait for one quiet tick.
            self.stamps = now
            self.pending = True
        elif self.pending:
            self.pending = False
            self.rebuild()

    # -- building --------------------------------------------------------
    def rebuild(self):
        t0 = time.time()
        _purge_modules([PKG_DIR, self.model_path.parent])
        repo = str(PKG_DIR.parent)
        if repo not in sys.path:
            sys.path.insert(0, repo)
        try:
            from flatpack import loader, solid
            model = loader.load(self.model_path)
            solids = solid.build(model)
            clashes = solid.clashes(solids)
            axes = solid.marker_axes(model)
            labels = solid.marker_labels(model)
            rods = solid.punch_rods(model)
            self._sync(model, solids, clashes, axes, labels, rods)
        except Exception as e:
            self._show_error(e)
            return
        dt = time.time() - t0
        unused = [p for p in model.punches if not p.used]
        head = (f"✓ {len(model.chips)} chips, {len(model.punches)} punches, {len(model.markers)} part entries "
                f"({dt:.1f}s, {time.strftime('%H:%M:%S')})")
        items = [(f"⚠ punch {p.name} isn't used by any chip   {p.source}", [f"punch:{p.name}"])
                 for p in unused]
        for c in clashes:
            what = f"failed to check: {c.error}" if c.error else f"{c.volume:.0f} mm³"
            src = [model[n].source for n in (c.a, c.b)]
            items.append((f"✕ {c.a}  ×  {c.b}   {what}\n    {src[0]}, {src[1]}",
                          [f"chip:{c.a}", f"chip:{c.b}", f"clash:{c.a}|{c.b}"]))
        if clashes:
            head += f"<br>{len(clashes)} clash{'es' if len(clashes) != 1 else ''} (double-click to select)"
        self.panel.show_result(True, head, items)

    def _show_error(self, e):
        tb = traceback.extract_tb(e.__traceback__)
        ours = [f for f in tb if Path(f.filename).resolve().parent == self.model_path.parent]
        where = f"{Path(ours[-1].filename).name}:{ours[-1].lineno}" if ours else ""
        if isinstance(e, SyntaxError) and e.filename:
            where = f"{Path(e.filename).name}:{e.lineno}"
        App.Console.PrintError("Flatpack build failed:\n" + "".join(
            traceback.format_exception(type(e), e, e.__traceback__)))
        lines = [(f"{type(e).__name__}: {e}", [])]
        if ours:
            lines.append((f"at {where}:  {ours[-1].line}", []))
        lines.append(("(still showing the last good build; full traceback in Report view)", []))
        self.panel.show_result(False, f"✕ build failed {where}", lines)

    def _doc(self, model):
        name = "Flatpack_" + "".join(ch if ch.isalnum() else "_" for ch in model.name)
        if self.doc_name != name or name not in App.listDocuments():
            self.first = True
        self.doc_name = name
        doc = App.listDocuments().get(name)
        if doc is None:
            # temp: it's generated from the .py, so never offer to save it.
            doc = App.newDocument(name, temp=True)
        return doc

    def _sync(self, model, solids, clashes, axes, labels, rods):
        doc = self._doc(model)
        have = {o.FlatpackId: o for o in doc.Objects if hasattr(o, "FlatpackId")}
        keep = set()

        def group(path):
            parent = None
            for i in range(1, len(path) + 1):
                fid = "grp:" + "/".join(path[:i])
                g = have.get(fid)
                if g is None:
                    g = doc.addObject("App::DocumentObjectGroup", "Group")
                    g.Label = path[i - 1]
                    _mark(g, fid)
                    have[fid] = g
                if parent is not None and g not in parent.Group:
                    parent.addObject(g)
                keep.add(fid)
                parent = g
            return parent

        def put(fid, label, shape, rgb, source, path, line=False, transparency=None):
            obj = have.get(fid)
            if obj is None:
                obj = doc.addObject("Part::Feature", "Chip")
                have[fid] = obj
                if transparency is not None and obj.ViewObject is not None:
                    obj.ViewObject.Transparency = transparency
            obj.Label = label
            obj.Shape = shape
            _mark(obj, fid, source)
            # Only recolor when the model's color changes, so GUI tweaks survive reloads.
            if getattr(obj, "FlatpackColor", None) != repr(rgb):
                _set_color(obj, rgb, line)
                _mark_color(obj, repr(rgb))
            if path:
                g = group(path)
                if obj not in g.Group:
                    g.addObject(obj)
            keep.add(fid)

        for n, c in model.chips.items():
            put(f"chip:{n}", n, solids[n], c.rgb or PLY, c.source, n.split("/")[:-1])
        for i, shape in enumerate(axes):
            if shape is not None:
                put(f"mark:{'xyz'[i]}", f"turtle {'xyz'[i]}", shape, AXES[i], "",
                    ["Turtles"], line=True)
        for name, rod, used in rods:
            put(f"punch:{name}", name if used else f"{name} (unused)", rod,
                PUNCH if used else PUNCH_UNUSED, "", ["Punches"], transparency=60)
        for path, short, pos in labels:
            fid = f"label:{path}"
            obj = have.get(fid)
            if obj is None:
                obj = doc.addObject("App::Annotation", "Label")
                have[fid] = obj
            if obj.ViewObject is not None and obj.ViewObject.FontSize != LABEL_FONT:
                obj.ViewObject.FontSize = LABEL_FONT
            obj.Label = path
            obj.LabelText = [short]
            obj.Position = pos
            _mark(obj, fid)
            g = group(["Turtles"])
            if obj not in g.Group:
                g.addObject(obj)
            keep.add(fid)

        # Clash markers are rebuilt from scratch every time.
        for fid, obj in list(have.items()):
            if fid.startswith("clash:"):
                doc.removeObject(obj.Name)
                del have[fid]
        for c in clashes:
            if c.shape is not None:
                put(f"clash:{c.a}|{c.b}", f"{c.a} × {c.b}", c.shape, CLASH, "", ["Clashes"])
        for fid, obj in list(have.items()):
            if fid not in keep:
                try:
                    doc.removeObject(obj.Name)
                except Exception:
                    pass
        doc.recompute()
        gdoc = Gui.getDocument(doc.Name)
        try:
            gdoc.Modified = False
        except Exception:
            pass

        if self.first:
            self.first = False
            _raise_view(doc)
            view = gdoc.activeView()
            if view is not None:
                view.viewIsometric()
                view.fitAll()

    def select(self, fids):
        doc = App.listDocuments().get(self.doc_name)
        if doc is None:
            return
        Gui.Selection.clearSelection()
        for o in doc.Objects:
            if getattr(o, "FlatpackId", None) in fids:
                Gui.Selection.addSelection(doc.Name, o.Name)


def ask_model(start=None):
    params = App.ParamGet(PARAMS)
    start = str(start or params.GetString("LastModel", str(PKG_DIR.parent / "models")))
    path, _ = QtWidgets.QFileDialog.getOpenFileName(
        Gui.getMainWindow(), "Flatpack model", start, "Python (*.py)")
    if path:
        params.SetString("LastModel", path)
    return path


def main(model_path=None):
    old = getattr(Gui, "_flatpack_live", None)
    if old is not None:
        old.stop()
    at_launch = model_path is None and "FLATPACK_MODEL" in os.environ
    model_path = model_path or os.environ.pop("FLATPACK_MODEL", None) or ask_model()
    if not model_path:
        return None
    App.ParamGet(PARAMS).SetString("LastModel", str(model_path))
    session = Session(model_path)
    Gui._flatpack_live = session
    if at_launch:
        session.panel.file.setText("Waiting for FreeCAD to finish starting…")
        QtCore.QTimer.singleShot(STARTUP_DELAY_MS, session.start)
    else:
        session.start()
    return session
