# -*- coding: utf-8 -*-
from .main import create_app, __version__, ZipApp, pip_install_target
from .activate_zipapps import activate

__all__ = ["create_app", "activate", "__version__", "ZipApp", "pip_install_target"]
__doc__ = "Package your python code into one zip file, even a virtual environment."
