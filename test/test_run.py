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
Test suites run
"""

import unittest
from tlib.stressrunner import StressRunner

from tlib import log
from test.test_1 import TestLog
from test.test_2 import TestMail


my_logger = log.get_logger(logfile='./test1/test_1.log', logger_name='test', debug=True, reset_logger=True)


if __name__ == '__main__':
    # Generate test suite
    # test_suite = unittest.TestSuite(map(TestLog, ['test_1']))
    test_suite = unittest.TestSuite()
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLog))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMail))

    # output to a file
    runner = StressRunner(
        report_path='./report/',
        title='My unit test',
        description='This demonstrates the report output by StressRunner.',
        logger=my_logger
    )
    runner.run(test_suite)
