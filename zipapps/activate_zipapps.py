import importlib
import sys
import zipfile
from pathlib import Path


def activate(path=None):
    path = Path(path) if path else Path(__file__).parent
    path_str = path.absolute().as_posix()
    if zipfile.is_zipfile(path_str):
        try:
            ensure_zipapps = importlib.import_module("ensure_zipapps")
            del ensure_zipapps
            sys.modules.pop("ensure_zipapps", None)
        except ImportError as err:
            sys.stderr.write(f"WARNING: activate failed for {err!r}\n")
            raise err
