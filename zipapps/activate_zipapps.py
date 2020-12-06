import pathlib
import zipimport
from warnings import warn


def activate(path=None):
    path = path or pathlib.Path(__file__).parent.absolute()
    try:
        return zipimport.zipimporter(path).load_module("ensure_zipapps")
    except ImportError as err:
        warn(f'activate failed for {err!r}')
        raise err
