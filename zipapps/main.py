# -*- coding: utf-8 -*-

import compileall
import json
import re
import shutil
import sys
import tempfile
import time
import typing
import zipapp
from glob import glob
from hashlib import md5
from pathlib import Path
from pkgutil import get_data
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile

__version__ = "2024.08.07"


def get_pip_main(ensurepip_root=None):
    try:
        import pip
    except ImportError:
        import ensurepip

        assert ensurepip._bootstrap(root=ensurepip_root) == 0
        if ensurepip_root:
            for _path in Path(ensurepip_root).glob("**/pip/"):
                if _path.is_dir():
                    sys.path.append(str(_path.parent.absolute()))
                    break
        import pip
    try:
        from pip._internal.cli.main import main

        return main
    except ImportError:
        pass
    try:
        from pip import main

        return main
    except ImportError:
        pass
    try:
        from pip._internal import main

        return main
    except ImportError:
        pass
    return pip.main


class ZipApp(object):
    DEFAULT_OUTPUT_PATH = "app.pyz"
    DEFAULT_UNZIP_CACHE_PATH = "zipapps_cache"
    AUTO_FIX_UNZIP_KEYS = {"AUTO_UNZIP", "AUTO"}
    COMPILE_KWARGS: typing.Dict[str, typing.Any] = {}
    HANDLE_OTHER_ENVS_FLAG = "--zipapps"
    LAZY_PIP_DIR_NAME = "_zipapps_lazy_pip"
    PATH_SPLIT_TAG = ","
    HANDLE_ACTIVATE_ZIPAPPS = "--activate-zipapps"
    ENV_ALIAS = {
        "unzip": "ZIPAPPS_UNZIP",
        "unzip_exclude": "ZIPAPPS_UNZIP_EXCLUDE",
        "unzip_path": "ZIPAPPS_CACHE",
        "ignore_system_python_path": "STRICT_PYTHON_PATH",
        "python_version_slice": "PYTHON_VERSION_SLICE",
        "clear_zipapps_cache": "CLEAR_ZIPAPPS_CACHE",
        "clear_zipapps_self": "CLEAR_ZIPAPPS_SELF",
        "chmod": "UNZIP_CHMOD",
    }

    LOGGING = True

    def __init__(
        self,
        includes: str = "",
        cache_path: typing.Optional[str] = None,
        main: str = "",
        output: typing.Optional[str] = None,
        interpreter: typing.Optional[str] = None,
        compressed: bool = False,
        shell: bool = False,
        unzip: str = "",
        unzip_path: str = "",
        ignore_system_python_path=False,
        main_shell=False,
        pip_args: typing.Optional[list] = None,
        compiled: bool = False,
        build_id: str = "",
        env_paths: str = "",
        lazy_install: bool = False,
        sys_paths: str = "",
        python_version_slice: int = 2,
        ensure_pip: bool = False,
        layer_mode: bool = False,
        layer_mode_prefix: str = "python",
        clear_zipapps_cache: bool = False,
        unzip_exclude: str = "",
        chmod: str = "",
        clear_zipapps_self: bool = False,
        rm_patterns: str = "*.dist-info,__pycache__",
    ):
        """Zip your code.

        :param includes: The given paths will be copied to `cache_path` while packaging, which can be used while running. The path strings will be splited by ",". such as `my_package_dir,my_module.py,my_config.json`, often used for libs not from `pypi` or some special config files, defaults to ''
        :type includes: str, optional
        :param cache_path: if not set, will use TemporaryDirectory, prefix='zipapps_', defaults to None
        :type cache_path: str, optional
        :param main: The entry point function of the application, the `valid format` is: `package.module:function` `package.module` `module:function` `package`, defaults to ''
        :type main: str, optional
        :param output: The path of the output file, defaults to None
        :type output: str, optional
        :param interpreter: The path of the Python interpreter which will be set as the `shebang line`, defaults to `None`. With shebang `/usr/bin/python3` you can run app with `./app.pyz` directly, no need for `python3 app.pyz`, defaults to None
        :type interpreter: str, optional
        :param compressed: only for python3.7+, defaults to False
        :type compressed: bool, optional
        :param shell: whether run python in subprocess, or use runpy if shell is False, defaults to False
        :type shell: bool, optional
        :param unzip: names to be unzip, using `AUTO` is a better choice, defaults to ''. Can be overwrite with environment variable `ZIPAPPS_UNZIP`
        :type unzip: str, optional
        :param unzip_path: If `unzip` arg is not null, cache files will be unzipped to the given path while running. Defaults to `zipapps_cache`, support some internal variables: `$TEMP` means `tempfile.gettempdir()`, `$HOME` means `Path.home()`, `$SELF` means `.pyz` file path, `$PID` means `os.getpid()`, `$CWD` means `Path.cwd()`, defaults to ''
        :type unzip_path: str, optional
        :param ignore_system_python_path: Ignore global PYTHONPATH, only use zipapps_cache and app.pyz, defaults to False
        :type ignore_system_python_path: bool, optional
        :param main_shell: Only for `main` is not null, call `main` with subprocess.Popen: `python -c "import a.b;a.b.c()"`. This is used for `psutil` ImportError of DLL load, defaults to False
        :type main_shell: bool, optional
        :param pip_args: args of `pip install `, defaults to None
        :type pip_args: list, optional
        :param compiled: compile py file into pyc, defaults to False
        :type compiled: bool, optional
        :param build_id: a string to skip duplicate builds, it can be the paths of files/folders which splited by ",", then the modify time will be used as build_id. If build_id contains `*`, will use `glob` function to get paths. For example, you can set requirements.txt as your build_id by `python3 -m zipapps -b requirements.txt -r requirements.txt` when you use pyz as venv, defaults to ''
        :type build_id: str, optional
        :param env_paths: Default --zipapps arg if it is not given while running. Support $TEMP/$HOME/$SELF/$PID/$CWD prefix, separated by commas, defaults to ''
        :type env_paths: str, optional
        :param lazy_install: Install packages with pip while running, which means requirements will not be install into pyz file, defaults to False
        :type lazy_install: bool, optional
        :param sys_paths: Paths be insert to sys.path[0] while running. Support $TEMP/$HOME/$SELF/$PID/$CWD prefix, separated by commas, defaults to ''
        :type sys_paths: str, optional
        :param python_version_slice: Only work for lazy-install mode, then `pip` target folders differ according to sys.version_info[:_slice], defaults to 2, which means 3.8.3 equals to 3.8.4 for same version accuracy 3.8, defaults to 2
        :type python_version_slice: int, optional
        :param ensure_pip: Add the ensurepip package to your pyz file, works for embed-python(windows) or other python versions without `pip` installed but `lazy-install` mode is enabled.
        :type ensure_pip: bool, optional
        :param layer_mode: Layer mode for the serverless use case, __main__.py / ensure_zipapps.py / activate_zipapps.py files will not be set in this mode, which means it will skip the activative process.
        :type layer_mode: bool, optional
        :param layer_mode_prefix: Only work while --layer-mode is set, will move the files in the given prefix folder.
        :type layer_mode_prefix: str, optional
        :param clear_zipapps_cache: Clear the zipapps cache folder after running, but maybe failed for .pyd/.so files.
        :type clear_zipapps_cache: bool, optional
        :param unzip_exclude: names not to be unzip, defaults to '', should be used with unzip. Can be overwrite with environment variable `ZIPAPPS_UNZIP_EXCLUDE`
        :type unzip_exclude: str, optional
        :param chmod: os.chmod(int(chmod, 8)) for unzip files with `--chmod=777`, unix-like system only
        :type chmod: str, optional
        :param clear_zipapps_self: Clear the zipapps pyz file after running.
        :type clear_zipapps_self: bool, optional
        :param rm_patterns: Delete useless files or folders, splited by "," and defaults to `*.dist-info,__pycache__`. Recursively glob: **/*.pyc
        :type rm_patterns: str
        """
        self.includes = includes
        self.cache_path = cache_path
        self.main = main
        self.output = output or self.DEFAULT_OUTPUT_PATH
        self._output_path = Path(self.output)
        self.interpreter = interpreter
        self.compressed = compressed
        self.shell = shell
        self.unzip = unzip
        self.unzip_exclude = unzip_exclude
        self.unzip_path = unzip_path
        self.ignore_system_python_path = ignore_system_python_path
        self.main_shell = main_shell
        self.pip_args = pip_args
        self.compiled = compiled
        self.build_id = build_id
        self.env_paths = env_paths
        self.lazy_install = lazy_install
        self.sys_paths = sys_paths
        self.python_version_slice = python_version_slice
        self.ensure_pip = ensure_pip
        self.layer_mode = layer_mode
        self.layer_mode_prefix = layer_mode_prefix
        self.clear_zipapps_cache = clear_zipapps_cache
        self.clear_zipapps_self = clear_zipapps_self
        self.chmod = chmod
        self.rm_patterns = rm_patterns

        self._tmp_dir: typing.Optional[tempfile.TemporaryDirectory] = None
        self._build_success = False
        self._is_greater_than_python_37 = (
            sys.version_info.minor >= 7 and sys.version_info.major >= 3
        )

    @property
    def kwargs(self):
        return dict(
            includes=self.includes,
            cache_path=str(self.cache_path or ""),
            main=self.main,
            output=self.output,
            interpreter=self.interpreter,
            compressed=self.compressed,
            shell=self.shell,
            unzip=self.unzip,
            unzip_path=self.unzip_path,
            ignore_system_python_path=self.ignore_system_python_path,
            main_shell=self.main_shell,
            pip_args=self.pip_args,
            compiled=self.compiled,
            build_id=self.build_id,
            env_paths=self.env_paths,
            lazy_install=self.lazy_install,
            sys_paths=self.sys_paths,
            python_version_slice=self.python_version_slice,
            ensure_pip=self.ensure_pip,
            layer_mode=self.layer_mode,
            layer_mode_prefix=self.layer_mode_prefix,
            clear_zipapps_cache=self.clear_zipapps_cache,
            unzip_exclude=self.unzip_exclude,
            chmod=self.chmod,
            clear_zipapps_self=self.clear_zipapps_self,
        )

    def ensure_args(self):
        if not self.unzip:
            if self.unzip_exclude:
                self._log(
                    "[WARN]: The arg `unzip_exclude` should not be with `unzip` but `unzip` is null."
                )
            if self.compiled:
                self._log(
                    "[WARN]: The arg `compiled` should not be True while `unzip` is null, because .pyc files of __pycache__ folder may not work in zip file."
                )
            if self.lazy_install:
                self._log(
                    '[WARN]: the `unzip` arg has been changed to "*" while `lazy_install` is True.'
                )
                self.unzip = "*"
        if self.cache_path:
            self._cache_path = Path(self.cache_path)
        else:
            self._tmp_dir = tempfile.TemporaryDirectory(prefix="zipapps_")
            self._cache_path = Path(self._tmp_dir.name)
        if not self.unzip_path:
            if self.lazy_install:
                self._log(
                    f"[WARN]: the arg `unzip_path` has been changed to `SELF/{self.DEFAULT_UNZIP_CACHE_PATH}` while `lazy_install` is True and `unzip_path` is null."
                )
                self.unzip_path = f"SELF/{ZipApp.DEFAULT_UNZIP_CACHE_PATH}"
            else:
                self._log(
                    f"[INFO]: the arg `unzip_path` has been changed to `{self.DEFAULT_UNZIP_CACHE_PATH}` by default."
                )
                self.unzip_path = self.DEFAULT_UNZIP_CACHE_PATH
        self.build_id_name = self.get_build_id_name()
        self._log(
            f"[INFO]: output path is `{self._output_path}`, you can reset it with the arg `output`."
        )

    def prepare_ensure_pip(self):
        if self.ensure_pip:
            import ensurepip

            ensurepip_dir_path = Path(ensurepip.__file__).parent
            shutil.copytree(
                str(ensurepip_dir_path.absolute()),
                self._cache_path / ensurepip_dir_path.name,
            )

    def build(self):
        self._log(
            f'[INFO]: {"=" * 10} Start building `{self._output_path}` with zipapps version <{__version__}> {"=" * 10}'
        )
        self.ensure_args()
        if self.build_exists():
            return self._output_path
        self.prepare_includes()
        self.prepare_ensure_pip()
        self.prepare_pip()
        if not self.layer_mode:
            self.prepare_entry_point()
        if self.build_id_name:
            # make build_id file
            (self._cache_path / self.build_id_name).touch()
        if self.compiled:
            compileall.compile_dir(self._cache_path, **ZipApp.COMPILE_KWARGS)
        self.clean_pip_pycache()
        if self.layer_mode:
            self.create_archive_layer()
        else:
            self.create_archive()
        self._build_success = True
        return self._output_path

    def create_archive_layer(self):
        if self.compressed:
            compression = ZIP_STORED
            compresslevel = 9
        else:
            compression = ZIP_DEFLATED
            compresslevel = 0
        _kwargs = dict(mode="w", compression=compression)
        if self._is_greater_than_python_37:
            _kwargs["compresslevel"] = compresslevel
        with ZipFile(str(self._output_path), **_kwargs) as zf:
            for f in self._cache_path.glob("**/*"):
                zf.write(f, str(f.relative_to(self._cache_path)))

    def create_archive(self):
        if self._is_greater_than_python_37:
            zipapp.create_archive(
                source=self._cache_path,
                target=str(self._output_path.absolute()),
                interpreter=self.interpreter,
                compressed=self.compressed,
            )
        elif self.compressed:
            raise RuntimeError("The arg `compressed` only support python3.7+")
        else:
            zipapp.create_archive(
                source=self._cache_path,
                target=str(self._output_path.absolute()),
                interpreter=self.interpreter,
            )

    def prepare_entry_point(self):
        # reset unzip_names
        unzip_names = set(self.unzip.split(",")) if self.unzip else set()
        warning_names: typing.Dict[str, dict] = {}
        for path in self._cache_path.iterdir():
            _name_not_included = path.name not in unzip_names
            if path.is_dir():
                pyd_counts = len(list(path.glob("**/*.pyd")))
                so_counts = len(list(path.glob("**/*.so")))
                if (pyd_counts or so_counts) and _name_not_included:
                    # warn which libs need to be unzipped
                    if pyd_counts:
                        warning_names.setdefault(path.name, {})[".pyd"] = pyd_counts
                    if so_counts:
                        warning_names.setdefault(path.name, {})[".so"] = so_counts
            elif path.is_file() and path.suffix in (".pyd", ".so"):
                if _name_not_included and path.stem not in unzip_names:
                    warning_names.setdefault(path.name, {})[path.suffix] = 1
        # remove the special keys from unzip_names
        auto_unzip_keys = ZipApp.AUTO_FIX_UNZIP_KEYS & unzip_names
        unzip_names -= auto_unzip_keys
        if warning_names:
            if self.clear_zipapps_cache:
                msg = f"[WARN]: clear_zipapps_cache is True but .pyd/.so files were found {warning_names}"
                self._log(msg)
            if auto_unzip_keys:
                unzip_names |= warning_names.keys()
            else:
                _fix_unzip_names = ",".join(warning_names.keys())
                msg = f"[WARN]: .pyd/.so files may be imported incorrectly, set `--unzip={_fix_unzip_names}` or `--unzip=AUTO` or `--unzip=*` to fix it. {warning_names}"
                self._log(msg)
        new_unzip = ",".join(unzip_names)
        self.unzip = new_unzip
        if self.unzip:
            self._log(
                f"[INFO]: these names will be unzipped while running: {self.unzip}"
            )
        self.prepare_active_zipapps()

    def prepare_active_zipapps(self):
        output_name = Path(self._output_path).stem
        if not re.match(r"^[0-9a-zA-Z_]+$", output_name):
            raise ValueError("The name of `output` should match regex: ^[0-9a-zA-Z_]+$")

        def make_runner():
            if self.main:
                pattern = r"^\w+(\.\w+)?(:\w+)?$"
                if re.match(pattern, self.main):
                    module, _, function = self.main.partition(":")
                    if module:
                        # main may be: 'module.py:main' or 'module.submodule:main'
                        # replace module.py to module
                        module_path = self._cache_path / module
                        if module_path.is_file():
                            module = module_path.stem
                        runner = f"import {module}"
                        if function:
                            runner += f"; {module}.{function}()"
                        self._log(
                            f"[INFO]: -m: matches re.match(r'{pattern}', self.main), add as `{runner}`."
                        )
                        return runner
                else:
                    self._log(
                        f"[INFO]: -m: not matches re.match(r'{pattern}', self.main), add as raw code `{self.main}`."
                    )
                    return self.main
            return ""

        kwargs = {
            "ts": self.setup_timestamp_file(),
            "shell": self.shell,
            "main_shell": self.main_shell,
            "unzip": repr(self.unzip),
            "unzip_exclude": repr(self.unzip_exclude),
            "output_name": output_name,
            "unzip_path": repr(self.unzip_path),
            "ignore_system_python_path": self.ignore_system_python_path,
            "has_main": bool(self.main),
            "run_main": make_runner(),
            "HANDLE_OTHER_ENVS_FLAG": self.HANDLE_OTHER_ENVS_FLAG,
            "env_paths": repr(self.env_paths),
            "LAZY_PIP_DIR_NAME": repr(self.LAZY_PIP_DIR_NAME),
            "pip_args_repr": repr(self.pip_args),
            "sys_paths": repr(self.sys_paths),
            "python_version_slice": repr(self.python_version_slice),
            "pip_args_md5": self.pip_args_md5,
            "clear_zipapps_cache": repr(self.clear_zipapps_cache),
            "HANDLE_ACTIVATE_ZIPAPPS": self.HANDLE_ACTIVATE_ZIPAPPS,
            "chmod": repr(self.chmod),
            "clear_zipapps_self": repr(self.clear_zipapps_self),
        }
        for k, v in self.ENV_ALIAS.items():
            kwargs[f"{k}_env"] = repr(v)
        code = get_data(__name__, "entry_point.py.template").decode("u8")
        (self._cache_path / "__main__.py").write_text(code.format(**kwargs))

        code = get_data(__name__, "ensure_zipapps.py.template").decode("u8")
        (self._cache_path / "ensure_zipapps.py").write_text(code.format(**kwargs))

        code = get_data(__name__, "activate_zipapps.py").decode("u8")
        (self._cache_path / "activate_zipapps.py").write_text(code)
        code += "\n\nactivate()"

        if output_name != "zipapps":
            (self._cache_path / f"ensure_{output_name}.py").write_text(code)
        (self._cache_path / f"ensure_zipapps_{output_name}.py").write_text(code)
        (self._cache_path / "zipapps_config.json").write_text(json.dumps(self.kwargs))

    def setup_timestamp_file(
        self,
    ):
        ts = str(int(time.time() * 10000000))
        (self._cache_path / ("_zip_time_%s" % ts)).touch()
        return ts

    @staticmethod
    def get_md5(value: typing.Any):
        if not isinstance(value, bytes):
            value = str(value).encode("utf-8")
        return md5(value).hexdigest()

    def prepare_pip(self):
        self.pip_args_md5 = ""
        if self.pip_args:
            if "-t" in self.pip_args or "--target" in self.pip_args:
                raise RuntimeError(
                    "`-t` / `--target` arg can be set with `--cache-path`/`cache_path` to rewrite the zipapps cache path."
                )
            if self.lazy_install:
                # copy files to cache folder
                _temp_pip_path = self._cache_path / self.LAZY_PIP_DIR_NAME
                _temp_pip_path.mkdir(parents=True, exist_ok=True)
                _md5_str = self.get_md5(self.pip_args)
                # overwrite path args to new path, such as requirements.txt or xxx.whl
                for index, arg in enumerate(self.pip_args):
                    path = Path(arg)
                    if path.is_file():
                        _md5_str += self.get_md5(path.read_bytes())
                        new_path = _temp_pip_path / path.name
                        shutil.copyfile(path, new_path)
                        _r_path = Path(self.LAZY_PIP_DIR_NAME) / path.name
                        self.pip_args[index] = _r_path.as_posix()
                self.pip_args_md5 = self.get_md5(_md5_str.encode("utf-8"))
                self._log(
                    f"[INFO]: pip_args_md5 has been generated: {self.pip_args_md5}"
                )
            else:
                self.pip_install()

    @classmethod
    def _rm_with_patterns(
        cls,
        target_dir: Path,
        patterns=("*.dist-info", "__pycache__"),
    ):
        target_dir = Path(target_dir)
        for pattern in patterns:
            if pattern:
                for path in target_dir.glob(pattern):
                    if path.is_dir():
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        try:
                            path.unlink()
                        except FileNotFoundError:
                            pass

    @classmethod
    def _pip_install(cls, target_dir: Path, pip_args: list):
        target_dir = Path(target_dir)
        _pip_args = [
            "install",
            "--target",
            target_dir.absolute().as_posix(),
        ] + pip_args
        pip_main = get_pip_main()
        result = pip_main(_pip_args)
        if result != 0:
            raise RuntimeError("pip install failed: return code=%s" % result)

    def clean_pip_pycache(self):
        if self.layer_mode:
            target_dir = self._cache_path / self.layer_mode_prefix
        else:
            target_dir = self._cache_path
        return self._rm_with_patterns(target_dir, patterns=self.rm_patterns.split(","))

    def pip_install(self):
        if self.layer_mode:
            _target_dir = self._cache_path.absolute() / self.layer_mode_prefix
        else:
            _target_dir = self._cache_path
        return self._pip_install(target_dir=_target_dir, pip_args=self.pip_args)

    def prepare_includes(self):
        if not self.includes:
            return
        if self.layer_mode:
            _target_dir = self._cache_path.absolute() / self.layer_mode_prefix
        else:
            _target_dir = self._cache_path.absolute()
        _target_dir.mkdir(parents=True, exist_ok=True)
        for _include_path in self.includes.split(self.PATH_SPLIT_TAG):
            include_path = Path(_include_path)
            if include_path.is_dir():
                shutil.copytree(include_path, _target_dir / include_path.name)
            elif include_path.is_file():
                shutil.copyfile(include_path, _target_dir / include_path.name)
            else:
                raise RuntimeError("%s is not exist" % include_path.absolute())

    def build_exists(self):
        if self.build_id_name and self._output_path.is_file():
            try:
                with ZipFile(self._output_path, "r") as zf:
                    for member in zf.infolist():
                        if member.filename == self.build_id_name:
                            return True
            except BadZipFile:
                pass
        return False

    def get_build_id_name(self):
        if not self.build_id:
            return ""
        build_id_str = ""
        if "*" in self.build_id:
            paths = glob(self.build_id)
        else:
            paths = self.build_id.split(",")
        for p in paths:
            try:
                path = Path(p)
                build_id_str += str(path.stat().st_mtime)
            except FileNotFoundError:
                pass
        build_id_str = build_id_str or str(self.build_id)
        md5_id = self.get_md5(build_id_str.encode("utf-8"))
        return f"_build_id_{md5_id}"

    @classmethod
    def create_app(
        cls,
        includes: str = "",
        cache_path: typing.Optional[str] = None,
        main: str = "",
        output: typing.Optional[str] = None,
        interpreter: typing.Optional[str] = None,
        compressed: bool = False,
        shell: bool = False,
        unzip: str = "",
        unzip_path: str = "",
        ignore_system_python_path=False,
        main_shell=False,
        pip_args: typing.Optional[list] = None,
        compiled: bool = False,
        build_id: str = "",
        env_paths: str = "",
        lazy_install: bool = False,
        sys_paths: str = "",
        python_version_slice: int = 2,
        ensure_pip: bool = False,
        layer_mode: bool = False,
        layer_mode_prefix: str = "python",
        clear_zipapps_cache: bool = False,
        unzip_exclude: str = "",
        chmod: str = "",
        clear_zipapps_self: bool = False,
        rm_patterns: str = "*.dist-info,__pycache__",
    ):
        app = cls(
            includes=includes,
            cache_path=cache_path,
            main=main,
            output=output,
            interpreter=interpreter,
            compressed=compressed,
            shell=shell,
            unzip=unzip,
            unzip_path=unzip_path,
            ignore_system_python_path=ignore_system_python_path,
            main_shell=main_shell,
            pip_args=pip_args,
            compiled=compiled,
            build_id=build_id,
            env_paths=env_paths,
            lazy_install=lazy_install,
            sys_paths=sys_paths,
            python_version_slice=python_version_slice,
            ensure_pip=ensure_pip,
            layer_mode=layer_mode,
            layer_mode_prefix=layer_mode_prefix,
            clear_zipapps_cache=clear_zipapps_cache,
            unzip_exclude=unzip_exclude,
            chmod=chmod,
            clear_zipapps_self=clear_zipapps_self,
            rm_patterns=rm_patterns,
        )
        return app.build()

    @classmethod
    def _log(cls, text):
        if cls.LOGGING:
            sys.stderr.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} | {text}\n')

    def __del__(self):
        if self._tmp_dir:
            self._tmp_dir.cleanup()
            self._log(f"[INFO]: Temp cache has been cleaned. ({self._tmp_dir!r})")
        if self._build_success:
            self._log(
                f'[INFO]: {"=" * 10} Successfully built `{self._output_path}` {"=" * 10}'
            )
        else:
            self._log(f'[ERROR]: {"=" * 10} Build failed {"=" * 10}')


