# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/11 14:50
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""es doc template"""

DOC_TYPE = 'doc'
TEST_ANALYZER = 'test_analyzer'
INDEX_ANALYSIS_FOR_WILDCARD = {
    "analyzer": {
        TEST_ANALYZER: {
            "type": "custom",
            "tokenizer": "keyword",
            "filter": [
                "lowercase"
            ]
        }
    }
}
INDEX_SETTING = {
    "analysis": INDEX_ANALYSIS_FOR_WILDCARD,
    "index.indexing.slowlog.threshold.index.debug": "2s",
    "index.indexing.slowlog.threshold.index.info": "5s",
    "index.indexing.slowlog.threshold.index.trace": "500ms",
    "index.indexing.slowlog.threshold.index.warn": "10s",
    "index.merge.policy.max_merged_segment": "2gb",
    "index.merge.policy.segments_per_tier": "24",
    "index.number_of_replicas": "1",
    "index.number_of_shards": "3",
    "index.optimize_auto_generated_id": "true",
    "index.refresh_interval": "10s",
    "index.routing.allocation.total_shards_per_node": "-1",
    "index.search.slowlog.threshold.fetch.debug": "500ms",
    "index.search.slowlog.threshold.fetch.info": "800ms",
    "index.search.slowlog.threshold.fetch.trace": "200ms",
    "index.search.slowlog.threshold.fetch.warn": "1s",
    "index.search.slowlog.threshold.query.debug": "2s",
    "index.search.slowlog.threshold.query.info": "5s",
    "index.search.slowlog.threshold.query.trace": "500ms",
    "index.search.slowlog.threshold.query.warn": "10s",
    # "index.translog.durability": "async",
    # "index.translog.flush_threshold_size": "5000mb",
    # "index.translog.sync_interval": "30m",
    "index.unassigned.node_left.delayed_timeout": "7200m",
    # "index.mapping.total_fields.limit": 1000000,
    "index.translog.durability": "request",
}
TEST_META_INDEX_SETTING = {
    "settings": INDEX_SETTING,
    "mappings": {
        DOC_TYPE: {
            "properties": {
                "doc_c_time": {
                    "type": "keyword"
                },
                "doc_i_time": {
                    "type": "keyword"
                },
                "file": {
                    "type": "text",
                    "analyzer": TEST_ANALYZER,
                    "search_analyzer": TEST_ANALYZER
                },
                "file_term": {
                    "type": "keyword"
                },
                "is_file": {
                    "type": "boolean"
                },
                "is_folder": {
                    "type": "boolean"
                },
                "path": {
                    "type": "keyword"
                },
                "size": {
                    "type": "long"
                },
                "uid": {
                    "type": "keyword"
                },
                "gid": {
                    "type": "keyword"
                },
                "ctime": {
                    "type": "date",
                    "format": "epoch_second"
                },
                "mtime": {
                    "type": "date",
                    "format": "epoch_second"
                },
                "atime": {
                    "type": "date",
                    "format": "epoch_second"
                },
                'snapshot_id': {
                    "type": "keyword"
                },
                "cc_id": {
                    "type": "keyword"
                },
                "cc_name": {
                    "type": "keyword"
                },
                "tenant": {
                    "type": "keyword"
                },
                "last_used_time": {
                    "type": "date",
                    "format": "epoch_second"
                },
                "app_type": {
                    "type": "keyword"
                },
                "denied": {
                    "type": "keyword"
                },
                "app_id": {
                    "type": "keyword"
                },
                "app_name": {
                    "type": "keyword"
                },
                "file_id": {
                    "type": "keyword"
                },
                # "file": {
                #     "type": "keyword"
                # },
                "allowed": {
                    "type": "keyword"
                }
            }
        }
    }
}

