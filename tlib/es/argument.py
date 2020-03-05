# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/11 14:17
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

import argparse
import unittest


def case_dict_to_string(case_dict, case_name_len=25):
    case_string = '  {0:<3} {1:<{2}}  {3}\n'.format(
        'NO.', 'CaseName', case_name_len, 'CaseDescription')
    for i, (k, v) in enumerate(case_dict.items()):
        case_string += '  {n:<3} {k:<{le}}  {v}\n'.format(
            n=i + 1, k=k, le=case_name_len, v=v)
    return case_string


class ElasticsearchParser(object):
    """ Elasticsearch related Parser """

    @property
    def base(self):
        """Elasticsearch base parser."""
        arg_parser = argparse.ArgumentParser(add_help=False)

        # Mandatory Parameters
        arg_group = arg_parser.add_argument_group('ES bsae Parameters.')
        arg_group.add_argument("--es_address", nargs='+', default=[],
                               help="The address of your cluster")
        arg_group.add_argument("--es_user", dest="es_user", default="root",
                               help="HTTP authentication Username")
        arg_group.add_argument("--es_pwd", dest="es_pwd", default="password",
                               help="HTTP authentication Password")
        arg_group.add_argument("--es_port", dest="es_port", type=int,
                               default=9211,
                               help="es port, default:9211)")
        return arg_parser

    @property
    def index(self):
        """Elasticsearch Index test parser."""
        arg_parser = self.base

        # Optional Parameters
        arg_group = arg_parser.add_argument_group('ES Index Parameters.')
        arg_group.add_argument("--index_name", action="store",
                               dest="index_name", default="pzindex",
                               help="base index name,default:pzindex")
        arg_group.add_argument("--indices", type=int, default=50,
                               help="Number of indices to write, default:50")
        arg_group.add_argument("--documents", type=int, default=100000,
                               help="Number of template documents that hold the same mapping, default:100000")
        arg_group.add_argument("--bulk-size", type=int, default=1000,
                               help="How many documents each bulk request should contain, default 1000")
        return arg_parser

    @property
    def stress(self):
        u"""Elasticsearch Index Stress test parser.
        """
        arg_parser = self.index

        arg_group = arg_parser.add_argument_group('Elasticsearch Stress Parameters')
        arg_group.add_argument("--clients", type=int, default=1,
                               help="Number of threads that send bulks to ES, default:1")
        arg_group.add_argument("--seconds", type=int, default=60,
                               help="How long should the test run. Note: it might take a bit longer, as sending of all bulks who's creation has been initiated is allowed")
        arg_group.add_argument("--number-of-shards", type=int, default=3,
                               help="How many shards per index, default:3")
        arg_group.add_argument("--number-of-replicas", type=int, default=1,
                               help="How many replicas per index, default 1")
        arg_group.add_argument("--max-fields-per-document", type=int, default=20,
                               help="The maximum number of fields each document template should hold,default:20")
        arg_group.add_argument("--max-size-per-field", type=int, default=20,
                               help="When populating the templates, the maximum length of the data each field would get, default:20")
        arg_group.add_argument("--cleanup",
                               action='store_true', dest="cleanup", default=False,
                               help="Delete the indices after completion")
        arg_group.add_argument("--stats-frequency", type=int, default=30,
                               help="How frequent to show the statistics, default:30")
        arg_group.add_argument("--not-green",
                               action="store_false", dest="green", default=True,
                               help="Script doesn't wait for the cluster to be green")
        arg_group.add_argument("--ca-file", dest="cafile", default="",
                               help="Path to Certificate file")
        arg_group.add_argument("--no-verify", action="store_true",
                               dest="no_verify", default=False,
                               help="No verify SSL certificates")

        return arg_parser


def tc_es_parsers(subparsers):
    """Elasticsearch Index/Stress test subcommand parser.

    Add parsers in Argument subparsers.
    @param subparsers Argument Parser had subparsers
    """

    es_parser = ElasticsearchParser()

    def tc_index(subparsers_1):
        case_info_dict = {
            'index': 'es index test'
        }
        case_info = case_dict_to_string(case_info_dict, 25)

        sub_parser_1 = subparsers_1.add_parser(
            'index',
            parents=[es_parser.index],
            epilog='Test Case List:\n{0}'.format(case_info),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            help='ES index args'
        )
        sub_parser_1.add_argument("--case", action="store", dest="case_list",
                                  default=['index'], nargs='+',
                                  choices=case_info_dict.keys(),
                                  help="default:['es_index]")
        sub_parser_1.set_defaults(suite='index')

    def tc_stress(subparsers_1):
        case_info_dict = {
            'stress': 'es index stress test',
            'cleanup': 'delete exist index'
        }
        case_info = case_dict_to_string(case_info_dict, 25)

        sub_parser_1 = subparsers_1.add_parser(
            'stress',
            parents=[es_parser.stress],
            epilog='Test Case List:\n{0}'.format(case_info),
            formatter_class=argparse.RawDescriptionHelpFormatter,
            help='ES index'
        )
        sub_parser_1.add_argument("--case", action="store", dest="case_list",
                                  default=['stress'], nargs='+',
                                  choices=case_info_dict.keys(),
                                  help="default:['es_stress]")
        sub_parser_1.set_defaults(suite='stress')

    sub_parser = subparsers.add_parser('es', help='ES index/stress')
    set_sub_parser = sub_parser.add_subparsers(help='ES index/stress')

    tc_index(set_sub_parser)
    tc_stress(set_sub_parser)

    sub_parser.set_defaults(func=test_suite_common)


def test_suite_common(args):
    if args.suite == 'stress':
        from tlib.es.test import ESIndexStressTestCase \
            as CurrentTestCase
    elif args.suite == 'index':
        from tlib.es.test import ESIndexTestCase \
            as CurrentTestCase
    else:
        raise Exception("Not support the test suite {0}".format(args.suite))

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
