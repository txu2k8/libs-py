# !/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#                                                        version: v1.0.0
#                                                             by: Tao.Xu
#                                                           date: 11/28/2018
#                                                      copyright: N/A
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NO INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
##############################################################################

r""" utils
"""

import os
import sys
import re
import string
import random
import base64
import shutil
import subprocess
import time
from datetime import date, datetime
from collections import OrderedDict
from progressbar import ProgressBar, Percentage, Bar, RotatingMarker, ETA
import scp
import xlrd
import json
import paramiko
import pexpect
import inspect
import socket
import hashlib
import yaml

from utils import log
from utils.retry import retry, retry_call

PY2 = sys.version_info[0] == 2
if PY2:
    ENCODING = None
    string_types = basestring,  # (str, unicode)
    import ConfigParser as configparser
    reload(sys)
    sys.setdefaultencoding('utf-8')
else:
    ENCODING = 'utf-8'
    string_types = str, bytes
    import configparser
    from imp import reload
    reload(sys)

# =============================
# --- Global Value
# =============================
my_logger = log.get_logger()

# --- OS constants
POSIX = os.name == "posix"
WINDOWS = os.name == "nt"
LINUX = sys.platform.startswith("linux")
OSX = sys.platform.startswith("darwin")
FREEBSD = sys.platform.startswith("freebsd")
OPENBSD = sys.platform.startswith("openbsd")
NETBSD = sys.platform.startswith("netbsd")
BSD = FREEBSD or OPENBSD or NETBSD
SUNOS = sys.platform.startswith("sunos") or sys.platform.startswith("solaris")
AIX = sys.platform.startswith("aix")
DD_BINARY = os.path.join(os.getcwd(), 'bin\dd\dd.exe') if WINDOWS else 'dd'
MD5SUM_BINARY = os.path.join(os.getcwd(), 'bin\git\md5sum.exe') if WINDOWS else 'md5sum'


class TimeoutError(Exception):
    pass


def print_for_call(func):
    """
    Wrapper function.
    """

    def wrapper_func(*args, **kwargs):
        my_logger.info('Enter {name}.'.format(name=func.__name__))
        rtn = func(*args, **kwargs)
        my_logger.info('Exit from {name}. result: {rtn_code}'.format(name=func.__name__, rtn_code=rtn))
        return rtn

    return wrapper_func


def escape(value):
    """
    Escape a single value of a URL string or a query parameter. If it is a list
    or tuple, turn it into a comma-separated string first.
    :param value:
    :return: escape value
    """

    # make sequences into comma-separated stings
    if isinstance(value, (list, tuple)):
        value = ",".join(value)

    # dates and datetimes into isoformat
    elif isinstance(value, (date, datetime)):
        value = value.isoformat()

    # make bools into true/false strings
    elif isinstance(value, bool):
        value = str(value).lower()

    # don't decode bytestrings
    elif isinstance(value, bytes):
        return value

    # encode strings to utf-8
    if isinstance(value, string_types):
        if PY2 and isinstance(value, unicode):
            return value.encode("utf-8")
        if not PY2 and isinstance(value, str):
            return value.encode("utf-8")

    return str(value)


def progressbar_k(sleep_time):
    """
    Print a progress bar, total value: sleep_time(seconds)
    :param sleep_time:
    :return:
    """

    widgets = ['Progress: ', Percentage(), ' ', Bar(marker=RotatingMarker('>-=')), ' ', ETA()]
    pbar = ProgressBar(widgets=widgets, maxval=sleep_time).start()
    for i in range(sleep_time):
        pbar.update(1 * i + 1)
        time.sleep(1)
    pbar.finish()


def get_config_ini(ini_file, section, key):
    """
    Get config.ini section->key->value
    [section]
    key = value

    :param ini_file:
    :param section:
    :param key:
    :return:value
    """

    try:
        config = configparser.ConfigParser()
        config.read(ini_file)
        value = config.get(section, key)
    except Exception as e:
        raise Exception(e)
    else:
        return value


