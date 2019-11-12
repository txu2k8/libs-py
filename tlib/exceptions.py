# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""Define exceptions"""

__all__ = [
    'BaseTestException', 'DecoratorException', 'LoggerException',
    'ResException', 'NoSuchProcess', 'AccessDenied', 'NetException',
    'AsyncMsgError', 'ThreadTermException', 'LockFileError',
    'NotImplementedYet', 'ConfigError'
]


class BaseTestException(Exception):
    """
    base test Exception. All other test Exceptions will inherit this.
    """
    def __init__(self, msg):
        self._msg = 'TLIB:' + str(msg)

    def __str__(self):
        return repr(self._msg)


# ## Decorator Exceptions ####
class DecoratorException(BaseTestException):
    """
    DecoratorException
    """
    def __init__(self, msg):
        super(self.__class__, self).__init__(msg)


# ## Log related exceptions ####
class LoggerException(BaseTestException):
    """
    Exception for logging, especially for log
    """
    def __init__(self, msg):
        super(self.__class__, self).__init__(msg)


# ## Resouce related exceptions ####
class ResException(BaseTestException):
    """
    Resource releated Exception
    """
    def __init__(self, msg):
        BaseTestException.__init__(self, msg)


class NoSuchProcess(ResException):
    """
    No such Process Exception
    """
    def __init__(self, pid, str_process_name):
        ResException.__init__(self, 'NoSuchProcess, pid:{0}, proc_name:{1}'.format(pid, str_process_name))


class AccessDenied(ResException):
    """
    Access Denied
    """
    def __init__(self, str_resouce):
        ResException.__init__(self, 'Resouce access denied:{0}'.format(str_resouce))


# ## Net related exceptions ####
class NetException(BaseTestException):
    """
    Network releated Exception
    """
    def __init__(self, msg=''):
        BaseTestException.__init__(self, msg)


class AsyncMsgError(NetException):
    """
    net.async msg related Exception
    """
    def __init__(self, msg=''):
        NetException.__init__(self, msg)


# ## Shell related exceptions ####
class ShellException(BaseTestException):
    """
    Exception for shell
    """
    def __init__(self, msg=''):
        BaseTestException.__init__(self, msg)


class IOException(BaseTestException):
    """
    IO related exceptions inside test
    """
    def __init__(self, msg=''):
        BaseTestException.__init__(self, msg)


class NoSuchFileOrDir(IOException):
    """
    No such file or directory
    """
    def __init__(self, msg=''):
        IOException.__init__(self, msg)


class ThreadTermException(BaseTestException):
    """
    Thread termination error
    """
    def __init__(self, msg=''):
        BaseTestException.__init__(self, msg)


class NotInitialized(BaseTestException):
    """
    Not initialized yet
    """
    def __init__(self, msg=''):
        msg = 'Not initialized: %s' % msg
        BaseTestException.__init__(self, msg)


class LockFileError(BaseTestException):
    """
    LockFileError
    """
    def __init__(self, msg=''):
        msg = 'LockFileError: %s' % msg
        BaseTestException.__init__(self, msg)


class ExpectFailure(BaseTestException):
    """
    Expect failure for unittest
    """
    def __init__(self, expect, got):
        msg = 'expect failure, expect {0}, got {1}'.format(expect, got)
        BaseTestException.__init__(self, msg)


class NotImplementedYet(BaseTestException):
    """
    Not implemented yet
    """
    def __init__(self, msg=''):
        msg = 'The functionality is not implemented yet, {0}'.format(msg)
        BaseTestException.__init__(self, msg)


class ConfigError(BaseTestException):
    """
    ConfigError
    """
    def __init__(self, msg=''):
        msg = 'Configuration Error: {0}'.format(msg)
        BaseTestException.__init__(self, msg)