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
usage:
===========================================================================
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
> python3 -m zipapps -c -a package1,package2 -o server.pyz -m package1.server:main -p /usr/bin/python3 -r requirements.txt
> ./server.pyz

3.2 unzip C-libs to cache folder for zipimport do not support .so .pyd files.
    bad
        > python3 -m zipapps -c lxml
        > python3 app.pyz -c "import lxml.html;print(lxml.html.__file__)"
    good
        > python3 -m zipapps -c -u lxml lxml
        > python3 app.pyz -c "import lxml.html;print(lxml.html.__file__)"

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
  --cache-path CACHE_PATH, -cp CACHE_PATH
                        The cache path of zipapps to store site-packages and `includes` files, which will be treat as PYTHONPATH. If not set, will create and clean-up automately.
  --unzip UNZIP, -u UNZIP
                        The names which need to be unzip while running, name without ext. such as .so/.pyd files(which can not be loaded by zipimport), or packages with operations of static files. If unzip is *, will unzip all files and folders.
  --unzip-path UNZIP_PATH, -up UNZIP_PATH
                        The names which need to be unzip while running, name without ext. such as .so/.pyd files(which can not be loaded by zipimport), or packages with operations of static files. Defaults to $(appname)_unzip_cache
  --shell, -s           Only while `main` is not set, used for shell=True in subprocess.Popen
  --strict-python-path, -spp
                        Ignore global PYTHONPATH, only use app_unzip_cache and app.pyz.
```


## FAQ

1. How to zip apps with C-lib requirements for `zipimport` ingore `.pyd`, `.so` files?
   1. as https://docs.python.org/3/library/zipimport.html
   2. we can unzip those packages in temp dirs with `-u` args
   3. > python3 -m zipapps -c -u selectolax selectolax
   4. > python3 app.pyz xxx.py
2. How to avoid  unlimited unzip cachefolder size growth?
   1. There is a null file named like `zip-time` in zip files and unzip folders
   2. The same `zip-time` cache with same name will not unzip again.
3. `PYTHONPATH` between zipapps's zip file and global python environment?
   1. If you set `-spp` for strict `PYTHONPATH`, you will not use the global `PYTHONPATH`.
   2. else you will use global libs as a second choice.
4. Where to Use it?
   1. Hadoop-Streaming's mapper & reducer.
   2. Simple deployment for different server with Jenkins(or other CI/CD tools).
   3. Distribute zipapp with embedded python.
   4. Other usages need to be found, and enjoy yourself.
