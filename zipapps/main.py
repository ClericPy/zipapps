# -*- coding: utf-8 -*-

import compileall
import re
import shutil
import subprocess
import sys
import tempfile
import time
import typing
import zipapp
from glob import glob
from hashlib import md5
from pathlib import Path
from pkgutil import get_data
from zipfile import ZipFile


class Config:
    """
    Default args
    """
    DEFAULT_OUTPUT_PATH = 'app.pyz'
    DEFAULT_UNZIP_CACHE_PATH = 'zipapps_cache'
    AUTO_FIX_UNZIP_KEYS = {'AUTO_UNZIP', 'AUTO'}
    COMPILE_KWARGS: typing.Dict[str, typing.Any] = {}
    HANDLE_OTHER_ENVS_FLAG = '--zipapps'
    LAZY_PIP_DIR_NAME = '_zipapps_lazy_pip'


def _log(text):
    sys.stderr.write(f'{text}\n')


def refresh_dir(path):
    """clean up files in dir path"""
    if path.is_dir():
        # clean up dir
        shutil.rmtree(path)
    path.mkdir()


def prepare_includes(includes, cache_path):
    if not includes:
        return
    for _include_path in re.split(r'[,\s]+', includes):
        include_path = Path(_include_path)
        if include_path.is_dir():
            shutil.copytree(include_path, cache_path / include_path.name)
        elif include_path.is_file():
            shutil.copyfile(include_path, cache_path / include_path.name)
        else:
            raise RuntimeError('%s is not exist' % include_path.absolute())


def prepare_entry(
    cache_path: Path,
    shell=False,
    main='',
    unzip='',
    unzip_path='',
    output_path: Path = None,
    ignore_system_python_path=False,
    main_shell=False,
    ts='None',
    env_paths: str = '',
    pip_args: list = None,
    sys_paths: str = '',
    python_version_slice: int = 2,
    pip_args_md5: str = '',
):
    unzip_names = set(unzip.split(',')) if unzip else set()
    warning_names: typing.Dict[str, dict] = {}
    for path in cache_path.iterdir():
        _name_not_included = path.name not in unzip_names
        if path.is_dir():
            pyd_counts = len(list(path.glob('**/*.pyd')))
            so_counts = len(list(path.glob('**/*.so')))
            if (pyd_counts or so_counts) and _name_not_included:
                # warn which libs need to be unzipped
                if pyd_counts:
                    warning_names.setdefault(path.name, {})['.pyd'] = pyd_counts
                if so_counts:
                    warning_names.setdefault(path.name, {})['.so'] = so_counts
        elif path.is_file() and path.suffix in ('.pyd', '.so'):
            if _name_not_included and path.stem not in unzip_names:
                warning_names.setdefault(path.name, {})[path.suffix] = 1
    # remove the special keys from unzip_names
    auto_unzip_keys = Config.AUTO_FIX_UNZIP_KEYS & unzip_names
    unzip_names -= auto_unzip_keys
    if warning_names:
        if auto_unzip_keys:
            unzip_names |= warning_names.keys()
        else:
            _fix_unzip_names = ",".join(warning_names.keys())
            msg = f'WARNING: .pyd/.so files may not be imported correctly, set `--unzip={_fix_unzip_names}` to avoid it. {warning_names}'
            _log(msg)
    new_unzip = ','.join(unzip_names)
    unzip = new_unzip
    output_path = output_path or Path(Config.DEFAULT_OUTPUT_PATH)
    output_name = Path(output_path).stem
    if not re.match(r'^[0-9a-zA-Z_]+$', output_name):
        raise ValueError('output_name should match regex: [0-9a-zA-Z_]+')
    module, _, function = main.partition(':')
    if module:
        module_path = cache_path / module
        if module_path.is_file():
            module = module_path.stem
    kwargs = {
        'ts': ts,
        'shell': shell,
        'main_shell': main_shell,
        'unzip': unzip,
        'output_name': output_name,
        'unzip_path': unzip_path or Config.DEFAULT_UNZIP_CACHE_PATH,
        'ignore_system_python_path': ignore_system_python_path,
        'has_main': bool(main),
        'import_main': 'import %s' % module if module else '',
        'run_main': '%s.%s()' % (module, function) if function else '',
        'HANDLE_OTHER_ENVS_FLAG': Config.HANDLE_OTHER_ENVS_FLAG,
        'env_paths': env_paths,
        'LAZY_PIP_DIR_NAME': Config.LAZY_PIP_DIR_NAME,
        'pip_args_repr': repr(pip_args),
        'sys_paths': sys_paths,
        'python_version_slice': python_version_slice,
        'pip_args_md5': pip_args_md5,
    }
    code = get_data('zipapps', '_entry_point.py').decode('u8')
    (cache_path / '__main__.py').write_text(code.format(**kwargs))
    code = get_data('zipapps', 'ensure_zipapps_template.py').decode('u8')
    (cache_path / 'ensure_zipapps.py').write_text(code.format(**kwargs))
    code = get_data('zipapps', 'activate_zipapps.py').decode('u8')
    (cache_path / 'activate_zipapps.py').write_text(code)
    code += '\n\nactivate()'
    if output_name != 'zipapps':
        (cache_path / f'ensure_{output_name}.py').write_text(code)
    (cache_path / f'ensure_zipapps_{output_name}.py').write_text(code)


