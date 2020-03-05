# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/2/17 14:15
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""
Create some index with mappings and load all the random docs into it.
"""


import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from tlib.es.elasticsearch_api import ESApi
from tlib import log
from tlib.retry import retry
from tlib.utils import util


# =============================
# --- Global
# =============================
logger = log.get_logger()


class ESIndex(ESApi):
    """create an index with mappings and load all docs"""
    def __init__(self, ip_list, port, user=None, password=None):
        super(ESIndex, self).__init__(ip_list, port, user, password)
        pass

    @staticmethod
    def docs_generator(doc_count):
        """
        documents generator
        :param doc_count:
        :return:
        """
        from tlib.es.example_settings import random_doc

        for _ in range(doc_count):
            yield random_doc()

    @util.print_for_call
    def multi_create_index(self, index_basename, index_setting, index_count):
        logger.info("Create index if not exist ...")
        pool = ThreadPoolExecutor(max_workers=100)
        indices = []
        futures = []
        for i in range(index_count):
            index_name = '{0}-{1}'.format(index_basename, i)
            indices.append(index_name)
            futures.append(
                pool.submit(self.create_index, index_name, index_setting))
        pool.shutdown()
        assert all([future.result() for future in as_completed(futures)])
        return indices

    @util.print_for_call
    def multi_index_docs(self, index_name_list, doc_count, bulk_size,
                         doc_type='doc', max_retries=3):
        pool = ThreadPoolExecutor(max_workers=100)
        futures = []
        for index_name in index_name_list:
            futures.append(
                pool.submit(self.bulk_actions,
                            index_name,
                            self.docs_generator(doc_count),
                            bulk_size, doc_type, max_retries))
        pool.shutdown()
        return all([future.result() for future in as_completed(futures)])

    @util.print_for_call
    @retry(tries=120, delay=30)
    def is_index_green(self, index_name):
        """
        get is the index list green
        :param index_name: A string or list of index names
        :return:
        """
        index_name_list = index_name if isinstance(index_name, list) else [index_name]
        for index_name in index_name_list:
            index_info = self.cat_indices(index_name=index_name)[0]
            if len(self.node_ips) > 2:
                if 'green' not in index_info['health']:
                    logger.warning(json.dumps(index_info, indent=4))
                    raise Exception('Index {0} exception occured(Not green)'.format(index_name))
            else:
                if 'yellow' not in index_info['health'] and 'green' not in \
                        index_info['health']:
                    logger.warning(json.dumps(index_info, indent=4))
                    cae = self.cluster_allocation_explain()
                    if 'index' in self.cluster_allocation_explain and \
                            cae['index'] == index_name:
                        logger.warning(cae['unassigned_info']['details'])
                    raise Exception('Index {0} exception occured(Not green/yellow)'.format(index_name))

        # logger.info(json.dumps(index_info, indent=4))
        return True


if __name__ == "__main__":
    from tlib.es.example_settings import CREATE_INDEX_BODY, random_doc

    es = ESIndex('10.25.119.71', 30707, 'root', 'password')
    index_names = es.multi_create_index('test', CREATE_INDEX_BODY, 3)
    es.multi_index_docs(index_names, doc_count=200000, bulk_size=2000, max_retries=300)
    es.is_index_green(index_names)
