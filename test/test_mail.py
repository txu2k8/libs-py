# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""
Test suite 1: TestCases for mail.py
"""

import unittest

from tlib.stressrunner import StressRunner
from tlib import log
from tlib.mail import SmtpServer, Mail, SmtpMailer, mutt_sendmail


my_logger = log.get_logger()


class TestMail(unittest.TestCase):
    def setUp(self):
        my_logger.info("Mail test Start ...")
        self.subject = 'Mail Test subject'
        self.content = 'Mail Test content'
        self.address_from = 'txu@panzura.com'
        self.address_to = 'txu@panzura.com'
        self.attachments = []  # ['./log/debug.log']

        self.host = "smtp.gmail.com"
        self.user = "xx@gmail.com"
        self.password = "password"
        self.port = 465
        self.tls = True

    def tearDown(self):
        my_logger.info("Mail test complete")

    def test_1(self):
        my_logger.log(21, 'Test for SmtpServer + Mail')

        try:
            my_logger.info('preparing mail...')
            mail = Mail(self.subject, self.content, self.address_from, self.address_to)
            my_logger.info('preparing attachments...')
            mail.attach(self.attachments)

            my_logger.info('preparing SMTP server...')
            print(self.host, type(self.host))
            smtp = SmtpServer(self.host, self.user, self.password, self.port, self.tls)
            my_logger.info('sending mail to {0}...'.format(self.address_to))
            smtp.sendmail(mail)
        except Exception as e:
            raise Exception('Error in sending email. [Exception]%s' % e)

    def test_2(self):
        my_logger.log(21, 'Test for SmtpMailer')
        mailer = SmtpMailer(self.user, self.host, self.port, is_html=False)
        mailer.sendmail(self.address_to, self.subject, self.content, self.attachments)

    def test_3(self):
        my_logger.log(21, 'Test for mutt_sendmail')
        # mutt_sendmail()
        pass


if __name__ == '__main__':
    # Generate test suite
    # test_suite = unittest.TestSuite()
    test_suite = unittest.TestSuite(map(TestMail, ['test_2']))
    # test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMail))

    # output to a file

    runner = StressRunner(
        report_path='./report/',
        title='My unit test',
        description='This demonstrates the report output by StressRunner.',
        # logger=my_logger
    )
    runner.run(test_suite)
