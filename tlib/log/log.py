# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

""" logging config
FYI:
https://docs.python.org/2/howto/logging-cookbook.html#logging-cookbook
https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/
http://blog.csdn.net/orangleliu/article/details/53896441
"""
import unittest

__all__ = [
    'debug', 'info', 'warning', 'error', 'critical',
    'init_logger', 'set_loglevel', 'get_inited_logger_name', 'basic_config',
    'ROTATION', 'INFINITE', 'parse_msg',
    'backtrace_info', 'backtrace_debug', 'backtrace_error', 'backtrace_critical',
    'debug_if', 'info_if', 'error_if', 'warn_if', 'critical_if', get_logger
]

import os
import re
import sys
import gzip
import shutil
import platform
import logging
import threading
import coloredlogs
from logging import handlers

from tlib import err


# ---------------------------
# --- Global for logging
# ---------------------------
ROTATION = 0
INFINITE = 1
INITED_LOGGER = []
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
DEBUG_FORMATE = '%(asctime)s %(name)s %(filename)s[%(lineno)d] [%(process)d:%(thread)d] %(levelname)s: %(message)s'
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

info = logging.info
warning = logging.warning
error = logging.error
debug = logging.debug
critical = logging.critical

# Add a new log level 21 -- DESCRIBE, usage: logging.log(21, 'mesage')
logging.addLevelName(21, 'DESCRIBE')


class _Singleton(object):
    """
    Make your class singeton

    example::

        from tlib import decorators

        @decorators.Singleton
        class YourClass(object):
            def __init__(self):
            pass
    """
    def __init__(self, cls):
        self.__instance = None
        self.__cls = cls
        self._lock = threading.Lock()

    def __call__(self, *args, **kwargs):
        self._lock.acquire()
        if self.__instance is None:
            self.__instance = self.__cls(*args, **kwargs)
        self._lock.release()
        return self.__instance


class _MsgFilter(logging.Filter):
    """Msg filters by log levels"""

    def __init__(self, msg_level=logging.WARNING):
        super(_MsgFilter, self).__init__()
        self.msg_level = msg_level

    def filter(self, record):
        if record.levelno >= self.msg_level:
            return False
        else:
            return logging.Filter.filter(self, record)


class _CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
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


