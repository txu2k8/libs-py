## **schedule**
[![](https://img.shields.io/badge/Project-schedule-yellow.svg)]()
[![](https://img.shields.io/badge/Python-2.7-green.svg)]()
[![](https://img.shields.io/badge/Python-3.6-green.svg)]()
[![](https://img.shields.io/badge/Email-tao.xu2008@outlook.com-red.svg)]()
[![](https://img.shields.io/badge/Blog-https://txu2008.github.io-red.svg)][1]

Decorators for schedule the func task and list the tasks with PrettyTable

#### Install
    pip install tlib

#### Usage
```python
from tlib.schedule import enter_phase, run_phase

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

```
     
***
[1]: https://txu2008.github.io