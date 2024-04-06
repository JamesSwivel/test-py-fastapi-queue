from enum import Enum
from typing import Union, Dict, TypedDict, overload, Optional, Any


class SWErrCode(Enum):
    """
    err code in Enum

    NOTE:
    - Given an Enum instance, obj.name to get the enum value, e.g. SWErrCode.E_Err.name == 'E_Err'
    """

    ## Special Error that indicates not an error
    E_NotErr = "E_NotErr"

    ## Default error code
    E_Err = "E_Err"

    ## General errors
    E_Timeout = "E_Timeout"
    E_Data = "E_Data"
    E_DataNotJson = "E_DataNotJson"
    E_Proto = "E_Proto"
    E_NotFound = "E_NotFound"

    ## req and res
    E_Req = "E_Req"
    E_Res = "E_Res"
    E_Cmd = "E_Cmd"

    ## Network errors
    E_Disconnected = "E_Disconnected"

    ## File errors
    E_FileNotFound = "E_FileNotFound"
    E_FileNotJson = "E_FileNotJson"
    E_FileData = "E_FileData"


class SWErr(Exception):
    @classmethod
    def noErr(cls):
        return SWErr(SWErrCode.E_NotErr, "")

    ## limit the instance variable
    ## Why? avoid bugs some methods created wrong instance variable
    __slots__ = ("_errCode", "_err", "_extra")

    @overload
    def __init__(self, arg1: str):
        """
        ctor by err msg
        """

    @overload
    def __init__(self, arg1: SWErrCode, arg2: str):
        """
        ctor by errcode and errMsg
        """

    @overload
    def __init__(self, arg1: Union["SWErr", Exception]):
        """
        ctor by SWErr or Exception
        """

    def __init__(self, arg1: Any, arg2: Any = None):
        """
        Args:
            1st form:
                arg1: err msg
            2nd form
                arg1: errcode, arg2: err msg
            3rd form
                arg1: Exception|SWErr
        """
        self._errCode: SWErrCode = SWErrCode.E_Err
        self._err = ""
        self._extra = {}
        self.setError(arg1, arg2)

    def errCode(self) -> SWErrCode:
        return self._errCode

    def err(self):
        return self._err

    def extra(self):
        return self._extra

    def errWithErrCode(self):
        return f"E[{self._errCode}] {self._err}"

    def isValid(self):
        return self._errCode == SWErrCode.E_NotErr

    def isError(self):
        return self._errCode != SWErrCode.E_NotErr

    def setExtra(self, extra: Union[TypedDict, Dict]):
        self._extra = extra

    @overload
    def setError(self, arg1: str):
        """
        Set Error by err msg
        """

    @overload
    def setError(self, arg1: SWErrCode, arg2: str):
        """
        Set Error by errcode and errMsg
        """

    @overload
    def setError(self, arg1: Union["SWErr", Exception]):
        """
        Set Error by SWErr or Exception
        """

    def setError(self, arg1: Any, arg2: Any = None):
        """
        Set error
        Args:
            1st form:
                arg1: err msg
            2nd form
                arg1: errcode, arg2: err msg
            3rd form
                arg1: Exception|SWErr
        """
        outErrCode: SWErrCode = SWErrCode.E_Err
        outErr = ""

        ## If arg1 is SWErr, arg2 is ignored
        if isinstance(arg1, SWErr):
            outErrCode, outErr = arg1.errCode(), arg1.err()
        ## If arg1 is Exception, arg2 is ignored
        elif isinstance(arg1, Exception):
            outErrCode, outErr = SWErrCode.E_Err, str(arg1)

        ## If arg1 is SWErrCode, arg2 is err msg
        elif isinstance(arg1, SWErrCode):
            outErrCode, outErr = arg1, arg2
        ## If arg1 is str
        else:
            outErr = arg1

        ## errCode must be non-empty, default value is E_Err
        self._errCode = outErrCode
        self._err = outErr

    def __str__(self):
        """
        String of object
        """
        return self._err
