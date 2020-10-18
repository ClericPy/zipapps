import argparse
import re
import shutil
import subprocess
import sys
import zipapp
from pathlib import Path

DEFAULT_CACHE_PATH = '_zipapps_cache'
DEFAULT_OUTPUT_PATH = 'app.pyz'
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


def prepare_default_main(cache_path, shell=False):
    _file_name = '_entry_point_shell' if shell else '_entry_point'
    src = Path(__file__).parent / ('%s.py' % _file_name)
    shutil.copyfile(src, cache_path / ('%s.py' % _file_name))
    return '%s:main' % _file_name


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


def create_app(includes: str = '',
               cache_path: str = '',
               main: str = '',
               output: str = DEFAULT_OUTPUT_PATH,
               interpreter: str = None,
               compressed: bool = False,
               shell: bool = False,
               pip_args: list = None):
    cache_path = cache_path or DEFAULT_CACHE_PATH
    _cache_path = Path(cache_path)
    if cache_path == DEFAULT_CACHE_PATH:
        refresh_dir(_cache_path)
    prepare_includes(includes, _cache_path)
    if pip_args:
        if '-t' in pip_args or '--target' in pip_args:
            raise RuntimeError(
                'target arg can be set with --cache-path to rewrite the zipapps cache path.'
            )
        pip_install(_cache_path, pip_args)
    if main:
        if ':' not in main:
            raise RuntimeError(
                'main arg should have ":", please set it like package.__main__:main which package with __main__.py.'
            )
    else:
        main = prepare_default_main(_cache_path, shell=shell)
    if sys.version_info.minor >= 7:
        zipapp.create_archive(source=_cache_path,
                              target=output,
                              interpreter=interpreter,
                              main=main,
                              compressed=compressed)
    elif compressed:
        raise RuntimeError('compressed arg only support python3.7+')
    else:
        zipapp.create_archive(source=_cache_path,
                              target=output,
                              interpreter=interpreter,
                              main=main)
    if cache_path == DEFAULT_CACHE_PATH:
        shutil.rmtree(_cache_path)
    return Path(output)


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
                        default=DEFAULT_CACHE_PATH,
                        help='The cache path of zipapps to store '
                        'site-packages and `includes` files, '
                        'which will be treat as PYTHONPATH.'
                        ' If not set, will create and clean-up automately.')
    parser.add_argument('--shell',
                        action='store_true',
                        help='Only while `main` is not set, used for shell=True'
                        ' in subprocess.Popen')
    args, pip_args = parser.parse_known_args()
    return create_app(includes=args.includes,
                      cache_path=args.cache_path,
                      main=args.main,
                      output=args.output,
                      interpreter=args.interpreter,
                      compressed=args.compress,
                      shell=args.shell,
                      pip_args=pip_args)


if __name__ == "__main__":
    main()
