import zipapps
import sys

zipapps.ZipApp.LOGGING = False


def test_six_1_16():
    app = zipapps.ZipApp(pip_args=['six==1.16.0', '-q'],
                         output='six_16.pyz').build()
    sys.path.insert(0, app.as_posix())
    sys.modules.pop('six', None)
    import six
    print(six.__file__)
    assert 'six_16.pyz' in six.__file__
    app.unlink()


def test_six_1_15():
    app = zipapps.ZipApp(pip_args=['six==1.15.0', '-q'],
                         output='six_15.pyz').build()
    sys.path.insert(0, app.as_posix())
    sys.modules.pop('six', None)
    import six
    print(six.__file__)
    assert 'six_15.pyz' in six.__file__
    app.unlink()


def main():
    test_six_1_16()
    test_six_1_15()


if __name__ == "__main__":
    main()
