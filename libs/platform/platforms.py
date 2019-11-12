# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""
:description:
    cross-platform functions related module
"""

import os
import time
import socket
import subprocess
import select
import platform
import scp
import inspect
import paramiko


from libs import log
from libs.bs import strsize_to_byte
from libs.ds import escape
from libs.retry import retry, retry_call

# =============================
# --- Global Value
# =============================
logger = log.get_logger()
# --- OS constants
POSIX = os.name == "posix"
WINDOWS = os.name == "nt"

# __all__ = [
#     'is_linux',
#     'is_windows',
#     'is_mac'
# ]


def is_linux():
    """
    Check if you are running on Linux.

    :return:
        True or False
    """
    if platform.platform().startswith('Linux'):
        return True
    else:
        return False


def is_windows():
    """
    Check if you are running on Windows.

    :return:
        True or False
    """

    if platform.platform().startswith('Windows'):
        return True
    else:
        return False


def is_mac():
    """
    is mac os
    """
    if hasattr(select, 'kqueue'):
        return True
    else:
        return False



def reserve_cpu_deadloop():
    """reserve all cpu resource by deadloop"""
    while True:
        pass


def reserve_memory(mem_size_str='1GB', reserve_time=3600):
    """
    reserve_memory: size and keep time
    :param mem_size_str: 1GB | 1MB | 1KB ...
    :param reserve_time: 60(s)
    :return:
    """
    mem_size_byte = strsize_to_byte(mem_size_str)
    s = ' ' * mem_size_byte
    time.sleep(reserve_time)
    return True


def subprocess_popen_cmd(cmd_spec, output=True, timeout=7200):
    """
    Executes command and Returns (rc, output) tuple
    :param cmd_spec: Command to be executed
    :param output: A flag for collecting STDOUT and STDERR of command execution
    :param timeout
    :return:
    """

    logger.info('Execute: {cmds}'.format(cmds=cmd_spec))
    try:
        p = subprocess.Popen(cmd_spec, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        t_beginning = time.time()

        while True:
            if p.poll() is not None:
                break
            seconds_passed = time.time() - t_beginning
            if timeout and seconds_passed > timeout:
                p.terminate()
                raise TimeoutError('TimeOutError: {0} seconds'.format(timeout))
            time.sleep(0.1)

        rc = p.returncode
        if output:
            # (stdout, stderr) = p.communicate()
            stdout, stderr = p.stdout.read(), p.stderr.read()
            if rc == 0:
                std_out_err = escape(stdout)
            else:
                std_out_err = escape(stderr)
                logger.warning('Output: rc={0}, stdout/stderr:\n{1}'.format(rc, std_out_err))
        else:
            std_out_err = ''
        # p.stdout.close()
        # p.stderr.close()
        # p.kill()
        return rc, std_out_err
    except Exception as e:
        raise Exception('Failed to execute: {0}\n{1}'.format(cmd_spec, e))


def run_cmd(cmd_spec, expected_rc=0, output=True, tries=1, delay=3, timeout=7200):
    """
    A generic method for running commands which will raise exception if return code of exeuction is not as expected.
    :param cmd_spec:A list of words constituting a command line
    :param expected_rc:An expected value of return code after command execution, defaults to 0, If expected. RC.upper()
    is 'IGNORE' then exception will not be raised.
    :param output:
    :param tries: retry times
    :param delay: retry delay
    :param timeout
    :return:
    """

    method_name = inspect.stack()[1][3]    # Get name of the calling method, returns <methodName>'
    rc, output = retry_call(subprocess_popen_cmd, fkwargs={'cmd_spec': cmd_spec, 'output': output, 'timeout': timeout},
                            tries=tries, delay=delay, logger=logger)

    if isinstance(expected_rc, str) and expected_rc.upper() == 'IGNORE':
        return rc, output

    if rc != expected_rc:
        raise Exception('%s(): Failed command: %s\nMismatched RC: Received [%d], Expected [%d]\nError: %s' % (
            method_name, cmd_spec, rc, expected_rc, output))
    return rc, output


def paramiko_ssh_cmd(ip, username, password, cmd_spec, key_file=None, timeout=7200, get_pty=False, docker_image=None):
    """
    ssh to <ip> and then run commands --paramiko
    :param ip:
    :param username:
    :param password:
    :param cmd_spec:
    :param key_file:
    :param timeout:
    :param get_pty:
    :param docker_image:
    :return:
    """

    sudo = False if username in ['root', 'support'] else True
    # run_cmd('ssh-keygen -f "/root/.ssh/known_hosts" -R "{0}"'.format(ip))
    ssh = paramiko.SSHClient()
    # ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if docker_image:
        cmd_spec = "docker run -i --rm --network host -v /dev:/dev -v /etc:/etc --privileged {image} bash " \
                   "-c '{cmd}'".format(image=docker_image, cmd=cmd_spec)
    logger.info('Execute: ssh {0}@{1} {2}'.format(username, ip, cmd_spec))
    try:
        if key_file is not None:
            pkey = paramiko.RSAKey.from_private_key_file(key_file)
            ssh.connect(ip, 22, username, password, timeout=timeout, pkey=pkey)
        else:
            ssh.connect(ip, 22, username, password, timeout=timeout)
        if sudo:
            stdin, stdout, stderr = ssh.exec_command('sudo {0}'.format(cmd_spec), get_pty=True, timeout=timeout)
            stdin.write(password + '\n')
            stdin.flush()
        else:
            stdin, stdout, stderr = ssh.exec_command(cmd_spec, get_pty=get_pty, timeout=360000)
            stdin.write('\n')
            stdin.flush()
        std_out, std_err = stdout.read(), stderr.read()  # escape(stdout.read()), escape(stderr.read())
        ssh.close()
        return std_out, std_err
    except Exception as e:
        raise Exception('Failed to run command: {0}\n{1}'.format(cmd_spec, e))


def ssh_cmd(ip, username, password, cmd_spec, expected_rc=0, key_file=None, timeout=7200, get_pty=False,
            docker_image=None, tries=3, delay=3):
    """
    ssh and run cmd
    :param ip:
    :param username:
    :param password:
    :param cmd_spec:
    :param expected_rc:
    :param key_file:
    :param timeout:
    :param get_pty:
    :param docker_image:
    :param tries:
    :param delay:
    :return:
    """
    method_name = inspect.stack()[1][3]  # Get name of the calling method, returns <methodName>'
    stdout, stderr = retry_call(paramiko_ssh_cmd,
                                fkwargs={'ip': ip,
                                         'username': username,
                                         'password': password,
                                         'cmd_spec': cmd_spec,
                                         'key_file': key_file,
                                         'timeout': timeout,
                                         'get_pty': get_pty,
                                         'docker_image': docker_image}, tries=tries, delay=delay, logger=logger)
    rc = -1 if stderr else 0
    output = stdout + stderr if stderr else stdout
    if isinstance(expected_rc, str) and expected_rc.upper() == 'IGNORE':
        return rc, output

    if rc != expected_rc:
        raise Exception('%s(): Failed command: %s\nMismatched RC: Received [%d], Expected [%d]\nError: %s' % (
            method_name, cmd_spec, rc, expected_rc, output))
    return rc, output


@retry(tries=2, delay=1)
def remote_sftp_put(host_ip, remote_path, local_path, username, password):
    """
    scp put --paramiko
    :param host_ip:
    :param remote_path:
    :param local_path:
    :param username:
    :param password:
    :return:
    """
    try:
        t = paramiko.Transport((host_ip, 22))
        t.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(t)
        sftp.put(local_path, remote_path)
        t.close()
        return True
    except Exception as e:
        raise e


@retry(tries=2, delay=1)
def remote_sftp_get(host_ip, remote_path, local_path, username, password):
    """
    scp get --paramiko
    :param host_ip:
    :param remote_path:
    :param local_path:
    :param username:
    :param password:
    :return:
    """
    try:
        t = paramiko.Transport((host_ip, 22))
        t.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(t)
        sftp.get(remote_path, local_path)
        t.close()
        return True
    except Exception as e:
        raise e


@retry(tries=2, delay=1)
def remote_scp_put(ip, local_path, remote_path, username, password, key_file=None, timeout=36000):
    """
    scp put --paramiko, scp
    :param ip:
    :param local_path:
    :param remote_path:
    :param username:
    :param password:
    :param key_file:
    :param timeout:
    :return:
    """

    logger.info('scp %s %s@%s:%s' % (local_path, username, ip, remote_path))
    ssh = paramiko.SSHClient()
    # ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if key_file is not None:
            pkey = paramiko.RSAKey.from_private_key_file(key_file)
            ssh.connect(ip, 22, username, password, timeout=timeout, pkey=pkey)
        else:
            ssh.connect(ip, 22, username, password, timeout=timeout)
        obj_scp = scp.SCPClient(ssh.get_transport())
        obj_scp.put(local_path, remote_path)
        ssh.close()
        return True
    except Exception as e:
        raise e


@retry(tries=2, delay=1)
def remote_scp_get(ip, local_path, remote_path, username, password, key_file=None, timeout=36000):
    """
    scp get --paramiko, scp
    :param ip:
    :param local_path:
    :param remote_path:
    :param username:
    :param password:
    :param key_file:
    :param timeout:
    :return:
    """

    logger.debug('scp %s@%s:%s %s' % (username, ip, remote_path, local_path))

    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if key_file is not None:
            pkey = paramiko.RSAKey.from_private_key_file(key_file)
            ssh.connect(ip, 22, username, password, timeout=timeout, pkey=pkey)
        else:
            ssh.connect(ip, 22, username, password, timeout=timeout)
        obj_scp = scp.SCPClient(ssh.get_transport())
        obj_scp.get(remote_path, local_path)
        ssh.close()
        return True
    except Exception as e:
        raise e


def get_local_ip():
    """
    Get the local ip address --linux/windows
    :return:local_ip
    """

    if WINDOWS:
        local_ip = socket.gethostbyname(socket.gethostname())
    else:
        local_ip = os.popen("ifconfig | grep 'inet addr:' | grep -v '127.0.0.1' | cut -d: -f2 | awk '{print $1}' | "
                            "head -1").read().strip('\n')
    return local_ip


def get_local_hostname():
    """
    Get the local ip address --linux/windows
    :return:local_hostname
    """

    local_hostname = socket.gethostname()
    return local_hostname


def get_remote_ip(ip, username, password, ifname='eth0'):
    """
    Get the remote ip address --linux
    :param ip:
    :param username:
    :param password:
    :param ifname:
    :return: ip_list
    """
    cmd = "LANG=C ifconfig %s| grep 'inet addr' | grep -v '127.0.0.1' |awk -F ':' '{print $2}' | awk '{print $1}'" % ifname
    rc, output = ssh_cmd(ip, username, password, cmd)
    ip_list = output.strip('\n').split('\n')
    return ip_list


def get_remote_hostname(ip, username, password):
    """
    Get the hostname --linux
    :param ip:
    :param username:
    :param password:
    :return:hostname
    """

    logger.info('Call get_remote_hostname for <%s>...' % ip)
    cmd = "hostname"
    try:
        rc, output = ssh_cmd(ip, username, password, cmd)
        hostname = output.strip('\n')
    except Exception as e:
        logger.error(e)
        return False
    else:
        return hostname


if __name__ == '__main__':
    pass
