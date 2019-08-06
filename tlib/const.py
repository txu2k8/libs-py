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
:desc:
    Const variable for internal use. Use it when you know
    what this _const really means
"""

import sys


class _const(object):
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

_const_obj = _const()
_const_obj.VERSION = '1.1.0'
_const_obj.AUTHOR = 'tao.xu2008@outlook.com'

sys.modules[__name__] = _const_obj
