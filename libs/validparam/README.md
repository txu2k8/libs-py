## **validparam**
[![](https://img.shields.io/badge/Project-validparam-yellow.svg)]()
[![](https://img.shields.io/badge/Python-2.7-green.svg)]()
[![](https://img.shields.io/badge/Python-3.6-green.svg)]()
[![](https://img.shields.io/badge/Email-tao.xu2008@outlook.com-red.svg)]()
[![](https://img.shields.io/badge/Blog-https://txu2008.github.io-red.svg)][1]

Decorators for verify param valid, verify param type, value range, ...

#### Install
    pip install tlib

#### Usage
```
from tlib.validparam import validParam, nullOk, multiType

@validParam(i=int)
def foo(i):
    return i+1

kinds of validator:

1. verify param type only:
@validParam(type, ...)
eg:
Check whether the parameter in the first location is type 'int':
@validParam(int)
Check whether the parameter 'x' is type 'int':
@validParam(x=int)

Verify multi-param:
@validParam(int, int)
Verify specific parameter name:
@validParam(int, s=str)

Validators for * and ** will validate each element that the parameters actually contain:
@validParam(varargs=int)
def foo(*varargs): pass

@validParam(kws=int)
def foo7(s, **kws): pass

2. Conditional validation:
@validParam((type, condition), ...)
'condition' is an expression string that USES x to reference the object to be validated.

According to bool(the value of the expression), it is considered a failure if an exception is
thrown when the expression is evaluated:
eg:
Verify an integer between 10 and 20:
@validParam(i=(int, '10<x<20'))
Verify a string with a length less than 20:
@validParam(s=(str, 'len(x)<20'))
Verify a student with an age of less than 20:
@validParam(stu=(Student, 'x.age<20'))

In addition, if the type is a string, condition can also use the slash to start and end
to represent a regular expression match.
Verify a string of Numbers:
@validParam(s=(str, '/^\d*$/'))

3. The authentication method above defaults to failure when the value is None.
If None is a valid parameter, nullOk() can be used.
nullOk() can accept a validation condition as a parameter.
eg:
@validParam(i=nullOk(int))
@validParam(i=nullOk((int, '10<x<20')))
it also equal to:
@validParam(i=nullOk(int, '10<x<20'))

4. If the parameter has multiple legal types, you can use multiType().
multiType() can accept multiple parameters, each of which is a validation condition.。
eg:
@validParam(s=multiType(int, str))
@validParam(s=multiType((int, 'x>20'), nullOk(str, '/^\d+$/')))

5. If you have more complex validation requirements, you can write a function that is passed in as a validation function.
This function takes the object to be validated as a parameter and will depending on the bool(return value) determines
whether or not to pass the validation and throws an exception as a failure.
eg:
def validFunction(x):
    return isinstance(x, int) and x>0
@validParam(i=validFunction)
def foo(i): pass

This fun equal to:
@validParam(i=(int, 'x>0'))
def foo(i): pass
```
    
***
[1]: https://txu2008.github.io