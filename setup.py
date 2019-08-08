# !/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#                                                        version: v1.0.0
#                                                             by: Tao.Xu
#                                                           date: 5/28/2019
#                                                      copyright: N/A
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NO INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
##############################################################################

"""
installation: setup.py
"""
import os
import re
import sys
import textwrap
import traceback
from setuptools import setup
# from distutils.core import setup

try:
    __name__ = 'tlib'
    __author__ = __import__(__name__).version.AUTHOR
    __version__ = __import__(__name__).version.VERSION
except Exception as e:
    raise Exception(e, traceback.print_exc())

this_directory = os.path.abspath(os.path.dirname(__file__))


# 读取文件内容
def _read_file(filename):
    with open(os.path.join(this_directory, filename), encoding='utf-8') as f:
        long_description = f.read()
    return long_description


def _read_requirements(filename):
    return [line.strip() for line in _read_file(filename).splitlines()
            if not line.startswith('#')]


def _find_packages(prefix=''):
    """find pckages"""
    packages = []
    path = '.'
    prefix = prefix
    for root, _, files in os.walk(path):
        if '__init__.py' in files:
            if sys.platform.startswith('linux'):
                item = re.sub('^[^A-z0-9_]', '', root.replace('/', '.'))
            elif sys.platform.startswith('win'):
                item = re.sub('^[^A-z0-9_]', '', root.replace('\\', '.'))
            else:
                item = re.sub('^[^A-z0-9_]', '', root.replace('/', '.'))
            if item is not None:
                packages.append(item.lstrip('.'))
    return packages


setup(
    name=__name__,
    version=__version__,
    author=__author__,
    # python_requires='>=3.4.0',
    install_requires=_read_requirements('requirements.txt'),
    description='Some own/observed great lib/ideas,common useful python libs',
    long_description=_read_file('README.md'),
    long_description_content_type="text/markdown",
    url='https://github.com/txu2008/TLIB',
    maintainer='tao.xu2008@outlook.com',
    author_email='tao.xu2008@outlook.com',
    keywords='library common baselib framework, stress runnner',
    packages=_find_packages(__name__),
    package_data={
        '': [
            '*.so', '*.pyo',
            # for matplotlib
            '*.ttf', '*.afm', '*.png', '*.svg', '*.xpm',
            'Matplotlib.nib/classes.nib', 'Matplotlib.nib/info.nib',
            'Matplotlib.nib/keyedobjects.nib',
            'mpl-data/lineprops.glade',
            'mpl-data/matplotlibrc',
        ]
    },
    classifiers=textwrap.dedent("""
        License :: MIT License,
        Natural Language :: English
        Intended Audience :: Developers
        Operating System :: WINDOWS
        Operating System :: POSIX :: Linux
        Programming Language :: Python :: 2.7
        Programming Language :: Python :: 3
        Topic :: Software Development :: Libraries :: Python Modules
        Topic :: Utilities
        """).strip().splitlines(),
)
