# [zipapps](https://github.com/ClericPy/zipapps)
[![PyPI](https://img.shields.io/pypi/v/zipapps?style=plastic)](https://pypi.org/project/zipapps/)[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/clericpy/zipapps/Python%20package?style=plastic)](https://github.com/ClericPy/zipapps/actions?query=workflow%3A%22Python+package%22)![PyPI - Wheel](https://img.shields.io/pypi/wheel/zipapps?style=plastic)![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zipapps?style=plastic)![PyPI - Downloads](https://img.shields.io/pypi/dm/zipapps?style=plastic)![PyPI - License](https://img.shields.io/pypi/l/zipapps?style=plastic)

Package your code with requirements into a standalone zip file(like a `jar`), even you can use it like a zipped virtual environment.

Depends on [PEP441](https://www.python.org/dev/peps/pep-0441/), which means it is also compatible for win32.

Inspired by [shiv](https://github.com/linkedin/shiv), to publish applications easily. Unlike shiv, this lib will not always create new cache folders while running.


## Features
- [x] Zip pure python code without cache folder while running.
  - pure python code will not unzip anything by default.
- [x] Zip files/folders by your choice, and unzip which you want.
  - files/libs/folders will be unzip to `-up`/`--unzip-path`, default is `./%s_unzip_cache` while running.
  - `unzip_path` could use the given variable `$HOME` / `$TEMP` / `$SELF`, for example
    - *$HOME/cache* => *~/cache* folder
    - *$TEMP/cache* => */tmp/cache* in linux
      - or *C:\Users\user\AppData\Local\Temp\cache* in win32
    - *$SELF/cache* => *app.pyz/../cache*
      - *$SELF* equals to the parent folder of **pyz** file
  - or you can **reset a new path with environment variable** `UNZIP_PATH`
    - have a try:
      - linux: `python3 -m zipapps -u bottle -o bottle_env.pyz bottle&&export UNZIP_PATH=./tmp&&python3 bottle_env.pyz -c "import bottle;print('here is bottle unzip position:', bottle.__file__)"`
      - win: `python3 -m zipapps -u bottle -o bottle_env.pyz bottle&&set UNZIP_PATH=./tmp&&python3 bottle_env.pyz -c "import bottle;print('here is bottle unzip position:', bottle.__file__)"`
- [x] Zip the dynamic modules (.pyd, .so) which [`zipimport`](https://docs.python.org/3/library/zipimport.html) not support.
  - package with `-u` for these libs.
- [x] Reuse the unzip cache folder for the same zip timestamp. 
  - `zip-timestamp` will play as a `build_id`
- [x] Use like a `venv` or interpreter with `python3 ./env.pyz script.py`, script.py will enjoy the PYTHONPATH of env.pyz.
  - package without `-m` arg, then run codes in `Popen`.
- [x] Fix `psutil` ImportError of DLL loading.
  - package with `-ss` to use `Popen` instead of import directly.
- [x] Support import `pyz` as venv zip file.
  - activate **auto-unzip** by `import ensure_zipapps` after `sys.path.append("app.pyz")`
    - or active with accurate import `import ensure_zipapps_bottle_env` while activating multiple environments
    - or run `python3 ./app.pyz script.py` directly.
  - view the example below for more infomation.
- [x] Support compile to `pyc` for better performance.
  - activate **compile** by `--compile` or `-cc`.
  - but `__pycache__` folder in zip file will not work,
  - so you can unzip them by `--unzip=xxx`,
  - to check whether `pyc` worked by `import bottle;print(bottle.__cached__)`
- [x] Support `build_id` to skip duplicate builds.
  - using like `python3 -m zipapps -b requirements.txt -r requirements.txt`
  - `python3 -m zipapps --build-id=a.py,b.py -r requirements.txt`
  - `python3 -m zipapps --build-id=./*.py -r requirements.txt`
  - `python3 -m zipapps --build-id=efdd0a5584169cdf791 -r requirements.txt`
  - `python3 -m zipapps --build-id=version1.0 -r requirements.txt`


## Requirements

> Only python3.6+, without any requirements.

## Install

> pip install zipapps -U

## Usage

### Normal usage

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
  --version             show program's version number and exit
  --output OUTPUT, -o OUTPUT
                        The name of the output file, defaults to "app.pyz".
  --python INTERPRETER, -p INTERPRETER
                        The name of the Python interpreter to use (default: no shebang line).
  --main MAIN, -m MAIN  The main function of the application. Format like package.module:function.
  --compress, -c        Compress files with the deflate method, defaults to uncompressed.
  --includes INCLUDES, -a INCLUDES
                        The files/folders of given dir path will be copied into cache-path, which can be import from PYTHONPATH). The path string will be splited by ",".
  --cache-path CACHE_PATH, --source-dir CACHE_PATH, -cp CACHE_PATH
                        The cache path of zipapps to store site-packages and `includes` files, which will be treat as PYTHONPATH. If not set, will create and clean-up automately.
  --unzip UNZIP, -u UNZIP
                        The names which need to be unzip while running, name without ext. such as .so/.pyd files(which can not be loaded by zipimport), or packages with operations of
                        static files. If unzip is *, will unzip all files and folders.
  --unzip-path UNZIP_PATH, -up UNZIP_PATH
                        The names which need to be unzip while running, name without ext. such as .so/.pyd files(which can not be loaded by zipimport), or packages with operations of
                        static files. Defaults to $(appname)_unzip_cache.
  --shell, -s           Only while `main` is not set, used for shell=True in subprocess.Popen.
  --main-shell, -ss     Only for `main` is not null, call `main` with subprocess.Popen: `python -c "import a.b;a.b.c()"`. This is used for `psutil` ImportError of DLL load.
  --strict-python-path, -spp
                        Ignore global PYTHONPATH, only use app_unzip_cache and app.pyz.
  -cc, --pyc, --compile, --compiled
                        Compile .py to .pyc for fast import, but zipapp does not work unless you unzip it.
  -b BUILD_ID, --build-id BUILD_ID
                        a string to skip duplicate builds, it can be the paths of files/folders which splited by ",", then the modify time will be used as build_id. If build_id contains
                        `*`, will use `glob` function to get paths. For example, you can set requirements.txt as your build_id by `python3 -m zipapps -b requirements.txt -r
                        requirements.txt` when you use pyz as venv.
```

### Using as the venv zip file

> As you see, `import ensure_zipapps_bottle_env` only works for packaging with a non-null `unzip` arg.
> 
> If you don't need to **unzip** any files/folders, `sys.path.append('app.pyz')` is enough.

WARNING: multiple pyz files for venv, you need to ensure each file by special name like `import ensure_zipapps_{file_name}`(such as `import ensure_zipapps_bottle`) instead of `import ensure_zipapps`.

```python
'''
zip env as usual:
python3 -m zipapps -u bottle -o bottle_env.pyz bottle
'''

import sys

# add `bottle_env.pyz` as import path
sys.path.append('bottle_env.pyz')

# now import bottle to see where it located

import bottle
print(bottle.__file__)
# yes, it's in the bottle_env.pyz: bottle_env.pyz/bottle.py

# now `import ensure_zipapps` to activate the unzip step
import ensure_zipapps_bottle_env

# reload bottle module to check if the location of bottle changed
import importlib
importlib.reload(bottle)

# now import bottle to see where it located
print(bottle.__file__)
# yes again, it changed to the unzip path: bottle_env_unzip_cache/bottle.py
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
   2. Simple deployment towards different servers with `jenkins`, or other CI/CD tools.
   3. Distribute zipapp with embedded python.
   4. Use as a requirements zip path.
      1. `import sys;sys.path.insert(0, 'app.pyz')` (without .so/.pyd)
      2. `python3 app.pyz script.py`
   5. Other usages need to be found, and enjoy yourself.
