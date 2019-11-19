# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/11 14:50
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

import datetime
import random
import uuid
import string
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from tlib.es.elasticsearch_super import EsSuper
from tlib.es.es_doc_setting import TEST_META_INDEX_SETTING
from tlib import log
from tlib.retry import retry
from tlib.utils import util

# =============================
# --- Global
# =============================
logger = log.get_logger()


class ElasticsearchIndex(EsSuper):
    """Elasticsearch Index Test"""

    def __init__(self, es_ips, username, password, port,
                 indices=1, documents=1, max_bulk_size=1, index_name='index'):
        super(ElasticsearchIndex, self).__init__(es_ips, port, username, password)
        self.es_ips = es_ips
        self.indices = indices
        self.documents = documents
        self.max_bulk_size = max_bulk_size
        self.index_name = index_name

    # Just to control the minimum value globally (though its not configurable)
    @staticmethod
    def generate_random_int(max_size, min_size=3):
        try:
            return random.randint(min_size, max_size)
        except Exception as e:
            print("Not supporting {0} as valid sizes!".format(max_size))
            raise e

    # Generate a random string with length of 1 to provided param
    def generate_random_string(self, max_size):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(self.generate_random_int(max_size)))

    def generate_doc(self):
        doc = {
            "doc_c_time": util.get_current_time(),
            "cc_id": str(uuid.uuid4()),
            "cc_name": self.generate_random_string(15),
            "tenant": self.generate_random_string(5),
            "name": '{0}.{1}'.format(self.generate_random_string(10), self.generate_random_string(3)),
            "name_term": '{0}.{1}'.format(self.generate_random_string(10), self.generate_random_string(3)),
            "is_file": True,
            "path": random.choice(["", "/", "/dir", "/dir" + "{}".format(random.randint(1, 100))]),
            "last_used_time": util.get_current_time(),
            'file_system': self.generate_random_string(5),
            "atime": util.get_current_time(),
            "mtime": util.get_current_time(),
            "ctime": util.get_current_time(),
            "size": random.randint(1, 1000000),
            "is_folder": False,
            "app_type": "test Index & Search",
            "uid": random.randint(0, 10),
            "denied": [],
            "app_id": str(uuid.uuid4()),
            "app_name": self.generate_random_string(10),
            "gid": random.randint(0, 10),
            "doc_i_time": util.get_current_time(),
            "file_id": str(random.randint(11111111111111111111111111111111, 99999911111111111111111111111111)),
            "file": self.generate_random_string(20),
            "allowed": ["FULL"]
        }

        return doc

    def generate_docs(self, docs_num):
        for _ in range(docs_num):
            yield self.generate_doc()

    # ---------------- index ----------------
    @util.print_for_call
    @retry(tries=120, delay=30)
    def is_index_green(self, index_name):
        index_info = self.get_cat_index_info(index_name=index_name)
        if len(self.es_nodes) > 2:
            if 'green' not in index_info['health']:
                logger.warning(json.dumps(index_info, indent=4))
                raise Exception('Index {target} exception occured(Not green)'.format(target=index_name))
        else:
            if 'yellow' not in index_info['health'] and 'green' not in index_info['health']:
                logger.warning(json.dumps(index_info, indent=4))

                cluster_allocation_explain = self.cluster_allocation_explain

                if 'index' in self.cluster_allocation_explain and cluster_allocation_explain['index'] == index_name:
                    logger.warning(cluster_allocation_explain['unassigned_info']['details'])

                raise Exception('Index {target} exception occured(Not green/yellow)'.format(target=index_name))

        logger.info(json.dumps(index_info, indent=4))
        return True

    @util.print_for_call
    def multi_create_indices(self, base_index_name, index_setting, indices_num):
        pool = ThreadPoolExecutor(max_workers=100)
        indices = []
        futures = []
        for i in range(indices_num):
            index_name = '{0}-{1}'.format(base_index_name, i)
            indices.append(index_name)
            futures.append(pool.submit(self.create_index, index_name, index_setting))
        pool.shutdown()

        future_result = [future.result() for future in as_completed(futures)]
        result = False if False in future_result else True
        assert result

        return indices

    @util.print_for_call
    def multi_index_docs(self, indices_name, doc_data_dict_list, max_bulk_size):
        pool = ThreadPoolExecutor(max_workers=100)
        futures = []
        for index_name in indices_name:
            futures.append(pool.submit(self.bulk_create_docs, index_name, doc_data_dict_list, max_bulk_size, False))
        pool.shutdown()

        future_result = [future.result() for future in as_completed(futures)]
        result = False if False in future_result else True
        return result

    @util.print_for_call
    def multi_refresh(self, indices_name):
        pool = ThreadPoolExecutor(max_workers=100)
        futures = []
        for index_name in indices_name:
            futures.append(pool.submit(self.refresh, index_name))
        pool.shutdown()

        future_result = [future.result() for future in as_completed(futures)]
        result = False if False in future_result else True
        return result

    @util.print_for_call
    def multi_flush(self, indices_name):
        pool = ThreadPoolExecutor(max_workers=100)
        futures = []
        for index_name in indices_name:
            futures.append(pool.submit(self.flush, index_name, True))
        pool.shutdown()

        future_result = [future.result() for future in as_completed(futures)]
        result = False if False in future_result else True
        return result

    @util.print_for_call
    @retry(tries=10, delay=300)
    def multi_index_random(self):
        """
        Elasticsearch index random directly
        :return:
        """

        # Basic configuration
        index_setting = TEST_META_INDEX_SETTING
        start_time = datetime.datetime.now()

        try:
            # 1.) Choose search engine
            indices_name = self.multi_create_indices(self.index_name, index_setting, self.indices)

            # 2.) Index - multi thread or not
            logger.info("Start creating docs")
            data_dict_list = list(self.generate_docs(self.documents))
            div_data_dict_lists = util.div_list_len(data_dict_list, self.max_bulk_size)
            for div_data_dict_list in div_data_dict_lists:
                self.multi_index_docs(indices_name, div_data_dict_list, self.max_bulk_size)

            # logger.info("Start refresh")
            # self.multi_refresh(indices_name)
            # logger.info("Finish refresh")
            # logger.info("Start flush")
            # self.multi_flush(indices_name)
            # logger.info("Finish flush")

            logger.info("Finish index")
            end_time = datetime.datetime.now()
            take_time = end_time - start_time
            logger.info('Take time: {time}'.format(time=take_time))
            logger.info('Index successfully')

        except Exception as e:
            raise Exception("Index failed, err:{0}".format(e))

        return indices_name