def get_config_items_ini(ini_file, section):
    """
    Get config.ini section all key->value
    [section]
    key = value

    :param ini_file:
    :param section:
    :return: (dict) key=value
    """

    kv = {}

    try:
        config = configparser.ConfigParser()
        config.read(ini_file)
        opts = config.options(section)
        for opt in opts:
            v = eval(config.get(section, opt))
            kv[opt] = v
    except Exception as e:
        raise Exception(e)
    else:
        return kv


def set_config_ini(ini_file, section, **kwargs):
    """
    Set config.ini section->key->value
    [section]
    key = value

    :param ini_file:
    :param section:
    :param kwargs: key=value
    :return:
    """

    modified = False
    try:
        config = configparser.ConfigParser()
        if not os.path.exists(ini_file):
            with open(ini_file, 'w') as f:
                f.write('')
                f.flush()

        config.read(ini_file)
        if not config.has_section(section):
            config.add_section(section)
            modified = True

        for option_key, option_value in kwargs.items():
            config.set(section, option_key, option_value)
            modified = True

        if modified:
            with open(ini_file, 'w') as fd:
                config.write(fd)
                fd.flush()
    except Exception as e:
        raise Exception(e)


def get_config_xls(xls_path, wb_name):
    """
    get config from excel file
    :param xls_path:
    :param wb_name:
    :return: row list
    """

    xls_fullpath = os.path.join(os.getcwd(), xls_path)
    print('Read config from {0}, wb_name:{1} ...'.format(xls_fullpath, wb_name))
    try:
        data = xlrd.open_workbook(xls_fullpath)
    except Exception as e:
        raise Exception(e)

    table = data.sheet_by_name(wb_name)
    nrows = table.nrows
    # colnames = table.row_values(0)
    row_list = []
    for rownum in range(0, nrows):
        row = table.row_values(rownum)
        if not row:
            break

        row_list.append(row)

    return row_list


def subprocess_popen_cmd(cmd_spec, output=True, timeout=7200):
    """
    Executes command and Returns (rc, output) tuple
    :param cmd_spec: Command to be executed
    :param output: A flag for collecting STDOUT and STDERR of command execution
    :param timeout
    :return:
    """

    my_logger.info('Execute: {cmds}'.format(cmds=cmd_spec))
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

        if output:
            # (stdout, stderr) = p.communicate()
            (stdout, stderr) = p.stdout.read(), p.stderr.read()
            (rtn_code, std_out_err) = (p.returncode, stdout.decode('UTF-8', 'ignore')) if p.returncode == 0 else \
                (p.returncode, stderr.decode('UTF-8', 'ignore'))
            if rtn_code != 0:
                my_logger.warning('Output: returncode {r_code}, stdout/stderr:\n{r_out}'.format(r_code=rtn_code, r_out=std_out_err))
        else:
            (rtn_code, std_out_err) = (p.returncode, '')
        # p.stdout.close()
        # p.stderr.close()
        # p.kill()
        return rtn_code, std_out_err
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
                            tries=tries, delay=delay, logger=my_logger)

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
    # if os.name == "posix":
    #     run_cmd('ssh-keygen -f "/root/.ssh/known_hosts" -R "{0}"'.format(ip))
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if docker_image:
        cmd_spec = "docker run -i --rm --network host -v /dev:/dev -v /etc:/etc --privileged {image} bash " \
                   "-c '{cmd}'".format(image=docker_image, cmd=cmd_spec)
    my_logger.info('Execute: ssh {0}@{1} {2}'.format(username, ip, cmd_spec))
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
        std_out, std_err = stdout.read().decode('UTF-8', 'ignore'), stderr.read().decode('UTF-8', 'ignore')
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
                                         'docker_image': docker_image}, tries=tries, delay=delay, logger=my_logger)
    rc = -1 if stderr else 0
    output = stdout + stderr if stderr else stdout
    if isinstance(expected_rc, str) and expected_rc.upper() == 'IGNORE':
        return rc, output

    if rc != expected_rc:
        raise Exception('%s(): Failed command: %s\nMismatched RC: Received [%d], Expected [%d]\nError: %s' % (
            method_name, cmd_spec, rc, expected_rc, output))
    return rc, output


