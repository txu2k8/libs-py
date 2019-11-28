# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/11/28 14:01
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""python etcd api"""

import etcd3
from tlib.log import log

# =============================
# --- Global
# =============================
logger = log.get_logger()


class EtcdAPI(object):
    _session = None

    def __init__(self, etcd_ip, etcd_port, ca_cert, cert_key, cert_cert):
        self.etcd_ip = etcd_ip
        self.etcd_port = etcd_port
        self.ca_cert = ca_cert
        self.cert_key = cert_key
        self.cert_cert = cert_cert

    @property
    def session(self):
        if self._session is None:
            logger.info('Connect to etcd:{0}:{1}'.format(self.etcd_ip,
                                                         self.etcd_port))
            self._session = etcd3.client(host=self.etcd_ip,
                                         port=self.etcd_port,
                                         ca_cert=self.ca_cert,
                                         cert_key=self.cert_key,
                                         cert_cert=self.cert_cert)

        return self._session

    def get(self, key):
        return self.session.get(key)

    def get_prefix(self, key_prefix):
        return self.session.get_prefix(key_prefix)

    def delete_prefix(self, key_prefix):
        return self.session.delete_prefix(key_prefix)


if __name__ == '__main__':
    pass
