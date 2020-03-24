# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/2/11 18:25
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""Elasticsearch API
FYI: https://elasticsearch-py.readthedocs.io/en/master/api.html
"""

import sys
import json
from functools import wraps
from elasticsearch import Elasticsearch
from elasticsearch import ElasticsearchException
from elasticsearch.helpers import streaming_bulk
from elasticsearch.serializer import JSONSerializer

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
ES_CONN_TIMEOUT = 36000
ES_OPERATION_TIMEOUT = '60m'


# print the func Enter/Output info
def print_for_call(func):
    """
    Enter <func>.
    Exit from <func>. result: "rtn"
    """

    @wraps(func)
    def _wrapped(*args, **kwargs):
        logger.info('Enter {name}.'.format(name=func.__name__))
        rtn = func(*args, **kwargs)
        logger.info('Exit from {name}. result: {rtn_code}'.format(
            name=func.__name__, rtn_code=rtn))
        return rtn

    return _wrapped


class CustomerJSONSerializer(JSONSerializer):
    def default(self, data):
        if isinstance(data, set):
            return list(data)
        if isinstance(data, bytes):
            return str(data, encoding='utf-8')
        return JSONSerializer.default(self, data)


class ESApi(object):
    _conn = None

    def __init__(self, ip_list, port, user=None, password=None):
        self.ips = ip_list
        self.port = port
        self.user = user
        self.password = password

    @retry(tries=10, delay=30)
    def connect(self):
        try:
            logger.info('Connect ES {0}:{1},user:{2},pwd:{3}'.format(
                self.ips, self.port, self.user, self.password))
            if self.user and self.password:
                es_conn = Elasticsearch(
                    self.ips, port=self.port, maxsize=8,
                    http_auth=(self.user, self.password),
                    timeout=ES_CONN_TIMEOUT,
                    serializer=CustomerJSONSerializer())
            else:
                es_conn = Elasticsearch(
                    self.ips, port=self.port, maxsize=8,
                    timeout=ES_CONN_TIMEOUT,
                    serializer=CustomerJSONSerializer())
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

    # ===============
    # Elasticsearch
    # class elasticsearch.Elasticsearch
    # ===============
    def get_cluster_info(self):
        """
        Returns basic information about the cluster.
        :return:
        """
        return self.conn.info()

    def is_doc_exists(self, index_name, doc_id, doc_type=None):
        """
        Returns information about whether a document exists in an index.
        :param index_name: The name of the index
        :param doc_id: The document ID
        :param doc_type: The type of the document (use `_all` to fetch the
            first document matching the ID across all types)
        :return:
        """
        return self.conn.exists(index_name, doc_id, doc_type)

    def get_doc(self, index_name, doc_id, doc_type=None):
        """
        Returns a document.
        :param index_name: The name of the index
        :param doc_id: The document ID
        :param doc_type: The type of the document (use `_all` to fetch the
            first document matching the ID across all types)
        :return:
        """
        return self.conn.get(index_name, doc_id, doc_type)

    def get_doc_count(self, body=None, index=None, doc_type=None):
        """
        Returns number of documents matching a query.
        :param body: A query to restrict the results specified with the
            Query DSL (optional)
        :param index: A comma-separated list of indices to restrict the
            results
        :param doc_type: A comma-separated list of types to restrict the
            results
        :return:
        """
        return self.conn.count(body, index, doc_type)

    def create_doc(self, index_name, doc_id, body, doc_type=None):
        """
        Creates a new document in the index.  Returns a 409 response when
        a document with a same ID already exists in the index.
        :param index_name: The name of the index
        :param doc_id: Document ID
        :param body: The document
        :param doc_type: The type of the document
        :return:
        """
        return self.conn.create(index_name, doc_id, body, doc_type)

    def delete_doc(self, index_name, doc_id, doc_type=None):
        """
        Removes a document from the index.
        :param index_name: he name of the index
        :param doc_id: The document ID
        :param doc_type: The type of the document
        :return:
        """
        return self.conn.delete(index_name, doc_id, doc_type)

    def index_doc(self, index_name, body, doc_type=None, doc_id=None):
        """
        Creates or updates a document in an index.
        :param index_name: The name of the index
        :param body: The document
        :param doc_type: The type of the document
        :param doc_id: Document ID
        :return:
        """
        return self.conn.index(index_name, body, doc_type, doc_id)

    def bulk(self, body, index=None, doc_type=None):
        """
        Allows to perform multiple index/update/delete operations in
        a single request.
        :param body: The operation definition and data (action-data
            pairs), separated by newlines
        :param index: Default index for items which don't provide one
        :param doc_type: Default document type for items which don't
            provide one
        :return:
        """
        return self.conn.bulk(body, index, doc_type)

    def bulk_actions(self, index_name, actions, bulk_size=500, doc_type='doc',
                     max_retries=3, **kwargs):
        """
        Streaming bulk consumes actions from the iterable passed in and
        yields results per action.
        :param index_name: Default index for items which don't provide one
        :param actions: iterable containing the actions to be executed
        :param bulk_size: number of docs in one chunk sent to es (default: 500)
        :param doc_type:
        :param max_retries: maximum number of times a document will be retried
        when ``429`` is received, set to 0 (default) for no retries on ``429``
        :param kwargs:
        :return:
        """
        num = 0
        pre_num = 0
        for ok, info in streaming_bulk(
            self.conn,
            actions,
            index=index_name,
            chunk_size=bulk_size,
            doc_type=doc_type,
            max_retries=max_retries,
            refresh='true',
            **kwargs
        ):
            action, result = info.popitem()
            doc_id = "/%s/doc/%s" % (index_name, result["_id"])
            # process the information from ES whether the document has been
            # successfully indexed
            if not ok:
                raise Exception(
                    "Failed to %s document %s: %r" % (action, doc_id, result))
            num += 1
            if num % bulk_size == 0:
                logger.info("{0} docs to {1} done: items {2} to {3}".format(
                    action, index_name, pre_num, num))
                pre_num = num
        logger.info("Streaming bulk total {0} docs to {1} done".format(num, index_name))
        return True

    # ===============
    # search
    # ===============
    def search(self, body=None, index_name=None, doc_type=None, **kwargs):
        """
        Returns results matching a query.
        :param body: The search definition using the Query DSL
        :param index_name: A comma-separated list of index names to search; use
            `_all` or empty string to perform the operation on all indices
        :param doc_type: A comma-separated list of document types to
            search; leave empty to perform the operation on all types
        :return:
        """
        return self.conn.search(body, index_name, doc_type, **kwargs)

    # ===============
    # Indices
    # class elasticsearch.client.IndicesClient(client)
    # ===============
    def is_index_exists(self, index_name):
        """
        Returns information about whether a particular index exists.
        :param index_name: A comma-separated list of index names
        :return:
        """
        return self.conn.indices.exists(index_name, allow_no_indices=True)

    def get_index_info(self, index_name):
        """
        Returns information about one or more indices.
        :param index_name: A comma-separated list of index names
        :return:
        """
        return self.conn.indices.get(index_name)

    def get_index_alias_info(self, index_name=None, alias_name=None):
        """
        Returns an alias.
        :param index_name: A comma-separated list of index names to filter
            aliases
        :param alias_name: A comma-separated list of alias names to return
        :return:
        """
        return self.conn.indices.get_alias(index_name, alias_name)

    def get_index_settings(self, index_name):
        """
        Returns settings for one or more indices.
        :param index_name: A comma-separated list of index names
        :return:
        """
        return self.conn.indices.get_settings(index_name)

    def get_index_template(self, index_name):
        """
        Returns an index template.
        :param index_name: A comma-separated list of index names
        :return:
        """
        return self.conn.indices.get_template(index_name)

    def get_index_mapping(self, index_name):
        """
        Returns mappings for one or more indices.
        :param index_name: A comma-separated list of index names
        :return:
        """
        return self.conn.indices.get_mapping(index_name)

    def get_index_field_mapping(self, fields, index_name=None, doc_type=None):
        """

        :param fields: A comma-separated list of fields
        :param index_name: A comma-separated list of index names
        :param doc_type: A comma-separated list of document types
        :return:
        """
        return self.conn.indices.get_field_mapping(fields, index_name, doc_type)

    def get_index_recovery(self, index_name):
        """
        Returns information about ongoing index shard recoveries.
        :param index_name:
        :return:
        """
        return self.conn.indices.recovery(index_name, active_only=False, detailed=True)

    def analyze_index(self, index_name, body):
        """
        Performs the analysis process on a text and return the tokens
        breakdown of the text.
        :param index_name: The name of the index to scope the operation
        :param body: Define analyzer/tokenizer parameters and the text
        on which the analysis should be performed
        :return:
        """
        return self.conn.indices.analyze(body, index_name)

    def clear_indices_cache(self, index_name):
        """
        Clears all or specific caches for one or more indices.
        :param index_name: A comma-separated list of index name to
            limit the operation
        :return:
        """
        return self.conn.indices.clear_cache(index_name)

    def clone_index(self, index_name, target, body):
        """
        Clones an index
        :param index_name:
        :param target:
        :param body:
        :return:
        """
        return self.conn.indices.clone(index_name, target, body)

    def close_index(self, index_name):
        """
        Closes an index.
        :param index_name: A comma separated list of indices to close
        :return:
        """
        return self.conn.indices.close(index_name)

    def create_index(self, index_name, body=None):
        """
        Creates an index with optional settings and mappings.
        :param index_name: The name of the index
        :param body: he configuration for the index (`settings` and
            `mappings`)
        :return:
        """

        if self.is_index_exists(index_name):
            logger.debug('{0} already exist! skip create new'.format(index_name))
            return True

        logger.info("Creating index {0} {1}".format(index_name, body))
        rc = self.conn.indices.create(index_name, body,
                                      timeout=ES_OPERATION_TIMEOUT)
        logger.info("Index {0} create done".format(index_name))
        return rc

    def delete_index(self, index_name):
        """
        Deletes an index.
        :param index_name: A comma-separated list of indices to delete; use
            `_all` or `*` string to delete all indices
        :return:
        """
        logger.info("Delete indices:{0} ...".format(index_name))
        return self.conn.indices.delete(index_name, allow_no_indices=True)

    def flush_index(self, index_name='_all'):
        """
        Performs the flush operation on one or more indices.
        :param index_name: A comma-separated list of index names;
        use _all or empty string for all indices
        :return:
        """
        return self.conn.indices.flush(index_name, wait_if_ongoing=True)

    def flush_synced_index(self, index_name='_all'):
        """
        Performs a synced flush operation on one or more indices.
        :param index_name: A comma-separated list of index names;
        use _all or empty string for all indices
        :return:
        """
        return self.conn.indices.flush(index_name)

    def force_merge_index(self, index_name='_all'):
        """
        Performs a synced flush operation on one or more indices.
        :param index_name: A comma-separated list of index names; use `_all` or
            empty string to perform the operation on all indices
        :return:
        """
        return self.conn.indices.forcemerge(index_name)

    def refresh_index(self, index_name='_all'):
        """
        Performs the refresh operation in one or more indices.
        :param index_name: A comma-separated list of index names; use `_all` or
            empty string to perform the operation on all indices
        :return:
        """
        return self.conn.indices.refresh(index_name)

    def reload_index_search_analyzers(self, index_name):
        """
        Performs the refresh operation in one or more indices.
        :param index_name: A comma-separated list of index names to reload
            analyzers for
        :return:
        """
        return self.conn.indices.reload_search_analyzers(index_name)

    def rollover_index(self, alias_name, body, new_index_name, dry_run=False):
        """
        Updates an alias to point to a new index when the existing index is
        considered to be too large or too old.
        :param alias_name: The name of the alias to rollover
        :param body: The conditions that needs to be met for executing
            rollover
        :param new_index_name: The name of the rollover index
        :param dry_run: If set to true the rollover action will only be
            validated but not actually performed even if a condition matches.
            The default is false
        :return:
        """
        return self.conn.indices.rollover(alias_name, body, new_index_name,
                                          dry_run=dry_run)

    def open_index(self, index_name):
        """
        Opens an index.
        :param index_name: A comma separated list of indices to open
        :return:
        """
        return self.conn.indices.open(index_name)

    def put_index_alias(self, index_name, alias_name, body=None):
        """
        Creates or updates an alias.
        :param index_name: A comma-separated list of index names the alias
            should point to (supports wildcards); use `_all` to perform the
            operation on all indices.
        :param alias_name: The name of the alias to be created or updated
        :param body: he settings for the alias, such as `routing` or
            `filter`
        :return:
        """
        return self.conn.indices.put_alias(index_name, alias_name, body,
                                           timeout=ES_OPERATION_TIMEOUT)

    def put_index_mapping(self, body, index_name=None, doc_type=None):
        """
        Updates the index mappings.
        :param body: The mapping definition
        :param index_name: A comma-separated list of index names the mapping
            should be added to (supports wildcards); use `_all` or omit to add the
            mapping on all indices.
        :param doc_type: The name of the document type
        :return:
        """
        return self.conn.indices.put_mapping(body, index_name, doc_type,
                                             timeout=ES_OPERATION_TIMEOUT)

    def put_index_settings(self, body, index_name=None):
        """
        Updates the index settings.
        :param body: he index settings to be updated
        :param index_name: A comma-separated list of index names; use `_all` or
            empty string to perform the operation on all indices
        :return:
        """
        return self.conn.indices.put_settings(body, index_name,
                                              timeout=ES_OPERATION_TIMEOUT)

    def put_index_template(self, template_name, body, create=False):
        """
        Updates the index settings.
        :param template_name: The name of the template
        :param body: The template definition
        :param create: Whether the index template should only be added if
            new or can also replace an existing one
        :return:
        """
        return self.conn.indices.put_template(template_name, body,
                                              create=create,
                                              timeout=ES_OPERATION_TIMEOUT)

    # ===============
    # Cluster
    # class elasticsearch.client.ClusterClient(client)
    # ===============
    def get_cluster_health(self, index=None, level='cluster'):
        """
        Returns basic information about the health of the cluster.
        :param index: Limit the information returned to a specific index
        :param level: Specify the level of detail for returned information
            Valid choices: cluster, indices, shards Default: cluster
        :return:
        """
        return self.conn.cluster.health(index, level=level)

    def get_cluster_state(self, metric, index_name):
        """
        Returns a comprehensive information about the state of the cluster.
        :param metric: Limit the information returned to the specified
            metrics Valid choices: _all, blocks, metadata, nodes,
            routing_table, routing_nodes, master_node, version
        :param index_name: A comma-separated list of index names; use `_all` or
            empty string to perform the operation on all indices
        :return:
        """
        return self.conn.cluster.state(metric, index_name)

    def get_cluster_stats(self, node_id):
        """
        Returns high-level overview of cluster statistics.
        :param node_id:
        :return:
        """
        return self.conn.cluster.stats(node_id)

    def get_cluster_settings(self):
        """
        Returns cluster settings.
        :return:
        """
        return self.conn.cluster.get_settings()

    def put_cluster_settings(self, body):
        """
        Updates the cluster settings.
        :param body: The settings to be updated. Can be either `transient`
            or `persistent` (survives cluster restart).
        :return:
        """
        logger.info('PUT Settings:{0}'.format(body))
        return self.conn.cluster.put_settings(body)

    def cluster_allocation_explain(self, body=None, include_disk_info=True):
        """
        Provides explanations for shard allocations in the cluster.
        :return:
        """
        return self.conn.cluster.allocation_explain(body,
                    include_disk_info=include_disk_info)

    def get_pending_tasks(self):
        """
        Returns a list of any cluster-level changes
        (e.g. create index, update mapping, allocate or fail shard) which
        have not yet been executed.
        :return:
        """
        return self.conn.cluster.pending_tasks()

    # ===============
    # Cat
    # class elasticsearch.client.CatClient(client)
    # ===============
    @property
    def ping(self):
        """Returns whether the cluster is running"""
        return self.conn.ping()

    @property
    def health(self):
        """
        Returns a concise representation of the cluster health.
        :return:
        """
        return self.conn.cat.health()

    @property
    def is_health_ok(self):
        return self.ping and 'red' not in self.health.split()[3]

    @property
    def nodes(self):
        """
        Returns basic statistics about performance of cluster nodes.
        :return:
        """
        return self.conn.cat.nodes(format='json')

    @property
    def node_attrs(self):
        """
        Returns information about custom node attributes.
        :return:
        """
        return self.conn.cat.nodeattrs(format='json')

    @property
    def master_nodes(self):
        """
        Returns information about the master node.
        :return:
        """
        return self.conn.cat.master(format='json')

    @property
    def node_ips(self):
        node_list = self.conn.cat.nodes().strip().split('\n')
        node_ips = [node.split()[0] for node in node_list]
        return node_ips

    @property
    def es_nodes(self):
        # todo: del
        return self.node_ips

    @property
    def master_node_ips(self):
        node_list = self.conn.cat.master().strip().split('\n')
        print(node_list)
        node_ips = [node.split()[2] for node in node_list]
        return node_ips

    @property
    def indices_names(self):
        indices_names = []
        for indices in self.conn.cat.indices().strip().split('\n'):
            indices_info = indices.split()
            if len(indices_info) > 3:
                indices_names.append(indices_info[2])
        return indices_names

    @property
    def es_cluster_health(self):
        """Returns a concise representation of the cluster health."""
        return self.conn.cat.health().split()[3]

    def cat_aliases(self, alias_name):
        """
        Shows information about currently configured aliases to indices
        including filter and routing infos.
        :param alias_name: A comma-separated list of alias names to return
        :return:
        """
        return self.conn.cat.aliases(alias_name, bytes='mb', format='json')

    def cat_allocation(self, node_id):
        """
        Provides a snapshot of how many shards are allocated to each
        data node and how much disk space they are using.
        :param node_id: A comma-separated list of node IDs or names to
            limit the returned information
        :return:
        """
        return self.conn.cat.allocation(node_id, bytes='mb', format='json')

    def cat_fielddata_size(self, fields):
        """
        Shows how much heap memory is currently being used by fielddata
        on every data node in the cluster.
        :param fields: A comma-separated list of fields to return the
            fielddata size
        :return:
        """
        return self.conn.cat.fielddata(fields, bytes='mb', format='json')

    def cat_doc_count(self, index_name):
        """
        Provides quick access to the document count of the entire cluster,
        or individual indices.
        :param index_name: A comma-separated list of index names to limit the
            returned information
        :return:
        """
        return self.conn.cat.count(index_name, format='json')

    def cat_indices(self, index_name, health=None):
        """
        Returns information about indices: number of primaries and replicas,
        document counts, disk size, ...
        :param index_name: A comma-separated list of index names to limit the
            returned information
        :param health: A health status ("green", "yellow", or "red" to
            filter only indices matching the specified health status
            Valid choices: green, yellow, red
        :return:
        """
        if health:
            return self.conn.cat.indices(index_name, health=health,
                                         format='json')
        else:
            return self.conn.cat.indices(index_name, format='json')

    def cat_shards(self, index_name):
        """
        Provides a detailed view of shard allocation on nodes.
        :param index_name: A comma-separated list of index names to limit the
            returned information
        :return:
        """
        return self.conn.cat.shards(index_name, bytes='kb')

    def cat_segments(self, index_name):
        """
        Provides low-level information about the segments in the shards
        of an index.
        :param index_name: A comma-separated list of index names to limit the
            returned information
        :return:
        """
        return self.conn.cat.segments(index_name, bytes='kb')

    def cat_pending_tasks(self):
        """
        Returns a concise representation of the cluster pending tasks.
        :return:
        """
        return self.conn.cat.pending_tasks(format='json')

    def cat_recovery_info(self, index_name, active_only=False, detailed=True):
        """
        Returns information about index shard recoveries, both
        on-going completed.
        :param index_name: Comma-separated list or wildcard expression
            of index names to limit the returned information
        :param active_only:If `true`, the response only includes ongoing
            shard recoveries
        :param detailed:If `true`, the response includes detailed
            information about shard recoveries
        :return:
        """
        return self.conn.cat.recovery(index_name, active_only=active_only,
                                      detailed=detailed, bytes='kb',
                                      format='json')

    def cat_repositories(self):
        """
        Returns information about snapshot repositories registered
        in the cluster.
        :return:
        """
        return self.conn.cat.repositories(format='json')

    def cat_snapshots(self, repository=None):
        """
        Returns all snapshots in a specific repository.
        :param repository:Name of repository from which to fetch the
            snapshot information
        :return:
        """
        return self.conn.cat.snapshots(repository, format='json')

    # ===============
    # Snapshot
    # class elasticsearch.client.SnapshotClient(client)
    # ===============
    def get_snapshot_info(self, repository, snap_name):
        """
        Returns information about a snapshot.
        :param repository: A repository name
        :param snap_name: A comma-separated list of snapshot names
        :return:
        """
        return self.conn.snapshot.get(repository, snap_name)

    def get_snapshot_status(self, repository, snap_name):
        """
        Returns information about the status of a snapshot.
        :param repository:A repository name
        :param snap_name:A comma-separated list of snapshot names
        :return:
        """

        return self.conn.snapshot.status(repository, snap_name,
                                         ignore_unavailable=True)

    def get_repository_info(self, repository):
        """
        Returns information about a repository.
        :param repository:A repository name
        :return:
        """
        try:
            repo = self.conn.snapshot.get_repository(repository, local=False)
            return repo
        except ElasticsearchException as e:
            logger.error(e)
            return None

    def verify_repository(self, repository):
        """
        Verifies a repository.
        :param repository:A repository name
        :return:
        """
        return self.conn.snapshot.verify_repository(
            repository,
            timeout=ES_OPERATION_TIMEOUT
        )

    def create_repository(self, repository, body):
        """
        Creates a repository.
        :param repository: A repository name
        :param body: The repository definition
        :return:
        """
        return self.conn.snapshot.create_repository(
            repository, body,
            timeout=ES_OPERATION_TIMEOUT, verify=True
        )

    def create_snapshot(self, repository, snap_name, body):
        """
        Creates a snapshot in a repository.
        :param repository: A repository name
        :param snap_name: A snapshot name
        :param body: The snapshot definition
        :return:
        """

        return self.conn.snapshot.create(
            repository, snap_name, body, wait_for_completion=True
        )

    def cleanup_repository(self, repository):
        """
        Removes stale data from repository.
        :param repository: A repository name
        :return:
        """
        return self.conn.snapshot.cleanup_repository(
            repository, timeout=ES_OPERATION_TIMEOUT
        )

    def delete_repository(self, repository):
        """
        Deletes a repository.
        :param repository:A comma-separated list of repository names
        :return:
        """
        return self.conn.snapshot.create_repository(
            repository, timeout=ES_OPERATION_TIMEOUT
        )

    def delete_snapshot(self, repository, snap_name):
        """
        Deletes a snapshot.
        :param repository: A repository name
        :param snap_name: A snapshot name
        :return:
        """

        return self.conn.snapshot.delete(repository, snap_name)

    def restore_snapshot(self, repository, snap_name, body):
        """

        :param repository:A repository name
        :param snap_name:A snapshot name
        :param body:Details of what to restore
        :return:
        """

        return self.conn.snapshot.restore(
            repository, snap_name, body, wait_for_completion=True
        )

    # ===============
    # Check
    # user-defined
    # ===============
    @print_for_call
    def is_index_green(self, index_name=None):
        """
        Check is the index list green
        :param index_name: A string or list of index names,
            will check all exist indices if None
        :return:
        """
        if not self.ping:
            raise Exception('The es cluster is not running(PING FAILED)!')

        index_name_list = index_name if isinstance(index_name, list) else [
            index_name]
        cold_nodes_num = len(self.nodes) - len(self.master_nodes)
        for index_name in index_name_list:
            index_info_list = self.cat_indices(index_name=index_name)
            for index_info in index_info_list:
                index = index_info['index']
                index_health = index_info['health']
                if cold_nodes_num > 2 and index_health != 'green':
                    logger.warning(json.dumps(index_info, indent=4))
                    raise Exception('Index {0} Not OK:{1}'.format(index, index_health))
                elif index_health not in ['yellow', 'green']:
                    logger.warning(json.dumps(index_info, indent=4))
                    allocation_explain = self.cluster_allocation_explain()
                    if 'index' in allocation_explain and allocation_explain['index'] == index:
                        logger.warning(allocation_explain['unassigned_info']['details'])
                    raise Exception('Index {0} Not OK:{1}'.format(index, index_health))
                else:
                    logger.debug(json.dumps(index_info, indent=4))
                    logger.info('Index {0} OK:{1}'.format(index, index_health))
        return True

    @print_for_call
    def is_cluster_ok(self):
        """Check the cluster health"""
        if not self.ping:
            raise Exception('The es cluster is not running(PING FAILED)!')

        cluster_health = self.es_cluster_health
        if 'red' in cluster_health:
            raise Exception('ES Cluster health: red')
        else:
            cold_nodes_num = len(self.nodes) - len(self.master_nodes)
            if cold_nodes_num > 2 and 'yellow' in cluster_health:
                raise Exception('ES Cluster:3 health: yellow')
            else:
                logger.info('ES Cluster OK:{0}'.format(cluster_health))
        return True


if __name__ == '__main__':
    es_api = ESApi('10.25.119.71', 30707, 'root', 'password')
    print(es_api.cat_indices('index-8'))
