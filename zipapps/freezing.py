import os
import re
import subprocess
import sys
import tempfile
import time
import typing
import venv
from pathlib import Path


def ttime(
    timestamp=None, tzone=int(-time.timezone / 3600), fail="", fmt="%Y-%m-%d %H:%M:%S"
):
    fix_tz = tzone * 3600
    if timestamp is None:
        timestamp = time.time()
    else:
        timestamp = float(timestamp)
        if 1e12 <= timestamp < 1e13:
            # Compatible timestamp with 13-digit milliseconds
            timestamp = timestamp / 1000
    try:
        timestamp = time.time() if timestamp is None else timestamp
        return time.strftime(fmt, time.gmtime(timestamp + fix_tz))
    except Exception:
        return fail


class FreezeTool(object):
    VENV_NAME = "zipapps_venv"
    # not stable
    FASTER_PREPARE_PIP = False

    def __init__(self, output: str, pip_args: list):
        if not pip_args:
            raise RuntimeError("pip args is null")
        self.temp_dir: typing.Optional[tempfile.TemporaryDirectory] = None
        self.pip_args = pip_args
        self.output_path = output

    def log(self, msg, flush=False):
        _msg = f"{ttime()} | {msg}"
        print(_msg, file=sys.stderr, flush=flush)

    def run(self):
        self.log(
            "All the logs will be redirected to stderr to ensure the output is stdout."
        )
        self.temp_dir = tempfile.TemporaryDirectory(prefix="zipapps_")
        self.temp_path = Path(self.temp_dir.name)
        self.log(
            f"Start mkdir temp folder: {self.temp_path.absolute()}, exist={self.temp_path.is_dir()}"
        )
        self.install_env()
        output = self.install_packages()
        self.freeze_requirements(output)
        return output

    def install_env(self):
        venv_path = self.temp_path / self.VENV_NAME
        self.log(f"Initial venv with pip: {venv_path.absolute()}")
        if self.FASTER_PREPARE_PIP:
            venv.create(env_dir=venv_path, system_site_packages=False, with_pip=False)
            import shutil

            import pip

            pip_dir = Path(pip.__file__).parent
            if os.name == "nt":
                target = venv_path / "Lib" / "site-packages" / "pip"
            else:
                pyv = "python%d.%d" % sys.version_info[:2]
                target = venv_path / "lib" / pyv / "site-packages" / "pip"
            shutil.copytree(pip_dir, target)
        else:
            venv.create(env_dir=venv_path, system_site_packages=False, with_pip=True)
        if not venv_path.is_dir():
            raise FileNotFoundError(str(venv_path))

    def install_packages(self):
        if os.name == "nt":
            python_path = self.temp_path / self.VENV_NAME / "Scripts" / "python.exe"
        else:
            python_path = self.temp_path / self.VENV_NAME / "bin" / "python"
        args = [
            str(python_path.absolute()),
            "-m",
            "pip",
            "install",
        ] + self.pip_args
        self.log(f'Install packages in venv: {args}\n{"-" * 30}')
        with subprocess.Popen(args, stdout=subprocess.PIPE) as proc:
            for line in proc.stdout:
                try:
                    line = line.decode()
                except ValueError:
                    line = line.decode("utf-8", "ignore")
                print(line.rstrip(), file=sys.stderr, flush=True)
        args = [str(python_path.absolute()), "-m", "pip", "freeze"]
        print("-" * 30, file=sys.stderr)
        self.log(f"Freeze packages in venv: {args}")
        output = subprocess.check_output(args)
        try:
            result = output.decode("utf-8")
        except ValueError:
            result = output.decode()
        result = re.sub("(\n|\r)+", "\n", result).strip()
        return result

    def freeze_requirements(self, output):
        if self.output_path == "-":
            print(output, flush=True)
        else:
            print(output, file=sys.stderr, flush=True)
            with open(self.output_path, "w", encoding="utf-8") as f:
                print(output, file=f, flush=True)

    def remove_env(self):
        if self.temp_dir and self.temp_path.is_dir():
            self.temp_dir.cleanup()
            self.log(
                f"Delete temp folder: {self.temp_path.absolute()}, exist={self.temp_path.is_dir()}"
            )

    def __del__(self):
        self.remove_env()

    def __enter__(self):
        return self

    def __exit__(self, *e):
        self.remove_env()


def test():
    with FreezeTool("-", ["six==1.15.0"]) as ft:
        result = ft.run()
        # print(result)
        assert result == "six==1.15.0"


if __name__ == "__main__":
    test()
