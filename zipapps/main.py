# -*- coding: utf-8 -*-

import compileall
import os
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
from warnings import warn
from zipfile import ZipFile


class Config:
    """
    Default args
    """
    DEFAULT_OUTPUT_PATH = 'app.pyz'
    UNZIP_CACHE_TEMPLATE = '%s_unzip_cache'
    COMPILE_KWARGS: typing.Dict[str, typing.Any] = {}


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


def prepare_entry(cache_path: Path,
                  shell=False,
                  main='',
                  unzip='',
                  unzip_path='',
                  output_path: Path = None,
                  ignore_system_python_path=False,
                  main_shell=False,
                  ts='None'):
    output_path = output_path or Path(Config.DEFAULT_OUTPUT_PATH)
    output_name = os.path.splitext(Path(output_path).name)[0]
    if not re.match(r'^[0-9a-zA-Z_]+$', output_name):
        raise ValueError('output_name should match regex: [0-9a-zA-Z_]+')
    module, _, function = main.partition(':')
    if module and (cache_path / module).is_file():
        module = os.path.splitext(module)[0]
    kwargs = {
        'ts': ts,
        'shell': shell,
        'main_shell': main_shell,
        'unzip': unzip,
        'output_name': output_name,
        'unzip_path': unzip_path or Config.UNZIP_CACHE_TEMPLATE % output_name,
        'ignore_system_python_path': ignore_system_python_path,
        'has_main': bool(main),
        'import_main': 'import %s' % module if module else '',
        'run_main': '%s.%s()' % (module, function) if function else ''
    }
    with open(Path(__file__).parent / '_entry_point.py', encoding='u8') as f:
        (cache_path / '__main__.py').write_text(f.read().format(**kwargs))
    with open(Path(__file__).parent / 'ensure_zipapps_template.py',
              encoding='u8') as f:
        (cache_path / f'ensure_zipapps_{output_name}.py').write_text(
            f.read().format(**kwargs))
    code = f'import ensure_zipapps_{output_name}'
    (cache_path / 'ensure_zipapps.py').write_text(code)


def clean_pip_cache(path):
    for dist_path in path.glob('*.dist-info'):
        shutil.rmtree(dist_path)
    pycache = path / '__pycache__'
    if pycache.is_dir():
        shutil.rmtree(pycache)


def pip_install(path, pip_args):
    if pip_args:
        if '-t' in pip_args or '--target' in pip_args:
            raise RuntimeError(
                'target arg can be set with --cache-path to rewrite the zipapps cache path.'
            )
        shell_args = [
            sys.executable, '-m', 'pip', 'install', '--target',
            str(path.absolute())
        ] + pip_args
        subprocess.Popen(shell_args).wait()
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


def create_app(includes: str = '',
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
               build_id: str = ''):
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
        pip_install(_cache_path, pip_args)
        if build_id_name:
            # make build_id file
            (_cache_path / build_id_name).touch()
        prepare_entry(_cache_path,
                      shell=shell,
                      main=main,
                      unzip=unzip,
                      unzip_path=unzip_path,
                      output_path=output_path,
                      ignore_system_python_path=ignore_system_python_path,
                      main_shell=main_shell,
                      ts=set_timestamp(_cache_path))
        if compiled:
            if not unzip:
                warn(
                    'compiled .pyc files of __pycache__ folder may not work in zipapp, unless you unzip them.'
                )
            compileall.compile_dir(_cache_path, **Config.COMPILE_KWARGS)
        _create_archive(_cache_path, output_path, interpreter, compressed)
        return output_path
    finally:
        if tmp_dir:
            tmp_dir.cleanup()
