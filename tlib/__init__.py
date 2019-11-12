# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""
Some own/observed great lib/ideas,common useful python libs.
"""

import sys
import test
from tlib import log
from tlib import decorators
from tlib import err
from tlib import mail
from tlib.platform import shell
from tlib.utils import util
from tlib import platform
from tlib import version

if sys.version_info < (2, 6):
    raise ImportError('tlib needs to be run on python 2.6 and above.')


__all__ = [
    'bs', 'ds', 'fileop', 'retry', 'stressrunner', 'log',
    'validparam', 'platform', 'mail', 'utils',
    'err', 'decorators', 'version', 'test'
]