def clean_pip_cache(path):
    for dist_path in path.glob('*.dist-info'):
        shutil.rmtree(dist_path)
    pycache = path / '__pycache__'
    if pycache.is_dir():
        shutil.rmtree(pycache)


def pip_install(path, pip_args):
    shell_args = [
        sys.executable, '-m', 'pip', 'install', '--target',
        str(path.absolute())
    ] + pip_args
    with subprocess.Popen(shell_args) as proc:
        proc.wait()
    clean_pip_cache(path)


def set_timestamp(_cache_path):
    ts = str(int(time.time() * 10000000))
    (_cache_path / ('_zip_time_%s' % ts)).touch()
    return ts


def _create_archive(_cache_path, output_path, interpreter, compressed):
    if sys.version_info.minor >= 7:
        zipapp.create_archive(source=_cache_path,
                              target=str(output_path.absolute()),
                              interpreter=interpreter,
                              compressed=compressed)
    elif compressed:
        raise RuntimeError('compressed arg only support python3.7+')
    else:
        zipapp.create_archive(source=_cache_path,
                              target=str(output_path.absolute()),
                              interpreter=interpreter)


def get_build_id_name(build_id: str):
    if not build_id:
        return ''
    build_id_str = ''
    if '*' in build_id:
        paths = glob(build_id)
    else:
        paths = build_id.split(',')
    for p in paths:
        try:
            path = Path(p)
            build_id_str += str(path.stat().st_mtime)
        except FileNotFoundError:
            pass
    build_id_str = build_id_str or str(build_id)
    md5_id = md5(build_id_str.encode('utf-8')).hexdigest()
    return f'_build_id_{md5_id}'


def build_exists(build_id_name: str, output_path: Path):
    """
    docstring
    """
    if not build_id_name or not output_path.is_file():
        return False
    with ZipFile(output_path, "r") as zf:
        for member in zf.infolist():
            if member.filename == build_id_name:
                return True
    return False


def create_app(
    includes: str = '',
    cache_path: str = None,
    main: str = '',
    output: str = Config.DEFAULT_OUTPUT_PATH,
    interpreter: str = None,
    compressed: bool = False,
    shell: bool = False,
    unzip: str = '',
    unzip_path: str = '',
    ignore_system_python_path=False,
    main_shell=False,
    pip_args: list = None,
    compiled: bool = False,
    build_id: str = '',
    env_paths: str = '',
    lazy_install: bool = False,
    sys_paths: str = '',
    python_version_slice: int = 2,
):
    tmp_dir: tempfile.TemporaryDirectory = None
    try:
        output_path = Path(output)
        build_id_name = get_build_id_name(build_id)
        if build_exists(build_id_name, output_path=output_path):
            return output_path
        if cache_path:
            _cache_path = Path(cache_path)
        else:
            tmp_dir = tempfile.TemporaryDirectory()
            _cache_path = Path(tmp_dir.name)
        prepare_includes(includes, _cache_path)
        pip_args_md5 = ''
        if pip_args:
            if '-t' in pip_args or '--target' in pip_args:
                raise RuntimeError(
                    'target arg can be set with --cache-path to rewrite the zipapps cache path.'
                )
            if lazy_install:
                _log(
                    'WARNING: `unzip` has been changed to "*" while `lazy_install` is True.'
                )
                unzip = '*'
                # copy files to cache folder
                _temp_pip_path = _cache_path / Config.LAZY_PIP_DIR_NAME
                _temp_pip_path.mkdir(parents=True, exist_ok=True)
                _md5_str = md5(str(pip_args).encode('utf-8')).hexdigest()
                for index, arg in enumerate(pip_args):
                    path = Path(arg)
                    if path.is_file():
                        _md5_str += md5(path.read_bytes()).hexdigest()
                        new_path = _temp_pip_path / path.name
                        shutil.copyfile(path, new_path)
                        _r_path = Path(Config.LAZY_PIP_DIR_NAME) / path.name
                        pip_args[index] = _r_path.as_posix()
                pip_args_md5 = md5(_md5_str.encode('utf-8')).hexdigest()
                _log(f'pip_args_md5: {pip_args_md5}')
                if not unzip_path:
                    _log(
                        f'WARNING: unzip path has been set to `SELF/{Config.DEFAULT_UNZIP_CACHE_PATH}` while `lazy_install` is True and `unzip_path` is null.'
                    )
                    unzip_path = f'SELF/{Config.DEFAULT_UNZIP_CACHE_PATH}'
            else:
                pip_install(_cache_path, pip_args)
        if build_id_name:
            # make build_id file
            (_cache_path / build_id_name).touch()
        prepare_entry(
            _cache_path,
            shell=shell,
            main=main,
            unzip=unzip,
            unzip_path=unzip_path,
            output_path=output_path,
            ignore_system_python_path=ignore_system_python_path,
            main_shell=main_shell,
            ts=set_timestamp(_cache_path),
            env_paths=env_paths,
            pip_args=pip_args,
            sys_paths=sys_paths,
            python_version_slice=python_version_slice,
            pip_args_md5=pip_args_md5,
        )
        if compiled:
            if not unzip:
                _log(
                    'WARNING: compiled .pyc files of __pycache__ folder may not work in zipapp, unless you unzip them.'
                )
            compileall.compile_dir(_cache_path, **Config.COMPILE_KWARGS)
        _create_archive(_cache_path, output_path, interpreter, compressed)
        return output_path
    finally:
        if tmp_dir:
            tmp_dir.cleanup()
