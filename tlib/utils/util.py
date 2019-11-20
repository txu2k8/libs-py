# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""utils"""
import os
import sys
import string
import random
import time
import hashlib
import socket
import subprocess
import scp
import inspect
import paramiko
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
from progressbar import ProgressBar, Percentage, Bar, RotatingMarker, ETA
try:
    import pexpect
except ImportError:
    pass

from tlib import log
from tlib.retry import retry, retry_call
# from tlib.ds import escape
from tlib.bs import ip_to_int, int_to_ip, strsize_to_byte

# =============================
# --- Global Value
# =============================
logger = log.get_logger()
# --- OS constants
POSIX = os.name == "posix"
WINDOWS = os.name == "nt"
PY2 = sys.version_info[0] == 2
ENCODING = None if PY2 else 'utf-8'
DD_BINARY = os.path.join(os.getcwd(), r'bin\dd\dd.exe') if WINDOWS else 'dd'
MD5SUM_BINARY = os.path.join(os.getcwd(), r'bin\git\md5sum.exe') if WINDOWS else 'md5sum'


def print_for_call(func):
    """
    Enter <func>.
    Exit from <func>. result: "rtn"
    """

    @wraps(func)
    def _wrapped(*args, **kwargs):
        logger.info('Enter {name}.'.format(name=func.__name__))
        rtn = func(*args, **kwargs)
        logger.info('Exit from {name}. result: {rtn_code}'.format(name=func.__name__, rtn_code=rtn))
        return rtn

    return _wrapped


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

    logger.info('>> Create file: {0}'.format(path_name))
    original_path = os.path.split(path_name)[0]
    if not os.path.isdir(original_path):
        try:
            os.makedirs(original_path)
        except OSError as e:
            raise Exception(e)

    size = strsize_to_byte(total_size)
    line_count = size // line_size
    unaligned_size = size % line_size

    with open(path_name, mode) as f:
        logger.info("write file: {0}".format(path_name))
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
    logger.debug('Get MD5: {0}'.format(f_name))
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


def mkdir_path_if_not_exist(local_path):
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


def is_ping_ok(ip, tries=30):
    """
    Check if the machine can ping successful
    :param ip:
    :param tries:
    :return:(bool) True / False
    """

    if WINDOWS:
        cmd = "ping %s" % ip
    elif POSIX:
        cmd = "ping -c1 %s" % ip
    else:
        cmd = "ping %s" % ip

    for x in range(tries):
        rc, output = run_cmd(cmd, expected_rc='ignore')
        if "ttl=" in output.lower():
            logger.info(ip + ' is Reachable')
            return True
        else:
            logger.warning(ip + ' is Not Reachable')
            time.sleep(3)
            continue
    else:
        return False


def get_reachable_ip(ip_list, ping_retry=3):
    for ip in ip_list:
        if is_ping_ok(ip, ping_retry):
            return ip
    else:
        raise Exception('All ips not reachable! {0}'.format(ip_list))


def get_unused_ip(ip_start, wasteful=True):
    """
    get unused ip
    :param ip_start:
    :param wasteful: If True, will skip the ip_start
    :return:
    """
    ip_start_num = ip_to_int(ip_start)
    if wasteful:
        ip_start_num += 1
    while True:
        new_ip = int_to_ip(ip_start_num)
        if is_ping_ok(new_ip, tries=1):
            ip_start_num += 1
            continue
        else:
            break
    return new_ip


def get_current_time():
    return int(time.time() * 1000)


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
                std_out_err = stdout.decode("utf-8", 'ignore')  # escape(stdout)
            else:
                std_out_err = stderr.decode("utf-8", 'ignore')  # escape(stderr)
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

    prompt = ['# ', '>>> ', '> ', r'\$ ']
    login_expect = [
        'Are you sure you want to continue connecting', '[P|p]assword: '
    ]
    login_expect.extend(prompt)

    try:
        if key_file:
            login_cmd = 'ssh -i {key} {user}@{host}'.format(
                key=key_file, user=username, host=ip)
        else:
            login_cmd = 'ssh {user}@{host}'.format(user=username, host=ip)

        logger.info(login_cmd)
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


