import argparse
import json
import sys
import time
import typing
from pathlib import Path

from . import __version__
from .main import ZipApp

USAGE = r"""
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
==========================================================================="""

PIP_PYZ_URL = "https://bootstrap.pypa.io/pip/pip.pyz"
DOWNLOAD_PYTHON_URL = "https://www.github.com/indygreg/python-build-standalone"


def _get_now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _get_pth_path():
    py_exe_path = Path(sys.executable)
    for _path in py_exe_path.parent.glob("*._pth"):
        _pth_path = _path
        break
    else:
        fname = f"python{sys.version_info.major}{sys.version_info.minor}._pth"
        _pth_path = py_exe_path.parent / fname
    return _pth_path


def _append_pth():
    import re

    _pth_path = _get_pth_path()
    if _pth_path.is_file():
        print("find _pth file:", _pth_path.as_posix(), flush=True, file=sys.stderr)
        _path_bytes = _pth_path.read_bytes()
    else:
        _path_bytes = b""
    if not re.search(b"^import site$", _path_bytes):
        _path_bytes += b"\nimport site\n"
    if not re.search(b"^pip\.pyz$", _path_bytes):
        _path_bytes += b"\npip.pyz\n"
    _pth_path.write_bytes(_path_bytes)


def download_pip_pyz(target: typing.Optional[Path] = None, log=True):
    from urllib.request import urlretrieve

    pip_pyz_path = Path(target or (Path(sys.executable).parent / "pip.pyz"))
    if log:
        msg = f"Download {PIP_PYZ_URL} -> {pip_pyz_path.absolute().as_posix()}"
        print(_get_now(), msg, flush=True, file=sys.stderr)
    if pip_pyz_path.is_file():
        pip_pyz_path.unlink()
    urlretrieve(
        url=PIP_PYZ_URL,
        filename=pip_pyz_path.absolute().as_posix(),
        reporthook=lambda a, b, c: print(
            _get_now(),
            f"Downloading {int(100*(1+a)*b/c)}%, {(1 + a) * b} / {c}",
            end="\r",
            flush=True,
            file=sys.stderr,
        )
        if log
        else None,
    )
    try:
        sys.path.append(pip_pyz_path.absolute().as_posix())
        import pip

        assert pip

        if log:
            print(f"\n{_get_now()} install pip ok", flush=True, file=sys.stderr)
        return True
    except ImportError:
        if log:
            print(f"\n{_get_now()} install pip failed", flush=True, file=sys.stderr)


def handle_win32_embeded():
    _pth_path = _get_pth_path()

    if not _pth_path.is_file():
        return
    try:
        import pip

        assert pip

        return
    except ImportError:
        need_install = (
            input(f'\n{"=" * 50}\npip module not found, try installing?(Y/n)')
            .lower()
            .strip()
            or "y"
        )
        if need_install != "y":
            return
    print("find _pth file:", _pth_path.as_posix(), flush=True, file=sys.stderr)
    if download_pip_pyz():
        _append_pth()
    import os

    os.system("%s -m pip -V" % Path(sys.executable).as_posix())
    os.system("pause")


