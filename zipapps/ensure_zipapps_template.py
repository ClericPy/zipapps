# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path
from shutil import rmtree
from tempfile import gettempdir
from zipfile import ZipFile

# const
ignore_system_python_path = {ignore_system_python_path}
unzip = os.environ.get('ZIPAPPS_UNZIP') or r'''{unzip}'''
unzip_exclude = os.environ.get(
    'ZIPAPPS_UNZIP_EXCLUDE') or r'''{unzip_exclude}'''
_cache_folder = os.environ.get('ZIPAPPS_CACHE') or os.environ.get(
    'UNZIP_PATH') or r'''{unzip_path}'''
ts_file_name = '_zip_time_{ts}'
LAZY_PIP_DIR_NAME = r'''{LAZY_PIP_DIR_NAME}'''
pip_args = {pip_args_repr}
pip_args_md5 = '{pip_args_md5}'
py_version = '.'.join(map(str, sys.version_info[:{python_version_slice}]))
_new_sys_paths = r'''{sys_paths}'''.strip()
clear_zipapps_cache = os.environ.get('CLEAR_ZIPAPPS_CACHE') or {clear_zipapps_cache}


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


def rm_dir_or_file(path: Path):
    for _ in range(3):
        try:
            if path.is_dir():
                rmtree(str(path.absolute()), ignore_errors=True)
            elif path.is_file():
                path.unlink()
            else:
                break
        except FileNotFoundError:
            break
        except PermissionError:
            break
    else:
        return False
    return True


def clear_old_cache(_cache_folder_path: Path, LAZY_PIP_DIR_NAME=''):
    for path in _cache_folder_path.glob('*'):
        if path.name == LAZY_PIP_DIR_NAME:
            continue
        rm_dir_or_file(path)


def get_pip_main(ensurepip_root=None):
    try:
        import pip
    except ImportError:
        import ensurepip
        assert ensurepip._bootstrap(root=ensurepip_root) == 0
        if ensurepip_root:
            for _path in Path(ensurepip_root).glob('**/pip/'):
                if _path.is_dir():
                    sys.path.append(str(_path.parent.absolute()))
                    break
        import pip
    pip_main = getattr(pip, 'main', None)
    if pip_main:
        return pip_main
    from pip._internal import main as pip_main
    return pip_main


def prepare_path():
    """Template code for zipapps entry point. Run with current PYTHONPATH"""
    # PYTHONPATH=./app.pyz
    zip_file_path = Path(__file__).parent.absolute()
    _zipapps_python_path_list = [str(zip_file_path)]
    if unzip:
        _cache_folder_path_parent = ensure_path(_cache_folder)
        _cache_folder_path = _cache_folder_path_parent / zip_file_path.stem
        if clear_zipapps_cache:
            import atexit

            def _remove_cache_folder():
                rm_dir_or_file(_cache_folder_path)
                if not any(_cache_folder_path_parent.iterdir()):
                    rm_dir_or_file(_cache_folder_path_parent)

            atexit.register(_remove_cache_folder)

        _cache_folder_path.mkdir(parents=True, exist_ok=True)
        _cache_folder_path_str = str(_cache_folder_path.absolute())
        _zipapps_python_path_list.insert(0, _cache_folder_path_str)
        if not (_cache_folder_path / ts_file_name).is_file():
            # check timestamp difference by file name, need to refresh _cache_folder
            # rm the folder
            clear_old_cache(_cache_folder_path, LAZY_PIP_DIR_NAME)
            _need_unzip_names = unzip.split(',')
            if unzip_exclude:
                _exclude_unzip_names = set(unzip_exclude.split(','))
            else:
                _exclude_unzip_names = set()
            _need_unzip_names.append(ts_file_name)
            with ZipFile(zip_file_path, "r") as zf:
                for member in zf.infolist():
                    file_dir_name = os.path.splitext(
                        member.filename.split('/')[0])[0]
                    allow_unzip = unzip == '*' or member.filename in _need_unzip_names or file_dir_name in _need_unzip_names
                    exclude_unzip = member.filename in _exclude_unzip_names or file_dir_name in _exclude_unzip_names
                    if allow_unzip and not exclude_unzip:
                        zf.extract(member, path=_cache_folder_path_str)
        if LAZY_PIP_DIR_NAME:
            import platform

            lazy_pip_dir = _cache_folder_path / LAZY_PIP_DIR_NAME
            if lazy_pip_dir.is_dir():
                # pip target isolation with by python version and platform
                platform_name = (platform.system() or '-')
                target_name = '%s_%s' % (py_version, platform_name)
                _pip_target = lazy_pip_dir / target_name
                _pip_target.mkdir(parents=True, exist_ok=True)
                lazy_pip_dir_str = str(_pip_target.absolute())
                _zipapps_python_path_list.insert(0, lazy_pip_dir_str)
                _need_reinstall = not (_pip_target / pip_args_md5).is_file(
                ) or '-U' in pip_args or '--upgrade' in pip_args
                if _need_reinstall:
                    # rm old requirements
                    rm_dir_or_file(_pip_target)
                    _pip_target.mkdir(parents=True, exist_ok=True)
                    _pip_args = ['install', '-t', lazy_pip_dir_str] + pip_args
                    cwd = os.getcwd()
                    os.chdir(_cache_folder_path_str)
                    try:
                        pip_main = get_pip_main(ensurepip_root=lazy_pip_dir_str)
                        pip_main(_pip_args)
                    finally:
                        os.chdir(cwd)
                    # avoid duplicated installation
                    (_pip_target / pip_args_md5).touch()
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
    os.environ['PYTHONPATH'] = os.pathsep.join(_new_paths)
    # let the dir path first
    zipapps_paths = [
        path for path in _zipapps_python_path_list if path not in sys.path
    ]
    sys.path = zipapps_paths + sys.path + new_sys_paths


prepare_path()
