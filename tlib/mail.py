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

"""Send email by smtp"""

import os
import smtplib
import mimetypes
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from email.mime import multipart
from email.mime import audio
from email.mime import base
from email.mime import image
from email.mime import text

from tlib import log
from tlib import decorators
from tlib import shell


my_logger = log.get_logger()


# ===================================================================
# --- Solution 1: SmtpServer + Mail
# ===================================================================
class SmtpServer(object):
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


# ===================================================================
# --- Solution 2: SmtpMailer
# ===================================================================
class SmtpMailer(object):
    """
    :param sender:  mail sender
    :param server: smtp的mailserver
    :param port: port
    :param is_html:  is html enabled

    smtp server examples
    ::

        from cup import mail
        mailer = mail.SmtpMailer(
            'xxx@xxx.com',
            'xxxx.smtp.xxx.com',
            is_html=True
        )
        mailer.sendmail(
            [
                'maguannan',
                'liuxuan05',
                'zhaominghao'
            ],
            'test_img',
            (
                'testset <img src="cid:screenshot.png"></img>'
            ),
            [
                '/home/work/screenshot.png',
                '../abc.zip'
            ]
        )
    """
    _COMMA_SPLITTER = ','

    def __init__(self, sender, server='localhost', port=25, is_html=False):
        """
        """
        self._server = None
        self._port = None
        self._sender = None
        self._is_html = False
        self._login_params = None
        self.setup(sender, server, port, is_html)

    def setup(self, sender, server, port=25, is_html=False):
        """
        change parameters during run-time
        """
        self._server = server
        self._port = port
        self._sender = sender
        self._is_html = is_html

    def login(self, username, passwords):
        """
        if the smtp need login, plz call this method before you call
        sendmail
        """

        self._login_params = (username, passwords)

    @classmethod
    def _check_type(cls, instance, type_list):
        if not type(instance) in type_list:
            raise TypeError('%s only accepts types like: %s' %(instance, ','.join(type_list)))

    @classmethod
    def _handle_attachments(cls, outer, attachments):
        if type(attachments) == str:
            attrs = [attachments]
        elif type(attachments) == list:
            attrs = attachments
        else:
            attrs = []
        for attached in attrs:
            if not os.path.isfile(attached):
                my_logger.warn('attached is not a file:%s' % attached)
                continue
            # Guess the content type based on the file's extension.  Encoding
            # will be ignored, although we should check for simple things like
            # gzip'd or compressed files.
            ctype, encoding = mimetypes.guess_type(attached)
            if ctype is None or encoding is not None:
                # No guess could be made, or the file is encoded (compressed)
                # use a generic bag-of-bits type.
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)
            try:
                if maintype == 'text':
                    with open(attached, 'rb') as fhandle:
                        # Note: we should handle calculating the charset
                        msg = text.MIMEText(
                            fhandle.read(), _subtype=subtype
                        )
                elif maintype == 'image':
                    with open(attached, 'rb') as fhandle:
                        imgid = os.path.basename(attached)
                        msg = image.MIMEImage(
                            fhandle.read(), _subtype=subtype
                        )
                        msg.add_header('Content-ID', imgid)
                elif maintype == 'audio':
                    with open(attached, 'rb') as fhandle:
                        msg = audio.MIMEAudio(fhandle.read(), _subtype=subtype)
                else:
                    with open(attached, 'rb') as fhandle:
                        msg = base.MIMEBase(maintype, subtype)
                        msg.set_payload(fhandle.read())
                    # Encode the payload using Base64
                    encoders.encode_base64(msg)
                    # Set the filename parameter
                msg.add_header(
                    'Content-Disposition', 'attachment',
                    filename=os.path.basename(attached)
                )
                outer.attach(msg)
            # pylint: disable=W0703
            except Exception as exception:
                my_logger.warn(
                    'failed to attach %s, errmsg:%s. Will skip it' % (
                        attached, str(exception)
                    )
                )

    def sendmail(self, recipients, subject='', body='', attachments=None, cc=None, bcc=None):
        """
        send mail

        :param recipients:
            "list" of recipients. See the example above
        :param subject:
            subject
        :param body:
            body of the mail
        :param attachments:
            "list" of attachments. Plz use absolute file path!
        :param cc:
            cc list
        :param bcc:
            bcc list
        :return:
            return (True, None) on success, return (False, error_msg) otherwise
        """
        errmsg = None
        # self._check_type(recipients, [str, list])
        # self._check_type(subject, [str])
        toaddrs = []
        # self._check_type(body, [str])
        if self._is_html:
            msg_body = text.MIMEText(body, 'html', _charset='utf-8')
        else:
            msg_body = text.MIMEText(body, 'plain', _charset='utf-8')
        outer = multipart.MIMEMultipart()
        outer['Subject'] = subject
        if isinstance(recipients, list):
            outer['To'] = self._COMMA_SPLITTER.join(recipients)
            toaddrs.extend(recipients)
        else:
            outer['To'] = recipients
            toaddrs.append(recipients)
        if cc is not None:
            if type(cc) == str:
                outer['Cc'] = cc
                toaddrs.append(cc)
            elif isinstance(cc, list):
                outer['Cc'] = self._COMMA_SPLITTER.join(cc)
                toaddrs.extend(cc)
            else:
                raise TypeError('cc only accepts string or list')
        if bcc is not None:
            if type(bcc) == str:
                outer['Bcc'] = bcc
                toaddrs.append(bcc)
            elif isinstance(bcc, list):
                outer['Bcc'] = self._COMMA_SPLITTER.join(bcc)
                toaddrs.extend(bcc)
            else:
                raise TypeError('bcc only accepts string or list')
        outer['From'] = self._sender
        outer.preamble = 'Peace and Joy!\n'
        self._handle_attachments(outer, attachments)
        outer.attach(msg_body)
        # handle attachments
        composed = outer.as_string()
        ret = (False, 'failed to send email')
        try:
            smtp = smtplib.SMTP(self._server, self._port)
            if self._login_params is not None:
                smtp.login(self._login_params[0], self._login_params[1])
            smtp.sendmail(self._sender, toaddrs, composed)
            smtp.quit()
            ret = (True, None)
        except smtplib.SMTPException as smtperr:
            ret = (False, str(errmsg))
        return ret


