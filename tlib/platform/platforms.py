# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""
:description:
    cross-platform functions related module
"""

import os
import sys
import time

import select
import platform

from tlib import log
from tlib.bs import strsize_to_byte

# =============================
# --- Global Value
# =============================
logger = log.get_logger()
# --- OS/SYS platform
POSIX = os.name == "posix"
WINDOWS = os.name == "nt"
sys_platform = sys.platform
LINUX = sys_platform.startswith("linux")
OSX = sys_platform.startswith("darwin")
FREEBSD = sys_platform.startswith("freebsd")
OPENBSD = sys_platform.startswith("openbsd")
NETBSD = sys_platform.startswith("netbsd")
BSD = FREEBSD or OPENBSD or NETBSD
SUNOS = sys_platform.startswith("sunos") or sys_platform.startswith("solaris")
AIX = sys_platform.startswith("aix")

# __all__ = [
#     'is_linux',
#     'is_windows',
#     'is_mac'
# ]


def is_linux():
    """
    Check if you are running on Linux.
    :return:
        True or False
    """
    return platform.platform().startswith('Linux')


def is_windows():
    """
    Check if you are running on Windows.
    :return:
        True or False
    """
    return platform.platform().startswith('Windows')


def is_mac():
    """
    Check if you are running on Mac os
    :return:
        True or False
    """
    return hasattr(select, 'kqueue')


def reserve_cpu_deadloop():
    """reserve all cpu resource by deadloop"""
    while True:
        pass


def reserve_memory(mem_size_str='1GB', reserve_time=3600):
    """
    reserve_memory: size and keep time
    :param mem_size_str: 1GB | 1MB | 1KB ...
    :param reserve_time: 60(s)
    :return:
    """
    mem_size_byte = strsize_to_byte(mem_size_str)
    s = ' ' * mem_size_byte
    time.sleep(reserve_time)
    return True


if __name__ == '__main__':
    pass