def pip_install_target(
    target: Path,
    pip_args: list,
    rm_patterns: str = "*.dist-info,__pycache__",
    force=False,
    clear_dir=False,
    sys_path: typing.Optional[int] = None,
):
    """
    Installs target dependencies using pip and cleans up the installed files afterwards.

    Args:
        target (Path): The target directory for dependency installation.
        pip_args (list): List of arguments for the pip install command.
        rm_patterns (str, optional): Patterns of files to remove after installation, defaults to "*.dist-info,__pycache__".
        force (bool, optional): Flag to force reinstallation, defaults to False.
        clear_dir (bool, optional): will rmtree the target directory while clear_dir=True.
        sys_path (typing.Optional[int], optional): If provided, inserts the target directory at the specified position in sys.path.

    Returns:
        bool: Returns True if the installation is successful.
    """
    target = Path(target)
    md5_path = target / ZipApp.get_md5(pip_args)
    if not force and md5_path.exists():
        return False
    if clear_dir and target.is_dir():
        shutil.rmtree(target.as_posix(), ignore_errors=True)
    ZipApp._pip_install(target_dir=target, pip_args=pip_args)
    if rm_patterns:
        ZipApp._rm_with_patterns(target, patterns=rm_patterns.split(","))

    md5_path.touch()
    if isinstance(sys_path, int):
        sys.path.insert(sys_path, target.absolute().as_posix())
    return True


create_app = ZipApp.create_app
