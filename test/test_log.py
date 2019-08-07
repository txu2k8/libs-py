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

import logging
import unittest

from tlib.stressrunner import StressRunner
from tlib import log


my_logger = log.get_logger()


class TestLog(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    def test_1(self):
        my_logger.log(21, 'test_1 Describe: Test Case for log.py')
        log_file = "test_1.log"
        log.basic_config(log_file)
        logger = logging.getLogger(__name__)
        logger.info('test_1 start ...')
        logger.warning('test_1 hello,world')
        logger.debug('test_1 hello,world')
        logger.error('test_1 hello,world')
        logger.critical('test_1 hello,world')

    def test_2(self):
        my_logger.log(21, 'test_1 Describe: Test Case for log.py')
        my_logger.info('test_2 info')
        my_logger.debug('test_2 debug')
        my_logger.warning('test_2 warning')
        my_logger.error('test_2 error')
        my_logger.critical('test_2 critical')

    def test_3(self):
        logger = log.get_logger(logfile='test_3.log', logger_name='test3', debug=True, reset_logger=True)
        logger.info('test_3 start ...')
        logger.warning('test_3 hello,world')
        logger.debug('test_3 hello,world')
        logger.error('test_3 hello,world')
        logger.critical('test_3 hello,world')

    def test_4(self):
        logger = log.get_logger(logfile='test_4.log', logger_name='test4', reset_logger=True)
        logger.info('test_4 start ...')
        logger.warning('test_4 hello,world')
        logger.debug('test_4 hello,world')
        logger.error('test_4 hello,world')
        logger.critical('test_4 hello,world')
        logger.log(21, 'test_4 hello,world')

    def test_5(self):
        logger = log.get_logger(logger_name='test4')
        logger.info('test_5 start ...')
        logger.warning('test_5 hello,world')


if __name__ == '__main__':
    # Generate test suite
    test_suite = unittest.TestSuite()
    # test_suite = unittest.TestSuite(map(TestMail, ['test_2']))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLog))

    # output to a file

    runner = StressRunner(
        report_path='./report/',
        title='My unit test',
        description='This demonstrates the report output by StressRunner.',
        # logger=my_logger
    )
    runner.run(test_suite)
