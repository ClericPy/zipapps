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
    parser.add_argument('--output',
                        '-o',
                        default=Config.DEFAULT_OUTPUT_PATH,
                        help='The path of the output file, defaults to'
                        f' "{Config.DEFAULT_OUTPUT_PATH}".')
    parser.add_argument(
        '--python',
        '-p',
        dest='interpreter',
        default=None,
        help='The path of the Python interpreter which will be '
        'set as the `shebang line`, defaults to `None`. With shebang `/usr/bin/python3` you can run app with `./app.pyz` directly, no need for `python3 app.pyz`'
    )
    parser.add_argument(
        '--main',
        '-m',
        default='',
        help='The entry point function of the application, the '
        '`valid format` is: `package.module:function` `package.module` `module:function` `package`'
    )
    parser.add_argument('--compress',
                        '-c',
                        action='store_true',
                        help='compress files with the deflate method or not.')
    parser.add_argument(
        '--includes',
        '--add',
        '-a',
        default='',
        help='The given paths will be copied to `cache_path` while packaging, '
        'which can be used while running. The path strings will be splited by ",". '
        'such as `my_package_dir,my_module.py,my_config.json`, often used for libs not from `pypi` or some special config files'
    )
    parser.add_argument(
        '--unzip',
        '-u',
        default='',
        help='The names which need to be unzipped while running, splited by "," '
        '`without ext`, such as `bottle,aiohttp`, or the complete path like `bin/bottle.py,temp.py`. For `.so/.pyd` files(which can not be loaded by zipimport), or packages with operations of static files. if unzip is set to "*", then will unzip all files and folders. if unzip is set to **AUTO**, then will add the `.pyd` and `.so` files automatically.'
    )
    parser.add_argument(
        '--unzip-path',
        '-up',
        default='',
        help='If `unzip` arg is not null, cache files will be unzipped to the '
        'given path while running. Defaults to `zipapps_cache`, support some internal variables: `TEMP/HOME/SELF` as internal variables, for example `HOME/zipapps_cache`. `TEMP` means `tempfile.gettempdir()`, `HOME` means `Path.home()`, `SELF` means `.pyz` file path.'
    )
    parser.add_argument(
        '-cc',
        '--pyc',
        '--compile',
        '--compiled',
        action='store_true',
        dest='compiled',
        help='Compile .py to .pyc for fast import, but zipapp does not work '
        'unless you unzip it.')
    parser.add_argument('--cache-path',
                        '--source-dir',
                        '-cp',
                        default=None,
                        dest='cache_path',
                        help='The cache path of zipapps to store '
                        'site-packages and `includes` files, '
                        'which will be treat as PYTHONPATH. If not set, will '
                        'create and clean-up in TEMP dir automately.')
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
        help='Ignore global PYTHONPATH, only use zipapps_cache and app.pyz.')
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
    parser.add_argument(
        '--zipapps',
        '--env-paths',
        default='',
        dest='env_paths',
        help='Default --zipapps arg if it is not given while running.'
        ' Support TEMP/HOME/SELF prefix, separated by commas.')
    parser.add_argument(
        '--delay',
        '-d',
        '--lazy-pip',
        '--lazy-install',
        '--lazy-pip-install',
        action='store_true',
        dest='lazy_install',
        help='Install packages with pip while running, which means '
        'requirements will not be install into pyz file.')
    parser.add_argument(
        '-pva',
        '--python-version-accuracy',
        '--python-version-slice',
        default='2',
        dest='python_version_slice',
        help='Only work for lazy-install mode, then `pip` target folders differ '
        'according to sys.version_info[:_slice], defaults to 2, which means '
        '3.8.3 equals to 3.8.4 for same version accuracy 3.8')
    parser.add_argument('--sys-paths',
                        '--sys-path',
                        '--py-path',
                        '--python-path',
                        default='',
                        dest='sys_paths',
                        help='Paths be insert to sys.path[-1] while running.'
                        ' Support TEMP/HOME/SELF prefix, separated by commas.')
    if len(sys.argv) == 1:
        return parser.print_help()
    args, pip_args = parser.parse_known_args()
    return create_app(
        includes=args.includes,
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
        build_id=args.build_id,
        env_paths=args.env_paths,
        lazy_install=args.lazy_install,
        sys_paths=args.sys_paths,
        python_version_slice=int(args.python_version_slice),
    )


if __name__ == "__main__":
    main()
