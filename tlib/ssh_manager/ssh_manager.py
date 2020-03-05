# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/10/10 15:40
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

""" paramiko ssh """

import re
import time
import paramiko
import scp
import inspect
import socket
import subprocess
import unittest

from tlib import log
from tlib.retry import retry, retry_call
from tlib.utils import util

# =============================
# --- Global
# =============================
logger = log.get_logger()
DOCKER_ARGS = '--dns=10.233.0.10 --dns-search=svc.cluster.local'


class SSHManager(object):
    """
    SSH Manager: exec_cmd/scp
    """
    _ssh = None

    def __init__(self, ip, username, password=None, key_file=None, port=22,
                 conn_timeout=1200):
        self.ip = util.get_reachable_ip(ip, ping_retry=3) \
            if isinstance(ip, list) else ip
        self.username = username
        self.password = password
        self.key_file = key_file
        self.port = port
        self.conn_timeout = conn_timeout

    def __del__(self):
        # logger.debug('Enter SSHObj.__del__()')
        try:
            self._ssh.close()
            del self._ssh
        except Exception as e:
            pass

    @property
    def ssh(self):
        if self._ssh is None or self._ssh.get_transport() is None or \
                not self._ssh.get_transport().is_active():
            self._ssh = self.connect()
        return self._ssh

    @retry(tries=10, delay=3, jitter=1)
    def connect(self):
        logger.info('SSH Connect to {0}@{1}(pwd:{2}, key_file:{3})'.format(
            self.username, self.ip, self.password, self.key_file))
        compile_ip = re.compile(r'^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
        if not compile_ip.match(self.ip):
            logger.error('Error IP address!')
            return None

        _ssh = paramiko.SSHClient()
        # _ssh.load_system_host_keys()
        _ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            if self.key_file is not None:
                pkey = paramiko.RSAKey.from_private_key_file(self.key_file)
                _ssh.connect(self.ip, self.port, self.username, self.password,
                             timeout=self.conn_timeout, pkey=pkey)
            else:
                _ssh.connect(self.ip, self.port, self.username, self.password,
                             timeout=self.conn_timeout)
        except Exception as e:
            logger.warning('SSH Connect {0} fail!'.format(self.ip))
            self._ssh = None
            raise e
        return _ssh

    @property
    def is_active(self):
        return self.ssh.get_transport().is_active()

    def subprocess_popen_cmd(self, cmd_spec, timeout=7200,
                             docker_image=None, docker_args=''):
        """
        Executes command and Returns (rc, output) tuple
        :param cmd_spec: Command to be executed
        :param output: A flag for collecting STDOUT and STDERR of command execution
        :param timeout
        :param docker_image:
        :param docker_args:
        :return:
        """

        sudo = False if self.username == 'root' else True
        # sudo = False if 'kubectl' in cmd_spec else sudo

        if docker_image:
            cmd_spec = "docker run -i --rm --network host {0} " \
                       "-v /dev:/dev -v /etc:/etc --privileged {1} bash " \
                       "-c '{2}'".format(docker_args, docker_image, cmd_spec)
        elif sudo:
            cmd_spec = 'sudo {cmd}'.format(cmd=cmd_spec)

        logger.info('Execute: {cmds}'.format(cmds=cmd_spec))
        try:
            p = subprocess.Popen(cmd_spec, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, shell=True)
            t_beginning = time.time()

            while True:
                if p.poll() is not None:
                    break
                seconds_passed = time.time() - t_beginning
                if timeout and seconds_passed > timeout:
                    p.terminate()
                    raise TimeoutError('TimeOutError: {0} seconds'.format(timeout))
                time.sleep(0.1)

            std_out = p.stdout.read().decode('UTF-8', 'ignore')
            std_err = p.stderr.read().decode('UTF-8', 'ignore')
            return std_out, std_err
        except Exception as e:
            raise Exception('Failed to execute: {0}\n{1}'.format(cmd_spec, e))

    def paramiko_ssh_cmd(self, cmd_spec, timeout=7200, get_pty=False,
                         docker_image=None, docker_args=''):
        """
        ssh to <ip> and then run commands --paramiko
        :param cmd_spec:
        :param timeout:
        :param get_pty:
        :param docker_image:
        :param docker_args:
        :return:
        """

        sudo = False if self.username == 'root' else True
        # sudo = False if 'kubectl' in cmd_spec else sudo

        if docker_image:
            cmd_spec = "docker run -i --rm --network host {0} " \
                       "-v /dev:/dev -v /etc:/etc --privileged {1} bash " \
                       "-c '{2}'".format(docker_args, docker_image, cmd_spec)
        elif sudo:
            cmd_spec = 'sudo {cmd}'.format(cmd=cmd_spec)

        logger.info('Execute: ssh {0}@{1}# {2}'.format(self.username, self.ip,
                                                       cmd_spec))

        try:
            if sudo and (self.password or self.key_file):
                w_pwd = '' if self.key_file else self.password
                stdin, stdout, stderr = self.ssh.exec_command(
                    cmd_spec, get_pty=True, timeout=timeout)
                stdin.write(w_pwd + '\n')
                stdin.flush()
            else:
                stdin, stdout, stderr = self.ssh.exec_command(
                    cmd_spec, get_pty=get_pty, timeout=timeout)
                stdin.write('\n')
                stdin.flush()
            std_out = stdout.read().decode('UTF-8', 'ignore')
            std_err = stderr.read().decode('UTF-8', 'ignore')
            return std_out, std_err
        except Exception as e:
            raise Exception('Failed to run: {0}\n{1}'.format(cmd_spec, e))

    def ssh_cmd(self, cmd_spec, expected_rc=0, timeout=7200, get_pty=False,
                docker_image=None, docker_args=DOCKER_ARGS, tries=3, delay=3):
        """
        ssh and run cmd
        """

        # Get name of the calling method, returns <methodName>'
        method_name = inspect.stack()[1][3]
        if self.ip == socket.gethostbyname(socket.gethostname()):
            # run command on local host
            stdout, stderr = retry_call(self.subprocess_popen_cmd,
                                        fkwargs={'cmd_spec': cmd_spec,
                                                 'timeout': timeout,
                                                 'docker_image': docker_image,
                                                 'docker_args': docker_args},
                                        tries=tries, delay=delay, logger=logger)
        else:
            stdout, stderr = retry_call(self.paramiko_ssh_cmd,
                                        fkwargs={'cmd_spec': cmd_spec,
                                                 'timeout': timeout,
                                                 'get_pty': get_pty,
                                                 'docker_image': docker_image,
                                                 'docker_args': docker_args},
                                        tries=tries, delay=delay, logger=logger)

        rc = -1 if stderr else 0
        output = stdout + stderr if stderr else stdout
        if isinstance(expected_rc, str) and expected_rc.upper() == 'IGNORE':
            return rc, output

        if rc != expected_rc:
            raise Exception('%s(): Failed command: %s\nMismatched '
                            'RC: Received [%d], Expected [%d]\nError: %s' % (
                method_name, cmd_spec, rc, expected_rc, output))
        return rc, output

    @retry(tries=3, delay=1)
    def remote_scp_put(self, local_path, remote_path):
        """
        scp put --paramiko, scp
        :param local_path:
        :param remote_path:
        :return:
        """

        logger.info('scp %s %s@%s:%s' % (
        local_path, self.username, self.ip, remote_path))

        try:
            obj_scp = scp.SCPClient(self.ssh.get_transport())
            obj_scp.put(local_path, remote_path)

            # make sure the local and remote file md5sum match
            # local_md5 = util.md5sum(local_path)
            # rc, output = self.ssh_cmd('md5sum {0}'.format(remote_path), expected_rc=0)
            # remote_md5 = output.strip('\n').split(' ')[0]
            # logger.info('{0} {1}'.format(local_md5, local_path))
            # logger.info('{0} {1}'.format(remote_md5, remote_path))
            # assert remote_md5 == local_md5

            return True
        except Exception as e:
            raise e

    @retry(tries=3, delay=1)
    def remote_scp_get(self, local_path, remote_path):
        """
        scp get --paramiko, scp
        :param local_path:
        :param remote_path:
        :return:
        """

        logger.info('scp %s@%s:%s %s' % (
        self.username, self.ip, remote_path, local_path))

        try:
            obj_scp = scp.SCPClient(self.ssh.get_transport())
            obj_scp.get(remote_path, local_path)

            # make sure the local and remote file md5sum match
            # rc, output = self.ssh_cmd('md5sum {0}'.format(remote_path), expected_rc=0)
            # remote_md5 = output.strip('\n').split(' ')[0]
            # local_md5 = util.md5sum(local_path)
            # logger.info('{0} {1}'.format(remote_md5, remote_path))
            # logger.info('{0} {1}'.format(local_md5, local_path))
            # assert remote_md5 == local_md5

            return True
        except Exception as e:
            raise e

    def mkdir_remote_path_if_not_exist(self, remote_path):
        cmd1 = 'ls {path}'.format(path=remote_path)
        rc, output = self.ssh_cmd(cmd1, expected_rc='ignore', tries=2)
        if 'No such file or directory' in output:
            cmd2 = 'mkdir -p {path}'.format(path=remote_path)
            self.ssh_cmd(cmd2)
        return True


class SSHManagerTestCase(unittest.TestCase):
    """docstring for SSHTestCase"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_1(self):
        ssh_obj = SSHManager(ip='10.25.119.1', username='root',
                             password='password')
        rc, output = ssh_obj.ssh_cmd('pwd')
        logger.info(output)

        rc, output = ssh_obj.ssh_cmd('ls')
        logger.info(output)


if __name__ == '__main__':
    # test
    unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(SSHManagerTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
