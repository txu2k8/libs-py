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
Some own/observed great lib/ideas,common useful python libs.
"""

import sys
from tlib import log
from tlib import decorators
from tlib import err

# from tlib import mail
# from tlib import shell
# from tlib import net
# from tlib import version
# from tlib import timeplus as time
# from tlib import timeplus
# from tlib import util
# from tlib import unittest
# from tlib import res
# from tlib.shell import oper
# from tlib import thirdp
from tlib import platforms

if sys.version_info < (2, 6):
    raise ImportError('tlib needs to be run on python 2.6 and above.')


# __all__ = [
#     'err', 'net', 'log', 'mail', 'shell', 'time',
#     'util', 'unittest', 'decorators', 'thirdp', 'platforms'
# ]
__all__ = [
    'err', 'log', 'decorators', 'platforms', 'shell'
]
