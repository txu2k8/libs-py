## **stressrunner** [![](https://github.com/txu2008/TLIB/blob/master/docs/profile_photo.png)][1]

A TestRunner inherit from TextTestRunner(Python unit testing framework). It
generates a HTML report to show the result at a glance.

[![](https://img.shields.io/badge/project-stressrunner-yellow.svg)]()
[![](https://img.shields.io/badge/Python-2.7-green.svg)]()
[![](https://img.shields.io/badge/Python-3.6-green.svg)]()
[![](https://img.shields.io/badge/Email-tao.xu2008@outlook.com-red.svg)]()
[![](https://img.shields.io/badge/Blog-https://txu2008.github.io-red.svg)][1]


#### Install
    pip install tlib

#### Usage
    from tlib.stressrunner import StressRunner
    from test.test_mail import TestMail
    runner = StressRunner(
            report_path='sr_test.log',
            title='My unit test with stressrunner',
            description='This demonstrates the report output by StressRunner.',
            logger=logger, # support owner logging logger
        )
    test_suite = unittest.TestSuite()
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMail))
    runner.run(test_suite)

***
[1]: https://txu2008.github.io