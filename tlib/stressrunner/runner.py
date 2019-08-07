# !/usr/bin/env python
# -*- coding: utf-8 -*-
#  ____  _                       ____
# / ___|| |_ _ __ ___  ___ ___  |  _ \ _   _ _ __  _ __   ___ _ __
# \___ \| __| '__/ _ \/ __/ __| | |_) | | | | '_ \| '_ \ / _ \ '__|
#  ___) | |_| | |  __/\__ \__ \ |  _ <| |_| | | | | | | |  __/ |
# |____/ \__|_|  \___||___/___/ |_| \_\\__,_|_| |_|_| |_|\___|_|
#
#                                                        version: v1.0.0
#                                                             by: Tao.Xu
#                                                           date: 1/31/2019
#                                                      copyright: N/A
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

r"""StressRunner
Description and Quick Start:
A TestRunner for use with the Python unit testing framework. It
generates a HTML report to show the result at a glance.
The simplest way to use this is to invoke its main method. E.g.
    import unittest
    import StressRunner
    ... define your tests ...
    if __name__ == '__main__':
        StressRunner.main()
For more customization options, instantiates a HTMLTestRunner object.
StressRunner is a counterpart to unittest's TextTestRunner. E.g.
    # output to a file
    runner = StressRunner.StressRunner(
                report_path='./report/',
                title='My unit test',
                description='This demonstrates the report output by StressRunner.'
                )

Change History:

Version: 3.1 -- Tao.Xu(tao.xu2008@outlook.com)
---------
    Iteration for test suite and Loop for each cases. eg:
    2 cases, run 10 iteration, 5 loop, will run follow:
        iteration-1:
            case1 - 5 loop, then
            case2 - 5 loop
            then
        iteration-2:
            case1 - 5 loop, then
            case2 - 5 loop
            then ...
        loop can set to 1

Version: 2.1 -- Tao.Xu(tao.xu2008@outlook.com)
---------
    Loop for each cases.eg:
    2 cases, run 10 iteration, will run follow:
    case1 - 10 iteration, then
    case2 - 10 iteration

Version in 1.2 -- Tao.Xu(tao.xu2008@outlook.com)
---------
    The first version, FYI: http://tungwaiyip.info/software/HTMLTestRunner.html
---------
"""

import logging
import coloredlogs
import copy
import re
import os
import sys
import datetime
import io
import socket
import traceback
from xml.sax import saxutils
import unittest

from tlib.mail import SmtpServer, Mail
from tlib.stressrunner import template


# =============================
# --- Global
# =============================
sys.setrecursionlimit(100000)
__author__ = "tao.xu"
__version__ = "1.0.0.1"
POSIX = os.name == "posix"
WINDOWS = os.name == "nt"

# DEFAULT_LOGGER_FORMATE = '%(asctime)s %(name)s %(filename)s[%(lineno)d] [PID:%(process)d] %(levelname)s: %(message)s'
DEFAULT_LOGGER_FORMATE = '%(asctime)s %(name)s %(levelname)s: %(message)s'
DEFAULT_LOGGER = logging.getLogger('StressRunner')
coloredlogs.install(logger=DEFAULT_LOGGER, level=logging.DEBUG, fmt=DEFAULT_LOGGER_FORMATE)

# default report_path
DEFAULT_REPORT_PATH = os.path.join(os.getcwd(), 'log')
DEFAULT_REPORT_NAME = "report.html"
DEFAULT_TITLE = 'Test Report'
DEFAULT_DESCRIPTION = ''
DEFAULT_TESTER = __author__  # 'QA'


def send_mail(subject, content, address_from, address_to, attach, host, user, password, port, tls):
    """

    :param subject:
    :param content:
    :param address_from:
    :param address_to:"txu1@test.com;txu2@test.com"
    :param attach:
    :param host:"smtp.gmail.com"
    :param user:"stress@test.com"
    :param password:"password"
    :param port:465
    :param tls:True
    :return:
    """

    try:
        print('preparing mail...')
        mail = Mail(subject, content, address_from, address_to)
        print('preparing attachments...')
        mail.attach(attach)

        print('preparing SMTP server...')
        smtp = SmtpServer(host, user, password, port, tls)
        print('sending mail to {0}...'.format(address_to))
        smtp.sendmail(mail)
    except Exception as e:
        raise Exception('Error in sending email. [Exception]%s' % e)


