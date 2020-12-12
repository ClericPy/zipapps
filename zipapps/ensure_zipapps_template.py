import os
import sys
from pathlib import Path
from shutil import rmtree
from tempfile import gettempdir
from zipfile import ZipFile


def prepare_path():
    """Template code for zipapps entry point. Run with current PYTHONPATH"""
    # PYTHONPATH=./app.pyz
    zip_file_path = Path(__file__).parent.absolute()
    python_path_list = [str(zip_file_path)]
    unzip = os.environ.get('ZIPAPPS_UNZIP') or r'''{unzip}'''
    if unzip:
        _temp_folder = os.environ.get('ZIPAPPS_CACHE') or os.environ.get(
            'UNZIP_PATH') or r'''{unzip_path}'''
        if _temp_folder.startswith('HOME'):
            _temp_folder_path = Path.home() / (_temp_folder[4:].lstrip('/\\'))
        elif _temp_folder.startswith('SELF'):
            _temp_folder_path = zip_file_path.parent / (
                _temp_folder[4:].lstrip('/\\'))
        elif _temp_folder.startswith('TEMP'):
            _temp_folder_path = Path(
                gettempdir()) / (_temp_folder[4:].lstrip('/\\'))
        else:
            _temp_folder_path = Path(_temp_folder)
        _temp_folder_path = _temp_folder_path / zip_file_path.stem
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
                    # remove the exist folder
                    rmtree(_temp_folder_path)
                except FileNotFoundError:
                    break
            _temp_folder_path.mkdir(parents=True)
            _need_unzip_names = unzip.split(',')
            _need_unzip_names.append(ts_file_name)
            with ZipFile(zip_file_path, "r") as zf:
                for member in zf.infolist():
                    file_dir_name = os.path.splitext(
                        member.filename.split('/')[0])[0]
                    if unzip == '*' or member.filename in _need_unzip_names or file_dir_name in _need_unzip_names:
                        zf.extract(member, path=_temp_folder_abs_path)
    sep = ';' if sys.platform == 'win32' else ':'
    ignore_system_python_path = {ignore_system_python_path}
    if ignore_system_python_path:
        sys.path.clear()
        # env of Popen is not valid for win32 platform, use os.environ instead.
        os.environ['PYTHONPATH'] = sep.join(python_path_list)
    else:
        os.environ['PYTHONPATH'] = sep.join(python_path_list) + sep + (
            os.environ.get('PYTHONPATH') or '')
    # let the dir path first
    paths = [path for path in python_path_list if path not in sys.path]
    sys.path = paths + sys.path


prepare_path()
