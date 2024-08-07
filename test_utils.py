import atexit
import os
import re
import shutil
import subprocess
import sys
import zipimport
from getpass import getuser
from pathlib import Path
from tempfile import gettempdir

from zipapps.main import create_app


@atexit.register
def _clean_paths():
    # files
    for p in [
        "mock_main.py",
        "app.pyz",
        "bottle.pyz",
        "bottle_env.pyz",
        "orjson.pyz",
        "_requirements.txt",
        "six.pyz",
        "entry_test.py",
        "zipapps_config.json",
        "mock_dir",
    ]:
        try:
            path = Path(p)
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path.as_posix())
        except Exception:
            pass
    # folders
    for d in [
        "mock_package",
        "zipapps_cache",
        "bottle_env",
        Path.home() / "app_cache",
        Path("./app_cache"),
        Path(gettempdir()) / "app_cache",
        Path("./zipapps_cache"),
    ]:
        try:
            shutil.rmtree(d)
        except Exception:
            pass


def test_quiet_mode():
    # test -qqqq quiet mode
    _clean_paths()
    output = subprocess.check_output([sys.executable, "-m", "zipapps", "six", "-qqqq"])
    assert not output, output


def test_freeze():
    # test --freeze-reqs
    _clean_paths()
    output = subprocess.check_output(
        [sys.executable, "-m", "zipapps", "--freeze-reqs", "-", "six==1.15.0"]
    )
    assert b"six==1.15.0" in output.strip(), output


def test_dump_load_config():
    # test `--dump-config` and `--load-config`
    _clean_paths()
    output, _ = subprocess.Popen(
        [sys.executable, "-m", "zipapps", "--dump-config", "-"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    output = output.strip()
    assert output.startswith(b"{") and output.endswith(b"}"), output
    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "zipapps",
            "--dump-config",
            "zipapps_config.json",
            "six",
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).wait()
    assert Path("zipapps_config.json").is_file()
    subprocess.Popen(
        [sys.executable, "-m", "zipapps", "--load-config", "zipapps_config.json"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).wait()
    output, _ = subprocess.Popen(
        [sys.executable, "app.pyz", "-c", "import six;print(six.__file__)"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    _output = output.decode()
    assert "app.pyz" in _output, output


def test_environ():
    # test os.environ
    _clean_paths()
    app_path = create_app(unzip="*", unzip_path="app_cache")
    os.environ["CLEAR_ZIPAPPS_CACHE"] = "1"
    os.environ["CLEAR_ZIPAPPS_SELF"] = "1"
    subprocess.Popen(
        [sys.executable, str(app_path), "--activate-zipapps"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).wait()
    os.environ.pop("CLEAR_ZIPAPPS_CACHE")
    os.environ.pop("CLEAR_ZIPAPPS_SELF")
    assert not Path("app_cache").is_dir()
    assert not Path("app.pyz").is_file()
    app_path = create_app(unzip="*", unzip_path="app_cache")
    subprocess.Popen(
        [sys.executable, str(app_path), "--activate-zipapps"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).wait()
    assert Path("app_cache").is_dir()
    assert Path("app.pyz").is_file()
    app_path = create_app(unzip="six", pip_args=["six"], unzip_path="$TEMP/app_cache")
    os.environ["ZIPAPPS_CACHE"] = "./bottle_env"
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), "-c", "import six;print(six.__file__)"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    _output = output.decode()
    assert "app_cache" not in _output and "bottle_env" in _output
    os.environ.pop("ZIPAPPS_CACHE")


def test_unzip_with_cwd_pid():
    # test unzip with $CWD / $PID
    _clean_paths()
    app_path = create_app(
        unzip="bottle", pip_args=["bottle"], unzip_path="$CWD/app_cache/$PID"
    )
    proc = subprocess.Popen(
        [sys.executable, str(app_path), "-c", "import bottle;print(bottle.__file__)"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    output, _ = proc.communicate()
    assert "$CWD" not in output.decode()
    assert str(proc.pid) in output.decode()
    assert (Path.cwd() / "app_cache").is_dir()


def test_clear_zipapps_self():
    # test clear_zipapps_self
    _clean_paths()
    assert not Path("app.pyz").is_file()
    app_path = create_app(clear_zipapps_self=True)
    assert Path("app.pyz").is_file()
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path), "--activate-zipapps"]
    ).communicate()
    assert not Path("app.pyz").is_file()


def test_unzip_exclude():
    # test unzip_exclude
    _clean_paths()
    app_path = create_app(unzip="*", pip_args=["six"], unzip_exclude="")
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path), "--activate-zipapps"]
    ).communicate()
    assert Path("./zipapps_cache/app/six.py").is_file()
    _clean_paths()
    app_path = create_app(unzip="*", pip_args=["six"], unzip_exclude="six")
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path), "--activate-zipapps"]
    ).communicate()
    assert not Path("./zipapps_cache/app/six.py").is_file()


