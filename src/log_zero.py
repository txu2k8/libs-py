# !/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
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
