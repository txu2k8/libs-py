## **Over View**
![](https://img.shields.io/badge/Project-TLIB-yellow.svg)
![](https://img.shields.io/badge/Python-2.7-green.svg)
![](https://img.shields.io/badge/Python-3.6-green.svg)
![](https://img.shields.io/badge/Email-tao.xu2008@outlook.com-red.svg)
[![](https://img.shields.io/badge/Blog-https://txu2008.github.io-red.svg)][1]

Some own/observed great lib/ideas,common useful python libs/utils.

GitHub **https://github.com/txu2008/tlib**

PyPI: **https://pypi.org/project/tlib**


## Catalogue
1. [**aws**](https://github.com/txu2008/TLIB/blob/master/tlib/aws) AWS SDK APIs for Python.
1. [**bs**](https://github.com/txu2008/TLIB/blob/master/tlib/bs) Math calculate releated functions.
1. [**data structure**](https://github.com/txu2008/TLIB/blob/master/tlib/ds) Data Structures operations.
1. [**data base**](https://github.com/txu2008/TLIB/blob/master/tlib/db) Data Base related API/Packages.
1. [**es**](https://github.com/txu2008/tlib/tree/master/tlib/es) ElasticSearch related test
1. [**fileop**](https://github.com/txu2008/tlib/tree/master/tlib/fileop) File operation related functions
1. [**jenkinslib**](https://github.com/txu2008/tlib/tree/master/tlib/jenkinslib) libs for jenkins
1. [**k8s**](https://github.com/txu2008/TLIB/blob/master/tlib/k8s) Kubernetes API.
1. [**log**](https://github.com/txu2008/TLIB/blob/master/tlib/log) logging config, colored, compress, log file/console.
1. [**mail**](https://github.com/txu2008/TLIB/blob/master/tlib/mail) Send email, attachment.
1. [**platform**](https://github.com/txu2008/tlib/tree/master/tlib/platform) Linux/windows platform operations,such as shell,cmd,ssh_manager...
1. [**vsphere**](https://github.com/txu2008/tlib/tree/master/tlib/vsphere) pyVmomi is the Python SDK for the VMware vSphere API that allows you to manage ESX, ESXi, and vCenter.
1. [**retry**](https://github.com/txu2008/tlib/tree/master/tlib/retry) Decorators for retry func
1. [**schedule**](https://github.com/txu2008/tlib/tree/master/tlib/schedule) Decorators for schedule the func task and list the tasks with PrettyTable
1. [**storage**](https://github.com/txu2008/tlib/tree/master/tlib/storage) Object related storage
1. [**Stress Runner**](https://github.com/txu2008/TLIB/tree/master/tlib/stressrunner) A TestRunner generates a HTML report to show the result at a glance.
1. [**utils**](https://github.com/txu2008/tlib/tree/master/tlib/utils) Some python utils
1. [**validparam**](https://github.com/txu2008/tlib/tree/master/tlib/validparam) Decorators for verify param valid, verify param type, value range, ...
1. [**vim-config**](https://github.com/txu2008/tlib/tree/master/tlib/vim-config) A easy vim configuration for python

## Quick Start
### 1. Installation

Install from pip

```bash
pip install tlib
```

Install from source code:

```bash
# git clone tlib or download the released tar balls, then:
python setup.py install
```

### 2. Doc & Wiki

Visit Wiki to see more details: https://github.com/txu2008/tlib/wiki

Visit Doc site to see py-docs: TODO

Visit examples to see .examples/*

```python
# Examples:

# 1. Init logging logger
from tlib import log
logger = log.get_logger(logfile='test1.log', logger_name='test1', debug=True, reset_logger=True)
logger.info('test_1 start ...')
logger.warning('test_1 hello,world')
logger.debug('test_1 hello,world')
logger.error('test_1 hello,world')
logger.critical('test_1 hello,world')

# 2. stressrunner
import unittest
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

```


## Tests
How to run test case in this project:
    - Run test/test_*.py
    - python run_test.py log
    - python run_test.py mail
    - python run_test.py es stress -h
    - python run_test.py es index -h
    - ...

## Contribute To TLIB
    - Commit code to Github, https://github.com/txu2008/tlib
    - Need to check pep8 and pylint rules before you start a pull request

## Discussion
    - Github Issues

## Reference
      * http://tungwaiyip.info/software/HTMLTestRunner.html

## WIKI
https://github.com/txu2008/tlib/wiki

## Code directory tree:
```text
tlib
    |-- docs                    module              Docments
    |-- examples                module              tlib useage examples   
    |-- test                    module              tlib unit test cases
    |-- tlib                    module              tlib packages
    |-- requirements.txt        module              Python package requirements, pip install -r requirements.txt
    |-- Pipfile                 module              Python packages manage with pipenv
    |-- run_test.py             module              An interface for run unit test, python run_test.py -h
    |-- setup.py                module              Setup
....
```

***
[1]: https://txu2008.github.io