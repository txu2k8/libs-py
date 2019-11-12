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
# from tlib import err
from libs.platform.shell import oper

from libs.platform.shell.oper import md5file
from libs.platform.shell.oper import kill9_byname
from libs.platform.shell.oper import del_if_exist
from libs.platform.shell.oper import execshell
from libs.platform.shell.oper import execshell_withpipe
from libs.platform.shell.oper import execshell_withpipe_exwitherr
from libs.platform.shell.oper import is_proc_alive
from libs.platform.shell.oper import forkexe_shell
from libs.platform.shell.oper import execshell_withpipe_ex
from libs.platform.shell.oper import execshell_withpipe_str
from libs.platform.shell.oper import ShellExec
from libs.platform.shell.oper import rmtree
from libs.platform.shell.oper import Asynccontent


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
