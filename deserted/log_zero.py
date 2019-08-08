# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

r""" logging config
    logzero
"""

import logging
import logzero
from logzero import logger
from logzero.colors import Fore as ForegroundColors

# init logger
fmt = "%(asctime)s %(color)s%(levelname)-8.8s%(end_color)s: %(message)s"
datefmt = '%y/%m/%d %H:%M:%S'
colors = {
    logging.DEBUG:      ForegroundColors.CYAN,
    logging.INFO:       ForegroundColors.GREEN,
    logging.WARNING:    ForegroundColors.YELLOW,
    logging.ERROR:      ForegroundColors.LIGHTRED_EX,
    logging.CRITICAL:   ForegroundColors.LIGHTMAGENTA_EX
}
logzero.formatter(logzero.LogFormatter(fmt=fmt, datefmt=datefmt, colors=colors))
logzero.logfile("debug.log", loglevel=logging.DEBUG)
logzero.loglevel(logging.DEBUG)


if __name__ == "__main__":

    logger.debug("hello")
    logger.info("info")
    logger.warn("warn")
    logger.error("error")

    # This is how you'd log an exception
    try:
        raise Exception("this is a demo exception")
    except Exception as e:
        logger.exception(e)
