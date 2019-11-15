# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/16 14:57
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""Python cassandra api"""

import ssl
from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

from tlib import log
from tlib.retry import retry

ssl._create_default_https_context = ssl._create_unverified_context

# =============================
# --- Global
# =============================
logger = log.get_logger()


class CassandraAPI(object):
    """docstring for CassandraObj"""
    _session = None
    _cluster = None

    def __init__(self, ips, user='cassandra', password='cassandra', port=9042,
                 keyspace=None, wait_for_all_pools=True):
        super(CassandraAPI, self).__init__()
        self.ips = ips
        self.user = user
        self.password = password
        self.port = port
        self.keyspace = keyspace
        self.wait_for_all_pools = wait_for_all_pools

    def __del__(self):
        try:
            # print('__del__: CassandraObj')
            self._session.shutdown()
            self._cluster.shutdown()
            del self._session
            del self._cluster
        except Exception as e:
            print(e)
            pass

    @retry(tries=30, delay=2, jitter=1)
    def connect(self):
        logger.info("Connect to cassandra {0} ({1}, {2}, {3}) ...".format(
            self.ips, self.user, self.password, self.port))
        try:
            plain_txt_auth = PlainTextAuthProvider(username=self.user,
                                                   password=self.password)
            cluster = Cluster(self.ips, port=self.port,
                              auth_provider=plain_txt_auth)
            self._cluster = cluster
            session = cluster.connect(
                keyspace=self.keyspace,
                wait_for_all_pools=self.wait_for_all_pools
            )
            session.default_consistency_level = ConsistencyLevel.LOCAL_QUORUM
        except Exception as e:
            raise e

        return session

    @property
    def session(self):
        if self._session is None:
            self._session = self.connect()

        return self._session

    @retry(tries=10, delay=2, jitter=1)
    def run_cql_cmd(self, cql_cmd):
        if 'insert' in cql_cmd.lower():
            logger.debug(cql_cmd)
        elif 'select' in cql_cmd.lower():
            logger.debug(cql_cmd)
        else:
            logger.info(cql_cmd)

        try:
            rows = self.session.execute(cql_cmd)
            return rows
        except Exception as e:
            raise Exception(e)

    def get_table_row_num(self, table_name):
        row_num = -1
        cql_cmd = "SELECT count(*) FROM {table}".format(table=table_name)
        rows = self.run_cql_cmd(cql_cmd)
        for row in rows:
            row_num = row.count

        return row_num

    @retry(tries=3, delay=2)
    def truncate_table(self, table):
        logger.info('> Truncate %s start' % table)
        self.run_cql_cmd("TRUNCATE TABLE %s " % table)
        if self.get_table_row_num(table) > 1:
            raise Exception('> Truncate %s failed' % table)
        logger.info('> Truncate %s done' % table)
        return True


if __name__ == "__main__":
    # import fire
    # fire.Fire()
    cassandra_ips = ['10.180.119.1']
    cassandra_obj = CassandraAPI(cassandra_ips)
    print(cassandra_obj.run_cql_cmd('select * from vizion.service'))

    cassandra_obj = CassandraAPI(cassandra_ips)
    print(cassandra_obj.run_cql_cmd('select * from vizion.volume'))
