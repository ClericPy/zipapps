# [zipapps](https://github.com/ClericPy/zipapps)

[![PyPI](https://img.shields.io/pypi/v/zipapps?style=plastic)](https://pypi.org/project/zipapps/)[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/clericpy/zipapps/pythonpackage.yml)](https://github.com/ClericPy/zipapps/actions)![PyPI - Wheel](https://img.shields.io/pypi/wheel/zipapps?style=plastic)![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=zipapps)![PyPI - Downloads](https://img.shields.io/pypi/dm/zipapps?style=plastic)![PyPI - License](https://img.shields.io/pypi/l/zipapps?style=plastic)

[Changelogs](https://github.com/ClericPy/zipapps/blob/master/changelog.md)

`zipapps` is a **pure-python** library, to package your python code into a single zip file with its dependencies.

Depends on [PEP441](https://www.python.org/dev/peps/pep-0441/) + [zipapp](https://docs.python.org/3/library/zipapp.html) + [zipimport](https://docs.python.org/3/library/zipimport.html).

# What is the `.pyz`?

`.pyz` to `Python` is like `.jar` to `Java`.

They are both zip archive files which aggregate many packages and associated metadata and resources (text, images, etc.) into one file for distribution.

All you need is the **Python Interpreter** as the runtime environment.

So, what could `zipapps` be?

1. `packaging tool`
    > compress your package folder into a zip file.
2. `single-file virtual environment`
    > a portable site-packages.
3. `dependences installer`
    > lazy install requirements while first running.
4. `set of import-path`
    > add many `venv.pyz` files to PYTHONPATH automatically.
5. `requirements.txt freezing toolkit`
    > use `venv` to freeze your pip packages.

> PS: The pyz extension can be modified to any character you want, such as `.py` and `.zip`.

# Install & Quick Start

> pip install zipapps -U

## 1. Source code without dependences

1. add your source code into the zip file, and set the entrypoint with `-m`
   1. > python3 -m zipapps -c -a entry.py -m entry:main -o app.pyz
      1. `entry.py` could be a package `package_name`
      2. `-m` format is `package.module:function`
2. run app.pyz
   1. > python3 app.pyz

## 2. Source code with dependences

1. zipapps with requirements
   
   1. > python3 -m zipapps -c -a entry.py -m entry:main -o app.pyz bottle
      1. `bottle` is a pure-python lib which may not be unzipped
         1. `-u AUTO` or `-u=*` should be set for some `.so/.pyd` libs
            1. such as `psutil`
            2. notice that the `-u=*` != `-u *`
   2. you don't need to install requirements at running

      1. ensure the compatibility of the system environment and python version
      2. or add `-d` of `lazy install` mode to skip the compatibility problem
         1. but comes a long-time `pip install` process at the first running.

2. run app.pyz
   
   1. > python3 app.pyz
   2. libs with `.pyd/.so` caches will be unzipped to the `./zipapps_cache/app` by `-u AUTO`

## 3. Virtual environments

1. zipapps with requirements
   
   1. > python3 -m zipapps -c -u AUTO -o venv.pyz -r requirements.txt

2. run entry.py with venv.pyz
   
   1. > python3 venv.pyz entry.py
   2. the cache will be unzipped to `./zipapps_cache/venv` for `-u` is not null

## 4. Activate the `.pyz` environment

1. `import zipimport; zipimport.zipimporter('bottle.pyz').load_module("ensure_zipapps")`
   1. automatically unzip cache, and add the path to sys.path
   2. it can be run multiple times
2. if they are all pure-python code and **no need to decompress**
   1. `impory sys; sys.path.insert(0, "bottle.pyz")`


# Command line usage

![image](https://github.com/ClericPy/zipapps/raw/master/args.png)

## Build Args

**most common args:**

- `-c`
  - to compress files, only for python3.7+.
- `-a xxx.py`
  - to add some files/folders into the zipped file.
- `-u=AUTO`
  - **Recommended**
  - auto unzip the .pyd / .so files
    - or `-u=*` to unzip all the files
- `-r requirements.txt`
  - install requirements with `pip install`
- `-o my_app.pyz`
  - output the zipped file as given path
- `-m app.__main__:main`
  - entry point
- `-p /usr/bin/python3`
  - set the `shebang` line
- `-d`
  - **Recommended**
  - requirements will be installed with `pip` while first running in the lazy install mode
  - zip file size will be very small, and the default unzip path is `SELF/zipapps_cache/`
- `--clear-zipapps-cache`, `-czc`
  - Clear the zipapps cache folder after running, but maybe failed for .pyd/.so files.

Details: 

> python3 -m zipapps -h

1. `-h, --help`
   1. **show the simple doc**
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
      1. `package.module:function`
      2. `package.module`
      3. `module:function`
      4. `package`
   2. the `main` arg of `zipapps.create_app`
   3. WARNING: If the `--main` arg is set, `python3 app.pyz` will not be able to used as venv like `python3 app.pyz xxx.py`
6. `--compress, -c`
   1. `Boolean` value, compress files with the deflate method or not.
   2. the `compressed` arg of `zipapps.create_app`
7. `--unzip, -u`
   1. The names which need to be unzipped while running, splited by "," `without ext`, such as `bottle,aiohttp`, or the complete path like `bin/bottle.py,temp.py`. For `.so/.pyd` files(which can not be loaded by zipimport), or packages with operations of static files.
      1. if unzip is set to "*", then will unzip all files and folders.
      2. if unzip is set to **AUTO**, then will add the `.pyd` and `.so` files automatically.
   2. Can be overwrite with environment variable `ZIPAPPS_UNZIP`
   3. the `unzip` arg of `zipapps.create_app`
8. `--unzip-exclude, -ue`
   1. The opposite of `--unzip` / `-u` which will not be unzipped, should be used with `--unzip` / `-u`.
   2. Can be overwrite with environment variable `ZIPAPPS_UNZIP_EXCLUDE`
9. `--unzip-path, -up`
   3. If `unzip` arg is not null, cache files will be unzipped to the given path while running. Defaults to `zipapps_cache`, support some internal variables as runtime args:
      1. `$TEMP/$HOME/$SELF/$PID/$CWD` as prefix, for example `$HOME/zipapps_cache`
         1. `TEMP` means `tempfile.gettempdir()`
         2. `HOME` means `Path.home()`
         3. `SELF` means `.pyz` file path.
         4. `$PID` means `os.getpid()`
         5. `$CWD` means `Path.cwd()`
      2. And you can also **overwrite** it with environment variables:
         1. `ZIPAPPS_CACHE` or `UNZIP_PATH`
   4. the `unzip_path` arg of `zipapps.create_app`
10. `-cc, --pyc, --compile, --compiled`
    1. Compile .py to .pyc for fast import, but zipapp does not work unless you unzip it(so NOT very useful).
    2. the `compiled` arg of `zipapps.create_app`
11. ` --cache-path, --source-dir, -cp`
    1. The cache path of zipapps to store site-packages and `includes` files. If not set, will create and clean-up in TEMP dir automately.
    2. the `cache_path` arg of `zipapps.create_app`
12. `--shell, -s`
    1. Only while `main` is not set, used for shell=True in `subprocess.run`.
       1. *very rarely used*, because extra sub-process is not welcome
    2. the `shell` arg of `zipapps.create_app`
13. `--main-shell, -ss`
    1. Only for `main` is not null, call `main` with `subprocess.Popen`: `python -c "import a.b;a.b.c()"`. This is used for `psutil` ImportError of DLL load.
       1. *very rarely used* too
    2. the `main_shell` arg of `zipapps.create_app`
14. `--strict-python-path, -spp`
    1. `Boolean` value. Ignore global PYTHONPATH, only use `zipapps_cache` and `app.pyz`.
    2. the `ignore_system_python_path` arg of `zipapps.create_app`
15. `-b, --build-id`
    1. The string to skip duplicate builds, it can be the paths of files/folders which splited by ",", then the modify time will be used as build_id. If build_id contains `*`, will use `glob` function to get paths. For example, you can set requirements.txt as your build_id by `python3 -m zipapps -b requirements.txt -r requirements.txt` when you use pyz as venv.
       1. *very rarely used* too too
    2. the `build_id` arg of `zipapps.create_app`
16. `--zipapps, --env-paths`
    1. Default `--zipapps` arg if it is not given while running. Support $TEMP/$HOME/$SELF/$PID/$CWD prefix.
17. `--delay, -d, --lazy-pip, --lazy-install, --lazy-pip-install`
    1. Install packages with pip while first running, which means requirements will not be install into pyz file.
18. `--ensure-pip`
    1. Add the ensurepip package to your pyz file, works for **embed-python**(windows) or other python versions without `pip` installed but `lazy-install` mode is enabled. [EXPERIMENTAL]
19. `--layer-mode`
    1. Layer mode for the `serverless` use case, `__main__.py / ensure_zipapps.py / activate_zipapps.py` files will not be set in this mode.
    2. `--layer-mode-prefix`
       1. Only work while `--layer-mode` is set, will move the files in the given prefix folder.
20. `--clear-zipapps-cache, -czc`
    1. Clear the zipapps cache folder after running, but maybe failed for .pyd/.so files.
21. `--clear-zipapps-self, -czs`
    1. Clear the zipapps pyz file self after running.
22. `--chmod`
    1. os.chmod(int(chmod, 8)) for unzip files with `--chmod=777`
        1.  unix-like system only
23. `--dump-config`
    1. Dump zipapps build args into JSON string.
       1. A file path needed and `-` means stdout.
24. `--load-config`
    1. Load zipapps build args from a JSON file.
25. `--freeze-reqs`
    1.  Freeze package versions of pip args with venv, output to the given file path.
        1.  `-` equals to `stdout`
        2.  logs will be redirect to `stderr`
    2.  Based on `pip` + `venv`
        1.  work folder is `tempfile.TemporaryDirectory`, prefix='zipapps_'
26. all the other (or `unknown`) args will be used by `pip install`
    1. such as `-r requirements.txt`
    2. such as `bottle aiohttp`
    3. the `pip_args` arg of `zipapps.create_app`

## Runtime Args

> available args while the `.pyz` is running

1. `--zipapps`
   1. including some other pyz into PYTHONPATH
   2. often be used as `multiple venv combination`
   3. for example
      1. build
         1. `python3 -m zipapps -o six.pyz six`
         2. `python3 -m zipapps -o psutil.pyz -u AUTO psutil`
         3. `python3 -m zipapps -o bottle.pyz bottle`
      2. run
         1. `python3 six.pyz --zipapps=psutil.pyz,bottle.pyz -c "import psutil, bottle"`
2. `--activate-zipapps` / `--ensure-zipapps`
   1. to ensure the zipapps_cache folder but do nothing
3. use environment variables to reset build args while running, and custom it with `ENV_ALIAS` arg
    1.  the upper names are environment variables
    2.  
            'unzip': 'ZIPAPPS_UNZIP',
            'unzip_exclude': 'ZIPAPPS_UNZIP_EXCLUDE',
            'unzip_path': 'ZIPAPPS_CACHE',
            'ignore_system_python_path': 'STRICT_PYTHON_PATH',
            'python_version_slice': 'PYTHON_VERSION_SLICE',
            'clear_zipapps_cache': 'CLEAR_ZIPAPPS_CACHE',
            'clear_zipapps_self': 'CLEAR_ZIPAPPS_SELF',
            'unzip_chmod': 'UNZIP_CHMOD',

# When to Use it?

1. Package your code(package or model) into one zipped file. 
   
   1. Pure python code without any 3rd-party dependencies.
   
   2. Python code with 3rd-party dependencies installed together.
   
   3. Python code with requirements be not installed until running. 
      
      1. [**Recommended**] The `lazy install` mode by the arg `-d`.
      
      2. The dependences will be installed at the first running(only once).
      
      3. This is `cross-platform` and `cross-python-version` for their independent cache paths.

2. Run with python interpreter from the `venv` path.
   
   1. which means the requirements(need to be unzipped) will be installed to the `venv` folder, not in `pyz` file.
   2. **build** your package into one `pyz` file with `-m package.module:function -p /venv/bin/python`.
   3. **run** the `pyz` file with `/venv/bin/python app.pyz` or `./app.pyz`.

3. Rapidly deploy stateless applications
   
   1. `Serverless`
      1. with a ready layer
   2. `Docker`
      1. only built once for a Python environment
      2. `wget http://S3_PATH/app.pyz && python3 app.pyz`
   3. `Spot instances`
      1. AWS or Aliyun
   4. `Hadoop-Streaming`
      1. mapper & reducer scripts

4. Simple deployment towards different servers with `jenkins`, or other CI/CD tools.
   
   1. Easy to uploads a clean `standalone` zip file.

5. Share the `app.pyz`to your friends
   
   1. someone has python installed
      
      1. or embedded python
      
      2. or use nuitka
         
         1. [zipapps with nuitka](https://github.com/ClericPy/zipapps/issues/11)

6. Use as a requirements zip path, or some `venv` usages.
   
   1. inner the code
      
      1. `import sys;sys.path.insert(0, 'app.pyz')` 
      
      2. with .so/.pyd?
         
         1. `import activate_zipapps`
   
   2. or run it directly
      
      1. `python3 app.pyz script.py`

7. Other usages need to be found, and enjoy yourself

# Advanced Usage

Inspired by [shiv](https://github.com/linkedin/shiv) and with the differences.

1. `zipapps` may not always create the cache folder.
   1. `pure-python` dependencies can be import directly without unzipped.
   2. unless your package includes the C language-based libraries or dynamic modules(`.so/.pyd`), such as `psutil`.
      1. use the arg `-u=AUTO` or `-u=*`
2. The default cache path is `./zipapps_cache` instead of the `HOME` path.
3. One app name create cache folder only once.
4. You can install requirements with `pip` while first running(not packaging) by `lazy install` mode
   1. reducing your `.pyz` file size.
      1. cross-platform and cross-python-version
   2. `python -m zipapps -c -d -a your-package -r requirements.txt`
5. Mix multiple `venv.pyz` files together.
   1. `python -m app.pyz --zipapps=bottle.pyz,requests.pyz`
6. **Freeze** your requirements.txt
   1. `python -m zipapps --freeze-reqs=requirements.lock -r requirements.txt`

<details>

<summary> <b>Click here read more</b> </summary>

## 1. Package your script file with only built-ins functions.

1.1 Code of `script.py`

```python
print('ok')
```

1.2 build the `app.pyz`

> python3 -m zipapps -c -a script.py -m script -p /usr/bin/python3

1.3 run this app

> python3 app.pyz

or

> ./app.pyz

ouput

    ok

Details:

    -c:
        compress files, 7.6KB => 3.3KB
    -a:
        add the script file to app.pyz, so you can use it while running
    -m:
        set the entry_point, also can be set as `-m script:main` as long as you has the main function
    -p:
        set the shebang line, so you can use `./app.pyz` instead of `python3 app.pyz`

## 2. Package your package folder into one zip file.

2.1 The package `example` and the code of `__main__.py`

    └── example
        ├── __init__.py
        └── __main__.py

```python
def main():
    print('ok')


if __name__ == "__main__":
    main()
```

2.2 build the `example.pyz`

> python3 -m zipapps -c -a example -o example.pyz -m example.__main__:main -p /usr/bin/python3

2.3 Run with `python3 example.pyz` or `./example.pyz`

output

    ok

Details:

    -m:
        set the entry_point with format like `package.model:function`
    -o:
        set the output file path, you can set it some other paths like `/home/centos/example.abc` and run with `python3 /home/centos/example.abc`
    no more new args.

## 3. Package your code with requirements (bottle).

3.1 The package `example` and the code of `__main__.py`

        └── example
            ├── __init__.py
            └── __main__.py

```python
def main():
    import bottle
    print(bottle.__version__)


if __name__ == "__main__":
    main()
```

3.2 build the `example.pyz` with requirements installed

> python3 -m zipapps -c -a example -o example.pyz -m example.__main__:main bottle

3.3 Run with `python3 example.pyz` or `./example.pyz`

Output

    0.12.19

Details:

    bottle:
        all the unhandled args (like `bottle`) will be used to `pip install`, so you can write `bottle` in requirements.txt and use like `-r requirements.txt`

**WARNING**: if the requirements have `.pyd/.so` files, you should unzip them while running, and the pure python libs like `bottle` or `requests`  no need to unzip anything. Read the 4th paragraph for more info.

## 4. Package your code with the requirements which includes `.pyd/.so` files.

4.1 The package `example` and the code of `__main__.py`

    └── example
        ├── __init__.py
        └── __main__.py

```python
def main():
    import psutil
    print(psutil.__version__)


if __name__ == "__main__":
    main()
```

4.2 build the `example.pyz` with requirements installed

> python3 -m zipapps -c -a example -o example.pyz -m example.__main__:main -u AUTO -up TEMP/cache psutil

4.3 Run with `python3 example.pyz` or `./example.pyz`

Output

    5.8.0

Details:

    -u:
        means the file or folder names you want to unzip while running. Here is the `AUTO`, will unzip the psutil package because of its .pyd or .so files included.
    -up:
        the unzip path of cache folder. $TEMP/$HOME/$SELF/$PID/$CWD are the built-in runtime args, but for the stable usage you can ignore this arg then use `./zipapps_cache/example`. The cache will be refreshed while you rebuild this pyz.

WARNING: unzip path can be overwrited by `export ZIPAPPS_CACHE=./xxx` or `export UNZIP_PATH=./xxx` while running.

## 5. Package the requirements like a virtual environment without entry_point.

5.1 Code of `script.py`

```python
import bottle, requests
print(bottle.__version__, requests.__version__)
```

5.2 build the `venv.pyz` 

> python3 -m zipapps -c -o venv.pyz -p /usr/bin/python3 bottle requests

5.3 Some use cases

5.3.1 use the `venv.pyz` like a middleware

> python3 venv.pyz script.py

5.3.2 use the `venv.pyz` like the interpreter

> ./venv.pyz script.py

even like is also valid

> `python3 venv.pyz -c "import bottle,requests;print(bottle.__version__, requests.__version__)"`

5.3.3 use the `bottle` lib of `venv.pyz` in your normal code

```python
import sys
sys.path.append('path_to_venv/venv.pyz')
import bottle

print(bottle.__file__)
```

5.3.3 use the `pstuil` lib of `venv.pyz` in other normal code

> python3 -m zipapps -c -o venv.pyz psutil

```python
import sys
sys.path.append('path_to_venv/psutil_venv.pyz')
# need to activate the unzip action, there are 2 ways for the `.so/.pyd` libs
# 1. use the default activate name
import activate_zipapps
# 2. use a distinct lib name with file name for another venv file
sys.path.append('path_to_venv/lxml_venv.pyz')
import ensure_lxml_venv
# 2.1 or the old name
# import ensure_zipapps_lxml_venv


import psutil
import lxml

print(psutil.__file__)
print(lxml.__file__)
```

Output

    0.12.19 2.25.1

Details:

    No `-m` arg here, then the pyz file will do like an interpreter which contains the installed requirements.
    
    So you can use it like this:
    > python3 venv.pyz
    >>> import bottle
    >>> bottle.__file__

## 6. Using multiple venv pyz files for your pyz model.

6.1 Here is `script.py` again

```python
import bottle, requests
print(bottle.__version__, requests.__version__)
```

6.2 Build the `script.pyz`

> python3 -m zipapps -c -o script.pyz -a script.py -m script requests

6.3 Build the `requests.pyz` and `bottle.pyz` respectively

> python3 -m zipapps -c -o requests.pyz requests
> 
> python3 -m zipapps -c -o bottle.pyz bottle

6.4 And now run the `script.pyz` with two requirements

> python3 script.pyz --zipapps=bottle.pyz,requests.pyz

Output

    0.12.19 2.25.1

Details:

    --zipapps:
        This arg will help you run some zipapp with given venv.pyz files, the paths is separated by commas.

## 7. Package your code with lazy install mode, for a attempt of cross-platform.

7.1 Here is `script.py` again

```python
import six
print(six.__file__)
```

7.2 Build the `script.pyz`, this is very fast without downloading and installing 3rd packages.

> python3 -m zipapps -c -o script.pyz -a script.py -m script -d six

7.3 Run this `.pyz` file, and the requirements will be installed while first running.

> python3 script.pyz

Output

    Looking in indexes: https://pypi.xxx.com/simple/
    Collecting six
    Using cached https://xxx/packages/ee/ff/xxxx/six-1.15.0-py2.py3-none-any.whl (10 kB)
    Installing collected packages: six
    Successfully installed six-1.15.0
    /tmp/zipapps_cache/script/_zipapps_lazy_pip/3.8/Linux/six.py

Details:

    -d:
        Lazy install mode is useful for distributing your cross-platform apps.

</details>