def get_local_ip():
    """
    Get the local ip address --linux/windows
    :return:(char) local_ip
    """

    if WINDOWS:
        local_ip = socket.gethostbyname(socket.gethostname())
    else:
        local_ip = os.popen(
            "ifconfig | grep 'inet ' | grep -v '127.0.0.1' |grep -v '172.17.0.1' |grep -v ' 10.233.'| cut -d: -f2 "
            "| awk '{print $2}' | head -1").read().strip('\n')
    return local_ip


def get_local_hostname():
    """
    Get the local ip address --linux/windows
    :return:
    """
    return socket.gethostname()


# ------------------------------------------------------------------------
# The redirectors below are used to capture output during testing. Output
# sent to sys.stdout and sys.stderr are automatically captured. However
# in some cases sys.stdout is already cached before HTMLTestRunner is
# invoked (e.g. calling logging.basicConfig). In order to capture those
# output, use the redirectors for the cached stream.
#
# e.g.
#   >>> logging.basicConfig(stream=HTMLTestRunner.stdout_redirector)
#   >>>


class OutputRedirector(object):
    """ Wrapper to redirect stdout or stderr """

    def __init__(self, fp):
        self.fp = fp
        self.__console__ = sys.stdout

    def write(self, s):
        if 'ERROR:' in s:
            if WINDOWS:
                pattern = re.compile(r'[^a]\W\d+[m]')
            elif POSIX:
                pattern = re.compile(r'[^a]\W\d+[m]\W?')
            else:
                pattern = re.compile(r'')
            s_mesg = pattern.sub('', s)
            s_mesg = s_mesg.encode(encoding="utf-8")
            self.fp.write(s_mesg)

        if 'DESCRIBE:' in s:
            pattern = re.compile(r'.+DESCRIBE:\W+\d+[m]\s')
            s_mesg = pattern.sub('', s)
            s_mesg = s_mesg.encode(encoding="utf-8")
            self.fp.write(s_mesg)
        self.__console__.write(str(s))

    def writelines(self, lines):
        if 'ERROR' in lines:
            self.fp.writelines(lines)
        self.__console__.write(str(lines))

    def flush(self):
        self.fp.flush()
        self.__console__.flush()


stdout_redirector = OutputRedirector(sys.stdout)
stderr_redirector = OutputRedirector(sys.stderr)

TestResult = unittest.TestResult