def centos_enable_root(ip, username='centos', password=None, key_file=None,
                       root_pwd='password'):
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
    cmd = 'sed -i ' \
          's/"PasswordAuthentication no"/"PasswordAuthentication yes"/g ' \
          '/etc/ssh/sshd_config;service sshd restart'
    child = pexpect_ssh_login(ip, username, password, key_file)

    try:
        logger.info(passwd_root)
        logger.info(root_pwd)
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
        logger.info(cmd)
        child.sendline(cmd)
        child.expect('Redirecting to /bin/systemctl restart sshd.service')
        child.close(force=True)
    except pexpect.EOF as e:
        raise Exception('[-] Error: {0}'.format(e))
    except pexpect.TIMEOUT as e:
        raise Exception('[-] TimeOut: {0}'.format(e))

    return True


# =============== multi thread / process ===============

def multi_dd_w(file_list, file_min_size=1024, file_max_size=1024):
    """
    multi thread dd write
    :param file_list: file full path name list
    :param file_min_size:
    :param file_max_size:
    :return:
    """

    f_min_size = strsize_to_byte(file_min_size)
    f_max_size = strsize_to_byte(file_max_size)
    block_size_list = ['512', '1k', '4k', '16k', '64k', '512k', '1M']

    bs = random.choice(block_size_list)
    bs_size = strsize_to_byte(bs)
    i_path = '/dev/random' if WINDOWS else '/dev/urandom'

    pool = ThreadPoolExecutor(max_workers=10)
    futures = []
    for f_path_name in file_list:
        rand_f_size = random.randint(f_min_size, f_max_size)
        # logger.debug('FILE SIZE: %s byte' % str(rand_f_size))
        if rand_f_size < 1024*1024:
            bs = rand_f_size
            dd_count = 1
        else:
            dd_count = rand_f_size // bs_size
        futures.append(pool.submit(dd_read_write, i_path, f_path_name, bs, str(dd_count)))

    pool.shutdown()
    future_result = [future.result() for future in futures]
    result = False if False in future_result else True
    return result


def multi_xls_w():
    pass
    # TODO


def multi_file_w(file_list, file_min_size=1024, file_max_size=1024, mode='w+'):
    """
    Multi Write files by "with open as f: f.write()"
    r 只能读
    r+ 可读可写 不会创建不存在的文件 从顶部开始写 会覆盖之前此位置的内容
    w+ 可读可写 如果文件存在 则覆盖整个文件不存在则创建
    w 只能写 覆盖整个文件 不存在则创建
    a 只能写 从文件底部添加内容 不存在则创建
    a+ 可读可写 从文件顶部读取内容 从文件底部添加内容 不存在则创建
    :param file_list:
    :param file_min_size:
    :param file_max_size:
    :param mode:
    :return:
    """

    f_min_size = strsize_to_byte(file_min_size)
    f_max_size = strsize_to_byte(file_max_size)

    pool = ThreadPoolExecutor(max_workers=10)
    futures = []
    for f_path_name in file_list:
        rand_f_size = random.randint(f_min_size, f_max_size)
        # logger.debug('FILE SIZE: %s byte' % str(rand_f_size))
        futures.append(pool.submit(create_file, f_path_name, rand_f_size, 128, mode))

    pool.shutdown()
    future_result = [future.result() for future in futures]
    result = False if False in future_result else True
    return result


def multi_get_md5(file_list):
    """
    get file_list md5
    :param file_list:
    :return:
    """

    pool = ThreadPoolExecutor(max_workers=5)
    results = pool.map(get_file_md5, file_list)
    pool.shutdown()

    files_md5 = {}
    for rtn in results:
        if not rtn:
            return False
        else:
            files_md5.update(rtn)

    return files_md5


if __name__ == "__main__":
    pass
