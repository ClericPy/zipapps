import argparse
import sys

from . import __version__
from .main import Config, create_app

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


def main():
    parser = argparse.ArgumentParser(usage=USAGE, prog='Zipapps')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument(
        '--output',
        '-o',
        default=Config.DEFAULT_OUTPUT_PATH,
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
                        '--source-dir',
                        '-cp',
                        default=None,
                        dest='cache_path',
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
                        ' in subprocess.Popen.')
    parser.add_argument(
        '--main-shell',
        '-ss',
        action='store_true',
        dest='main_shell',
        help='Only for `main` is not null, call `main` with subprocess.Popen: '
        '`python -c "import a.b;a.b.c()"`. This is used for `psutil` ImportError of DLL load.'
    )
    parser.add_argument(
        '--strict-python-path',
        '-spp',
        action='store_true',
        dest='ignore_system_python_path',
        help='Ignore global PYTHONPATH, only use app_unzip_cache and app.pyz.')
    parser.add_argument(
        '-cc',
        '--pyc',
        '--compile',
        '--compiled',
        action='store_true',
        dest='compiled',
        help='Compile .py to .pyc for fast import, but zipapp does'
        ' not work unless you unzip it.')
    parser.add_argument(
        '-b',
        '--build-id',
        default='',
        dest='build_id',
        help='a string to skip duplicate builds,'
        ' it can be the paths of files/folders which splited by ",", '
        'then the modify time will be used as build_id. If build_id contains `*`,'
        ' will use `glob` function to get paths. '
        'For example, you can set requirements.txt as your build_id by'
        ' `python3 -m zipapps -b requirements.txt -r requirements.txt` when you use pyz as venv.'
    )
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
                      main_shell=args.main_shell,
                      pip_args=pip_args,
                      compiled=args.compiled,
                      build_id=args.build_id)


if __name__ == "__main__":
    main()
