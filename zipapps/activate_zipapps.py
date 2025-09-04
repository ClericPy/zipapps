import zipimport
import sys
import zipfile
from pathlib import Path


def activate(path=None):
    path = Path(path) if path else Path(__file__).parent
    path_str = path.absolute().as_posix()
    if zipfile.is_zipfile(path_str):
        try:
            importer = zipimport.zipimporter(path_str)
            spec = importer.find_spec("ensure_zipapps")
            if spec and spec.loader is not None:
                ensure_zipapps = spec.loader.load_module("ensure_zipapps")
                del ensure_zipapps
                sys.modules.pop("ensure_zipapps", None)
            else:
                raise ImportError(f"Cannot find 'ensure_zipapps' in {path_str!r}")
        except ImportError as err:
            sys.stderr.write(f"WARNING: activate failed for {err!r}\n")
            raise err
