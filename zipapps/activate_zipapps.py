import sys
import zipfile
from pathlib import Path


def activate(path=None):
    path = Path(path) if path else Path(__file__).parent
    path_str = path.absolute().as_posix()
    if zipfile.is_zipfile(path_str):
        try:
            from zipimport import zipimporter

            importer = zipimporter(path_str)
            try:
                spec = importer.find_spec("ensure_zipapps")
                if spec and spec.loader:
                    module = spec.loader.load_module("ensure_zipapps")
                else:
                    raise ImportError("Module not found")
            except AttributeError:
                module = importer.load_module("ensure_zipapps")
            del module
            sys.modules.pop("ensure_zipapps", None)
        except ImportError as err:
            sys.stderr.write(f"WARNING: activate failed for {err!r}\n")
            raise err
