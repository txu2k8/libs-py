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
Test suite 1: TestCases for log.py
"""

import unittest

from tlib.stressrunner import StressRunner
from tlib import log


my_logger = log.get_logger()


class TestMail(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    def test_2(self):
        my_logger.log(21, 'test_2 Describe: Test Case for mail.py')
        my_logger.info('test_2 info')
        my_logger.debug('test_2 debug')
        my_logger.warning('test_2 warning')
        my_logger.error('test_2 error')
        my_logger.critical('test_2 critical')


if __name__ == '__main__':
    # Generate test suite
    test_suite = unittest.TestSuite(map(TestMail, ['test_2']))
    # test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLog))

    # output to a file

    runner = StressRunner(
        report_path='./report/',
        title='My unit test',
        description='This demonstrates the report output by StressRunner.',
        # logger=my_logger
    )
    runner.run(test_suite)
