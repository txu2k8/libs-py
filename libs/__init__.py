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
from libs import log
from libs import decorators
from libs import err
from libs import mail
from libs.platform import shell
from libs.utils import util
from libs import platform
from libs import version

if sys.version_info < (2, 6):
    raise ImportError('tlib needs to be run on python 2.6 and above.')


__all__ = [
    'bs', 'data_structure', 'fileop', 'retry', 'stressrunner', 'log',
    'validparam', 'platform', 'mail', 'utils',
    'err', 'decorators', 'version', 'test'
]
