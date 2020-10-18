import os
import subprocess
import sys
from pathlib import Path


def main():
    """run python file with current PYTHONPATH"""
    # default entry point, used like venv
    shell_args = [sys.executable] + sys.argv[1:]
    # env of Popen is not valid for win32 platform, use os.environ instead.
    # PYTHONPATH=./app.pyz
    os.environ['PYTHONPATH'] = str(Path(__file__).parent.absolute())
    subprocess.Popen(shell_args, shell=True).wait()
