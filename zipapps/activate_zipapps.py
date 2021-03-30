import zipimport
from pathlib import Path
from sys import stderr


def activate(path=None):
    path = Path(path).absolute() if path else Path(__file__).parent.absolute()
    try:
        return zipimport.zipimporter(path).load_module("ensure_zipapps")
    except ImportError as err:
        stderr.write(f'WARNING: activate failed for {err!r}\n')
        raise err
