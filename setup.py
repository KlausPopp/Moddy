# created based on
# https://python-packaging.readthedocs.io/en/latest/minimal.html
# But instead of python setup.py register sdist upload,
# use https://pypi.org/p/twine/
#


from setuptools import setup
import sys
import os
import re

sys.path.append("src")


def read(fname):
    try:
        return open(os.path.join(os.path.dirname(__file__), fname)).read()
    except IOError:
        return "File '%s' not found.\n" % fname


def readVersion():
    txt = read("src/moddy/version.py")
    ver = re.findall(r"([0-9]+)", txt)
    print("ver=%s" % ver)
    return ver[0] + "." + ver[1] + "." + ver[2]


setup(
    name="moddy",
    install_requires=["svgwrite"],
    version=readVersion(),
    description="A discrete event simulator generating sequence diagrams",
    long_description=read("README.rst"),
    url="https://github.com/KlausPopp/Moddy",
    project_urls={
        "Documentation": "https://klauspopp.github.io/Moddy/",
        "Source Code": "https://github.com/KlausPopp/Moddy/",
    },
    keywords="simulation modelling",
    author="Klaus Popp",
    author_email="klauspopp@gmx.de",
    license="LGPL-3.0",
    platforms="OS Independent",
    package_dir={"": "src"},
    packages=[
        "moddy",
        "moddy.seq_diag_interactive_viewer",
        "moddy.lib",
        "moddy.lib.net",
    ],
    package_data={"moddy.seq_diag_interactive_viewer": ["*.css", "*.js"]},
)
