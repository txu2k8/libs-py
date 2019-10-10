## **BS**
[![](https://img.shields.io/badge/Project-BS-yellow.svg)]()
[![](https://img.shields.io/badge/Python-2.7-green.svg)]()
[![](https://img.shields.io/badge/Python-3.6-green.svg)]()
[![](https://img.shields.io/badge/Email-tao.xu2008@outlook.com-red.svg)]()
[![](https://img.shields.io/badge/Blog-https://txu2008.github.io-red.svg)][1]

Math calculate releated functions.

#### Install
    pip install tlib

#### Usage
```python
from tlib.bs import *

if __name__ == '__main__':
    print(binary_system(2542, 7, 12))  # 将7进制的2542转为12进制
    print(gcd(97 * 2, 97 * 3))  # 最大公约数
    print(ip_to_int('192.168.1.1'))  # IP地址转换为整数
    print(int_to_ip(3232235778))  # 整数转换为IP地址
    print(strsize_to_byte('4k'))  # 字符 "4k" 转换为整数，单位 byte

'''
output:
    681
    97
    3232235777
    192.168.1.2
    4096
'''
```

***
[1]: https://txu2008.github.io