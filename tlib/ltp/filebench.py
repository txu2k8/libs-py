# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/11/26 14:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""
FileBench TEST -- Flexible workload generator
https://github.com/filebench/filebench/wiki

===============
Filebench is a file system and storage benchmark that can generate a large
variety of workloads. Unlike typical benchmarks it is extremely flexible and
allows to specify application's I/O behavior using its extensive Workload Model
Language (WML). Users can either describe desired workloads from scratch or use
(with or without modifications) workload personalities shipped with Filebench
(e.g., mail-, web-, file-, and database-server workloads).

Filebench 是一款文件系统性能的自动化测试工具，它通过快速模拟真实应用服务器的负载来
测试文件系统的性能。
它不仅可以仿真文件系统微操作(如 copyfiles, createfiles, randomread,randomwrite)，
而且可以仿真复杂的应用程序(如varmail,fileserver,oltp,dss,webserver,webproxy)。
Filebench 比较适合用来测试文件服务器性能，但同时也是一款负载自动生成工具，也可用于文件系统的性能。
"""

import os

from tlib.log import log
from tlib.utils import util
from tlib.ltp.bd import BlockDevice


logger = log.get_logger()


class FileBench(BlockDevice):
    """FileBench"""

    def __init__(self, device, fs_type='ext4'):
        super(FileBench, self).__init__()
        self.device = device  # eg: /dev/sdc
        self.target = os.path.join('/mnt/', os.path.basename(device))
        self.fs_type = fs_type

    @property
    def mount_point(self):
        rc = self.get_mount_point(self.device, self.target, self.fs_type)
        m_point = rc or self.mount_fs(self.device, self.target, self.fs_type)
        return m_point

    def run(self, filebench_conf):
        logger.info('Load: {0}'.format(filebench_conf))
        conf_name = os.path.split(filebench_conf)[-1]
        tmp_path = os.path.join(os.getcwd(), 'tmp')
        util.mkdir_path_if_not_exist(tmp_path)
        tmp_conf_name = '{0}_{1}_{2}'.format('filebench', self.mount_point.replace('/', '_'), conf_name)
        tmp_conf = os.path.join(tmp_path, tmp_conf_name)
        rc, output = util.run_cmd('cp {0} {1}'.format(filebench_conf, tmp_conf), expected_rc=0)
        # print(output)

        # modify the tmp conf file
        conf_cmd = "sed -i 's/set \$dir=\/tmp/set \$dir={mount_point}/g' {conf_file}".format(
            mount_point=self.mount_point.replace('/', '\/'),
            conf_file=tmp_conf)
        rc, output = util.run_cmd(conf_cmd, expected_rc=0)
        # print(output)

        with open(tmp_conf, "a+") as f:
            f_text = f.read()
            if f_text.find('run 60') == -1:
                f.write('run 60\n')

        case_name = 'FileBench'
        logger.info("%-20s\t%-20s\t%-15s" % (case_name, self.device, 'Running'))
        tmp_conf_log = os.path.join(tmp_path, '{0}.log'.format(tmp_conf_name.split('.')[0]))
        try:
            rc1, output1 = util.run_cmd('which filebench')
            if 'no filebench' in output1:
                os.system('yum install filebench -y')
            rc, output = util.run_cmd(
                'echo 0 to /proc/sys/kernel/randomize_va_space')
            logger.info(output.strip('\n'))
            rc, output = util.run_cmd('filebench -f {0} | tee -a {1}'.format(tmp_conf, tmp_conf_log), timeout=72000)
            logger.info('\n'.format(output.strip('\n')))
            logger.info("%-20s\t%-20s\t%-15s" % (case_name, self.device, 'PASS [Completed]'))
        except Exception as e:
            logger.info("%-20s\t%-20s\t%-15s" % (case_name, self.device, 'Failed'))
            raise e
        finally:
            util.run_cmd('rm -rf {0}'.format(tmp_conf))