def ssh_l_cmd(ip, username, password, cmd_spec):
    """
    ssh -l username ip, only support linux VM
    :param ip:
    :param username:
    :param password:
    :param cmd_spec:
    :return:
    """

    ssh_newkey = 'Are you sure you want to continue connecting'
    child = pexpect.spawn('ssh -l {user} {host} {cmd}'.format(user=username, host=ip, cmd=cmd_spec), encoding=ENCODING)
    rtn_1 = child.expect([pexpect.TIMEOUT, ssh_newkey, 'password: '])
    if rtn_1 == 0:  # Timeout
        raise Exception(child.before + child.after)
    if rtn_1 == 1:  # SSH does not have the public key. Just accept it.
        child.sendline('yes')
        child.expect('password: ')
        rtn_2 = child.expect([pexpect.TIMEOUT, 'password: '])
        if rtn_2 == 0:  # Timeout
            raise Exception(child.before + child.after)
    child.sendline(password)
    return child.before


@retry(tries=3, delay=3)
def pexpect_ssh_login(ip, username, password=None, key_file=None, timeout=720):
    """
    This runs a command on the remote host. This could also be done with the
        pxssh class, but this demonstrates what that class does at a simpler level.
        This returns a pexpect.spawn object. This handles the case when you try to
        connect to a new host and ssh asks you if you want to accept the public key
        fingerprint and continue connecting.
    :param ip:
    :param username:
    :param password:
    :param key_file:
    :param timeout:
    :return:
    """

    prompt = ['# ', '>>> ', '> ', '\$ ']
    login_expect = ['Are you sure you want to continue connecting', '[P|p]assword: ']
    login_expect.extend(prompt)

    try:
        if key_file:
            login_cmd = 'ssh -i {key} {user}@{host}'.format(key=key_file, user=username, host=ip)
        else:
            login_cmd = 'ssh {user}@{host}'.format(user=username, host=ip)

        my_logger.info(login_cmd)
        child = pexpect.spawn(login_cmd, timeout=timeout, encoding=ENCODING)
        # child.logfile = sys.stdout
        ret = child.expect(login_expect)
        if ret == 0:
            child.sendline('yes')
            ret = child.expect(login_expect)
        if ret == 1:
            child.sendline(password)
            ret = child.expect(login_expect)
        if ret > 1:
            print('SSH Login success ...')
            return child
    except pexpect.EOF as e:
        raise Exception('[-] Error Connecting, {0}'.format(e))
    except pexpect.TIMEOUT as e:
        raise Exception('[-] TimeOut Connecting, {0}'.format(e))