@_Singleton
class _LoggerMan(object):
    _instance = None
    _mylogger = None
    _maxsize = 0
    _b_rotation = False
    _logfile = ''
    _logtype = ROTATION

    def __init__(self):
        pass

    @property
    def m_logger(self):
        if self._mylogger is None:
            raise err.LoggerException('The logger has not been initalized Yet. Call init_comlog first')
        return self._mylogger

    def set_logger(self, logger_name):
        if self._mylogger is not None:
            raise err.LoggerException('WARNING!!! The logger {0} has been initialized already.'.format(self._mylogger))
        logging.root = logging.RootLogger(logging.WARNING)
        logger = logging.getLogger(logger_name)
        self._mylogger = logger
        self._mylogger.handlers = []
        self._mylogger.setLevel(logging.DEBUG)

    def reset_logger(self, logger_name):
        if self._mylogger:
            del self._mylogger
        logging.root = logging.RootLogger(logging.WARNING)
        logger = logging.getLogger(logger_name)
        self._mylogger = logger
        # logging.root = logger
        self._mylogger.handlers = []
        self._mylogger.setLevel(logging.DEBUG)

    @property
    def is_initialized(self):
        """Initialized or not"""
        if self._mylogger is None:
            return False
        else:
            # self._mylogger.debug('{0} has been already initalized'.format(self._mylogger))
            return True

    @staticmethod
    def verify_path(file_path):
        if not os.path.isdir(file_path):
            try:
                os.makedirs(file_path)
            except OSError as e:
                print(e)

    def verify_logfile(self, logfile):
        logfile = logfile + '.log' if not logfile.endswith('.log') else logfile
        logfile_split = os.path.split(logfile)
        log_path = os.path.join(os.getcwd(), 'logs', logfile_split[0])
        self.verify_path(log_path)

        log_name = logfile_split[1]
        logfile = os.path.join(log_path, log_name)

        if not os.path.exists(logfile):
            try:
                if WINDOWS:
                    with open(logfile, 'w+') as fhandle:
                        fhandle.write('')
                else:
                    os.mknod(logfile)
            except Exception as e:
                raise err.LoggerException(e)
        elif not os.path.isfile(logfile):
            raise err.LoggerException('The log file exists. But NOT a regular file')

        return logfile

    def config_file_logger(self, logfile, loglevel=FILE_LEVEL, logtype=ROTATION,
                           maxsize=FILE_MAXBYTES, rotation_count=FILE_BACKUPCOUNT, compress_log=False, gen_wf=False):
        logfile = self.verify_logfile(logfile)
        # Config the file handler
        if logtype == ROTATION:
            if compress_log:
                fdhandler = _CompressedRotatingFileHandler(logfile, mode='a', maxBytes=maxsize,
                                                           backupCount=rotation_count)
            else:
                fdhandler = handlers.RotatingFileHandler(logfile, mode='a', maxBytes=maxsize,
                                                         backupCount=rotation_count, encoding='utf-8')
        else:
            fdhandler = logging.FileHandler(logfile, 'a', encoding='utf-8')
        formatter = logging.Formatter(FILE_FORMATE)
        fdhandler.setFormatter(formatter)
        fdhandler.setLevel(loglevel)
        if gen_wf:
            # add .wf handler
            file_wf = str(logfile) + '.wf'
            warn_handler = logging.FileHandler(file_wf, 'a', encoding='utf-8')
            warn_handler.setLevel(logging.WARNING)
            warn_handler.setFormatter(formatter)
            self._mylogger.addHandler(warn_handler)
            fdhandler.addFilter(_MsgFilter(logging.WARNING))

        self._mylogger.addHandler(fdhandler)

    def config_console_logger(self, log_level=CONSOLE_LEVEL, colored_console=True):
        # Config the console handler
        # print('print_console enabled, will print to stdout')
        if colored_console:
            coloredlogs.install(logger=self._mylogger, level=log_level, fmt=CONSOLE_FORMATE,
                                field_styles=DEFAULT_FIELD_STYLES, level_styles=DEFAULT_LEVEL_STYLES)
        else:
            formatter = logging.Formatter(fmt=CONSOLE_FORMATE, datefmt=DATE_FORMATE)
            streamhandler = logging.StreamHandler()
            streamhandler.setLevel(log_level)
            streamhandler.setFormatter(formatter)
            self._mylogger.addHandler(streamhandler)


def init_logger(logfile='debug.log', logger_name='test', log_level=FILE_LEVEL,
                log_type=ROTATION, maxsize=FILE_MAXBYTES, rotation_count=FILE_BACKUPCOUNT,
                output_logfile=True, compress_log=False, gen_wf=False,
                print_console=True, colored_console=True, reset_logger=False):
    """
    Initialize your logging

    :param logger_name:
        Unique logger name
    :param log_level:
        4 default levels: log.DEBUG log.INFO log.ERROR log.CRITICAL
    :param logfile:
        log file. Will try to create it if no existence
    :param log_type:
        Two type candidiates: log.ROTATION and log.INFINITE

        log.ROTATION will let logfile switch to a new one (30 files at most).
        When logger reaches the 30th logfile, will overwrite from the
        oldest to the most recent.

        log.INFINITE will write on the logfile infinitely
    :param maxsize:
        maxmum log size with byte
    :param rotation_count:
        maxmum log count with int
    :param output_logfile:
        output log to file
    :param compress_log:
        compress log
    :param gen_wf:
        print log msges with level >= WARNING to file (${logfile}.wf)
    :param print_console:
        print to stdout or not?
    :param colored_console:
        print to stdout colored
    :param reset_logger:
        reset logger

    *E.g.*
    ::
        import logging
        from tlib import log
        log.init_logger(
            '/home/work/test/test.log',
            'test'
        )
        log.info('test xxx')
        log.critical('test critical')

    """

    logger_man = _LoggerMan()

    # logging.root = logging.RootLogger(logging.WARNING)
    # new_logger = logging.getLogger(logger_name)
    if reset_logger:
        logger_man.reset_logger(logger_name)
    elif not logger_man.is_initialized:
        logger_man.set_logger(logger_name)
    else:
        # Not need init the initialized logger
        return logging.getLogger(logger_name)

    if output_logfile:
        logger_man.config_file_logger(logfile, log_level, log_type, maxsize, rotation_count, compress_log, gen_wf)
    if print_console:
        logger_man.config_console_logger(CONSOLE_LEVEL, colored_console)
    global INITED_LOGGER
    if logger_name not in INITED_LOGGER:
        INITED_LOGGER.append(logger_name)

    new_logger = logging.getLogger(logger_name)
    new_logger.info('Log path: {0}'.format(logfile))
    new_logger.debug('-' * 20 + '{0} Initialized Successfully'.format(new_logger) + '-' * 20)
    return new_logger


