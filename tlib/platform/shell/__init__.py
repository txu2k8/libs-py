# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""
:description:
    shell related module
"""
# import os
# import time
# import sys
# import shutil
# import signal
# import random
# import hashlib
# import warnings
# import datetime
# import threading
# import traceback
# import subprocess
# import collections

# import tlib
# from tlib import exceptions as err
from tlib.platform.shell import oper

from tlib.platform.shell.oper import md5file
from tlib.platform.shell.oper import kill9_byname
from tlib.platform.shell.oper import del_if_exist
from tlib.platform.shell.oper import execshell
from tlib.platform.shell.oper import execshell_withpipe
from tlib.platform.shell.oper import execshell_withpipe_exwitherr
from tlib.platform.shell.oper import is_proc_alive
from tlib.platform.shell.oper import forkexe_shell
from tlib.platform.shell.oper import execshell_withpipe_ex
from tlib.platform.shell.oper import execshell_withpipe_str
from tlib.platform.shell.oper import ShellExec
from tlib.platform.shell.oper import rmtree
from tlib.platform.shell.oper import Asynccontent


_DEPRECATED_MSG = '''Plz use class tlib.shell.ShellExec instead. Function %s
 deprecated'''


def _test():
    pass


__all__ = [
    'oper',
    'expect'
]


if __name__ == '__main__':
    _test()
