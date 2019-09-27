# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/9/23 18:22
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com


"""数据结构"""

import sys
import base64
from datetime import date, datetime
from collections import OrderedDict

import yaml
from tlib import log

PY2 = sys.version_info[0] == 2
if PY2:
    ENCODING = None
    string_types = basestring,  # (str, unicode)
else:
    ENCODING = 'utf-8'
    string_types = str, bytes

# =============================
# --- Global Value
# =============================
logger = log.get_logger()


# 字符处理
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


# list/dict 处理
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
        logger.error("Please input the correct base value, should be 'key' or 'value'")
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


if __name__ == '__main__':
    pass