def get_logger(logfile='debug.log', logger_name='test', output_logfile=True, compress_log=False, gen_wf=False,
               print_console=True, colored_console=True, debug=False, reset_logger=False):
    if debug:
        global FILE_LEVEL, CONSOLE_LEVEL, CONSOLE_FORMATE, FILE_FORMATE
        FILE_LEVEL = logging.DEBUG
        CONSOLE_LEVEL = logging.DEBUG
        CONSOLE_FORMATE = DEBUG_FORMATE
        FILE_FORMATE = DEBUG_FORMATE

    test_logger = init_logger(logfile, logger_name, output_logfile=output_logfile, compress_log=compress_log,
                              gen_wf=gen_wf, print_console=print_console, colored_console=colored_console,
                              reset_logger=reset_logger)
    return test_logger


def _line(back=0):
    return sys._getframe(back + 1).f_lineno


def _file(back=0):
    return os.path.basename(sys._getframe(back + 1).f_code.co_filename)


def _proc_thd_id():
    return str(os.getpid()) + ':' + str(threading.current_thread().ident)


def _log_file_func_info(msg, back_trace_len=0):
    tmp_msg = ' * [%s] [%s:%s] ' % (_proc_thd_id(), _file(2 + back_trace_len), _line(2 + back_trace_len))

    msg = '%s%s' % (tmp_msg, msg)
    if isinstance(msg, unicode):
        return msg
    else:
        return msg.decode('utf8')


def get_inited_logger_name():
    """
    get initialized logger name
    """
    global INITED_LOGGER
    return INITED_LOGGER


def _fail_handle(msg, e):
    if not isinstance(msg, unicode):
        msg = msg.decode('utf8')
    print('{0}\nerror:{1}'.format(msg, e))


def backtrace_info(msg, back_trace_len=0):
    """
    info with backtrace support
    """
    try:
        msg = _log_file_func_info(msg, back_trace_len)
        logger_man = _LoggerMan()
        logger_man.m_logger.info(msg)
    except err.LoggerException:
        return
    except Exception as e:
        _fail_handle(msg, e)


def backtrace_debug(msg, back_trace_len=0):
    """
    debug with backtrace support
    """
    try:
        msg = _log_file_func_info(msg, back_trace_len)
        logger_man = _LoggerMan()
        logger_man.m_logger.debug(msg)
    except err.LoggerException:
        return
    except Exception as e:
        _fail_handle(msg, e)


def backtrace_warn(msg, back_trace_len=0):
    """
    warning msg with backtrace support
    """
    try:
        msg = _log_file_func_info(msg, back_trace_len)
        logger_man = _LoggerMan()
        logger_man.m_logger.warn(msg)
    except err.LoggerException:
        return
    except Exception as e:
        _fail_handle(msg, e)


def backtrace_error(msg, back_trace_len=0):
    """
    error msg with backtarce support
    """
    try:
        msg = _log_file_func_info(msg, back_trace_len)
        logger_man = _LoggerMan()
        logger_man.m_logger.error(msg)
    except err.LoggerException:
        return
    except Exception as error:
        _fail_handle(msg, error)


def backtrace_critical(msg, back_trace_len=0):
    """
    logging.CRITICAL with backtrace support
    """
    try:
        msg = _log_file_func_info(msg, back_trace_len)
        logger_man = _LoggerMan()
        logger_man.m_logger.critical(msg)
    except err.LoggerException:
        return
    except Exception as e:
        _fail_handle(msg, e)


