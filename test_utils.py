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
    # files
    for p in [
            'mock_main.py', 'app.pyz', 'bottle.pyz', 'bottle_env.pyz',
            'psutil.pyz', '_requirements.txt', 'six.pyz', 'entry_test.py',
            'zipapps_config.json'
    ]:
        try:
            Path(p).unlink()
        except Exception:
            pass
    # folders
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

    # test `--dump-config` and `--load-config`
    _clean_paths()
    output, _ = subprocess.Popen(
        [sys.executable, '-m', 'zipapps', '--dump-config', '-'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert output.startswith(b'{') and output.endswith(b'}'), output
    subprocess.Popen(
        [
            sys.executable, '-m', 'zipapps', '--dump-config',
            'zipapps_config.json', 'six'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).wait()
    assert Path('zipapps_config.json').is_file()
    subprocess.Popen(
        [
            sys.executable, '-m', 'zipapps', '--load-config',
            'zipapps_config.json'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).wait()
    output, _ = subprocess.Popen(
        [sys.executable, 'app.pyz', '-c', 'import six;print(six.__file__)'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    _output = output.decode()
    assert 'app.pyz' in _output

    # test os.environ
    _clean_paths()
    app_path = create_app(unzip='*', unzip_path='app_cache')
    os.environ['CLEAR_ZIPAPPS_CACHE'] = '1'
    os.environ['CLEAR_ZIPAPPS_SELF'] = '1'
    subprocess.Popen(
        [sys.executable, str(app_path), '--activate-zipapps'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).wait()
    os.environ.pop('CLEAR_ZIPAPPS_CACHE')
    os.environ.pop('CLEAR_ZIPAPPS_SELF')
    assert not Path('app_cache').is_dir()
    assert not Path('app.pyz').is_file()
    app_path = create_app(unzip='*', unzip_path='app_cache')
    subprocess.Popen(
        [sys.executable, str(app_path), '--activate-zipapps'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).wait()
    assert Path('app_cache').is_dir()
    assert Path('app.pyz').is_file()
    app_path = create_app(unzip='six',
                          pip_args=['six'],
                          unzip_path='$TEMP/app_cache')
    os.environ['ZIPAPPS_CACHE'] = './bottle_env'
    output, _ = subprocess.Popen(
        [sys.executable,
         str(app_path), '-c', 'import six;print(six.__file__)'],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    _output = output.decode()
    assert 'app_cache' not in _output and 'bottle_env' in _output
    os.environ.pop('ZIPAPPS_CACHE')

    # test unzip with $CWD / $PID
    _clean_paths()
    app_path = create_app(unzip='bottle',
                          pip_args=['bottle'],
                          unzip_path='$CWD/app_cache/$PID')
    proc = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import bottle;print(bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    output, _ = proc.communicate()
    assert '$CWD' not in output.decode()
    assert str(proc.pid) in output.decode()
    assert (Path.cwd() / 'app_cache').is_dir()

    # test clear_zipapps_self
    _clean_paths()
    assert not Path('app.pyz').is_file()
    app_path = create_app(clear_zipapps_self=True)
    assert Path('app.pyz').is_file()
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path), '--activate-zipapps']).communicate()
    assert not Path('app.pyz').is_file()

    # test unzip_exclude
    _clean_paths()
    app_path = create_app(unzip='*', pip_args=['six'], unzip_exclude='')
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path), '--activate-zipapps']).communicate()
    assert Path('./zipapps_cache/app/six.py').is_file()
    _clean_paths()
    app_path = create_app(unzip='*', pip_args=['six'], unzip_exclude='six')
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path), '--activate-zipapps']).communicate()
    assert not Path('./zipapps_cache/app/six.py').is_file()

    # test -czc
    _clean_paths()
    app_path = create_app(clear_zipapps_cache=False, unzip='*')
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path), '-V']).communicate()
    assert Path('./zipapps_cache').is_dir()
    _clean_paths()
    app_path = create_app(clear_zipapps_cache=True, unzip='*')
    stdout_output, stderr_output = subprocess.Popen(
        [sys.executable, str(app_path), '-V']).communicate()
    assert not Path('./zipapps_cache').is_dir()

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
        includes='./zipapps/_entry_point.py.template,./zipapps/main.py')
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

    # test unzip with $HOME / $SELF / $TEMP
    _clean_paths()
    app_path = create_app(unzip='bottle',
                          pip_args=['bottle'],
                          unzip_path='$HOME/app_cache')
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
                          unzip_path='$SELF/app_cache')
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
                          unzip_path='$TEMP/app_cache')
    output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c', 'import bottle;print(bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert str((Path(gettempdir()) / 'app_cache').absolute()) in output.decode()

    # test --zipapps
    _clean_paths()
    create_app(unzip='AUTO', output='psutil.pyz', pip_args=['psutil'])
    create_app(output='six.pyz', pip_args=['six'])
    cmd = '%s six.pyz --zipapps=psutil.pyz -c "import six,psutil;print(six.__file__, psutil.__file__)"' % sys.executable
    stdout_output = subprocess.check_output(args=cmd, shell=True).decode()
    # print(stdout_output)
    assert re.search(r'six.pyz[\\/]six.py', stdout_output) and re.search(
        r'psutil[\\/]psutil[\\/]__init__.py', stdout_output)

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
    # test for $SELF arg
    create_app(pip_args=['six'], output='six.pyz')
    Path('./entry_test.py').write_text('import six;print(six.__file__)')
    _, error = subprocess.Popen(
        [
            sys.executable, '-m', 'zipapps', '--zipapps', '$SELF/six.pyz', '-m',
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
    stdout_output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c',
            'import six,bottle;print(six.__file__, bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    assert b'Collecting six' in stdout_output, stdout_output
    app_path = create_app(lazy_install=True,
                          pip_args=['bottle', '-r', '_requirements.txt'])
    stdout_output, _ = subprocess.Popen(
        [
            sys.executable,
            str(app_path), '-c',
            'import six,bottle;print(six.__file__, bottle.__file__)'
        ],
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ).communicate()
    # print(stdout_output, stderr_output)
    assert b'Collecting six' not in stdout_output, stdout_output

    # test sys_path
    _clean_paths()
    # pip install by given --target
    args = [
        sys.executable, '-m', 'pip', 'install', 'bottle', '-t', './bottle_env'
    ]
    subprocess.Popen(args=args).wait()
    mock_requirement = Path('_requirements.txt')
    mock_requirement.write_text('bottle')
    old_file = create_app(sys_paths='$SELF/bottle_env')
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

    if os.name != 'nt':
        # posix only
        # test --chmod
        _clean_paths()
        app_path = create_app(unzip='*', pip_args=['six'], lazy_install=True)
        subprocess.Popen([sys.executable,
                          str(app_path), '--activate-zipapps']).wait()
        assert Path('app.pyz').stat().st_mode != 33279
        for _path in Path('zipapps_cache/app').rglob('*'):
            if _path.name == 'six.py':
                assert _path.stat().st_mode != 33279, _path.stat().st_mode
                break

        _clean_paths()
        app_path = create_app(unzip='*',
                              pip_args=['six'],
                              lazy_install=True,
                              chmod='777')
        subprocess.Popen([sys.executable,
                          str(app_path), '--activate-zipapps']).wait()
        assert Path('app.pyz').stat().st_mode == 33279
        for _path in Path('zipapps_cache/app').rglob('*'):
            if _path.name == 'six.py':
                assert _path.stat().st_mode == 33279, _path.stat().st_mode
                break


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
