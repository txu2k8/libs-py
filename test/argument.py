# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""
argument for test modes
"""

import argparse
import unittest


# --- platform
platform_parser = argparse.ArgumentParser(add_help=False)
platform_parser.add_argument("--platform", required=True, action="store", dest="platform", default=None,
                             choices=['vshphere', 'aws'], help="platform,default:None")


def mail_parser():
    """
    vmware args
    :return:
    """
    arg_parser = argparse.ArgumentParser(add_help=False)
    mail_group = arg_parser.add_argument_group('MAIL arguments')
    mail_group.add_argument("--host", action="store", dest="host", default="smtp.gmail.com",
                            help="Mail server host,default:smtp.gmail.com")
    mail_group.add_argument("--user", action="store", dest="user", default=None,
                            help="Mail server user,default:None")
    mail_group.add_argument("--password", action="store", dest="password", default="password",
                            help="Mail server password,default:None")
    mail_group.add_argument("--port", action="store", dest="port", default=465,
                            help="Mail server port,default:465")
    mail_group.set_defaults(tls=True)

    return arg_parser


def tc_log_parsers(subparsers):
    """
    test case log subparsers
    :param subparsers:
    :return:
    """
    sub_parser = subparsers.add_parser('log', help='log.py test')

    sub_parser.add_argument("--case", action="store", dest="case_list", default=['all'],
                            nargs='+', help="default:['all']")
    sub_parser.set_defaults(func=test_suite_common, suite='log')


def tc_mail_parsers(subparsers):
    """
    test case mail subparsers
    :param subparsers:
    :return:
    """

    sub_parser = subparsers.add_parser('mail', parents=[mail_parser()], help='mail.py test')

    sub_parser.add_argument("--case", action="store", dest="case_list", default=['all'],
                            choices=['1', '2', '3'], nargs='+', help="default:['all']")
    sub_parser.set_defaults(func=test_suite_common, suite='mail')


def test_suite_common(args):
    if args.suite == 'log':
        from test.test_log import TestLog as CurrentTestCase
    elif args.suite == 'mail':
        from test.test_mail import TestMail as CurrentTestCase
    else:
        raise Exception('Error suite')

    if 'all' in args.case_list:
        test_suite = unittest.TestSuite()
        test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(CurrentTestCase))
    else:
        case_name_list = []
        for case in args.case_list:
            case_name = "test_" + case
            case_name_list.append(case_name)

        print("case_name_list:%s" % case_name_list)
        # Load the test suite
        test_suite = unittest.TestSuite(map(CurrentTestCase, case_name_list))
    return test_suite


# =============================
# set subparsers
# =============================
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
