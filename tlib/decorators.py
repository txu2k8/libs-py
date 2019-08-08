# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""
:description:
    decorators related module
"""

import os
import time
import platform
import threading
from functools import wraps
from datetime import datetime as datetime_in

from tlib import err
from tlib import log

__all__ = [
    'Singleton', 'print_for_call', 'TraceUsedTime', 'needlinux', 'needposix', 'needmac',
    'py_versioncheck'
]

my_logger = log.get_logger()


class Singleton(object):
    """
    Make your class singeton

    example::

        @Singleton
        class YourClass(object):
            def __init__(self):
            pass
    """
    def __init__(self, cls):
        self.__instance = None
        self.__cls = cls
        self._lock = threading.Lock()

    def __call__(self, *args, **kwargs):
        self._lock.acquire()
        if self.__instance is None:
            self.__instance = self.__cls(*args, **kwargs)
        self._lock.release()
        return self.__instance


def print_for_call(func):
    """
    Print the func Enter / Exit
    """

    def wrapper_func(*args, **kwargs):
        my_logger.info('Enter {0}.'.format(func.__name__))
        rtn = func(*args, **kwargs)
        my_logger.info('Exit from {0}. result: {1}'.format(func.__name__, rtn))
        return rtn

    return wrapper_func


def py_versioncheck(function, version):
    """
    :platform:
        any platform + any functions in python

    :param version:
        The python on the OS should be >= param version.
        *E.g. version=('2', '7', '0')*
        OS python version should >= 2.7.0
    """
    ind = 0
    py_version = platform.python_version_tuple()
    for i in py_version:
        if int(version(ind)) < int(i):
            raise err.DecoratorException(
                'Python version check failed. You expect version >= %s,'
                'but python-version on this machine:%s' %
                (version, py_version)
            )
        ind += 1
    return function


def needlinux(function):
    """
    make sure the func is only used on linux.
    Raise err.DecoratorException otherwise.

    :platform:
        Linux

    example
    ::

        from tlib import decorators
        @decorators.needlinux
        def your_func():
            pass
    """
    if platform.system() != 'Linux':
        raise err.DecoratorException(
            'The system is not linux.'
            'This functionality only supported in linux'
        )
    return function


def needposix(function):
    """
    only support posix

    :platform:
        Posix compatible

    example
    ::
        from tlib import decorators
        @decorators.needposix
        def your_func():
            pass
    """
    if os.name != 'posix':
        raise err.DecoratorException(
            'The system is not posix-based'
        )
    return function


def needmac(function):
    """
    only support macOS

    :platform:
        macOS

    example
    ::
        from tlib import decorators
        @decorators.needmac
        def your_func():
            pass
    """
    if platform.system() != 'Darwin':
        raise err.DecoratorException(
            'The system is not macOS.'
            'This functionality only supported in macOS'
        )
    return function


class TraceUsedTime(object):
    """
    Trace used time inside a function.

    Will print to LOGFILE if you initialized logging with log.init_comlog.

    example::

        import time

        from tlib import decorators

        @decorators.TraceUsedTime(True)
        def test():
            print 'test'
            time.sleep(4)


        # trace something with context. E.g. event_id
        def _test_trace_time_map(sleep_time):
            print "ready to work"
            time.sleep(sleep_time)


        traced_test_trace_time_map = decorators.TraceUsedTime(
            b_print_stdout=False,
            enter_msg='event_id: 0x12345',
            leave_msg='event_id: 0x12345'
        )(_test_trace_time_map)
        traced_test_trace_time_map(sleep_time=5)

    """
    def __init__(self, b_print_stdout=False, enter_msg='', leave_msg=''):
        """
        :param b_print_stdout:
            When b_print_stdout is True, tlib will print to both LOGFILE
            that passed to log.init_comlog and stdout

        :param enter_msg:
            entrance msg before invoking the function

        :param leave_msg:
            exist msg after leaving the function

        If you never use log.init_comlog, make sure b_print_stdout == True
        """
        self._b_print_stdout = b_print_stdout
        self._enter_msg = enter_msg
        self._leave_msg = leave_msg

    def __call__(self, function):
        @wraps(function)
        def _wrapper_log(*args, **kwargs):
            now = time.time()
            enter_msg = 'Enter func:{0},time:{1}, msg:{2}'.format(function.__name__, datetime_in.now(), self._enter_msg)
            if self._b_print_stdout:
                print(enter_msg)
            my_logger.info(enter_msg)

            function(*args, **kwargs)

            then = time.time()
            used_time = then - now
            exit_msg = 'Exit func:{0}, time:{1}, used_time:{2}, msg:{3}'.format(
                function.__name__, datetime_in.now(), used_time, self._leave_msg)
            my_logger.info(exit_msg)
            if self._b_print_stdout:
                print(exit_msg)
        return _wrapper_log


# Things below for unittest
@TraceUsedTime(False)
def _test_trace_time():
    """test trace time"""
    print('now, {0}, {1}'.format(time.time(), datetime_in.now()))
    time.sleep(3)
    print('then, {0}, {1}'.format(time.time(), datetime_in.now()))


@TraceUsedTime(True)
def _test_trace_time_log():
    print('now, {0}, {1}'.format(time.time(), datetime_in.now()))
    time.sleep(3)
    print('then, {0}, {1}'.format(time.time(), datetime_in.now()))


def _test_trace_time_map(sleep_time):
    print('ready to work')
    time.sleep(sleep_time)


def _test():
    _test_trace_time()
    _test_trace_time_log()
    func = TraceUsedTime(
        b_print_stdout=False,
        enter_msg='event_id: 0x12345',
        leave_msg='event_id: 0x12345'
    )(_test_trace_time_map)
    func(sleep_time=5)


if __name__ == '__main__':
    _test()

# vi:set tw=0 ts=4 sw=4 nowrap fdm=indent
