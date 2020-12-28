# [zipapps](https://github.com/ClericPy/zipapps)
[![PyPI](https://img.shields.io/pypi/v/zipapps?style=plastic)](https://pypi.org/project/zipapps/)[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/clericpy/zipapps/Python%20package?style=plastic)](https://github.com/ClericPy/zipapps/actions?query=workflow%3A%22Python+package%22)![PyPI - Wheel](https://img.shields.io/pypi/wheel/zipapps?style=plastic)![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zipapps?style=plastic)![PyPI - Downloads](https://img.shields.io/pypi/dm/zipapps?style=plastic)![PyPI - License](https://img.shields.io/pypi/l/zipapps?style=plastic)

Package your python code (with requirements) into a standalone zip file (like a `jar`).

`zipapps` is a `pure-python library`, without any 3rd-party dependencies. Inspired by [shiv](https://github.com/linkedin/shiv) but unlike `shiv`, this lib will not always create new cache folders while running, and easy to combine multiple `venv.pyz` files then let them work well together.

# What is the `pyz`?

`.pyz` to **Python** is like `.jar` to **Java**. They are both zip archive files which aggregate many packages and associated metadata and resources (text, images, etc.) into one file for distribution. Then what you only need is a Python Interpreter as the runtime environment.

PS: The **pyz** ext could be any other suffixes even without ext names, so you can rename `app.pyz` to `app.zip` as you wish. Depends on [PEP441](https://www.python.org/dev/peps/pep-0441/), then the apps may be `cross-platform` as long as written with pure python code without any C++ building processes.

## Where to Use it?
   1. Hadoop-Streaming's mapper & reducer scripts.
   2. Simple deployment towards different servers with `jenkins`, or other CI/CD tools.
      1. Easy to uploads a clean `standalone` zip file.
   3. Distribute `zipapp` with embedded python.
   4. Use as a requirements zip path, or some venv usages.
      1. `import sys;sys.path.insert(0, 'app.pyz')` (without .so/.pyd)
      2. `python3 app.pyz script.py`
   5. Other usages need to be found, and enjoy yourself.

# Install

> pip install zipapps -U

# Quick Start

## zip as the app
1. zipapps with requirements
   1. > python3 -m zipapps -u AUTO -a entry.py -m entry:main -o app.pyz aiohttp,psutils
2. run app.pyz
   1. > python3 app.pyz
   2. **cache will be unzipped to `./zipapps_cache/app`**

## zip as the venv
1. zipapps with requirements
   1. > python3 -m zipapps -u AUTO -o venv.pyz -r requirements.txt
2. run entry.py with venv.pyz
   1. > python3 venv.pyz entry.py
   2. **cache will be unzipped to `./zipapps_cache/venv`**

# CMD Args

## Packaging args

> **most common args:**

- `-c`
- `-a xxx.py`
- `-u=AUTO`, 
- `-r requirements.txt`
- `-o my_app.pyz`
- `-m app.__main__:main`
- `-p /usr/bin/python3`

1. `-h, --help`
   1. show the simple doc
2. `--includes, --add, -a`
   1. The given paths will be copied to `cache_path` while packaging, which can be used while running. The path strings will be splited by ",".
      1. such as `my_package_dir,my_module.py,my_config.json`
      2. often used for libs not from `pypi` or some special config files
   2. the `output` arg of `zipapps.create_app`
3. `--output, -o`
   1. The path of the output file, defaults to `app.pyz`.
   2. the `output` arg of `zipapps.create_app`
4. `--python, -p`
   1. The path of the Python interpreter which will be set as the `shebang line`, defaults to `None`.
      1. with shebang `/usr/bin/python3` you can run app with `./app.pyz` directly, no need for `python3 app.pyz`
   2. the `interpreter` arg of `zipapps.create_app`
5. `--main, -m`
   1. The entry point function of the application, the `valid format` is:
      1.  `package.module:function`
      2.  `package.module`
      3.  `module:function`
      4.  `package`
   2. the `main` arg of `zipapps.create_app`
   3. WARNING: If the `--main` arg is set, `python3 app.pyz` will not be able to used as venv like `python3 app.pyz xxx.py`
6. `--compress, -c`
   1. `Boolean` value, compress files with the deflate method or not.
   2. the `compressed` arg of `zipapps.create_app`
7. `--unzip, -u`
   1. The names which need to be unzipped while running, splited by "," `without ext`, such as `bottle,aiohttp`, or the complete path like `bin/bottle.py,temp.py`. For `.so/.pyd` files(which can not be loaded by zipimport), or packages with operations of static files.
      1. if unzip is set to "*", then will unzip all files and folders.
      2. if unzip is set to **AUTO**, then will add the `.pyd` and `.so` files automatically.
   2. the `unzip` arg of `zipapps.create_app`
8. `--unzip-path, -up`
   1. If `unzip` arg is not null, cache files will be unzipped to the given path while running. Defaults to `zipapps_cache`, support some internal variables:
      1.  `TEMP/HOME/SELF` as internal variables, for example `HOME/zipapps_cache`
          1. `TEMP` means `tempfile.gettempdir()`
          2. `HOME` means `Path.home()`
          3. `SELF` means `.pyz` file path.
      2. And you can also **overwrite** it with environment variables:
         1. `ZIPAPPS_CACHE` or `UNZIP_PATH`
   2. the `unzip_path` arg of `zipapps.create_app`
9. `-cc, --pyc, --compile, --compiled`
   1. Compile .py to .pyc for fast import, but zipapp does not work unless you unzip it(so NOT very useful).
   2. the `compiled` arg of `zipapps.create_app`
10. ` --cache-path, --source-dir, -cp`
   3. The cache path of zipapps to store site-packages and `includes` files. If not set, will create and clean-up in TEMP dir automately.
   4. the `cache_path` arg of `zipapps.create_app`
11. `--shell, -s`
    1.  Only while `main` is not set, used for shell=True in `subprocess.run`.
        1.  *very rarely used*, because extra sub-process is not welcome
    2.  the `shell` arg of `zipapps.create_app`
12. `--main-shell, -ss`
    1.  Only for `main` is not null, call `main` with `subprocess.Popen`: `python -c "import a.b;a.b.c()"`. This is used for `psutil` ImportError of DLL load.
        1.  *very rarely used* too
    2.  the `main_shell` arg of `zipapps.create_app`
13. `--strict-python-path, -spp`
    1.  `Boolean` value. Ignore global PYTHONPATH, only use `zipapps_cache` and `app.pyz`.
    2.  the `ignore_system_python_path` arg of `zipapps.create_app`
14. `-b, --build-id`
    1.  The string to skip duplicate builds, it can be the paths of files/folders which splited by ",", then the modify time will be used as build_id. If build_id contains `*`, will use `glob` function to get paths. For example, you can set requirements.txt as your build_id by `python3 -m zipapps -b requirements.txt -r requirements.txt` when you use pyz as venv.
        1.  *very rarely used* too too
    2.  the `build_id` arg of `zipapps.create_app`
15. all the other (or `unknown`) args will be used by "pip install"
    1.  such as `-r requirements.txt`
    2.  such as `bottle aiohttp`
    3.  the `pip_args` arg of `zipapps.create_app`

## Running args

> available args while the `.pyz` is running

1. `--zipapps`
   1. including some other pyz into PYTHONPATH
   2. often be used as `multiple venv combination`
   3. for example
      1. building
         1. `python3 -m zipapps -o six.pyz six`
         2. `python3 -m zipapps -o psutil.pyz -u AUTO psutil`
         3. `python3 -m zipapps -o bottle.pyz bottle`
      2. run
         1. `python3 six.pyz --zipapps=psutil.pyz,bottle.pyz -c "import psutil, bottle"`


# Changelogs

- 2020.12.27
  - Combile multiple `pyz` files, do like this:
    - python3 -m zipapps -o six.pyz six
    - python3 -m zipapps -o psutil.pyz -u AUTO psutil
    - python3 six.pyz --zipapps=psutil.pyz -c "import six,psutil;print(six.__file__, psutil.__file__)"
- 2020.12.23
  - `--unzip` support **auto-check** by `-u AUTO`, alias for `--unzip=AUTO_UNZIP`
  - fix `run_module` bug while running `./app.pyz -m module`
- 2020.12.21
  - now will not run a new subprocess in most cases.
    - using `runpy.run_path` and `runpy.run_module`
    - and using `subprocess.run` instead of `subprocess.call`
- 2020.12.13
  - `--unzip` support complete path
  - `--unzip` support **auto-check** by `--unzip=AUTO_UNZIP`
- 2020.11.23
  - add `activate_zipapps` to activate zipapps `PYTHONPATH` easily
- 2020.11.21
  - reset unzip_path as the parent folder to unzip files
    - so the cache path will be like `./zipapps_cache/app/` for `app.pyz`,
    - this is different from old versions.
  - add environment variable `ZIPAPPS_CACHE` for arg `unzip_path`
  - add environment variable `ZIPAPPS_UNZIP` for arg `unzip`

[Old Docs](old_doc.md)
