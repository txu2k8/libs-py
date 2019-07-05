"""
This class is used for logging.

:author: txu
"""
import datetime

import os
import sys
import time
import unittest
import logging
import logging.config
from logging import FileHandler
# import colorlog

TRACE_LEVEL = 5


class Logger(logging.Logger):
    """
    This class is custom logger for python framework.

    This class can be used the same way as the standard library logging.logger:

    >> from log import Logger
    >> logger = Logger.get_logger(__name__)
    >> logger.debug("my debug message")

    of course you can use all debug functions provided by python logging
    standard lib (debug, info, warning, error, etc.).

    All messages are displayed on both standard output and in a common file.
    This common log file is in log directory and its name starts with date.
    Its name contains jenkins job id and build id if the corresponding
    environment variables are available.

    For messages sent from a test case file, a subdirectory is created in
    log directory with the test case name (zz0000_hello_world). A file
    is created which name contains the date, the test case name, and
    jenkins job and build id if available. This log file contains only
    test case messages. It can be used to debug the test case itself.

    As soon as there is an issue in the framework or in a library, the
    common log file must be used to investigate.

    All messages from test cases automatically reach the common file thanks
    to the "propagate" property of python standard logging library.
    """

    logging.addLevelName(TRACE_LEVEL, "TRACE")
    jenkins_job_name = "JOB_NAME"
    jenkins_build_number = "BUILD_NUMBER"
    jenkins_joburl = "JOB_URL"
    jenkinsJob = os.environ.get(jenkins_job_name)
    jenkinsBuild = os.environ.get(jenkins_build_number)
    jenkinsJobURL = os.environ.get(jenkins_joburl)
    date = datetime.datetime.now().strftime("%Y%m%d-" + "%H%M%S.%f")  # + time.tzname[1]
    log_dir_name = "log"
    if not os.path.exists(log_dir_name):
        os.makedirs(log_dir_name)
    filename = log_dir_name + os.sep + date
    if jenkinsJob:
        jenkinsJob = jenkinsJob.split('/')[-1]
        filename += "_job_" + jenkinsJob
    if jenkinsBuild:
        filename += "_build_" + jenkinsBuild
    if jenkinsJobURL is None:
        jenkinsJobURL = ""
    filename_full = filename
    filename_full += "_full.log"
    filename += "_debug.log"
    loggerConfig = {
        "version": 1,
        "loggers": {
            "": {
                "handlers": ["console", "defaultFile", "fullFile"],
                "level": "TRACE"
            },
            "paramiko": {
                "level": "CRITICAL"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "stream": sys.stdout,
                "formatter": "colored"
            },
            "defaultFile": {
                "class": "logging.FileHandler",
                "formatter": "defaultFormatter",
                "level": "DEBUG",
                "filename": filename
            },
            "fullFile": {
                "class": "logging.FileHandler",
                "formatter": "defaultFormatter",
                "level": "TRACE",
                "filename": filename_full
            }
        },
        "formatters": {
            "defaultFormatter": {
                "format": "%(asctime)s - %(levelname)-8s - %(threadName)-12s - %(filename)-25.25s - "
                          "%(lineno)-4d - %(message)s"
            },
            "colored": {
                '()': 'colorlog.ColoredFormatter',
                "format": "%(bold)s%(asctime)s %(reset)s - %(log_color)s%(levelname)-8s %(reset)s - "
                          "%(threadName)12s - %(filename)-25.25s - %(lineno)-4d - %(message)s"
            }
        }
    }
    logging.config.dictConfig(loggerConfig)
    if jenkinsBuild:
        filename = jenkinsBuild + "/artifact/log/"
    logging.getLogger().debug("\nGlobal PostBuild Log directory is: " + jenkinsJobURL + filename)
    current_tc_log_dir = str()
    post_build_test_logfile = ''

    @staticmethod
    def get_logger(name):
        """
        This method is logger configuration.
        Goal of this is to customize logger, to have different logging level for console and file and file_full.

        It returns logger with the specified name.

        :param str name: test case/class name
        :return: Logger object
        :rtype: object

        >> from log import Logger
        >> LOGGER = Logger.get_logger(__name__)
        >> LOGGER.info('info level log message')
        """
        logger_name = name
        logger_name_full = name + "_full"
        if "ci_" in name or "stf" in name:
            logging.getLogger().debug("\n\n{0} {1} {2}".format('+'*33, name, '+'*33))
            short_name = name.split(".")[-1]
            handler = name + "FileHandler"
            handler_full = name + "FileHandler" + "_full"
            Logger.loggerConfig["loggers"][name] = {
                "handlers": [handler],
                "level": "DEBUG"
            }
            Logger.loggerConfig["loggers"][logger_name_full] = {
                "handlers": [handler_full],
                "level": "TRACE"
            }
            Logger.loggerConfig["handlers"][handler] = Logger.loggerConfig["handlers"]["defaultFile"].copy()
            Logger.loggerConfig["handlers"][handler_full] = Logger.loggerConfig["handlers"]["fullFile"].copy()
            log_dir = Logger.log_dir_name + os.sep + short_name
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            filename = log_dir + os.sep + Logger.date
            if Logger.jenkinsJob:
                filename += "_job_" + Logger.jenkinsJob
            if Logger.jenkinsBuild:
                filename += "_build_" + Logger.jenkinsBuild
            filename += "_" + short_name + "_TC_skeleton.log"
            Logger.loggerConfig["handlers"][handler]["filename"] = filename
            if Logger.jenkinsBuild:
                filename = Logger.jenkinsBuild + "/artifact/" + filename
            Logger.post_build_test_logfile = ("Test PostBuild Log file is: " + Logger.jenkinsJobURL + "/" + filename)
        else:
            logger_name = None

        logging.config.dictConfig(Logger.loggerConfig)
        return logging.getLogger(logger_name)

    @staticmethod
    def get_log_dir(name):
        """
        This method returns string type: log/<name>, or None in case when 'ci_' is not in 'name'.

        :param str name: string
        :return: string log/<name>
        :rtype: str

        >> from log import Logger
        >> LOGDIR = Logger.getLogDir(__name__)
        """
        if "ci_" in name or "stf" in name:
            short_name = name.split(".")[-1]
            return Logger.log_dir_name + os.sep + short_name
        else:
            return None

    def trace(self, message, *args, **kws):
        """
        This method adds a new logger level below DEBUG.

        No return value for the method.

        :param str message: the message
        :param args: the positional arguments
        :param kws: the keyword arguments

        >> from log import Logger
        >> LOGGER = Logger.get_logger(__name__)
        >> LOGGER.trace("Low level message")
        """
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, message, args, **kws)

    logging.Logger.trace = trace

    @staticmethod
    def switch_to_tc_log(logger, tc_name, loop=None):
        """
        This method:
        - removes the main handler from the logger
        - creates and adds the TC handler to the logger

        It returns the main handler, the TC handler and the link to the TC log file.

        :param Logger logger: Logger object
        :param str tc_name: test case name
        :param int loop: number of loops, the default value is None
        :return: tuple (main handler, TC handler, link to the TC log file)
        :rtype: tuple

        >> from log import Logger
        >> logger = Logger.get_logger(__name__)
        >> mainHandler, mainHandlerFull, message = Logger.switchToTcLog(logger, testItem)
        """
        # copy "DefaultFile handler"
        old_handler = logger.handlers[1]
        old_handler_full = logger.handlers[2]
        # create filename
        jenkins_job_name = "JOB_NAME"
        jenkins_build_number = "BUILD_NUMBER"
        jenkins_joburl = "JOB_URL"
        jenkins_job = os.environ.get(jenkins_job_name)
        jenkins_build = os.environ.get(jenkins_build_number)
        jenkins_job_url = os.environ.get(jenkins_joburl)
        date = Logger.date
        log_dir_name = "log/" + tc_name
        tc_filename = log_dir_name + os.sep + date
        if jenkins_job:
            jenkins_job = jenkins_job.split('/')[-1]
            tc_filename += "_job_" + jenkins_job
        if jenkins_build:
            tc_filename += "_build_" + jenkins_build
        if jenkins_job_url is None:
            jenkins_job_url = ""
        if loop is None:
            tc_filename_full = tc_filename + "_" + tc_name + '_full.log'
            tc_filename = tc_filename + "_" + tc_name + "_debug.log"
        else:
            tc_filename = tc_filename + "_" + tc_name + "_" + str(loop)
            tc_filename_full = tc_filename + '_full.log'
            tc_filename += "_debug.log"
        # copy the old_handler formatter
        formatter = old_handler.__getattribute__("formatter")
        # create the new handler to replace "DefaultFile" handler
        new_handler = FileHandler(tc_filename)
        new_handler_full = FileHandler(tc_filename_full)
        new_handler.setLevel('DEBUG')
        new_handler_full.setLevel(TRACE_LEVEL)
        new_handler.setFormatter(formatter)
        new_handler_full.setFormatter(formatter)
        # change main handler
        logger.removeHandler(old_handler)
        logger.removeHandler(old_handler_full)
        logger.addHandler(new_handler)
        logger.addHandler(new_handler_full)

        # create url to WS directory
        filename = log_dir_name + "/"
        if jenkins_build:
            filename = jenkins_build + "/artifact/" + filename
        message = jenkins_job_url + "/" + filename
        Logger.current_tc_log_dir = log_dir_name
        return old_handler, old_handler_full, message

    @staticmethod
    def switch_to_main_log(logger, main_log, main_log_full):
        """
        This method removes the tcLog handler from the logger and adds the main_log handler to the logger.

        No return value for the method.

        :param Logger logger: Logger object
        :param Logger main_log: main handler object
        :param Logger main_log_full: TC handler object

        >> from log import Logger
        >> logger = Logger.get_logger(__name__)
        >> main_log, main_log_full, _ = Logger.switchToTcLog(LOGGER, testItem)
        >> Logger.switchToMainLog(LOGGER, main_log, main_log_full)
        """
        # remove TC handler + TC Handler Full
        logger.removeHandler(logger.handlers[2])
        logger.removeHandler(logger.handlers[1])
        # add old handler
        logger.addHandler(main_log)
        logger.addHandler(main_log_full)


class LogTestCase(unittest.TestCase):
    """docstring for LogTestCase"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_1(self):
        logger = Logger.get_logger('logger_test')
        logger.info('test_1 start ...')
        logger.info('hello,world')
        logger.warning('hello,world')
        logger.debug('hello,world')
        logger.error('hello,world')
        logger.critical('hello,world')
        logger.trace('hello,world')


if __name__ == '__main__':
    # test
    # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(LogTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