def pexpect_ssh_cmd(ip, username, password, cmd_spec, expect_kv_list=None, key_file=None, timeout=720):
    """
    This runs a command on the remote host. This could also be done with the
    pxssh class, but this demonstrates what that class does at a simpler level.
    This returns a pexpect.spawn object. This handles the case when you try to
    connect to a new host and ssh asks you if you want to accept the public key
    fingerprint and continue connecting.

    :param ip:
    :param username:
    :param password:
    :param cmd_spec:
    :param expect_kv_list: eg: [('input ip', '10.180.119.1'), ('input user', 'root')]
    :param key_file:
    :param timeout:
    :return:
    """

    prompt = ['# ', '>>> ', '> ', '\$ ']
    login_expect = ['Are you sure you want to continue connecting', '[P|p]assword: ']
    login_expect.extend(prompt)

    try:
        if key_file:
            login_cmd = 'ssh -i {key} {user}@{host}'.format(key=key_file, user=username, host=ip)
        else:
            login_cmd = 'ssh {user}@{host}'.format(user=username, host=ip)

        my_logger.info(login_cmd)
        child = pexpect.spawn(login_cmd, timeout=timeout, encoding=ENCODING)
        # child.logfile = sys.stdout
        ret = child.expect(login_expect)
        if ret == 0:
            child.sendline('yes')
            ret = child.expect(login_expect)
        if ret == 1:
            child.sendline(password)
            ret = child.expect(login_expect)
        if ret > 1:
            my_logger.info('SSH Login success ...')
    except pexpect.EOF as e:
        raise Exception('[-] Error Connecting, {0}'.format(e))
    except pexpect.TIMEOUT as e:
        raise Exception('[-] TimeOut Connecting, {0}'.format(e))

    my_logger.info('Execute:{0}'.format(cmd_spec))
    child.sendline(cmd_spec)
    expect_key_list = [expect_key for expect_key, expect_value in expect_kv_list]
    expect_key_list.extend(prompt)
    show = False
    timeout_try = 0
    buffer_next = child.buffer.strip('\r\n')
    while child.isalive():
        try:
            index = child.expect(expect_key_list, timeout=60)
            timeout_try = 0
            buffer_next = child.buffer.strip('\r\n')
            my_logger.info("{0}{1}".format(child.after, child.buffer))
            if expect_key_list[index] in prompt:
                break
            semd_cmd = expect_kv_list[index][1]
            my_logger.info("index:{0}, sendline('{1}')".format(index, semd_cmd))
            child.sendline(str(semd_cmd))
            # expect_key_list.pop(index)
            # expect_kv_list.pop(index)
            show = False
            if index == len(expect_kv_list) - 1:
                show = True
                child.expect(prompt, timeout=30)
                break
        except pexpect.EOF:
            my_logger.debug("{0}".format(child.buffer))
            my_logger.debug('EOF: sendline('')')
            child.sendline('')
        except pexpect.TIMEOUT:
            timeout_try += 1
            if timeout_try > 0 and (child.buffer.strip('\r\n') != buffer_next):
                buffer_next = child.buffer.strip('\r\n')
                if show:
                    my_logger.info("{0}".format(child.buffer))
                    progressbar_k(300)
                else:
                    buffer_list = child.buffer.strip('\n').split('\n')
                    if buffer_list:
                        my_logger.info("{0}".format(buffer_list[-1]))
                my_logger.warning('TIMEOUT: sendline('')')
                child.sendline()
                show = True
                try:
                    child.expect(prompt, timeout=30)
                    break
                except Exception as e:
                    my_logger.debug(e)
                timeout_try = 0
            else:
                time.sleep(10)
        finally:
            my_logger.debug('-' * 30)
            my_logger.debug('buffer: {0}'.format(child.buffer))
            my_logger.debug('before: {0}'.format(child.before))
            my_logger.debug('after: {0}'.format(child.after))
            my_logger.debug('-' * 30)
    child.close(force=True)
    return True


def centos_enable_root(ip, username='centos', password=None, key_file=None, root_pwd='password'):
    """
    enable centos root user and set root password
    :param ip:
    :param username:
    :param password:
    :param key_file:
    :param root_pwd:
    :return:
    """

    passwd_root = 'sudo passwd root'
    cmd = 'sed -i s/"PasswordAuthentication no"/"PasswordAuthentication yes"/g /etc/ssh/sshd_config;service sshd restart'
    child = pexpect_ssh_login(ip, username, password, key_file)

    try:
        my_logger.info(passwd_root)
        my_logger.info(root_pwd)
        child.sendline(passwd_root)
        child.expect('New password:')
        child.sendline(root_pwd)
        child.expect('Retype new password:')
        child.sendline(root_pwd)
        child.expect('all authentication tokens updated successfully.')
        child.sendline('su root')
        child.expect('Password:')
        child.sendline(root_pwd)
        child.expect('root@.*#')
        my_logger.info(cmd)
        child.sendline(cmd)
        child.expect('Redirecting to /bin/systemctl restart sshd.service')
        child.close(force=True)
    except pexpect.EOF as e:
        raise Exception('[-] Error: {0}'.format(e))
    except pexpect.TIMEOUT as e:
        raise Exception('[-] TimeOut: {0}'.format(e))

    return True


