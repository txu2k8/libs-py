# !/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#                                                        version: v1.0.0
#                                                             by: Tao.Xu
#                                                           date: 11/28/2018
#                                                      copyright: N/A
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NO INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
##############################################################################

r""" decorator: retry
"""

import traceback
import logging
import random
import time
import functools
from functools import partial
from progressbar import ProgressBar, Percentage, Bar, RotatingMarker, ETA

try:
    from decorator import decorator
except ImportError:
    def decorator(caller):
        """ Turns caller into a decorator.
        Unlike decorator module, function signature is not preserved.
        :param caller: caller(f, *args, **kwargs)
        """
        def decor(f):
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                return caller(f, *args, **kwargs)
            return wrapper
        return decor

try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

from utils import log

# ======================
# --- Global
# ======================
# logging_logger = logging.getLogger(__name__)
logging_logger = log.get_logger()


def __progressbar_k(sleep_time):
    """
    Print a progress bar, total value: sleep_time(seconds)
    :param sleep_time:
    :return:
    """

    widgets = ['Progress: ', Percentage(), ' ', Bar(marker=RotatingMarker('>-=')), ' ', ETA()]
    pbar = ProgressBar(widgets=widgets, maxval=sleep_time).start()
    for i in range(sleep_time):
        pbar.update(1 * i + 1)
        time.sleep(1)
    pbar.finish()


def __retry_internal(f, exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1, jitter=0,
                     raise_exception=True, logger=logging_logger):
    """
    Executes a function and retries it if it failed.
    :param f: the function to execute.
    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :param logger: logger.warning(fmt, error, delay) will be called on failed attempts.
                   default: retry.logging_logger. if None, logging is disabled.
    :returns: the result of the f function.
    """
    _tries, _delay = tries, delay
    while _tries:
        try:
            return f()
        except exceptions as e:
            if 'An error occurred (500)' in str(e) and _tries > 2:
                _tries = 2
            _tries -= 1

            if logger is not None:  # and tries not in (-1, 0, 1)
                if not _tries:
                    logger.error('{err}, retry <{f_name}> times arrived!!!({tries}/{total_tries})'.format(
                        err=e, f_name=f.func.__name__, delay=_delay, tries=(tries - _tries), total_tries=tries))
                    logger.warning(traceback.format_exc())

                    if raise_exception is True:
                        raise e
                    else:
                        return False
                else:
                    logger.warning('{err}, retry <{f_name}> after {delay} seconds...({tries}/{total_tries})'.format(
                        err=e, f_name=f.func.__name__, delay=_delay, tries=(tries - _tries), total_tries=tries))
                    logger.debug(traceback.format_exc())
            else:
                print('{err}, retry <{f_name}> after {delay} seconds...({tries}/{total_tries})'.format(
                    err=e, f_name=f.func.__name__, delay=_delay, tries=(tries - _tries), total_tries=tries))
                if not _tries and raise_exception is True:
                    raise e
                else:
                    return False

            # time.sleep(_delay)
            __progressbar_k(_delay)
            _delay *= backoff

            if isinstance(jitter, tuple):
                _delay += random.uniform(*jitter)
            else:
                _delay += jitter

            if max_delay is not None:
                _delay = min(_delay, max_delay)


def retry(exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1, jitter=0, raise_exception=True,
          logger=logging_logger):
    """Returns a retry decorator.
    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :param logger: logger.warning(fmt, error, delay) will be called on failed attempts.
                   default: retry.logging_logger. if None, logging is disabled.
    :returns: a retry decorator.
    """

    @decorator
    def retry_decorator(f, *fargs, **fkwargs):
        args = fargs if fargs else list()
        kwargs = fkwargs if fkwargs else dict()
        return __retry_internal(partial(f, *args, **kwargs), exceptions, tries, delay, max_delay, backoff, jitter,
                                raise_exception, logger)

    return retry_decorator


def retry_call(f, fargs=None, fkwargs=None, exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1,
               jitter=0, raise_exception=True, logger=logging_logger):
    """
    Calls a function and re-executes it if it failed.
    :param f: the function to execute.
    :param fargs: the positional arguments of the function to execute.
    :param fkwargs: the named arguments of the function to execute.
    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :param logger: logger.warning(fmt, error, delay) will be called on failed attempts.
                   default: retry.logging_logger. if None, logging is disabled.
    :returns: the result of the f function.
    """
    args = fargs if fargs else list()
    kwargs = fkwargs if fkwargs else dict()
    return __retry_internal(partial(f, *args, **kwargs), exceptions, tries, delay, max_delay, backoff, jitter,
                            raise_exception, logger)


if __name__ == "__main__":
    pass
