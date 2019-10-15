# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""utils"""
import os
import string
import random
import time
from functools import wraps
from progressbar import ProgressBar, Percentage, Bar, RotatingMarker, ETA
import hashlib

from tlib import log
from tlib.retry import retry

# =============================
# --- Global Value
# =============================
logger = log.get_logger()
# --- OS constants
POSIX = os.name == "posix"
WINDOWS = os.name == "nt"
DD_BINARY = os.path.join(os.getcwd(), 'bin\dd\dd.exe') if WINDOWS else 'dd'
MD5SUM_BINARY = os.path.join(os.getcwd(), 'bin\git\md5sum.exe') if WINDOWS else 'md5sum'


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

    size = strsize_to_size(total_size)
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


if __name__ == "__main__":
    pass
    rc, output = ssh_cmd('10.25.119.1', 'root', 'password', 'df -h')
    print(output.split(b'\n'))