def pexpect_ssh_cli(ip, username, password, cmd_spec, expect_kv_list=None, key_file=None, timeout=720, show=False):
    """
    pexpect ssh run cli
    run cmd -> expect output
    :param ip:
    :param username:
    :param password:
    :param cmd_spec:
    :param expect_kv_list: k:cmd, v:output
    :param key_file:
    :param timeout:
    :return:
    """

    expect_kv_list.append(('exit', 'exit'))
    prompt = ['~/setup# ', '# ', '>>> ', '> ', '\$ ']
    child = pexpect_ssh_login(ip, username, password, key_file, timeout)

    my_logger.info('Execute:{0}'.format(cmd_spec))
    child.sendline(cmd_spec)
    ret = child.expect(prompt)
    if ret == 0:
        my_logger.info('Enter CLI({0}) ...'.format(cmd_spec))
    else:
        raise Exception('Execute: {0} failed!'.format(cmd_spec))

    timeout_try = 0
    buffer_next = child.buffer.strip('\r\n')
    for cmd, expect in expect_kv_list:
        my_logger.info("CLI Execute: {0}".format(cmd))
        my_logger.debug("CLI Expected: {0}".format(expect))

        try:
            child.sendline(cmd)
            child.expect([expect], timeout=60)
            timeout_try = 0
            buffer_next = child.buffer.strip('\r\n')
            output_msg = "output:\n{0}".format(child.before + child.after)
            if show:
                my_logger.info(output_msg)
            else:
                my_logger.debug(output_msg)
        except pexpect.EOF:
            my_logger.warning('EOF ...')
            my_logger.debug("{0}".format(child.buffer))
        except pexpect.TIMEOUT:
            timeout_try += 1
            if timeout_try > 0 and (child.buffer.strip('\r\n') != buffer_next):
                buffer_next = child.buffer.strip('\r\n')
                if show:
                    my_logger.info("{0}".format(child.buffer))
                    progressbar_k(300)
                else:
                    buffer_list = child.buffer.strip('\n').split('\n')
                    if buffer_list:
                        my_logger.info("{0}".format(buffer_list[-1]))
                my_logger.warning('TIMEOUT ...')
                show = True
                try:
                    child.expect(prompt, timeout=30)
                    break
                except Exception as e:
                    my_logger.debug(e)
                timeout_try = 0
            else:
                time.sleep(10)
        finally:
            my_logger.debug('-' * 30)
            my_logger.debug('buffer: {0}'.format(child.buffer))
            my_logger.debug('before: {0}'.format(child.before))
            my_logger.debug('after: {0}'.format(child.after))
            my_logger.debug('-' * 30)
    child.close(force=True)
    return True


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

    my_logger.info('scp %s %s@%s:%s' % (local_path, username, ip, remote_path))
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

    my_logger.debug('scp %s@%s:%s %s' % (username, ip, remote_path, local_path))

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


@retry(tries=3, delay=1)
def shutil_copytree(src_path, dest_path):
    """
    shutil.copytree(src_path, dest_path)
    :param src_path:
    :param dest_path:
    :return:
    """

    my_logger.info("shutil.copytree(%s, %s)" % (src_path, dest_path))
    if os.path.isdir(dest_path):
        try:
            shutil.rmtree(dest_path)
        except OSError as e:
            raise e
    try:
        shutil.copytree(src_path, dest_path)
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

    my_logger.info('Call get_remote_hostname for <%s>...' % ip)
    cmd = "hostname"
    try:
        rc, output = ssh_cmd(ip, username, password, cmd)
        hostname = output.strip('\n')
    except Exception as e:
        my_logger.error(e)
        return False
    else:
        return hostname


def get_freebsd_kern_boottime(ip, username, password):
    """
    get freebsd kern boot time
    sysctl kern.boottime
    :param ip:
    :param username:
    :param password:
    :return:
    """

    cmd = 'sysctl kern.boottime'
    kern_boottime = ''
    try:
        rc, output = ssh_cmd(ip, username, password, cmd)
        my_logger.info(output)
        pattern = re.compile(r'}\s(.+)')
        kern_boottime = pattern.findall(output.strip('\n'))[0]
    except Exception as e:
        my_logger.error(e)

    return kern_boottime


