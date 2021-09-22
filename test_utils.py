import atexit
import os
import re
import shutil
import subprocess
import sys
from getpass import getuser
from pathlib import Path
from tempfile import gettempdir

from zipapps.main import create_app


@atexit.register
def _clean_paths():
    for p in [
            'mock_main.py', 'app.pyz', 'bottle.pyz', 'bottle_env.pyz',
            'psutil.pyz', '_requirements.txt', 'six.pyz', 'entry_test.py'
    ]:
        try:
            Path(p).unlink()
        except Exception:
            pass
    for d in [
            'mock_package', 'zipapps_cache', 'bottle_env',
            Path.home() / 'app_cache',
            Path('./app_cache'),
            Path(gettempdir()) / 'app_cache',
            Path('./zipapps_cache')
    ]:
        try:
            shutil.rmtree(d)
        except Exception:
            pass


def test_create_app_function():

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
    _clean_paths()
    app_path = create_app(unzip='bottle', pip_args=['bottle'])
    output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import bottle;print(bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    file_counts = len(list(Path('zipapps_cache').glob('**/*')))
    assert file_counts >= 5, file_counts
    assert b'zipapps_cache' in output, 'test unzip failed, zipapps_cache as sys.path should be priority'

    # test unzip with complete path
    _clean_paths()
    app_path = create_app(unzip='ensure_app,bin/bottle.py', pip_args=['bottle'])
    output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import bottle;print(bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    file_counts = len(list(Path('zipapps_cache').glob('**/*')))
    # print(file_counts)
    assert file_counts == 5, 'test unzip failed, zipapps_cache as sys.path should be priority'

    # test unzip with `AUTO_UNZIP` and `*`
    _clean_paths()
    app_path = create_app(unzip='', pip_args=['aiohttp'])
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), '-V'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    aiohttp_unzipped = bool(list(Path('zipapps_cache').glob('**/aiohttp')))
    assert not aiohttp_unzipped, 'test unzip failed, aiohttp should not be unzipped'
    _clean_paths()
    app_path = create_app(unzip='AUTO_UNZIP', pip_args=['aiohttp'])
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), '-V'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    aiohttp_unzipped = bool(list(Path('zipapps_cache').glob('**/aiohttp')))
    assert aiohttp_unzipped, 'test unzip failed, aiohttp should be unzipped'
    _clean_paths()
    # test auto unzip without nonsense folder
    app_path = create_app(unzip='AUTO_UNZIP')
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), '-V'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    no_cache_dir = not Path('zipapps_cache').is_dir()
    assert no_cache_dir, 'test unzip failed, should not unzip anything'
    _clean_paths()
    app_path = create_app(unzip='AUTO', pip_args=['aiohttp'])
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), '-V'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    aiohttp_unzipped = bool(list(Path('zipapps_cache').glob('**/aiohttp')))
    assert aiohttp_unzipped, 'test unzip failed, aiohttp should be unzipped'
    _clean_paths()
    app_path = create_app(unzip='*', pip_args=['aiohttp'])
    output, _ = subprocess.Popen(
        [sys.executable, str(app_path), '-V'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    aiohttp_unzipped = bool(list(Path('zipapps_cache').glob('**/aiohttp')))
    assert aiohttp_unzipped, 'test unzip failed, aiohttp should be unzipped'

    # test psutil, only for win32
    _clean_paths()
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
    _clean_paths()
    create_app(output='bottle_env.pyz', unzip='bottle', pip_args=['bottle'])
    sys.path.insert(0, 'bottle_env.pyz')
    # ! ensure before import for refresh path
    import ensure_bottle_env as _
    import bottle

    # using app unzip cache for `import ensure_zipapps`
    # print(bottle.__file__)
    assert 'zipapps_cache' in bottle.__file__

    # test compiled
    _clean_paths()
    app_path = create_app(unzip='six', compiled=True, pip_args=['six'])
    output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import six;print(six.__cached__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # print(output)
    assert b'.pyc' in output, output

    # test unzip with HOME / SELF / TEMP
    _clean_paths()
    app_path = create_app(unzip='bottle',
                          pip_args=['bottle'],
                          unzip_path='HOME/app_cache')
    output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import bottle;print(bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert getuser() in output.decode()

    app_path = create_app(unzip='bottle',
                          pip_args=['bottle'],
                          unzip_path='SELF/app_cache')
    output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import bottle;print(bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # print(output)
    assert str(Path('./app_cache').absolute()) in output.decode()

    app_path = create_app(unzip='bottle',
                          pip_args=['bottle'],
                          unzip_path='TEMP/app_cache')
    output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import bottle;print(bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert str((Path(gettempdir()) / 'app_cache').absolute()) in output.decode()

    # test os.environ
    app_path = create_app(unzip='bottle',
                          pip_args=['bottle'],
                          unzip_path='TEMP/app_cache')
    os.environ['UNZIP_PATH'] = './bottle_env'
    output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import bottle;print(bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    _output = output.decode()
    assert 'app_cache' not in _output and 'bottle_env' in _output

    # test --zipapps
    _clean_paths()
    create_app(unzip='AUTO', output='psutil.pyz', pip_args=['psutil'])
    create_app(output='six.pyz', pip_args=['six'])
    cmd = '%s six.pyz --zipapps=psutil.pyz -c "import six,psutil;print(six.__file__, psutil.__file__)"' % sys.executable
    stdout_output = subprocess.check_output(args=cmd, shell=True).decode()
    # print(stdout_output)
    assert re.search(r'six.pyz[\\/]six.py', stdout_output) and re.search(
        r'psutil[\\/]psutil[\\/]__init__.py', stdout_output)
    os.environ.pop('UNZIP_PATH')

    # test --zipapps while building
    _clean_paths()
    # test for simple usage
    create_app(pip_args=['six'], output='six.pyz')
    Path('./entry_test.py').write_text('import six;print(six.__file__)')
    output, error = subprocess.Popen(
        [
            sys.executable, '-m', 'zipapps', '--zipapps', 'six.pyz', '-m',
            'entry_test', '-a', 'entry_test.py'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert not output, output
    assert b'Successfully built' in error, error
    output, error = subprocess.Popen(
        [sys.executable, './app.pyz'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert not error
    assert b'six.pyz' in output

    _clean_paths()
    # test for SELF arg
    create_app(pip_args=['six'], output='six.pyz')
    Path('./entry_test.py').write_text('import six;print(six.__file__)')
    _, error = subprocess.Popen(
        [
            sys.executable, '-m', 'zipapps', '--zipapps', 'SELF/six.pyz', '-m',
            'entry_test', '-a', 'entry_test.py'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert b'Successfully built' in error
    output, error = subprocess.Popen(
        [sys.executable, './app.pyz'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert not error
    assert b'six.pyz' in output

    _clean_paths()
    # test for without --zipapps
    create_app(pip_args=['six'], output='six.pyz')
    Path('./entry_test.py').write_text('import six;print(six.__file__)')
    _, error = subprocess.Popen(
        [
            sys.executable, '-m', 'zipapps', '-m', 'entry_test', '-a',
            'entry_test.py'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert b'Successfully built' in error
    output, error = subprocess.Popen(
        [sys.executable, './app.pyz'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert b'six.pyz' not in output

    # test run_path
    _clean_paths()
    create_app(output='app.pyz')
    Path('mock_main.py').write_text('import sys;print(__name__, sys.argv)')
    output = subprocess.check_output('%s app.pyz mock_main.py --test-arg' %
                                     sys.executable,
                                     shell=True).decode()
    # print(output)
    assert '__main__' in output and '--test-arg' in output

    # test lazy pip install
    _clean_paths()
    mock_requirements = Path('_requirements.txt')
    mock_requirements.write_text('six')
    app_path = create_app(lazy_install=True,
                          pip_args=['bottle', '-r', '_requirements.txt'])
    stdout_output, stderr_output = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c',
            'import six,bottle;print(six.__file__, bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # print(stdout_output, stderr_output)
    assert b'Installing collected packages' in stderr_output, stderr_output
    assert stdout_output.count(b'_zipapps_lazy_pip') == 2, stdout_output
    app_path = create_app(lazy_install=True,
                          pip_args=['bottle', '-r', '_requirements.txt'])
    stdout_output, stderr_output = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c',
            'import six,bottle;print(six.__file__, bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # print(stdout_output, stderr_output)
    assert b'Installing collected packages' not in stderr_output, stderr_output

    # test sys_path
    _clean_paths()
    # pip install by given --target
    args = [
        sys.executable, '-m', 'pip', 'install', 'bottle', '-t', './bottle_env'
    ]
    subprocess.Popen(args=args).wait()
    mock_requirement = Path('_requirements.txt')
    mock_requirement.write_text('bottle')
    old_file = create_app(sys_paths='SELF/bottle_env')
    output = subprocess.check_output([
        sys.executable, 'app.pyz', '-c', "import bottle;print(bottle.__file__)"
    ]).decode()
    assert 'bottle_env' in output

    # test layer-mode
    _clean_paths()
    old_file = create_app(includes='setup.py',
                          layer_mode=True,
                          layer_mode_prefix='python3',
                          pip_args=['six'])
    from zipfile import ZipFile
    with ZipFile(old_file) as zf:
        namelist = {'python3/', 'python3/setup.py', 'python3/six.py'}
        assert set(zf.namelist()) == namelist, zf.namelist()


def main():
    """
    test all cases
    """
    test_create_app_function()
    print('=' * 80)
    print('All tests finished.')
    print('=' * 80)


if __name__ == "__main__":
    main()
