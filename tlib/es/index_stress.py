# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/11 14:02
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com


"""Elasticsearch Stress
FYI: https://github.com/logzio/elasticsearch-stress-test
"""

import random
import string
import time
import sys
import json
# import urllib3
import threading
from threading import Lock, Thread, Condition, Event
from concurrent.futures import ThreadPoolExecutor, as_completed

from elasticsearch import Elasticsearch
from elasticsearch.connection import create_ssl_context
from elasticsearch.exceptions import TransportError


from tlib import log
from tlib.retry import retry
from tlib.utils import util

# =============================
# --- Global
# =============================
logger = log.get_logger()
# urllib3.disable_warnings()

ES_CONN_TIMEOUT = 10800  # 180 min = 180 * 60 = 10800
ES_OPERATION_TIMEOUT = '180m'


class ElasticsearchObj(object):
    """ElasticsearchObj"""
    _conn = None

    def __init__(self, esaddress, username, password, port, cafile, no_verify):
        super(ElasticsearchObj, self).__init__()
        self.esaddress = esaddress
        self.username = username
        self.password = password
        self.port = port
        self.cafile = cafile
        self.no_verify = no_verify

    @retry(tries=5, delay=3)
    def connect(self):
        """
        Initiate the elasticsearch session, We increase the timeout here from the default value (10 seconds)
        to ensure we wait for requests to finish even if the cluster is overwhelmed and
        it takes a bit longer to process one bulk.
        :return:
        """
        try:
            logger.info(
                "Connect to ES({0},{1},{2},{3})...".format(self.esaddress, self.username, self.password, self.port))
            context = create_ssl_context(cafile=self.cafile) if self.cafile else ''
            auth = (self.username, self.password) if self.username and self.password else ()
            es_conn = Elasticsearch(self.esaddress, http_auth=auth, verify_certs=(not self.no_verify),
                                    ssl_context=context, port=self.port, timeout=ES_CONN_TIMEOUT)
            return es_conn
        except Exception as e:
            raise Exception("Failed:Connect to ES!\n{0}".format(e))

    @property
    def conn(self):
        if self._conn is None:
            self._conn = self.connect()

        return self._conn

    def get_cat_index_info(self, index_name=None):
        cat_result_list = self.conn.cat.indices(index=index_name, v=True).split('\n')
        index_info = dict()
        if cat_result_list:
            if index_name is None:
                index_info = []
                for i in range(1, len(cat_result_list)):
                    index_info.append(dict(zip(cat_result_list[0].split(), cat_result_list[i].split())))
            else:
                index_info = dict(zip(cat_result_list[0].split(), cat_result_list[1].split()))

        return index_info

    @property
    def es_indices_names(self):
        # return [es_indices.split()[2] for es_indices in self.conn.cat.indices().strip().split('\n')]
        es_indices_names = []
        for es_indices in self.conn.cat.indices().strip().split('\n'):
            es_indices_info = es_indices.split()
            if len(es_indices_info) > 3:
                es_indices_names.append(es_indices_info[2])

        return es_indices_names

    @retry(tries=3, delay=3, jitter=1, raise_exception=False)
    def delete_indices(self, index):
        """
        delete index from indices
        :param index:
        :return:
        """
        try:
            logger.info("Delete indices:{0} ...".format(index))
            self.conn.indices.delete(index=index, ignore=[400, 404])
            return True
        except Exception as e:
            raise Exception("Failed:delete index {0}. Continue anyway..\n{1}".format(index, e))

    @retry(tries=20, delay=3, jitter=1)
    def create_indices(self, index, shards, replicas):
        try:
            # And create it in ES with the shard count and replicas
            logger.info("Create indices:index={0},shards={1}, replicas={2} ...".format(index, shards, replicas))
            self.conn.indices.create(index=index, body={"settings": {"number_of_shards": shards,
                                                                     "number_of_replicas": replicas}})
            return True
        except TransportError as e:
            if 'exists' in e.error:
                logger.warning(e)
                return True
            raise Exception("Failed:Create index!\n{0}".format(e))

    def multi_delete_indices(self, index_list, name_start=None):
        pool = ThreadPoolExecutor(max_workers=100)
        futures = []
        for index in index_list:
            if name_start and not index.startswith(name_start):
                continue
            futures.append(pool.submit(self.delete_indices, index))
        pool.shutdown()
        future_result = [future.result() for future in as_completed(futures)]
        result = False if False in future_result else True
        return result

    def multi_create_indices(self, index_list, shards, replicas):
        pool = ThreadPoolExecutor(max_workers=100)
        futures = []
        for index in index_list:
            futures.append(pool.submit(self.create_indices, index, shards, replicas))
        pool.shutdown()
        future_result = [future.result() for future in as_completed(futures)]
        result = False if False in future_result else True
        return result

    @retry(tries=30, delay=10)
    def wait_for_green(self):
        try:
            self.conn.cluster.health(wait_for_status='green', master_timeout='600s', timeout='600s')
            return True
        except Exception as e:
            raise Exception(e)


