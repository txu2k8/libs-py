# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/11 14:50
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""es index / search example body template"""

import random
import uuid
import string

from tlib.utils import util

# ===============
# Index
# ===============
DOC_TYPE = 'doc'
ANALYZER = 'test_analyzer'
INDEX_ANALYSIS_FOR_WILDCARD = {
    "analyzer": {
        ANALYZER: {
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
CREATE_INDEX_BODY = {
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
                    "analyzer": ANALYZER,
                    "search_analyzer": ANALYZER
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


def random_int(max_size, min_size=3):
    try:
        return random.randint(min_size, max_size)
    except Exception as e:
        print("Not supporting {0} as valid sizes!".format(max_size))
        raise e


# Generate a random string with length of 1 to provided param
def random_string(max_size):
    return ''.join(
        random.choice(string.ascii_letters + string.digits) for _ in
        range(random_int(max_size)))


def random_doc():
    doc = {
        "doc_c_time": util.get_current_time(),
        "cc_id": str(uuid.uuid4()),
        "cc_name": random_string(15),
        "tenant": random_string(5),
        "name": '{0}.{1}'.format(random_string(10),
                                 random_string(3)),
        "name_term": '{0}.{1}'.format(random_string(10),
                                      random_string(3)),
        "is_file": True,
        "path": random.choice(["", "/", "/dir", "/dir" + "{}".format(
            random.randint(1, 100))]),
        "last_used_time": util.get_current_time(),
        'file_system': random_string(5),
        "atime": util.get_current_time(),
        "mtime": util.get_current_time(),
        "ctime": util.get_current_time(),
        "size": random.randint(1, 1000000),
        "is_folder": False,
        "app_type": "test Index & Search",
        "uid": random.randint(0, 10),
        "denied": [],
        "app_id": str(uuid.uuid4()),
        "app_name": random_string(10),
        "gid": random.randint(0, 10),
        "doc_i_time": util.get_current_time(),
        "file_id": str(random.randint(11111111111111111111111111111111,
                                      99999911111111111111111111111111)),
        "file": random_string(20),
        "allowed": ["FULL"]
    }

    return doc


# ===============
# search
# ===============
SEARCH_BODY_1 = {
    "query": {
            "bool": {
                "must": {"match": {"uid": 3}},
                "must_not": {"term": {"file": "test_elasticsearch"}},
            }
    },
}
SEARCH_BODY_2 = {
    "query": {"term": {"app_type": "test Index & Search"}},
    "sort": [{"ctime": {"order": "desc"}}],
    "size": 8,
}
SEARCH_BODY_3 = {
    "size": 0,
    "aggs": {
        "committers": {
            "terms": {"field": "committer.name.keyword"},
            "aggs": {"line_stats": {"stats": {"field": "stats.lines"}}},
        }
    },
}