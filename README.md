# [TLIB](https://github.com/txu2008/TLIB)

Please Visit **https://github.com/txu2008/TLIB** for more details

## Quick Start

### 1. Download
    - git clone tlib or download the released tar balls

### 2. Installation

Install from pip

```bash
pip install tlib
```

Install from source code:

```bash
python setup.py install
```

### 3. Doc & Wiki

Visit Wiki to see more details: https://github.com/txu2008/TLIB/wiki

Visit Doc site to see py-docs: TODO

```python
# Examples:
# 1. Init logging logger
from tlib import log
my_logger = log.get_logger(logfile='test1.log', logger_name='test1', debug=True, reset_logger=True)
my_logger.info('test_1 start ...')
my_logger.warning('test_1 hello,world')
my_logger.debug('test_1 hello,world')
my_logger.error('test_1 hello,world')
my_logger.critical('test_1 hello,world')
```


## Tests
    - run test/test_*.py
    - python run_test.py log
    - python run_test.py mail
    - etc.

## Contribute To TLIB
    - Commit code to GITHUB, https://github.com/txu2008/TLIB
    - Need to check pep8 and pylint rules before you start a pull request

## Discussion
    - Github Issues

## Reference
      * http://tungwaiyip.info/software/HTMLTestRunner.html

## WIKI
https://github.com/txu2008/TLIB/wiki

## code directory tree:

```text
tlib
    |-- stressrunner/*          module              supper unittest framework, fit for stress test, report html, send email, etc.
    |-- cache.py                module              Memory cache related module
    |-- decorators.py           module              Decorators of python
    |-- err.py                  module              Exception classes for TLIB
    |-- __init__.py             module              Default __init__.py
    |-- log.py                  module              TLIB logging
    |-- mail.py                 module              TLIB Email module (send emails)
    |-- oper.py                 module              Mixin operations
    |-- platforms.py            module              Cross-platform operations
    |-- shell                   package             Shell Operations、cross-hosts execution
    |-- util                    package             common func utils, etc
    |-- version.py              module              TLIB Version
```
