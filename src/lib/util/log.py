import os
import sys
import datetime
from typing import Union, NoReturn, TypedDict, Literal, Final

from .err import SWErr

"""
## Test

python

import sys
sys.path.append('./src/lib')
import util as U
from util import SWErr, SWErrCode

def func1():
    prefix = func1.__name__
    try:
        func2()
        # x = 1/0
        # raise Exception(f'error in func1')
        # raise SWErr(SWErrCode.E_Data, f'error in func1')
    except Exception as e:
        U.logPrefixE(prefix, e)

def func2():
    prefix = func2.__name__
    try:
        func3()
        # raise Exception(f'error in func2')
        # raise SWErr(SWErrCode.E_Data, f'error in func2')
    except Exception as e:
        U.throwPrefix(prefix, e)

def func3():
    prefix = func3.__name__
    try:
        x = 1 /0
        # raise Exception(f'error in func3')
        # raise SWErr(SWErrCode.E_Data, f'error in func2')
    except Exception as e:
        U.throwPrefix(prefix, e)

def testLog():
    funcName = testLog.__name__
    prefix = funcName
    try:
        U.logD(f"{prefix} debug test message")
        U.logI(f"{prefix} debug info message")
        U.logW(f"{prefix} debug warning message")
        U.logE(f"{prefix} debug error message")
    except Exception as e:
        U.throwPrefix(prefix, e)


"""

## Support older python 3.6.x
##from typing_extensions import TypedDict


