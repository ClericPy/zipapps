# [zipapps](https://github.com/ClericPy/zipapps) [![PyPI](https://img.shields.io/pypi/v/zipapps?style=plastic)](https://pypi.org/project/zipapps/)[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/clericpy/zipapps/Python%20package?style=plastic)](https://github.com/ClericPy/zipapps/actions?query=workflow%3A%22Python+package%22)![PyPI - Wheel](https://img.shields.io/pypi/wheel/zipapps?style=plastic)![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zipapps?style=plastic)![PyPI - Downloads](https://img.shields.io/pypi/dm/zipapps?style=plastic)![PyPI - License](https://img.shields.io/pypi/l/zipapps?style=plastic)

Package your python code into one zip file, even a virtual environment. Also compatible for win32.

Inspired by [shiv](https://github.com/linkedin/shiv), to publish applications easily. Unlike shiv, this lib will not create cache folders while running apps.


## Requirements

> Only python3.6+

## Install

> pip install zipapps -U

## Usage

> python3 -m zipapps -h

```
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
python3 -m zipapps -c -a package1,package2 -o server.pyz -m package1.server:main -p /usr/bin/python3 -r requirements.txt
./server.pyz

PS: all the unknown args will be used by "pip install".
===========================================================================

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        The name of the output file, defaults to "app.pyz".
  --python INTERPRETER, -p INTERPRETER
                        The name of the Python interpreter to use (default: no shebang line).
  --main MAIN, -m MAIN  The main function of the application. Format like package.module:function.
  --compress, -c        Compress files with the deflate method, defaults to uncompressed.
  --includes INCLUDES, -a INCLUDES
                        The files/folders of given dir path will be copied into cache-path, which can be import from PYTHONPATH). The path string will be splited by ",".
  --cache-path CACHE_PATH
                        The cache path of zipapps to store site-packages and `includes` files, which will be treat as PYTHONPATH. If not set, will create and clean-up automately.
  --shell               Only while `main` is not set, used for shell=True in subprocess.Popen
```