def main():
    parser = argparse.ArgumentParser(usage=USAGE, prog="Zipapps")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--output",
        "-o",
        default=ZipApp.DEFAULT_OUTPUT_PATH,
        help="The path of the output file, defaults to"
        f' "{ZipApp.DEFAULT_OUTPUT_PATH}".',
    )
    parser.add_argument(
        "--python",
        "-p",
        dest="interpreter",
        default=None,
        help="The path of the Python interpreter which will be "
        "set as the `shebang line`, defaults to `None`. With shebang `/usr/bin/python3` you can run app with `./app.pyz` directly, no need for `python3 app.pyz`",
    )
    parser.add_argument(
        "--main",
        "-m",
        default="",
        help="The entry point function of the application, "
        "the format is: `package` | `package.module` | `package.module:function` | `module:function`",
    )
    parser.add_argument(
        "--compress",
        "-c",
        dest="compressed",
        action="store_true",
        help="compress files with the deflate method or not.",
    )
    parser.add_argument(
        "--includes",
        "--add",
        "-a",
        default="",
        help="The given paths will be copied to `cache_path` while packaging, "
        'which can be used while running. The path strings will be splited by ",". '
        "such as `my_package_dir,my_module.py,my_config.json`, often used for libs not from `pypi` or some special config files",
    )
    parser.add_argument(
        "--unzip",
        "-u",
        default="",
        help='The names which need to be unzipped while running, splited by "," '
        '`without ext`, such as `bottle,aiohttp`, or the complete path like `bin/bottle.py,temp.py`. For `.so/.pyd` files(which can not be loaded by zipimport), or packages with operations of static files. if unzip is set to "*", then will unzip all files and folders. if unzip is set to **AUTO**, then will add the `.pyd` and `.so` files automatically. Can be overwrite with environment variable `ZIPAPPS_UNZIP`',
    )
    parser.add_argument(
        "--unzip-exclude",
        "-ue",
        default="",
        dest="unzip_exclude",
        help="The opposite of `--unzip` / `-u` which will not be unzipped, "
        "should be used with `--unzip` / `-u`. Can be overwrite with environment variable `ZIPAPPS_UNZIP_EXCLUDE`",
    )
    parser.add_argument(
        "--unzip-path",
        "-up",
        default="",
        help="If `unzip` arg is not null, cache files will be unzipped to the "
        "given path while running. Defaults to `zipapps_cache`, support some internal variables: `$TEMP/$HOME/$SELF/$PID/$CWD` as internal variables, for example `$HOME/zipapps_cache`. `$TEMP` means `tempfile.gettempdir()`, `$HOME` means `Path.home()`, `$SELF` means `.pyz` file path, `$PID` means `os.getpid()`, `$CWD` means `Path.cwd()`.",
    )
    parser.add_argument(
        "-cc",
        "--pyc",
        "--compiled",
        action="store_true",
        dest="compiled",
        help="Compile .py to .pyc for fast import, but zipapp does not work "
        "unless you unzip it.",
    )
    parser.add_argument(
        "--cache-path",
        "--source-dir",
        "-cp",
        default=None,
        dest="cache_path",
        help="The cache path of zipapps to store "
        "site-packages and `includes` files, "
        "which will be treat as PYTHONPATH. If not set, will "
        "create and clean-up in TEMP dir automately.",
    )
    parser.add_argument(
        "--shell",
        "-s",
        action="store_true",
        help="Only while `main` is not set, used for shell=True"
        " in subprocess.Popen.",
    )
    parser.add_argument(
        "--main-shell",
        "-ss",
        action="store_true",
        dest="main_shell",
        help="Only for `main` is not null, call `main` with subprocess.Popen: "
        '`python -c "import a.b;a.b.c()"`. This is used for `psutil` ImportError of DLL load.',
    )
    parser.add_argument(
        "--strict-python-path",
        "-spp",
        action="store_true",
        dest="ignore_system_python_path",
        help="Ignore global PYTHONPATH, only use zipapps_cache and app.pyz.",
    )
    parser.add_argument(
        "-b",
        "--build-id",
        default="",
        dest="build_id",
        help="a string to skip duplicate builds,"
        ' it can be the paths of files/folders which splited by ",", then the modify time will be used as build_id. If build_id contains `*`, will use `glob` function to get paths. For example, you can set requirements.txt as your build_id by `python3 -m zipapps -b requirements.txt -r requirements.txt` when you use pyz as venv.',
    )
    parser.add_argument(
        "--zipapps",
        "--env-paths",
        default="",
        dest="env_paths",
        help="Default --zipapps arg if it is not given while running."
        " Also support $TEMP/$HOME/$SELF/$PID/$CWD prefix, separated by commas.",
    )
    parser.add_argument(
        "--delay",
        "-d",
        "--lazy-pip",
        "--lazy-install",
        "--lazy-pip-install",
        action="store_true",
        dest="lazy_install",
        help="Install packages with pip while running, which means "
        "requirements will not be install into pyz file. Default unzip path will be changed to `SELF/zipapps_cache`",
    )
    parser.add_argument(
        "-pva",
        "--python-version-accuracy",
        "--python-version-slice",
        default=2,
        type=int,
        dest="python_version_slice",
        help="Only work for lazy-install mode, then `pip` target folders differ "
        "according to sys.version_info[:_slice], defaults to 2, which means "
        "3.8.3 equals to 3.8.4 for same version accuracy 3.8",
    )
    parser.add_argument(
        "--sys-paths",
        "--sys-path",
        "--py-path",
        "--python-path",
        default="",
        dest="sys_paths",
        help="Paths be insert to sys.path[-1] while running."
        " Support $TEMP/$HOME/$SELF/$PID/$CWD prefix, separated by commas.",
    )
    parser.add_argument(
        "--activate",
        default="",
        dest="activate",
        help="Activate the given paths of zipapps app, "
        "only activate them but not run them, separated by commas.",
    )
    parser.add_argument(
        "--ensure-pip",
        action="store_true",
        dest="ensure_pip",
        help="Add the ensurepip package to your pyz file, works for "
        "embed-python(windows) or other python versions without `pip`"
        " installed but `lazy-install` mode is enabled. [EXPERIMENTAL]",
    )
    parser.add_argument(
        "--layer-mode",
        action="store_true",
        dest="layer_mode",
        help="Layer mode for the serverless use case, "
        "__main__.py / ensure_zipapps.py / activate_zipapps.py files will not be set in this mode.",
    )
    parser.add_argument(
        "--layer-mode-prefix",
        default="python",
        dest="layer_mode_prefix",
        help="Only work while --layer-mode is set, "
        "will move the files in the given prefix folder.",
    )
    parser.add_argument(
        "-czc",
        "--clear-zipapps-cache",
        action="store_true",
        dest="clear_zipapps_cache",
        help="Clear the zipapps cache folder after running, "
        "but maybe failed for .pyd/.so files.",
    )
    parser.add_argument(
        "-czs",
        "--clear-zipapps-self",
        action="store_true",
        dest="clear_zipapps_self",
        help="Clear the zipapps pyz file self after running.",
    )
    parser.add_argument(
        "--chmod",
        default="",
        dest="chmod",
        help="os.chmod(int(chmod, 8)) for unzip files with `--chmod=777`,"
        " unix-like system only",
    )
    parser.add_argument(
        "--dump-config",
        default="",
        dest="dump_config",
        help="Dump zipapps build args into JSON string."
        " A file path needed and `-` means stdout.",
    )
    parser.add_argument(
        "--load-config",
        default="",
        dest="load_config",
        help="Load zipapps build args from a JSON file.",
    )
    parser.add_argument(
        "--freeze-reqs",
        default="",
        dest="freeze",
        help="Freeze package versions of pip args with venv,"
        " output to the given file path.",
    )
    parser.add_argument(
        "-q",
        "--quite",
        action="count",
        dest="quite_mode",
        help="mute logs.",
    )
    parser.add_argument(
        "--download-pip-pyz",
        default="",
        dest="download_pip_pyz",
        help=f'Download pip.pyz from "{PIP_PYZ_URL}"',
    )
    parser.add_argument(
        "--download-python",
        action="store_true",
        dest="download_python",
        help=f'Download standalone python from "{DOWNLOAD_PYTHON_URL}"',
    )
    parser.add_argument(
        "--rm-patterns",
        default="*.dist-info,__pycache__",
        dest="rm_patterns",
        help='Delete useless files or folders, splited by "," and defaults to `*.dist-info,__pycache__`. Recursively glob: **/*.pyc',
    )
    if len(sys.argv) == 1:
        parser.print_help()
        handle_win32_embeded()
        return
    args, pip_args = parser.parse_known_args()
    if args.download_python:
        from .download_python import download_python

        return download_python()
    elif args.download_pip_pyz:
        return download_pip_pyz(args.download_pip_pyz)
    if args.quite_mode:
        ZipApp.LOGGING = False
        if "-q" not in pip_args and "--quiet" not in pip_args:
            pip_args.append(f'-{"q" * args.quite_mode}')
    ZipApp._log(f"zipapps args: {args}, pip install args: {pip_args}")
    if args.activate:
        from .activate_zipapps import activate

        for path in args.activate.split(","):
            activate(path)
        return
    if args.freeze:
        from .freezing import FreezeTool

        with FreezeTool(args.freeze, pip_args) as ft:
            ft.run()
        return
    if args.load_config:
        with open(args.load_config, "r", encoding="utf-8") as f:
            kwargs = json.load(f)
            app = ZipApp(**kwargs)
    else:
        app = ZipApp(
            includes=args.includes,
            cache_path=args.cache_path,
            main=args.main,
            output=args.output,
            interpreter=args.interpreter,
            compressed=args.compressed,
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
            ensure_pip=args.ensure_pip,
            layer_mode=args.layer_mode,
            layer_mode_prefix=args.layer_mode_prefix,
            clear_zipapps_cache=args.clear_zipapps_cache,
            unzip_exclude=args.unzip_exclude,
            chmod=args.chmod,
            clear_zipapps_self=args.clear_zipapps_self,
            rm_patterns=args.rm_patterns,
        )
    if args.dump_config:
        config_json = json.dumps(app.kwargs)
        if args.dump_config == "-":
            print(config_json)
        else:
            with open(args.dump_config, "w", encoding="utf-8") as f:
                f.write(config_json)
    else:
        return app.build()


if __name__ == "__main__":
    main()
