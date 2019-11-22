# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/11/19 16:20
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

import unittest

from tlib.log import log
from tlib import const
from tlib.utils import util
from tlib.es.elasticsearch_index import ElasticsearchIndex
from tlib.es.elasticsearch_stress import ElasticsearchStress, ElasticsearchObj

# =============================
# --- Global
# =============================
logger = log.get_logger()
args = const.get_value('args')

# # Elasticsearch Stress Mandatory Parameters
# ES_ADDRESS = args.es_address
# ES_USERNAME = args.es_user
# ES_PASSWORD = args.es_pwd
# ES_PORT = args.es_port
#
# # Elasticsearch Stress/Index Optional Parameters
# NUMBER_OF_INDICES = args.indices
# NUMBER_OF_DOCUMENTS = args.documents
# INDEX_NAME = args.index_name
# BULK_SIZE = args.bulk_size

# =============== Elasticsearch Stress ===============
# Elasticsearch Stress Mandatory Parameters
ES_ADDRESS = args.es_address
ES_USERNAME = args.es_user
ES_PASSWORD = args.es_pwd
ES_PORT = args.es_port

# Elasticsearch Stress/Index Optional Parameters
NUMBER_OF_INDICES = args.indices
NUMBER_OF_DOCUMENTS = args.documents
INDEX_NAME = args.index_name
BULK_SIZE = args.bulk_size

# Elasticsearch Stress Optional Parameters
NUMBER_OF_CLIENTS = args.clients
NUMBER_OF_SECONDS = args.seconds
NUMBER_OF_SHARDS = args.number_of_shards
NUMBER_OF_REPLICAS = args.number_of_replicas
MAX_FIELDS_PER_DOCUMENT = args.max_fields_per_document
MAX_SIZE_PER_FIELD = args.max_size_per_field
CLEANUP = args.cleanup
STATS_FREQUENCY = args.stats_frequency
WAIT_FOR_GREEN = args.green
CA_FILE = args.cafile
NO_VERIFY_CERTS = args.no_verify


class ElasticsearchIndexTestCase(unittest.TestCase):
    """Elasticsearch Index Test Cases"""

    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    def test_index(self):
        """Elasticsearch index Test: multi-thread index"""
        logger.info(self.test_index.__doc__)
        es_index_obj = ElasticsearchIndex(
            ES_ADDRESS, ES_USERNAME, ES_PASSWORD, ES_PORT, NUMBER_OF_INDICES,
            NUMBER_OF_DOCUMENTS, BULK_SIZE, INDEX_NAME)
        indices_name = es_index_obj.multi_index_random()
        for index_name in indices_name:
            es_index_obj.is_index_green(index_name)
        logger.info("Sleep 600s after the iteration es index complete...")
        util.sleep_progressbar(600)


class ElasticsearchStressTestCase(unittest.TestCase):
    """
    Elasticsearch Stress unit test cases
    """

    def setUp(self):
        logger.info("Elasticsearch Stress Start ...")

    def tearDown(self):
        logger.info("Elasticsearch Stress Complete!")

    def test_stress(self):
        """Elasticsearch Stress Test"""
        logger.info(self.test_stress.__doc__)

        es_stress_obj = ElasticsearchStress(
            ES_ADDRESS, ES_USERNAME, ES_PASSWORD, ES_PORT, CA_FILE, NO_VERIFY_CERTS,
            NUMBER_OF_INDICES, NUMBER_OF_DOCUMENTS, NUMBER_OF_CLIENTS,
            NUMBER_OF_SECONDS, NUMBER_OF_SHARDS, NUMBER_OF_REPLICAS, BULK_SIZE,
            MAX_FIELDS_PER_DOCUMENT, MAX_SIZE_PER_FIELD, CLEANUP,
            STATS_FREQUENCY, WAIT_FOR_GREEN, index_name='es_stress')
        es_stress_obj.run()

    def test_cleanup(self):
        """cleanup exist index"""
        logger.info(self.test_cleanup.__doc__)
        es_obj = ElasticsearchObj(ES_ADDRESS[0], ES_USERNAME, ES_PASSWORD,
                                  ES_PORT, cafile="", no_verify=False)
        curr_indices = es_obj.es_indices_names
        if curr_indices:
            es_obj.multi_delete_indices(curr_indices, INDEX_NAME)
        util.sleep_progressbar(60)


if __name__ == '__main__':
    unittest.main()
