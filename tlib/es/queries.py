# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/2/17 14:15
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""run some sample queries"""
import time

from tlib.es.elasticsearch_api import ESApi
from tlib import log


# =============================
# --- Global
# =============================
logger = log.get_logger()


class ESSearch(ESApi):
    """create an index with mappings and load all docs"""
    def __init__(self, ip_list, port, user=None, password=None):
        super(ESSearch, self).__init__(ip_list, port, user, password)
        pass

    def search_results(self, body, index_name_list, doc_type='doc'):
        for index_name in index_name_list:
            yield self.search(body, index_name, doc_type)

    @staticmethod
    def print_search_stats(results):
        logger.info("=" * 80)
        logger.info("Total %d found in %dms" % (results["hits"]["total"], results["took"]))
        logger.info("-" * 80)

    def print_hits(self, results):
        """
        Simple utility function to print results of a search query.
        :param results:
        :return:
        """
        self.print_search_stats(results)
        for hit in results["hits"]["hits"]:
            # get created date for a repo and fallback to authored_date for a commit
            ctime = hit["_source"].get("created_at", hit["_source"]["ctime"])
            created_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ctime/1000))
            logger.info(
                "/%s/%s/%s (%s): %s"
                % (
                    hit["_index"],
                    hit["_type"],
                    hit["_id"],
                    created_at,
                    hit["_source"]["name"].split("\n")[0],
                )
            )

        logger.info("=" * 80)


if __name__ == "__main__":
    from tlib.es.example_settings import SEARCH_BODY_1, SEARCH_BODY_2, SEARCH_BODY_3

    es = ESSearch('10.25.119.71', 30707, 'root', 'password')
    index_names = ['test-0', 'test-1', 'test-2']

    # logger.info("Empty search:")
    # for result in es.search_results(None, index_names):
    #     es.print_hits(result)
    #
    # logger.info('Find that match "uid=3" tests:')
    # for result in es.search_results(SEARCH_BODY_1, index_names):
    #     es.print_hits(result)
    #
    # logger.info('Find that "app_type=test Index & Search" sort tests:')
    # for result in es.search_results(SEARCH_BODY_2, index_names):
    #     es.print_hits(result)

    # print("Stats for top 10 committers:")
    # for result in es.search_results(SEARCH_BODY_3, index_names):
    #     es.print_search_stats(result)

    while True:
        for result in es.search_results(SEARCH_BODY_1, index_names):
            es.print_search_stats(result)
