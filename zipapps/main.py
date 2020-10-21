# -*- coding: utf-8 -*-

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipapp
from pathlib import Path

DEFAULT_OUTPUT_PATH = 'app.pyz'
UNZIP_CACHE_TEMPLATE = '%s_unzip_cache'


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
    output_path = output_path or Path(DEFAULT_OUTPUT_PATH)
    output_name = os.path.splitext(Path(output_path).name)[0]
    with open(Path(__file__).parent / '_entry_point.py', encoding='u8') as f:
        module, _, function = main.partition(':')
        if module and (cache_path / module).is_file():
            module = os.path.splitext(module)[0]
        kwargs = {
            'ts': ts,
            'shell': shell,
            'main_shell': main_shell,
            'unzip': unzip,
            'unzip_path': unzip_path or UNZIP_CACHE_TEMPLATE % output_name,
            'ignore_system_python_path': ignore_system_python_path,
            'has_main': bool(main),
            'import_main': 'import %s' % module if module else '',
            'run_main': '%s.%s()' % (module, function) if function else ''
        }
        (cache_path / '__main__.py').write_text(f.read().format(**kwargs))


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


def create_app(
    includes: str = '',
    cache_path: str = None,
    main: str = '',
    output: str = DEFAULT_OUTPUT_PATH,
    interpreter: str = None,
    compressed: bool = False,
    shell: bool = False,
    unzip: str = '',
    unzip_path: str = '',
    ignore_system_python_path=False,
    main_shell=False,
    pip_args: list = None,
):
    tmp_dir: tempfile.TemporaryDirectory = None
    try:
        if cache_path:
            _cache_path = Path(cache_path)
        else:
            tmp_dir = tempfile.TemporaryDirectory()
            _cache_path = Path(tmp_dir.name)
        prepare_includes(includes, _cache_path)
        pip_install(_cache_path, pip_args)
        output_path = Path(output)
        prepare_entry(_cache_path,
                      shell=shell,
                      main=main,
                      unzip=unzip,
                      unzip_path=unzip_path,
                      output_path=output_path,
                      ignore_system_python_path=ignore_system_python_path,
                      main_shell=main_shell,
                      ts=set_timestamp(_cache_path))
        _create_archive(_cache_path, output_path, interpreter, compressed)
        return output_path
    finally:
        if tmp_dir:
            tmp_dir.cleanup()