class _TestResult(TestResult):
    """
    note: _TestResult is a pure representation of results.
    It lacks the output and reporting ability compares to unittest._TextTestResult.
    """

    def __init__(self,
                 total_start_time,
                 logger=DEFAULT_LOGGER,
                 verbosity=2,
                 descriptions=1,
                 case_loop_limit=1,
                 run_time=None,
                 save_last_result=False):
        """
        _TestResult inherit from unittest TestResult
        :param total_start_time:
        :param logger: default is logging.get_logger()
        :param verbosity:
        :param descriptions:
        :param case_loop_limit: the max loop running for each case
        :param run_time:
        :param save_last_result: just save the last loop result
        """
        super(_TestResult, self).__init__()
        TestResult.__init__(self)
        self.stdout0 = None
        self.stderr0 = None
        self.success_count = 0
        self.failure_count = 0
        self.error_count = 0
        self.skipped_count = 0  # add skipped_count
        self.canceled_count = 0  # add canceled_count
        self.total_start_time = total_start_time
        self.logger = logger
        self.showAll = verbosity > 1
        self.dots = verbosity == 1
        self.descriptions = descriptions
        self.verbosity = verbosity

        '''
        result is a list of result in 4 tuple
        (
          result code (0: success; 1: fail; 2: error),
          TestCase object,
          Test output (byte string),
          stack trace,
        )
        '''
        self.result = []
        self.passrate = float(0)
        self.status = 0
        self.case_loop_limit = case_loop_limit
        self.case_loop_complete = 0
        self.global_iteration = 0
        self.run_time = run_time
        self.save_last_result = save_last_result
        self.iteration_start = ''

        self.case_start_time = ''
        self.outputBuffer = ''

    def get_description(self, test):
        if self.descriptions:
            return test.shortDescription() or str(test)
        else:
            return str(test)

    def startTest(self, test):
        self.logger.info("[START ] %s -- iteration: %s" % (str(test), self.global_iteration + 1))
        self.result.append((4, test, '', '', '', self.global_iteration + 1))
        self.case_start_time = datetime.datetime.now()
        TestResult.startTest(self, test)
        # just one buffer for both stdout and stderr
        self.outputBuffer = io.BytesIO()
        self.outputBuffer.truncate(0)
        stdout_redirector.fp = self.outputBuffer
        stderr_redirector.fp = self.outputBuffer
        self.stdout0 = sys.stdout
        self.stderr0 = sys.stderr
        sys.stdout = stdout_redirector
        sys.stderr = stderr_redirector

    def complete_output(self, test):
        """
        Disconnect output redirection and return buffer.
        Safe to call multiple times.
        """
        self.result.pop(-1)  # remove the running record (4, test, '', '', '', self.global_iteration + 1)
        if self.stdout0:
            sys.stdout = self.stdout0
            sys.stderr = self.stderr0
            self.stdout0 = None
            self.stderr0 = None

        case_stop_time = datetime.datetime.now()
        case_elapsedtime = str(case_stop_time - self.case_start_time).split('.')[0]
        total_elapsedtime = str(case_stop_time - self.total_start_time).split('.')[0]
        output_info = self.outputBuffer.getvalue().decode('UTF-8')
        self.outputBuffer.close()
        for test_item, err in (self.errors + self.failures):
            if test_item == test:
                output_info += "{test_info}:".format(test_info=test)

        return output_info, case_elapsedtime, total_elapsedtime

    def stopTest(self, test):
        # Usually one of addSuccess, addError or addFailure would have been called.
        # But there are some path in unittest that would bypass this.
        # We must disconnect stdout in stopTest(), which is guaranteed to be called.

        # self.complete_output(test)
        pass

    def addSuccess(self, test):
        self.case_loop_complete += 1
        self.success_count += 1
        self.status = 0
        TestResult.addSuccess(self, test)
        output, duration, total_elapsedtime = self.complete_output(test)
        self.result.append((0, test, output, '', duration, self.global_iteration+1))
        if self.verbosity > 1:
            self.logger.info(
                "[ PASS ] %s -- iteration: %s --Elapsed Time: %s" % (str(test), self.global_iteration+1, str(duration)))
            self.logger.info("Total Running time up to now: {total_time}".format(total_time=total_elapsedtime))
        else:
            self.logger.info("\n.")

        if (self.case_loop_limit == 0) or (self.case_loop_limit > self.case_loop_complete):
            retry_flag = True
        elif self.run_time:
            retry_flag = True
            self.run_time -= duration
        else:
            retry_flag = False

        if retry_flag:
            if self.save_last_result:
                self.result.pop(-1)
                self.success_count -= 1
            test = copy.copy(test)
            self.iteration_start = datetime.datetime.now()
            test(self)
        else:
            self.case_loop_complete = 0

    def addError(self, test, err):
        self.error_count += 1
        self.status = 2
        TestResult.addError(self, test, err)
        _, _exc_str = self.errors[-1]
        output, duration, total_elapsedtime = self.complete_output(test)
        self.result.append((2, test, output, _exc_str, duration, self.global_iteration + 1))
        if self.verbosity > 1:
            # self.logger.critical("\n[  ERROR  ] %s" % str(test))
            self.logger.critical(
                "[ERROR ] %s -- iteration: %s --Elapsed Time: %s" % (str(test), self.global_iteration+1, str(duration)))
            self.logger.info("Total Running time up to now: {total_time}".format(total_time=total_elapsedtime))
        else:
            self.logger.critical("\nE")
        self.case_loop_complete = 0

    def addFailure(self, test, err):
        self.failure_count += 1
        self.status = 1
        TestResult.addFailure(self, test, err)
        _, _exc_str = self.failures[-1]
        output, duration, total_elapsedtime = self.complete_output(test)
        self.result.append((1, test, output, _exc_str, duration, self.global_iteration + 1))
        if self.verbosity > 1:
            # self.logger.critical("\n[  FAILED  ] %s" % str(test))
            self.logger.critical(
                "[FAILED] %s -- iteration: %s --Elapsed Time: %s" % (str(test), self.global_iteration+1, str(duration)))
            self.logger.info("Total Running time up to now: {total_time}".format(total_time=total_elapsedtime))
        else:
            self.logger.critical("\nF")
        self.case_loop_complete = 0

    def addSkip(self, test, reason):
        self.skipped_count += 1
        self.status = 3
        TestResult.addSkip(self, test, reason)
        output, duration, total_elapsedtime = self.complete_output(test)
        self.result.append((3, test, output, reason, duration, self.global_iteration+1))
        if self.showAll:
            self.logger.warning("\n[ SKIP   ] %s" % str(test))
            self.logger.info("Total Running time up to now: {total_time}".format(total_time=total_elapsedtime))
        else:
            self.logger.warning("\nS")
        self.case_loop_complete = 0

    def printErrors(self):
        if self.dots or self.showAll:
            sys.stderr.write('\n')
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            self.logger.error("%s: %s\n%s" % (flavour, self.get_description(test), err))