def set_loglevel(logging_level):
    """
    change log level during runtime
    """
    logger_man = _LoggerMan()
    logger_man.m_logger.setLevel(logging_level)


def parse_msg(log_line):
    """
    return a dict if the line is valid.
    Otherwise, return None

    ::
        dict_info:= {
           'loglevel': 'DEBUG',
           'date': '2015-10-14',
           'time': '16:12:22,924',
           'pid': 8808,
           'tid': 1111111,
           'srcline': 'util.py:33',
           'msg': 'this is the log content'
        }

    """
    try:
        content = log_line[log_line.find(']'):]
        content = content[(content.find(']') + 1):]
        content = content[(content.find(']') + 1):].strip()
        regex = re.compile('[ \t]+')
        items = regex.split(log_line)
        loglevel, date, time_, _, pid_tid, src = items[0:6]
        pid, tid = pid_tid.strip('[]').split(':')
        return {
            'loglevel': loglevel.strip(':'),
            'date': date,
            'time': time_,
            'pid': pid,
            'tid': tid,
            'srcline': src.strip('[]'),
            'msg': content
        }
    except Exception as e:
        print(e)
        return None


def debug_if(bol, msg, back_trace_len=1):
    """log msg with critical loglevel if bol is true"""
    if bol:
        logging.debug(msg, back_trace_len)


def info_if(bol, msg, back_trace_len=1):
    """log msg with info loglevel if bol is true"""
    if bol:
        logging.info(msg, back_trace_len)


def error_if(bol, msg, back_trace_len=1):
    """log msg with error loglevel if bol is true"""
    if bol:
        logging.error(msg, back_trace_len)


def warn_if(bol, msg, back_trace_len=1):
    """log msg with error loglevel if bol is true"""
    if bol:
        logging.warn(msg, back_trace_len)


def critical_if(bol, msg, back_trace_len=1):
    """log msg with critical loglevel if bol is true"""
    if bol:
        logging.critical(msg, back_trace_len)


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
    if not os.path.isdir(log_path):
        try:
            os.makedirs(log_path)
        except OSError as e:
            print(e)

    # logging.basicConfig(level=FILE_LEVEL,
    #                     format=FILE_FORMATE,
    #                     datefmt=DATE_FORMATE,
    #                     filename=log_pathname,
    #                     filemode='w',
    #                     )
    console = logging.StreamHandler()
    console.setLevel(CONSOLE_LEVEL)
    formatter = logging.Formatter(fmt=CONSOLE_FORMATE, datefmt=DATE_FORMATE)
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
        logger.warning('test_1 hello,world')
        logger.debug('test_1 hello,world')
        logger.error('test_1 hello,world')
        logger.critical('test_1 hello,world')

    def test_2(self):
        logfile = "test_2.log"
        logger = get_logger(logfile, logger_name='test2', debug=True)
        logger.info('test_2 start ...')
        logger.warning('test_2 hello,world')
        logger.debug('test_2 hello,world')
        logger.error('test_2 hello,world')
        logger.critical('test_2 hello,world')

    def test_2_2(self):
        log_file = "test_2_2.log"
        basic_config(log_file)
        logger = logging.getLogger(__name__)
        logger.info('test_2_2 start ...')
        logger.warning('test_2_2 hello,world')
        logger.debug('test_2_2 hello,world')
        logger.error('test_2_2 hello,world')
        logger.critical('test_2_2 hello,world')

    def test_3(self):
        logger = get_logger(logger_name='test2', logfile='test.log', reset_logger=True)
        logger.info('test_3 start ...')
        logger.warning('test_3 hello,world')
        logger.debug('test_3 hello,world')
        logger.error('test_3 hello,world')
        logger.critical('test_3 hello,world')
        logger.log(21, 'test_3 hello,world')

    def test_4(self):
        logger = get_logger(logger_name='test2')
        logger.info('test_4 start ...')
        logger.warning('test_4 hello,world')


if __name__ == '__main__':
    # test
    # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(LogTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