class ESIndexStress(ElasticsearchObj):
    """
    Elasticsearch Stress
    FYI: https://github.com/logzio/elasticsearch-stress-test
    """

    def __init__(self, esaddress, username, password, port, cafile, no_verify, indices, documents, clients, seconds,
                 number_of_shards, number_of_replicas, bulk_size, max_fields_per_document, max_size_per_field, cleanup,
                 stats_frequency, green, index_name=None):
        super(ESIndexStress, self).__init__(esaddress, username, password, port, cafile, no_verify)
        self.esaddress = esaddress
        self.indices = indices
        self.documents = documents
        self.clients = clients
        self.seconds = seconds
        self.number_of_shards = number_of_shards
        self.number_of_replicas = number_of_replicas
        self.bulk_size = bulk_size
        self.max_fields_per_document = max_fields_per_document
        self.max_size_per_field = max_size_per_field
        self.cleanup = cleanup  # cleanup index after test complete, if True
        self.stats_frequency = stats_frequency
        self.green = green
        self.index_name = index_name

        # Placeholders
        self.start_timestamp = 0
        self.success_bulks = 0
        self.failed_bulks = 0
        self.total_size = 0

        # Thread safe
        self.success_lock = Lock()
        self.fail_lock = Lock()
        self.size_lock = Lock()
        self.shutdown_event = Event()

    # Helper functions
    def increment_success(self):
        # First, lock
        self.success_lock.acquire()
        try:
            self.success_bulks += 1
        finally:  # Just in case
            # Release the lock
            self.success_lock.release()

    def increment_failure(self):
        # First, lock
        self.fail_lock.acquire()
        try:
            self.failed_bulks += 1
        finally:  # Just in case
            # Release the lock
            self.fail_lock.release()

    def increment_size(self, size):
        # First, lock
        self.size_lock.acquire()
        try:
            self.total_size += size
        finally:  # Just in case
            # Release the lock
            self.size_lock.release()

    def has_timeout(self, start_timestamp):
        # Match to the timestamp
        if (start_timestamp + self.seconds) > int(time.time()):
            return False
        return True

    # Just to control the minimum value globally (though its not configurable)
    @staticmethod
    def generate_random_int(max_size):
        try:
            return random.randint(1, max_size)
        except Exception as e:
            print("Not supporting {0} as valid sizes!".format(max_size))
            raise e

    # Generate a random string with length of 1 to provided param
    def generate_random_string(self, max_size):
        return ''.join(random.choice(string.ascii_lowercase) for _ in range(self.generate_random_int(max_size)))

    # Create a document template
    def generate_document(self):
        temp_doc = {}

        # Iterate over the max fields
        for _ in range(self.generate_random_int(self.max_fields_per_document)):
            # Generate a field, with random content
            temp_doc[self.generate_random_string(10)] = self.generate_random_string(self.max_size_per_field)

        # Return the created document
        return temp_doc

    def fill_documents(self, documents_templates):
        """
        fill document with random string from template
        :param documents_templates:
        :return:
        """
        document_list = []
        # Generating 10 random subsets
        for _ in range(10):
            # Get a temp document
            random_doc = random.choice(documents_templates)

            # Populate the fields
            temp_doc = {}
            for field in random_doc:
                temp_doc[field] = self.generate_random_string(self.max_size_per_field)
            document_list.append(temp_doc)
        return document_list

    def client_worker(self, indices, document_list):
        # Running until timeout
        thread_id = threading.current_thread()
        logger.info("Perform the bulk operation, bulk_size:{0} ({1})...".format(self.bulk_size, thread_id))
        while (not self.has_timeout(self.start_timestamp)) and (not self.shutdown_event.is_set()):
            curr_bulk = ""
            # Iterate over the bulk size
            for _ in range(self.bulk_size):
                # Generate the bulk operation
                curr_bulk += "{0}\n".format(json.dumps({"index": {"_index": random.choice(indices),
                                                                  "_type": "stresstest"}}))
                curr_bulk += "{0}\n".format(json.dumps(random.choice(document_list)))
            try:
                # Perform the bulk operation
                self.conn.bulk(body=curr_bulk, timeout=ES_OPERATION_TIMEOUT)
                # Adding to success bulks
                self.increment_success()
                # Adding to size (in bytes)
                self.increment_size(sys.getsizeof(str(curr_bulk)))
            except Exception as e:
                # Failed. incrementing failure
                self.increment_failure()
                logger.error(e)

    def generate_clients(self, indices, document_list):
        # Clients placeholder
        temp_clients = []
        # Iterate over the clients count
        for _ in range(self.clients):
            temp_thread = Thread(target=self.client_worker, args=[indices, document_list])
            temp_thread.daemon = True
            # Create a thread and push it to the list
            temp_clients.append(temp_thread)
        # Return the clients
        return temp_clients

    def generate_documents(self):
        # Documents placeholder
        temp_documents = []

        # Iterate over the clients count
        for _ in range(self.documents):
            # Create a document and push it to the list
            temp_documents.append(self.generate_document())

        # Return the documents
        return temp_documents

    def generate_indices(self):
        # Placeholder
        temp_indices = []

        # Iterate over the indices count
        for x in range(self.indices):
            # Generate the index name
            temp_index = '{0}_{1}'.format(self.index_name, x) if self.index_name else self.generate_random_string(16)
            temp_indices.append(temp_index)

        self.multi_create_indices(temp_indices, self.number_of_shards, self.number_of_replicas)
        return temp_indices

    def print_stats(self):
        # Calculate elpased time
        elapsed_time = (int(time.time()) - self.start_timestamp)

        # Calculate size in MB
        size_mb = self.total_size / 1024 / 1024

        # Protect division by zero
        if elapsed_time == 0:
            mbs = 0
        else:
            mbs = size_mb / float(elapsed_time)

        # Print stats to the user
        logger.info("Elapsed time: {0} seconds".format(elapsed_time))
        logger.info("Successful bulks: {0} ({1} documents)".format(self.success_bulks, (self.success_bulks * self.bulk_size)))
        logger.info("Failed bulks: {0} ({1} documents)".format(self.failed_bulks, (self.failed_bulks * self.bulk_size)))
        logger.info("Indexed approximately {0} MB which is {1:.2f} MB/s".format(size_mb, mbs))
        logger.info("")

    def print_stats_worker(self):
        # Create a conditional lock to be used instead of sleep (prevent dead locks)
        lock = Condition()

        # Acquire it
        lock.acquire()

        # Print the stats every STATS_FREQUENCY seconds
        while (not self.has_timeout(self.start_timestamp)) and (not self.shutdown_event.is_set()):

            # Wait for timeout
            lock.wait(self.stats_frequency)

            # To avoid double printing
            if not self.has_timeout(self.start_timestamp):
                # Print stats
                self.print_stats()

    def run(self):
        clients = []
        all_indices = []

        # Set the timestamp
        self.start_timestamp = int(time.time())

        logger.info("")
        logger.info("Starting initialization of {0} ...".format(self.esaddress))
        logger.info("Generate docs ...")
        documents_templates = self.generate_documents()
        document_list = self.fill_documents(documents_templates)
        logger.info("Done!")

        logger.info("Creating indices.. ")
        indices = self.generate_indices()
        all_indices.extend(indices)
        logger.info("Done!")

        if self.green:
            logger.info('Check es cluster health ...')
            self.wait_for_green()
            logger.info("Done!")

        logger.info("Generating documents and workers.. ")  # Generate the clients
        clients.extend(self.generate_clients(indices, document_list))
        logger.info("Done!")

        logger.info("Starting the test. Will print stats every {0} seconds.".format(self.stats_frequency))
        logger.info("The test would run for {0} seconds, but it might take a bit more "
                       "because we are waiting for current bulk operation to complete.".format(self.seconds))

        original_active_count = threading.active_count()

        # Run the clients!
        for d in clients:
            d.start()
        # Create and start the print stats thread
        stats_thread = Thread(target=self.print_stats_worker)
        stats_thread.daemon = True
        stats_thread.start()

        for c in clients:
            while c.is_alive():
                try:
                    c.join(timeout=0.1)
                except KeyboardInterrupt:
                    logger.info("")
                    logger.info("Ctrl-c received! Sending kill to threads...")
                    self.shutdown_event.set()

                    # set loop flag true to get into loop
                    flag = True
                    while flag:
                        # sleep 2 secs that we don't loop to often
                        time.sleep(2)
                        '''
                        # set loop flag to false. If there is no thread still alive it will stay false
                        flag = False
                        # loop through each running thread and check if it is alive
                        for t in threading.enumerate():
                            # if one single thread is still alive repeat the loop
                            if t.isAlive():
                                flag = True
                        '''
                        # wait the bulk threads complete!
                        bulk_active_count = threading.active_count() - original_active_count
                        if bulk_active_count > 0:
                            print('bulk_active_count: {0}'.format(bulk_active_count))
                            flag = True
                        else:
                            flag = False

                    if self.cleanup:
                        logger.info("Cleaning up created indices.. ")
                        self.multi_delete_indices(all_indices)

        logger.info('')
        logger.info("Test is done! Final results:")
        self.print_stats()

        if self.cleanup:
            logger.info("Cleaning up created indices.. ")
            self.multi_delete_indices(all_indices)
            logger.info("Done!")
