# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""utils"""
import os
import sys
import re
import string
import base64
import random
import time
from datetime import date, datetime
from functools import wraps
from collections import OrderedDict
from progressbar import ProgressBar, Percentage, Bar, RotatingMarker, ETA
import json
import xlrd
import scp
import yaml
import hashlib
import inspect
import subprocess
import paramiko
import socket

from tlib import log
from tlib.retry import retry, retry_call

# =============================
# --- Global Value
# =============================
my_logger = log.get_logger()
# --- OS constants
POSIX = os.name == "posix"
WINDOWS = os.name == "nt"
DD_BINARY = os.path.join(os.getcwd(), 'bin\dd\dd.exe') if WINDOWS else 'dd'
MD5SUM_BINARY = os.path.join(os.getcwd(), 'bin\git\md5sum.exe') if WINDOWS else 'md5sum'
PY2 = sys.version_info[0] == 2
if PY2:
    ENCODING = None
    string_types = basestring,  # (str, unicode)
    import ConfigParser as configparser
else:
    ENCODING = 'utf-8'
    string_types = str, bytes
    import configparser


def print_for_call(func):
    """
    Enter <func>.
    Exit from <func>. result: "rtn"
    """

    @wraps(func)
    def _wrapped(*args, **kwargs):
        my_logger.info('Enter {name}.'.format(name=func.__name__))
        rtn = func(*args, **kwargs)
        my_logger.info('Exit from {name}. result: {rtn_code}'.format(name=func.__name__, rtn_code=rtn))
        return rtn

    return _wrapped


def base64_encode(original_string):
    return base64.b64encode(original_string)


def base64_decode(encoded_string):
    return base64.b64decode(encoded_string)


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


# parameters that apply to all methods
GLOBAL_PARAMS = ("timeout",)


def query_params(*func_query_params):
    """
    Decorator that pops all accepted parameters from method's kwargs and puts
    them in the params argument.
    :param func_query_params:
    :return:
    """

    def _wrapper(func):
        @wraps(func)
        def _wrapped(*args, **kwargs):
            params = {}
            if "params" in kwargs:
                params = kwargs.pop("params").copy()
            for p in func_query_params + GLOBAL_PARAMS:
                if p in kwargs:
                    v = kwargs.pop(p)
                    if v is not None:
                        params[p] = escape(v)

            # don't treat ignore and request_timeout as other params to avoid escaping
            for p in ("ignore", "request_timeout"):
                if p in kwargs:
                    params[p] = kwargs.pop(p)
            return func(*args, params=params, **kwargs)

        return _wrapped

    return _wrapper


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

        rc = p.returncode
        if output:
            # (stdout, stderr) = p.communicate()
            stdout, stderr = p.stdout.read(), p.stderr.read()
            if rc == 0:
                std_out_err = escape(stdout)
            else:
                std_out_err = escape(stderr)
                my_logger.warning('Output: rc={0}, stdout/stderr:\n{1}'.format(rc, std_out_err))
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
    # run_cmd('ssh-keygen -f "/root/.ssh/known_hosts" -R "{0}"'.format(ip))
    ssh = paramiko.SSHClient()
    # ssh.load_system_host_keys()
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
                                         'docker_image': docker_image}, tries=tries, delay=delay, logger=my_logger)
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

    my_logger.info('scp %s %s@%s:%s' % (local_path, username, ip, remote_path))
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


def sleep_progressbar(seconds):
    """
    Print a progress bar, total value: seconds
    :param seconds:
    :return:
    """

    # widgets = ['Progress: ', Percentage(), ' ', Bar(marker=RotatingMarker('-=>')), ' ', Timer(), ' | ', ETA()]
    widgets = ['Progress: ', Percentage(), ' ', Bar(marker=RotatingMarker('-=>')), ' ', ETA()]
    pbar = ProgressBar(widgets=widgets, maxval=seconds).start()
    for i in range(seconds):
        pbar.update(1 * i + 1)
        time.sleep(1)
    pbar.finish()


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


# tools
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
    mem_size_byte = strsize_to_size(mem_size_str)
    s = ' ' * mem_size_byte
    time.sleep(reserve_time)
    return True


if __name__ == "__main__":
    pass
    rc, output = ssh_cmd('10.25.119.1', 'root', 'password', 'df -h')
    print(output.split(b'\n'))
