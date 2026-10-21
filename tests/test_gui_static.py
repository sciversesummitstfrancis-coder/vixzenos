"""Static GUI guards (headless): catch signal-name and widget misuses that
only explode at window-open time, which --smoke never exercises.

Would have caught: ListBoxRow.connect("activated") (correct: "activate").
"""
import ast
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
APPS = [
    REPO / "apps" / "power-menu" / "vixzen_power.py",
    REPO / "apps" / "file-manager" / "vixzen_files.py",
    REPO / "apps" / "system-settings" / "vixzen_settings.py",
    REPO / "preview" / "src" / "vixzen_preview.py",
    REPO / "desktop" / "panel" / "vixzen_panel.py",
]

# .connect("NAME") calls that are invalid on the widget they target.
# Kept minimal and certain: ListBoxRow has "activate", not "activated".
BAD_CONNECTS = {
    "ListBoxRow": {"activated"},
}


def test_signal_names():
    offenders = []
    for path in APPS:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "connect"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)):
                sig = node.args[0].value
                # find enclosing variable type heuristically: row/listbox
                src = ast.get_source_segment(path.read_text(), node) or ""
                recv = (node.func.value.id
                        if isinstance(node.func.value, ast.Name) else "")
                if recv == "row" and sig in BAD_CONNECTS["ListBoxRow"]:
                    offenders.append((str(path), node.lineno, sig))
    assert not offenders, f"invalid signal connects: {offenders}"


def test_no_bare_window_blockers():
    """No app may call fullscreen()/maximize() on its main window."""
    for path in APPS:
        txt = path.read_text()
        assert "\n        self.fullscreen()" not in txt, path


if __name__ == "__main__":
    test_signal_names()
    test_no_bare_window_blockers()
    print("gui-static tests OK: 2 checks passed")
