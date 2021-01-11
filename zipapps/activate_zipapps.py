import zipimport
from pathlib import Path
from warnings import warn


def activate(path=None):
    path = Path(path).absolute() if path else Path(__file__).parent.absolute()
    try:
        return zipimport.zipimporter(path).load_module("ensure_zipapps")
    except ImportError as err:
        warn(f'activate failed for {err!r}')
        raise err