class ElasticsearchSearch(EsSuper):
    """Elasticsearch Search Test"""

    def __init__(self, es_ips, username, password, port,
                 indices=1, documents=1, max_bulk_size=1, index_name='index'):
        super(ElasticsearchSearch, self).__init__(es_ips, port, username,
                                                 password)
        self.es_ips = es_ips
        self.indices = indices
        self.documents = documents
        self.max_bulk_size = max_bulk_size
        self.index_name = index_name

    # Just to control the minimum value globally (though its not configurable)
    @staticmethod
    def generate_random_int(max_size, min_size=3):
        try:
            return random.randint(min_size, max_size)
        except Exception as e:
            print("Not supporting {0} as valid sizes!".format(max_size))
            raise e

    # Generate a random string with length of 1 to provided param
    def generate_random_string(self, max_size):
        return ''.join(
            random.choice(string.ascii_letters + string.digits) for _ in
            range(self.generate_random_int(max_size)))

    def generate_search_body(self):
        pattern = "*{str}*".format(str=self.generate_random_string(5))
        logger.info('Search file key: {name}'.format(name=pattern))

        body = {
            "query": {
                "bool": {
                    "must": {
                        "bool": {
                            "should": [
                                {
                                    "wildcard": {
                                        "file": {
                                            "wildcard": pattern
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        }

        return body

    def generate_search_bodys(self, bodys_num):
        for _ in range(bodys_num):
            yield self.generate_search_body()

    @util.print_for_call
    def multi_search(self, indices_name):
        pool = ThreadPoolExecutor(max_workers=100)
        futures = []
        for index_name in indices_name:
            futures.append(pool.submit(self.search, index_name, None, self.generate_search_body(), None))
        pool.shutdown()

        future_result = [future.result() for future in as_completed(futures)]
        result = False if False in future_result else True
        return result