# ===================================================================
# --- Solution 3: mutt sendmail, not recommended to use
# ===================================================================
def mutt_sendmail(m_to, subject, body, attach, content_is_html=False):
    """
    Notice: this function is not recommended to use. Use SMTPServer/Mail instead.

    :param  exec_cwd:
        exec working directory. Plz use
    :param m_to:
        recipt list, separated by ,
    :param subject:
        subject
    :param body:
        email content
    :param attach:
        email attachment
    :param content_is_html:
        is htm mode opened
    :return:
        return True on success, False otherwise
    """
    decorators.needlinux(mutt_sendmail)
    shellobj = shell.ShellExec()
    temp_cwd = os.getcwd()

    str_att = ''
    cmdstr = ''
    if attach == '':
        if content_is_html is True:
            cmdstr = 'echo "%s"|/usr/bin/mutt -e "my_hdr Content-Type:'\
                'text/html" -s "%s" %s' \
                % (body, subject, m_to)
        else:
            cmdstr = 'echo "%s"|/usr/bin/mutt -s "%s" %s' % (
                body, subject, m_to
            )
    else:
        attlist = attach.strip().split(',')
        attlen = len(attlist)
        for i in range(0, attlen):
            str_att += '-a ' + attlist[i]
            if(i != attlen - 1):
                str_att += ' '
        if content_is_html is True:
            cmdstr = 'echo %s|/usr/bin/mutt -e "my_hdr Content-Type:'\
                'text/html" -s "%s" %s %s' % (body, subject, str_att, m_to)
        else:
            cmdstr = 'echo %s|/usr/bin/mutt -s "%s" %s %s' % (
                body, subject, str_att, m_to
            )
    ret_dic = shellobj.run(cmdstr, 60)
    os.chdir(temp_cwd)
    if ret_dic['returncode'] == 0:
        return True
    else:
        my_logger.warn(ret_dic['stderr'])
        return False