def generate_random_string(str_len=16):
    """
    generate random string
    return ''.join(random.sample((string.ascii_letters + string.digits)*str_len, str_len))
    :param str_len: byte
    :return:random_string
    """

    base_string = string.ascii_letters + string.digits
    # base_string = string.printable
    base_string_len = len(base_string)
    multiple = 1
    if base_string_len < str_len:
        multiple = (str_len // base_string_len) + 1

    return ''.join(random.sample(base_string * multiple, str_len))


def create_file(path_name, total_size='4k', line_size=128, mode='w+'):
    """
    create original file, each line with line_number, and specified line size
    :param path_name:
    :param total_size:
    :param line_size:
    :param mode: w+ / a+
    :return:
    """

    my_logger.info('>> Create file: {0}'.format(path_name))
    original_path = os.path.split(path_name)[0]
    if not os.path.isdir(original_path):
        try:
            os.makedirs(original_path)
        except OSError as e:
            raise Exception(e)

    size = strsize_to_size(total_size)
    line_count = size // line_size
    unaligned_size = size % line_size

    with open(path_name, mode) as f:
        my_logger.info("write file: {0}".format(path_name))
        for line_num in range(0, line_count):
            random_sting = generate_random_string(line_size - 2 - len(str(line_num))) + '\n'
            f.write('{line_num}:{random_s}'.format(line_num=line_num, random_s=random_sting))
        if unaligned_size > 0:
            f.write(generate_random_string(unaligned_size))
        f.flush()
        os.fsync(f.fileno())

    file_md5 = hash_md5(path_name)
    return file_md5


def dd_read_write(if_path, of_path, bs, count, skip='', seek='', oflag='', timeout=1800):
    """
    dd read write
    :param if_path: read path
    :param of_path: write path
    :param bs:
    :param count:
    :param skip: read offset
    :param seek: write offset
    :param oflag: eg: direct
    :param timeout: run_cmd timeout second
    :return:
    """

    dd_cmd = "{0} if={1} of={2} bs={3} count={4}".format(DD_BINARY, if_path, of_path, bs, count)
    if oflag:
        dd_cmd += " oflag={0}".format(oflag)
    if skip:
        dd_cmd += " skip={0}".format(skip)
    if seek:
        dd_cmd += " seek={0}".format(seek)

    rc, output = run_cmd(dd_cmd, 0, tries=2, timeout=timeout)

    return rc, output


@retry(tries=2, delay=3)
def md5sum(f_name):
    """
    get md5sum on POSIX by cmd: md5sum file_name
    :param f_name:file full path
    :return:
    """

    md5sum_cmd = "{md5_binary} {file_name}".format(md5_binary=MD5SUM_BINARY, file_name=f_name)
    rc, output = run_cmd(md5sum_cmd, 0, tries=3)

    return output.split(' ')[0].split('\\')[-1]


@retry(tries=2, delay=3)
def hash_md5(f_name):
    """
    returns the hash md5 of the opened file
    :param f_name: file full path
    :return:(string) md5_value 32-bit hexadecimal string.
    """
    my_logger.debug('Get MD5: {0}'.format(f_name))
    try:
        h_md5 = hashlib.md5()
        with open(f_name, "rb") as f:
            for chunk in iter(lambda: f.read(), b""):
                h_md5.update(chunk)
        return h_md5.hexdigest()
    except Exception as e:
        raise Exception(e)


@retry(tries=2, delay=3)
def hash_sha1(f_name):
    """
    returns the hash sha1 of the opened file
    :param f_name:file full path
    :return:(string) sha1_value 40-bit hexadecimal string.
    """
    try:
        h_sha1 = hashlib.sha1()
        with open(f_name, "rb") as f:
            for chunk in iter(lambda: f.read(), b""):
                h_sha1.update(chunk)
        return h_sha1.hexdigest()
    except Exception as e:
        raise Exception(e)


@retry(tries=2, delay=3)
def hash_sha256(f_name):
    """
    returns the hash sha256 of the opened file
    :param f_name:file full path
    :return: (string) sha256_value 64-bit hexadecimal string.
    """
    try:
        h_sha256 = hashlib.sha256()
        with open(f_name, "rb") as f:
            for chunk in iter(lambda: f.read(), b""):
                h_sha256.update(chunk)
        return h_sha256.hexdigest()
    except Exception as e:
        raise Exception(e)


def get_file_md5(f_name):
    """
    get file md5
    :param f_name:file full path
    :return: dict {file_name: md5}
    """

    # md5_info = {f_name: md5sum(f_name)}
    md5_info = {os.path.split(f_name)[-1]: md5sum(f_name)}

    return md5_info


def div_list_len(original_list, div_len):
    """
    Yield successive len-sized chunks from original_list
    original_list ==> some of div_list, each div list len=div_len
    :param original_list:
    :param div_len:
    :return:
    """

    for i in range(0, len(original_list), div_len):
        yield original_list[i:i + div_len]


def div_list_count(original_list, count):
    """
    Yield successive count chunks from original_list
    original_list ==> count of div_list
    :param original_list:
    :param count:
    :return:
    """

    original_list_len = len(original_list)
    if original_list_len < count:
        yield original_list
    else:
        div_len = original_list_len // count
        for i in range(0, original_list_len, div_len):
            yield original_list[i:i + div_len]


def get_list_intersection(list_a, list_b):
    """
    Get the intersection between list_a and list_b
    :param list_a:
    :param list_b:
    :return:(list) list_intersection
    """

    assert isinstance(list_a, list)
    assert isinstance(list_b, list)
    return list((set(list_a).union(set(list_b))) ^ (set(list_a) ^ set(list_b)))


def get_list_difference(list_a, list_b):
    """
    Get the difference set between list_a and list_b
    :param list_a:
    :param list_b:
    :return:(list) list_difference
    """

    assert isinstance(list_a, list)
    assert isinstance(list_b, list)
    return list(set(list_a).symmetric_difference(set(list_b)))


def delete_list_duplicated(list_data):
    """
    Delete the list duplicated key_value
    :param list_data:
    :return:(list) new_list_data
    """

    assert isinstance(list_data, list)
    return sorted(set(list_data), key=list_data.index)


def delete_list_match(list_data, keyword):
    """
    Remove the match item in list_data
    :param list_data:
    :param keyword:
    :return:(list) list_data
    """

    assert isinstance(list_data, list)
    keyword_item_list = [x for x in list_data if keyword in x]
    for item in keyword_item_list:
        list_data.remove(item)

    return list_data


def invert_dict_key_value(dict_data):
    """
    invert the dict: key <==> value
    :param dict_data:
    :return:(dict) new_dict_data
    """

    rtn_dict = {}
    for k, v in dict_data.items():
        rtn_dict[v] = k
    return rtn_dict


def sort_dict(dict_data, base='key', reverse=False):
    """
    sort dict by base key
    :param dict_data: dict_data
    :param base: 'key' or 'value'
    :param reverse: descending order if True, else if False:ascending
    :return:(list) list_data
    """

    if base == 'key':
        return sorted(dict_data.items(), key=lambda d: d[0], reverse=reverse)
    elif base == 'value':
        return sorted(dict_data.items(), key=lambda d: d[1], reverse=reverse)
    else:
        my_logger.error("Please input the correct base value, should be 'key' or 'value'")
        return False


def sort_list_by_keylist(list_data, keylist, base):
    """
    sort the list_data follow the keylist
    :param list_data:
    :param keylist:
    :param base:
    :return:
    """
    sorted_list = []
    for sorted_key in keylist:
        for item in list_data:
            if sorted_key == item[base]:
                sorted_list.append(item)
    return sorted_list


def ordered_yaml_load(yaml_path, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))

    OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping)
    with open(yaml_path) as stream:
        return yaml.load(stream, OrderedLoader)