class StressRunner(object):
    """
    stress runner
    """

    def __init__(self,
                 report_path=DEFAULT_REPORT_PATH,
                 report_name=DEFAULT_REPORT_NAME,
                 logger=DEFAULT_LOGGER,
                 verbosity=2,
                 title=DEFAULT_TITLE,
                 description=DEFAULT_DESCRIPTION,
                 tester=DEFAULT_TESTER,
                 test_input='',
                 test_version='version',
                 test_env=[],
                 comment=None,
                 iteration=1,
                 mail_info=None,
                 run_time=None,
                 save_last_iteration=False,
                 backup_path_list=[],
                 user_args=None
                 ):
        """
        :param report_path: default ./
        :param report_name: default report.html
        :param verbosity:
        :param title:
        :param description:
        :param tester:
        :param test_input:
        :param test_version:
        :param test_env:
        :param iteration: the max test iteration
        :param mail_info: default, example:
            MAIL_INFO = dict(
                m_from="stress@test.com",
                m_to="txu@test.com", # split to ";", eg: "txu1@test.com;txu2@test.com"
                host="smtp.gmail.com",
                user="txu@test.com",
                password="P@ssword1",
                port=465,
                tls = True
                )
        :param run_time: the max run time
        :param save_last_iteration: will save only the last iteration results if true
        :param backup_path_list: pust test logs to backup path
        :param user_args: the user inout args
        """

        self.report_path = report_path
        self.report_name = report_name + '.html' if not report_name.endswith('.html') else report_name
        self.report_path_full = os.path.join(self.report_path, self.report_name)
        self.logger = logger
        self.verbosity = verbosity
        self.title = title + '-' + test_version
        self.description = description
        self.tester = tester
        self.test_input = test_input
        self.test_version = test_version
        self.test_env = test_env
        self.comment = comment
        self.iteration = iteration
        self.mail_info = mail_info
        self.run_time = run_time
        self.save_last_iteration = save_last_iteration
        self.backup_path_list = backup_path_list
        self.user_args = user_args
        self.elapsedtime = ''
        self.start_time = datetime.datetime.now()
        self.stop_time = ''
        self.passrate = ''
        self.exec_iteration_duration = ''

        # results for write in mysql
        self.status = ''

    def run(self, test):
        """
        Run the given test case or test suite
        :param test:
        :return:
        """
        case_loop_limit = 1  # each case run only 1 loop in one iteration
        result = _TestResult(self.start_time, self.logger, self.verbosity, 1, case_loop_limit, self.run_time,
                             self.save_last_iteration)
        test_status = 'ERROR'
        retry_flag = True
        result.global_iteration = 0
        try:
            while retry_flag:
                tmp_test = copy.deepcopy(test)
                self.logger.info("Test Case List:")
                for _test in tmp_test._tests:
                    self.logger.info(_test)

                exec_start_time = datetime.datetime.now()
                tmp_test(result)
                result.global_iteration += 1
                exec_stopt_time = datetime.datetime.now()
                self.exec_iteration_duration = str(exec_stopt_time - exec_start_time).split('.')[0]
                fail_count = result.failure_count + result.error_count
                test_status = 'FAILED' if result and fail_count > 0 else 'PASSED'

                if fail_count > 0:
                    retry_flag = False
                elif (self.iteration == 0) or (self.iteration > result.global_iteration):
                    retry_flag = True
                elif self.run_time:
                    retry_flag = True
                    self.run_time -= self.exec_iteration_duration
                else:
                    retry_flag = False

        except KeyboardInterrupt:
            self.logger.info("Script stoped by user --> ^C")
            if result:
                if (result.failure_count + result.error_count) > 0:
                    test_status = 'FAILED'
                elif result.success_count <= 0:
                    test_status = 'CANCELED'
                else:
                    test_status = 'PASSED'
            else:
                test_status = 'CANCELED'
            result.canceled_count += 1
            cancled_time = str(datetime.datetime.now() - result.case_start_time).split('.')[0]
            n, t, o, e, d, l = result.result[-1]
            if n == 4:
                result.result.pop(-1)
                result.result.append((n, t, o, e, cancled_time, l))
        except Exception as e:
            self.logger.error(e)
            self.logger.error('{err}'.format(err=traceback.format_exc()))
            failed_time = str(datetime.datetime.now() - result.case_start_time).split('.')[0]
            n, t, o, e, d, l = result.result[-1]
            if n == 4:
                result.result.pop(-1)
                result.result.append((2, t, o, e, failed_time, l))
        finally:
            self.logger.info(result)
            if result.testsRun < 1:
                return result
            self.stop_time = datetime.datetime.now()
            self.elapsedtime = str(self.stop_time - self.start_time).split('.')[0]
            self.title = test_status + ": " + self.title
            self.generate_report(result)

            # self.logger.info('=' * 50)
            # self.logger.info("Errors & Failures:")
            # result.printErrors()

            self.logger.info('=' * 50)
            if result.result:
                for test_result in result.result:
                    status_flag = ['PASS', 'FAIL', 'ERROR', 'SKIP', 'PASS(CANCELED)']
                    self.logger.info(
                        "{rtn} - {casename} - Iteration: {iteration} - Last Iteration Elapsed Time: {elapsedtime}".format(
                            rtn=status_flag[test_result[0]], casename=test_result[1], iteration=test_result[5],
                            elapsedtime=test_result[4]))
                    err_failure = test_result[3].strip('\n')  # test_result[2].strip('\n') + test_result[3].strip('\n')
                    if err_failure:
                        self.logger.error("{err_failure}".format(err_failure=err_failure))
            else:
                for _test in test._tests:
                    self.logger.info(_test)

            self.logger.info("Pass: %d" % result.success_count)
            self.logger.info("Fail: %d" % result.failure_count)
            self.logger.info("Error: %d" % result.error_count)
            self.logger.info("Skiped: %d" % result.skipped_count)
            self.logger.info("Canceled: %d" % result.canceled_count)
            total_count = result.success_count + result.failure_count + result.error_count + result.skipped_count + result.canceled_count
            self.logger.info("Total: %d" % total_count)
            self.logger.info('Time Elapsed: %s' % self.elapsedtime)
            self.logger.info('Report Path: %s' % self.report_path_full)
            self.logger.info('Test Location: %s(%s)' % (get_local_hostname(), get_local_ip()))
            self.logger.info('=' * 50)

            # -- extend operations here -----------------------------------
            # eg: write test result to mysql
            # eg: tar and backup test logs
            # eg: send email
            if self.mail_info:
                subject = self.title
                content = ''
                with open(self.report_path_full, 'rb') as f:
                    content = f.read()
                address_from = self.mail_info['m_from']
                address_to = self.mail_info['m_to']
                attach = [self.report_path_full]
                if 'tc_path' in self.user_args:
                    attach.append(os.path.join(os.getcwd(), self.user_args.tc_path))
                log_file_path_full = self.report_path_full.replace('.html', '.log')
                if os.path.getsize(log_file_path_full) < 2048 * 1000:
                    attach.append(log_file_path_full)
                host = self.mail_info['host']
                user = self.mail_info['user']
                password = self.mail_info['password']
                port = self.mail_info['port']
                tls = self.mail_info['tls']

                send_mail(subject, content, address_from, address_to, attach, host, user, password, port, tls)
                print(">> Send mail done.")

            return result, test_status

    def sort_result(self, result_list):
        """
        unittest does not seems to run in any particular order.
        Here at least we want to group them together by class.

        :param result_list:
        :return:
        """

        rmap = {}
        classes = []
        for n, t, o, e, d, l in result_list:
            cls = t.__class__
            if cls not in rmap:
                rmap[cls] = []
                classes.append(cls)
            rmap[cls].append((n, t, o, e, d, l))
        r = [(cls, rmap[cls]) for cls in classes]
        return r

    def generate_report(self, result):
        heading_attrs = self._get_heading_attributes(result)
        stylesheet = self._generate_stylesheet()
        heading = self._generate_heading(heading_attrs)
        report = self._generate_report(result)
        output = template.HTML_TEMPLATE % dict(
            title=saxutils.escape(self.title),
            stylesheet=stylesheet,
            heading=heading,
            report=report,
        )

        if not os.path.isdir(self.report_path):
            try:
                os.makedirs(self.report_path)
            except OSError as e:
                raise Exception(e)
        with open(self.report_path_full, 'wb') as f:
            f.write(output.encode('UTF-8'))

        return True

    def _generate_heading(self, heading_attrs):
        a_lines = []
        for name, value in heading_attrs:
            line = template.HEADING_ATTRIBUTE_TEMPLATE % dict(
                name=saxutils.escape(name),
                value=saxutils.escape(value),
            )
            a_lines.append(line)

        heading = template.HEADING_TEMPLATE % dict(
            title=saxutils.escape(self.title),
            parameters=''.join(a_lines),
            description=saxutils.escape(self.description),
            tester=saxutils.escape(self.tester),
        )

        return heading

    def _get_heading_attributes(self, result):
        """
        Return report attributes as a list of (name, value).
        Override this to add custom attributes.
        :param result:
        :return:
        """

        start_time = str(self.start_time).split('.')[0]
        stop_time = str(self.stop_time).split('.')[0]
        duration = str(self.stop_time - self.start_time).split('.')[0]
        status = []
        status.append('ALL %s' % (result.success_count + result.failure_count + result.error_count +
                                  result.skipped_count + result.canceled_count))
        if result.success_count: status.append('Pass %s' % result.success_count)
        if result.failure_count: status.append('Failure %s' % result.failure_count)
        if result.error_count:   status.append('Error %s' % result.error_count)
        if result.skipped_count: status.append('Skip %s' % result.skipped_count)
        if result.canceled_count: status.append('Cancel %s' % result.canceled_count)

        if status:
            status = ', '.join(status)
            self.passrate = str("%.0f%%" % (float(result.success_count + result.canceled_count) / float(
                result.success_count + result.failure_count + result.error_count + result.canceled_count) * 100))
        else:
            status = 'none'
        self.status = status + ", Passing rate: " + self.passrate

        attr_list = [
            (u'Tester', self.tester),
            ('Version', self.test_version),
            ('Start Time', start_time),
            ('End Time', stop_time),
            ('Duration', duration),
            ('Status', self.status),
            ('Test Location', '{host}({ip})'.format(host=get_local_hostname(), ip=get_local_ip())),
            ('Report Path', self.report_path_full),
            ('Test Cmd', self.test_input),
        ]
        attr_list.extend(self.test_env)
        if self.comment:
            attr_list.append(('Comment', self.comment))

        return attr_list

    def _generate_stylesheet(self):
        return template.STYLESHEET_TEMPLATE

    def _generate_report(self, result):
        rows = []
        sorted_result = self.sort_result(result.result)
        for cid, (cls, cls_results) in enumerate(sorted_result):
            # subtotal for a class
            np = nf = ne = ns = 0
            for n, t, o, e, d, l in cls_results:
                if n == 0:
                    np += 1
                elif n == 1:
                    nf += 1
                elif n == 3:
                    ns += 1
                elif n == 4:
                    np += 1
                else:
                    ne += 1

            # format class description
            if cls.__module__ == "__main__":
                name = cls.__name__
            else:
                name = "%s.%s" % (cls.__module__, cls.__name__)
            doc = cls.__doc__ and cls.__doc__.split("\n")[0] or ""
            desc = doc and '%s: %s' % (name, doc) or name

            row = template.REPORT_CLASS_TEMPLATE % dict(
                style=ne > 0 and 'errorClass' or nf > 0 and 'failClass' or 'passClass',
                desc=desc,
                count=np + nf + ne + ns,
                Pass=np,
                fail=nf,
                error=ne,
                skip=ns,
                cid='c%s' % (cid + 1),
            )
            rows.append(row)

            for tid, (n, t, o, e, d, l) in enumerate(cls_results):
                self._generate_report_test(rows, cid, tid, n, t, o, e, d, l)

        report = template.REPORT_TEMPLATE % dict(
            test_list=''.join(rows),
            count=str(result.success_count + result.failure_count + result.error_count + result.skipped_count),
            Pass=str(result.success_count),
            fail=str(result.failure_count),
            error=str(result.error_count),
            skip=str(result.skipped_count),
            passrate=self.passrate,
        )

        return report

    def _generate_report_test(self, rows, cid, tid, n, t, o, e, d, l):
        has_output = bool(o)
        has_err = bool(e)
        tid = (n in (0, 4) and 'p' or (n == 1 and 'f' or (n == 2 and 'e' or 's'))) + 't%s_%s' % (cid + 1, tid + 1)
        name = t.id().split('.')[-1]
        doc = t.shortDescription() or ""
        desc = doc and ('%s: %s' % (name, doc)) or name
        # tmpl = has_output and self.REPORT_TEST_WITH_OUTPUT_TMPL or self.REPORT_TEST_NO_OUTPUT_TMPL
        tmpl = (n == 3 and template.REPORT_SKIP_TEMPLATE or
                (has_err and template.REPORT_WITH_ERROR_TEMPLATE or
                 (has_output and template.REPORT_WITH_OUTPUT_TEMPLATE or
                  template.REPORT_NO_OUTPUT_TEMPLATE
                  )
                 )
                )
        # o and e should be byte string because they are collected from stdout and stderr?
        if isinstance(o, str):
            # TODO: some problem with 'string_escape': it escape \n and mess up formating
            # uo = unicode(o.encode('string_escape'))
            # uo = o.decode('latin-1')
            uo = o
        else:
            uo = o
        if isinstance(e, str):
            # TODO: some problem with 'string_escape': it escape \n and mess up formating
            # ue = unicode(e.encode('string_escape'))
            # ue = e.decode('latin-1')
            ue = e
        else:
            ue = e
        if isinstance(d, str):
            # TODO: some problem with 'string_escape': it escape \n and mess up formating
            # ue = unicode(e.encode('string_escape'))
            # ue = e.decode('latin-1')
            ud = d
        else:
            ud = d

        script = template.REPORT_OUTPUT_TEMPLATE % dict(
            # id = tid,
            output=saxutils.escape(uo + ue),
        )

        row = tmpl % dict(
            tid=tid,
            Class=(n == 0 and 'none' or 'none'),  # (n == 0 and 'hiddenRow' or 'none'),
            style=n == 2 and 'errorCase' or (n == 1 and 'failCase' or (n == 3 and 'skipCase' or 'passCase' or 'none')),
            desc=desc,
            iteration=l,
            elapsedtime=ud,
            script=script,
            status=template.STATUS[n],
        )
        rows.append(row)
        if not has_output:
            return


##############################################################################
# Facilities for running tests from the command line
##############################################################################

# Note: Reuse unittest.TestProgram to launch test. In the future we may
# build our own launcher to support more specific command line
# parameters like test title, CSS, etc.
class TestProgram(unittest.TestProgram):
    """
    A variation of the unittest.TestProgram. Please refer to the base
    class for command line parameters.
    """

    def runTests(self):
        # Pick StressRunner as the default test runner.
        # base class's testRunner parameter is not useful because it means
        # we have to instantiate StressRunner before we know self.verbosity.
        if self.testRunner is None:
            self.testRunner = StressRunner()
        unittest.TestProgram.runTests(self)


main = TestProgram

##############################################################################
# Executing this module from the command line
##############################################################################

if __name__ == "__main__":
    main(module=None)
