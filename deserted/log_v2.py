# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

r""" logging config
FYI:
https://docs.python.org/2/howto/logging-cookbook.html#logging-cookbook
https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/
http://blog.csdn.net/orangleliu/article/details/53896441
"""

import os
import sys
import logging
import logging.config
import logging.handlers
import gzip
import shutil
import platform
import coloredlogs
import unittest

# =============================
# --- Global Value
# =============================

# ---------------------------
# --- Global for logging
# ---------------------------
# file log level
FILE_LEVEL = logging.DEBUG
# console log level
CONSOLE_LEVEL = logging.INFO
# RotatingFileHandler backupCount
FILE_BACKUPCOUNT = 5
# RotatingFileHandler maxBytes
FILE_MAXBYTES = 20 * 1024 * 1024
# date formate
DATE_FORMATE = '%Y-%m-%d %H:%M:%S'
# log format
INFO_FORMATE = '%(asctime)s %(name)s %(levelname)s: %(message)s'
DEBUG_FORMATE = '%(asctime)s %(filename)s[%(lineno)d] [PID:%(process)d] [TID:%(thread)d] %(levelname)s: %(message)s'
CONSOLE_FORMATE = INFO_FORMATE if (CONSOLE_LEVEL == logging.INFO) else DEBUG_FORMATE
FILE_FORMATE = INFO_FORMATE  # if (FILE_LEVEL == logging.INFO) else DEBUG_FORMATE

# ---------------------------
# --- Global for coloredlogs
# ---------------------------
# Windows requires special handling and the first step is detecting it :-).
WINDOWS = sys.platform.startswith('win')
# Optional external dependency (only needed on Windows).
NEED_COLORAMA = WINDOWS
"""
Whether bold fonts can be used in default styles (a boolean).
This is disabled on Windows because in my (admittedly limited) experience the
ANSI escape sequence for bold font is simply not translated by Colorama,
instead it's printed to the terminal without any translation.
"""
CAN_USE_BOLD_FONT = (not NEED_COLORAMA)
# Mapping of log format names to default font styles.
DEFAULT_FIELD_STYLES = dict(
    asctime=dict(color='green'),
    hostname=dict(color='magenta'),
    levelname=dict(color='green', bold=CAN_USE_BOLD_FONT),
    programname=dict(color='blue'),
    name=dict(color='cyan'))
# Mapping of log level names to default font styles
DEFAULT_LEVEL_STYLES = dict(
    spam=dict(color='green', faint=True),
    debug=dict(color='green'),
    verbose=dict(color='blue'),
    info=dict(),
    describ=dict(color='green'),
    notice=dict(color='magenta'),
    warning=dict(color='yellow'),
    success=dict(color='green', bold=CAN_USE_BOLD_FONT),
    error=dict(color='red'),
    critical=dict(color='red', bold=CAN_USE_BOLD_FONT))


