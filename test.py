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

import sys
import argparse
import unittest
from tlib.stressrunner import StressRunner
from tlib import log


my_logger = log.get_logger(logfile='./test1/test_1.log', logger_name='test', debug=True, reset_logger=True)


def parse_arg():
    """
    Set argument
    :return:
    """

    # Parent parser
    parser = argparse.ArgumentParser(description='Panzura Vizion Test Project')
    parser.add_argument("--debug", action="store_true", dest="debug", default=False,
                        help="debug mode,will not send email")
    parser.add_argument("--run_time", action="store", dest="run_time", default=60*60*24*3, type=int,
                        help="run time(s),default:60*60*24*3 (3 days)")
    parser.add_argument("--run_iteration", action="store", dest="run_iteration", default=0, type=int,
                        help="run_iteration(0:keep run forever),default:0")
    parser.add_argument("--sys_user", action="store", dest="sys_user", default="root", help="system user")
    parser.add_argument("--sys_pwd", action="store", dest="sys_pwd", default="password", help="system password")
    parser.add_argument("--key_file", action="store", dest="key_file", default=None, help="system login key_file")
    parser.add_argument("-m", action="store", dest="comment", default=None, help="test comment")
    parser.add_argument("--mail_to", action="store", dest="mail_to", default=None, help="mail_to, split with ';'")
    parser.set_defaults(runner='StressRunner', project='ut')
    # Sub parser
    subparsers = parser.add_subparsers(help='unit test')
    from test.argument import set_subparsers_project
    set_subparsers_project(subparsers)

    return parser.parse_args()


def main_1():
    """Main method
    """
    args = parse_arg()
    command = 'python ' + ' '.join(sys.argv)

    my_logger.info('Test args:\n{0}'.format(args))
    my_logger.info("Test command:\n{cmd}".format(cmd=command))

    # -----------------------------
    # --- Run unittest suite
    # -----------------------------
    if args.runner == 'TextTestRunner':
        # run with TextTestRunner
        from unittest import TextTestRunner
        runner = TextTestRunner(verbosity=2)
    else:
        # run with StressRunner -- report html
        # run with StressRunner -- report html
        runner = StressRunner(
            report_path='./report/',
            title='My unit test',
            description='This demonstrates the report output by StressRunner.',
            logger=my_logger
        )

    # get unittest test suite and then run unittest case
    test_suite = args.func(args)
    runner.run(test_suite)

    return True


def main_2():
    from test.test_log import TestLog
    from test.test_mail import TestMail

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


if __name__ == '__main__':
    main_1()