def ordered_yaml_dump(data, stream=None, Dumper=yaml.SafeDumper, **kwds):
    class OrderedDumper(Dumper):
        pass

    def _dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            data.items())

    OrderedDumper.add_representer(OrderedDict, _dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)


def json_load(json_file_path):
    """
    Load json files: json.load
    :param json_file_path:
    :return:
    """

    my_logger.log(21, 'Load json {0}'.format(json_file_path))
    try:
        with open(json_file_path, 'r') as f:
            json_info = json.load(f)
        return json_info
    except Exception as e:
        raise Exception('Load json file failed.\n{err}'.format(err=e))


def strsize_to_size(str_size):
    """
    convert str_size such as 1K,1M,1G,1T to size 1024 (byte)
    :param str_size:such as 1K,1M,1G,1T
    :return:size (byte)
    """

    str_size = str(str_size) if not isinstance(str_size, str) else str_size

    if not bool(re.search('[a-z_A-Z]', str_size)):
        return int(str_size)

    if not bool(re.search('[0-9]', str_size)):
        raise Exception('Not support string size: {}'.format(str_size))

    regx = re.compile(r'(\d+)\s*([a-z_A-Z]+)', re.I)
    tmp_size_unit = regx.findall(str_size)[0]
    tmp_size = int(tmp_size_unit[0])
    tmp_unit = tmp_size_unit[1]
    if bool(re.search('K', tmp_unit, re.IGNORECASE)):
        size_byte = tmp_size * 1024
    elif bool(re.search('M', tmp_unit, re.IGNORECASE)):
        size_byte = tmp_size * 1024 * 1024
    elif bool(re.search('G', tmp_unit, re.IGNORECASE)):
        size_byte = tmp_size * 1024 * 1024 * 1024
    elif bool(re.search('T', tmp_unit, re.IGNORECASE)):
        size_byte = tmp_size * 1024 * 1024 * 1024 * 1024
    else:
        raise Exception("Error string size, just support KB/MB/GB/TB (IGNORECASE)")

    return size_byte


