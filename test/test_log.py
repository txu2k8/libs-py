# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""
Test suite 1: TestCases for log.py
"""

import logging
import unittest

from tlib.stressrunner import StressRunner
from tlib import log


logger = log.get_logger()


class TestLog(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    def test_1(self):
        logger.log(21, 'test_1 Describe: Test Case for log.py')
        log_file = "test_1.log"
        log.basic_config(log_file)
        logger = logging.getLogger(__name__)
        logger.info('test_1 start ...')
        logger.warning('test_1 hello,world')
        logger.debug('test_1 hello,world')
        logger.error('test_1 hello,world')
        logger.critical('test_1 hello,world')

    def test_2(self):
        logger.log(21, 'test_1 Describe: Test Case for log.py')
        logger.info('test_2 info')
        logger.debug('test_2 debug')
        logger.warning('test_2 warning')
        logger.error('test_2 error')
        logger.critical('test_2 critical')

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
        # logger=logger
    )
    runner.run(test_suite)
