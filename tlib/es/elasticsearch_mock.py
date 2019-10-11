# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/11 14:05
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""Mock Elasticsearch"""

import sys
import string
import base64
from functools import wraps
import unittest
# from mock import patch

from elasticsearch.client.utils import query_params
from elasticsearch.client import _normalize_hosts
from elasticsearch.exceptions import NotFoundError

# TODO
DEFAULT_ELASTICSEARCH_ID_SIZE = 20
CHARSET_FOR_ELASTICSEARCH_ID = string.ascii_letters + string.digits
DEFAULT_ELASTICSEARCH_SEARCHRESULTPHASE_COUNT = 6
PY3 = sys.version_info[0] == 3
if PY3:
    unicode = str
ELASTIC_INSTANCES = {}


def get_random_id(size=DEFAULT_ELASTICSEARCH_ID_SIZE):
    return ''.join(random.choice(CHARSET_FOR_ELASTICSEARCH_ID) for _ in range(size))


def get_random_scroll_id(size=DEFAULT_ELASTICSEARCH_SEARCHRESULTPHASE_COUNT):
    return base64.b64encode(''.join(get_random_id() for _ in range(size)).encode())


def get_mock_elastic(hosts=None, *args, **kwargs):
    host = _normalize_hosts(hosts)[0]
    elastic_key = '{0}:{1}'.format(host.get('host', 'localhost'), host.get('port', 9200))

    if elastic_key in ELASTIC_INSTANCES:
        connection = ELASTIC_INSTANCES.get(elastic_key)
    else:
        connection = MockElasticsearch()
        ELASTIC_INSTANCES[elastic_key] = connection
    return connection


def mock_elastic(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        ELASTIC_INSTANCES.clear()
        with patch('elasticsearch.Elasticsearch', get_mock_elastic):
            result = f(*args, **kwargs)
        return result
    return decorated


class MockElasticsearch(Elasticsearch):
    __documents_dict = None

    def __init__(self, hosts=None, transport_class=None, **kwargs):
        super(MockElasticsearch, self).__init__()
        self.__documents_dict = {}
        self.__scrolls = {}

    @query_params()
    def ping(self, params=None):
        return True

    @query_params()
    def info(self, params=None):
        return {
            'status': 200,
            'cluster_name': 'elasticmock',
            'version':
                {
                    'lucene_version': '4.10.4',
                    'build_hash': '00f95f4ffca6de89d68b7ccaf80d148f1f70e4d4',
                    'number': '1.7.5',
                    'build_timestamp': '2016-02-02T09:55:30Z',
                    'build_snapshot': False
                },
            'name': 'Nightwatch',
            'tagline': 'You Know, for Search'
        }

    @query_params('consistency', 'op_type', 'parent', 'refresh', 'replication',
                  'routing', 'timeout', 'timestamp', 'ttl', 'version', 'version_type')
    def index(self, index, doc_type, body, id=None, params=None):
        if index not in self.__documents_dict:
            self.__documents_dict[index] = list()

        if id is None:
            id = get_random_id()

        version = 1

        self.__documents_dict[index].append({
            '_type': doc_type,
            '_id': id,
            '_source': body,
            '_index': index,
            '_version': version
        })

        return {
            '_type': doc_type,
            '_id': id,
            'created': True,
            '_version': version,
            '_index': index
        }

    @query_params('parent', 'preference', 'realtime', 'refresh', 'routing')
    def exists(self, index, doc_type, id, params=None):
        result = False
        if index in self.__documents_dict:
            for document in self.__documents_dict[index]:
                if document.get('_id') == id and document.get('_type') == doc_type:
                    result = True
                    break
        return result

    @query_params('_source', '_source_exclude', '_source_include', 'fields',
                  'parent', 'preference', 'realtime', 'refresh', 'routing', 'version',
                  'version_type')
    def get(self, index, id, doc_type='_all', params=None):
        result = None
        if index in self.__documents_dict:
            for document in self.__documents_dict[index]:
                if document.get('_id') == id:
                    if doc_type == '_all':
                        result = document
                        break
                    else:
                        if document.get('_type') == doc_type:
                            result = document
                            break

        if result:
            result['found'] = True
        else:
            error_data = {
                '_index': index,
                '_type': doc_type,
                '_id': id,
                'found': False
            }
            raise NotFoundError(404, json.dumps(error_data))

        return result

    @query_params('_source', '_source_exclude', '_source_include', 'parent',
                  'preference', 'realtime', 'refresh', 'routing', 'version',
                  'version_type')
    def get_source(self, index, doc_type, id, params=None):
        document = self.get(index=index, doc_type=doc_type, id=id, params=params)
        return document.get('_source')

    @query_params('_source', '_source_exclude', '_source_include',
                  'allow_no_indices', 'analyze_wildcard', 'analyzer', 'default_operator',
                  'df', 'expand_wildcards', 'explain', 'fielddata_fields', 'fields',
                  'from_', 'ignore_unavailable', 'lenient', 'lowercase_expanded_terms',
                  'preference', 'q', 'request_cache', 'routing', 'scroll', 'search_type',
                  'size', 'sort', 'stats', 'suggest_field', 'suggest_mode',
                  'suggest_size', 'suggest_text', 'terminate_after', 'timeout',
                  'track_scores', 'version')
    def count(self, index=None, doc_type=None, body=None, params=None):
        searchable_indexes = self._normalize_index_to_list(index)

        i = 0
        for searchable_index in searchable_indexes:
            for document in self.__documents_dict[searchable_index]:
                if doc_type is not None and document.get('_type') != doc_type:
                    continue
                i += 1
        result = {
            'count': i,
            '_shards': {
                'successful': 1,
                'failed': 0,
                'total': 1
            }
        }

        return result

    @query_params('_source', '_source_exclude', '_source_include',
                  'allow_no_indices', 'analyze_wildcard', 'analyzer', 'default_operator',
                  'df', 'expand_wildcards', 'explain', 'fielddata_fields', 'fields',
                  'from_', 'ignore_unavailable', 'lenient', 'lowercase_expanded_terms',
                  'preference', 'q', 'request_cache', 'routing', 'scroll', 'search_type',
                  'size', 'sort', 'stats', 'suggest_field', 'suggest_mode',
                  'suggest_size', 'suggest_text', 'terminate_after', 'timeout',
                  'track_scores', 'version')
    def search(self, index=None, doc_type=None, body=None, params=None):
        searchable_indexes = self._normalize_index_to_list(index)

        matches = []
        for searchable_index in searchable_indexes:
            for document in self.__documents_dict[searchable_index]:
                if doc_type:
                    if isinstance(doc_type, list) and document.get('_type') not in doc_type:
                        continue
                    if isinstance(doc_type, str) and document.get('_type') != doc_type:
                        continue
                matches.append(document)

        result = {
            'hits': {
                'total': len(matches),
                'max_score': 1.0
            },
            '_shards': {
                # Simulate indexes with 1 shard each
                'successful': len(searchable_indexes),
                'failed': 0,
                'total': len(searchable_indexes)
            },
            'took': 1,
            'timed_out': False
        }

        hits = []
        for match in matches:
            match['_score'] = 1.0
            hits.append(match)

        # build aggregations
        if body is not None and 'aggs' in body:
            aggregations = {}

            for aggregation, definition in body['aggs'].items():
                aggregations[aggregation] = {
                    "doc_count_error_upper_bound": 0,
                    "sum_other_doc_count": 0,
                    "buckets": []
                }

            if aggregations:
                result['aggregations'] = aggregations

        if 'scroll' in params:
            result['_scroll_id'] = str(get_random_scroll_id())
            params['size'] = int(params.get('size') if 'size' in params else 10)
            params['from'] = int(params.get('from') + params.get('size') if 'from' in params else 0)
            self.__scrolls[result.get('_scroll_id')] = {
                'index': index,
                'doc_type': doc_type,
                'body': body,
                'params': params
            }
            hits = hits[params.get('from'):params.get('from') + params.get('size')]

        result['hits']['hits'] = hits

        return result

    @query_params('scroll')
    def scroll(self, scroll_id, params=None):
        scroll = self.__scrolls.pop(scroll_id)
        result = self.search(
            index=scroll.get('index'),
            doc_type=scroll.get('doc_type'),
            body=scroll.get('body'),
            params=scroll.get('params')
        )
        return result

    @query_params('consistency', 'parent', 'refresh', 'replication', 'routing',
                  'timeout', 'version', 'version_type')
    def delete(self, index, doc_type, id, params=None):

        found = False

        if index in self.__documents_dict:
            for document in self.__documents_dict[index]:
                if document.get('_type') == doc_type and document.get('_id') == id:
                    found = True
                    self.__documents_dict[index].remove(document)
                    break

        result_dict = {
            'found': found,
            '_index': index,
            '_type': doc_type,
            '_id': id,
            '_version': 1,
        }

        if found:
            return result_dict
        else:
            raise NotFoundError(404, json.dumps(result_dict))

    @query_params('allow_no_indices', 'expand_wildcards', 'ignore_unavailable',
                  'preference', 'routing')
    def suggest(self, body, index=None, params=None):
        if index is not None and index not in self.__documents_dict:
            raise NotFoundError(404, 'IndexMissingException[[{0}] missing]'.format(index))

        result_dict = {}
        for key, value in body.items():
            text = value.get('text')
            suggestion = int(text) + 1 if isinstance(text, int) else '{0}_suggestion'.format(text)
            result_dict[key] = [
                {
                    'text': text,
                    'length': 1,
                    'options': [
                        {
                            'text': suggestion,
                            'freq': 1,
                            'score': 1.0
                        }
                    ],
                    'offset': 0
                }
            ]
        return result_dict

    def _normalize_index_to_list(self, index):
        # Ensure to have a list of index
        if index is None:
            searchable_indexes = self.__documents_dict.keys()
        elif isinstance(index, str) or isinstance(index, unicode):
            searchable_indexes = [index]
        elif isinstance(index, list):
            searchable_indexes = index
        else:
            # Is it the correct exception to use ?
            raise ValueError("Invalid param 'index'")

        # Check index(es) exists
        for searchable_index in searchable_indexes:
            if searchable_index not in self.__documents_dict:
                raise NotFoundError(404, 'IndexMissingException[[{0}] missing]'.format(searchable_index))

        return searchable_indexes


class TestMockElasticsearch(unittest.TestCase):
    @mock_elastic
    def setUp(self):
        # self.es = ElasticsearchObj('10.25.119.91', 'root', 'password', 9211, cafile='', no_verify=False)
        self.es = Elasticsearch(hosts=[{'host': 'localhost', 'port': 9200}])
        self.index_name = 'test_index'
        self.doc_type = 'doc-Type'
        self.body = {'string': 'content', 'id': 1}

    def test_should_create_fake_elasticsearch_instance(self):
        self.assertIsInstance(self.es, MockElasticsearch)

    def test_should_index_document(self):
        data = self.es.index(index=self.index_name, doc_type=self.doc_type, body=self.body)

        self.assertEqual(self.doc_type, data.get('_type'))
        self.assertTrue(data.get('created'))
        self.assertEqual(1, data.get('_version'))
        self.assertEqual(self.index_name, data.get('_index'))

    def test_should_raise_notfounderror_when_nonindexed_id_is_used(self):
        with self.assertRaises(NotFoundError):
            self.es.get(index=self.index_name, id='1')

    def test_should_get_document_with_id(self):
        data = self.es.index(index=self.index_name, doc_type=self.doc_type, body=self.body)

        document_id = data.get('_id')
        target_doc = self.es.get(index=self.index_name, id=document_id)

        expected = {
            '_type': self.doc_type,
            '_source': self.body,
            '_index': self.index_name,
            '_version': 1,
            'found': True,
            '_id': document_id
        }

        self.assertDictEqual(expected, target_doc)

    def test_should_get_document_with_id_and_doc_type(self):
        data = self.es.index(index=self.index_name, doc_type=self.doc_type, body=self.body)

        document_id = data.get('_id')
        target_doc = self.es.get(index=self.index_name, id=document_id, doc_type=self.doc_type)

        expected = {
            '_type': self.doc_type,
            '_source': self.body,
            '_index': self.index_name,
            '_version': 1,
            'found': True,
            '_id': document_id
        }

        self.assertDictEqual(expected, target_doc)

    def test_should_return_exists_false_if_nonindexed_id_is_used(self):
        self.assertFalse(self.es.exists(index=self.index_name, doc_type=self.doc_type, id=1))

    def test_should_return_exists_true_if_indexed_id_is_used(self):
        data = self.es.index(index=self.index_name, doc_type=self.doc_type, body=self.body)
        document_id = data.get('_id')
        self.assertTrue(self.es.exists(index=self.index_name, doc_type=self.doc_type, id=document_id))

    def test_should_return_true_when_ping(self):
        self.assertTrue(self.es.ping())

    def test_should_return_status_200_for_info(self):
        info = self.es.info()
        self.assertEqual(info.get('status'), 200)

    def test_should_get_only_document_source_with_id(self):
        data = self.es.index(index=self.index_name, doc_type=self.doc_type, body=self.body)

        document_id = data.get('_id')
        target_doc_source = self.es.get_source(index=self.index_name, doc_type=self.doc_type, id=document_id)

        self.assertEqual(target_doc_source, self.body)

    def test_should_raise_notfounderror_when_search_for_unexistent_index(self):
        with self.assertRaises(NotFoundError):
            self.es.search(index=self.index_name)

    def test_should_return_count_for_indexed_documents_on_index(self):
        index_quantity = 0
        for i in range(0, index_quantity):
            self.es.index(index='index_{0}'.format(i), doc_type=self.doc_type, body={'data': 'test_{0}'.format(i)})

        count = self.es.count()
        self.assertEqual(index_quantity, count.get('count'))

    def test_should_return_hits_hits_even_when_no_result(self):
        search = self.es.search()
        self.assertEqual(0, search.get('hits').get('total'))
        self.assertListEqual([], search.get('hits').get('hits'))

    def test_should_return_all_documents(self):
        index_quantity = 10
        for i in range(0, index_quantity):
            self.es.index(index='index_{0}'.format(i), doc_type=self.doc_type, body={'data': 'test_{0}'.format(i)})

        search = self.es.search()
        self.assertEqual(index_quantity, search.get('hits').get('total'))

    def test_should_return_only_indexed_documents_on_index(self):
        index_quantity = 2
        for i in range(0, index_quantity):
            self.es.index(index=self.index_name, doc_type=self.doc_type, body={'data': 'test_{0}'.format(i)})

        search = self.es.search(index=self.index_name)
        self.assertEqual(index_quantity, search.get('hits').get('total'))

    def test_should_return_only_indexed_documents_on_index_with_doc_type(self):
        index_quantity = 2
        for i in range(0, index_quantity):
            self.es.index(index=self.index_name, doc_type=self.doc_type, body={'data': 'test_{0}'.format(i)})
        self.es.index(index=self.index_name, doc_type='another-Doctype', body={'data': 'test'})

        search = self.es.search(index=self.index_name, doc_type=self.doc_type)
        self.assertEqual(index_quantity, search.get('hits').get('total'))

    def test_should_raise_exception_when_delete_nonindexed_document(self):
        with self.assertRaises(NotFoundError):
            self.es.delete(index=self.index_name, doc_type=self.doc_type, id=1)

    def test_should_delete_indexed_document(self):
        data = self.es.index(index=self.index_name, doc_type=self.doc_type, body=self.body)
        document_id = data.get('_id')
        search = self.es.search(index=self.index_name)
        self.assertEqual(1, search.get('hits').get('total'))
        delete_data = self.es.delete(index=self.index_name, doc_type=self.doc_type, id=document_id)
        search = self.es.search(index=self.index_name)
        self.assertEqual(0, search.get('hits').get('total'))
        self.assertDictEqual({
            'found': True,
            '_index': self.index_name,
            '_type': self.doc_type,
            '_id': document_id,
            '_version': 1,
        }, delete_data)

    @mock_elastic
    def test_should_return_same_elastic_instance_when_instantiate_more_than_one_instance_with_same_host(self):
        es1 = Elasticsearch(hosts=[{'host': 'localhost', 'port': 9200}])
        es2 = Elasticsearch(hosts=[{'host': 'localhost', 'port': 9200}])
        self.assertEqual(es1, es2)

    @mock_elastic
    def test_should_raise_notfounderror_when_nonindexed_id_is_used_for_suggest(self):
        with self.assertRaises(NotFoundError):
            self.es.suggest(body={}, index=self.index_name)

    @mock_elastic
    def test_should_return_suggestions(self):
        self.es.index(index=self.index_name, doc_type=self.doc_type, body=self.body)
        suggestion_body = {
            'suggestion-string': {
                'text': 'test_text',
                'term': {
                    'field': 'string'
                }
            },
            'suggestion-id': {
                'text': 1234567,
                'term': {
                    'field': 'id'
                }
            }
        }
        suggestion = self.es.suggest(body=suggestion_body, index=self.index_name)
        self.assertIsNotNone(suggestion)
        self.assertDictEqual({
            'suggestion-string': [
                {
                    'text': 'test_text',
                    'length': 1,
                    'options': [
                        {
                            'text': 'test_text_suggestion',
                            'freq': 1,
                            'score': 1.0
                        }
                    ],
                    'offset': 0
                }
            ],
            'suggestion-id': [
                {
                    'text': 1234567,
                    'length': 1,
                    'options': [
                        {
                            'text': 1234568,
                            'freq': 1,
                            'score': 1.0
                        }
                    ],
                    'offset': 0
                }
            ],
        }, suggestion)

    def test_should_search_in_multiple_indexes(self):
        self.es.index(index='groups', doc_type='groups', body={'budget': 1000})
        self.es.index(index='users', doc_type='users', body={'name': 'toto'})
        self.es.index(index='pcs', doc_type='pcs', body={'model': 'macbook'})

        result = self.es.search(index=['users', 'pcs'])
        self.assertEqual(2, result.get('hits').get('total'))

    def test_should_count_in_multiple_indexes(self):
        self.es.index(index='groups', doc_type='groups', body={'budget': 1000})
        self.es.index(index='users', doc_type='users', body={'name': 'toto'})
        self.es.index(index='pcs', doc_type='pcs', body={'model': 'macbook'})

        result = self.es.count(index=['users', 'pcs'])
        self.assertEqual(2, result.get('count'))

    def test_doc_type_can_be_list(self):
        doc_types = ['1_idx', '2_idx', '3_idx']
        count_per_doc_type = 3

        for doc_type in doc_types:
            for _ in range(count_per_doc_type):
                self.es.index(index=self.index_name, doc_type=doc_type, body={})

        result = self.es.search(doc_type=[doc_types[0]])
        self.assertEqual(count_per_doc_type, result.get('hits').get('total'))

        result = self.es.search(doc_type=doc_types[:2])
        self.assertEqual(count_per_doc_type * 2, result.get('hits').get('total'))

    def test_usage_of_aggregations(self):
        self.es.index(index='index', doc_type='document', body={'genre': 'rock'})

        body = {"aggs": {"genres": {"terms": {"field": "genre"}}}}
        result = self.es.search(index='index', body=body)

        self.assertTrue('aggregations' in result)

    def test_search_with_scroll_param(self):
        for _ in range(100):
            self.es.index(index='groups', doc_type='groups', body={'budget': 1000})

        result = self.es.search(index='groups', params={'scroll': '1m', 'size': 30})
        self.assertNotEqual(None, result.get('_scroll_id', None))
        self.assertEqual(30, len(result.get('hits').get('hits')))
        self.assertEqual(100, result.get('hits').get('total'))

    def test_scrolling(self):
        for _ in range(100):
            self.es.index(index='groups', doc_type='groups', body={'budget': 1000})

        result = self.es.search(index='groups', params={'scroll': '1m', 'size': 30})
        self.assertNotEqual(None, result.get('_scroll_id', None))
        self.assertEqual(30, len(result.get('hits').get('hits')))
        self.assertEqual(100, result.get('hits').get('total'))

        for _ in range(2):
            result = self.es.scroll(scroll_id=result.get('_scroll_id'), scroll='1m')
            self.assertNotEqual(None, result.get('_scroll_id', None))
            self.assertEqual(30, len(result.get('hits').get('hits')))
            self.assertEqual(100, result.get('hits').get('total'))

        result = self.es.scroll(scroll_id=result.get('_scroll_id'), scroll='1m')
        self.assertNotEqual(None, result.get('_scroll_id', None))
        self.assertEqual(10, len(result.get('hits').get('hits')))
        self.assertEqual(100, result.get('hits').get('total'))


if __name__ == '__main__':
    unittest.main()