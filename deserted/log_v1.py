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
# summary log level
SUMMARY_LEVEL = logging.INFO
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
# summary log format
SUMMARY_FORMATE = '%(message)s'
# file log format
FILE_FORMATE_INFO = '%(asctime)s %(name)s %(levelname)s: %(message)s'
FILE_FORMATE_DEBUG = '%(asctime)s %(filename)s[%(lineno)d] [PID:%(process)d] [TID:%(thread)d] %(levelname)s: %(message)s'
# console log format
CONSOLE_FORMATE_INFO = '%(asctime)s %(name)s %(levelname)s: %(message)s'
CONSOLE_FORMATE_DEBUG = '%(asctime)s %(filename)s[%(lineno)d] [PID:%(process)d] [TID:%(thread)d] %(levelname)s: %(message)s'
CONSOLE_FORMATE = CONSOLE_FORMATE_INFO if (CONSOLE_LEVEL == logging.INFO) else CONSOLE_FORMATE_DEBUG
FILE_FORMATE = FILE_FORMATE_INFO  # if (FILE_LEVEL == logging.INFO) else FILE_FORMATE_DEBUG

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
    programname=dict(color='cyan'),
    name=dict(color='blue'))
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

    def __init__(self, log_file, logger_name='test', colored_console=True, output_logfile=True,
                 output_summary=False, debug=False, compress_log=True):
        super(Init, self).__init__()
        self.log_file = log_file + '.log' if not log_file.endswith('.log') else log_file
        self.log_file_split = os.path.split(self.log_file)
        self.log_path = os.path.join(os.getcwd(), 'log', self.log_file_split[0])
        self.log_name = self.log_file_split[1]
        self.summary_name = 'summary_' + self.log_name
        self.log_pathname = os.path.join(self.log_path, self.log_name)
        self.summary_pathname = os.path.join(self.log_path, self.summary_name)

        self.logger_name = logger_name
        self.colored_console = colored_console
        self.output_logfile = output_logfile
        self.output_summary = output_summary
        self.debug = debug
        self.compress_log = compress_log

        if self.debug:
            global FILE_LEVEL, CONSOLE_LEVEL, CONSOLE_FORMATE, FILE_FORMATE
            FILE_LEVEL = logging.DEBUG
            CONSOLE_LEVEL = logging.DEBUG
            CONSOLE_FORMATE = CONSOLE_FORMATE_DEBUG
            FILE_FORMATE = FILE_FORMATE_DEBUG

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
        if self.output_summary:
            self.logging_config_summary_hander()

    def verify_path(self, log_path):
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

    def logging_config_summary_hander(self):
        summary_logger_name = self.logger_name + ".summary"
        summary_logger = logging.getLogger(summary_logger_name)
        summary_logger.setLevel(logging.DEBUG)

        if self.compress_log:
            summary_log = CompressedRotatingFileHandler(self.summary_pathname, mode='a', maxBytes=FILE_MAXBYTES,
                                                        backupCount=FILE_BACKUPCOUNT)
        else:
            summary_log = logging.handlers.RotatingFileHandler(self.summary_pathname, mode='a', maxBytes=FILE_MAXBYTES,
                                                               backupCount=FILE_BACKUPCOUNT)
        # summary_log = logging.handlers.RotatingFileHandler(self.summary_pathname, 'a',FILE_MAXBYTES, FILE_BACKUPCOUNT)
        summary_log.setLevel(SUMMARY_LEVEL)
        summary_log.setFormatter(logging.Formatter(SUMMARY_FORMATE))
        summary_logger.addHandler(summary_log)

    def get_log_pathname(self):
        if self.output_logfile and self.output_summary:
            return self.log_pathname, self.summary_pathname
        elif self.output_logfile:
            return self.log_pathname
        elif self.output_summary:
            return self.summary_pathname
        else:
            return None


def get_logger(log_file='debug.log', logger_name='test', colored_console=True, output_logfile=True,
               output_summary=False, debug=False):
    if not logging.getLogger(logger_name).handlers or log_file != 'debug.log':
        obj_log = Init(log_file, logger_name, colored_console, output_logfile, output_summary, debug=debug)
        logging.getLogger(logger_name).info('log_path:{log_path}'.format(log_path=obj_log.get_log_pathname()))
    if output_summary:
        test_logger = logging.getLogger(logger_name)
        summary_logger = logging.getLogger(logger_name + ".summary")
        return test_logger, summary_logger
    else:
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
        logger.info('hello,world')
        logger.warning('hello,world')
        logger.debug('hello,world')
        logger.error('hello,world')
        logger.critical('hello,world')

    def test_2(self):
        obj_log = Init(log_file='test_2', output_summary=True)
        print(obj_log.get_log_pathname())
        logger = logging.getLogger(__name__)
        logger.info('test_2 start ...')
        logger.info('hello,world')
        logger.warning('hello,world')
        logger.debug('hello,world')
        logger.error('hello,world')
        logger.critical('hello,world')
        logger.log(21, 'hello,world')

        logger_s = logging.getLogger('summary')
        logger_s.critical('summary: hello,world')
        logger_s.debug('summary: hello,world')

    def test_3(self):
        my_logger, summary_logger = get_logger('C:\\test\\test.log', output_summary=True)
        my_logger1, summary_logger1 = get_logger(output_summary=True)
        my_logger.info('info 1111111')
        my_logger.log(21, 'level-21 1111111')
        summary_logger.error('summary error: 22222222')
        my_logger1.info('info 1111111')
        summary_logger1.error('summary error: 22222222')


if __name__ == '__main__':
    # test
    # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(LogTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
