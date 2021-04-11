import os
import sys
from pathlib import Path
from shutil import rmtree
from tempfile import gettempdir
from zipfile import ZipFile


def ensure_path(path):
    if path.startswith('HOME'):
        _cache_folder_path = Path.home() / (path[4:].lstrip('/\\'))
    elif path.startswith('SELF'):
        _cache_folder_path = Path(__file__).parent.parent / (
            path[4:].lstrip('/\\'))
    elif path.startswith('TEMP'):
        _cache_folder_path = Path(gettempdir()) / (path[4:].lstrip('/\\'))
    else:
        _cache_folder_path = Path(path)
    return _cache_folder_path


def rm_dir(dir_path: Path):
    for _ in range(3):
        try:
            if not dir_path.is_dir():
                break
            # remove the exist folder
            rmtree(dir_path)
        except FileNotFoundError:
            break


def prepare_path():
    """Template code for zipapps entry point. Run with current PYTHONPATH"""
    # PYTHONPATH=./app.pyz
    zip_file_path = Path(__file__).parent.absolute()
    _zipapps_python_path_list = [str(zip_file_path)]
    unzip = os.environ.get('ZIPAPPS_UNZIP') or r'''{unzip}'''
    if unzip:
        _cache_folder = os.environ.get('ZIPAPPS_CACHE') or os.environ.get(
            'UNZIP_PATH') or r'''{unzip_path}'''

        _cache_folder_path = ensure_path(_cache_folder)
        _cache_folder_path = _cache_folder_path / zip_file_path.stem
        _cache_folder_path_str = str(_cache_folder_path.absolute())
        _zipapps_python_path_list.insert(0, _cache_folder_path_str)
        ts_file_name = '_zip_time_{ts}'
        if not (_cache_folder_path / ts_file_name).is_file():
            # check timestamp difference by file name, need to refresh _cache_folder
            # rm the folder
            rm_dir(_cache_folder_path)
            _cache_folder_path.mkdir(parents=True)
            _need_unzip_names = unzip.split(',')
            _need_unzip_names.append(ts_file_name)
            with ZipFile(zip_file_path, "r") as zf:
                for member in zf.infolist():
                    file_dir_name = os.path.splitext(
                        member.filename.split('/')[0])[0]
                    if unzip == '*' or member.filename in _need_unzip_names or file_dir_name in _need_unzip_names:
                        zf.extract(member, path=_cache_folder_path_str)
            # lazy pip install
            lazy_pip_dir = _cache_folder_path / r'''{LAZY_PIP_DIR_NAME}'''
            if lazy_pip_dir.is_dir():
                try:
                    import pip
                except ImportError:
                    import ensurepip
                    ensurepip.bootstrap()
                import subprocess
                shell_args = [
                    sys.executable, '-m', 'pip', 'install', '--target',
                    _cache_folder_path_str
                ] + {pip_args_repr}
                with subprocess.Popen(shell_args,
                                      cwd=_cache_folder_path_str) as proc:
                    proc.wait()
    sep = ';' if sys.platform == 'win32' else ':'
    ignore_system_python_path = {ignore_system_python_path}
    _new_sys_paths = r'''{sys_paths}'''.strip()
    if _new_sys_paths:
        new_sys_paths = [str(ensure_path(p)) for p in _new_sys_paths.split(',')]
    else:
        new_sys_paths = []
    if ignore_system_python_path:
        sys.path.clear()
        # env of Popen is not valid for win32 platform, use os.environ instead.
        _new_paths = _zipapps_python_path_list + new_sys_paths
    else:
        _old_path = os.environ.get('PYTHONPATH') or ''
        _new_paths = _zipapps_python_path_list + [_old_path] + new_sys_paths
    os.environ['PYTHONPATH'] = sep.join(_new_paths)
    # let the dir path first
    zipapps_paths = [
        path for path in _zipapps_python_path_list if path not in sys.path
    ]
    sys.path = zipapps_paths + sys.path + new_sys_paths


prepare_path()
