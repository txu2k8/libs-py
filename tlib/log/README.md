## **LOG**
[![](https://img.shields.io/badge/Project-log-yellow.svg)]()
[![](https://img.shields.io/badge/Python-2.7-green.svg)]()
[![](https://img.shields.io/badge/Python-3.6-green.svg)]()
[![](https://img.shields.io/badge/Email-tao.xu2008@outlook.com-red.svg)]()
[![](https://img.shields.io/badge/Blog-https://txu2008.github.io-red.svg)][1]

logging config, colored, compress, log file/console .etc

#### Install
    pip install tlib

#### Usage
    from tlib import log
    if __name__ == "__main__":
        logfile = "test_2.log"
        logger = log.get_logger(logfile, logger_name='test2', debug=True)
        logger.info('test_2 start ...')
        logger.warning('test_2 hello,world')
        logger.debug('test_2 hello,world')
        logger.error('test_2 hello,world')
        logger.critical('test_2 hello,world')

***
[1]: https://txu2008.github.io