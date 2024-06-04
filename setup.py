# python
# -*- coding: utf-8 -*-
import codecs
import os
import re

from setuptools import find_packages, setup

"""
linux:
rm -rf "dist/*";rm -rf "build/*";python3 setup.py bdist_wheel;twine upload "dist/*;rm -rf "dist/*";rm -rf "build/*""
win32:
rm -rf dist;rm -rf build;python3 setup.py bdist_wheel;twine upload "dist/*";rm -rf dist;rm -rf build;rm -rf *.egg-info;python3 -m zipapps -m zipapps.__main__:main -a zipapps -o zipapps.pyz
"""

with codecs.open("README.md", encoding="u8") as f:
    long_description = f.read()

here = os.path.abspath(os.path.dirname(__file__))
with codecs.open(os.path.join(here, "zipapps", "main.py"), encoding="u8") as f:
    m = re.search(r"""__version__ = ['"](.*?)['"]""", f.read())
    assert m
    version = m.group(1)
desc = "Package your python code into one zip file, even a virtual environment."
keywords = "zipapp distribute publish zip standalone portable".split()
setup(
    name="zipapps",
    version=version,
    keywords=keywords,
    description=desc,
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT License",
    package_data={"zipapps": ["*.template"]},
    py_modules=["zipapps"],
    python_requires=">=3.7",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    author="ClericPy",
    author_email="clericpy@gmail.com",
    url="https://github.com/ClericPy/zipapps",
    packages=find_packages(),
    platforms="any",
)
