# [zipapps](https://github.com/ClericPy/zipapps)
[![PyPI](https://img.shields.io/pypi/v/zipapps?style=plastic)](https://pypi.org/project/zipapps/)[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/clericpy/zipapps/Python%20package?style=plastic)](https://github.com/ClericPy/zipapps/actions?query=workflow%3A%22Python+package%22)![PyPI - Wheel](https://img.shields.io/pypi/wheel/zipapps?style=plastic)![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zipapps?style=plastic)![PyPI - Downloads](https://img.shields.io/pypi/dm/zipapps?style=plastic)![PyPI - License](https://img.shields.io/pypi/l/zipapps?style=plastic)

Package your python code(with requirements) into a standalone file(like a `jar`).

Inspired by [shiv](https://github.com/linkedin/shiv), and unlike `shiv`, this lib will not always create new cache folders while running.

# What is `pyz`?

`.pyz` to **Python** is like `.jar` to **Java**. They are both zipped archive files which aggregate many Python packages and associated metadata and resources (text, images, etc.) into one file for distribution. Then you will need only a Python Interpreter as the runtime environment.

PS: The **pyz** ext could be any other suffixes even without ext names, so you can rename `app.pyz` to `app.par` as you wish. Depends on [PEP441](https://www.python.org/dev/peps/pep-0441/), so it may be cross-platform without C-Libs.

# Install

Written with the pure python without any 3rd party libraries.

> pip install zipapps -U

# Usage

## Scene-1: Package your code with requirements as a standalone application.



## View more

> python3 -m zipapps -h

<details>
    <summary>Using as the venv zip file</summary>
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
# yes again, it changed to the unzip path: zipapps_cache/bottle_env/bottle.py
```
</details>

# FAQ

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
4. How to use multiple venv `pyz` files in one script?
   1. os.environ['UNZIP_PATH'] = '/tmp/unzip_caches'
      1. or os.environ['ZIPAPPS_PATH'] = '/tmp/unzip_caches'
   2. sys.path.insert(0, 'PATH_TO_PYZ_1')
   3. import ensure_zipapps_{output_name_1}
   4. sys.path.insert(0, 'PATH_TO_PYZ_2')
   5. import ensure_zipapps_{output_name_2}
5. Where to Use it?
   1. Hadoop-Streaming's mapper & reducer.
   2. Simple deployment towards different servers with `jenkins`, or other CI/CD tools.
   3. Distribute zipapp with embedded python.
   4. Use as a requirements zip path.
      1. `import sys;sys.path.insert(0, 'app.pyz')` (without .so/.pyd)
      2. `python3 app.pyz script.py`
   5. Other usages need to be found, and enjoy yourself.

# Todos

- [x] Zip pure python code without cache folder while running.
  - pure python code will not unzip anything by default.
- [x] Zip files/folders by your choice, and unzip which you want.
  - files/libs/folders will be unzip to `-up`/`--unzip-path`, default is `./zipapps_cache` while running.
  - `unzip_path` could use the given variable `HOME` / `TEMP` / `SELF`, for example
    - *HOME/cache* => *~/cache* folder
    - *TEMP/cache* => */tmp/cache* in linux
      - or *C:\Users\user\AppData\Local\Temp\cache* in win32
    - *SELF/cache* => *app.pyz/../cache*
      - *SELF* equals to the parent folder of **pyz** file
  - or you can **reset a new path with environment variable** `UNZIP_PATH` or `ZIPAPPS_PATH`
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

# Changelogs

- 2020.11.21
  - reset unzip_path as the parent folder to unzip files
    - so the cache path will be like `./zipapps_cache/app/` for `app.pyz`,
    - this is different from old versions.
  - add environment variable `ZIPAPPS_PATH` for arg `unzip_path`
  - add environment variable `ZIPAPPS_UNZIP` for arg `unzip`
