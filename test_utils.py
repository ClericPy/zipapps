import subprocess
import sys
from zipapps import create_app


def test_create_app_function():
    # test pip_args
    _, output = subprocess.Popen([sys.executable, '-c', 'import bottle'],
                                 stderr=subprocess.PIPE).communicate()
    assert b'No module named' in output, 'check init failed, bottle should not be installed'
    app_path = create_app(pip_args=['bottle'])
    _, output = subprocess.Popen(
        [sys.executable, app_path, '-c', 'import bottle'],
        stderr=subprocess.PIPE).communicate()
    assert b'No module named' not in output, 'test pip_args failed'
    app_path.unlink()


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