def test_clear_zip_cache():
    # test -czc
    _clean_paths()
    app_path = create_app(clear_zipapps_cache=False, unzip="*")
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path), "-V"]
    ).communicate()
    assert Path("./zipapps_cache").is_dir()
    _clean_paths()
    app_path = create_app(clear_zipapps_cache=True, unzip="*")
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path), "-V"]
    ).communicate()
    assert not Path("./zipapps_cache").is_dir()


def test_build_id_and_single_file():
    # test build_id
    _clean_paths()
    mock_requirement = Path("_requirements.txt")
    mock_requirement.write_text("bottle")
    old_file = create_app(
        build_id="_requirements.txt", pip_args=["-r", "_requirements.txt"]
    )
    old_size = old_file.stat().st_size
    # test single file
    new_file1 = create_app(
        build_id="_requirements.txt", pip_args=["-r", "_requirements.txt"]
    )
    assert old_size == new_file1.stat().st_size, "same build_id error"
    # test glob *
    new_file2 = create_app(
        build_id="*requirements*", pip_args=["-r", "_requirements.txt"]
    )
    assert old_size == new_file2.stat().st_size, "same build_id error"
    # test different build_id
    mock_requirement.write_text("bottle<0.12.18")
    new_file2 = create_app(
        build_id="_requirements.txt", pip_args=["-r", "_requirements.txt"]
    )
    assert old_size != new_file2.stat().st_size, "different build_id error"


def test_main_source_code():
    # test main: source code
    _clean_paths()
    subprocess.check_output(
        [
            sys.executable,
            "-m",
            "zipapps",
            "-m",
            "import six;print(six.__version__)",
            "six==1.15.0",
        ]
    )
    output = subprocess.check_output([sys.executable, "app.pyz"])
    assert b"1.15.0" == output.strip(), output


def test_main_module():
    # test main module+function
    _clean_paths()
    mock_main = Path("mock_main.py")
    mock_main.touch()
    mock_main.write_text("print(1)")
    app_path = create_app(includes="mock_main.py", main="mock_main:main")
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path)],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert stdout_output.strip() == b"1", "test main failed"
    # test package entry point
    mock_package = Path("mock_package")
    mock_package.mkdir()
    mock_main = mock_package / "mock_main.py"
    mock_main.touch()
    mock_main.write_text("print(1)")
    app_path = create_app(includes="mock_package", main="mock_package.mock_main:main")
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path)],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert stdout_output.strip() == b"1", "test main failed"
    # test package entry point with __main__
    mock_package = Path("mock_package")
    mock_main = mock_package / "__main__.py"
    mock_main.touch()
    mock_main.write_text("def main():print(1)")
    app_path = create_app(includes="mock_package", main="mock_package.__main__:main")
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path)],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert stdout_output.strip() == b"1", "test main failed"