class Log:
    ## https://www.unixtutorial.org/how-to-show-colour-numbers-in-unix-terminal/
    ## define COLOR_GRAY "\x1b[1;30m"  // this one has problem selecting text in putty (cannot see what is selected)
    COLOR_GRAY: Final[str] = "\x1b[38;5;240m"
    COLOR_YELLOW: Final[str] = "\x1b[0;33m"
    COLOR_YELLOW_L: Final[str] = "\x1b[1;33m"
    COLOR_RED: Final[str] = "\x1b[0;31m"
    COLOR_RED_L: Final[str] = "\x1b[1;31m"
    COLOR_GREEN: Final[str] = "\x1b[0;32m"
    COLOR_GREEN_L: Final[str] = "\x1b[1;32m"
    COLOR_PURPLE: Final[str] = "\x1b[0;35m"
    COLOR_PURPLE_L: Final[str] = "\x1b[1;35m"
    COLOR_CYAN: Final[str] = "\x1b[0;36m"
    COLOR_CYAN_L: Final[str] = "\x1b[1;36m"
    COLOR_NONE: Final[str] = "\x1b[0m"

    @classmethod
    def isWin(cls) -> bool:
        return os.name == "nt"

    @classmethod
    def isPosix(cls) -> bool:
        return os.name == "posix"

    @classmethod
    def exceptionProps(cls, e: Exception):
        """
        Get exception props

        Args:
            e: Exception

        Returns:
            refer to Returns_exceptionProps
        """

        class Returns_exceptionProps(TypedDict):
            isRuntimeErr: bool
            err: str
            errno: int
            filename: str
            filename2: str

        ## default out
        out: Returns_exceptionProps = {
            "isRuntimeErr": False,
            "err": "UNKNOWN err",
            "errno": 0,
            "filename": "",
            "filename2": "",
        }
        try:
            ## default err string
            out["err"] = str(e)

            ## In case of OSError, try get OS errno and str
            if isinstance(e, OSError):
                out["isRuntimeErr"] = True
                ## e.strerror and e.errno may be None
                if e.strerror is not None:
                    out["err"] = e.strerror
                if e.errno is not None:
                    out["errno"] = e.errno

            ## In case of FileNotFoundError, try get the relevant filename
            elif isinstance(e, FileNotFoundError) or isinstance(e, PermissionError):
                out["isRuntimeErr"] = True
                if e.filename is not None:
                    out["filename"] = e.filename
                if e.filename2 is not None:
                    out["filename2"] = e.filename2

            ## insufficient memory
            elif isinstance(e, MemoryError):
                out["isRuntimeErr"] = True
                out["err"] = "memory err"

            ## reference to garbage-collected object (already free/released)
            elif isinstance(e, ReferenceError):
                out["isRuntimeErr"] = True
                out["err"] = "memory err (reference)"

            ## Python common runtime error
            elif (
                ## value, key, attribute
                isinstance(e, ValueError)
                or isinstance(e, AttributeError)
                or isinstance(e, TypeError)
                or isinstance(e, KeyError)
                or isinstance(e, IndexError)
                or isinstance(e, NameError)
                ## math
                or isinstance(e, ZeroDivisionError)
                or isinstance(e, OverflowError)
                or isinstance(e, FloatingPointError)
                or isinstance(e, ZeroDivisionError)
                ## file
                or isinstance(e, EOFError)
                ## misc
                or isinstance(e, AssertionError)
                or isinstance(e, ImportError)
                or isinstance(e, IndentationError)
                or isinstance(e, NotImplementedError)
            ):
                out["isRuntimeErr"] = True

            ## App level exception is NOT considered as a python runtime error
            ## Thus, exception originated from Python is considered as runtime error
            else:
                pass

        ## Any exception will return default out
        except Exception as e:
            pass
        return out

    @classmethod
    def toExceptionStr(cls, e: Union[Exception, str]):
        """
        Convert exception to str (handle runtime error, and OSError with errno)

        Args:
            e: exception

        Returns:
            str
        """
        exceptionMsg = ""
        prefix = ""
        suffix = ""
        if isinstance(e, Exception):
            props = cls.exceptionProps(e)
            prefix = "<runtimeErr> " if props["isRuntimeErr"] else ""
            suffix += f", filename={props['filename']}" if props["filename"] else ""
            suffix += f", filename2={props['filename2']}" if props["filename2"] else ""
            suffix += f", errno={props['errno']}" if props["errno"] > 0 else ""
            exceptionMsg = props["err"]
        else:
            exceptionMsg = e

        out = f"{prefix}{exceptionMsg}{suffix}"
        return out

    @classmethod
    def log_(cls, logType: Literal["I", "D", "W", "E"], message: str):
        ## By default and for Windows, do not use color
        hdColor = ""
        msgColor = ""

        ## For linux/posix, use terminal color
        ## NOTE: Windows 11 command prompt support terminal color as well
        # if cls.isPosix():
        if True:
            if logType == "I":
                hdColor = cls.COLOR_GREEN
                msgColor = ""
            elif logType == "D":
                hdColor = cls.COLOR_GRAY
                msgColor = ""
            elif logType == "W":
                hdColor = cls.COLOR_PURPLE_L
                msgColor = cls.COLOR_PURPLE_L
            elif logType == "E":
                hdColor = cls.COLOR_RED_L
                msgColor = cls.COLOR_RED_L
            else:
                hdColor = cls.COLOR_GRAY
                msgColor = ""

        now = datetime.datetime.now()
        nowEpms = int(now.timestamp() * 1000)
        nowStr = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(
            (
                f"{'' if hdColor == '' else cls.COLOR_YELLOW}"
                f"{nowStr}`{hdColor}{logType}"
                f"{'' if hdColor == '' else cls.COLOR_NONE }`"
                f"{msgColor}{message}"
                f"{'' if msgColor == '' else cls.COLOR_NONE }"
            ),
            ## In case of 'E" log, use stderr instead of stdout
            file=sys.stderr if logType == "E" else sys.stdout,
        )
        # sys.stdout.flush()

    @classmethod
    def logPrefixE_(cls, prefix: str, msg: Union[str, Exception]):
        """
        Print error log with prefix.  Prefix has the exception trace history
        - If logPrefixE() is called from the first exception,
          msg has no leading '|', then it prints '|prefix| msg'
        - If logPrefixE() is called from cascading exceptions
          msg has leading "|", then it prints '|prefixN|...|prefix2|prefix1 msg'.
          The cascading prefix shows useful exception trace history.
        """
        msg1 = f"{cls.toExceptionStr(msg)}"
        isFirstPrefix = msg1[0] != "|"
        err = ""
        if isFirstPrefix:
            err = f"|{prefix}| {msg1}"
        else:
            err = f"|{prefix}{msg1}"

        ## If msg is SWErr, include E[errcode] as leading prefix
        if isinstance(msg, SWErr):
            err = f"E[{msg.errCode().name}] " + err
        cls.log_("E", err)

    @classmethod
    def throwPrefix_(cls, prefix: str, msg: Union[str, Exception]) -> NoReturn:
        """
        Throw SWErr that keeps errcode, err msg and trace history
        Refer to logPrefixE_() for details about exception trace history.
        """
        msg1 = f"{cls.toExceptionStr(msg)}"
        err = ""
        isFirstPrefix = msg1[0] != "|"
        if isFirstPrefix:
            err = f"|{prefix}| {msg1}"
        else:
            err = f"|{prefix}{msg1}"

        ## If msg is SWErr, simply raise it
        if isinstance(msg, SWErr):
            ## keep SWErr errcode but err msg is updated
            msg.setError(msg.errCode(), err)
            raise msg
        ## If msg is str, simply raise the exception str
        else:
            raise Exception(err)


def throwPrefix(prefix: str, msg: Union[str, Exception]) -> NoReturn:
    """
    Throw SWErr that keeps errcode, err msg and trace history
    Refer to logPrefixE_() for details about exception trace history.
    """
    Log.throwPrefix_(prefix, msg)


def logPrefixE(prefix: str, msg: Union[str, Exception]):
    """
    Print error log with prefix.
    - Prefix reveals the exception trace history
    - Example: |prefixN|...|prefix2|prefix1 msg
    """
    Log.logPrefixE_(prefix, msg)


def logI(message: str):
    """
    Print log (information)
    """
    Log.log_("I", message)


def logD(message: str):
    """
    Print log (debug)
    """
    Log.log_("D", message)


def logW(message: str):
    """
    Print log (warning)
    """
    Log.log_("W", message)


def logE(message: Union[str, Exception]):
    """
    Print log (error)

    Args:
        message can be str or exception
    """
    Log.log_("E", Log.toExceptionStr(message))


def trimErrPrefix(err: str) -> str:
    """
    Trim err leading prefix, i.e. get the trailing err message
    """
    if len(err) > 0 and err[0] == "|":
        ## Prefix format: |xxx|xxx|xxx| yyyy
        ## tokens[1] is yyyy
        tokens = err.split("| ")
        return "".join(tokens[1:]) if len(tokens) >= 2 else err
    else:
        return err
