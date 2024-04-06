import os
import sys
import datetime
import json
from enum import Enum
from typing import Union, NoReturn, TypedDict, Literal, Optional, NotRequired, List

import util as U
from util import SWErr, SWErrCode

# U.logD(f"Loading name={__name__}, file={__file__}")

"""

## Test

python

import sys
sys.path.append('./src/lib')
import util as U
from util import SWErr, SWErrCode
import appTest

appTest.testPrintLog()
appTest.testExceptionCases(3)

try:
   appTest.testUnionType(2)
   appTest.testUnionType([1,3,5])
   appTest.testUnionType([1,3,'x'])
except Exception as e:
   U.logPrefixE('testUnion', e)

"""


def testPrintLog():
    funcName = testPrintLog.__name__
    prefix = funcName
    try:
        U.logD(f"{prefix} test debug message")
        U.logI(f"{prefix} test info message")
        U.logW(f"{prefix} test warning message")
        U.logE(f"{prefix} test error message")
    except Exception as e:
        U.throwPrefix(prefix, e)


class TOpts_testException(TypedDict):
    f1: NotRequired[Literal["divideByZero", "exception", "SWErr"]]
    f2: NotRequired[Literal["divideByZero", "exception", "SWErr"]]
    f3: NotRequired[Literal["divideByZero", "exception", "SWErr"]]


## First level function
def testException1(opts: TOpts_testException = {}):
    funcName = testException1.__name__
    prefix = funcName
    try:
        ## If not specified the test case, run testFunc2_()
        if not "f1" in opts:
            testException2(opts)
        ## If specified the test case, follow what has been defined
        elif opts["f1"] == "divideByZero":
            x = 1 / 0
        elif opts["f1"] == "exception":
            raise Exception(f"error in {funcName}")
        elif opts["f1"] == "SWErr":
            raise SWErr(SWErrCode.E_Data, f"SWErr in {funcName}")
    except Exception as e:
        U.logPrefixE(prefix, e)


## Second level function
def testException2(opts: TOpts_testException):
    funcName = testException2.__name__
    prefix = funcName
    try:
        ## If not specified the test case, run testFunc2_()
        if not "f2" in opts:
            testException3(opts)
        ## If specified the test case, follow what has been defined
        elif opts["f2"] == "divideByZero":
            x = 1 / 0
        elif opts["f2"] == "exception":
            raise Exception(f"error in {funcName}")
        elif opts["f2"] == "SWErr":
            raise SWErr(SWErrCode.E_Data, f"SWErr in {funcName}")
    except Exception as e:
        U.throwPrefix(prefix, e)


## Third level function
def testException3(opts: TOpts_testException):
    funcName = testException3.__name__
    prefix = funcName
    try:
        ## If not specified the test case, creTestCase"ate a key error
        if not "f3" in opts:
            v = {}
            x = v["ThisKeyDoesNotExist"]  ## this has keyError
        ## If specified the test case, follow what has been defined
        elif opts["f3"] == "divideByZero":
            x = 1 / 0
        elif opts["f3"] == "exception":
            raise Exception(f"error in {funcName}")
        elif opts["f3"] == "SWErr":
            raise SWErr(SWErrCode.E_Data, f"SWErr in {funcName}")
    except Exception as e:
        U.throwPrefix(prefix, e)


## Showcase the use of Optional
## Optional[int] is the same as Optional[None, int]
def testExceptionCases(level: Optional[int]):
    funcName = testExceptionCases.__name__
    prefix = funcName
    try:
        ## Showcase the use of Optional[]
        if level is None:
            return

        if level >= 1:
            U.logI(f"Exception is thrown at first level of function")
            testException1({"f1": "divideByZero"})
            testException1({"f1": "exception"})
            testException1({"f1": "SWErr"})

        if level >= 2:
            U.logI(f"Exception is thrown at second level of function")
            testException1({"f2": "divideByZero"})
            testException1({"f2": "exception"})
            testException1({"f2": "SWErr"})

        if level >= 3:
            U.logI(f"Exception is thrown at third level of function")
            testException1()
            testException1({"f3": "divideByZero"})
            testException1({"f3": "exception"})
            testException1({"f3": "SWErr"})
    except Exception as e:
        U.logPrefixE(prefix, e)


## showcase the use of Union[]
def testUnionType(x: Union[int, List[int]]) -> int:
    funcName = testUnionType.__name__
    prefix = funcName
    try:
        if isinstance(x, int):
            return 2 * x
        elif isinstance(x, list):
            return sum(x)
        else:
            raise Exception(f"x is not int or List[int]")
    except Exception as e:
        U.throwPrefix(prefix, e)
