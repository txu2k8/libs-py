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
:argument for test modes
"""

import argparse
import unittest


# --- platform
platform_parser = argparse.ArgumentParser(add_help=False)
platform_parser.add_argument("--platform", required=True, action="store", dest="platform", default=None,
                             choices=['vshphere', 'aws'], help="platform,default:None")


def vmware_parser():
    """
    vmware args
    :return:
    """
    arg_parser = argparse.ArgumentParser(add_help=False)
    vmware_group = arg_parser.add_argument_group('VMWare arguments')
    vmware_group.add_argument("--vc_ip", action="store", dest="vc_ip", default=None, help="vcenter ip,default:None")
    vmware_group.add_argument("--vc_user", action="store", dest="vc_user", default=None,
                              help="vcenter user,default:None(const.py define)")
    vmware_group.add_argument("--vc_pwd", action="store", dest="vc_pwd", default=None,
                              help="vcenter pwd,default:None(const.py define)")

    return arg_parser


def tc_log_parsers(subparsers):
    """
    test case log subparsers
    :param subparsers:
    :return:
    """

    sub_parser = subparsers.add_parser('log', parents=[platform_parser, vmware_parser],
                                       help='')

    sub_parser.add_argument("--case", action="store", dest="case_list", default=['test_1'],
                            choices=['test_1', 'test_2'], nargs='+', help="default:['test_1']")
    sub_parser.set_defaults(func=test_suite_common, suite='log')


def tc_mail_parsers(subparsers):
    """
    test case mail subparsers
    :param subparsers:
    :return:
    """

    sub_parser = subparsers.add_parser('mail', parents=[platform_parser, vmware_parser],
                                       help='')

    sub_parser.add_argument("--case", action="store", dest="case_list", default=['test_1'],
                            choices=['test_1', 'test_2'], nargs='+', help="default:['test_1']")
    sub_parser.set_defaults(func=test_suite_common, suite='mail')


def test_suite_common(args):
    if args.suite == 'log':
        from test.test_log import TestLog as CurrentTestCase
    elif args.suite == 'mail':
        from test.test_mail import TestMail as CurrentTestCase
    else:
        raise Exception('Error suite')

    case_name_list = []
    for case in args.case_list:
        case_name = "test_" + case
        case_name_list.append(case_name)

    print("case_name_list:%s" % case_name_list)
    # Load the test suite
    test_suite = unittest.TestSuite(map(CurrentTestCase, case_name_list))
    # test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(CurrentTestCase))
    return test_suite


# =============================
# set subparsers
# =============================
def set_subparsers_project(sub_parser):
    """
    set subparsers
    :param sub_parser:
    :return:
    """

    suite_parser = sub_parser.add_parser('suite', help='sub command of log test')
    suite_parser.set_defaults(project='project')
    suite_sub_parser = suite_parser.add_subparsers(help='log test suite')
    set_subparsers_suite(suite_sub_parser)


def set_subparsers_suite(sub_parser):
    """
    set subparsers
    :param sub_parser:
    :return:
    """
    tc_log_parsers(sub_parser)
    tc_mail_parsers(sub_parser)


if __name__ == "__main__":
    pass
    parser = vmware_parser()
    p = parser.parse_args()
    print(p)
    print(p.__dict__)
    print('sys_user1' in p.__dict__)