def test_includes():
    # test includes
    _clean_paths()
    app_path = create_app(includes="")
    _, stderr_output = subprocess.Popen(
        [sys.executable, "-c", "import main"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # files not be set by includes arg
    assert b"Traceback" in stderr_output, "test includes failed"
    app_path = create_app(
        includes="./zipapps/entry_point.py.template,./zipapps/main.py"
    )
    _, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path), "-c", "import main"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # files has been copied
    assert stderr_output == b"", "test includes failed %s" % stderr_output


def test_pip_args():
    # test pip_args
    _clean_paths()
    stdout, _ = subprocess.Popen(
        [sys.executable, "-c", "import bottle;print(bottle.__file__)"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert b'app.pyz' not in stdout, "test pip_args failed %s" % stdout
    app_path = create_app(pip_args=["bottle"])
    stdout, _ = subprocess.Popen(
        [sys.executable, str(app_path), "-c", "import bottle;print(bottle.__file__)"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert b'app.pyz' in stdout, "test pip_args failed %s" % stdout


def test_cache_path():
    # test cache_path
    _clean_paths()
    mock_dir = Path("mock_package")
    mock_dir.mkdir()
    create_app(cache_path=mock_dir)
    assert mock_dir.is_dir(), "test cache_path failed"


def test_unzip():
    # test unzip
    _clean_paths()
    app_path = create_app(unzip="bottle", pip_args=["bottle"])
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), "-c", "import bottle;print(bottle.__file__)"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    file_counts = len(list(Path("zipapps_cache").glob("**/*")))
    assert file_counts >= 5, file_counts
    assert (
        b"zipapps_cache" in output
    ), "test unzip failed, zipapps_cache as sys.path should be priority"


def test_unzip_complete_path():
    # test unzip with complete path
    _clean_paths()
    app_path = create_app(unzip="ensure_app,bin/bottle.py", pip_args=["bottle"])
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), "-c", "import bottle;print(bottle.__file__)"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    file_counts = len(list(Path("zipapps_cache").glob("**/*")))
    # print(file_counts)
    assert (
        file_counts == 5
    ), "test unzip failed, zipapps_cache as sys.path should be priority"


def test_unzip_with_auto_unzip():
    # test unzip with `AUTO_UNZIP` and `*`
    _clean_paths()
    app_path = create_app(unzip="", pip_args=["orjson"])
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), "-V"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    orjson_unzipped = bool(list(Path("zipapps_cache").glob("**/orjson")))
    assert not orjson_unzipped, "test unzip failed, orjson should not be unzipped"
    _clean_paths()
    app_path = create_app(unzip="AUTO_UNZIP", pip_args=["orjson"])
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), "-V"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    orjson_unzipped = bool(list(Path("zipapps_cache").glob("**/orjson")))
    assert orjson_unzipped, "test unzip failed, orjson should be unzipped"
    _clean_paths()
    # test auto unzip without nonsense folder
    app_path = create_app(unzip="AUTO_UNZIP")
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), "-V"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    no_cache_dir = not Path("zipapps_cache").is_dir()
    assert no_cache_dir, "test unzip failed, should not unzip anything"
    _clean_paths()
    app_path = create_app(unzip="AUTO", pip_args=["orjson"])
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), "-V"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    orjson_unzipped = bool(list(Path("zipapps_cache").glob("**/orjson")))
    assert orjson_unzipped, "test unzip failed, orjson should be unzipped"
    _clean_paths()
    app_path = create_app(unzip="*", pip_args=["orjson"])
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), "-V"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    orjson_unzipped = bool(list(Path("zipapps_cache").glob("**/orjson")))
    assert orjson_unzipped, "test unzip failed, orjson should be unzipped"


def test_env_usage():
    # test ensure path for venv usage
    _clean_paths()
    create_app(output="bottle_env.pyz", unzip="bottle", pip_args=["bottle"])
    # activate sys.path and unzip cache
    zipimport.zipimporter("bottle_env.pyz").load_module("ensure_zipapps")
    import bottle

    # using app unzip cache for `import ensure_zipapps`
    # print(bottle.__file__)
    assert "zipapps_cache" in bottle.__file__


def test_compiled():
    # test compiled
    _clean_paths()
    app_path = create_app(unzip="six", compiled=True, pip_args=["six"])
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), "-c", "import six;print(six.__cached__)"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # print(output)
    assert b".pyc" in output, output


def test_variable_home_self_temp():
    # test unzip with $HOME / $SELF / $TEMP
    _clean_paths()
    app_path = create_app(
        unzip="bottle", pip_args=["bottle"], unzip_path="$HOME/app_cache"
    )
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), "-c", "import bottle;print(bottle.__file__)"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert getuser() in output.decode()

    app_path = create_app(
        unzip="bottle", pip_args=["bottle"], unzip_path="$SELF/app_cache"
    )
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), "-c", "import bottle;print(bottle.__file__)"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # print(output)
    assert str(Path("./app_cache").absolute()) in output.decode()

    app_path = create_app(
        unzip="bottle", pip_args=["bottle"], unzip_path="$TEMP/app_cache"
    )
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), "-c", "import bottle;print(bottle.__file__)"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert str((Path(gettempdir()) / "app_cache").absolute()) in output.decode()


