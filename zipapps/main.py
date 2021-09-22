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
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipFile, ZipFile

__version__ = '2021.09.22'


class ZipApp(object):
    DEFAULT_OUTPUT_PATH = 'app.pyz'
    DEFAULT_UNZIP_CACHE_PATH = 'zipapps_cache'
    AUTO_FIX_UNZIP_KEYS = {'AUTO_UNZIP', 'AUTO'}
    COMPILE_KWARGS: typing.Dict[str, typing.Any] = {}
    HANDLE_OTHER_ENVS_FLAG = '--zipapps'
    LAZY_PIP_DIR_NAME = '_zipapps_lazy_pip'
    PATH_SPLIT_TAG = ','

    def __init__(
        self,
        includes: str = '',
        cache_path: str = None,
        main: str = '',
        output: str = None,
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
        ensure_pip: bool = False,
        layer_mode: bool = False,
        layer_mode_prefix: str = 'python',
    ):
        """Zip your code.

        :param includes: The given paths will be copied to `cache_path` while packaging, which can be used while running. The path strings will be splited by ",". such as `my_package_dir,my_module.py,my_config.json`, often used for libs not from `pypi` or some special config files, defaults to ''
        :type includes: str, optional
        :param cache_path: if not set, will use TemporaryDirectory, defaults to None
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
        :param unzip: names to be unzip, using `AUTO` is a better choice, defaults to ''
        :type unzip: str, optional
        :param unzip_path: If `unzip` arg is not null, cache files will be unzipped to the given path while running. Defaults to `zipapps_cache`, support some internal variables: `TEMP/HOME/SELF` as internal variables, for example `HOME/zipapps_cache`. `TEMP` means `tempfile.gettempdir()`, `HOME` means `Path.home()`, `SELF` means `.pyz` file path, defaults to ''
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
        :param env_paths: Default --zipapps arg if it is not given while running. Support TEMP/HOME/SELF prefix, separated by commas, defaults to ''
        :type env_paths: str, optional
        :param lazy_install: Install packages with pip while running, which means requirements will not be install into pyz file, defaults to False
        :type lazy_install: bool, optional
        :param sys_paths: Paths be insert to sys.path[-1] while running. Support TEMP/HOME/SELF prefix, separated by commas, defaults to ''
        :type sys_paths: str, optional
        :param python_version_slice: Only work for lazy-install mode, then `pip` target folders differ according to sys.version_info[:_slice], defaults to 2, which means 3.8.3 equals to 3.8.4 for same version accuracy 3.8, defaults to 2
        :type python_version_slice: int, optional
        :param ensure_pip: Add the ensurepip package to your pyz file, works for embed-python(windows) or other python versions without `pip` installed but `lazy-install` mode is enabled.
        :type includes: bool, optional
        :param layer_mode: Layer mode for the serverless use case, __main__.py / ensure_zipapps.py / activate_zipapps.py files will not be set in this mode, which means it will skip the activative process.
        :type includes: bool, optional
        :param layer_mode_prefix: Only work while --layer-mode is set, will move the files in the given prefix folder.
        :type includes: str, optional
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

        self._tmp_dir: tempfile.TemporaryDirectory = None
        self._build_success = False
        self._is_greater_than_python_37 = sys.version_info.minor >= 7 and sys.version_info.major >= 3

    def ensure_args(self):
        if not self.unzip:
            if self.compiled:
                self._log(
                    '[WARN]: The arg `compiled` should not be True while `unzip` is null, because .pyc files of __pycache__ folder may not work in zip file.'
                )
            if self.lazy_install:
                self._log(
                    '[WARN]: the `unzip` arg has been changed to "*" while `lazy_install` is True.'
                )
                self.unzip = '*'
        if self.cache_path:
            self._cache_path = Path(self.cache_path)
        else:
            self._tmp_dir = tempfile.TemporaryDirectory()
            self._cache_path = Path(self._tmp_dir.name)
        if not self.unzip_path:
            if self.lazy_install:
                self._log(
                    f'[WARN]: the arg `unzip_path` has been changed to `SELF/{self.DEFAULT_UNZIP_CACHE_PATH}` while `lazy_install` is True and `unzip_path` is null.'
                )
                self.unzip_path = f'SELF/{ZipApp.DEFAULT_UNZIP_CACHE_PATH}'
            else:
                self._log(
                    f'[INFO]: the arg `unzip_path` has been changed to `{self.DEFAULT_UNZIP_CACHE_PATH}` by default.'
                )
                self.unzip_path = self.DEFAULT_UNZIP_CACHE_PATH
        self.build_id_name = self.get_build_id_name()
        self._log(
            f'[INFO]: output path is `{self._output_path}`, you can reset it with the arg `output`.'
        )

    def prepare_ensure_pip(self):
        if self.ensure_pip:
            import ensurepip
            ensurepip_dir_path = Path(ensurepip.__file__).parent
            shutil.copytree(str(ensurepip_dir_path.absolute()),
                            self._cache_path / ensurepip_dir_path.name)

    def build(self):
        self._log(
            f'{"=" * 10} Start building `{self._output_path}` with zipapps version <{__version__}> {"=" * 10}'
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
        _kwargs = dict(mode='w', compression=compression)
        if self._is_greater_than_python_37:
            _kwargs['compresslevel'] = compresslevel
        with ZipFile(str(self._output_path), **_kwargs) as zf:
            for f in self._cache_path.glob('**/*'):
                zf.write(f, str(f.relative_to(self._cache_path)))

    def create_archive(self):
        if self._is_greater_than_python_37:
            zipapp.create_archive(source=self._cache_path,
                                  target=str(self._output_path.absolute()),
                                  interpreter=self.interpreter,
                                  compressed=self.compressed)
        elif self.compressed:
            raise RuntimeError('The arg `compressed` only support python3.7+')
        else:
            zipapp.create_archive(source=self._cache_path,
                                  target=str(self._output_path.absolute()),
                                  interpreter=self.interpreter)

    def prepare_entry_point(self):
        # reset unzip_names
        unzip_names = set(self.unzip.split(',')) if self.unzip else set()
        warning_names: typing.Dict[str, dict] = {}
        for path in self._cache_path.iterdir():
            _name_not_included = path.name not in unzip_names
            if path.is_dir():
                pyd_counts = len(list(path.glob('**/*.pyd')))
                so_counts = len(list(path.glob('**/*.so')))
                if (pyd_counts or so_counts) and _name_not_included:
                    # warn which libs need to be unzipped
                    if pyd_counts:
                        warning_names.setdefault(path.name,
                                                 {})['.pyd'] = pyd_counts
                    if so_counts:
                        warning_names.setdefault(path.name,
                                                 {})['.so'] = so_counts
            elif path.is_file() and path.suffix in ('.pyd', '.so'):
                if _name_not_included and path.stem not in unzip_names:
                    warning_names.setdefault(path.name, {})[path.suffix] = 1
        # remove the special keys from unzip_names
        auto_unzip_keys = ZipApp.AUTO_FIX_UNZIP_KEYS & unzip_names
        unzip_names -= auto_unzip_keys
        if warning_names:
            if auto_unzip_keys:
                unzip_names |= warning_names.keys()
            else:
                _fix_unzip_names = ",".join(warning_names.keys())
                msg = f'[WARN]: .pyd/.so files may be imported incorrectly, set `--unzip={_fix_unzip_names}` or `--unzip=AUTO` to fix it. {warning_names}'
                self._log(msg)
        new_unzip = ','.join(unzip_names)
        self.unzip = new_unzip
        if self.unzip:
            self._log(
                f'[INFO]: these names will be unzipped while running: {self.unzip}'
            )
        self.prepare_active_zipapps()

    def prepare_active_zipapps(self):
        output_name = Path(self._output_path).stem
        if not re.match(r'^[0-9a-zA-Z_]+$', output_name):
            raise ValueError(
                'The name of `output` should match regex: ^[0-9a-zA-Z_]+$')
        module, _, function = self.main.partition(':')
        if module:
            module_path = self._cache_path / module
            if module_path.is_file():
                module = module_path.stem
        kwargs = {
            'ts': self.setup_timestamp_file(),
            'shell': self.shell,
            'main_shell': self.main_shell,
            'unzip': self.unzip,
            'output_name': output_name,
            'unzip_path': self.unzip_path,
            'ignore_system_python_path': self.ignore_system_python_path,
            'has_main': bool(self.main),
            'import_main': 'import %s' % module if module else '',
            'run_main': '%s.%s()' % (module, function) if function else '',
            'HANDLE_OTHER_ENVS_FLAG': self.HANDLE_OTHER_ENVS_FLAG,
            'env_paths': self.env_paths,
            'LAZY_PIP_DIR_NAME': self.LAZY_PIP_DIR_NAME,
            'pip_args_repr': repr(self.pip_args),
            'sys_paths': self.sys_paths,
            'python_version_slice': self.python_version_slice,
            'pip_args_md5': self.pip_args_md5,
        }
        code = get_data('zipapps', '_entry_point.py').decode('u8')
        (self._cache_path / '__main__.py').write_text(code.format(**kwargs))
        code = get_data('zipapps', 'ensure_zipapps_template.py').decode('u8')
        (self._cache_path / 'ensure_zipapps.py').write_text(
            code.format(**kwargs))
        code = get_data('zipapps', 'activate_zipapps.py').decode('u8')
        (self._cache_path / 'activate_zipapps.py').write_text(code)
        code += '\n\nactivate()'
        if output_name != 'zipapps':
            (self._cache_path / f'ensure_{output_name}.py').write_text(code)
        (self._cache_path / f'ensure_zipapps_{output_name}.py').write_text(code)

    def setup_timestamp_file(self,):
        ts = str(int(time.time() * 10000000))
        (self._cache_path / ('_zip_time_%s' % ts)).touch()
        return ts

    def prepare_pip(self):
        self.pip_args_md5 = ''
        if self.pip_args:
            if '-t' in self.pip_args or '--target' in self.pip_args:
                raise RuntimeError(
                    '`-t` / `--target` arg can be set with `--cache-path` to rewrite the zipapps cache path.'
                )
            if self.lazy_install:
                # copy files to cache folder
                _temp_pip_path = self._cache_path / self.LAZY_PIP_DIR_NAME
                _temp_pip_path.mkdir(parents=True, exist_ok=True)
                _md5_str = md5(str(self.pip_args).encode('utf-8')).hexdigest()
                # overwrite path args to new path, such as requirements.txt or xxx.whl
                for index, arg in enumerate(self.pip_args):
                    path = Path(arg)
                    if path.is_file():
                        _md5_str += md5(path.read_bytes()).hexdigest()
                        new_path = _temp_pip_path / path.name
                        shutil.copyfile(path, new_path)
                        _r_path = Path(self.LAZY_PIP_DIR_NAME) / path.name
                        self.pip_args[index] = _r_path.as_posix()
                self.pip_args_md5 = md5(_md5_str.encode('utf-8')).hexdigest()
                self._log(
                    f'[INFO]: pip_args_md5 has been generated: {self.pip_args_md5}'
                )
            else:
                self.pip_install()

    def pip_install(self):
        if self.layer_mode:
            _target_dir = self._cache_path.absolute() / self.layer_mode_prefix
            target = str(_target_dir)
        else:
            target = str(self._cache_path.absolute())
        shell_args = [
            sys.executable, '-m', 'pip', 'install', '--target', target
        ] + self.pip_args
        with subprocess.Popen(shell_args) as proc:
            proc.wait()
        self.clean_pip_pycache()

    def clean_pip_pycache(self):
        if self.layer_mode:
            root = self._cache_path / self.layer_mode_prefix
        else:
            root = self._cache_path
        for dist_path in root.glob('*.dist-info'):
            shutil.rmtree(dist_path)
        pycache = root / '__pycache__'
        if pycache.is_dir():
            shutil.rmtree(pycache)

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
                raise RuntimeError('%s is not exist' % include_path.absolute())

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
            return ''
        build_id_str = ''
        if '*' in self.build_id:
            paths = glob(self.build_id)
        else:
            paths = self.build_id.split(',')
        for p in paths:
            try:
                path = Path(p)
                build_id_str += str(path.stat().st_mtime)
            except FileNotFoundError:
                pass
        build_id_str = build_id_str or str(self.build_id)
        md5_id = md5(build_id_str.encode('utf-8')).hexdigest()
        return f'_build_id_{md5_id}'

    @classmethod
    def create_app(cls, *args, **kwargs):
        app = cls(*args, **kwargs)
        return app.build()

    @staticmethod
    def _log(text):
        sys.stderr.write(f'{text}\n')

    def __del__(self):
        if self._tmp_dir:
            self._tmp_dir.cleanup()
            self._log(
                f'[INFO] Temp cache has been cleaned. ({self._tmp_dir!r})')
        if self._build_success:
            self._log(
                f'{"=" * 10} Successfully built `{self._output_path}` {"=" * 10}'
            )
        else:
            self._log(f'{"=" * 10} Build failed {"=" * 10}')


def create_app(*args, **kwargs):
    return ZipApp.create_app(*args, **kwargs)
