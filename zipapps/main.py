# -*- coding: utf-8 -*-

import argparse
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
USAGE = r'''
===========================================================================
0. package your code without any requirements

> python3 -m zipapps -c -a ./simple_package -p /usr/bin/python3 -o simple_package.pyz
> ./simple_package.pyz
OR
> python3 -m zipapps -c -a ./simple_package -o simple_package.pyz
> python3 simple_package.pyz

------------------------------------

1. use zipapps to make a standalone app which need bottle installed
> python3 -m zipapps -c -a bottle_server.py -m bottle_server:main bottle
> python3 app.pyz
OR
> python3 -m zipapps -c -a bottle_server.py -m bottle_server:main bottle
> python3 app.pyz

------------------------------------

2. use zipapps for venv
> python3 -m zipapps -c bottle
> python3 app.pyz bottle_server.py
OR
> python3 -m zipapps -c -p /usr/bin/python3 bottle
> ./app.pyz bottle_server.py

------------------------------------

3. advanced usages
3.1 more args
> python3 -m zipapps -c -a package1,package2 -o server.pyz -m package1.server:main -p /usr/bin/python3 -r requirements.txt
> ./server.pyz

3.2 unzip C-libs to cache folder for zipimport do not support .so .pyd files.
    bad
    > python3 -m zipapps -c lxml
    > python3 app.pyz -c "import lxml.html;print(lxml.html.__file__)"
    good
    > python3 -m zipapps -c -u lxml lxml
    > python3 app.pyz -c "import lxml.html;print(lxml.html.__file__)"

PS: all the unknown args will be used by "pip install".
==========================================================================='''


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
                      ts=set_timestamp(_cache_path))
        _create_archive(_cache_path, output_path, interpreter, compressed)
        return output_path
    finally:
        if tmp_dir:
            tmp_dir.cleanup()


def main():
    parser = argparse.ArgumentParser(usage=USAGE)
    parser.add_argument(
        '--output',
        '-o',
        default=DEFAULT_OUTPUT_PATH,
        help='The name of the output file, defaults to "app.pyz".')
    parser.add_argument('--python',
                        '-p',
                        dest='interpreter',
                        default=None,
                        help='The name of the Python interpreter to use '
                        '(default: no shebang line).')
    parser.add_argument('--main',
                        '-m',
                        default='',
                        help='The main function of the application.'
                        ' Format like package.module:function.')
    parser.add_argument('--compress',
                        '-c',
                        action='store_true',
                        help='Compress files with the deflate method,'
                        ' defaults to uncompressed.')
    parser.add_argument('--includes',
                        '-a',
                        default='',
                        help='The files/folders of given dir path'
                        ' will be copied into cache-path, '
                        'which can be import from PYTHONPATH).'
                        ' The path string will be splited by ",".')
    parser.add_argument('--source-dir',
                        '--cache-path',
                        '-cp',
                        default=None,
                        help='The cache path of zipapps to store '
                        'site-packages and `includes` files, '
                        'which will be treat as PYTHONPATH.'
                        ' If not set, will create and clean-up automately.')
    parser.add_argument(
        '--unzip',
        '-u',
        default='',
        help='The names which need to be unzip while running, name without ext. '
        'such as .so/.pyd files(which can not be loaded by zipimport), '
        'or packages with operations of static files. If unzip is *, will unzip all files and folders.'
    )
    parser.add_argument(
        '--unzip-path',
        '-up',
        default='',
        help='The names which need to be unzip while running, name without ext. '
        'such as .so/.pyd files(which can not be loaded by zipimport), '
        'or packages with operations of static files. Defaults to $(appname)_unzip_cache.'
    )
    parser.add_argument('--shell',
                        '-s',
                        action='store_true',
                        help='Only while `main` is not set, used for shell=True'
                        ' in subprocess.Popen')
    parser.add_argument(
        '--strict-python-path',
        '-spp',
        action='store_true',
        dest='ignore_system_python_path',
        help='Ignore global PYTHONPATH, only use app_unzip_cache and app.pyz.')
    if len(sys.argv) == 1:
        return parser.print_help()
    args, pip_args = parser.parse_known_args()
    return create_app(includes=args.includes,
                      cache_path=args.cache_path,
                      main=args.main,
                      output=args.output,
                      interpreter=args.interpreter,
                      compressed=args.compress,
                      shell=args.shell,
                      unzip=args.unzip,
                      unzip_path=args.unzip_path,
                      ignore_system_python_path=args.ignore_system_python_path,
                      pip_args=pip_args)


if __name__ == "__main__":
    main()
