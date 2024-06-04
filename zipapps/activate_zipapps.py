import zipfile
import zipimport
from pathlib import Path
from sys import modules, stderr


def activate(path=None):
    path = Path(path) if path else Path(__file__).parent
    path_str = path.absolute().as_posix()
    if zipfile.is_zipfile(path_str):
        try:
            _tmp = zipimport.zipimporter(path_str).load_module("ensure_zipapps")
            modules.pop(_tmp.__name__, None)
            del _tmp
            return True
        except ImportError as err:
            stderr.write(f"WARNING: activate failed for {err!r}\n")
            raise err
