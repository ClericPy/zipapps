# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
from shutil import rmtree
from zipfile import ZipFile


def main():
    """Template code for zipapps entry point. Run with current PYTHONPATH"""
    # env of Popen is not valid for win32 platform, use os.environ instead.
    # PYTHONPATH=./app.pyz
    zip_file_path = str(Path(__file__).parent.absolute())
    python_path_list = [zip_file_path]
    unzip = r'''{unzip}'''
    if unzip:
        _temp_folder = r'''{unzip_path}'''
        _temp_folder_path = Path(_temp_folder)
        _temp_folder_abs_path = str(_temp_folder_path.absolute())
        python_path_list.insert(0, _temp_folder_abs_path)
        ts_file_name = '_zip_time_{ts}'
        if not (_temp_folder_path / ts_file_name).is_file():
            # check timestamp difference by file name, need to refresh _temp_folder
            # rm the folder
            for _ in range(3):
                try:
                    if not _temp_folder_path.is_dir():
                        break
                    rmtree(_temp_folder_path)
                except FileNotFoundError:
                    break
            _temp_folder_path.mkdir()
            _need_unzip_names = unzip.split(',')
            _need_unzip_names.append(ts_file_name)
            with ZipFile(zip_file_path, "r") as zf:
                for member in zf.infolist():
                    file_dir_name = os.path.splitext(
                        member.filename.split('/')[0])[0]
                    if unzip == '*' or file_dir_name in _need_unzip_names:
                        zf.extract(member, path=_temp_folder_abs_path)

    sep = ';' if sys.platform == 'win32' else ':'
    os.environ['PYTHONPATH'] = sep.join(python_path_list)
    has_main = {has_main}
    if has_main:
        if {main_shell}:
            from subprocess import call
            shell_args = [sys.executable, '-c', '{import_main};{run_main}']
            call(shell_args, shell={shell})
        else:
            ignore_system_python_path = {ignore_system_python_path}
            if ignore_system_python_path:
                sys.path.clear()
            # let the dir as first
            sys.path = python_path_list + sys.path
            {import_main}
            {run_main}
    else:
        from subprocess import call
        shell_args = [sys.executable] + sys.argv[1:]
        call(shell_args, shell={shell})


if __name__ == "__main__":
    main()
