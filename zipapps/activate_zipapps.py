import zipfile
import zipimport
from pathlib import Path
from sys import modules, stderr


def activate(path=None):
    path = Path(path) if path else Path(__file__).parent
    path_str = path.absolute().as_posix()
    if zipfile.is_zipfile(path_str):
        try:
            spec = zipimport.zipimporter(path_str).find_spec("ensure_zipapps")
            if spec and spec.loader:
                _tmp = spec.loader.load_module("ensure_zipapps")
                modules.pop(_tmp.__name__, None)
                del _tmp
                return True
            else:
                raise ImportError(path_str)
        except ImportError as err:
            stderr.write(f"WARNING: activate failed for {err!r}\n")
            raise err
