# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/11 14:31
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com


import sys
import json
import superelasticsearch
from superelasticsearch import SuperElasticsearch
from elasticsearch import serializer, exceptions

from tlib import log
from tlib.retry import retry

if sys.version_info > (3, 0, 0):
    from imp import reload

    reload(sys)
else:
    reload(sys)
    sys.setdefaultencoding('utf-8')

# =============================
# --- Global
# =============================
logger = log.get_logger()
ES_CONN_TIMEOUT = 300
ES_OPERATION_TIMEOUT = '60m'

SEARCH_ENGINE_TYPE_MAP = {
    0: 'ElasticSearchClusterObj'
}

SEARCH_ENGINE_STATUS_MAP = {
    'ENABLED': 0,
    'DISABLED': 1
}

ES_CLUSTER_STATUS_MAP = {
    'NORMAL': 0,
    'MAINTAINING': 1,
    'REJECTED': 2,
    'SHUTDOWN': 3
}


class MyJSONSerializer(serializer.JSONSerializer):
    def default(self, data):
        if isinstance(data, set):
            return list(data)
        if isinstance(data, bytes):
            return str(data, encoding='utf-8')
        return serializer.JSONSerializer.default(self, data)


superelasticsearch.json = MyJSONSerializer()


class EsSuper(object):
    _conn = None
    target_index = None
    update_index_list = None

    def __init__(self, ip_list, port, user=None, password=None):
        self.ips = ip_list
        self.port = port
        self.user = user
        self.password = password

        assert self.conn

    def set_target_index(self, index_name):
        self.target_index = index_name

    def set_update_index_list(self, index_name_list):
        self.update_index_list = index_name_list

    @retry(tries=10, delay=30)
    def connect(self):
        try:
            logger.info('Connect ES {0}:{1},user:{2},pwd:{3}'.format(
                self.ips, self.port, self.user, self.password))
            if self.user and self.password:
                es_conn = SuperElasticsearch(
                    self.ips, port=self.port, maxsize=8,
                    http_auth=(self.user, self.password),
                    timeout=ES_CONN_TIMEOUT, serializer=MyJSONSerializer())
            else:
                es_conn = SuperElasticsearch(
                    self.ips, port=self.port, maxsize=8,
                    timeout=ES_CONN_TIMEOUT, serializer=MyJSONSerializer())
            if not es_conn.ping:
                raise Exception("client ping failed, cluster is not up!!!")
            return es_conn
        except Exception as e:
            logger.error("Failed to connect the search engine!")
            raise Exception(e)

    @property
    def conn(self):
        if self._conn is None or not self._conn.ping():
            self._conn = self.connect()
        return self._conn

    @property
    def ping(self):
        return self.conn.ping()

    @property
    def health(self):
        return self.ping and 'red' not in self.conn.cat.health().split()[3]

    @property
    def es_status(self):
        return self.conn.cat.health().split()[3]  # TODO if no indices

    @property
    def es_nodes(self):
        es_nodes = []
        for es_node_info in self.conn.cat.nodes().strip().split('\n'):
            es_nodes.append(es_node_info.split()[0])

        return es_nodes

    @property
    def es_indices_names(self):
        es_indices_names = []
        for es_indices in self.conn.cat.indices().strip().split('\n'):
            es_indices_info = es_indices.split()
            if len(es_indices_info) > 3:
                es_indices_names.append(es_indices_info[2])

        return es_indices_names

    def get_cat_index_info(self, index_name=None):
        cat_result_list = self.conn.cat.indices(index=index_name,
                                                v=True).split('\n')
        index_info = dict()
        if cat_result_list:
            if index_name is None:
                index_info = []
                for i in range(1, len(cat_result_list)):
                    index_info.append(dict(zip(cat_result_list[0].split(),
                                               cat_result_list[i].split())))
            else:
                index_info = dict(zip(cat_result_list[0].split(),
                                      cat_result_list[1].split()))

        return index_info

    def get_cluster_settings(self):
        response = self.conn.cluster.get_settings()

        return response

    def put_cluster_settings(self, body):
        logger.info('PUT Settings:{0}'.format(body))
        response = self.conn.cluster.put_settings(body=body)

        return response

    @property
    def cluster_allocation_explain(self):
        response = self.conn.cluster.allocation_explain()

        return response

    def cluster_state(self, index_name=None):
        response = self.conn.cluster.state(index=index_name)

        return response

    def create_index(self, index_name, index_settings=None):
        if self.is_index_exist(index_name):
            logger.info('{0} index exist!'.format(index_name))
            return True

        logger.info(
            "The target index {} does not exist, create it first".format(
                index_name))
        logger.info(
            "Start creating index {} {}".format(index_name, index_settings))
        try:
            rtn = self.conn.indices.create(index_name,
                                           index_settings)  # , timeout=ES_OPERATION_TIMEOUT
            logger.info("Create index {0} finished".format(index_name))
            return rtn
        except exceptions.TransportError as e:
            logger.warning(e)
            if 'exists' in e.info:
                return True
            raise e

    def create_template(self, template_name, index_settings):
        logger.info("Start creating template {} {}".format(template_name,
                                                           index_settings))
        try:
            return self.conn.indices.put_template(template_name,
                                                  index_settings,
                                                  master_timeout=ES_OPERATION_TIMEOUT)
        except exceptions.TransportError as e:
            logger.warning(e)
            if 'exists' in e.info:
                return True
            raise e

    def does_template_exist(self, template_name):
        return self.conn.indices.exists_template(template_name)

    def delete_index(self, index_name):
        return self.conn.indices.delete(index_name)

    def is_index_exist(self, index_name):
        return self.conn.indices.exists(index_name)

    def get_all_types(self, index_name):
        return self.conn.indices.get_mapping(index_name)[index_name][
            'mappings'].keys()

    def delete_doc_type(self, index_name, doc_type):
        return self.conn.delete_by_query(index_name,
                                         {"query": {"match_all": {}}},
                                         doc_type=doc_type,
                                         wait_for_completion=True,
                                         refresh=True)

    def delete_match_docs(self, index_name, doc_type, condition_dict_list):
        logger.info(
            "Delete docs where index_name: {}, doc_type: {} and conditions: {}".format(
                index_name, doc_type, json.dumps(condition_dict_list))
        )
        search_body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            condition_dict.get('type_', 'term'): {
                                condition_dict['key']: condition_dict['value']
                            }
                        } for condition_dict in condition_dict_list
                    ]
                }
            }
        }

        if doc_type:
            return self.conn.delete_by_query(index_name,
                                             search_body,
                                             doc_type=doc_type,
                                             wait_for_completion=True,
                                             refresh=True,
                                             conflicts='proceed')
        else:
            return self.conn.delete_by_query(index_name,
                                             search_body,
                                             wait_for_completion=True,
                                             refresh=True,
                                             conflicts='proceed')

    def index_doc(self, index_name, doc_type, doc_data_dict):
        return self.conn.index(
            index=index_name,
            doc_type=doc_type,
            body=doc_data_dict,
            timeout=ES_OPERATION_TIMEOUT
        )

    def create_doc(self, index_name, doc_type, doc_data_dict, id_):
        return self.conn.index(
            id=id_,
            index=index_name,
            doc_type=doc_type,
            body=doc_data_dict,
            timeout=ES_OPERATION_TIMEOUT
        )

    def bulk_create_docs(self, index_name, doc_data_dict_list,
                         max_bulk_size=20000, refresh=True):
        num = 0
        pre_num = 0
        bulk = None
        #         for doc_data_dict in generate_docs(docs_num):
        for doc_data_dict in doc_data_dict_list:
            num += 1
            if num % max_bulk_size == 1:
                bulk = self.conn.bulk_operation()

            bulk.index(
                index=index_name,
                doc_type='doc',
                body=doc_data_dict
            )

            if num % max_bulk_size == 0:
                logger.info(
                    "Start sending from items {} to {} to ElasticSearch Server".format(
                        pre_num, num))
                pre_num = num
                if bulk.execute(timeout=ES_OPERATION_TIMEOUT, refresh=refresh):
                    logger.info("Finished sending these items")
                else:
                    return False
        logger.info("Total file number: {}".format(num))
        if num != pre_num:
            logger.info(
                "Start sending from items {} to {} to ElasticSearch Server".format(
                    pre_num, num))
            rc = bulk.execute(timeout=ES_OPERATION_TIMEOUT, refresh=refresh)
            if rc:
                logger.info("Finished")
            return rc
        else:
            return False

    def bulk_update_docs(self, index_name, doc_type, doc_data_dict_list,
                         max_bulk_size=2000, refresh=True,
                         index_if_not_exist=True):
        num = 0
        pre_num = 0
        bulk = None
        for doc_data_dict in doc_data_dict_list:
            num += 1
            if num % max_bulk_size == 1:
                bulk = self.conn.bulk_operation()
            body = {
                "doc": doc_data_dict,
                "doc_as_upsert": True
            } if index_if_not_exist else {
                "doc": doc_data_dict
            }

            if 'to_delete' in doc_data_dict:
                bulk.delete(
                    id=doc_data_dict['id_'],
                    index=index_name,
                    doc_type='doc'
                )
            else:
                bulk.update(
                    id=doc_data_dict.pop("id_"),
                    index=index_name,
                    doc_type='doc',
                    body=body
                )

            if num % max_bulk_size == 0:
                logger.info(
                    "Start sending from items {} to {} to ElasticSearch Server".format(
                        pre_num, num))
                pre_num = num
                if bulk.execute(timeout=ES_OPERATION_TIMEOUT, refresh=refresh):
                    logger.info("Finished sending these items")
                else:
                    return False
        logger.info("Total file number: {}".format(num))
        if num != pre_num:
            logger.info(
                "Start sending from items {} to {} to ElasticSearch Server".format(
                    pre_num, num))
            rc = bulk.execute(timeout=ES_OPERATION_TIMEOUT, refresh=refresh)
            if rc:
                logger.info("Finished")
            return rc
        else:
            return False

    def refresh(self, index_name=None):
        return self.conn.indices.refresh(index_name)

    def flush(self, index_name=None, wait_if_ongoing=True):
        return self.conn.indices.flush(index=index_name,
                                       wait_if_ongoing=wait_if_ongoing)

    def thread_pool(self, thread_type=None):
        return self.conn.cat.thread_pool(thread_type).split("\n")

    @property
    def index_queue_num(self):
        queue_num = 0
        for node_bulk_thread_info in self.thread_pool(thread_type="bulk"):
            if node_bulk_thread_info:
                logger.info(node_bulk_thread_info)
                queue_num += int(node_bulk_thread_info.split()[3])
        return queue_num

    def delete_doc(self):
        pass

    def search(self, index=None, doc_type=None, body=None, scroll=None):
        if body is None:
            body = {"query": {"match_all": {}}, 'size': 15}

        rtn = self.conn.search(index=index, doc_type=doc_type, body=body,
                               scroll=scroll)
        logger.info('Search take times: {time}ms'.format(time=rtn['took']))
        logger.info('Search hits docs: {num}'.format(num=rtn['hits']['total']))

        return rtn

    def count(self, index=None, doc_type=None, body=None):
        return self.conn.count(index=index, doc_type=doc_type, body=body)

    def scroll(self, scroll_id, scroll='30m'):
        return self.conn.scroll(scroll_id=scroll_id, scroll=scroll)

    def put_cluster_setting(self, body):
        self.conn.cluster.put_settings(body)


if __name__ == "__main__":
    es_ips = ['10.25.119.7']
    es_port = 9200
    es_user = 'root'
    es_pwd = 'password'
    es_obj = EsSuper(es_ips, es_port, es_user, es_pwd)
    print(es_obj.es_status)
