import zipimport
from pathlib import Path
from sys import modules, stderr


def activate(path=None):
    path = Path(path).absolute() if path else Path(__file__).parent.absolute()
    try:
        _tmp = zipimport.zipimporter(path).load_module("ensure_zipapps")
        modules.pop(_tmp.__name__, None)
        del _tmp
        return True
    except ImportError as err:
        stderr.write(f'WARNING: activate failed for {err!r}\n')
        raise err
