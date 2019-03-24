# created based on https://python-packaging.readthedocs.io/en/latest/minimal.html
# But instead of python setup.py register sdist upload, use https://pypi.org/p/twine/
#



from setuptools import setup, find_packages
import sys
import os

sys.path.append("src")
from moddy.version import VERSION

def read(fname):
    try:
        return open(os.path.join(os.path.dirname(__file__), fname)).read()
    except IOError:
        return "File '%s' not found.\n" % fname

setup(name='moddy',
    install_requires=['svgwrite'],
    version=VERSION,
    
    description='A discrete event simulator generating sequence diagrams',
    
    long_description=read('README.rst'),
    url='https://github.com/KlausPopp/Moddy',
      
    project_urls={
        "Documentation": "https://klauspopp.github.io/Moddy/",
        "Source Code": "https://github.com/KlausPopp/Moddy/",
    },

    keywords = "simulation modelling",
      
    author='Klaus Popp',
    author_email='klauspopp@gmx.de',
    license='LGPL-3.0',
    
    platforms="OS Independent",
    
    package_dir = { '': 'src'},
    
    packages = [ 'moddy', 'moddy.seqDiagInteractiveViewer'],
    
    package_data={'moddy.seqDiagInteractiveViewer': ['*.css', '*.js']},
    
    )
