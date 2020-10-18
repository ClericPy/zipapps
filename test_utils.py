import subprocess
import sys
from zipapps.main import create_app, DEFAULT_CACHE_PATH
from pathlib import Path
import shutil
import atexit


@atexit.register
def _clean_paths():
    for p in ['mock_main.py', 'app.pyz']:
        try:
            Path(p).unlink()
        except Exception:
            pass
    for d in ['mock_package', DEFAULT_CACHE_PATH]:
        try:
            shutil.rmtree(d)
        except Exception:
            pass


def test_create_app_function():
    # no change args like interpreter, compressed will not test

    # test main
    _clean_paths()
    mock_main = Path('mock_main.py')
    mock_main.touch()
    mock_main.write_text('print(1)')
    app_path = create_app(includes='mock_main.py', main='mock_main:main')
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path)],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert stdout_output.strip() == b'1', 'test main failed'
    # test package entry point
    mock_package = Path('mock_package')
    mock_package.mkdir()
    mock_main = mock_package / 'mock_main.py'
    mock_main.touch()
    mock_main.write_text('print(1)')
    app_path = create_app(includes='mock_package',
                          main='mock_package.mock_main:main')
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path)],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert stdout_output.strip() == b'1', 'test main failed'
    # test package entry point with __main__
    mock_package = Path('mock_package')
    mock_main = mock_package / '__main__.py'
    mock_main.touch()
    mock_main.write_text('def main():print(1)')
    app_path = create_app(includes='mock_package',
                          main='mock_package.__main__:main')
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path)],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert stdout_output.strip() == b'1', 'test main failed'

    # test includes
    _clean_paths()
    app_path = create_app(includes='')
    _, stderr_output = subprocess.Popen(
        [sys.executable, '-c', 'import _entry_point;import _entry_point_shell'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # files not be set by includes arg
    assert b'Traceback' in stderr_output, 'test includes failed'
    app_path = create_app(
        includes='./zipapps/_entry_point.py,./zipapps/_entry_point_shell.py')
    _, stderr_output = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import _entry_point;import _entry_point_shell'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # files has been copied
    assert stderr_output == b'', 'test includes failed'

    # test pip_args
    _clean_paths()
    _, stderr_output = subprocess.Popen([sys.executable, '-c', 'import bottle'],
                                        stderr=subprocess.PIPE,
                                        stdout=subprocess.PIPE).communicate()
    assert b'No module named' in stderr_output, 'check init failed, bottle should not be installed'
    app_path = create_app(pip_args=['bottle'])
    _, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path), '-c', 'import bottle'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE).communicate()
    assert stderr_output == b'', 'test pip_args failed'

    # test cache_path
    _clean_paths()
    mock_dir = Path('mock_package')
    mock_dir.mkdir()
    app_path = create_app(cache_path=mock_dir)
    assert mock_dir.is_dir(), 'test cache_path failed'
    # test auto rm default cache_path
    app_path = create_app(cache_path=DEFAULT_CACHE_PATH)
    assert not Path(
        DEFAULT_CACHE_PATH).is_dir(), 'test auto rm default cache_path failed'


def test_create_app_command_line():
    """
    TODO
    """
    pass


def main():
    """
    test all cases
    """
    test_create_app_function()


if __name__ == "__main__":
    main()
