## **retry**
[![](https://img.shields.io/badge/Project-retry-yellow.svg)]()
[![](https://img.shields.io/badge/Python-2.7-green.svg)]()
[![](https://img.shields.io/badge/Python-3.6-green.svg)]()
[![](https://img.shields.io/badge/Email-tao.xu2008@outlook.com-red.svg)]()
[![](https://img.shields.io/badge/Blog-https://txu2008.github.io-red.svg)][1]

Decorators for retry func

#### Install
    pip install tlib

#### Usage
    from tlib.retry import retry, retry_call
    
    @retry(tries=3, delay=10, jitter=1)
    def test_1(a):
        if not a:
            raise Exception('raise for retry')
            
    def test_2(a):
        if not a:
            raise Exception('raise for retry')
            
    if __name__ == "__main__":
        retry_call(test_2, fkwargs={'a':False}, tries=3, delay=10, jitter=1)
        
***
[1]: https://txu2008.github.io