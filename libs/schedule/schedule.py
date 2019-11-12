# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/11/1 15:57
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

"""This try schedule the func task and list the tasks with PrettyTable
If the func is a instance.func and class has __dict_.phase_list,
can record the all phase status.
Such as:
class A(object):
    def __init__(self):
    self.phase_list = []

Usage:
See the test examples
"""

import time
import unittest
from functools import wraps, partial
from prettytable import PrettyTable

from tlib.log import log

# ======================
# --- Global
# ======================
logger = log.get_logger()


def __run_phase(f, skip=False, comments=''):
    """
    Record the running/complete phase status
    Requirement in class:
        phase_list = []  # PrettyTable(['Step', 'Result', 'Comments'])
    :param f:
    :param skip:
    :param comments:
    :return:
    """

    phase_name = f.func.__name__
    comments = str(comments or '')
    try:
        phase_list = f.args[0].phase_list
    except Exception as e:
        phase_list = []
        verbosity = 0
    else:
        verbosity = 1

    # if '__wrapped__' in f.func.__dict__:
    #     print(f.func.__dict__['__wrapped__'].__name__)

    phase_stat = 'SKIP' if skip else 'START'
    if '__wrapped__' not in f.func.__dict__:
        logger.log(21, '{0}: {1} ...'.format(phase_stat, phase_name))
    phase_list.append([phase_name, phase_stat, comments])

    if verbosity > 0 and not skip:
        # print with PrettyTable
        cur_table = PrettyTable(['No.', 'Step', 'Progress', 'Comments'])
        cur_table.align['Step'] = 'l'
        cur_table.align['Comments'] = 'l'
        for idx, phase in enumerate(phase_list):
            phase_status = [idx + 1] + phase
            cur_table.add_row(phase_status)
        logger.info("Test Progress:\n{0}".format(cur_table))

    if skip:  # and '__wrapped__' not in f.func.__dict__:
        return True

    # run func and update the phase running result(PASS or FAIL)
    idx = len(phase_list) - 1
    if f.func.__doc__:
        logger.info(f.func.__doc__)
    time.sleep(1)
    rtn = f()
    result = 'PASS' if rtn else 'FAIL'
    logger.log(21, '{0}:{1}, rc:{2}'.format(result, phase_name, rtn))
    phase_list[idx][1] = result

    return rtn


def enter_phase(skip=False, comments=''):
    """
    a decorator call for _run_phase
    :param skip:
    :param comments:
    :return:
    """

    def decorator(f):
        @wraps(f)
        def wrapper(*fargs, **fkwargs):
            args = fargs if fargs else list()
            kwargs = fkwargs if fkwargs else dict()
            return __run_phase(partial(f, *args, **kwargs), skip, comments)
        return wrapper

    return decorator


def run_phase(f, fargs=None, fkwargs=None, skip=False, comments=''):
    """
    Calls a function with _run_phase.
    :param f:
    :param fargs:
    :param fkwargs:
    :param skip:
    :param comments:
    :return:
    """
    args = fargs if fargs else list()
    kwargs = fkwargs if fkwargs else dict()
    return __run_phase(partial(f, *args, **kwargs), skip, comments)


# ===================== Test =====================
@enter_phase(comments='test----1')
def func_1(a, b):
    logger.info('{0} + {1}'.format(a, b))
    return a + b


@enter_phase(comments='test----2')
def func_2(a, b):
    logger.info('{0} + {1}'.format(a, b))
    return a + b


@enter_phase(comments='test----3')
def func_3(a, b):
    logger.info('{0} + {1}'.format(a, b))
    return a + b


class Func(object):
    """Test enter_phase/run_phase for class func"""

    def __init__(self):
        super(Func, self).__init__()
        self.phase_list = []

    @enter_phase(comments='test----1')
    def func_1(self, a, b):
        logger.info('{0} + {1}'.format(a, b))
        return a + b

    @enter_phase(comments='test----2', skip=True)
    def func_2(self, a, b):
        logger.info('{0} + {1}'.format(a, b))
        return a + b

    @enter_phase(comments='test----3')
    def func_3(self, a, b):
        logger.info('{0} + {1}'.format(a, b))
        return a + b


class ScheduleTestCase(unittest.TestCase):
    """Schedule unit test case"""
    def setUp(self):
        self.phase_list = []

    def tearDown(self):
        logger.info('Test Complete!')
        if self.phase_list:
            step_table = PrettyTable(['No.', 'Step', 'Result', 'Comments'])
            step_table.align['Step'] = 'l'
            step_table.align['Comments'] = 'l'
            for idx, step in enumerate(self.phase_list):
                step_status = [idx + 1] + step
                step_table.add_row(step_status)
            logger.info("Test Case run steps list:\n{0}".format(step_table))

    def test_1(self):
        print('='*10 + 'enter_phase for function' + '='*10)
        func_1(1, 2)
        func_2(2, 3)
        func_3(3, 4)

    def test_2(self):
        print('=' * 10 + 'run_phase for function' + '=' * 10)
        run_phase(func_1.__wrapped__, fkwargs={'a': 1, 'b': 2}, comments='TEST1')
        run_phase(func_2.__wrapped__, fkwargs={'a': 2, 'b': 3}, comments='TEST2')
        run_phase(func_3.__wrapped__, fkwargs={'a': 3, 'b': 4}, comments='TEST3')

    def test_3(self):
        print('=' * 10 + 'enter_phase for class' + '=' * 10)
        test_f = Func()
        test_f.func_1(1, 2)
        test_f.func_2(2, 3)
        test_f.func_3(3, 4)
        self.phase_list.extend(test_f.phase_list)

    def test_4(self):
        print('=' * 10 + 'run_phase for class' + '=' * 10)
        test_f = Func()
        run_phase(test_f.func_1, fkwargs={'a': 1, 'b': 2},
                  comments='TEST1')
        run_phase(test_f.func_2.__wrapped__, [test_f], fkwargs={'a': 2, 'b': 3},
                  comments='TEST2', skip=True)
        run_phase(test_f.func_3.__wrapped__, [test_f], fkwargs={'a': 3, 'b': 4},
                  comments='TEST3')
        self.phase_list.extend(test_f.phase_list)


if __name__ == "__main__":
    # test
    # unittest.main()
    # suite = unittest.TestLoader().loadTestsFromTestCase(ScheduleTestCase)
    suite = unittest.TestSuite(map(ScheduleTestCase, ['test_4']))
    unittest.TextTestRunner(verbosity=2).run(suite)