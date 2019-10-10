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
1. [**vim-config**](https://github.com/txu2008/tlib/tree/master/tlib/vim-config) A easy vim configuration for python
2. [**Stress Runner**](https://github.com/txu2008/TLIB/tree/master/tlib/stressrunner) A TestRunner generates a HTML report to show the result at a glance.
3. [**log**](https://github.com/txu2008/TLIB/blob/master/tlib/log) logging config, colored, compress, log file/console.
4. [**mail**](https://github.com/txu2008/TLIB/blob/master/tlib/mail) Send email, attachment.
5. [**bs**](https://github.com/txu2008/TLIB/blob/master/tlib/bs) Math calculate releated functions.
6. [**data structure**](https://github.com/txu2008/TLIB/blob/master/tlib/data_structure) Data Structures operations.
7. [**validparam**](https://github.com/txu2008/tlib/tree/master/tlib/validparam) Decorators for verify param valid, verify param type, value range, ...
8. [**platform**](https://github.com/txu2008/tlib/tree/master/tlib/platform) Linux/windows platform operations,such as shell,cmd,ssh...
9. [**retry**](https://github.com/txu2008/tlib/tree/master/tlib/retry) Decorators for retry func
10. [**jenkinslib**](https://github.com/txu2008/tlib/tree/master/tlib/jenkinslib) libs for jenkins
11. [**fileop**](https://github.com/txu2008/tlib/tree/master/tlib/fileop) File operation related functions
12. [**utils**](https://github.com/txu2008/tlib/tree/master/tlib/utils) Some python utils
...

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
    - Run test/test_*.py
    - python run_test.py log
    - python run_test.py mail
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

## code directory tree:

```text
tlib/tlib
    |-- stressrunner            module              A TestRunner generates a HTML report to show the result at a glance.
    |-- log                     module              logging config, colored, compress, log file/console.    
    |-- mail                    module              Send email, attachment.
    |-- bs                      module              Math calculate releated functions.
    |-- data_structure          module              Data Structures operations.
    |-- validparam              module              Decorators for verify param valid, verify param type, value range, ...
    |-- platform                module              Linux/windows platform operations,such as shell,cmd,ssh...
    |-- retry                   module              Decorators for retry func
    |-- jenkinslib              module              libs for jenkins
    |-- fileop                  module              File operation related functions
    |-- util                    package             common func utils, etc
    |-- __init__.py             module              Default __init__.py
    |-- cache.py                module              Memory cache related module
    |-- decorators.py           module              Decorators of python
    |-- err.py                  module              Exception classes for tlib
    |-- version.py              module              TLIB Version
....
```

***
[1]: https://txu2008.github.io