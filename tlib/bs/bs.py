# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/9/23 18:11
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com


"""数字计算处理：
1. 辗转相除
2. 任意进制相互转化
3. 最大公约数
"""

import re


def successive_division(n, x):  # 辗转相除法
    while n:
        yield n % x  # 将余数返回
        n //= x  # 剩下余数


def binary_system(x, base_x, base_y):
    """
    转化进制
    :param x: 字符串非负整数
    :param base_x: 字符串的进制
    :param base_y: 转化的进制
    :return: 被转化的进制
    """
    if base_y <= 1 or base_x <= 1:  # 进制不可能小于1
        raise ValueError('进制不可能小于1')
    if not isinstance(x, (int, str)):
        raise ValueError('x值应该是int类型或者字符串类型')
    if isinstance(x, int):
        if x < 1:
            raise ValueError('x的值不可能小于1')
        x = str(x)
    y = int(x, base_x)  # 将其他进制先转为十进制
    # 在将十进制转为其他进制,并且将大于10的数字用ASCII值来表示,第一个ASCII是97小写的a
    m = map(lambda b: chr(b + 87) if b >= 10 else str(b), successive_division(y, base_y))
    bs = ''.join(m)[::-1]  # 返回字符串并且反转
    if int(bs, base_y) == y:  # 检验进制是否正确
        return bs
    raise ValueError('验证进制错误!')  # 如果检验失败,返回错误


def gcd(m, n):
    """最大公约数 -- greatest common divisor"""
    if n == 0:
        m, n = m, n
    while m != 0:
        m, n = n % m, m
    return n


def ip_to_int(ip):
    """
    convert ip(ipv4) address to a int num
    :param ip:
    :return: int num
    """

    lp = [int(x) for x in ip.split('.')]
    return lp[0] << 24 | lp[1] << 16 | lp[2] << 8 | lp[3]


def int_to_ip(num):
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


def strsize_to_byte(str_size):
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
        raise Exception("Error string input, fmt:<int>KB/MB/GB/TB(IGNORECASE)")

    return size_byte


if __name__ == '__main__':
    print(binary_system(2542, 7, 12))  # 将7进制的2542转为12进制
    print(gcd(97 * 2, 97 * 3))  # 最大公约数
    print(ip_to_int('192.168.1.1'))  # IP地址转换为整数
    print(int_to_ip(3232235778))  # 整数转换为IP地址
    print(strsize_to_byte('4k'))  # 字符 "4k" 转换为整数，单位 byte