def ip_to_num(ip):
    """
    convert ip(ipv4) address to a int num
    :param ip:
    :return: int num
    """

    lp = [int(x) for x in ip.split('.')]
    return lp[0] << 24 | lp[1] << 16 | lp[2] << 8 | lp[3]


def num_to_ip(num):
    """
    convert int num to ip(ipv4) address
    :param num:
    :return:
    """

    ip = ['', '', '', '']
    ip[3] = (num & 0xff)
    ip[2] = (num & 0xff00) >> 8
    ip[1] = (num & 0xff0000) >> 16
    ip[0] = (num & 0xff000000) >> 24
    return '%s.%s.%s.%s' % (ip[0], ip[1], ip[2], ip[3])


def is_ping_ok(ip, retry=30):
    """
    Check if the machine can ping successful
    :param ip:
    :param retry:
    :return:(bool) True / False
    """

    if WINDOWS:
        cmd = "ping %s" % ip
    elif POSIX:
        cmd = "ping -c1 %s" % ip
    else:
        cmd = "ping %s" % ip

    for x in range(retry):
        rc, output = run_cmd(cmd, expected_rc='ignore')
        if "ttl=" in output.lower():
            my_logger.info(ip + ' is Reachable')
            return True
        else:
            time.sleep(3)
            my_logger.warning(ip + ' is Not Reachable')
            continue
    else:
        return False


def get_unused_ip(ip_start, wasteful=True):
    """
    get unused ip
    :param ip_start:
    :param wasteful: If True, will skip the ip_start
    :return:
    """
    ip_start_num = ip_to_num(ip_start)
    if wasteful:
        ip_start_num += 1
    while True:
        new_ip = num_to_ip(ip_start_num)
        if is_ping_ok(new_ip, retry=1):
            ip_start_num += 1
            continue
        else:
            break
    return new_ip


def get_current_time():
    return int(time.time() * 1000)


def base64_encode(original_string):
    return base64.b64encode(original_string)


def base64_decode(encoded_string):
    return base64.b64decode(encoded_string)


def verify_path(local_path):
    """
    verify the local path exist, if not create it
    :param local_path:
    :return:
    """
    if not os.path.isdir(local_path):
        try:
            os.makedirs(local_path)
        except OSError as e:
            raise Exception(e)


def python_major_version():
    return sys.version_info.major


if __name__ == "__main__":
    pass
    restart_sv_list = [('e', 'd'), ('a', 's')]
    sv_type_seq_list = ['a', 'b', 'c', 'e']
    print(sort_list_by_keylist(restart_sv_list, sv_type_seq_list, 0))
