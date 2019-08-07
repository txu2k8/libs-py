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
from tlib.shell import expect
from tlib.shell import oper

from tlib.shell.oper import md5file
from tlib.shell.oper import kill9_byname
from tlib.shell.oper import del_if_exist
from tlib.shell.oper import execshell
from tlib.shell.oper import execshell_withpipe
from tlib.shell.oper import execshell_withpipe_exwitherr
from tlib.shell.oper import is_proc_alive
from tlib.shell.oper import forkexe_shell
from tlib.shell.oper import execshell_withpipe_ex
from tlib.shell.oper import execshell_withpipe_str
from tlib.shell.oper import ShellExec
from tlib.shell.oper import rmtree
from tlib.shell.oper import Asynccontent


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

# vi:set tw=0 ts=4 sw=4 nowrap fdm=indent