def test_runtime_zipapps_arg():
    # test --zipapps
    _clean_paths()
    create_app(unzip="AUTO", output="orjson.pyz", pip_args=["orjson"])
    create_app(output="six.pyz", pip_args=["six"])
    cmd = (
        '%s six.pyz --zipapps=orjson.pyz -c "import six,orjson;print(six.__file__, orjson.__file__)"'
        % sys.executable
    )
    stdout_output = subprocess.check_output(args=cmd, shell=True).decode()
    # print(stdout_output)
    assert re.search(r"six.pyz[\\/]six.py", stdout_output) and re.search(
        r"orjson[\\/]orjson[\\/]__init__.py", stdout_output
    )


def test_build_zipapps_arg():
    # test --zipapps while building
    _clean_paths()
    # test for simple usage
    create_app(pip_args=["six"], output="six.pyz")
    Path("./entry_test.py").write_text("import six;print(six.__file__)")
    output, error = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "zipapps",
            "--zipapps",
            "six.pyz",
            "-m",
            "entry_test",
            "-a",
            "entry_test.py",
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert not output, output
    assert b"Successfully built" in error, error
    output, error = subprocess.Popen(
        [sys.executable, "./app.pyz"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert not error
    assert b"six.pyz" in output

    _clean_paths()
    # test for $SELF arg
    create_app(pip_args=["six"], output="six.pyz")
    Path("./entry_test.py").write_text("import six;print(six.__file__)")
    _, error = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "zipapps",
            "--zipapps",
            "$SELF/six.pyz",
            "-m",
            "entry_test",
            "-a",
            "entry_test.py",
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert b"Successfully built" in error
    output, error = subprocess.Popen(
        [sys.executable, "./app.pyz"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert not error
    assert b"six.pyz" in output

    _clean_paths()
    # test for without --zipapps
    create_app(pip_args=["six"], output="six.pyz")
    Path("./entry_test.py").write_text("import six;print(six.__file__)")
    _, error = subprocess.Popen(
        [sys.executable, "-m", "zipapps", "-m", "entry_test", "-a", "entry_test.py"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert b"Successfully built" in error
    output, error = subprocess.Popen(
        [sys.executable, "./app.pyz"],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert b"six.pyz" not in output


def test_run_path():
    # test run_path
    _clean_paths()
    create_app(output="app.pyz")
    Path("mock_main.py").write_text("import sys;print(__name__, sys.argv)")
    output = subprocess.check_output(
        "%s app.pyz mock_main.py --test-arg" % sys.executable, shell=True
    ).decode()
    # print(output)
    assert "__main__" in output and "--test-arg" in output


def test_lazy_install():
    # test lazy pip install
    _clean_paths()
    mock_requirements = Path("_requirements.txt")
    mock_requirements.write_text("six")
    app_path = create_app(
        lazy_install=True, pip_args=["bottle", "-r", "_requirements.txt"]
    )
    stdout_output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path),
            "-c",
            "import six,bottle;print(six.__file__, bottle.__file__)",
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert b"Collecting six" in stdout_output, stdout_output
    app_path = create_app(
        lazy_install=True, pip_args=["bottle", "-r", "_requirements.txt"]
    )
    stdout_output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path),
            "-c",
            "import six,bottle;print(six.__file__, bottle.__file__)",
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # print(stdout_output, stderr_output)
    assert b"Collecting six" not in stdout_output, stdout_output


def test_sys_paths():
    # test sys_paths
    _clean_paths()
    # pip install by given --target
    args = [sys.executable, "-m", "pip", "install", "bottle", "-t", "./bottle_env"]
    subprocess.Popen(args=args).wait()
    create_app(sys_paths="$SELF/bottle_env")
    output = subprocess.check_output(
        [sys.executable, "app.pyz", "-c", "import bottle;print(bottle.__file__)"]
    ).decode()
    assert "bottle_env" in output


def test_layer_mode():
    # test layer-mode
    _clean_paths()
    old_file = create_app(
        includes="setup.py",
        layer_mode=True,
        layer_mode_prefix="python3",
        pip_args=["six"],
    )
    from zipfile import ZipFile

    with ZipFile(old_file) as zf:
        namelist = {"python3/", "python3/setup.py", "python3/six.py"}
        assert set(zf.namelist()) == namelist, zf.namelist()


def test_chmod():
    if os.name != "nt":
        # posix only
        # test --chmod
        _clean_paths()
        app_path = create_app(unzip="*", pip_args=["six"], lazy_install=True)
        subprocess.Popen([sys.executable, str(app_path), "--activate-zipapps"]).wait()
        assert Path("app.pyz").stat().st_mode != 33279
        for _path in Path("zipapps_cache/app").rglob("*"):
            if _path.name == "six.py":
                assert _path.stat().st_mode != 33279, _path.stat().st_mode
                break

        _clean_paths()
        app_path = create_app(
            unzip="*", pip_args=["six"], lazy_install=True, chmod="777"
        )
        subprocess.Popen([sys.executable, str(app_path), "--activate-zipapps"]).wait()
        assert Path("app.pyz").stat().st_mode == 33279
        for _path in Path("zipapps_cache/app").rglob("*"):
            if _path.name == "six.py":
                assert _path.stat().st_mode == 33279, _path.stat().st_mode
                break


def test_delete_useless():
    # test layer-mode
    _clean_paths()
    from zipfile import ZipFile

    # test cmd mode, do not delete dist-info dir
    subprocess.Popen(
        [sys.executable, "-m", "zipapps", "--rm-patterns", "__pycache__", "six"],
    ).wait()
    with ZipFile("app.pyz") as zf:
        namelist = zf.namelist()
        assert "__pycache__" not in str(namelist), namelist
        assert "dist-info" in str(namelist), namelist

    mock_dir = Path("mock_dir/mock_dir/mock_dir/mock_dir/mock_dir")
    mock_dir.mkdir(parents=True, exist_ok=True)
    (mock_dir / "mock_file.py").touch()

    # test rm glob with default patterns
    old_file = create_app(
        includes="mock_dir", pip_args=["six"], rm_patterns="*.dist-info,__pycache__"
    )
    with ZipFile(old_file) as zf:
        namelist = zf.namelist()
        assert ".dist-info" not in str(namelist), namelist
        assert "mock_file.py" in str(namelist), namelist

    # test rm rglob with **/mock_file.py
    old_file = create_app(
        includes="mock_dir", pip_args=["six"], rm_patterns="**/mock_file.py"
    )
    with ZipFile(old_file) as zf:
        namelist = zf.namelist()
        assert "mock_file.py" not in str(namelist), namelist


def test_pip_install_target():
    import time

    from zipapps import pip_install_target

    _clean_paths()
    # test without "insert sys.path"
    start_time = time.time()
    assert pip_install_target(
        "./mock_dir", ["six", "--no-cache-dir"], force=False, sys_path=None
    )
    assert time.time() - start_time > 0.1
    try:
        sys.modules.pop("six", None)
        import six

        assert "mock_dir" not in six.__file__
    except (ImportError, FileNotFoundError):
        pass
    # hit md5 cache, force=False, sys_path ignored
    start_time = time.time()
    assert not pip_install_target(
        "./mock_dir", ["six", "--no-cache-dir"], force=False, sys_path=0
    )
    assert time.time() - start_time < 0.1
    try:
        sys.modules.pop("six", None)
        import six

        assert "mock_dir" not in six.__file__
    except (ImportError, FileNotFoundError):
        pass
    # test force=True, sys_path=0 worked
    start_time = time.time()
    assert pip_install_target(
        "./mock_dir", ["six", "--no-cache-dir"], force=True, sys_path=0
    )
    assert time.time() - start_time > 0.1
    sys.modules.pop("six", None)
    import six

    assert "mock_dir" in six.__file__


def main():
    """
    test all cases
    """
    import inspect

    count = 0
    items = list(globals().items())
    total = len(items)
    name_list = ""
    for name, func in items:
        if name_list and name not in name_list:
            continue
        if name.startswith("test_") and inspect.isfunction(func):
            count += 1
            print("=" * 80)
            print(count, "/", total, "start testing:", name, flush=True)
            func()
            print("=" * 80)
            # quit('test one')
    print("=" * 80)
    print("All tests finished.")
    print("=" * 80)


if __name__ == "__main__":
    main()
