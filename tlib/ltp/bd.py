# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/11/26 15:00
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

import re

from tlib.log import log
from tlib.utils import util
from tlib.ssh_manager import SSHManager


logger = log.get_logger()


class BlockDevice(object):
    """block device related ops"""

    def __init__(self, ip=None, username=None, password=None, key_file=None):
        super(BlockDevice, self).__init__()
        if ip:
            ssh_mgr = SSHManager(ip, username, password, key_file)
            self.run_cmd = ssh_mgr.ssh_cmd
        else:
            self.run_cmd = util.run_cmd

    def _mknod_device(self, device):
        """
        mknod /dev/dpl1 b 44 16
        :param device:
        :return:
        """

        minor = int(re.search(r'\d+$', device).group())*16
        cmd = 'mknod {0} b 44 {1}'.format(device, minor)
        rc, output = self.run_cmd(cmd, expected_rc=0)
        logger.info(output)
        return rc

    def get_all_devices(self, pattern='/dev/*'):
        rc, output = self.run_cmd('ls %s' % pattern, expected_rc='ignore')
        logger.info(output)
        device_list = output.strip('\n').split(' ')
        return device_list

    def _is_path_exist(self, path):
        ls_cmd = 'ls {0}'.format(path)
        rc, output = self.run_cmd(ls_cmd, expected_rc='ignore')
        if 'No such file or directory' in output:
            logger.warning(output)
            return False
        else:
            logger.info(output)
            return True

    def _validate_device(self, device):
        if not self._is_path_exist(device):
            self._mknod_device(device)

    def _validate_directory(self, directory):
        if not self._is_path_exist(directory):
            logger.info('Create a new one')
            mkdir_cmd = 'mkdir -p {0}'.format(directory)
            self.run_cmd(mkdir_cmd, expected_rc=0)

    def mkfs_filesystem(self, device, types='ext4',
                        options='-F -b4096 -E nodiscard'):
        """
        Make a Linux filesystem.
        :param device:explicitly specifies device path, eg: /dev/dpl1
        :param types:
        :param options:
        :return:
        """

        # mkfs.ext4 -F -b4096 -E nodiscard /dev/dpl1
        cmd = 'mkfs.{0} {1} {2}'.format(types, options, device)
        rc, output = self.run_cmd(cmd, expected_rc=0)
        logger.info(output)
        return rc

    def mount_fs(self, source, target, types, options='discard'):
        """
        mount a filesystem.
        :param source:explicitly specifies source (path, label, uuid)
        :param target:explicitly specifies mountpoint
        :param types:<-t> limit the set of filesystem types
        :param options:<-o> comma-separated list of mount options
        :return:
        """

        # if the mount point path not exist, will create a new one
        self._validate_directory(target)
        cmd = 'mount -t %s -o %s %s %s ' % (types, options, source, target)
        rc, output = self.run_cmd(cmd, expected_rc=0, tries=3)
        logger.info(output)
        return rc

    def umount_fs(self, path, options=''):
        """
        Unmount filesystems.
        :param path:explicitly <source> | <directory>
        :param options: eg:-a -l -f, details FYI: umount -h
        :return:
        """

        cmd = 'umount {0} {1}'.format(options, path)
        rc, output = self.run_cmd(cmd, expected_rc=0, tries=3)
        logger.info(output)
        return rc

    def get_mount_point(self, source, target, types='ext4'):
        """
        Get the mount point by source and types
        :param source:
        :param target:
        :param types:
        :return:
        """

        cmd = "/bin/mount | grep %s | grep %s | grep %s | awk '{print $3}'" % (
            source, target, types)
        rc, output = self.run_cmd(cmd, expected_rc='ignore')
        return output.strip('\n')

