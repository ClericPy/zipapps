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
        python_path_list.insert(0, _temp_folder)
        _temp_folder_path = Path(_temp_folder)
        ts_file_name = '_zip_time_{ts}'
        if not (_temp_folder_path / ts_file_name).is_file():
            # check timestamp different, need to refresh _temp_folder
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
                        zf.extract(member,
                                   path=str(_temp_folder_path.absolute()))

    sep = ';' if sys.platform == 'win32' else ':'
    os.environ['PYTHONPATH'] = sep.join(python_path_list)

    shell_args = [sys.executable] + sys.argv[1:]
    has_main = {has_main}
    if has_main:
        if {ignore_system_python_path}:
            sys.path.clear()
        for p in python_path_list[::-1]:
            sys.path.insert(0, p)
        {import_main}
        {run_main}
    else:
        from subprocess import Popen
        Popen(shell_args, shell={shell}).wait()


if __name__ == "__main__":
    main()
