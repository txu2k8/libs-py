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
    """
    create an index with mappings and load all docs
    Override the docs_generator() method for customized docs contents
    """
    def __init__(self, ip_list, port, user=None, password=None):
        super(ESIndex, self).__init__(ip_list, port, user, password)
        pass

    @staticmethod
    def docs_generator(doc_count):
        """
        documents generator, This just an example
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
    def multi_delete_indices(self, index_list, name_start=None):
        pool = ThreadPoolExecutor(max_workers=100)
        futures = []
        for index in index_list:
            if name_start and not index.startswith(name_start):
                continue
            futures.append(pool.submit(self.delete_index, index))
        pool.shutdown()
        future_result = [future.result() for future in as_completed(futures)]
        result = False if False in future_result else True
        return result


if __name__ == "__main__":
    from tlib.es.example_settings import CREATE_INDEX_BODY

    es = ESIndex('10.25.119.71', 30707, 'root', 'password')
    index_names = es.multi_create_index('test', CREATE_INDEX_BODY, 3)
    es.multi_index_docs(index_names, doc_count=200000, bulk_size=2000, max_retries=300)
    es.is_index_green(index_names)