# ===================================================================
# --- Solution 1: config multi-hander
# Usage:
# install(log_file)
# logger = logging.getLogger()
# ===================================================================
class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = "%s.%d.gz" % (self.baseFilename, i)
                dfn = "%s.%d.gz" % (self.baseFilename, i + 1)
                if os.path.exists(sfn):
                    # print "%s -> %s" % (sfn, dfn)
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.baseFilename + ".1"
            if os.path.exists(dfn):
                os.remove(dfn)
            # Issue 18940: A file may not have been created if delay is True.
            if os.path.exists(self.baseFilename):
                os.rename(self.baseFilename, dfn)
            # Compress it.
            with open(dfn, 'rb') as f_in, gzip.open('{}.gz'.format(dfn), 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
                os.remove(dfn)
        if platform.python_version().strip() == '2.7.12':
            if not self.delay:
                self.stream = self._open()


class Init(object):
    """logging Init"""

    def __init__(self, log_file, logger_name='test', colored_console=True, output_logfile=True, debug=False,
                 compress_log=True):
        super(Init, self).__init__()
        self.log_file = log_file + '.log' if not log_file.endswith('.log') else log_file
        self.log_file_split = os.path.split(self.log_file)
        self.log_path = os.path.join(os.getcwd(), 'log', self.log_file_split[0])
        self.log_name = self.log_file_split[1]
        self.log_pathname = os.path.join(self.log_path, self.log_name)

        self.logger_name = logger_name
        self.colored_console = colored_console
        self.output_logfile = output_logfile
        self.debug = debug
        self.compress_log = compress_log

        if self.debug:
            global FILE_LEVEL, CONSOLE_LEVEL, CONSOLE_FORMATE, FILE_FORMATE
            FILE_LEVEL = logging.DEBUG
            CONSOLE_LEVEL = logging.DEBUG
            CONSOLE_FORMATE = DEBUG_FORMATE
            FILE_FORMATE = DEBUG_FORMATE

        # Add a new log level 21 -- DESCRIBE, usage: logging.log(21, 'mesage')
        logging.addLevelName(21, 'DESCRIBE')

        self.logger = logging.getLogger(self.logger_name)
        self.logger.addHandler(logging.NullHandler())

        self.logger.handlers = []
        self.logger.setLevel(logging.DEBUG)

        self.verify_path(self.log_path)
        self.logging_config_console_hander()
        if self.output_logfile:
            self.logging_config_file_hander()

    @staticmethod
    def verify_path(log_path):
        if not os.path.isdir(log_path):
            try:
                os.makedirs(log_path)
            except OSError as e:
                print(e)

    def logging_config_console_hander(self):
        if self.colored_console:
            coloredlogs.install(logger=self.logger, level=CONSOLE_LEVEL, fmt=CONSOLE_FORMATE,
                                field_styles=DEFAULT_FIELD_STYLES, level_styles=DEFAULT_LEVEL_STYLES)
        else:
            console_log = logging.StreamHandler()
            console_log.setLevel(CONSOLE_LEVEL)
            formatter = logging.Formatter(CONSOLE_FORMATE)
            console_log.setFormatter(formatter)
            self.logger.addHandler(console_log)

    def logging_config_file_hander(self):
        if self.compress_log:
            file_log = CompressedRotatingFileHandler(self.log_pathname, mode='a', maxBytes=FILE_MAXBYTES,
                                                     backupCount=FILE_BACKUPCOUNT)
        else:
            file_log = logging.handlers.RotatingFileHandler(self.log_pathname, mode='a', maxBytes=FILE_MAXBYTES,
                                                            backupCount=FILE_BACKUPCOUNT)
        # file_log = logging.handlers.RotatingFileHandler(self.log_pathname, 'a', FILE_MAXBYTES, FILE_BACKUPCOUNT)
        file_log.setLevel(FILE_LEVEL)
        file_log.setFormatter(logging.Formatter(FILE_FORMATE))
        self.logger.addHandler(file_log)


def get_logger(log_file='debug.log', logger_name='test', colored_console=True, output_logfile=True, debug=False):
    if not logging.getLogger(logger_name).handlers or log_file != 'debug.log':
        obj_log = Init(log_file, logger_name, colored_console, output_logfile, debug=debug)
        logging.getLogger(logger_name).info('log_path:{log_path}'.format(log_path=obj_log.log_pathname))
    test_logger = logging.getLogger(logger_name)
    return test_logger


# ===================================================================
# --- Solution 2: logging.basicConfig
# out put: console and log file
# ===================================================================
def basic_config(log_file):
    # add the handler to the root logger
    log_file = log_file + '.log' if not log_file.endswith('.log') else log_file
    log_file_split = os.path.split(log_file)
    log_path = os.path.join(os.getcwd(), 'log', log_file_split[0])
    log_name = log_file_split[1]
    log_pathname = os.path.join(log_path, log_name)

    logging.basicConfig(level=FILE_LEVEL,
                        format=FILE_FORMATE,
                        datefmt=DATE_FORMATE,
                        filename=log_pathname,
                        filemode='w')
    console = logging.StreamHandler()
    console.setLevel(CONSOLE_LEVEL)
    formatter = logging.Formatter(CONSOLE_FORMATE)
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)


# ===================================================================
# --- Solution 3: config ini
# ===================================================================
def init_config():
    pass


# ===================================================================
# --- Solution 4: config json
# ===================================================================
def json_config():
    pass


# ===================================================================
# --- unittest
# ===================================================================

class LogTestCase(unittest.TestCase):
    """docstring for LogTestCase"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_1(self):
        log_file = "test_1.log"
        basic_config(log_file)
        logger = logging.getLogger(__name__)
        logger.info('test_1 start ...')
        logger.info('test_1 hello,world')
        logger.warning('test_1 hello,world')
        logger.debug('test_1 hello,world')
        logger.error('test_1 hello,world')
        logger.critical('test_1 hello,world')

    def test_2(self):
        logging.getLogger(__name__).disabled = True

        Init(log_file='test_2', logger_name='test')
        logger = logging.getLogger('test')
        logger.info('test_2 start ...')
        logger.info('test_2 hello,world')
        logger.warning('test_2 hello,world')
        logger.debug('test_2 hello,world')
        logger.error('test_2 hello,world')
        logger.critical('test_2 hello,world')
        logger.log(21, 'test_2 hello,world')

    def test_3(self):
        logger = get_logger()
        logger.info('test_3 start ...')
        logger.info('test_3 hello,world')
        logger.warning('test_3 hello,world')
        logger.debug('test_3 hello,world')
        logger.error('test_3 hello,world')
        logger.critical('test_3 hello,world')
        logger.log(21, 'test_3 hello,world')


if __name__ == '__main__':
    # test
    # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(LogTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
