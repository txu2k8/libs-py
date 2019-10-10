# !/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/8/8 12:49
# @Author  : Tao.Xu
# @Email   : tao.xu2008@outlook.com

r""" param verifier
@summary: param verifier
The module provides a decorator to verify whether the parameter is legal.
Usage as follow:

from validparam import validParam, nullOk, multiType

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
"""

import inspect
import re


class ValidateException(Exception):
    pass


def valid_param(*varargs, **keywords):
    """param verifier"""

    varargs = map(_to_standard_condition, varargs)
    keywords = dict((k, _to_standard_condition(keywords[k]))
                    for k in keywords)

    def generator(func):
        args, varargname, kwname = inspect.getargspec(func)[:3]
        dctValidator = _getcallargs(args, varargname, kwname,
                                    varargs, keywords)

        def wrapper(*callvarargs, **callkeywords):
            dctCallArgs = _getcallargs(args, varargname, kwname,
                                       callvarargs, callkeywords)

            k, item = None, None
            try:
                for k in dctValidator:
                    if k == varargname:
                        for item in dctCallArgs[k]:
                            assert dctValidator[k](item)
                    elif k == kwname:
                        for item in dctCallArgs[k].values():
                            assert dctValidator[k](item)
                    else:
                        item = dctCallArgs[k]
                        assert dctValidator[k](item)
            except:
                raise ValidateException('%s() parameter validation fails, param: %s, value: %s(%s)'
                                        % (func.func_name, k, item, item.__class__.__name__))

            return func(*callvarargs, **callkeywords)

        wrapper = _wrapps(wrapper, func)
        return wrapper

    return generator


def _to_standard_condition(condition):
    """Convert check conditions in various formats to check functions."""

    if inspect.isclass(condition):
        return lambda x: isinstance(x, condition)

    if isinstance(condition, (tuple, list)):
        cls, condition = condition[:2]
        if condition is None:
            return _to_standard_condition(cls)

        if cls in (str, str) and condition[0] == condition[-1] == '/':
            return lambda x: (isinstance(x, cls)
                              and re.match(condition[1:-1], x) is not None)

        return lambda x: isinstance(x, cls) and eval(condition)

    return condition


def nullOk(cls, condition=None):
    """The check condition specified by this function accepts None."""

    return lambda x: x is None or _to_standard_condition((cls, condition))(x)


def multiType(*conditions):
    """The check condition specified by this function requires only one pass."""

    lst_validator = map(_to_standard_condition, conditions)

    def validate(x):
        for v in lst_validator:
            if v(x):
                return True

    return validate


def _getcallargs(args, varargname, kwname, varargs, keywords):
    """Gets the dictionary of the parameter name-value of the call."""

    dct_args = {}
    varargs = tuple(varargs)
    keywords = dict(keywords)

    argcount = len(args)
    varcount = len(varargs)
    callvarargs = None

    if argcount <= varcount:
        for n, argname in enumerate(args):
            dct_args[argname] = varargs[n]

        callvarargs = varargs[-(varcount - argcount):]

    else:
        for n, var in enumerate(varargs):
            dct_args[args[n]] = var

        for argname in args[-(argcount - varcount):]:
            if argname in keywords:
                dct_args[argname] = keywords.pop(argname)

        callvarargs = ()

    if varargname is not None:
        dct_args[varargname] = callvarargs

    if kwname is not None:
        dct_args[kwname] = keywords

    dct_args.update(keywords)
    return dct_args


def _wrapps(wrapper, wrapped):
    """Copy"""

    for attr in ('__module__', '__name__', '__doc__'):
        setattr(wrapper, attr, getattr(wrapped, attr))
    for attr in ('__dict__',):
        getattr(wrapper, attr).update(getattr(wrapped, attr, {}))

    return wrapper


if __name__ == '__main__':
    pass
