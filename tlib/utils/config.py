# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/9/23 18:27
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""Config"""

import os
import sys
import json

import xlrd
from tlib import log

PY2 = sys.version_info[0] == 2
if PY2:
    ENCODING = None
    string_types = basestring,  # (str, unicode)
    import ConfigParser as configparser
else:
    ENCODING = 'utf-8'
    string_types = str, bytes
    import configparser


# =============================
# --- Global Value
# =============================
my_logger = log.get_logger()


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


if __name__ == '__main__':
    pass
