# -*- coding: utf-8 -*-

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
import zipapp
from pathlib import Path

DEFAULT_CACHE_PATH = '_zipapps_cache'
DEFAULT_OUTPUT_PATH = 'app.pyz'
UNZIP_CACHE_TEMPLATE = '%s_'
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
python3 -m zipapps -c -a package1,package2 -o server.pyz -m package1.server:main -p /usr/bin/python3 -r requirements.txt
./server.pyz


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
                  output_name='noname',
                  ignore_system_python_path=False,
                  ts='None'):
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


def create_app(
    includes: str = '',
    cache_path: str = '',
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
    cache_path = cache_path or DEFAULT_CACHE_PATH
    _cache_path = Path(cache_path)
    if cache_path == DEFAULT_CACHE_PATH:
        refresh_dir(_cache_path)
    ts = set_timestamp(_cache_path)
    prepare_includes(includes, _cache_path)
    if pip_args:
        if '-t' in pip_args or '--target' in pip_args:
            raise RuntimeError(
                'target arg can be set with --cache-path to rewrite the zipapps cache path.'
            )
        pip_install(_cache_path, pip_args)
    output_path = Path(output)
    output_name = os.path.splitext(Path(output_path).name)[0]
    prepare_entry(_cache_path,
                  shell=shell,
                  main=main,
                  unzip=unzip,
                  unzip_path=unzip_path,
                  output_name=output_name,
                  ignore_system_python_path=ignore_system_python_path,
                  ts=ts)
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
    if cache_path == DEFAULT_CACHE_PATH:
        for _ in range(3):
            try:
                if not _cache_path.is_dir():
                    break
                shutil.rmtree(_cache_path)
            except FileNotFoundError:
                break
    return output_path


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
    parser.add_argument('--cache-path',
                        '-cp',
                        default=DEFAULT_CACHE_PATH,
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
        'or packages with operations of static files.')
    parser.add_argument(
        '--unzip-path',
        '-up',
        default='',
        help='The names which need to be unzip while running, name without ext. '
        'such as .so/.pyd files(which can not be loaded by zipimport), '
        'or packages with operations of static files.')
    parser.add_argument('--shell',
                        '-s',
                        action='store_true',
                        help='Only while `main` is not set, used for shell=True'
                        ' in subprocess.Popen')
    parser.add_argument('--strict-python-path',
                        '-spp',
                        action='store_true',
                        dest='ignore_system_python_path',
                        help='Skip global PYTHONPATH.')
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
