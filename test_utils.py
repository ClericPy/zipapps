import atexit
import shutil
import subprocess
import sys
import time
from pathlib import Path

from zipapps.main import create_app


@atexit.register
def _clean_paths():
    for p in ['mock_main.py', 'app.pyz', '_requirements.txt']:
        try:
            Path(p).unlink()
        except Exception:
            pass
    for d in ['mock_package', 'app_unzip_cache']:
        try:
            shutil.rmtree(d)
        except Exception:
            pass


def test_create_app_function():
    # no change args like interpreter, compressed will not test

    # test build_id
    _clean_paths()
    mock_requirement = Path('_requirements.txt')
    mock_requirement.write_text('bottle')
    old_file = create_app(build_id='_requirements.txt',
                          pip_args=['-r', '_requirements.txt'])
    old_size = old_file.stat().st_size
    # test single file
    new_file1 = create_app(build_id='_requirements.txt',
                           pip_args=['-r', '_requirements.txt'])
    assert old_size == new_file1.stat().st_size, 'same build_id error'
    # test glob *
    new_file2 = create_app(build_id='*requirements*',
                           pip_args=['-r', '_requirements.txt'])
    assert old_size == new_file2.stat().st_size, 'same build_id error'
    # test different build_id
    mock_requirement.write_text('bottle<0.12.18')
    new_file2 = create_app(build_id='_requirements.txt',
                           pip_args=['-r', '_requirements.txt'])
    assert old_size != new_file2.stat().st_size, 'different build_id error'

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
        [sys.executable, '-c', 'import main'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # files not be set by includes arg
    assert b'Traceback' in stderr_output, 'test includes failed'
    app_path = create_app(
        includes='./zipapps/_entry_point.py,./zipapps/main.py')
    _, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path), '-c', 'import main'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # files has been copied
    assert stderr_output == b'', 'test includes failed %s' % stderr_output

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

    # test unzip
    app_path = create_app(unzip='bottle', pip_args=['bottle'])
    output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import bottle;print(bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    file_counts = len(list(Path('app_unzip_cache').glob('**/*')))
    assert file_counts == 4, file_counts
    assert b'app_unzip_cache' in output, 'test unzip failed, app_unzip_cache as sys.path should be priority'

    # test unzip *
    app_path = create_app(unzip='*', pip_args=['bottle'])
    output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import bottle;print(bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    file_counts = len(list(Path('app_unzip_cache').glob('**/*')))
    assert file_counts > 4, 'test unzip failed, app_unzip_cache as sys.path should be priority'

    # test psutil, only for win32
    if sys.platform == 'win32':
        mock_main = Path('mock_main.py')
        mock_main.write_text('import psutil;print(psutil.__file__)')
        app_path = create_app(pip_args=['psutil'],
                              main='mock_main',
                              includes='mock_main.py')
        _, error = subprocess.Popen(
            [sys.executable, str(app_path)],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        ).communicate()
        assert b'ModuleNotFoundError' in error, 'no error now?'
        app_path = create_app(unzip='psutil',
                              pip_args=['psutil'],
                              main='mock_main',
                              includes='mock_main.py')
        _, error = subprocess.Popen(
            [sys.executable, str(app_path)],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
        ).communicate()
        assert not error, error

    # test ensure path for venv usage
    create_app(unzip='bottle', pip_args=['bottle'])
    sys.path.insert(0, 'app.pyz')
    import bottle
    import ensure_zipapps

    # using app unzip cache for `import ensure_zipapps`
    assert 'app_unzip_cache' in bottle.__file__

    # test compiled
    app_path = create_app(compiled=True, pip_args=['bottle'])
    output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import bottle;print(bottle.__cached__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # print(output)
    assert b'None' in output
    app_path = create_app(unzip='bottle', compiled=True, pip_args=['bottle'])
    output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import bottle;print(bottle.__cached__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # print(output)
    assert b'.pyc' in output


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
