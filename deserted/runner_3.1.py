# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

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
"""

import logging
import copy
import re
import os
import time
import datetime
import socket
import traceback
import io
import unittest
from xml.sax import saxutils
import sys
import smtplib
import mimetypes
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import coloredlogs

from utils import util

# =============================
# --- Global
# =============================
sys.setrecursionlimit(100000)
__author__ = "tao.xu"
__version__ = "1.0.0.1"
POSIX = os.name == "posix"
WINDOWS = os.name == "nt"
# default report_path
# CUR_DIR = os.path.dirname(os.path.abspath(__file__))
CUR_DIR = os.getcwd()
DEFAULT_REPORT_PATH = os.path.join(CUR_DIR, 'log')
DEFAULT_REPORT_NAME = "report.html"
DEFAULT_TITLE = 'Test Report'
DEFAULT_DESCRIPTION = ''
DEFAULT_TESTER = __author__  # 'QA'

DEFAULT_LOGGER_FORMATE = '%(asctime)s %(filename)s[%(lineno)d] [PID:%(process)d] %(levelname)s: %(message)s'
DEFAULT_LOGGER = logging.getLogger('StressRunner')
coloredlogs.install(logger=DEFAULT_LOGGER, level=logging.DEBUG, fmt=DEFAULT_LOGGER_FORMATE)


class Mail(object):
    """docstring for Mail"""

    def __init__(self, subject='', content='', m_from='', m_to='', m_cc=''):
        self.subject = subject
        self.content = MIMEText(content, 'html', 'utf-8')
        self.m_from = m_from
        self.m_to = m_to
        self.m_cc = m_cc

        self.body = MIMEMultipart('related')
        self.body['Subject'] = self.subject
        self.body['From'] = self.m_from
        self.body['To'] = self.m_to
        self.body.preamble = 'This is a multi-part message in MIME format.'

        self.alternative = MIMEMultipart('alternative')
        self.alternative.attach(self.content)
        self.body.attach(self.alternative)

    def attach(self, attachments):
        """
        attach files
        :param attachments: list
        :return:
        """
        for attachment in attachments:
            if not os.path.isfile(attachment):
                print('WARNING: Unable to attach %s because it is not a file.' % attachment)
                continue

            ctype, encoding = mimetypes.guess_type(attachment)
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            # maintype, subtype = ctype.split('/', 1)

            fp = open(attachment, 'rb')
            attachment_mime = MIMEBase("application", "octet-stream")
            attachment_mime.set_payload(fp.read())
            fp.close()

            encoders.encode_base64(attachment_mime)
            attachment_mime.add_header('Content-Disposition', 'attachment', filename=os.path.split(attachment)[1])
            self.body.attach(attachment_mime)


class SMTPServer(object):
    """docstring for SMTPServer"""

    def __init__(self, host='localhost', user='', password='', port=25, tls=False):
        self.port = port
        self.smtp = smtplib.SMTP()
        self.host = host
        self.user = user
        self.password = password
        self.is_gmail = False
        if self.host == 'smtp.gmail.com':
            self.is_gmail = True
            self.port = 587
        self.tls = tls

    def sendmail(self, mail):
        """
        Send Mail()
        :param mail:
        :return:
        """
        self.smtp.connect(self.host, self.port)
        if self.tls or self.is_gmail:
            self.smtp.starttls()
            self.smtp.ehlo()
            self.smtp.esmtp_features['auth'] = 'LOGIN DIGEST-MD5 PLAIN'
        if self.user:
            self.smtp.login(self.user, self.password)
        self.smtp.sendmail(mail.m_from, mail.m_to.split(';'), mail.body.as_string())
        self.smtp.quit()


class Util(object):
    """docstring for ClassName"""

    def __init__(self, logger=DEFAULT_LOGGER):
        super(Util, self).__init__()
        self.logger = logger

    def send_mail(self, subject, content, address_from, address_to, attach, host, user, password, port, tls):
        """
        subject = "test"
        content = "xxx"
        address_from = "stress@test.com"
        address_to = "txu1@test.com;txu2@test.com"
        attach = ''
        host = "smtp.gmail.com"
        user = "stress@test.com"
        password = "P@ssw0rd"
        port = 465
        tls = True
        """

        try:
            self.logger.info('preparing mail...')
            mail = Mail(subject, content, address_from, address_to)
            self.logger.info('preparing attachments...')
            mail.attach(attach)

            self.logger.info('preparing SMTP server...')
            smtp = SMTPServer(host, user, password, port, tls)
            self.logger.info('sending mail to {0}...'.format(address_to))
            smtp.sendmail(mail)
        except Exception as e:
            self.logger.error('Error in sending email. [Exception]%s' % e)

    def get_local_ip(self):
        """
        Get the local ip address --linux/windows
        @params:
          (void)
        @output:
          (char) local_ip
        """
        if WINDOWS:
            local_ip = socket.gethostbyname(socket.gethostname())
        else:
            local_ip = os.popen(
                "ifconfig | grep 'inet ' | grep -v '127.0.0.1' |grep -v '172.17.0.1' |grep -v ' 10.233.'| cut -d: -f2 "
                "| awk '{print $2}' | head -1").read().strip('\n')
        return local_ip

    def get_local_hostname(self):
        """
        Get the local ip address --linux/windows
        @params:
          (void)
        @output:
          (char) local_ip
        """
        local_hostname = socket.gethostname()
        return local_hostname

    def tar_log(self, ip, username, password, log_path='/var/log/', dest_path='~/', exclude_list=None):
        """
        tar log_path to dest_path
        :param ip:
        :param username:
        :param password:
        :param log_path:
        :param dest_path:
        :param exclude_list: eg: ['/var/log/filebeat']
        :return:
        """

        ls_cmd = 'ls {0}'.format(dest_path)
        rc, output = util.ssh_cmd(ip, username, password, ls_cmd, expected_rc='ignore', tries=2)
        # print(output)
        if 'No such file or directory' in output:
            mkdir_cmd = 'mkdir -p {0}'.format(dest_path)
            util.ssh_cmd(ip, username, password, mkdir_cmd, expected_rc='ignore', tries=2)

        str_time = str(time.strftime("%Y%m%d%H%M%S", time.localtime()))
        tar_file_name = "%s_%s_%s.tar.gz" % (ip, log_path.replace('/', ''), str_time)
        tar_file_pathname = os.path.join(dest_path, tar_file_name)
        tar_cmd = "tar -czvPf %s %s* " % (tar_file_pathname, log_path)
        if exclude_list and isinstance(exclude_list, list):
            for exclude in exclude_list:
                tar_cmd = tar_cmd + " --exclude={exclude}".format(exclude=exclude)
        self.logger.info("Backup {0} to {1} ...".format(log_path, tar_file_pathname))
        util.ssh_cmd(ip, username, password, tar_cmd, expected_rc='ignore', tries=2)

        return tar_file_pathname


class TemplateMix(object):
    r""" Define a HTML template for report customerization and generation.

    Overall structure of an HTML report

        HTML
        +------------------------+
        |<html>                  |
        |  <head>                |
        |                        |
        |   STYLESHEET           |
        |   +----------------+   |
        |   |                |   |
        |   +----------------+   |
        |                        |
        |  </head>               |
        |                        |
        |  <body>                |
        |                        |
        |   HEADING              |
        |   +----------------+   |
        |   |                |   |
        |   +----------------+   |
        |                        |
        |   REPORT               |
        |   +----------------+   |
        |   |                |   |
        |   +----------------+   |
        |                        |
        |   ENDING               |
        |   +----------------+   |
        |   |                |   |
        |   +----------------+   |
        |                        |
        |  </body>               |
        |</html>                 |
        +------------------------+

    """
    STATUS = {
        0: 'PASS',
        1: 'FAIL',
        2: 'ERROR',
        3: 'SKIP',
        4: 'PASS(Canceled By User)',
    }

    # ------------------
    # HTML Template
    # variables: (title, generator, stylesheet, heading, report, ending)
    HTML_TMPL = r"""<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>%(title)s</title>
        <meta name="generator" content="%(generator)s"/>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
        <link href="http://libs.baidu.com/bootstrap/3.0.3/css/bootstrap.min.css" rel="stylesheet">
        <script src="http://libs.baidu.com/jquery/2.0.0/jquery.min.js"></script>
        <script src="http://libs.baidu.com/bootstrap/3.0.3/js/bootstrap.min.js"></script>
        %(stylesheet)s
    </head>
    <body >
    <script language="javascript" type="text/javascript">
    output_list = Array();

    /*level
    0:Summary //all hiddenRow
    1:Pass    //pt none, ft/et/st hiddenRow
    2:Failed  //ft none, pt/et/st hiddenRow,
    3:Error   //et none, pt/ft/st hiddenRow
    4:Skiped  //st none, pt/ft/et hiddenRow
    5:All     //pt/ft/et/st none
    */
    function showCase(level) {
        trs = document.getElementsByTagName("tr");
        for (var i = 0; i < trs.length; i++) {
            tr = trs[i];
            id = tr.id;
            if (id.substr(0,2) == 'ft') {
                if (level == 4 || level == 3 || level == 1 || level == 0 ) {
                    tr.className = 'hiddenRow';
                }
                else {
                    tr.className = '';
                }
            }
            if (id.substr(0,2) == 'pt') {
                if (level == 4 || level == 3 || level == 2 || level == 0) {
                    tr.className = 'hiddenRow';
                }
                else {
                    tr.className = '';
                }
            }
            if (id.substr(0,2) == 'et') {
                if (level == 4 || level == 2 || level == 1 || level == 0) {
                    tr.className = 'hiddenRow';
                }
                else {
                    tr.className = '';
                }
            }
            if (id.substr(0,2) == 'st') {
                if (level == 3 || level == 2 || level == 1 || level == 0) {
                    tr.className = 'hiddenRow';
                }
                else {
                    tr.className = '';
                }
            }
        }

        //add detail_class
        detail_class=document.getElementsByClassName('detail');

        //console.log(detail_class.length)
        if (level == 5) {
            for (var i = 0; i < detail_class.length; i++){
                detail_class[i].innerHTML="outline"
            }
        }
        else{
            for (var i = 0; i < detail_class.length; i++){
                detail_class[i].innerHTML="detail"
            }
        }
    }

    function showClassDetail(cid, count) {
        var id_list = Array(count);
        var toHide = 1;
        for (var i = 0; i < count; i++) {
            tid0 = 't' + cid.substr(1) + '_' + (i+1);
            tid = 'f' + tid0;
            tr = document.getElementById(tid);
            if (!tr) {
                tid = 'p' + tid0;
                tr = document.getElementById(tid);
                if (!tr) {
                    tid = 'e' + tid0;
                    tr = document.getElementById(tid);
                    if (!tr) {
                        tid = 's' + tid0;
                        tr = document.getElementById(tid);
                    }
                }
            }
            id_list[i] = tid;
            if (tr.className) {
                toHide = 0;
            }
        }
        for (var i = 0; i < count; i++) {
            tid = id_list[i];
            if (toHide) {
                document.getElementById(tid).className = 'hiddenRow';
                document.getElementById(cid).innerText = "detail"
            }
            else {
                document.getElementById(tid).className = '';
                document.getElementById(cid).innerText = "outline"
            }
        }
    }

    function html_escape(s) {
        s = s.replace(/&/g,'&amp;');
        s = s.replace(/</g,'&lt;');
        s = s.replace(/>/g,'&gt;');
        return s;
    }

    function drawCircle(pass, fail, error, skip){
        var color = ["#6c6","#c00","#c60", "#d7d808"];
        var data = [pass,fail,error,skip];
        var text_arr = ["pass", "fail", "error", "skip"];

        var canvas = document.getElementById("circle");
        var ctx = canvas.getContext("2d");
        var startPoint=0;
        var width = 28, height = 14;
        var posX = 112 * 2 + 20, posY = 30;
        var textX = posX + width + 5, textY = posY + 10;
        for(var i=0;i<data.length;i++){
            ctx.fillStyle = color[i];
            ctx.beginPath();
            ctx.moveTo(112,70);
            ctx.arc(112,70,70,startPoint,startPoint+Math.PI*2*(data[i]/(data[0]+data[1]+data[2])),false);
            ctx.fill();
            startPoint += Math.PI*2*(data[i]/(data[0]+data[1]+data[2]));
            ctx.fillStyle = color[i];
            ctx.fillRect(posX, posY + 20 * i, width, height);
            ctx.moveTo(posX, posY + 20 * i);
            ctx.font = 'bold 14px';
            ctx.fillStyle = color[i];
            var percent = text_arr[i] + " "+data[i];
            ctx.fillText(percent, textX, textY + 20 * i);

        }
    }

    </script>
    <div class="piechart">
        <div>
            <canvas id="circle" width="350" height="168" </canvas>
        </div>
    </div>
    %(heading)s
    %(report)s
    %(ending)s

    </body>
    </html>
    """

    # ------------------
    # Stylesheet
    STYLESHEET_TMPL = """
    <style type="text/css" media="screen">
    body        { font-family: Microsoft YaHei,Tahoma,arial,helvetica,sans-serif;padding: 20px; font-size: 80%; }
    table       { font-size: 100%; }

    /* -- heading ---------------------------------------------------------------------- */
    h1 {
        font-size: 16pt;
        color: gray;
    }
    .heading {
        margin-top: 0ex;
        margin-bottom: 1ex;
    }
    .heading .attribute {
        margin-top: 1ex;
        margin-bottom: 0;
    }
    .heading .description {
        margin-top: 4ex;
        margin-bottom: 6ex;
    }

    /* -- report ------------------------------------------------------------------------ */
    #total_row  { font-weight: bold; }
    .passCase   { color: #5cb85c; }
    .failCase   { color: #d9534f; font-weight: bold; }
    .errorCase  { color: #f04e4e; font-weight: bold; }
    .skipCase   { color: #f0a20d; font-weight: bold; }
    .hiddenRow  { display: none; }
    .testcase   { margin-left: 2em; }
    .piechart{
        position:absolute;  ;
        top:75px;
        left:400px;
        width: 200px;
        float: left;
        display:  inline;
    }
    </style>
    """

    # ------------------
    # Heading
    # variables: (title, parameters, description)
    HEADING_TMPL = """<div class='heading'>
    <h1>%(title)s</h1>
    %(parameters)s
    <p class='description'>%(description)s</p>
    </div>

    """

    # ------------------
    # Heading attribute
    # # variables: (name, value)
    HEADING_ATTRIBUTE_TMPL = """<p class='attribute'><strong>%(name)s : </strong> %(value)s</p>
    """

    # ------------------
    # Report
    REPORT_TMPL = """
    <p id='show_detail_line'>
    <a class="btn btn-primary" href='javascript:showCase(0)'>Summary{ %(passrate)s }</a>
    <a class="btn btn-success" href='javascript:showCase(1)'>Passed{ %(Pass)s }</a>
    <a class="btn btn-danger" href='javascript:showCase(2)'>Failed{ %(fail)s }</a>
    <a class="btn btn-danger" href='javascript:showCase(3)'>Error{ %(error)s }</a>
    <a class="btn btn-warning" href='javascript:showCase(4)'>Skiped{ %(skip)s }</a>
    <a class="btn btn-info" href='javascript:showCase(5)'>ALL{ %(count)s }</a>
    </p>
    <table id='result_table' class="table table-condensed table-bordered table-hover">
    <colgroup>
    <col align='left' />
    <col align='right' />
    <col align='right' />
    <col align='right' />
    <col align='right' />
    <col align='right' />
    </colgroup>
    <tr id='header_row' class="text-center success" style="font-weight: bold;font-size: 14px;">
        <td>Test Group/Test case</td>
        <td>Count</td>
        <td>Pass</td>
        <td>Fail</td>
        <td>Error</td>
        <td>Skip</td>
        <td>View</td>
    </tr>
    %(test_list)s
    <tr id='total_row' class="text-center active">
        <td>Total</td>
        <td>%(count)s</td>
        <td>%(Pass)s</td>
        <td>%(fail)s</td>
        <td>%(error)s</td>
        <td>%(skip)s</td>
        <td>Passing rate: %(passrate)s</td>
    </tr>
    </table>
    <script>
        showCase(5);
        drawCircle(%(Pass)s, %(fail)s, %(error)s, %(skip)s);
    </script>
    """  # variables: (test_list, count, Pass, fail, error ,passrate)

    REPORT_CLASS_TMPL = r"""
    <tr class='%(style)s warning'>
        <td>%(desc)s</td>
        <td class="text-center">%(count)s</td>
        <td class="text-center">%(Pass)s</td>
        <td class="text-center">%(fail)s</td>
        <td class="text-center">%(error)s</td>
        <td class="text-center">%(skip)s</td>
        <td class="text-center"><a href="javascript:showClassDetail('%(cid)s',%(count)s)" class="detail" id='%(cid)s'>Detail</a></td>
    </tr>
    """  # variables: (style, desc, count, Pass, fail, error, cid)

    REPORT_TEST_WITH_ERROR_TMPL = r"""
    <tr id='%(tid)s' class='%(Class)s'>
        <td class='%(style)s'><div class='testcase'>%(desc)s</div></td>
        <td colspan='4' align='center'>
        <!--pack up error info default
        <button id='btn_%(tid)s' type="button"  class="btn btn-danger btn-xs collapsed" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
        <div id='div_%(tid)s' class="collapse">  -->

        <!-- unfold error info default -->
        <button id='btn_%(tid)s' type="button"  class="btn btn-danger btn-xs" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
        <div align='left'>
        <div id='div_%(tid)s' class="collapse in"><pre>%(script)s</pre></div>
        <!--css div popup end-->

        <td colspan='1' align='center'>%(elapsedtime)s</td>
        <td colspan='1' align='center'>Loop: %(iteration)s</td>
        </td>
    </tr>
    """  # variables: (tid, Class, style, desc, status)

    REPORT_TEST_WITH_OUTPUT_TMPL = r"""
        <tr id='%(tid)s' class='%(Class)s'>
            <td class='%(style)s'><div class='testcase'>%(desc)s</div></td>
            <td colspan='4' align='center'>
            <!--pack up error info default
            <button id='btn_%(tid)s' type="button"  class="btn btn-success btn-xs collapsed" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
            <div id='div_%(tid)s' class="collapse">  -->

            <!-- unfold error info default -->
            <button id='btn_%(tid)s' type="button"  class="btn btn-success btn-xs collapsed" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
            <div align='left'>
            <div id='div_%(tid)s' class="collapse"><pre>%(script)s</pre></div>
            <!--css div popup end-->

            <td colspan='1' align='center'>%(elapsedtime)s</td>
            <td colspan='1' align='center'>Loop: %(iteration)s</td>
            </td>
        </tr>
        """  # variables: (tid, Class, style, desc, status)

    REPORT_SKIP_TMPL = r"""
        <tr id='%(tid)s' class='%(Class)s'>
            <td class='%(style)s'><div class='testcase'>%(desc)s</div></td>
            <td colspan='4' align='center'>
            <!--pack up error info default
            <button id='btn_%(tid)s' type="button"  class="btn btn-danger btn-xs collapsed" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
            <div id='div_%(tid)s' class="collapse">  -->

            <!-- unfold error info default -->
            <button id='btn_%(tid)s' type="button"  class="btn btn-warning btn-xs" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
            <div align='left'>
            <div id='div_%(tid)s' class="collapse in"><pre>%(script)s</pre></div>
            <!--css div popup end-->

            <td colspan='1' align='center'>%(elapsedtime)s</td>
            <td colspan='1' align='center'>Loop: %(iteration)s</td>
            </td>
        </tr>
        """  # variables: (tid, Class, style, desc, status)

    REPORT_TEST_NO_OUTPUT_TMPL = r"""
    <tr id='%(tid)s' class='%(Class)s'>
        <td class='%(style)s'><div class='testcase'>%(desc)s</div></td>
        <td colspan='4' align='center'>
        <button id='btn_%(tid)s' type="button" class="btn btn-success btn-xs collapsed" data-toggle="collapse" data-target='#div_%(tid)s'>%(status)s</button>
        <!--css div popup end-->

        <td colspan='1' align='center'>%(elapsedtime)s</td>
        <td colspan='1' align='center'>Loop: %(iteration)s</td>
    </tr>
    """  # variables: (tid, Class, style, desc, status)

    REPORT_TEST_OUTPUT_TMPL = r"""%(output)s"""  # variables: (id, output)

    # ------------------
    # Ending
    ENDING_TMPL = """<div id='ending'>&nbsp;</div>
        <div style=" position:fixed;right:50px; bottom:30px; width:20px; height:20px;cursor:pointer">
        <a href="#"><span class="glyphicon glyphicon-eject" style = "font-size:30px;" aria-hidden="true">
        </span></a></div>
        """


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
    @params:
      (char) verbosity
      (char) descriptions
      (*) value
      (char) configPATH --fullpath or non-fullpath
    @output:
      (void)
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

        # result is a list of result in 4 tuple
        # (
        #   result code (0: success; 1: fail; 2: error),
        #   TestCase object,
        #   Test output (byte string),
        #   stack trace,
        # )
        self.result = []
        self.passrate = float(0)
        self.status = 0
        self.case_loop_limit = case_loop_limit
        self.case_loop_complete = 0
        self.global_iteration = 0
        self.run_time = run_time
        self.save_last_result = save_last_result
        self.iteration_start = ''

        self.case_startTime = ''
        self.outputBuffer = ''

    def get_description(self, test):
        if self.descriptions:
            return test.shortDescription() or str(test)
        else:
            return str(test)

    def startTest(self, test):
        self.logger.info("[START ] %s -- iteration: %s" % (str(test), self.global_iteration + 1))
        self.result.append((4, test, '', '', '', self.global_iteration + 1))
        self.case_startTime = datetime.datetime.now()
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

        case_stoptTime = datetime.datetime.now()
        case_elapsedtime = str(case_stoptTime - self.case_startTime).split('.')[0]
        total_elapsedtime = str(case_stoptTime - self.total_start_time).split('.')[0]
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


class StressRunner(TemplateMix):
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
        self.exec_iteration_duration = ''
        self.startTime = datetime.datetime.now()

        # results for write in mysql
        self.status = ''
        self.suite = user_args.project
        self.tc = title.replace(user_args.project + '-', '').replace(user_args.project, '')

        self.obj_util = Util(self.logger)

    def run(self, test):
        """
        Run the given test case or test suite
        :param test:
        :return:
        """
        case_loop_limit = 1  # each case run only 1 loop in one iteration
        result = _TestResult(self.startTime, self.logger, self.verbosity, 1, case_loop_limit, self.run_time,
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
                test_status = 'FAILED' if result and fail_count > 0 else'PASSED'

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
            cancled_time = str(datetime.datetime.now() - result.case_startTime).split('.')[0]
            n, t, o, e, d, l = result.result[-1]
            if n == 4:
                result.result.pop(-1)
                result.result.append((n, t, o, e, cancled_time, l))
        except Exception as e:
            self.logger.error(e)
            self.logger.error('{err}'.format(err=traceback.format_exc()))
            failed_time = str(datetime.datetime.now() - result.case_startTime).split('.')[0]
            n, t, o, e, d, l = result.result[-1]
            if n == 4:
                result.result.pop(-1)
                result.result.append((2, t, o, e, failed_time, l))
        finally:
            self.logger.info(result)
            if result.testsRun < 1:
                return result
            self.stopTime = datetime.datetime.now()
            self.elapsedtime = str(self.stopTime - self.startTime).split('.')[0]
            self.title = test_status + ": " + self.title
            self.generateReport(result)

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
            self.logger.info('Test Location: %s(%s)' % (self.obj_util.get_local_hostname(), self.obj_util.get_local_ip()))
            self.logger.info('=' * 50)

            # write mysql
            try:
                util.remote_scp_put('10.25.119.1', self.report_path_full, '/sdb/log', 'root', 'password')
                from libs.mysqldb_obj import MySQLObj
                mysql_obj = MySQLObj(host='10.25.119.1', user='test', password='password', port=3306, database='test')
                insert_sql = '''INSERT INTO test_results (Version, Suite, Test, Status, Results, StartTime, Elapsed, 
                                Tester, Report) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)'''
                data = [(self.test_version, self.suite, self.tc, test_status, self.status,
                         str(self.startTime).split('.')[0], self.elapsedtime, self.tester, self.report_name)]
                mysql_obj.insert_update_delete(insert_sql, data)
            except Exception as e:
                self.logger.warning(e)

            # tar logs
            if (result.failure_count + result.error_count) > 0 and self.user_args.suite not in \
                    ['deploy', 'upgradecore', 'tools']:
                from src.vizion.commons.vcc_obj import VCCObj

                cass_ips = self.user_args.cass_ips
                vset_ids = self.user_args.vset_ids
                if util.is_ping_ok(cass_ips[0], retry=1):
                    node_ips = VCCObj(cass_ips, vset_ids=vset_ids).vset_node_ips
                    tar_log_path = '/var/log/'
                    tar_log_backup_path = '/var/log/backup'
                    if vset_ids:
                        tar_log_backup_path = os.path.join(tar_log_backup_path, 'vset{0}'.format('_'.join([str(x) for x in vset_ids])))
                    for node_ip in node_ips:
                        self.obj_util.tar_log(node_ip, self.user_args.sys_user, self.user_args.sys_pwd, tar_log_path,
                                              tar_log_backup_path, exclude_list=['/var/log/filebeat', '/var/log/backup'])
                        # util.remote_scp_get(node_ip, self.report_path, tar_file_pathname, self.user_args.sys_user,
                        #                     self.user_args.sys_pwd)

            if self.mail_info and self.mail_info['m_to']:
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
                if os.path.getsize(log_file_path_full) < 2048*1000:
                    attach.append(log_file_path_full)
                host = self.mail_info['host']
                user = self.mail_info['user']
                password = self.mail_info['password']
                port = self.mail_info['port']
                tls = self.mail_info['tls']

                self.obj_util = Util(self.logger)
                self.obj_util.send_mail(subject, content, address_from, address_to, attach, host, user, password, port,
                                        tls)
                self.logger.info(">> Send mail done.")

            return result, test_status

    def sortResult(self, result_list):
        # unittest does not seems to run in any particular order.
        # Here at least we want to group them together by class.
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

    def getReportAttributes(self, result):
        """
        Return report attributes as a list of (name, value).
        Override this to add custom attributes.
        """
        startTime = str(self.startTime).split('.')[0]
        stopTime = str(self.stopTime).split('.')[0]
        duration = str(self.stopTime - self.startTime).split('.')[0]
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
            ('Start Time', startTime),
            ('End Time', stopTime),
            ('Duration', duration),
            ('Status', self.status),
            ('Test Location',
             '{host}({ip})'.format(host=self.obj_util.get_local_hostname(), ip=self.obj_util.get_local_ip())),
            ('Report Path', self.report_path_full),
            ('Test Cmd', self.test_input),
        ]
        attr_list.extend(self.test_env)
        if self.comment:
            attr_list.append(('Comment', self.comment))

        return attr_list

    def generateReport(self, result):
        report_attrs = self.getReportAttributes(result)
        generator = 'HTMLTestRunner %s' % __version__
        stylesheet = self._generate_stylesheet()
        heading = self._generate_heading(report_attrs)
        report = self._generate_report(result)
        ending = self._generate_ending()
        output = self.HTML_TMPL % dict(
            title=saxutils.escape(self.title),
            generator=generator,
            stylesheet=stylesheet,
            heading=heading,
            report=report,
            ending=ending,
        )

        if not os.path.isdir(self.report_path):
            try:
                os.makedirs(self.report_path)
            except OSError as e:
                self.logger.error(e)
                sys.exit(1)
        with open(self.report_path_full, 'wb') as f:
            f.write(output.encode('UTF-8'))

    def _generate_stylesheet(self):
        return self.STYLESHEET_TMPL

    def _generate_heading(self, report_attrs):
        a_lines = []
        for name, value in report_attrs:
            line = self.HEADING_ATTRIBUTE_TMPL % dict(
                name=saxutils.escape(name),
                value=saxutils.escape(value),
            )
            a_lines.append(line)
        heading = self.HEADING_TMPL % dict(
            title=saxutils.escape(self.title),
            parameters=''.join(a_lines),
            description=saxutils.escape(self.description),
            tester=saxutils.escape(self.tester),
        )
        return heading

    def _generate_report(self, result):
        rows = []
        sortedResult = self.sortResult(result.result)
        for cid, (cls, cls_results) in enumerate(sortedResult):
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

            row = self.REPORT_CLASS_TMPL % dict(
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

        report = self.REPORT_TMPL % dict(
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
        # e.g. 'pt1.1', 'ft1.1', etc
        has_output = bool(o)
        has_err = bool(e)
        tid = (n in (0, 4) and 'p' or (n == 1 and 'f' or (n == 2 and 'e' or 's'))) + 't%s_%s' % (cid + 1, tid + 1)
        name = t.id().split('.')[-1]
        doc = t.shortDescription() or ""
        desc = doc and ('%s: %s' % (name, doc)) or name
        # tmpl = has_output and self.REPORT_TEST_WITH_OUTPUT_TMPL or self.REPORT_TEST_NO_OUTPUT_TMPL
        tmpl = n == 3 and self.REPORT_SKIP_TMPL or \
               (has_err and self.REPORT_TEST_WITH_ERROR_TMPL or (has_output and self.REPORT_TEST_WITH_OUTPUT_TMPL or
                                                                  self.REPORT_TEST_NO_OUTPUT_TMPL))
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

        script = self.REPORT_TEST_OUTPUT_TMPL % dict(
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
            status=self.STATUS[n],
        )
        rows.append(row)
        if not has_output:
            return

    def _generate_ending(self):
        return self.ENDING_TMPL


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
            self.testRunner = StressRunner(verbosity=self.verbosity)
        unittest.TestProgram.runTests(self)


main = TestProgram

##############################################################################
# Executing this module from the command line
##############################################################################

if __name__ == "__main__":
    main(module=None)
