# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""
:desc:
    Const variable for internal use. Use it when you know
    what this _const really means
"""

import sys


# =============================
# --- golabl value set/get
# =============================
_global_dict = {}


def set_value(key, value):
    global _global_dict
    _global_dict[key] = value


def get_value(key, default_value=None):
    try:
        global _global_dict
        return _global_dict[key]
    except KeyError:
        return default_value


class _Const(object):
    """
    internal const class
    """
    class ConstError(Exception):
        """
        const error
        """

        def __init__(self, msg):
            self._msg = 'TLIB const error:' + str(msg)

        def __str__(self):
            return repr(self._msg)

    def __setattr__(self, key, value):
        if not key.isupper():
            raise self.ConstError('Const value shoule be upper')
        if key in self.__dict__:
            raise self.ConstError('Const value cannot be changed')
        self.__dict__[key] = value


"""
you can access tlib const like below:
    from tlib import const
    print const.VERSION

"""

_const_obj = _Const()
_const_obj.VERSION = '1.1.0'
_const_obj.AUTHOR = 'tao.xu2008@outlook.com'

sys.modules[__name__] = _const_obj
